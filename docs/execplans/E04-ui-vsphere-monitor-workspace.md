# ExecPlan: E04 UI vSphere monitor workspace

## Цель и наблюдаемый результат

Оператор видит VM и hypervisor object workspace в vSphere-like модели: крупные top-level tabs,
локальную secondary navigation внутри `Monitor`, отдельные поверхности `Performance Overview`,
`Utilization`, `Tasks` и `Events`, а также dense event table с backend-bounded UX. До изменения
workspace уже существовал, но имел плоский набор вкладок `Performance` и `Tasks/Events`, без
resource-specific monitor navigation, current utilization bars и таблицы events.

Наблюдаемость результата:

- frontend component tests показывают новые tabs/secondary navigation для VM и hypervisor;
- tests доказывают, что utilization не смешивается с performance time-series;
- tests доказывают, что event table хранит только page/filter/sort/view state и не содержит
  browser-side export полного набора данных;
- frontend lint/typecheck/unit проходят;
- AIO smoke/deploy попытка выполнена и результат записан без секретов.

## Контекст и текущее состояние

Работа ведется в worktree:
`/Users/dmitry/Desktop/dawn/.worktrees/ui-vsphere-monitor-workspace`.

В основном дереве `/Users/dmitry/Desktop/dawn` остались незакоммиченные doc-правки, которые были
перенесены в этот worktree через patch. Кодовый baseline worktree:

- `frontend/src/workspace/vm/VirtualMachineWorkspace.tsx` уже рендерит VM workspace, но через
  плоский `VM_TABS` список: `Summary`, `Hardware`, `Network`, `Performance`, `Snapshots`,
  `Console`, `ISO/Media`, `Tasks/Events`;
- `frontend/src/workspace/hypervisor/HypervisorWorkspace.tsx` уже рендерит hypervisor workspace, но
  через плоский `HYPERVISOR_TABS` список: `Summary`, `VMs`, `Performance`, `Network`,
  `Services/NTP`, `Diagnostics`, `Users/Roles`, `Tasks/Events`;
- `frontend/src/workspace/MetricsPanel.tsx`, `DiagnosticsPanel.tsx`, `SelectionSummary.tsx` и
  `ActionState.tsx` уже существуют;
- `frontend/src/workspace/TasksEventsPanel.tsx` есть как простой placeholder;
- baseline tests после `npm install` прошли: 6 workspace test files, 7 tests passed.

Node/npm ограничение: `npm install` прошел, но показал `EBADENGINE`, потому что проект ожидает Node
`>=24 <25`, а текущая среда использует Node `v25.9.0`. Это ограничение фиксируется как риск среды,
не как изменение продукта.

## Scope

- Добавить shared model для top-level tabs, secondary navigation, utilization и object events.
- Добавить `SecondaryNavigation`, `UtilizationPanel`, `ObjectEventTable`.
- Обновить VM workspace под top-level tabs и VM-specific `Monitor` navigation.
- Обновить hypervisor workspace под top-level tabs и hypervisor-specific `Monitor` navigation.
- Сохранить pending/blocked action model и отсутствие mutation controls для неподдержанных действий.
- Обновить стили без декоративной переработки.
- Обновить generated evidence/risk docs только в части нового UI-поведения.
- Выполнить релевантные frontend checks и попытку AIO deploy/smoke.

## Non-goals

- Не включать live telemetry datasource.
- Не добавлять backend metrics/events endpoints.
- Не включать VM/host mutating operations.
- Не добавлять console proxy, diagnostics bundle или export backend contract.
- Не менять RBAC/session/auth/backend API/OpenAPI.
- Не коммитить vSphere screenshots, credentials, cookies, tokens, стендовые IP или production URL.

## Требования и ограничения

- Browser обращается только к frontend/BFF `/api/v1`.
- UI capabilities являются UX hint, не авторизацией.
- Large inventory/event UX не должен загружать полный dataset в browser.
- Export/copy для task/event/inventory datasets остается disabled/pending до backend-bounded
  audited contract.
- New public API не добавляется; OpenAPI не меняется.
- Изменение должно быть rolling-update safe, потому что затрагивает только frontend static code/docs.

## Связь с ДКБ

- ДКБ-01/03/12: UI показывает защищенные inventory/action surfaces, но не расширяет доступ. Доказание:
  component tests и отсутствие новых backend endpoints.
- ДКБ-46/49: Tasks/Events становятся видимой surface для будущего audit/correlation UX. Доказание:
  event table tests и documentation updates; полное закрытие невозможно без backend audit/event data.
- ДКБ-55/56: UI не должен хранить секреты, токены, console URLs. Доказание: existing storage tests,
  secret scan; полное закрытие зависит от backend/session evidence.
- ДКБ-77/82: документация UI/API/evidence обновляется. API contract не меняется.

## Milestones

1. Baseline and plan: создать worktree, перенести doc updates, подтвердить текущие workspace tests.
2. Contract tests: добавить failing tests для secondary navigation, utilization и events table.
3. Minimal UI implementation: добавить компоненты и интегрировать в VM/hypervisor workspace.
4. Safety and docs: подтвердить отсутствие full-browser export, обновить generated evidence/risk docs.
5. Verification: frontend tests, typecheck, lint, secret scan, diff review.
6. AIO attempt: выполнить доступную build/deploy/smoke команду, записать результат и ограничения.

## Progress

- [x] 2026-07-01 Baseline and plan: worktree создан, doc patch применен, `npm install` выполнен,
  workspace tests прошли: 6 files, 7 tests.
- [x] 2026-07-01 Contract and test double: RED run failed as expected for missing
  `SecondaryNavigation`, `UtilizationPanel`, `ObjectEventTable` and old flat tab labels.
- [x] 2026-07-01 Minimal implementation: components integrated into VM/hypervisor workspace; focused
  GREEN run passed: 5 files, 5 tests.
- [x] 2026-07-01 Negative scenarios and security: event table keeps export disabled/pending and tests
  assert no full browser dataset export wording or arbitrary input controls.
- [x] 2026-07-01 Integration and user checks: expanded frontend suite passed, AIO Kolla image
  build/push succeeded, no-migration reconfigure completed and direct AIO smoke passed.
- [x] 2026-07-01 Documentation, evidence and review: generated UI evidence, risk register, current
  state and E09 AIO deployment evidence updated without secret values.

## Неожиданные открытия

- 2026-07-01: в worktree отсутствовал `frontend/node_modules`, baseline test сначала упал с
  `vitest: command not found`. После `npm install` baseline workspace tests прошли.
- 2026-07-01: среда использует Node `v25.9.0`, а `frontend/package.json` требует `>=24 <25`.
  `npm install` завершился с warning `EBADENGINE`, не с ошибкой.
- 2026-07-01: Serena project activation для worktree определила только Python, поэтому TypeScript
  symbols не извлекаются; код исследуется через `sed`/`rg`.
- 2026-07-01: первый GREEN run упал из-за одинаковых labels у secondary navigation group heading and
  item (`Issues and Alarms`). Исправлено в сторону vSphere-like структуры: group `Issues and Alarms`
  содержит `All Issues` and `Triggered Alarms`, `Resource Allocation` содержит CPU/Memory/Storage.
- 2026-07-01: штатный Kolla build wrapper требует `CLOUD_UI_SOURCE_PIN`, который резолвится в git
  commit. Для AIO проверки без изменения локальной истории был создан временный git repo только на
  Ansible host с source pin `506facab4f9f115cc063b8e52cf90d565a10aea6`.
- 2026-07-01: при первом `build-images.sh push` registry input был указан как
  `192.168.10.15:5000/kolla/cloud-ui-test`; вместе с `namespace=cloud-ui-test` это создало
  промежуточный путь `.../cloud-ui-test/cloud-ui-test/...`. Собранные backend/frontend images были
  retagged and pushed в ожидаемый путь `192.168.10.15:5000/kolla/cloud-ui-test/...` без пересборки.
- 2026-07-01: `kolla-ansible reconfigure-no-migration` сообщил Docker warning `IPv4 forwarding is
  disabled`. Direct smoke на `127.0.0.1:18081` and `127.0.0.1:13080` прошел; HAProxy/VIP/TLS и
  inter-container network hardening остаются вне этого UI-среза.

## Журнал решений

- 2026-07-01: выполнять реализацию в отдельном worktree, а не в грязном `main`. Альтернатива:
  продолжить в основном дереве с doc-правками. Причина: execution-plan workflow и безопасность
  основного дерева. Последствие: итоговые изменения находятся в worktree branch
  `feature/ui-vsphere-monitor-workspace`.
- 2026-07-01: реализовать инкремент поверх существующих workspace components вместо переписывания
  shell/App. Причина: existing offline workspace уже принят, а новый scope касается Monitor UX.
- 2026-07-01: не делать clickable route switching в secondary navigation в этом срезе. Альтернатива:
  вводить полноценное tab state/router state. Причина: текущий offline workspace already renders
  all planned surfaces as placeholders; route state belongs to later route-module slice.
- 2026-07-01: для AIO использовать `reconfigure-no-migration`, а не migration-enabled reconfigure.
  Причина: изменение frontend/static UI не меняет schema/API/backend contract. Последствие: Alembic
  one-shot containers were skipped, а четыре permanent Cloud UI containers were replaced by digest.

## Детальный план реализации

1. Добавить tests:
   - `frontend/src/workspace/SecondaryNavigation.test.tsx`;
   - `frontend/src/workspace/UtilizationPanel.test.tsx`;
   - `frontend/src/workspace/ObjectEventTable.test.tsx`;
   - обновить `VirtualMachineWorkspace.test.tsx`;
   - обновить `HypervisorWorkspace.test.tsx`.
2. Убедиться, что tests падают по ожидаемым причинам: missing components/labels.
3. Обновить `frontend/src/workspace/types.ts`:
   - `WorkspaceTab`;
   - `SecondaryNavigationSection`;
   - `UtilizationMetric`;
   - `ObjectEventRow`;
   - `ObjectEventTableState`.
4. Создать компоненты:
   - `frontend/src/workspace/SecondaryNavigation.tsx`;
   - `frontend/src/workspace/UtilizationPanel.tsx`;
   - `frontend/src/workspace/ObjectEventTable.tsx`.
5. Обновить VM/hypervisor workspaces:
   - top-level tabs: `Summary`, `Monitor`, `Configure`, `Permissions`, related resource tabs;
   - resource-specific `Monitor` secondary navigation;
   - `MetricsPanel` title `Performance Overview`;
   - `UtilizationPanel` separate from metrics;
   - `ObjectEventTable` for `Events`;
   - keep pending/blocked action behavior.
6. Обновить `frontend/src/styles.css` для dense secondary navigation, utilization bars and events
   table with stable dimensions.
7. Обновить docs:
   - `docs/generated/ui-shell-horizon-parity.md`;
   - `docs/generated/risk-register.md`.

## Миграции и совместимость

DB/API migrations отсутствуют. Frontend change совместим с текущими backend responses, потому что
использует existing `InstanceItem`, `HypervisorItem`, static placeholders and capabilities.
Rollback: вернуть измененные frontend/docs файлы или переключить deployment на предыдущий image.

## Проверка

Команды из worktree:

```bash
cd frontend && npm test -- --run src/workspace/SecondaryNavigation.test.tsx src/workspace/UtilizationPanel.test.tsx src/workspace/ObjectEventTable.test.tsx src/workspace/vm/VirtualMachineWorkspace.test.tsx src/workspace/hypervisor/HypervisorWorkspace.test.tsx
cd frontend && npm test -- --run src/workspace/ActionState.test.tsx src/workspace/MetricsPanel.test.tsx src/workspace/DiagnosticsPanel.test.tsx src/workspace/SelectionSummary.test.tsx src/workspace/vm/VirtualMachineWorkspace.test.tsx src/workspace/hypervisor/HypervisorWorkspace.test.tsx src/App.test.tsx src/shell/CloudShell.test.tsx
cd frontend && npm run typecheck
cd frontend && npm run lint
cd frontend && npm test
./scripts/secret-scan.sh
git diff --check
```

AIO attempt будет выбран после осмотра `deploy/AGENTS.md`, `Makefile` and AIO docs. Если команда
требует production credential или destructive operation, будет выполнен только safe build/smoke/dry
run и это будет записано как ограничение.

Дополнительные AIO команды, выполненные через approved all-in-one test stand:

```bash
cd frontend && npm run build
ssh root@192.168.10.15 '... build-images.sh list'
ssh root@192.168.10.15 '... build-images.sh push'
ssh root@192.168.10.15 '... run-cloud-ui-aio-kolla.py preflight ...'
ssh root@192.168.10.15 '... run-cloud-ui-aio-kolla.py reconfigure-no-migration ...'
ssh root@192.168.10.15 'ssh root@192.168.10.14 curl ... /api/v1/health/ready'
ssh root@192.168.10.15 'ssh root@192.168.10.14 curl ... http://127.0.0.1:13080/'
ssh root@192.168.10.15 'ssh root@192.168.10.14 curl ... /api/v1/session'
```

## Доказательства

- Vitest output for focused workspace tests.
- Typecheck/lint/unit output.
- Secret scan output.
- `git diff --check` output.
- AIO build/deploy/smoke command output or explicit blocked reason.
- AIO result: tag `2025.1-rocky-9-ui-vsphere-20260701T2230`, backend digest
  `sha256:488fe10ca83838a17283e363d4bcc3efe1e5314b2a1a54103ee78d9a11777f63`, frontend digest
  `sha256:087aca8065069ab760308f9ce299603789f4a63fb728494e556b699fc531fd05`.
- AIO preflight: `localhost : ok=10 changed=0 failed=0`.
- AIO reconfigure-no-migration: `openstack-aio : ok=34 changed=4 failed=0 skipped=3`.
- AIO smoke: API ready HTTP 200 with DB/RabbitMQ reachable; frontend index HTTP 200 with
  `/assets/index-D8pWmsuw.js` and `/assets/index-OB7EfGmx.css`; BFF `/api/v1/session` HTTP 401
  `not_authenticated`; sanitized inspect confirms new digests, `user=cloudui`, read-only rootfs,
  `cap_drop=[ALL]`, `no-new-privileges`.

## Откат и восстановление

- Для локального отката: удалить worktree branch или вернуть changed files в
  `.worktrees/ui-vsphere-monitor-workspace`.
- Для основного дерева: текущий worktree не меняет `main`; doc changes в основном дереве можно
  откатить отдельно, если они не нужны.
- Для deployment: выполнить documented AIO rollback через
  `run-cloud-ui-aio-kolla.py reconfigure-no-migration` с предыдущей digest-парой:
  backend `sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438` and frontend
  `sha256:750ac3131e9ea9868d0893ff6df4eb603641b31c413c204c6a1470c20d17e790`. Не использовать
  `make down` для AIO, потому что текущий выкат выполнен через Kolla-Ansible, а не local compose.

## Итог и остаточные риски

Реализация и AIO attempt завершены. Остаточные риски:

- secondary navigation пока статична в текущем offline workspace; полноценный route state остается
  отдельным срезом;
- `Utilization` и `Events` используют placeholder/read-model-facing data, не live telemetry backend;
- event export остается disabled до backend-bounded audited export contract;
- live AIO evidence является partial lab evidence: не закрывает three-node rollout, HAProxy/VIP/TLS,
  SELinux labels, corporate signing/scanning/provenance и ДКБ-69 waiver;
- текущая Node среда `v25.9.0` вне заявленного frontend engine range `>=24 <25`.
