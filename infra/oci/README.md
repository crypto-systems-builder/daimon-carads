# Second OCI tenancy → another Always Free server

Everything Oracle makes you do by hand is in **Part 1**. Everything after that is
scripted. Total time is roughly 20 minutes of clicking plus however long it takes
Always Free ARM capacity to appear in your region.

```
infra/oci/
  oci.env.example   → copy to oci.env, fill in
  01-network.sh     VCN, internet gateway, routes, security list, public subnet
  02-instance.sh    launch the A1.Flex box, retrying until capacity appears
  cloud-init.yaml   first-boot host setup (firewall, swap, Caddy, fail2ban)
  03-deploy-site.sh rsync daimon-carads to the box + write the Caddy config
  99-destroy.sh     tear the whole stack back down
```

---

## Part 1 — the manual bits

### 1. Sign up

<https://signup.cloud.oracle.com/>

Three decisions that are hard or impossible to undo:

- **Home region is permanent.** You cannot move a tenancy later. Pick a region that
  is close to you *and* not saturated — Always Free ARM capacity is far easier to get
  in a quieter region than in Frankfurt or Amsterdam. If this box is only serving the
  static site, latency barely matters and a quieter region is the better trade.
- **Use an email that is not already on an Oracle tenancy.** Reusing the address on
  the first account is the usual cause of a signup that silently stalls.
- **Stay on Always Free.** Oracle asks for a card and puts a small verification hold
  on it. Do not click "Upgrade to Pay As You Go" unless you actually want billing —
  the upgrade is one-way in practice.

Expect the account to take anywhere from a few minutes to a few hours to provision.

### 2. Create an API key

Console → profile icon (top right) → **My Profile** → **API Keys** → **Add API Key**
→ *Generate API key pair* → **Download private key** → Add.

Oracle then shows a config preview. Keep that tab open — you need those four values.

```bash
mkdir -p ~/.oci && chmod 700 ~/.oci
mv ~/Downloads/<downloaded-key>.pem ~/.oci/daimon2.pem
chmod 600 ~/.oci/daimon2.pem
```

### 3. Add a profile for the *new* tenancy

One profile per account — this is how the second tenancy coexists with the first
instead of overwriting it. Append to `~/.oci/config`:

```ini
[DAIMON2]
user=ocid1.user.oc1..xxxxx
fingerprint=aa:bb:cc:...
tenancy=ocid1.tenancy.oc1..xxxxx
region=eu-amsterdam-1
key_file=~/.oci/daimon2.pem
```

Paste `user`, `fingerprint`, `tenancy` and `region` straight from the config preview
in step 2; set `key_file` to the path from step 2.

### 4. Install the CLI and confirm the profile works

```bash
# macOS
brew install oci-cli jq
# Linux
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"

oci --profile DAIMON2 iam region-subscription list   # should list your home region
oci --profile DAIMON2 iam compartment list --all     # note the compartment OCID
```

If that last command errors, the profile is wrong — fix it before going further.
For a personal account the **tenancy OCID is also the root compartment OCID**, and
using it is fine.

### 5. SSH key for the box

```bash
ssh-keygen -t ed25519 -f ~/.ssh/oci_daimon2 -C daimon2
```

---

## Part 2 — the scripted bits

```bash
cd infra/oci
cp oci.env.example oci.env
$EDITOR oci.env          # OCI_PROFILE, OCI_COMPARTMENT_ID, SITE_DOMAIN

./01-network.sh          # ~30s
./02-instance.sh         # minutes, or hours if capacity is tight — just leave it
./03-deploy-site.sh      # ~1 min depending on how big press/ has got
```

Each script is safe to rerun. Created OCIDs are cached in `.state.<profile>.env`
(gitignored), so a rerun reuses what already exists instead of duplicating it.

### About "Out of host capacity"

This is the normal Always Free ARM experience, not a misconfiguration. Oracle
releases A1 capacity as other people give it back, so `02-instance.sh` retries every
60 seconds across every availability domain rather than failing. Leave it running.

If a full 4 OCPU / 24 GB box never lands, ask for less — small shapes place much more
easily:

```bash
# in oci.env
OCI_OCPUS=1
OCI_MEMORY_GB=6
```

You can also raise the patience: `MAX_ATTEMPTS=500 ./02-instance.sh`.

### What Always Free actually gives you

Per tenancy, which is exactly why a second account is worth having:

| Resource | Allowance |
|---|---|
| Ampere A1 (ARM) | 4 OCPUs + 24 GB RAM **total**, split however you like |
| AMD micro VMs | 2 × VM.Standard.E2.1.Micro (1/8 OCPU, 1 GB) |
| Block storage | 200 GB total, max 2 volume groups |
| Outbound transfer | 10 TB/month |
| Public IPs | 2 ephemeral, 1 reserved |

The 4/24 ARM allowance is the whole point — one 4/24 box, or four 1/6 boxes.

---

## Gotchas already handled in these scripts

- **Two firewalls, not one.** Opening a port in the VCN security list is only half of
  it; Oracle's Ubuntu images also ship iptables rules that reject everything past
  port 22. `cloud-init.yaml` opens 80/443 host-side and persists the rules. This is
  the number one reason a fresh OCI box appears to ignore HTTP.
- **No swap by default.** `cloud-init.yaml` adds a 4 GB swapfile.
- **TLS.** Caddy provisions and renews certificates automatically — but only once
  `SITE_DOMAIN`'s A record points at the instance IP. Point DNS first, then run
  `03-deploy-site.sh`. With `SITE_WWW=true`, `www.$SITE_DOMAIN` needs its own
  A/CNAME record too.
- **Deploys wait for first boot.** Both `02-instance.sh` and `03-deploy-site.sh`
  gate on `cloud-init status --wait`, since SSH answers minutes before the
  first-boot package installs finish.
- **Idle reclamation applies to Pay As You Go tenancies, not Always Free ones.**
  Always Free A1 instances are not reclaimed for being idle; do not bother with
  fake-load cron jobs.

## Tearing it down

```bash
./99-destroy.sh          # asks you to type the stack name to confirm
```

## Adding a third tenancy later

Add another `[PROFILE]` block to `~/.oci/config`, then a second env file — the state
file is keyed on the profile name, so tenancies never collide:

```bash
cp oci.env oci-third.env    # edit OCI_PROFILE / OCI_COMPARTMENT_ID / STACK_NAME
OCI_ENV_FILE=$PWD/oci-third.env ./01-network.sh
```
