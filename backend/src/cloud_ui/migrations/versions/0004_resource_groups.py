"""create resource group tables"""

import sqlalchemy as sa
from alembic import op

revision = "0004_resource_groups"
down_revision = "0003_inventory_read_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_groups",
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
    )
    op.create_index(
        "ix_resource_groups_owner_scope_name",
        "resource_groups",
        ["owner_subject_id", "scope_type", "scope_id", "deleted_at", "name", "group_id"],
    )
    op.create_table(
        "resource_group_members",
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
    )
    op.create_index(
        "ix_resource_group_members_group_page",
        "resource_group_members",
        ["group_id", "added_at", "resource_type", "cloud_id", "region_id", "resource_id"],
    )
    op.create_index(
        "ix_resource_group_members_resource_lookup",
        "resource_group_members",
        ["resource_type", "cloud_id", "region_id", "resource_id", "group_id"],
    )
    op.create_table(
        "resource_group_revisions",
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
    )
    op.create_index(
        "ix_resource_group_revisions_group_revision",
        "resource_group_revisions",
        ["group_id", "revision", "revision_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resource_group_revisions_group_revision",
        table_name="resource_group_revisions",
    )
    op.drop_table("resource_group_revisions")
    op.drop_index(
        "ix_resource_group_members_resource_lookup",
        table_name="resource_group_members",
    )
    op.drop_index(
        "ix_resource_group_members_group_page",
        table_name="resource_group_members",
    )
    op.drop_table("resource_group_members")
    op.drop_index("ix_resource_groups_owner_scope_name", table_name="resource_groups")
    op.drop_table("resource_groups")
