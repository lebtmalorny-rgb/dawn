# Kolla Mistral Watcher Masakari TLS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Mistral, Watcher, Masakari, HTTPS/TLS and Kolla build tooling on the test Kolla-Ansible OpenStack environment.

**Architecture:** All operational changes run from the existing Ansible host `192.168.10.15` using `/root/venvs/kolla-epoxy`. Configuration edits are backed up first and applied through Kolla-Ansible, not through direct service database edits.

**Tech Stack:** Rocky Linux, Kolla-Ansible `20.4.1.dev5`, Docker/Kolla `2025.1-rocky-9`, OpenStack Epoxy, SSH, OpenSSL, Kolla certificates, Kolla `globals.yml`.

---

## Execution result

Completed on 2026-06-19 against test inventory `/etc/kolla/all-in-one`.

Changed remote configuration/artifacts:

- Backup created on the Ansible host: `/root/dawn-kolla-backup-20260619T173048Z`.
- Enabled `enable_mistral`, `enable_watcher`, `enable_masakari`, `enable_redis`, `kolla_enable_tls_internal`, `kolla_enable_tls_external`, `kolla_copy_ca_into_containers`, `openstack_cacert` and `kolla_admin_openrc_cacert` in `/etc/kolla/globals.yml`.
- Left `enable_masakari_instancemonitor` and `enable_masakari_hostmonitor` disabled for the all-in-one lab to avoid enabling HA cluster/Pacemaker/Corosync on a single-node test cloud.
- Generated Kolla certificates with `kolla-ansible certificates -i /etc/kolla/all-in-one`.
- Installed the Kolla CA into the Ansible and OpenStack host trust stores.
- Installed `kolla==20.*` and Python package `podman` into `/root/venvs/kolla-epoxy`.
- Created `/etc/kolla/kolla-build.conf` for Podman-based Kolla image work.

Verification evidence:

- `kolla-ansible prechecks -i /etc/kolla/all-in-one` completed with `failed=0`.
- `kolla-ansible pull -i /etc/kolla/all-in-one` completed with `failed=0`.
- `kolla-ansible reconfigure -i /etc/kolla/all-in-one` completed with `failed=0`.
- `kolla-ansible post-deploy -i /etc/kolla/all-in-one` regenerated HTTPS openrc/clouds.yaml.
- `kolla-ansible check -i /etc/kolla/all-in-one` completed with `ok=51 changed=0 failed=0`.
- `mistral_*`, `watcher_*`, `masakari_api`, `masakari_engine`, `redis` and `redis_sentinel` containers were observed running.
- Keystone service catalog contains `mistral workflowv2`, `watcher infra-optim` and `masakari instance-ha`.
- Mistral endpoint: `https://192.168.10.250:8989/v2`.
- Watcher endpoint: `https://192.168.10.250:9322`.
- Masakari endpoint: `https://192.168.10.250:15868`.
- Live Keystone TLS check reports TLSv1.3 and `Verification: OK` with the Kolla CA.
- `kolla-build --config-file /etc/kolla/kolla-build.conf --template-only --profile aux` generated Dockerfiles successfully.
- Horizon/Mistral dashboard TLS was fixed with `/etc/kolla/config/horizon/_9999-custom-settings.py`, which sets `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` from `OPENSTACK_SSL_CACERT`.
- `mistralclient.workbooks.list()` from the Horizon container with a real admin token returned `workbooks_count=0` instead of `SSLCertVerificationError`.
- `kolla-ansible check -i /etc/kolla/all-in-one --tags horizon` completed with `failed=0`.

Known residual warnings/gaps:

- `/etc/kolla/globals.yml` already contains duplicate `enable_prometheus`, `enable_grafana` and `enable_grafana_external` keys. Ansible warns and uses the last value; this did not block deployment.
- TLS is lab TLS with Kolla CA, not production corporate PKI or mTLS evidence.
- `/root/openrc` and `/root/openrc.sh` still reference an old unreachable endpoint and should not be used as evidence.
- Full image build/push was not run; only Kolla build tooling and template generation were verified.

---

### Task 1: Discover Active Inventory And Backup

**Files:**
- Remote read: `/etc/kolla/globals.yml`
- Remote read: `/etc/kolla/passwords.yml` only for existence/permissions, not content
- Remote read: `/root/all-in-one`
- Remote read: `/root/multinode`
- Remote create: `/root/dawn-kolla-backup-<timestamp>/`

- [ ] **Step 1: Identify inventory and config**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   echo __INVENTORIES__;
   for f in /root/all-in-one /root/multinode /etc/kolla/all-in-one; do [ -f "$f" ] && echo "$f"; done;
   echo __GLOBALS_SAFE__;
   grep -E "^(kolla_base_distro|openstack_release|network_interface|kolla_internal_vip_address|kolla_external_vip_address|enable_horizon|enable_heat|enable_mistral|enable_watcher|enable_masakari|kolla_enable_tls_|kolla_copy_ca_into_containers)" /etc/kolla/globals.yml 2>/dev/null || true'
```

Expected: prints existing inventory files and safe Kolla config keys without passwords.

- [ ] **Step 2: Create backup**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   ts=$(date -u +%Y%m%dT%H%M%SZ);
   b=/root/dawn-kolla-backup-$ts;
   mkdir -p "$b";
   cp -a /etc/kolla/globals.yml "$b/globals.yml";
   cp -a /etc/kolla/passwords.yml "$b/passwords.yml";
   [ -f /root/all-in-one ] && cp -a /root/all-in-one "$b/all-in-one";
   [ -f /root/multinode ] && cp -a /root/multinode "$b/multinode";
   chmod 700 "$b";
   echo "$b"'
```

Expected: prints backup directory path. Do not copy backup contents locally.

### Task 2: Verify/Install Build Tooling

**Files:**
- Remote inspect: `/root/venvs/kolla-epoxy/bin/`
- Remote possible install into: `/root/venvs/kolla-epoxy`

- [ ] **Step 1: Check Kolla commands**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   /root/venvs/kolla-epoxy/bin/kolla-ansible --version;
   if [ -x /root/venvs/kolla-epoxy/bin/kolla-build ]; then /root/venvs/kolla-epoxy/bin/kolla-build --version; else echo KOLLA_BUILD_MISSING; fi;
   /root/venvs/kolla-epoxy/bin/python -m pip show kolla kolla-ansible || true'
```

Expected: Kolla-Ansible version prints; if `KOLLA_BUILD_MISSING`, install Kolla package.

- [ ] **Step 2: Install Kolla build package if missing**

Run only if missing:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   /root/venvs/kolla-epoxy/bin/python -m pip install "kolla==20.*";
   /root/venvs/kolla-epoxy/bin/kolla-build --version'
```

Expected: `kolla-build` version prints. If pip cannot reach package index, stop and document blocker.

### Task 3: Configure TLS Certificates

**Files:**
- Remote inspect/create: `/etc/kolla/certificates/`
- Remote modify: `/etc/kolla/globals.yml`

- [ ] **Step 1: Check existing certificates**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   ls -la /etc/kolla/certificates 2>/dev/null || true;
   find /etc/kolla/certificates -maxdepth 2 -type f 2>/dev/null | sort || true'
```

Expected: certificate files listed or directory absent.

- [ ] **Step 2: Generate test-only certificates if absent**

Run only if no usable VIP certificate exists:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   mkdir -p /etc/kolla/certificates/private;
   chmod 700 /etc/kolla/certificates/private;
   cat > /tmp/dawn-kolla-openssl.cnf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = 192.168.10.250

[v3_req]
subjectAltName = @alt_names

[alt_names]
IP.1 = 192.168.10.250
DNS.1 = openstack-aio
DNS.2 = ansible.example.local
EOF
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout /etc/kolla/certificates/private/haproxy.key \
     -out /etc/kolla/certificates/haproxy.crt \
     -config /tmp/dawn-kolla-openssl.cnf;
   cat /etc/kolla/certificates/haproxy.crt /etc/kolla/certificates/private/haproxy.key > /etc/kolla/certificates/haproxy.pem;
   cp /etc/kolla/certificates/haproxy.crt /etc/kolla/certificates/ca.crt;
   chmod 600 /etc/kolla/certificates/private/haproxy.key /etc/kolla/certificates/haproxy.pem;
   rm -f /tmp/dawn-kolla-openssl.cnf;
   openssl x509 -in /etc/kolla/certificates/haproxy.crt -noout -subject -issuer -dates'
```

Expected: subject/issuer/dates print. Private key content is not printed.

### Task 4: Enable Services And TLS In globals.yml

**Files:**
- Remote modify: `/etc/kolla/globals.yml`

- [ ] **Step 1: Apply minimal config patch via Python YAML-preserving line editor**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   python3 - <<PY
from pathlib import Path
p = Path("/etc/kolla/globals.yml")
text = p.read_text()
settings = {
    "enable_mistral": "\"yes\"",
    "enable_watcher": "\"yes\"",
    "enable_masakari": "\"yes\"",
    "kolla_enable_tls_external": "\"yes\"",
    "kolla_enable_tls_internal": "\"yes\"",
    "kolla_copy_ca_into_containers": "\"yes\"",
}
lines = text.splitlines()
for key, value in settings.items():
    replacement = f"{key}: {value}"
    found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}:") or stripped.startswith(f"#{key}:"):
            lines[i] = replacement
            found = True
            break
    if not found:
        lines.append(replacement)
p.write_text("\\n".join(lines) + "\\n")
PY
   grep -E "^(enable_mistral|enable_watcher|enable_masakari|kolla_enable_tls_external|kolla_enable_tls_internal|kolla_copy_ca_into_containers):" /etc/kolla/globals.yml'
```

Expected: all six keys print with `"yes"`.

### Task 5: Kolla Precheck And Deploy/Reconfigure

**Files:**
- Remote use: selected inventory, likely `/root/all-in-one`

- [ ] **Step 1: Run prechecks**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   inv=/root/all-in-one;
   [ -f /root/multinode ] && inv=/root/multinode;
   /root/venvs/kolla-epoxy/bin/kolla-ansible -i "$inv" prechecks'
```

Expected: prechecks complete without failed tasks. If failure occurs, stop and inspect.

- [ ] **Step 2: Apply Kolla reconfigure**

Run only after precheck succeeds:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   inv=/root/all-in-one;
   [ -f /root/multinode ] && inv=/root/multinode;
   /root/venvs/kolla-epoxy/bin/kolla-ansible -i "$inv" reconfigure'
```

Expected: reconfigure completes. If it reports missing images or service-specific failures, inspect before retry.

### Task 6: Verify Services And TLS

**Files:**
- Remote read-only OpenStack CLI
- Remote read-only Docker state
- Local docs update after results

- [ ] **Step 1: Verify containers and catalog**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   echo __CONTAINERS__;
   ssh -o BatchMode=no -o StrictHostKeyChecking=no root@192.168.10.14 "docker ps --format \"{{.Names}} {{.Image}} {{.Status}}\" | egrep \"mistral|watcher|masakari|haproxy|horizon|keystone\" || true";
   echo __CATALOG__;
   set +x; source /etc/kolla/admin-openrc.sh >/dev/null 2>&1; set -x;
   /root/venvs/kolla-epoxy/bin/openstack service list -f value -c Name -c Type | sort'
```

Expected: Mistral, Watcher and Masakari containers/catalog entries appear, or precise blocker is captured.

- [ ] **Step 2: Verify HTTPS**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   curl -k -sS -m 10 -I https://192.168.10.250/ | sed -n "1,20p";
   curl -k -sS -m 10 https://192.168.10.250:5000/v3 | sed -n "1,20p";
   openssl s_client -connect 192.168.10.250:443 -servername 192.168.10.250 </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates'
```

Expected: HTTPS responds and certificate details print.

### Task 7: Update Local E00 Docs

**Files:**
- Modify: `cloud-ui-codex-md/docs/generated/current-state.md`
- Modify: `cloud-ui-codex-md/docs/generated/integration-register.md`
- Modify: `cloud-ui-codex-md/docs/generated/api-register.md`
- Modify: `cloud-ui-codex-md/docs/generated/tls-matrix.md`
- Modify: `cloud-ui-codex-md/docs/execplans/E00-discovery-baseline.md`

- [ ] **Step 1: Record sanitized outcomes**

Update docs with:

- Kolla build tooling status.
- Service catalog outcome.
- TLS outcome.
- Any blockers and rollback backup path.

- [ ] **Step 2: Verify no secrets**

Run:

```bash
rg -n "OS_PASSWORD|password:|passwd|BEGIN [A-Z ]*PRIVATE KEY|(?i)(password\\s*=|token\\s*=|secret\\s*=|credential\\s*=)" cloud-ui-codex-md/docs/generated cloud-ui-codex-md/docs/adr cloud-ui-codex-md/docs/execplans
```

Expected: no matches.

## Rollback

Use backup path from Task 1:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.15 \
  'set -e;
   backup=/root/dawn-kolla-backup-YYYYMMDDTHHMMSSZ;
   cp -a "$backup/globals.yml" /etc/kolla/globals.yml;
   inv=/root/all-in-one;
   [ -f /root/multinode ] && inv=/root/multinode;
   /root/venvs/kolla-epoxy/bin/kolla-ansible -i "$inv" reconfigure'
```

Replace `backup` with actual printed backup path.
