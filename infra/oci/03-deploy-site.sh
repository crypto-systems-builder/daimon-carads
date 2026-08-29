#!/usr/bin/env bash
# Publish the daimon-carads static site to the instance and (re)write Caddy's config.
# Rerun this after any change to the site — it is a plain rsync, no downtime.

. "$(dirname "$0")/lib.sh"
load_env

[ -n "${PUBLIC_IP:-}" ] || die "no PUBLIC_IP in state — run ./02-instance.sh first"
command -v rsync >/dev/null || die "rsync not found"

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -i "$SSH_PRIVATE_KEY_FILE")
SSH_CMD="ssh -o StrictHostKeyChecking=accept-new -i '$SSH_PRIVATE_KEY_FILE'"
remote="$SSH_USER@$PUBLIC_IP"

# Belt and braces with 02's gate: /srv/daimon is root-owned and Caddy absent
# until cloud-init's runcmd completes, so a deploy before that fails midway.
say "checking the box finished first-boot setup"
ssh "${SSH_OPTS[@]}" "$remote" 'cloud-init status --wait >/dev/null 2>&1 || [ $? -eq 2 ]' \
  || die "cloud-init has not finished (or failed) on $PUBLIC_IP — check:
  ssh -i $SSH_PRIVATE_KEY_FILE $remote cloud-init status --long"

say "syncing site to $remote:/srv/daimon"
rsync -az --delete --human-readable \
  -e "$SSH_CMD" \
  --exclude '.git/' \
  --exclude 'infra/' \
  --exclude '.DS_Store' \
  "$REPO_ROOT/" "$remote:/srv/daimon/"

# --- Caddy config ------------------------------------------------------------
if [ -n "${SITE_DOMAIN:-}" ]; then
  case "$SITE_DOMAIN" in
    *[!A-Za-z0-9.-]*) die "SITE_DOMAIN '$SITE_DOMAIN' contains characters invalid in a hostname" ;;
  esac
  say "configuring Caddy for $SITE_DOMAIN (automatic TLS)"
  caddyfile="$(cat <<EOF
$SITE_DOMAIN {
  root * /srv/daimon
  file_server
  encode gzip zstd

  # Media filenames are not content-hashed, so let browsers revalidate daily —
  # file_server sends ETag/Last-Modified, making that a cheap 304 when unchanged.
  @media path *.mp4 *.png *.jpg *.jpeg *.webp *.woff2
  header @media Cache-Control "public, max-age=86400, must-revalidate"
  @html path *.html /
  header @html Cache-Control "public, max-age=300"

  header {
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
  }
}
EOF
)"
  # www needs its own DNS record, so it is opt-in — without the record, ACME
  # validation for www fails forever in the background and burns rate limits.
  if [ "${SITE_WWW:-false}" = "true" ]; then
    caddyfile="$caddyfile
www.$SITE_DOMAIN {
  redir https://$SITE_DOMAIN{uri} permanent
}"
  fi
else
  c_ylw "SITE_DOMAIN is empty — serving plain HTTP on $PUBLIC_IP (no certificate)"
  caddyfile="$(cat <<'EOF'
:80 {
  root * /srv/daimon
  file_server
  encode gzip zstd
}
EOF
)"
fi

# Validate before touching the live config: a bad file would survive the failed
# reload on disk and brick Caddy at the next restart or reboot.
say "validating and installing the Caddy config"
printf '%s\n' "$caddyfile" | ssh "${SSH_OPTS[@]}" "$remote" '
  set -e
  tmp=$(mktemp)
  cat > "$tmp"
  caddy validate --adapter caddyfile --config "$tmp" >/dev/null
  sudo install -m 0644 "$tmp" /etc/caddy/Caddyfile
  sudo systemctl reload caddy
  rm -f "$tmp"'

if [ -n "${SITE_DOMAIN:-}" ]; then
  c_grn "deployed — https://$SITE_DOMAIN"
  say "if the certificate fails, the A record for $SITE_DOMAIN must point at $PUBLIC_IP first"
  if [ "${SITE_WWW:-false}" = "true" ]; then
    say "SITE_WWW=true also needs an A/CNAME record for www.$SITE_DOMAIN"
  fi
else
  c_grn "deployed — http://$PUBLIC_IP"
fi
