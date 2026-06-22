from __future__ import annotations

from dataclasses import dataclass

from cloud_ui.security.identity import (
    AuthenticationFailed,
    IdentityProvider,
    LoginRequest,
    LoginResult,
    Subject,
)


@dataclass(frozen=True)
class _MockSubjectRecord:
    login: str
    expected_credential: str
    subject: Subject


class MockIdentityProvider(IdentityProvider):
    def __init__(self, records: list[_MockSubjectRecord]) -> None:
        self._records = {record.login: record for record in records}

    def authenticate(self, request: LoginRequest) -> LoginResult:
        record = self._records.get(request.login)
        if record is None or record.expected_credential != request.credential:
            raise AuthenticationFailed("Invalid mock identity credentials")

        return LoginResult(subject=record.subject, authentication_method="mock")


def build_mock_identity_provider() -> MockIdentityProvider:
    return MockIdentityProvider(
        [
            _MockSubjectRecord(
                login="viewer",
                expected_credential="viewer-code",
                subject=Subject(
                    subject_id="mock-user-viewer",
                    display_name="Наблюдатель облака",
                    subject_type="human",
                    scope_type="project",
                    scope_id="project-a",
                    roles=frozenset({"cloud_viewer"}),
                    capabilities=frozenset(
                        {
                            "instance.read",
                            "hypervisor.read",
                            "group.read",
                            "operation.read",
                        }
                    ),
                ),
            ),
            _MockSubjectRecord(
                login="operator",
                expected_credential="operator-code",
                subject=Subject(
                    subject_id="mock-user-operator",
                    display_name="Оператор облака",
                    subject_type="human",
                    scope_type="project",
                    scope_id="project-a",
                    roles=frozenset({"cloud_operator"}),
                    capabilities=frozenset(
                        {
                            "instance.read",
                            "hypervisor.read",
                            "group.read",
                            "group.manage",
                            "operation.read",
                            "instance.refresh",
                            "workflow.execute.maintenance-host",
                        }
                    ),
                ),
            ),
            _MockSubjectRecord(
                login="auditor",
                expected_credential="auditor-code",
                subject=Subject(
                    subject_id="mock-user-auditor",
                    display_name="Аудитор безопасности",
                    subject_type="human",
                    scope_type="system",
                    scope_id=None,
                    roles=frozenset({"security_auditor"}),
                    capabilities=frozenset({"audit.read", "operation.read"}),
                ),
            ),
            _MockSubjectRecord(
                login="admin",
                expected_credential="admin-code",
                subject=Subject(
                    subject_id="mock-user-admin",
                    display_name="Администратор портала",
                    subject_type="human",
                    scope_type="system",
                    scope_id=None,
                    roles=frozenset({"portal_admin"}),
                    capabilities=frozenset(
                        {
                            "audit.read",
                            "instance.read",
                            "instance.refresh",
                            "hypervisor.read",
                            "group.read",
                            "group.manage",
                            "operation.read",
                            "role.manage",
                            "session.manage",
                        }
                    ),
                ),
            ),
        ]
    )
