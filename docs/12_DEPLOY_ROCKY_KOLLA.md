# Развертывание на Rocky Linux через Kolla

## Целевая упаковка

Собираются два custom image:

    cloud-ui-frontend
    cloud-ui-backend

Один backend image запускается командами:

    cloud-ui api
    cloud-ui worker
    cloud-ui events
    cloud-ui db-upgrade
    cloud-ui smoke

Не создавать отдельные образы для API, worker и events без доказанной несовместимости зависимостей.

## Локальный PoC

На отдельной Rocky Linux VM используется compose profile:

- frontend;
- API;
- worker;
- event consumer;
- MariaDB;
- RabbitMQ;
- mock OpenStack/IdP/SIEM при необходимости.

При подключении к тестовым общим MariaDB/RabbitMQ локальные stateful containers отключаются. Реальные credentials поступают только через защищенный runtime mechanism и не попадают в Git.

## Kolla Build

E09 должен создать:

- custom build configuration;
- Dockerfile/Jinja templates;
- source archive или repository pin;
- version labels;
- image digest/SBOM;
- vulnerability scan;
- push в корпоративный registry;
- reproducible build command;
- policy, запрещающую latest tag.

Base image и версия Rocky выбираются по фактически поддерживаемой локальной Kolla 2025.1 baseline и фиксируются ADR. Не менять базу только ради удобства Codex.

## Kolla-Ansible role

Custom role отвечает за:

- service enable flags;
- groups/inventory placement;
- config generation;
- secrets references;
- container definitions;
- health checks;
- volumes;
- log routing;
- HAProxy frontend/backend;
- TLS paths;
- migration job;
- rolling deploy;
- stop/reconfigure/upgrade;
- smoke test;
- rollback.

Роль должна быть идемпотентной. `check`/dry-run ограничения Ansible документируются.

## Топология трех узлов

На каждом control/UI node:

    cloud_ui_frontend
    cloud_ui_api
    cloud_ui_worker
    cloud_ui_events

Всего 12 постоянных containers. `cloud_ui_db_migrate` запускается один раз перед rollout совместимого backend.

При необходимости worker/events размещаются в отдельной inventory group, но API/frontend остаются горизонтально масштабируемыми.

## БД

Создаются отдельные:

- database/schema `cloud_ui`;
- DB user с правами только на эту schema;
- migration credential при необходимости отдельно от runtime;
- backup/restore runbook.

Не использовать root MariaDB в runtime. Не читать OpenStack service tables.

## Модель доступа Keystone, MariaDB и RabbitMQ

Keystone авторизует пользователей и service users для OpenStack API и service-to-service API
вызовов. Он не является механизмом аутентификации для прямого подключения приложения к MariaDB или
RabbitMQ.

Для Cloud UI разделяются три класса учетных данных:

- OpenStack/Keystone service credential или application credential для вызовов Keystone/Nova и других
  OpenStack API через backend;
- MariaDB runtime/migration users для собственной schema `cloud_ui`;
- RabbitMQ user/vhost для собственного transport namespace `/cloud-ui`.

`oslo.messaging` задает стандартную модель transport для OpenStack services, но при backend broker
RabbitMQ сама аутентификация transport остается broker-level: user/password, vhost, permissions и TLS
из `transport_url`/секретного runtime config. Это не Keystone token flow. Поэтому ошибка MariaDB
`1045 Access denied` или RabbitMQ `ACCESS_REFUSED` на `/cloud-ui` означает проблему DB/MQ principal,
пароля, vhost/permissions или secret injection, а не отказ Keystone RBAC.

Ссылки на upstream-модель:

- OpenStack Keystone service users/service tokens: `https://docs.openstack.org/keystone/latest/admin/manage-services.html`;
- `oslo.messaging` transport URLs: `https://docs.openstack.org/oslo.messaging/latest/reference/transport.html`;
- Kolla-Ansible password classes: `https://docs.openstack.org/kolla-ansible/latest/admin/password-rotation.html`.

## RabbitMQ

Создаются:

- vhost `/cloud-ui`;
- отдельный user;
- permissions только на свои exchanges/queues;
- TLS в production;
- dead-letter exchange;
- queue retention/limits;
- alert queue age;
- безопасный rotation.

OpenStack notifications поступают через отдельно утвержденный notification transport/binding. Consumer не получает wildcard access к RPC exchanges.

## HAProxy и URL

Рекомендуется same-origin:

    https://cloud-ui.example/
    https://cloud-ui.example/api/v1/

HAProxy:

- TLS >= 1.2;
- redirects HTTP → HTTPS либо HTTP listener отключен;
- security headers;
- request size limits;
- timeouts;
- health checks;
- trusted proxy headers;
- rate limiting по утвержденной политике;
- backend TLS/mTLS согласно matrix.

## Конфигурация

Runtime config разделяется:

- non-secret environment/config files;
- secret references/material;
- CA bundle;
- feature flags;
- cloud/region registry;
- workflow catalog;
- role/policy config.

Config version и checksum видимы в protected status endpoint/metrics без раскрытия значений.

## Файловая система контейнеров

- root filesystem read-only, где возможно;
- tmp/cache/log paths — tmpfs или named volume;
- no Docker/Podman socket;
- no host root mounts;
- no openrc/clouds.yaml в frontend;
- backend credentials — минимально scoped и read-only mounted;
- SELinux labels заданы и тестируются;
- log output — stdout/stderr или утвержденный collector path.

## Миграции и rolling update

Порядок:

1. backup/precheck;
2. pull images by digest;
3. run expand-compatible migration;
4. smoke DB schema;
5. rolling API/worker/events;
6. frontend rollout;
7. compatibility smoke;
8. contract/negative tests;
9. finalize/contract migration только после rollback window;
10. сохранить evidence.

Destructive one-step migration запрещена.

## Rollback

- frontend может откатиться независимо в пределах API compatibility window;
- backend rollback возможен до contract migration;
- workflow definitions versioned и не перезаписываются;
- config rollback по Git commit;
- images по digest;
- queued operations не удаляются;
- migration rollback проверяется на копии данных.

## Network zones

Минимум:

- user/external access zone;
- management/API zone;
- DB/messaging backend;
- storage;
- tenant/tunnel;
- provider/external network.

Портал не должен связывать external browser network напрямую с MariaDB/RabbitMQ/OpenStack internal endpoints. Фактические ACL фиксируются в `docs/generated/network-flow-matrix.md`.

## E09 acceptance

- оба image собираются на Rocky/Kolla baseline;
- image находятся в корпоративном test registry;
- compose smoke проходит;
- Kolla role генерирует ожидаемые 12 containers для трех nodes;
- migration job выполняется один раз;
- HAProxy URL отвечает;
- container inspection подтверждает non-root/caps/mounts;
- secrets absent from image history/log;
- uninstall/rollback procedure воспроизводима;
- DKB-24, 42–44, 69–70, 77, 80 обновлены evidence, но gaps не скрыты.
