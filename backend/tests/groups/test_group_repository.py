from __future__ import annotations

import inspect
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.dml import Insert, Update

from cloud_ui.groups import schema
from cloud_ui.groups.models import GroupNotFound, GroupRevisionConflict
from cloud_ui.groups.repository import GroupRepository


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    schema.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> GroupRepository:
    return GroupRepository(engine=engine)


def test_group_crud_soft_delete_and_revision_conflict(repository: GroupRepository) -> None:
    created = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="prod-vms",
        description="Production VMs",
        resource_type="vm",
        membership_mode="explicit",
    )

    updated = repository.update_group(
        group_id=created.group_id,
        actor_id="mock-user-operator",
        expected_revision=created.revision,
        name="prod-vms-renamed",
        description="Renamed",
    )

    assert updated.revision == created.revision + 1
    with pytest.raises(GroupRevisionConflict):
        repository.update_group(
            group_id=created.group_id,
            actor_id="mock-user-operator",
            expected_revision=created.revision,
            name="stale",
            description="stale",
        )

    repository.delete_group(group_id=created.group_id, actor_id="mock-user-operator")
    assert repository.get_group(created.group_id) is None


def test_membership_add_remove_is_idempotent(repository: GroupRepository) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )

    first = repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    second = repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )

    assert first == second
    assert [member.resource_id for member in repository.list_members(group.group_id, limit=50)] == [
        "instance-0001"
    ]

    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        actor_id="mock-user-operator",
    )
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        actor_id="mock-user-operator",
    )
    assert repository.list_members(group.group_id, limit=50) == []


def test_list_groups_returns_owner_scope_and_admin_views(repository: GroupRepository) -> None:
    owned = repository.create_group(
        actor_id="operator-a",
        scope_type="project",
        scope_id="project-a",
        name="owned",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    repository.create_group(
        actor_id="operator-a",
        scope_type="project",
        scope_id="project-b",
        name="other-scope",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    admin_visible = repository.create_group(
        actor_id="operator-b",
        scope_type="project",
        scope_id="project-a",
        name="admin-visible",
        description=None,
        resource_type="host",
        membership_mode="explicit",
    )

    owner_page = repository.list_groups(
        actor_id="operator-a",
        scope_type="project",
        scope_id="project-a",
        include_admin=False,
        limit=50,
    )
    admin_page = repository.list_groups(
        actor_id="portal-admin",
        scope_type="project",
        scope_id="project-a",
        include_admin=True,
        limit=50,
    )
    system_page = repository.list_groups(
        actor_id="portal-admin",
        scope_type="project",
        scope_id=None,
        include_admin=True,
        limit=50,
    )

    assert [group.group_id for group in owner_page] == [owned.group_id]
    assert [group.group_id for group in admin_page] == [
        admin_visible.group_id,
        owned.group_id,
    ]
    assert {group.scope_id for group in system_page} == {"project-a", "project-b"}


def test_repository_rejects_group_without_project_scope_id(repository: GroupRepository) -> None:
    with pytest.raises(ValueError, match="project scope_id"):
        repository.create_group(
            actor_id="mock-user-operator",
            scope_type="project",
            scope_id=None,
            name="invalid",
            description=None,
            resource_type="vm",
            membership_mode="explicit",
        )


def test_membership_changes_increment_revision_only_when_state_changes(
    repository: GroupRepository,
) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )

    repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    after_first_add = repository.get_group(group.group_id)
    repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    after_second_add = repository.get_group(group.group_id)

    assert after_first_add is not None
    assert after_second_add is not None
    assert after_first_add.revision == group.revision + 1
    assert after_second_add.revision == after_first_add.revision

    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        actor_id="mock-user-operator",
    )
    after_first_remove = repository.get_group(group.group_id)
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        actor_id="mock-user-operator",
    )
    after_second_remove = repository.get_group(group.group_id)

    assert after_first_remove is not None
    assert after_second_remove is not None
    assert after_first_remove.revision == after_first_add.revision + 1
    assert after_second_remove.revision == after_first_remove.revision


def test_revision_history_records_create_update_member_changes_delete(
    repository: GroupRepository,
    engine: Engine,
) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    repository.update_group(
        group_id=group.group_id,
        actor_id="mock-user-operator",
        expected_revision=group.revision,
        name="tenant-a-renamed",
        description="Renamed",
    )
    repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        actor_id="mock-user-operator",
    )
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        actor_id="mock-user-operator",
    )
    repository.delete_group(group_id=group.group_id, actor_id="mock-user-operator")

    rows = _revision_rows(engine, group.group_id)

    assert [row["revision"] for row in rows] == [1, 2, 3, 4, 5]
    assert [row["change_type"] for row in rows] == [
        "group.created",
        "group.updated",
        "member.added",
        "member.removed",
        "group.deleted",
    ]
    assert len({row["revision"] for row in rows}) == len(rows)


def test_list_members_is_stably_ordered_by_added_at_and_key(
    repository: GroupRepository,
    engine: Engine,
) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="mixed",
        membership_mode="explicit",
    )
    added_at = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            schema.resource_group_members.insert(),
            [
                _member_row(group.group_id, "vm", "instance-0002", added_at),
                _member_row(group.group_id, "host", "compute-0001", added_at),
                _member_row(group.group_id, "vm", "instance-0001", added_at),
            ],
        )

    members = repository.list_members(group.group_id, limit=50)

    assert [
        (member.resource_type, member.cloud_id, member.region_id, member.resource_id)
        for member in members
    ] == [
        ("host", "dev-cloud", "RegionOne", "compute-0001"),
        ("vm", "dev-cloud", "RegionOne", "instance-0001"),
        ("vm", "dev-cloud", "RegionOne", "instance-0002"),
    ]


def test_add_member_rejects_competing_revision_update(
    repository: GroupRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    _install_competing_group_revision_update(
        monkeypatch=monkeypatch,
        group_id=group.group_id,
        next_revision=group.revision + 1,
    )

    with pytest.raises(GroupRevisionConflict):
        repository.add_member(
            group_id=group.group_id,
            resource_type="vm",
            cloud_id="dev-cloud",
            region_id="RegionOne",
            resource_id="instance-0001",
            source="explicit",
            actor_id="mock-user-operator",
        )

    assert repository.list_members(group.group_id, limit=50) == []


def test_remove_member_rejects_competing_revision_update(
    repository: GroupRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    member = repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    updated_group = repository.get_group(group.group_id)
    assert updated_group is not None
    _install_competing_group_revision_update(
        monkeypatch=monkeypatch,
        group_id=group.group_id,
        next_revision=updated_group.revision + 1,
    )

    with pytest.raises(GroupRevisionConflict):
        repository.remove_member(
            group_id=group.group_id,
            resource_type=member.resource_type,
            cloud_id=member.cloud_id,
            region_id=member.region_id,
            resource_id=member.resource_id,
            actor_id="mock-user-operator",
        )

    assert repository.list_members(group.group_id, limit=50) == [member]


def test_add_member_returns_existing_member_after_duplicate_insert_race(
    repository: GroupRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    original_execute = Connection.execute
    duplicate_injected = False

    def execute_with_duplicate_member(
        self: Connection,
        statement: Any,
        parameters: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal duplicate_injected
        if (
            not duplicate_injected
            and _is_insert_for(statement, schema.resource_group_members)
        ):
            duplicate_injected = True
            _execute_original(original_execute, self, statement, parameters, args, kwargs)
            _execute_original(
                original_execute,
                self,
                schema.resource_groups.update()
                .where(schema.resource_groups.c.group_id == group.group_id)
                .values(
                    revision=group.revision + 1,
                    updated_at=datetime(2026, 6, 22, 11, 0, tzinfo=UTC),
                ),
                None,
                (),
                {},
            )
            _execute_original(
                original_execute,
                self,
                schema.resource_group_revisions.insert().values(
                    revision_id="competing-member-add",
                    group_id=group.group_id,
                    revision=group.revision + 1,
                    actor_id="mock-user-operator",
                    change_type="member.added",
                    change_json={
                        "resource_type": "vm",
                        "cloud_id": "dev-cloud",
                        "region_id": "RegionOne",
                        "resource_id": "instance-0001",
                        "source": "explicit",
                    },
                    created_at=datetime(2026, 6, 22, 11, 0, tzinfo=UTC),
                ),
                None,
                (),
                {},
            )
            raise sa.exc.IntegrityError(
                statement=str(statement),
                params=parameters,
                orig=Exception("duplicate resource_group_members key"),
            )
        return _execute_original(original_execute, self, statement, parameters, args, kwargs)

    monkeypatch.setattr(Connection, "execute", execute_with_duplicate_member)

    member = repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )

    assert duplicate_injected is True
    assert member.resource_id == "instance-0001"
    assert repository.list_members(group.group_id, limit=50) == [member]
    updated_group = repository.get_group(group.group_id)
    assert updated_group is not None
    assert updated_group.revision == group.revision + 1


def test_add_member_reraises_unrelated_integrity_error(
    repository: GroupRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    original_execute = Connection.execute

    def execute_with_unrelated_integrity_error(
        self: Connection,
        statement: Any,
        parameters: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if _is_insert_for(statement, schema.resource_group_members):
            raise sa.exc.IntegrityError(
                statement=str(statement),
                params=parameters,
                orig=Exception("unrelated integrity failure"),
            )
        return _execute_original(original_execute, self, statement, parameters, args, kwargs)

    monkeypatch.setattr(Connection, "execute", execute_with_unrelated_integrity_error)

    with pytest.raises(sa.exc.IntegrityError):
        repository.add_member(
            group_id=group.group_id,
            resource_type="vm",
            cloud_id="dev-cloud",
            region_id="RegionOne",
            resource_id="instance-0001",
            source="explicit",
            actor_id="mock-user-operator",
        )


def test_list_members_rejects_missing_or_deleted_group(repository: GroupRepository) -> None:
    with pytest.raises(GroupNotFound):
        repository.list_members("missing-group", limit=50)

    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )
    repository.delete_group(group_id=group.group_id, actor_id="mock-user-operator")

    with pytest.raises(GroupNotFound):
        repository.list_members(group.group_id, limit=50)


def test_remove_member_requires_explicit_actor_id() -> None:
    actor_parameter = inspect.signature(GroupRepository.remove_member).parameters["actor_id"]

    assert actor_parameter.default is inspect.Parameter.empty


def _revision_rows(engine: Engine, group_id: str) -> list[dict[str, Any]]:
    statement = (
        sa.select(schema.resource_group_revisions)
        .where(schema.resource_group_revisions.c.group_id == group_id)
        .order_by(
            schema.resource_group_revisions.c.revision.asc(),
            schema.resource_group_revisions.c.revision_id.asc(),
        )
    )
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(statement).mappings()]


def _member_row(
    group_id: str,
    resource_type: str,
    resource_id: str,
    added_at: datetime,
) -> dict[str, Any]:
    return {
        "group_id": group_id,
        "resource_type": resource_type,
        "cloud_id": "dev-cloud",
        "region_id": "RegionOne",
        "resource_id": resource_id,
        "source": "explicit",
        "added_by": "mock-user-operator",
        "added_at": added_at,
        "expires_at": None,
    }


def _install_competing_group_revision_update(
    *,
    monkeypatch: pytest.MonkeyPatch,
    group_id: str,
    next_revision: int,
) -> None:
    original_execute = Connection.execute
    competing_update_done = False

    def execute_with_competing_revision_update(
        self: Connection,
        statement: Any,
        parameters: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal competing_update_done
        if (
            not competing_update_done
            and _is_update_for(statement, schema.resource_groups)
        ):
            competing_update_done = True
            _execute_original(
                original_execute,
                self,
                schema.resource_groups.update()
                .where(schema.resource_groups.c.group_id == group_id)
                .values(
                    revision=next_revision,
                    updated_at=datetime(2026, 6, 22, 11, 0, tzinfo=UTC),
                ),
                None,
                (),
                {},
            )
        return _execute_original(original_execute, self, statement, parameters, args, kwargs)

    monkeypatch.setattr(Connection, "execute", execute_with_competing_revision_update)


def _is_insert_for(statement: Any, table: sa.Table) -> bool:
    return isinstance(statement, Insert) and statement.table.name == table.name


def _is_update_for(statement: Any, table: sa.Table) -> bool:
    return isinstance(statement, Update) and statement.table.name == table.name


def _execute_original(
    original_execute: Any,
    connection: Connection,
    statement: Any,
    parameters: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    if parameters is None:
        return original_execute(connection, statement, *args, **kwargs)
    return original_execute(connection, statement, parameters, *args, **kwargs)
