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

if [ -n "${INSTANCE_ID:-}" ]; then
  say "terminating instance (and its boot volume)"
  o compute instance terminate --instance-id "$INSTANCE_ID" \
    --preserve-boot-volume false --force --wait-for-state TERMINATED || true
fi

# The VCN will not delete while a subnet still holds a VNIC, hence the ordering.
if [ -n "${SUBNET_ID:-}" ]; then
  say "deleting subnet"
  o network subnet delete --subnet-id "$SUBNET_ID" --force --wait-for-state TERMINATED || true
fi

if [ -n "${IG_ID:-}" ]; then
  say "deleting internet gateway"
  o network internet-gateway delete --ig-id "$IG_ID" --force --wait-for-state TERMINATED || true
fi

if [ -n "${VCN_ID:-}" ]; then
  say "deleting VCN"
  o network vcn delete --vcn-id "$VCN_ID" --force --wait-for-state TERMINATED || true
fi

rm -f "$STATE_FILE"
c_grn "stack '$STACK_NAME' destroyed"
