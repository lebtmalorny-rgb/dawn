from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine, RowMapping

from cloud_ui.groups import schema
from cloud_ui.groups.models import GroupMember, GroupNotFound, GroupRevisionConflict, ResourceGroup


class GroupRepository:
    def __init__(self, *, engine: Engine) -> None:
        self._engine = engine

    @property
    def engine(self) -> Engine:
        return self._engine

    def create_group(
        self,
        *,
        actor_id: str,
        scope_type: str,
        scope_id: str | None,
        name: str,
        description: str | None,
        resource_type: str,
        membership_mode: str,
    ) -> ResourceGroup:
        _validate_scope(scope_type, scope_id)
        now = _now()
        group_id = str(uuid4())
        row = {
            "group_id": group_id,
            "name": name,
            "description": description,
            "resource_type": resource_type,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "membership_mode": membership_mode,
            "rule_version": 1,
            "rule_body_json": None,
            "owner_subject_id": actor_id,
            "revision": 1,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }

        with self._engine.begin() as connection:
            connection.execute(schema.resource_groups.insert().values(row))
            _insert_revision(
                connection=connection,
                group_id=group_id,
                revision=1,
                actor_id=actor_id,
                change_type="group.created",
                change_json={
                    "name": name,
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "resource_type": resource_type,
                    "membership_mode": membership_mode,
                },
                created_at=now,
            )

        return _group_from_mapping(row)

    def get_group(self, group_id: str) -> ResourceGroup | None:
        statement = sa.select(schema.resource_groups).where(
            schema.resource_groups.c.group_id == group_id,
            schema.resource_groups.c.deleted_at.is_(None),
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        if row is None:
            return None
        return _group_from_mapping(row)

    def list_groups(
        self,
        *,
        actor_id: str,
        scope_type: str,
        scope_id: str | None,
        include_admin: bool,
        limit: int,
    ) -> list[ResourceGroup]:
        conditions = [
            schema.resource_groups.c.scope_type == scope_type,
            schema.resource_groups.c.deleted_at.is_(None),
        ]
        if scope_id is not None:
            conditions.append(schema.resource_groups.c.scope_id == scope_id)
        if not include_admin:
            conditions.append(schema.resource_groups.c.owner_subject_id == actor_id)

        statement = (
            sa.select(schema.resource_groups)
            .where(*conditions)
            .order_by(schema.resource_groups.c.name.asc(), schema.resource_groups.c.group_id.asc())
            .limit(_limit(limit))
        )
        with self._engine.connect() as connection:
            rows = list(connection.execute(statement).mappings())
        return [_group_from_mapping(row) for row in rows]

    def update_group(
        self,
        *,
        group_id: str,
        actor_id: str,
        expected_revision: int,
        name: str,
        description: str | None,
    ) -> ResourceGroup:
        now = _now()
        with self._engine.begin() as connection:
            current = _active_group_row(connection, group_id)
            if current is None:
                raise GroupNotFound(f"group not found: {group_id}")
            current_revision = int(current["revision"])
            if current_revision != expected_revision:
                raise GroupRevisionConflict(
                    f"group revision conflict: expected {expected_revision}, got {current_revision}"
                )

            next_revision = current_revision + 1
            result = connection.execute(
                schema.resource_groups.update()
                .where(
                    schema.resource_groups.c.group_id == group_id,
                    schema.resource_groups.c.revision == expected_revision,
                    schema.resource_groups.c.deleted_at.is_(None),
                )
                .values(
                    name=name,
                    description=description,
                    revision=next_revision,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                raise GroupRevisionConflict(
                    f"group revision conflict: expected {expected_revision}"
                )
            _insert_revision(
                connection=connection,
                group_id=group_id,
                revision=next_revision,
                actor_id=actor_id,
                change_type="group.updated",
                change_json={"name": name, "description": description},
                created_at=now,
            )
            updated = _active_group_row(connection, group_id)
            if updated is None:
                raise GroupNotFound(f"group not found: {group_id}")

        return _group_from_mapping(updated)

    def delete_group(self, *, group_id: str, actor_id: str) -> None:
        now = _now()
        with self._engine.begin() as connection:
            current = _active_group_row(connection, group_id)
            if current is None:
                raise GroupNotFound(f"group not found: {group_id}")
            next_revision = int(current["revision"]) + 1
            connection.execute(
                schema.resource_groups.update()
                .where(
                    schema.resource_groups.c.group_id == group_id,
                    schema.resource_groups.c.deleted_at.is_(None),
                )
                .values(
                    revision=next_revision,
                    updated_at=now,
                    deleted_at=now,
                )
            )
            _insert_revision(
                connection=connection,
                group_id=group_id,
                revision=next_revision,
                actor_id=actor_id,
                change_type="group.deleted",
                change_json={},
                created_at=now,
            )

    def add_member(
        self,
        *,
        group_id: str,
        resource_type: str,
        cloud_id: str,
        region_id: str,
        resource_id: str,
        source: str,
        actor_id: str,
    ) -> GroupMember:
        now = _now()
        with self._engine.begin() as connection:
            current = _active_group_row(connection, group_id)
            if current is None:
                raise GroupNotFound(f"group not found: {group_id}")

            existing = _member_row(
                connection=connection,
                group_id=group_id,
                resource_type=resource_type,
                cloud_id=cloud_id,
                region_id=region_id,
                resource_id=resource_id,
            )
            if existing is not None:
                return _member_from_mapping(existing)

            member = {
                "group_id": group_id,
                "resource_type": resource_type,
                "cloud_id": cloud_id,
                "region_id": region_id,
                "resource_id": resource_id,
                "source": source,
                "added_by": actor_id,
                "added_at": now,
                "expires_at": None,
            }
            connection.execute(schema.resource_group_members.insert().values(member))
            next_revision = int(current["revision"]) + 1
            _update_revision(
                connection=connection,
                group_id=group_id,
                revision=next_revision,
                updated_at=now,
            )
            _insert_revision(
                connection=connection,
                group_id=group_id,
                revision=next_revision,
                actor_id=actor_id,
                change_type="member.added",
                change_json=_member_key_json(member),
                created_at=now,
            )

        return _member_from_mapping(member)

    def remove_member(
        self,
        *,
        group_id: str,
        resource_type: str,
        cloud_id: str,
        region_id: str,
        resource_id: str,
        actor_id: str = "system",
    ) -> None:
        now = _now()
        with self._engine.begin() as connection:
            current = _active_group_row(connection, group_id)
            if current is None:
                raise GroupNotFound(f"group not found: {group_id}")

            result = connection.execute(
                schema.resource_group_members.delete().where(
                    schema.resource_group_members.c.group_id == group_id,
                    schema.resource_group_members.c.resource_type == resource_type,
                    schema.resource_group_members.c.cloud_id == cloud_id,
                    schema.resource_group_members.c.region_id == region_id,
                    schema.resource_group_members.c.resource_id == resource_id,
                )
            )
            if result.rowcount != 1:
                return

            next_revision = int(current["revision"]) + 1
            _update_revision(
                connection=connection,
                group_id=group_id,
                revision=next_revision,
                updated_at=now,
            )
            _insert_revision(
                connection=connection,
                group_id=group_id,
                revision=next_revision,
                actor_id=actor_id,
                change_type="member.removed",
                change_json={
                    "resource_type": resource_type,
                    "cloud_id": cloud_id,
                    "region_id": region_id,
                    "resource_id": resource_id,
                },
                created_at=now,
            )

    def list_members(self, group_id: str, *, limit: int) -> list[GroupMember]:
        statement = (
            sa.select(schema.resource_group_members)
            .where(schema.resource_group_members.c.group_id == group_id)
            .order_by(
                schema.resource_group_members.c.added_at.asc(),
                schema.resource_group_members.c.resource_type.asc(),
                schema.resource_group_members.c.cloud_id.asc(),
                schema.resource_group_members.c.region_id.asc(),
                schema.resource_group_members.c.resource_id.asc(),
            )
            .limit(_limit(limit))
        )
        with self._engine.connect() as connection:
            rows = list(connection.execute(statement).mappings())
        return [_member_from_mapping(row) for row in rows]


def _validate_scope(scope_type: str, scope_id: str | None) -> None:
    if scope_id is None or not scope_id.strip():
        raise ValueError(f"{scope_type} scope_id is required")


def _active_group_row(connection: Connection, group_id: str) -> RowMapping | None:
    return (
        connection.execute(
            sa.select(schema.resource_groups).where(
                schema.resource_groups.c.group_id == group_id,
                schema.resource_groups.c.deleted_at.is_(None),
            )
        )
        .mappings()
        .one_or_none()
    )


def _member_row(
    *,
    connection: Connection,
    group_id: str,
    resource_type: str,
    cloud_id: str,
    region_id: str,
    resource_id: str,
) -> RowMapping | None:
    return (
        connection.execute(
            sa.select(schema.resource_group_members).where(
                schema.resource_group_members.c.group_id == group_id,
                schema.resource_group_members.c.resource_type == resource_type,
                schema.resource_group_members.c.cloud_id == cloud_id,
                schema.resource_group_members.c.region_id == region_id,
                schema.resource_group_members.c.resource_id == resource_id,
            )
        )
        .mappings()
        .one_or_none()
    )


def _update_revision(
    *,
    connection: Connection,
    group_id: str,
    revision: int,
    updated_at: datetime,
) -> None:
    connection.execute(
        schema.resource_groups.update()
        .where(
            schema.resource_groups.c.group_id == group_id,
            schema.resource_groups.c.deleted_at.is_(None),
        )
        .values(revision=revision, updated_at=updated_at)
    )


def _insert_revision(
    *,
    connection: Connection,
    group_id: str,
    revision: int,
    actor_id: str,
    change_type: str,
    change_json: dict[str, Any],
    created_at: datetime,
) -> None:
    connection.execute(
        schema.resource_group_revisions.insert().values(
            revision_id=str(uuid4()),
            group_id=group_id,
            revision=revision,
            actor_id=actor_id,
            change_type=change_type,
            change_json=change_json,
            created_at=created_at,
        )
    )


def _group_from_mapping(row: RowMapping | dict[str, Any]) -> ResourceGroup:
    return ResourceGroup(
        group_id=str(row["group_id"]),
        name=str(row["name"]),
        description=_optional_string(row["description"]),
        resource_type=str(row["resource_type"]),
        scope_type=str(row["scope_type"]),
        scope_id=str(row["scope_id"]),
        membership_mode=str(row["membership_mode"]),
        rule_version=int(row["rule_version"]),
        rule_body_json=_optional_dict(row["rule_body_json"]),
        owner_subject_id=str(row["owner_subject_id"]),
        revision=int(row["revision"]),
        created_at=_as_utc(row["created_at"]),
        updated_at=_as_utc(row["updated_at"]),
        deleted_at=_optional_datetime(row["deleted_at"]),
    )


def _member_from_mapping(row: RowMapping | dict[str, Any]) -> GroupMember:
    return GroupMember(
        group_id=str(row["group_id"]),
        resource_type=str(row["resource_type"]),
        cloud_id=str(row["cloud_id"]),
        region_id=str(row["region_id"]),
        resource_id=str(row["resource_id"]),
        source=str(row["source"]),
        added_by=str(row["added_by"]),
        added_at=_as_utc(row["added_at"]),
        expires_at=_optional_datetime(row["expires_at"]),
    )


def _member_key_json(row: RowMapping | dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_type": str(row["resource_type"]),
        "cloud_id": str(row["cloud_id"]),
        "region_id": str(row["region_id"]),
        "resource_id": str(row["resource_id"]),
        "source": str(row["source"]),
    }


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("expected JSON object")
    return value


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return _as_utc(value)


def _as_utc(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _now() -> datetime:
    return datetime.now(UTC)


def _limit(limit: int) -> int:
    return max(1, limit)
