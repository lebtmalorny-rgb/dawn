# Доменная модель и данные

## Принципы

- Ресурсы OpenStack в БД портала являются проекцией, а не источником истины.
- Прикладные сущности портала имеют собственный lifecycle.
- В каждой таблице определены owner, tenant/scope, timestamps и audit semantics.
- Для удаления read model используется tombstone или `deleted_at`, чтобы позднее событие не воскресило ресурс без проверки.
- Все внешние identifiers хранятся вместе с `cloud_id`/`region_id`, потому что UUID может быть уникален только в пределах deployment.
- Фильтруемые поля не прячутся в JSON.
- Никакие OpenStack credentials не хранятся в read model.

## Основные сущности

### Cloud и Region

`clouds` и `regions` описывают подключенные deployment/region, endpoint status, supported capabilities и last sync. В PoC может быть одна запись, но ключи данных остаются multi-region-ready.

### Project и User reference

Хранят только минимальные reference-данные для отображения и фильтрации. Полные identity-профили не реплицируются без необходимости.

### Instance projection

Минимальные поля:

- `cloud_id`, `region_id`, `instance_id`;
- `name`, `project_id`, `user_id`;
- `status`, `power_state`, `task_state`, `vm_state`;
- `host_name`, `hypervisor_id`, `availability_zone`;
- `flavor_id`, `vcpus`, `ram_mb`, `disk_gb`;
- `image_id`, `boot_volume_id`;
- нормализованные IP/metadata/tags;
- `source_created_at`, `source_updated_at`, `observed_at`;
- `sync_generation`, `sync_status`, `deleted_at`;
- hash значимых полей для cheap change detection.

Уникальный ключ: `(cloud_id, region_id, instance_id)`.

### Hypervisor projection

- `hypervisor_id`, `host_name`;
- `service_id`, `service_status`, `service_state`;
- `hypervisor_type`, `version`;
- capacity и usage;
- running VMs;
- availability zone и aggregates;
- maintenance/disabled reason;
- `observed_at`, `sync_status`, `deleted_at`.

### Service health projections

Для real-time health и неполных прав нужны отдельные проекции статуса сервисов:

- `compute_services`: Nova compute/scheduler/conductor service state, status, disabled reason, host/AZ;
- `network_agents`: Neutron agent type, host, alive/admin state, configurations summary;
- `volume_services`: Cinder service state, cluster/host, replication/availability status where exposed;
- `image_tasks`: Glance task/image operation status and safe error summary;
- `orchestration_stacks`: Heat stack status, resource count and operation correlation if module enabled;
- `load_balancers`, `dns_zones`, `secret_metadata`, `baremetal_nodes`: module-specific projections only when Octavia/Designate/Barbican/Ironic are enabled and authorized.

Каждая projection имеет `observed_at`, `source_updated_at`, `sync_status`, `source` and `visibility_scope`. Protected names/counts can be redacted while preserving aggregate partial-state semantics.

### Watcher projection

Watcher хранится как projection, не как источник истины:

- goals and strategies with supported parameters, datasource requirements and enabled status;
- audit templates with JSON Schema-like parameter contract, risk level and required capability;
- audits, including one-shot and continuous audits, status, trigger, target scope, telemetry freshness and history;
- action plans, actions and recommendations with impact, confidence, affected resources, dependency links and conflict markers;
- execution correlation: portal `operation_id`, Mistral `execution_id` if used, Watcher audit/action IDs, rollback/abort availability and final verification state;
- risk metadata for automatic apply: disabled by default, approval mode, maximum scope, canary/dry-run requirement and audit mapping.

Telemetry datasource references are explicit: Ceilometer, Gnocchi, Prometheus and Aetos are separate integration records with coverage/freshness/gap status.
Prometheus exporter path starts with `openstack-exporter` and `node_exporter`; these metrics are telemetry/corroboration signals, not direct Watcher/Masakari automation authority.

### Masakari projection

Masakari projection covers:

- failover segments, recovery method, segment hosts and monitor coverage/config status;
- host/instance/process notifications, source monitor, generated time, status, duplicate marker and recovery state;
- hostmonitor events normalized into a recovery timeline, including Consul-driven network health matrix signals when Masakari hostmonitor uses `monitoring_driver=consul`;
- processmonitor and instancemonitor events with explicit coverage state; `processmonitor` remains R&D/diagnostic for Kolla/container deployments until tested in a representative lab;
- relation to hypervisor, Nova compute service, instance state, migration/evacuation task and availability zone;
- operator approval gates and pending/approved/rejected state for portal-driven recovery workflows;
- conflicting states: maintenance, disabled service, already migrating, stale monitor, partial monitor coverage, repeated notification or Nova policy denial.

Nova evacuate/live migration remains an OpenStack operation with Nova policy enforcement. Masakari UI shows correlation and preconditions; it does not bypass Nova.
Consul Events, Prometheus alerts and exporter metrics can enrich confidence and diagnostics, but the authoritative recovery state is Masakari/Nova state plus reconciliation.

### Topology and dependency graph projection

Topology queries use graph-shaped projections built from read model tables, not live fan-out:

- nodes: VM, port, network, subnet, router, floating IP, security group, volume, image, hypervisor, aggregate, availability zone, resource group and enabled service module entities;
- edges: attachment, boot source, placement, route, membership, dependency, operation impact and HA/recovery relation;
- every node/edge has `visibility_scope`, `freshness`, `partial` and optional redaction reason;
- graph layout stores only UI preferences/cache, not source-of-truth relationships.

### Resource group

E05 реализует resource groups как portal-owned metadata в MariaDB. Это не Nova server group,
не host aggregate и не Placement side effect: группа не меняет размещение или состояние OpenStack
ресурса сама по себе.

- `group_id`;
- `name`, `description`;
- `resource_type`: `vm`, `host`, `mixed`;
- `scope_type` и `scope_id`;
- `membership_mode`: `explicit`, `dynamic`, `imported`;
- `rule_version` и безопасное декларативное rule body;
- owner и ACL/capability references;
- revision;
- timestamps.

E05 P0 правила владения:

- VM group всегда project-scoped; `scope_id` берется из server-side subject scope либо, для
  `portal_admin`, из явно указанного project scope.
- VM member может быть добавлен только если `instances.project_id == resource_groups.scope_id` в
  trusted inventory read model.
- Host groups не являются project-owned; создание и изменение host/mixed групп требует P0
  admin/system-like capability.
- `mixed + dynamic` запрещен до отдельной семантики rule evaluation для разных resource types.
- Удаление группы soft-delete; deleted group недоступна для list/detail/member operations.
- Revision увеличивается при изменениях metadata/membership, а `resource_group_revisions` хранит
  snapshot evidence для optimistic concurrency и аудита.

### Group member

Для explicit/imported membership:

- `group_id`;
- `resource_type`;
- `cloud_id`, `region_id`, `resource_id`;
- source;
- `added_by`, `added_at`;
- optional expiry.

Dynamic membership вычисляется предсказуемым query compiler, а не произвольным SQL/Jinja/Python.
Текущий DSL допускает только allowlisted поля и операторы для `vm`/`host`, ограничивает глубину AST,
запрещает дополнительные свойства и компилируется в SQLAlchemy expressions с bound values.

### Resource group idempotency key

Для retry-safe explicit membership mutations E05 хранит отдельные bindings:

- `group_id`, `actor_id`, `action`;
- HMAC-hash `idempotency-key`, не исходный header;
- request hash;
- deterministic `operation_id`;
- timestamps.

Запись создается даже для no-op add/remove, поэтому повтор с тем же key и другим payload получает
`409 idempotency_key_conflict`. Same-key/same-payload replay возвращает стабильный metadata result,
но не является моделью для будущих destructive workflows без сохраненного response snapshot.

### Portal role и permission

- `portal_roles`;
- `permissions`;
- `role_permissions`;
- `role_bindings`;
- optional group ACL.

Permission names версионируются как `resource.action`, например:

    instance.read
    hypervisor.read
    group.manage
    workflow.execute.maintenance-host
    watcher.read
    watcher.recommendation.apply
    masakari.read
    masakari.recovery.approve
    realtime.stream.read
    audit.read
    role.manage

Role binding содержит subject type, subject ID, scope и validity interval. Конфликтующие роли проверяются в корпоративном IAM; портал дополнительно запрещает известные несовместимые комбинации.

### Session

- opaque `session_id`;
- subject and identity context;
- encrypted server-side token reference/data according to approved design;
- created, last_activity, absolute_expiry;
- revoked_at and reason;
- client metadata в минимальном объеме;
- session generation.

Browser получает только opaque cookie. Idle timeout проверяется сервером на каждом request.

### Workflow definition

- stable `workflow_key`;
- version;
- display metadata;
- target types;
- JSON Schema input;
- Mistral workflow name/version mapping;
- required capabilities;
- cancel/retry policy;
- enabled state;
- checksum and approval metadata.

### Operation

- `operation_id`;
- workflow key/version;
- initiator;
- scope and targets;
- sanitized input summary;
- idempotency key and request hash;
- state;
- external execution ID;
- timestamps;
- correlation ID;
- error code and safe error summary;
- revision.

Уникальность idempotency задается на actor/scope/key либо по утвержденной модели.

### Operation event

Append-only timeline: accepted, queued, dispatched, started, progress, completed, failed, cancel requested, cancelled. Payload versioned и sanitized.

Operation events are also the canonical input for live task/progress UI. The browser receives filtered projections through SSE or polling fallback, never raw worker or OpenStack messages. WebSocket is only allowed after ADR and load/backpressure evidence.

### Audit event

Портал хранит прикладной оперативный индекс и delivery state. Долговременный authoritative audit находится во внешней системе.

Поля соответствуют `docs/08_AUDIT_OBSERVABILITY.md`.

### Sync state

`sync_runs`, `sync_cursors`, `sync_failures` и `reconciliation_findings` позволяют повторять chunk, видеть stale region и доказывать актуальность.

### Outbox

`outbox_events` создаются в той же транзакции, что и операция/изменение. Worker публикует событие и помечает delivery. Повторная публикация безопасна.

### Event stream cursor

`event_stream_offsets` или эквивалентная таблица хранит resume cursor per subject/session/channel when required. Cursor подписывается backend, scopes events by actor/capability and can be invalidated on policy revision. It is not an audit store and can be rebuilt from operation/audit/read-model projections.

## Индексы

Минимальные индексы для instance list:

- `(cloud_id, region_id, deleted_at, name, instance_id)`;
- `(project_id, status, instance_id)`;
- `(host_name, status, instance_id)`;
- `(availability_zone, status, instance_id)`;
- `(observed_at)`;
- normalized tag/member lookup.

Фактические composite indexes определяются query telemetry и `EXPLAIN`, а не предположением.

Watcher/Masakari/topology indexes are introduced with the modules that query them. Required query cases include audit/action plan by status, recommendation by affected resource, segment host by host, notification by recovery status and graph edge lookup by node.

## Пагинация

Предпочтительна cursor/keyset pagination с детерминированным tie-breaker `instance_id`. Cursor подписывается backend и содержит только разрешенные значения. Offset допустим для малых административных справочников.

## Retention

- sessions: удаляются после expiry плюс короткий forensic period;
- idempotency records: дольше максимального retry window;
- operation timeline: по эксплуатационному регламенту;
- portal audit index: ограниченный период, authoritative copy в SIEM;
- deleted projections: до прохождения reconciliation/retention;
- secrets не попадают в эти таблицы.

Сроки утверждаются в E00/E08.
