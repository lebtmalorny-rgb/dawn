# E08 — Security hardening, TLS/mTLS, Vault (SecMan) и supply chain

## Пользовательский результат

Команда получает hardened test candidate, формализованную матрицу TLS/mTLS, контракт с Vault (SecMan), воспроизводимый SBOM/scan и честный список требований ДКБ, которые требуют внешних мер или исключений.

## Входные критерии

- E07 принят.
- Доступны тестовые PKI/Vault(SecMan)/SIEM interfaces либо их официальные contracts.
- Утвержден owner каждого secret class.
- Определена корпоративная политика vulnerability severity/exception.

## Прочитать

- `docs/10_SECURITY_DKB.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- `docs/12_DEPLOY_ROCKY_KOLLA.md`;
- `docs/13_TEST_STRATEGY.md`;
- `docs/15_DECISIONS_AND_OPEN_QUESTIONS.md`.

## Единицы работы

### E08.1. Threat model review

Обновить assets/trust boundaries/threats по фактическому коду. Связать mitigations с tests/config и выявить high risks.

### E08.2. TLS/mTLS implementation plan

Заполнить `docs/generated/tls-matrix.md` для всех flows. Для test environment реализовать HTTPS и выбранные mTLS flows с hostname/certificate/authorization checks. Отрицательные тесты обязательны.

### E08.3. Secret inventory и adapter

Заполнить lifecycle каждого secret: store, issue, inject, cache, rotate, revoke, break-glass, audit. Реализовать interface/test adapter к Vault (SecMan) без real secret в Git.

### E08.4. Session/token protection

Проверить encryption/signing key lifecycle, token retention, memory/log/message leakage и revoke behavior.

### E08.5. Container hardening

Убрать build tools/package managers из runtime, запустить non-root, drop caps, read-only FS, safe tmp, no socket/host mounts. Проверить SELinux labels на Rocky test host.

### E08.6. Supply chain

Pinned dependencies/base digest, SBOM, vulnerability scan, secret scan, license inventory при необходимости, image provenance/signing test.

### E08.7. DKB gaps/waivers

Создать draft gaps для ДКБ-07, 22.02, 48, 50, 55, 56, 65, 69, 72 и других external requirements. Для каждого: причина, compensating controls, owner, expiry/review.

### E08.8. Security review

Использовать `templates/SECURITY_REVIEW_TEMPLATE.md`, исправить critical/high findings или заблокировать release.

## Acceptance

- TLS >=1.2 доказан test scan;
- mTLS negative case отклоняется;
- no token/secret in browser/log/message/image layers;
- Vault adapter contract/retry/redaction tested;
- runtime images non-root/minimal;
- SBOM generated and tied to digest;
- vulnerability policy evaluated;
- SELinux test result saved or explicit blocker;
- DKB-69 conflict documented, not hidden;
- security review has no unresolved critical/high for P2;
- external gaps have owner.

## Затронутые ДКБ

Основные: 07, 13, 22.02, 23.02, 24, 25, 42–44, 48, 51, 55, 56, 65, 69, 70, 76, 77, 80. Network deployment evidence окончательно появляется в E09.

## Не делать

- хранить Vault token в image/env file Git;
- отключать verification;
- разрешать wildcard network ради теста;
- заявлять DKB-69 закрытым для Python backend;
- исправлять scan удалением необходимого security package без анализа;
- подключать production Vault (SecMan).

## Итоговый запрос Codex

> Выполни E08 как hardening и evidence этап. Не подменяй внешнюю интеграцию mock-ом в статусе. Для каждого gap укажи compensating control и owner. Critical/high finding блокирует переход к E09.
