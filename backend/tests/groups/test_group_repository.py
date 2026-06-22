from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.groups import schema
from cloud_ui.groups.models import GroupRevisionConflict
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
    )
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
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
    )
    after_first_remove = repository.get_group(group.group_id)
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
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
    )
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
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
