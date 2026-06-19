# Источники

## Исходный анализ ДКБ

- Пользовательский файл `aнализ ДКБ.xlsx` (первая буква имени — латинская `a`), листы `Сводка`, `Матрица`, `Риски`, `Источники`.
- SHA-256 исходного файла: `a41babf82b628bda275bc6bb086aa52c8be67fe71c3360b8f2c68c099544046d`.
- На момент формирования комплекта из листа `Матрица` извлечено 73 требования; исходный файл остается первичным источником формулировок.

## OpenStack и Kolla

| Название | URL | Назначение |
|---|---|---|
| OpenStack Epoxy release | https://releases.openstack.org/epoxy/index.html | Официальная документация / подтверждение возможностей |
| OpenStack docs overview | https://docs.openstack.org/2025.1/ | Официальная документация / подтверждение возможностей |
| Keystone default roles/RBAC | https://docs.openstack.org/keystone/latest/admin/service-api-protection.html | Официальная документация / подтверждение возможностей |
| Keystone federation | https://docs.openstack.org/keystone/2025.1/admin/federation/introduction.html | Официальная документация / подтверждение возможностей |
| Keystone LDAP | https://docs.openstack.org/keystone/2025.1/admin/configuration.html#integrate-identity-with-ldap | Официальная документация / подтверждение возможностей |
| Keystone OAuth2 mTLS | https://docs.openstack.org/keystone/2025.1/admin/oauth2-mtls-usage-guide.html | Официальная документация / подтверждение возможностей |
| Neutron RBAC | https://docs.openstack.org/neutron/2025.1/admin/config-rbac.html | Официальная документация / подтверждение возможностей |
| Horizon settings | https://docs.openstack.org/horizon/latest/configuration/settings.html | Официальная документация / подтверждение возможностей |
| OpenStack Security Guide TLS | https://docs.openstack.org/security-guide/secure-communication/tls-proxies-and-http-services.html | Официальная документация / подтверждение возможностей |
| Kolla-Ansible TLS | https://docs.openstack.org/kolla-ansible/2025.1/admin/tls.html | Официальная документация / подтверждение возможностей |
| Kolla-Ansible production architecture | https://docs.openstack.org/kolla-ansible/2025.1/admin/production-architecture-guide.html | Официальная документация / подтверждение возможностей |
| Kolla-Ansible HAProxy/Keepalived | https://docs.openstack.org/kolla-ansible/2025.1/reference/high-availability/haproxy-guide.html | Официальная документация / подтверждение возможностей |
| Keystonemiddleware audit | https://docs.openstack.org/keystonemiddleware/2025.1/audit.html | Официальная документация / подтверждение возможностей |
| Keystone event notifications | https://docs.openstack.org/keystone/2025.1/admin/event_notifications.html | Официальная документация / подтверждение возможностей |
| oslo.log configuration | https://docs.openstack.org/oslo.log/2025.1/configuration/ | Официальная документация / подтверждение возможностей |
| Barbican security guide | https://docs.openstack.org/security-guide/secrets-management/barbican.html | Официальная документация / подтверждение возможностей |
| Barbican plugin backends | https://docs.openstack.org/barbican/2025.1/configuration/plugin_backends.html | Официальная документация / подтверждение возможностей |
| Kolla release notes | https://docs.openstack.org/releasenotes/kolla/2025.1.html | Официальная документация / подтверждение возможностей |
| Kolla image build/local registry | https://docs.openstack.org/kolla/2025.1/admin/image-building.html | Официальная документация / подтверждение возможностей |
| Nova host aggregates | https://docs.openstack.org/nova/2025.1/admin/aggregates | Официальная документация / подтверждение возможностей |
| Nova sample config/storage paths | https://docs.openstack.org/nova/2025.1/configuration/sample-config.html | Официальная документация / подтверждение возможностей |
| OpenStack Security Guide sVirt/SELinux/AppArmor | https://docs.openstack.org/security-guide/compute/hardening-the-virtualization-layers.html | Официальная документация / подтверждение возможностей |

## Codex

- https://developers.openai.com/codex/learn/best-practices — структура задания, Plan mode, тестирование и review.
- https://developers.openai.com/codex/guides/agents-md — загрузка и layering `AGENTS.md`.
- https://developers.openai.com/codex/permissions — ограничение filesystem/network permissions.
- https://developers.openai.com/cookbook/articles/codex_exec_plans — живые ExecPlans и `PLANS.md`.

## Правила использования источников

- При реализации сверять документацию с фактической версией OpenStack/Kolla в test environment.
- Для технических решений использовать официальную документацию и исходный код upstream.
- В ADR фиксировать конкретную версию/microversion и дату проверки.
- Не копировать в репозиторий production payload, token или закрытую документацию.
