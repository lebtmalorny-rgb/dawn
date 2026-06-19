# Локальные инструкции Codex: deploy

Этот файл дополняет корневой `AGENTS.md`.

## Безопасная область

- Работать только с test inventory.
- Production hostnames, passwords, keys и inventory не добавлять.
- Команды deployment по умолчанию документировать/dry-run; реальный запуск только в явно предоставленной test среде.
- Не ослаблять SELinux, TLS, firewall или container permissions для прохождения smoke.

## Kolla

- Два custom image: frontend/backend.
- API, worker, events, migration используют один backend digest.
- Config и secrets отделены от image.
- Migration one-shot с lock/precheck.
- Role idempotent для deploy/reconfigure/upgrade/stop.
- HAProxy same-origin и health checks.
- DB/RabbitMQ least privilege.
- Registry uses digest, не latest.
- Rolling update совместим со schema/API.
- Rollback test обязателен до завершения E09.

## Container hardening

- non-root;
- minimal runtime;
- no compiler/package manager, где возможно;
- no socket/host root mount;
- drop capabilities;
- read-only root FS;
- controlled writable paths;
- SELinux labels;
- SBOM/scan/digest;
- no secrets in history/env output/log.

## Проверки

- render/inspect generated config;
- count containers;
- inspect user/caps/mounts;
- TLS scan;
- DB/MQ permission test;
- failure migration;
- reconfigure idempotency;
- rolling update/rollback;
- secret scan.

Не заявлять ДКБ-69 закрытым для Python backend без waiver.
