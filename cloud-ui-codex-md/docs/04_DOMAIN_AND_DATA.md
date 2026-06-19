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

### Resource group

- `group_id`;
- `name`, `description`;
- `resource_type`: `vm`, `host`, `mixed`;
- `scope_type` и `scope_id`;
- `membership_mode`: `explicit`, `dynamic`, `imported`;
- `rule_version` и безопасное декларативное rule body;
- owner и ACL/capability references;
- revision;
- timestamps.

### Group member

Для explicit/imported membership:

- `group_id`;
- `resource_type`;
- `cloud_id`, `region_id`, `resource_id`;
- source;
- `added_by`, `added_at`;
- optional expiry.

Dynamic membership вычисляется предсказуемым query compiler, а не произвольным SQL/Jinja/Python.

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

### Audit event

Портал хранит прикладной оперативный индекс и delivery state. Долговременный authoritative audit находится во внешней системе.

Поля соответствуют `docs/08_AUDIT_OBSERVABILITY.md`.

### Sync state

`sync_runs`, `sync_cursors`, `sync_failures` и `reconciliation_findings` позволяют повторять chunk, видеть stale region и доказывать актуальность.

### Outbox

`outbox_events` создаются в той же транзакции, что и операция/изменение. Worker публикует событие и помечает delivery. Повторная публикация безопасна.

## Индексы

Минимальные индексы для instance list:

- `(cloud_id, region_id, deleted_at, name, instance_id)`;
- `(project_id, status, instance_id)`;
- `(host_name, status, instance_id)`;
- `(availability_zone, status, instance_id)`;
- `(observed_at)`;
- normalized tag/member lookup.

Фактические composite indexes определяются query telemetry и `EXPLAIN`, а не предположением.

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
