# E07 Fluentd/OpenSearch lab evidence path

- Stage: E07
- Date: 2026-06-22
- Environment: all-in-one OpenStack Epoxy 2025.1 lab, not production.
- Scope: manual evidence/runbook only. Portal runtime and local tests do not deploy Fluentd or OpenSearch.

## Observed pre-state

Observed through the test stand path via the Ansible host:

| Item | Observed value |
|---|---|
| Ansible host | `192.168.10.15` |
| All-in-one OpenStack host | `192.168.10.14` |
| Kolla virtualenv | `/root/venvs/kolla-epoxy` |
| Kolla `fluentd` container | present/running on all-in-one |
| `/etc/kolla/globals.yml` `enable_central_logging` | `"no"` |
| `/etc/kolla/globals.yml` `enable_opensearch` | `"no"` |
| `/etc/kolla/globals.yml` `enable_opensearch_dashboards` | `"no"` |

This means E07 can document a Fluentd/OpenSearch lab path, but it cannot claim OpenSearch evidence until an operator approves and executes the manual Kolla change.

## E07 code contract

E07 implements:

- `LocalTestAuditSink` for deterministic success/failure/recovery tests;
- `FluentdHttpAuditSink.build_payload()` contract with `tag`, `time` and sanitized `record`;
- durable audit outbox with retry, dead-letter and delivery state;
- heartbeat state with queue depth and oldest pending age.

E07 does not commit a SIEM credential, Fluentd endpoint, client certificate, OpenSearch URL or production retention policy.

## Manual lab enablement

Run only on the test all-in-one after explicit approval from the environment owner.

1. Back up Kolla globals:

   ```bash
   cp -a /etc/kolla/globals.yml /etc/kolla/globals.yml.e07-audit-backup
   ```

2. Edit `/etc/kolla/globals.yml` for the lab:

   ```yaml
   enable_opensearch: "yes"
   enable_opensearch_dashboards: "yes"
   enable_central_logging: "yes"
   ```

3. Activate the Kolla virtualenv:

   ```bash
   source /root/venvs/kolla-epoxy/bin/activate
   ```

4. Reconfigure the logging stack with the lab inventory selected by the platform owner:

   ```bash
   kolla-ansible -i <lab-inventory> reconfigure --tags opensearch,opensearch-dashboards,fluentd
   ```

5. Verify containers on the all-in-one:

   ```bash
   docker ps --format '{{.Names}} {{.Status}}' | egrep 'fluentd|opensearch'
   ```

6. Confirm the Fluentd HTTP input endpoint and tag before sending any synthetic event. Do not send production data. The synthetic payload must use the `FluentdHttpAuditSink` shape from `audit-sample-events.md`.

7. Query OpenSearch/OpenSearch Dashboards for the synthetic `event_id` and verify:

   - event appears once or as an idempotent replay;
   - `metadata` contains only sanitized values;
   - `request_id` and `correlation_id` are indexed;
   - no token, cookie, password, private key, raw request body or production endpoint is present.

## Rollback

1. Restore the previous Kolla globals:

   ```bash
   cp -a /etc/kolla/globals.yml.e07-audit-backup /etc/kolla/globals.yml
   ```

2. Re-run the owner-approved Kolla reconfigure for the same lab inventory:

   ```bash
   source /root/venvs/kolla-epoxy/bin/activate
   kolla-ansible -i <lab-inventory> reconfigure --tags opensearch,opensearch-dashboards,fluentd
   ```

3. Verify the expected container state and retain only the sanitized smoke summary. Do not commit raw OpenSearch documents, logs or credentials.

## Evidence limits

- Current E07 evidence is local/contract evidence, not production SIEM evidence.
- ДКБ-47 protected-channel compliance still requires PKI/mTLS/auth configuration, negative certificate tests and SIEM owner review.
- ДКБ-48 still requires external FIM/auditd/IaC and missing-flow alerting because root on a controller can disable local logging.
- ДКБ-50 still requires external OpenStack, host, storage, IdP and monitoring sources listed in `audit-source-map.md`.
