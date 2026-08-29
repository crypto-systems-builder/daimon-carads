# Shared helpers. Sourced by the numbered scripts, not run directly.
# shellcheck shell=bash

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
STATE_FILE="$HERE/.state.$(basename "${OCI_PROFILE:-default}").env"

c_red()  { printf '\033[31m%s\033[0m\n' "$*"; }
c_grn()  { printf '\033[32m%s\033[0m\n' "$*"; }
c_ylw()  { printf '\033[33m%s\033[0m\n' "$*"; }
say()    { printf '\033[36m==>\033[0m %s\n' "$*"; }
die()    { c_red "error: $*" >&2; exit 1; }

load_env() {
  # OCI_ENV_FILE lets a second tenancy reuse these scripts with its own settings.
  local env_file="${OCI_ENV_FILE:-$HERE/oci.env}"
  [ -f "$env_file" ] || die "missing $env_file — copy oci.env.example to oci.env and fill it in"
  # shellcheck disable=SC1090
  set -a; . "$env_file"; set +a

  : "${OCI_PROFILE:?set OCI_PROFILE in oci.env}"
  : "${OCI_COMPARTMENT_ID:?set OCI_COMPARTMENT_ID in oci.env}"
  STACK_NAME="${STACK_NAME:-daimon}"

  # Expand ~ / $HOME that survived the .env as literal text.
  SSH_PUBLIC_KEY_FILE="$(eval echo "${SSH_PUBLIC_KEY_FILE:-$HOME/.ssh/oci_daimon2.pub}")"
  SSH_PRIVATE_KEY_FILE="$(eval echo "${SSH_PRIVATE_KEY_FILE:-$HOME/.ssh/oci_daimon2}")"

  command -v oci >/dev/null || die "oci CLI not found — see README.md step 3"
  command -v jq  >/dev/null || die "jq not found — install it (brew install jq / apt install jq)"

  STATE_FILE="$HERE/.state.$OCI_PROFILE.env"
  # shellcheck disable=SC1090
  [ -f "$STATE_FILE" ] && { set -a; . "$STATE_FILE"; set +a; }
  return 0
}

# oci CLI wrapper: always the right profile, always parseable output.
o() { oci --profile "$OCI_PROFILE" "$@"; }

# Record a discovered/created OCID so later scripts (and reruns) can find it again.
save_state() {
  local key="$1" val="$2"
  touch "$STATE_FILE"
  # Rewrite in place rather than appending, so reruns do not stack duplicates.
  grep -v "^${key}=" "$STATE_FILE" > "$STATE_FILE.tmp" 2>/dev/null || true
  printf '%s=%s\n' "$key" "$val" >> "$STATE_FILE.tmp"
  mv "$STATE_FILE.tmp" "$STATE_FILE"
  export "$key=$val"
}

# First OCID out of an `oci ... list` response, empty if nothing matched. Every
# script looks a resource up by display name this way before creating it, which is
# what makes reruns safe.
first_id() { jq -r '.data[0].id // empty'; }
