# ExecPlan: E00 discovery baseline

## Цель и наблюдаемый результат

Команда получает проверенный baseline комплекта документов и локальной среды, PoC cutline, provisional scale profile, ADR backlog, реестры интеграций/API/network/TLS/secrets и план по 73 требованиям ДКБ. После этого можно переходить к E01 без скрытых предположений о целевой среде.

## Контекст и текущее состояние

Рабочая директория `/Users/dmitry/Desktop/dawn` не является Git-репозиторием. В ней есть один исходный архитектурный отчет `skyline:horizon arch.md` и каталог `cloud-ui-codex-md/` с документами, задачами и шаблонами. Прикладного frontend/backend/deploy кода пока нет.

Ключевые входные документы:

- `cloud-ui-codex-md/AGENTS.md`
- `cloud-ui-codex-md/PLANS.md`
- `cloud-ui-codex-md/tasks/E00_DISCOVERY.md`
- `cloud-ui-codex-md/docs/00_CONTEXT.md`
- `cloud-ui-codex-md/docs/01_SCOPE_AND_REQUIREMENTS.md`
- `cloud-ui-codex-md/docs/02_TARGET_ARCHITECTURE.md`
- `cloud-ui-codex-md/docs/10_SECURITY_DKB.md`
- `cloud-ui-codex-md/docs/11_DKB_TRACEABILITY.md`
- `cloud-ui-codex-md/docs/15_DECISIONS_AND_OPEN_QUESTIONS.md`

Локальная машина является macOS host, а не целевым Rocky/Kolla test host. Это значит, что E00 фиксирует локальную доступность tools, но не подтверждает production или Kolla baseline.

## Scope

- Осмотр текущего комплекта документов и локальной среды.
- Создание `docs/generated/current-state.md`.
- Создание `docs/generated/poc-scope.md`.
- Создание `docs/generated/scale-profile.md`.
- Создание ADR-001..ADR-010 в `docs/adr/`.
- Создание `docs/generated/integration-register.md`.
- Создание `docs/generated/api-register.md`.
- Создание `docs/generated/network-flow-matrix.md`.
- Создание `docs/generated/tls-matrix.md`.
- Создание `docs/generated/secret-inventory.md`.
- Создание `docs/generated/dkb-implementation-plan.md`.
- Проверка на явные secrets, unresolved compliance claims и количество ДКБ-кодов.

## Non-goals

- Не создавать прикладной frontend/backend.
- Не подключаться к OpenStack, SIEM, Vault, registry или production network.
- Не запускать Kolla-Ansible.
- Не принимать финальное соответствие ДКБ.
- Не подменять unknown внешней системы догадкой.

## Требования и ограничения

- Browser не должен получать OpenStack tokens.
- Все OpenStack integrations должны идти через backend adapters.
- Длительные workflow должны идти через allowlisted Mistral definitions.
- Read model является projection, а не source of truth.
- P0 не считается evidence соответствия ДКБ.
- Любое unknown должно иметь owner или способ получения.
- Production credentials не предоставлены и не должны появляться в Git.

## Связь с ДКБ

E00 не меняет статус соответствия. Он классифицирует все 73 требования из `docs/11_DKB_TRACEABILITY.md`, назначает контур ответственности, gate, план evidence и явные gaps. Финальная оценка остается за владельцем безопасности.

Наиболее рискованные требования, которые нельзя закрыть только порталом:

- ДКБ-07: service accounts OpenStack требуют формального разграничения.
- ДКБ-22.02: mTLS по всем flows требует per-integration matrix.
- ДКБ-48/50: полный аудит требует внешнего SIEM, host/container/libvirt/network/storage/IdP sources.
- ДКБ-55/56: all secrets lifecycle требует Vault (SecMan) и deployment pipeline.
- ДКБ-65: SELinux/AppArmor требует фактического host evidence.
- ДКБ-69: Python backend конфликтует с запретом интерпретаторов.
- ДКБ-72: storage architecture не закрывается UI.
- ДКБ-76: исходное требование неполное и требует детализации.

## Milestones

1. Зафиксировать текущее состояние и локальные tools.
2. Зафиксировать PoC cutline и provisional scale profile.
3. Создать ADR backlog по 10 обязательным решениям.
4. Создать реестры integration/API/network/TLS/secrets.
5. Создать план ДКБ по 73 кодам.
6. Выполнить проверки ссылок/секретов/claims.

## Progress

- [x] 2026-06-19: Исследование фактического состояния. Evidence: `docs/generated/current-state.md`.
- [x] 2026-06-19: Scope и scale profile. Evidence: `docs/generated/poc-scope.md`, `docs/generated/scale-profile.md`.
- [x] 2026-06-19: ADR backlog. Evidence: `docs/adr/ADR-001-authentication-federation.md` .. `docs/adr/ADR-010-dynamic-group-rule-language.md`.
- [x] 2026-06-19: Integration/API/network/TLS/secret registers. Evidence: `docs/generated/*-register.md`, `docs/generated/*-matrix.md`, `docs/generated/secret-inventory.md`.
- [x] 2026-06-19: DKB implementation plan. Evidence: `docs/generated/dkb-implementation-plan.md`.
- [x] 2026-06-19: Verification and self-review. Evidence: commands listed in this plan.

## Неожиданные открытия

- Текущая папка не является Git-репозиторием. Worktree создать нельзя; E00 выполнен в текущем workspace.
- Docker CLI установлен, но Docker daemon недоступен из sandbox через user socket. Это не доказывает отсутствие Docker на машине, только недоступность daemon для текущего запуска.
- Ansible установлен, но стандартный tmp path в home недоступен из sandbox. Команда `ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible --version` успешно подтвердила версию.
- Kolla CLI (`kolla-build`, `kolla-ansible`) в локальном PATH отсутствует.
- User-provided test Ansible host `192.168.10.15` is reachable and runs Rocky Linux 9.5.
- Test OpenStack all-in-one host `192.168.10.14` runs Rocky Linux 9.8 and Kolla containers tagged `2025.1-rocky-9`.
- Kolla-Ansible is installed in `/root/venvs/kolla-epoxy` on the Ansible host, not in root PATH.
- Current service catalog includes Keystone/Nova/Placement/Neutron/Glance/Cinder/Heat, but not Mistral/Watcher/Masakari.
- `/root/openrc` points to unreachable `192.168.10.50`; `/etc/kolla/admin-openrc.sh` points to working VIP `192.168.10.250`.
- Initial E00 discovery observed VIP/API endpoints over HTTP; this was superseded by the post-E00 Kolla TLS update below.
- Post-E00 operational update on 2026-06-19: Mistral, Watcher, Masakari API/engine, Redis and Kolla TLS were enabled through Kolla-Ansible on `/etc/kolla/all-in-one`.
- Post-E00 operational update on 2026-06-19: `/etc/kolla/admin-openrc.sh` now uses `https://192.168.10.250:5000` and Kolla CA, and OpenStack CLI token/service catalog checks work over HTTPS.
- Post-E00 operational update on 2026-06-19: `kolla-build` is installed in `/root/venvs/kolla-epoxy`; Podman build tooling is configured through `/etc/kolla/kolla-build.conf`.

## Журнал решений

- 2026-06-19: Для E00 не создавать branch/worktree, потому что рабочая директория не Git repository. Последствие: rollback выполняется удалением новых E00-файлов вручную, а не через Git.
- 2026-06-19: Все ADR кроме ADR-005 и ADR-010 оставить `proposed`, пока не появятся внешние facts или accepted owners. Последствие: E01 blocked до принятия ADR-006 runtime/package versions.
- 2026-06-19: Redis/WebSocket из исходного отчета не включать в P0/P1 baseline. Последствие: Redis добавляется только после измеренного bottleneck и ADR, SSE/WebSocket после доказанной необходимости.

## Детальный план реализации

Созданы каталоги:

- `cloud-ui-codex-md/docs/generated/`
- `cloud-ui-codex-md/docs/execplans/`
- `cloud-ui-codex-md/docs/adr/`
- `cloud-ui-codex-md/artifacts/`

Созданы файлы:

- `docs/generated/current-state.md`
- `docs/generated/poc-scope.md`
- `docs/generated/scale-profile.md`
- `docs/generated/integration-register.md`
- `docs/generated/api-register.md`
- `docs/generated/network-flow-matrix.md`
- `docs/generated/tls-matrix.md`
- `docs/generated/secret-inventory.md`
- `docs/generated/dkb-implementation-plan.md`
- `docs/adr/ADR-001-authentication-federation.md`
- `docs/adr/ADR-002-openstack-client-strategy.md`
- `docs/adr/ADR-003-notification-reconciliation.md`
- `docs/adr/ADR-004-workflow-publication.md`
- `docs/adr/ADR-005-session-concurrency-policy.md`
- `docs/adr/ADR-006-runtime-package-versions.md`
- `docs/adr/ADR-007-scheduler-leader.md`
- `docs/adr/ADR-008-audit-sink.md`
- `docs/adr/ADR-009-secman-vault.md`
- `docs/adr/ADR-010-dynamic-group-rule-language.md`

## Миграции и совместимость

E00 создает только документацию. Схемы БД, API и runtime artifacts не меняются. Rolling update не применим.

Откат: удалить новые директории/файлы E00:

- `cloud-ui-codex-md/docs/generated/`
- `cloud-ui-codex-md/docs/execplans/E00-discovery-baseline.md`
- `cloud-ui-codex-md/docs/adr/ADR-001-authentication-federation.md` .. `ADR-010-dynamic-group-rule-language.md`
- `cloud-ui-codex-md/artifacts/`, если пустой каталог не нужен.

## Проверка

Команды, выполненные из `/Users/dmitry/Desktop/dawn`:

- `git rev-parse --show-toplevel` -> failed: not a Git repository.
- `git status --short` -> failed: not a Git repository.
- `uname -a` -> macOS Darwin arm64 host.
- `sw_vers` -> macOS 26.5.1.
- `git --version` -> 2.49.0.
- `python3 --version` -> 3.14.0.
- `node --version` -> v25.9.0.
- `npm --version` -> 11.12.1.
- `pnpm --version` -> command not found.
- `uv --version` -> 0.11.7.
- `make --version` -> GNU Make 3.81.
- `docker --version` -> Docker 29.0.1.
- `docker info` -> client present, server socket permission denied.
- `ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ansible --version` -> ansible core 2.18.6.
- `kolla-build --version` -> command not found.
- `kolla-ansible --version` -> command not found.
- `rg -o "ДКБ-[0-9]+(?:\\.[0-9]+)?" cloud-ui-codex-md/docs/11_DKB_TRACEABILITY.md | sort -u | wc -l` -> 73.
- `ssh ... root@192.168.10.15 'hostname; cat /etc/os-release; ...'` -> Ansible host `ansible.example.local`, Rocky 9.5; Kolla tools not in root PATH.
- `ssh ... root@192.168.10.15 '/root/venvs/kolla-epoxy/bin/kolla-ansible --version; ...'` -> Kolla-Ansible `20.4.1.dev5`, Ansible core `2.18.17`, OpenStack CLI `7.5.0`.
- `ssh ... root@192.168.10.14 'hostname; cat /etc/os-release; docker --version; docker ps ...'` -> OpenStack host `openstack-aio`, Rocky 9.8, Docker `29.5.2`, Kolla containers `2025.1-rocky-9`.
- Initial E00 `curl` from Ansible host to `http://192.168.10.250:5000/v3` -> Keystone version discovery `v3.14`; superseded by HTTPS verification after post-E00 Kolla TLS update.
- OpenStack CLI via `/etc/kolla/admin-openrc.sh` -> service catalog and resource counts collected without storing credentials.
- `kolla-ansible prechecks -i /etc/kolla/all-in-one` -> completed with `failed=0`.
- `kolla-ansible pull -i /etc/kolla/all-in-one` -> completed with `failed=0`.
- `kolla-ansible reconfigure -i /etc/kolla/all-in-one` -> completed with recap `failed=0`.
- `kolla-ansible post-deploy -i /etc/kolla/all-in-one` -> regenerated openrc/clouds.yaml for HTTPS.
- `kolla-ansible check -i /etc/kolla/all-in-one` -> completed with recap `ok=51 changed=0 failed=0`.
- `curl --cacert /etc/kolla/certificates/ca/root.crt https://192.168.10.250:5000/v3` -> Keystone version discovery `v3.14`.
- `openssl s_client -brief -connect 192.168.10.250:5000 -CAfile /etc/kolla/certificates/ca/root.crt` -> TLSv1.3 and `Verification: OK`.
- OpenStack CLI via regenerated `/etc/kolla/admin-openrc.sh` -> `mistral`, `watcher` and `masakari` present in service catalog.
- `kolla-build --config-file /etc/kolla/kolla-build.conf --template-only --profile aux` -> generated Dockerfiles under `/tmp/kolla-build-config-dryrun/docker`.

Final verification commands are listed in the final report.

## Доказательства

Документальные evidence для E00 находятся в `docs/generated/` и `docs/adr/`. Они не содержат credentials, private endpoints или production payload.

## Откат и восстановление

Так как Git отсутствует, откат выполняется удалением новых E00-файлов. Перед переходом к E01 рекомендуется инициализировать Git или перенести комплект в целевой repository, чтобы следующие этапы выполнялись через branch/worktree.

## Итог и остаточные риски

E00 baseline создан. Остаточные blockers до E01:

- Нужно принять ADR-006 с фактическими Python/Node/package manager/Kolla base versions.
- Нужно перенести комплект в Git repository или инициализировать repository перед кодом.
- Нужно подтвердить image base digests и целевой registry.
- Mistral/Watcher/Masakari включены в lab; для Masakari нужно отдельно решить, требуются ли host/instance monitors и HA cluster вне all-in-one стенда.
- TLS включён и проверен в lab с Kolla CA; production PKI/mTLS, rotation/revocation и hostname policy остаются E08/E09 gaps.
- Нужно назначить owners внешних IAM/PKI/SIEM/Vault(SecMan)/PAM/storage/network controls.
