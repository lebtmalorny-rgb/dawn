# E08 Vault/SecMan lab runbook

- Stage: E08
- Scope: permanent lab Vault on Ansible host `192.168.10.15`
- Rule: commands must not print root token, unseal keys, client token, private keys or real secret values.

## Precheck

Run on Ansible host:

```bash
hostname -f
ip addr
timedatectl status
swapon --show
ss -ltnp | grep ':8200\|:8201' || true
```

Expected evidence: host identity, time sync, swap state, and no conflicting Vault listener. Save only sanitized command results.

## Target layout

- user/group: `vault:vault`
- config: `/etc/vault.d/vault.hcl`, owned by `root:vault`, mode `0640`
- data: `/opt/vault/data`, owned by `vault:vault`, mode `0700`
- TLS certificate: `/etc/vault.d/tls/vault.crt`
- TLS private key: `/etc/vault.d/tls/vault.key`, mode `0600`, never copied into Git or evidence
- audit log: `/var/log/vault/audit.log`, writable by Vault and readable only by approved operators
- API address: `https://192.168.10.15:8200`
- cluster address: `https://192.168.10.15:8201`

Target listener binds to `192.168.10.15:8200` and `192.168.10.15:8201` with `tls_min_version = "tls12"`. If temporary wildcard bind is required, record firewall restriction, owner and expiry as a lab gap.

## TLS

Preferred path: use corporate/test PKI with IP SAN `192.168.10.15` and optional DNS SAN `vault.lab.local`. Evidence must include the CA type, CA fingerprint, certificate SANs, expiration and TLS scan result, not certificate private material.

Fallback path: create a separate lab CA outside Git. Record only the lab CA fingerprint and expiration. Lab CA evidence is acceptable for E08 integration smoke, but it is not corporate PKI compliance evidence for production.

## Smoke without secret disclosure

Run only with a non-root lab token or auth role scoped by `docs/generated/e08-vault-policy.hcl`:

```bash
vault status
vault secrets list
vault audit list
vault kv get -field=value kv/cloud-ui/local/session >/dev/null
vault kv get kv/other-service/local/test
```

Expected outcomes:

- `vault status` reports initialized and unsealed.
- `vault secrets list` shows KV v2 mounted at `kv/`.
- `vault audit list` shows the file audit device.
- The allowed synthetic portal path read succeeds without printing the value.
- The unrelated path read fails for the portal policy token.
- No output contains real secret values, root token, unseal keys, client token or private key material.

## Rollback

```bash
sudo systemctl stop vault
sudo systemctl disable vault
```

Preserve `/opt/vault/data` unless destructive cleanup is explicitly approved. If rollback includes token revocation, trust-store cleanup or firewall changes, record the command intent and sanitized result without secret material.
