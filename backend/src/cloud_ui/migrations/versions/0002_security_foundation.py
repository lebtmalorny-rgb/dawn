"""create security foundation tables"""

import sqlalchemy as sa
from alembic import op

revision = "0002_security_foundation"
down_revision = "0001_schema_info"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("subject_id", sa.String(length=128), primary_key=True),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=128), primary_key=True),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("csrf_hash", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.subject_id"], ondelete="CASCADE"),
    )
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(length=128), primary_key=True),
        sa.Column("event_version", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "roles",
        sa.Column("role_id", sa.String(length=128), primary_key=True),
        sa.Column("role_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
    )
    op.create_table(
        "permissions",
        sa.Column("permission_id", sa.String(length=128), primary_key=True),
        sa.Column("description", sa.String(length=255), nullable=False),
    )
    op.create_table(
        "role_bindings",
        sa.Column("binding_id", sa.String(length=128), primary_key=True),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("role_id", sa.String(length=128), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.subject_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("role_bindings")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("audit_events")
    op.drop_table("sessions")
    op.drop_table("subjects")
