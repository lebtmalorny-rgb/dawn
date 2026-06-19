# Локальные инструкции Codex: security и ДКБ

Этот файл дополняет корневой `AGENTS.md`.

## Основное правило

Не присваивай финальный статус соответствия. Твоя задача — найти доказательства, пробелы и неподтвержденные claims.

## Проверка требования

Для каждого ДКБ-кода различай:

1. код портала;
2. конфигурацию OpenStack/Kolla/Rocky;
3. автоматический/ручной test;
4. внешний корпоративный control;
5. эксплуатационный регламент;
6. waiver/gap.

Отсутствие одного слоя нельзя скрывать формулировкой «поддерживается».

## Обязательные проверки

- UI hide + backend deny;
- least privilege и scope;
- SoD external evidence;
- session timeout/limit/revoke;
- TLS/mTLS positive and negative;
- secret lifecycle;
- audit fields/redaction/delivery/heartbeat;
- no direct DB/broker/index access;
- workflow allowlist/idempotency;
- container/SELinux/supply chain;
- HA failover, не только replicas;
- unused API technical blocking;
- storage/backup/guest OS external boundary.

## Особые конфликты

- ДКБ-07: service accounts нужны OpenStack.
- ДКБ-56: all secrets rotation требует deployment pipeline.
- ДКБ-65: нужен фактический host SELinux/AppArmor evidence.
- ДКБ-69: Python interpreter необходим backend.
- ДКБ-72: зависит от storage architecture.
- ДКБ-76: неполное исходное требование.

## Evidence hygiene

- no secrets/PII/business data;
- exact commit/image/config/environment/date;
- reproducible command;
- expected/actual result;
- negative scenario;
- owner/reviewer;
- expiry для waiver.

Используй `templates/SECURITY_REVIEW_TEMPLATE.md` и `templates/DKB_EVIDENCE_TEMPLATE.md`.
