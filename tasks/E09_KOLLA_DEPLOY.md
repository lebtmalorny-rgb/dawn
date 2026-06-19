# E09 — Kolla Build и Kolla-Ansible deployment

## Пользовательский результат

Два custom image собираются и публикуются в test registry, а Kolla-Ansible custom role развертывает на трех test control/UI nodes 12 постоянных контейнеров и одноразовую миграцию за HAProxy/TLS.

## Входные критерии

- E08 принят.
- Есть отдельный test inventory и registry.
- Rocky/Kolla exact baseline подтвержден.
- Нет production inventory/credentials в workspace.
- Migration/rollback plan принят.

## Прочитать

- `docs/12_DEPLOY_ROCKY_KOLLA.md`;
- `docs/09_PERFORMANCE_HA.md`;
- `docs/10_SECURITY_DKB.md`;
- завершенный security review E08.

## Единицы работы

### E09.1. Kolla image build

Создать custom Kolla Build configuration/templates для frontend/backend. Build reproducible, pinned, labeled, scanned, SBOM и pushed by digest.

### E09.2. Ansible role skeleton

Service groups, defaults, handlers, config templates, container definitions и checks. Role idempotent и не меняет другие services.

### E09.3. Database/RabbitMQ provisioning

Отдельные DB/user и vhost/user/queues. Secrets из test secret mechanism. Least privilege tests.

### E09.4. Migration job

Single execution, lock/precheck, logs, failure/retry, no API auto migration.

### E09.5. Process containers

По одному frontend/API/worker/events на каждом из трех nodes. Backend command/config различается, image одинаков.

### E09.6. HAProxy/TLS/network

Same-origin route, health, timeout, trusted proxy, headers, TLS/backend TLS по matrix. Management network/ACL documented.

### E09.7. Reconfigure/upgrade/rollback

Test clean deploy, idempotent reconfigure, rolling update, failed update rollback и uninstall/disable.

### E09.8. Deployment smoke/evidence

Container count, image digests, user/caps/mounts/SELinux, DB/MQ access, health, no secret leakage, API/UI smoke.

## Acceptance

- ровно два custom image;
- три nodes дают 12 permanent containers;
- migration one-shot;
- Kolla deploy/reconfigure idempotent;
- HAProxy URL works over TLS;
- DB/MQ least privilege;
- non-root/read-only/caps/SELinux inspected;
- image digest/SBOM/scan linked;
- rolling update and rollback executed in test;
- no production action;
- network/API registry/DKB evidence updated.

## Затронутые ДКБ

ДКБ-22.02, 23.02, 24, 42–44, 55/56, 65, 66 (частично), 69/70, 76/77, 80, 82.

## Не делать

- запускать на production;
- использовать `latest`;
- создавать отдельные backend images;
- хранить passwords в Ansible vars Git;
- менять OpenStack service DB;
- выполнять contract migration до rollback window.

## Итоговый запрос Codex

> Реализуй E09 только на test inventory. Сначала build, затем role, затем single-node smoke, затем three-node rollout. Докажи 2 images/12 containers и rollback; не запускай production deploy.
