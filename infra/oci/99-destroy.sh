#!/usr/bin/env bash
# Delete everything the 01/02 scripts created, in dependency order.
# Destructive and not reversible — the instance and its boot volume go with it.

. "$(dirname "$0")/lib.sh"
load_env

c_ylw "About to permanently delete stack '$STACK_NAME' in profile '$OCI_PROFILE':"
printf '  instance : %s\n  subnet   : %s\n  vcn      : %s\n' \
  "${INSTANCE_ID:-none}" "${SUBNET_ID:-none}" "${VCN_ID:-none}"
read -r -p "Type the stack name ($STACK_NAME) to confirm: " confirm
[ "$confirm" = "$STACK_NAME" ] || die "aborted"

# Tolerate only already-gone resources. Any other failure is recorded so the
# state file — the only record of these OCIDs — survives for a rerun instead of
# being wiped while something still exists and bills allowance.
fail=0
del() {
  local out
  if ! out="$("$@" 2>&1)"; then
    case "$out" in
      *NotAuthorizedOrNotFound*|*"not found"*) : ;;
      *) c_red "$out"; fail=1 ;;
    esac
  fi
}

if [ -n "${INSTANCE_ID:-}" ]; then
  say "terminating instance (and its boot volume)"
  del o compute instance terminate --instance-id "$INSTANCE_ID" \
    --preserve-boot-volume false --force --wait-for-state TERMINATED
fi

# The VCN will not delete while a subnet still holds a VNIC, hence the ordering.
if [ -n "${SUBNET_ID:-}" ]; then
  say "deleting subnet"
  del o network subnet delete --subnet-id "$SUBNET_ID" --force --wait-for-state TERMINATED
fi

# OCI refuses (409) to delete an internet gateway while a route rule still
# points at it, so blank the default route table first. Safe to clear: the
# default route table is deleted together with the VCN.
if [ -n "${VCN_ID:-}" ]; then
  say "clearing default route table"
  rt_id="$(o network vcn get --vcn-id "$VCN_ID" 2>/dev/null \
             | jq -r '.data."default-route-table-id" // empty' || true)"
  if [ -n "$rt_id" ]; then
    del o network route-table update --rt-id "$rt_id" --route-rules '[]' --force
  fi
fi

if [ -n "${IG_ID:-}" ]; then
  say "deleting internet gateway"
  del o network internet-gateway delete --ig-id "$IG_ID" --force --wait-for-state TERMINATED
fi

if [ -n "${VCN_ID:-}" ]; then
  say "deleting VCN"
  del o network vcn delete --vcn-id "$VCN_ID" --force --wait-for-state TERMINATED
fi

if [ "$fail" -eq 0 ]; then
  rm -f "$STATE_FILE"
  c_grn "stack '$STACK_NAME' destroyed"
else
  die "some resources were NOT deleted — state file kept; fix the errors above and rerun"
fi
