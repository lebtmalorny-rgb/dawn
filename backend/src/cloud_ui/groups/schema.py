from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()

resource_groups = sa.Table(
    "resource_groups",
    metadata,
    sa.Column("group_id", sa.String(length=128), nullable=False),
    sa.Column("name", sa.String(length=255), nullable=False),
    sa.Column("description", sa.String(length=1024), nullable=True),
    sa.Column("resource_type", sa.String(length=32), nullable=False),
    sa.Column("scope_type", sa.String(length=32), nullable=False),
    sa.Column("scope_id", sa.String(length=128), nullable=False),
    sa.Column("membership_mode", sa.String(length=32), nullable=False),
    sa.Column("rule_version", sa.Integer(), nullable=False),
    sa.Column("rule_body_json", sa.JSON(), nullable=True),
    sa.Column("owner_subject_id", sa.String(length=128), nullable=False),
    sa.Column("revision", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint("group_id"),
    sa.Index(
        "ix_resource_groups_owner_scope_name",
        "owner_subject_id",
        "scope_type",
        "scope_id",
        "deleted_at",
        "name",
        "group_id",
    ),
)

resource_group_members = sa.Table(
    "resource_group_members",
    metadata,
    sa.Column("group_id", sa.String(length=128), nullable=False),
    sa.Column("resource_type", sa.String(length=32), nullable=False),
    sa.Column("cloud_id", sa.String(length=128), nullable=False),
    sa.Column("region_id", sa.String(length=128), nullable=False),
    sa.Column("resource_id", sa.String(length=128), nullable=False),
    sa.Column("source", sa.String(length=32), nullable=False),
    sa.Column("added_by", sa.String(length=128), nullable=False),
    sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint(
        "group_id",
        "resource_type",
        "cloud_id",
        "region_id",
        "resource_id",
    ),
    sa.ForeignKeyConstraint(
        ["group_id"],
        ["resource_groups.group_id"],
        ondelete="CASCADE",
    ),
    sa.Index(
        "ix_resource_group_members_group_page",
        "group_id",
        "resource_type",
        "cloud_id",
        "region_id",
        "resource_id",
    ),
    sa.Index(
        "ix_resource_group_members_resource_lookup",
        "resource_type",
        "cloud_id",
        "region_id",
        "resource_id",
        "group_id",
    ),
)

resource_group_revisions = sa.Table(
    "resource_group_revisions",
    metadata,
    sa.Column("revision_id", sa.String(length=128), nullable=False),
    sa.Column("group_id", sa.String(length=128), nullable=False),
    sa.Column("revision", sa.Integer(), nullable=False),
    sa.Column("actor_id", sa.String(length=128), nullable=False),
    sa.Column("change_type", sa.String(length=64), nullable=False),
    sa.Column("change_json", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("revision_id"),
    sa.ForeignKeyConstraint(
        ["group_id"],
        ["resource_groups.group_id"],
        ondelete="CASCADE",
    ),
    sa.Index(
        "ix_resource_group_revisions_group_revision",
        "group_id",
        "revision",
        "revision_id",
    ),
)
