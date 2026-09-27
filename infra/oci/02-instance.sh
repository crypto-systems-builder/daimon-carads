#!/usr/bin/env bash
# Launch the Always Free instance, retrying across availability domains.
#
# "Out of host capacity" is the normal experience on Always Free ARM, not a bug:
# Oracle hands the shape out as capacity frees up, so this loops instead of failing.
# Leave it running in a terminal; it will grab a box as soon as one appears.

. "$(dirname "$0")/lib.sh"
load_env

INSTANCE_NAME="$STACK_NAME-web"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-120}"   # x RETRY_SLEEP = how long we keep trying
RETRY_SLEEP="${RETRY_SLEEP:-60}"

[ -n "${SUBNET_ID:-}" ] || die "no SUBNET_ID in state — run ./01-network.sh first"
[ -f "$SSH_PUBLIC_KEY_FILE" ] || die "no SSH public key at $SSH_PUBLIC_KEY_FILE
  generate one with: ssh-keygen -t ed25519 -f ${SSH_PRIVATE_KEY_FILE} -C $STACK_NAME"

# --- Already provisioned? ----------------------------------------------------
# Match any live state, not just RUNNING: an interrupted --wait-for-state poll
# leaves a PROVISIONING/STARTING instance behind, and launching on top of it
# would double-spend the Always Free allowance (or trip LimitExceeded).
existing="$(o compute instance list --compartment-id "$OCI_COMPARTMENT_ID" \
              --display-name "$INSTANCE_NAME" \
  | jq -r '[.data[] | select(."lifecycle-state"
        | IN("RUNNING","PROVISIONING","STARTING","STOPPING","STOPPED"))][0].id // empty')"
if [ -n "$existing" ]; then
  c_ylw "instance $INSTANCE_NAME already exists — reusing it"
  instance_id="$existing"
  state="$(o compute instance get --instance-id "$instance_id" \
             | jq -r '.data."lifecycle-state"' || true)"
  if [ "$state" = "STOPPED" ]; then
    say "instance is STOPPED — starting it"
    o compute instance action --instance-id "$instance_id" --action START >/dev/null
  fi
  while [ "$state" != "RUNNING" ]; do
    say "waiting for instance to reach RUNNING (currently ${state:-unknown})"
    sleep 10
    state="$(o compute instance get --instance-id "$instance_id" 2>/dev/null \
               | jq -r '.data."lifecycle-state"' || true)"
  done
else
  # --- Resolve the image ------------------------------------------------------
  if [ -z "${OCI_IMAGE_ID:-}" ]; then
    say "finding newest $OCI_OS $OCI_OS_VERSION image for $OCI_SHAPE"
    OCI_IMAGE_ID="$(o compute image list \
        --compartment-id "$OCI_COMPARTMENT_ID" \
        --operating-system "$OCI_OS" \
        --operating-system-version "$OCI_OS_VERSION" \
        --shape "$OCI_SHAPE" \
        --sort-by TIMECREATED --sort-order DESC | first_id)"
    [ -n "$OCI_IMAGE_ID" ] || die "no image found for $OCI_OS $OCI_OS_VERSION on $OCI_SHAPE"
  fi

  # --- Availability domains ---------------------------------------------------
  # Read into an array without mapfile — macOS still ships bash 3.2.
  ADS=()
  while IFS= read -r ad_name; do
    [ -n "$ad_name" ] && ADS+=( "$ad_name" )
  done < <(o iam availability-domain list --compartment-id "$OCI_COMPARTMENT_ID" \
             | jq -r '.data[].name')
  [ "${#ADS[@]}" -gt 0 ] || die "no availability domains returned — check the profile's region"
  say "will try ${#ADS[@]} availability domain(s): ${ADS[*]}"

  launch_args=(
    --compartment-id "$OCI_COMPARTMENT_ID"
    --display-name "$INSTANCE_NAME"
    --shape "$OCI_SHAPE"
    --image-id "$OCI_IMAGE_ID"
    --subnet-id "$SUBNET_ID"
    --assign-public-ip true
    --boot-volume-size-in-gbs "${OCI_BOOT_VOLUME_GB:-50}"
    --ssh-authorized-keys-file "$SSH_PUBLIC_KEY_FILE"
    --user-data-file "$HERE/cloud-init.yaml"
  )
  # Fixed shapes (e.g. VM.Standard.E2.1.Micro) reject --shape-config.
  case "$OCI_SHAPE" in
    *.Flex) launch_args+=( --shape-config "$(jq -nc \
              --argjson o "$OCI_OCPUS" --argjson m "$OCI_MEMORY_GB" \
              '{ocpus:$o,memoryInGBs:$m}')" ) ;;
  esac

  # --wait-for-state writes progress chatter to stderr, so keep the streams apart:
  # stdout must stay pure JSON for jq, stderr is what we pattern-match on failure.
  err_file="$(mktemp)"
  trap 'rm -f "$err_file"' EXIT

  instance_id=""
  for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    for ad in "${ADS[@]}"; do
      say "attempt $attempt/$MAX_ATTEMPTS in $ad"
      if out="$(o compute instance launch --availability-domain "$ad" \
                  "${launch_args[@]}" --wait-for-state RUNNING 2>"$err_file")"; then
        instance_id="$(jq -r '.data.id' <<<"$out")"
        c_grn "launched in $ad"
        break 2
      fi
      err="$(cat "$err_file")"

      case "$err" in
        *"Out of host capacity"*|*"OutOfHostCapacity"*|*"Out of capacity for shape"*)
          c_ylw "  no capacity in $ad" ;;
        *"LimitExceeded"*|*"QuotaExceeded"*|*"exceed"*"limit"*)
          c_red "$err"
          die "tenancy limit hit, not a capacity blip.
  The Always Free ARM allowance is 4 OCPUs / 24 GB TOTAL. If you already have A1
  instances in this tenancy, delete them or lower OCI_OCPUS/OCI_MEMORY_GB in oci.env." ;;
        *"NotAuthorizedOrNotFound"*)
          c_red "$err"
          die "auth or OCID problem — check OCI_COMPARTMENT_ID and the '$OCI_PROFILE' profile" ;;
        *"TooManyRequests"*|*"429"*)
          c_ylw "  rate limited, backing off" ; sleep 30 ;;
        *)
          c_red "$err"
          die "unexpected launch failure (see above)" ;;
      esac
    done
    sleep "$RETRY_SLEEP"
  done

  [ -n "$instance_id" ] || die "still no capacity after $MAX_ATTEMPTS rounds.
  Try a smaller shape (OCI_OCPUS=1, OCI_MEMORY_GB=6) — small A1 shapes place far more
  easily than a full 4/24 box. Re-running this script later also works; it just waits."
fi
save_state INSTANCE_ID "$instance_id"

# --- Public IP ---------------------------------------------------------------
public_ip="$(o compute instance list-vnics --instance-id "$instance_id" \
               | jq -r '.data[0]."public-ip" // empty')"
[ -n "$public_ip" ] || die "instance is running but has no public IP"
save_state PUBLIC_IP "$public_ip"

c_grn "instance $INSTANCE_NAME is up at $public_ip"

# --- Wait for SSH, then for cloud-init to finish -----------------------------
# SSH answers minutes before runcmd completes (package upgrade, Caddy install,
# the chown of /srv/daimon), and deploying in that window fails — so readiness
# is cloud-init completion, not the first successful ssh probe.
say "waiting for SSH (instance is booting)"
for _ in $(seq 1 60); do
  if ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes \
         -i "$SSH_PRIVATE_KEY_FILE" "$SSH_USER@$public_ip" true 2>/dev/null; then
    say "SSH is up — waiting for cloud-init to finish (first boot installs packages)"
    # exit 2 = finished with recoverable errors on newer cloud-init: still usable.
    if ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes \
           -i "$SSH_PRIVATE_KEY_FILE" "$SSH_USER@$public_ip" \
           'cloud-init status --wait >/dev/null 2>&1 || [ $? -eq 2 ]'; then
      c_grn "bootstrap finished:  ssh -i $SSH_PRIVATE_KEY_FILE $SSH_USER@$public_ip"
    else
      c_ylw "cloud-init reported errors — inspect with:
  ssh -i $SSH_PRIVATE_KEY_FILE $SSH_USER@$public_ip cloud-init status --long"
    fi
    exit 0
  fi
  sleep 10
done
c_ylw "SSH not answering yet. The instance is running; give it a few more minutes, then:
  ssh -i $SSH_PRIVATE_KEY_FILE $SSH_USER@$public_ip 'cloud-init status --wait'"
