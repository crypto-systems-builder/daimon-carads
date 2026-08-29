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

say "syncing site to $remote:/srv/daimon"
rsync -az --delete --human-readable \
  -e "$SSH_CMD" \
  --exclude '.git/' \
  --exclude 'infra/' \
  --exclude '.DS_Store' \
  "$REPO_ROOT/" "$remote:/srv/daimon/"

# --- Caddy config ------------------------------------------------------------
if [ -n "${SITE_DOMAIN:-}" ]; then
  say "configuring Caddy for $SITE_DOMAIN (automatic TLS)"
  caddyfile="$(cat <<EOF
$SITE_DOMAIN, www.$SITE_DOMAIN {
  root * /srv/daimon
  file_server
  encode gzip zstd

  # Long cache for the heavy media, short for the HTML that points at it.
  @media path *.mp4 *.png *.jpg *.jpeg *.webp *.woff2
  header @media Cache-Control "public, max-age=2592000, immutable"
  @html path *.html /
  header @html Cache-Control "public, max-age=300"

  header {
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
  }
}
EOF
)"
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

printf '%s\n' "$caddyfile" | ssh "${SSH_OPTS[@]}" "$remote" \
  'sudo tee /etc/caddy/Caddyfile >/dev/null && sudo systemctl reload caddy'

if [ -n "${SITE_DOMAIN:-}" ]; then
  c_grn "deployed — https://$SITE_DOMAIN"
  say "if the certificate fails, the A record for $SITE_DOMAIN must point at $PUBLIC_IP first"
else
  c_grn "deployed — http://$PUBLIC_IP"
fi
