# E12 — Production gap analysis и решение о pilot

## Пользовательский результат

Архитектурный комитет и безопасность получают честный пакет: что доказано порталом, что доказано OpenStack/Kolla, какие внешние контуры обязательны, какие исключения ДКБ нужны и какие blockers остаются до production pilot.

## Входные критерии

- E11 принят.
- Доступны evidence owners IAM/PKI/SIEM/Vault(SecMan)/PAM/backup/storage/network.
- Определен authority, который принимает DKB compliance/gaps.

## Прочитать

- `docs/10_SECURITY_DKB.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- `docs/14_DEFINITION_OF_DONE.md`;
- все security/deployment/load/acceptance reports.

## Единицы работы

### E12.1. Evidence audit

Проверить каждую из 73 строк: claim, artifact, owner, date, environment, limitation. Удалить unsupported claims.

### E12.2. External control matrix

IAM/IdP, PKI, SIEM, Vault (SecMan), PAM/auditd, backup, storage, network, vendor updates. Для каждого: interface, owner, evidence, SLA, gap.

### E12.3. High-risk gaps

Отдельно:

- service account exception ДКБ-07;
- mTLS scope ДКБ-22.02;
- anti-disable/full audit ДКБ-48/50;
- all secrets rotation ДКБ-55/56;
- SELinux/AppArmor ДКБ-65;
- interpreter/shell conflict ДКБ-69;
- hypervisor filesystem ДКБ-72;
- incomplete container requirements ДКБ-76.

### E12.4. Waiver/compensating controls

Для каждого waiver: exact conflict, scope, risk, compensating controls, owner, expiry, review cadence, exit plan.

### E12.5. Production readiness decision

Категория каждого gap:

- blocker;
- accepted risk;
- external prerequisite;
- post-pilot improvement;
- requirement clarification.

### E12.6. Pilot plan

Limited scope, users/projects/workflows, monitoring, change freeze, rollback triggers, incident contacts, success/stop criteria.

## Acceptance

- 73/73 requirements reviewed;
- every claim has reproducible evidence or explicit no-evidence;
- high-risk gaps have owner;
- DKB-69/72 conflicts not hidden;
- production blockers separated from improvements;
- pilot scope/rollback/stop criteria defined;
- final decision made by authorized humans, not Codex;
- docs do not imply certification.

## Затронутые ДКБ

Все 73 требования. Этот этап не «реализует» внешние controls, а проверяет и оформляет их доказательства.

## Не делать

- автоматически переводить partial в compliant;
- считать upstream documentation deployment evidence;
- принимать waiver без owner/expiry;
- разрешать Codex подписывать compliance decision;
- запускать pilot до human approval.

## Итоговый запрос Codex

> Выполни E12 как forensic evidence review. Для каждой строки ДКБ различи код, конфигурацию, test и внешний control. Удали неподтвержденные claims. Финальное решение оставь уполномоченным владельцам.
