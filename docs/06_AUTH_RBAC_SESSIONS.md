# Аутентификация, RBAC и сессии

## Модель доверия

Портал не выдает корпоративную идентичность. Production flow использует корпоративный IdP и Keystone federation. Backend получает и хранит необходимый OpenStack security context на сервере. Browser имеет только opaque session cookie.

Локальная mock-аутентификация разрешена только в P0 и должна быть явно отключена production configuration.

## Два уровня авторизации

### OpenStack authorization

Keystone roles, scopes и policy сервисов решают, разрешена ли операция над OpenStack resource. Эта проверка окончательна.

### Portal authorization

Прикладные roles/capabilities решают, видна ли функция портала, можно ли использовать custom group, workflow или audit view. Portal permission может запретить действие, разрешенное OpenStack, но не может разрешить действие, запрещенное OpenStack.

## Рекомендуемая role model

Базовые функциональные роли уточняются в E00:

- `cloud_viewer`;
- `cloud_operator`;
- `tenant_admin`;
- `compute_operator`;
- `network_operator`;
- `image_operator`;
- `availability_operator`;
- `security_auditor`;
- `workflow_designer`;
- `portal_admin`.

Технологические identity отделены от human identity. Роль `service` не показывается как пользовательская.

### P0 role matrix E02

E02 реализует минимальную deterministic matrix для проверки portal RBAC без production identity:

| Роль | Тип subject | Capabilities | Назначение в P0 |
|---|---|---|---|
| `cloud_viewer` | human | `instance.read`, `hypervisor.read`, `group.read`, `operation.read` | read-only shell и проверка отсутствия mutating permissions |
| `cloud_operator` | human | `instance.read`, `hypervisor.read`, `group.read`, `operation.read`, `workflow.execute.maintenance-host` | happy path оператора и проверка, что portal allow не обходит OpenStack deny |
| `security_auditor` | human | `audit.read`, `operation.read` | аудит без mutating permissions |
| `portal_admin` | human | `audit.read`, `operation.read`, `role.manage` | проверка role-binding policy без `admin-all` shortcut |
| `service` | service only | определяется отдельным service identity | не назначается human subject; E02 API возвращает `403 service_role_for_human` |

Эта матрица является P0 test double. Production роли и группы должны приходить из корпоративного IdP/Keystone federation и подтверждаться IAM/PAM evidence.

## Scope

Permission оценивается минимум по:

- subject;
- system/domain/project scope;
- cloud/region;
- resource group;
- target ownership;
- action/workflow.

Scope не передается клиентом как доверенный факт. Backend выводит его из session и проверяемого target.

## Capability response

`GET /api/v1/capabilities` возвращает эффективные capabilities, например:

    {
      "scope": {"type": "system", "id": null},
      "capabilities": [
        "instance.read",
        "hypervisor.read",
        "group.read",
        "workflow.execute.evacuate-host"
      ],
      "expires_at": "...",
      "policy_revision": "..."
    }

Frontend использует ответ для UX. Любой mutating endpoint повторяет проверку.

## Сессии

### Требования

- opaque random ID;
- server-side storage;
- `HttpOnly`;
- `Secure` в интегрированной среде;
- `SameSite=Lax` или `Strict` по выбранному federation flow;
- CSRF token для state-changing request;
- idle timeout 900 секунд;
- absolute lifetime отдельно;
- configurable simultaneous-session limit;
- logout и административный revoke;
- rotation после login/elevation;
- audit login success/failure, logout, timeout, revoke.

### Ограничение одновременных сессий

Политика `deny` или `disconnect_oldest` конфигурируется. Изменение политики является security configuration и покрывается тестами. CLI/OpenStack token sessions находятся вне UI session registry и требуют политики IdP/Keystone.

E02 выбирает `deny` как default P0 policy: второй login того же subject отклоняется с безопасным `409 session_limit_reached` и audit event. `disconnect_oldest` оставлен как конфигурируемая политика для отдельного hardening/test cycle.

### Хранение OpenStack context

Предпочтение:

1. короткоживущий token в зашифрованном server-side session record;
2. refresh/re-auth в соответствии с federation flow;
3. минимальный срок хранения;
4. key material из Vault (SecMan) в production;
5. очистка при revoke/expiry.

Нельзя сериализовать token в browser, log, audit или RabbitMQ message.

## Проверка права на действие

Порядок:

1. аутентифицировать session;
2. проверить session expiry/revocation;
3. проверить CSRF и idempotency;
4. получить target из trusted read model/OpenStack;
5. проверить portal capability и scope;
6. вызвать OpenStack API с user context или утвержденной delegated model;
7. OpenStack policy выполняет окончательную проверку;
8. зафиксировать outcome в audit.

Shared service-admin credential для выполнения пользовательских действий запрещен, если нет отдельной утвержденной impersonation/delegation модели.

## Segregation of duties

ДКБ требует непересекающихся административных, технологических и внутренних ролей и запрет совмещения администратора. Основной enforcement выполняется IAM/IdP. Портал:

- не позволяет назначать service roles human user;
- валидирует известные конфликтующие role bindings;
- показывает источник binding;
- журналирует назначения;
- предоставляет отчет по конфликтам;
- не заявляет закрытие SoD без IAM evidence.

## UI-правила

- route guard и action visibility используют capability data;
- скрытая функция не доступна по прямому URL;
- 403 отображается без раскрытия existence защищенного ресурса там, где требуется;
- bulk action предварительно показывает, сколько targets доступно, запрещено или устарело;
- frontend не содержит hardcoded «admin means all».

## Обязательные отрицательные тесты

- user без capability не видит action;
- прямой HTTP request получает 403;
- изменение resource ID не дает доступ к чужому scope;
- истекшая/revoked session отклоняется;
- превышение session limit выполняет выбранную политику;
- CSRF отсутствует/неверен;
- tampered cursor/idempotency/target rejected;
- service role не назначается human subject;
- portal role не расширяет OpenStack 403;
- audit reader не получает mutating permissions.
