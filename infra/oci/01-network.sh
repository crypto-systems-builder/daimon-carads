#!/usr/bin/env bash
# Create the VCN, internet gateway, routing and firewall rules for the new tenancy.
# Safe to rerun: everything is looked up by display name before it is created.

. "$(dirname "$0")/lib.sh"
load_env

VCN_NAME="$STACK_NAME-vcn"
SUBNET_NAME="$STACK_NAME-public-subnet"

say "Using profile '$OCI_PROFILE' in compartment ${OCI_COMPARTMENT_ID: -8}"

# --- VCN ---------------------------------------------------------------------
vcn_id="$(o network vcn list --compartment-id "$OCI_COMPARTMENT_ID" \
            --display-name "$VCN_NAME" --lifecycle-state AVAILABLE | first_id)"
if [ -z "$vcn_id" ]; then
  say "creating VCN $VCN_NAME"
  vcn_id="$(o network vcn create \
      --compartment-id "$OCI_COMPARTMENT_ID" \
      --cidr-blocks '["10.0.0.0/16"]' \
      --display-name "$VCN_NAME" \
      --dns-label "${STACK_NAME//[^a-z0-9]/}" \
      --wait-for-state AVAILABLE | jq -r '.data.id')"
else
  say "VCN $VCN_NAME already exists"
fi
save_state VCN_ID "$vcn_id"

vcn_json="$(o network vcn get --vcn-id "$vcn_id")"
rt_id="$(jq -r '.data."default-route-table-id"'   <<<"$vcn_json")"
sl_id="$(jq -r '.data."default-security-list-id"' <<<"$vcn_json")"

# --- Internet gateway --------------------------------------------------------
ig_id="$(o network internet-gateway list --compartment-id "$OCI_COMPARTMENT_ID" \
           --vcn-id "$vcn_id" --display-name "$STACK_NAME-ig" | first_id)"
if [ -z "$ig_id" ]; then
  say "creating internet gateway"
  ig_id="$(o network internet-gateway create \
      --compartment-id "$OCI_COMPARTMENT_ID" --vcn-id "$vcn_id" \
      --display-name "$STACK_NAME-ig" --is-enabled true \
      --wait-for-state AVAILABLE | jq -r '.data.id')"
fi
save_state IG_ID "$ig_id"

# --- Default route: everything out via the internet gateway ------------------
say "pointing default route at the internet gateway"
o network route-table update --rt-id "$rt_id" --force \
  --route-rules "$(jq -nc --arg ig "$ig_id" \
      '[{destination:"0.0.0.0/0",destinationType:"CIDR_BLOCK",networkEntityId:$ig}]')" >/dev/null

# --- Security list -----------------------------------------------------------
# This is only half the firewall. Oracle's Ubuntu images also ship iptables rules
# that drop everything but 22 — cloud-init.yaml opens 80/443 on the host side.
say "opening 22/80/443 on the security list"
o network security-list update --security-list-id "$sl_id" --force \
  --egress-security-rules '[
    {"destination":"0.0.0.0/0","destinationType":"CIDR_BLOCK","protocol":"all","isStateless":false}
  ]' \
  --ingress-security-rules '[
    {"source":"0.0.0.0/0","sourceType":"CIDR_BLOCK","protocol":"6","isStateless":false,
     "tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
    {"source":"0.0.0.0/0","sourceType":"CIDR_BLOCK","protocol":"6","isStateless":false,
     "tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
    {"source":"0.0.0.0/0","sourceType":"CIDR_BLOCK","protocol":"6","isStateless":false,
     "tcpOptions":{"destinationPortRange":{"min":443,"max":443}}},
    {"source":"0.0.0.0/0","sourceType":"CIDR_BLOCK","protocol":"1","isStateless":false,
     "icmpOptions":{"type":3,"code":4}}
  ]' >/dev/null

# --- Public subnet -----------------------------------------------------------
subnet_id="$(o network subnet list --compartment-id "$OCI_COMPARTMENT_ID" \
               --vcn-id "$vcn_id" --display-name "$SUBNET_NAME" \
               --lifecycle-state AVAILABLE | first_id)"
if [ -z "$subnet_id" ]; then
  say "creating public subnet $SUBNET_NAME"
  subnet_id="$(o network subnet create \
      --compartment-id "$OCI_COMPARTMENT_ID" --vcn-id "$vcn_id" \
      --cidr-block "10.0.1.0/24" --display-name "$SUBNET_NAME" \
      --dns-label public --route-table-id "$rt_id" \
      --security-list-ids "[\"$sl_id\"]" \
      --prohibit-public-ip-on-vnic false \
      --wait-for-state AVAILABLE | jq -r '.data.id')"
else
  say "subnet $SUBNET_NAME already exists"
fi
save_state SUBNET_ID "$subnet_id"

c_grn "network ready — state written to $(basename "$STATE_FILE")"
