# E02 — Security foundation: аутентификация, сессии и RBAC

## Пользовательский результат

Пользователь входит через mock identity в P0 и через утвержденный test identity flow в P1, получает server-side session, видит только разрешенные разделы, а прямой запрещенный API request получает 403 и audit event.

## Входные критерии

- E01 принят.
- Authentication ADR принят либо test adapter четко отделен.
- Выбрана session limit policy.
- Определена начальная role matrix.

## Прочитать

- `docs/06_AUTH_RBAC_SESSIONS.md`;
- `docs/08_AUDIT_OBSERVABILITY.md`;
- `docs/10_SECURITY_DKB.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- `docs/13_TEST_STRATEGY.md`.

## Единицы работы

### E02.1. Identity interfaces

Создать provider interface и две реализации:

- deterministic mock для P0;
- test federation/Keystone adapter согласно ADR, если среда доступна.

Mock hard-disabled production config.

### E02.2. Server-side sessions

Добавить schema/migrations, opaque cookie, idle/absolute expiry, rotation, logout, revoke и simultaneous-session policy. OpenStack context не попадает в browser.

### E02.3. CSRF и headers

Защитить mutating portal endpoints, настроить trusted proxy/origin behavior и security headers для local/test mode.

### E02.4. Portal RBAC

Добавить permissions, roles, bindings, scopes и policy service. Создать seed roles без hardcoded admin-all. Service role нельзя назначить human subject.

### E02.5. Capabilities API

Реализовать session/capabilities endpoints. Frontend route/action guard использует capabilities, но backend выполняет повторную проверку.

### E02.6. Audit baseline

Фиксировать login success/failure, logout, timeout, revoke, session-limit и authorization denial с mandatory fields и redaction.

### E02.7. Negative tests

Реализовать полную матрицу из `docs/06_AUTH_RBAC_SESSIONS.md`.

## Acceptance

- token отсутствует в storage/assets/network response browser.
- Idle timeout по умолчанию 900 секунд.
- Session limit policy тестируется.
- CSRF отклоняет неверный request.
- UI скрывает запрещенный route/action.
- Прямой request получает 403.
- Portal allow не обходит simulated OpenStack deny.
- Все auth events имеют audit record.
- Mock login невозможно включить production profile случайно.
- Role matrix и DKB evidence обновлены.

## Затронутые ДКБ

Основные: ДКБ-01–07, 12, 13, 15, 20, 21. ДКБ-04/05/07 требуют внешнего IAM/PAM evidence и не считаются полностью закрытыми.

## Не делать

- реальные mutating OpenStack actions;
- custom workflow;
- admin UI для произвольного policy expression;
- shared service-admin impersonation.

## Итоговый запрос Codex

> Выполни E02 security-first. Сначала policy/session contracts и отрицательные тесты, затем UI. Не считай скрытие UI авторизацией. Обнови DKB traceability с разделением portal/IAM/PAM.
