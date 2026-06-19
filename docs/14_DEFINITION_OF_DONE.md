# Definition of Done и критерии приемки

## Общий DoD изменения

Изменение завершено, когда одновременно выполнено следующее:

- есть воспроизводимый пользовательский или операторский результат;
- scope соответствует текущему этапу;
- реализованы happy path и ключевые отрицательные сценарии;
- backend authorization нельзя обойти прямым request;
- отсутствуют secrets и sensitive payload в Git, browser, logs и audit;
- релевантные unit/component/contract/integration/E2E tests проходят;
- lint и typecheck проходят;
- OpenAPI и документация обновлены;
- migration безопасна для повторного запуска и rollback;
- observability позволяет диагностировать ошибку по correlation ID;
- performance budget не нарушен либо зафиксирован regression/gap;
- DKB traceability обновлена;
- self-review и security review не имеют необработанных critical/high findings;
- создана инструкция отката;
- известные ограничения названы прямо.

## DoD этапа

Этап закрывается только после выполнения всех acceptance criteria в `tasks/E*.md` и сохранения ExecPlan с фактическим outcome.

## Критерий P0

- приложение стартует локально одной документированной командой;
- два custom image;
- mock inventory;
- список ВМ/host;
- группы;
- mock workflow operation;
- тесты;
- no real credentials.

P0 не является DKB compliance evidence.

## Критерий P1

- real test OpenStack read-only;
- federation/test identity;
- server-side session;
- timeout/session limit;
- backend RBAC;
- HTTPS;
- inventory read model;
- partial/stale indication;
- portal audit;
- negative tests;
- documented API.

## Критерий P2

- allowlisted real Mistral workflow в test project;
- operation tracking;
- idempotency;
- cancel/retry semantics;
- target scope/preconditions;
- SIEM test delivery;
- redaction;
- failure recovery;
- security review.

## Критерий P3

- Kolla deployment на HA test environment;
- 12 permanent containers/3 nodes и migration job;
- corporate registry/PKI/Vault(SecMan)/SIEM integration;
- TLS/mTLS matrix;
- network segmentation evidence;
- image SBOM/scan/signature policy;
- SELinux evidence;
- load/failover/rollback reports;
- external audit/PAM/storage/backup evidence;
- approved DKB gaps/waivers;
- эксплуатационные runbooks.

## Недопустимые заявления

Нельзя писать:

- «ДКБ выполнено», если есть только plan/mock;
- «RBAC реализован», если проверена только видимость UI;
- «аудит полный», если покрыты только portal events;
- «Vault integrated», если secret лежит в `.env`;
- «HA», если запущены три контейнера без failover test;
- «hardened image», если выполнен только vulnerability scan;
- «API заблокирован», если он просто не используется frontend;
- «rollback поддерживается», если процедура не запускалась в test environment.

## Приемочный протокол

Для каждого сценария:

- ID и цель;
- версия image/git commit;
- environment;
- preconditions;
- actor/role;
- steps;
- expected result;
- actual result;
- correlation/operation IDs;
- audit evidence;
- screenshots только без secrets;
- pass/fail;
- linked defect;
- reviewer/date.

## Release decision

Release candidate имеет:

- неизменяемые image digests;
- release notes;
- migration plan;
- rollback plan;
- known issues;
- compatibility matrix;
- test summary;
- security summary;
- DKB delta;
- approval owner.
