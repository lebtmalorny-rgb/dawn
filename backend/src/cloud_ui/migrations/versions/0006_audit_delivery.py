"""expand audit events with delivery outbox"""

import sqlalchemy as sa
from alembic import op

revision = "0006_audit_delivery"
down_revision = "0005_operations"
branch_labels = None
depends_on = None

AUDIT_EVENT_COLUMNS = [
    sa.Column("actor_display", sa.String(length=255), nullable=True),
    sa.Column("authentication_method", sa.String(length=64), nullable=True),
    sa.Column("session_reference", sa.String(length=128), nullable=True),
    sa.Column("cloud_id", sa.String(length=128), nullable=True),
    sa.Column("region_id", sa.String(length=128), nullable=True),
    sa.Column("project_id", sa.String(length=128), nullable=True),
    sa.Column("scope_type", sa.String(length=32), nullable=True),
    sa.Column("scope_id", sa.String(length=128), nullable=True),
    sa.Column("source_ip", sa.String(length=64), nullable=True),
    sa.Column("trusted_proxy_chain_json", sa.JSON(), nullable=True),
    sa.Column("operation_id", sa.String(length=128), nullable=True),
    sa.Column("external_execution_id", sa.String(length=128), nullable=True),
    sa.Column("component", sa.String(length=64), nullable=True),
    sa.Column("safe_error_code", sa.String(length=128), nullable=True),
    sa.Column("delivery_state", sa.String(length=32), nullable=True),
    sa.Column("event_hash", sa.String(length=128), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
]


def upgrade() -> None:
    for column in AUDIT_EVENT_COLUMNS:
        op.add_column("audit_events", column)

    op.create_table(
        "audit_outbox",
        sa.Column("outbox_id", sa.String(length=160), primary_key=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("sink_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("not_before_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("envelope_json", sa.JSON(), nullable=False),
        sa.Column("event_hash", sa.String(length=128), nullable=False),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sink_message_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["audit_events.event_id"], ondelete="CASCADE"),
    )
    op.create_table(
        "audit_delivery_attempts",
        sa.Column("attempt_id", sa.String(length=160), primary_key=True),
        sa.Column("outbox_id", sa.String(length=160), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("sink_id", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("safe_error_code", sa.String(length=128), nullable=True),
        sa.Column("ack_id", sa.String(length=128), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["outbox_id"], ["audit_outbox.outbox_id"], ondelete="CASCADE"),
    )
    op.create_table(
        "audit_heartbeats",
        sa.Column("sink_id", sa.String(length=64), primary_key=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("queue_depth", sa.Integer(), nullable=False),
        sa.Column("oldest_pending_age_seconds", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_audit_events_occurred_event",
        "audit_events",
        ["occurred_at", "event_id"],
    )
    op.create_index(
        "ix_audit_events_action_occurred",
        "audit_events",
        ["action", "occurred_at"],
    )
    op.create_index("ix_audit_events_correlation", "audit_events", ["correlation_id"])
    op.create_index(
        "ix_audit_outbox_state_not_before",
        "audit_outbox",
        ["state", "not_before_at", "outbox_id"],
    )
    op.create_index(
        "ix_audit_delivery_attempts_outbox_created",
        "audit_delivery_attempts",
        ["outbox_id", "created_at", "attempt_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audit_delivery_attempts_outbox_created",
        table_name="audit_delivery_attempts",
    )
    op.drop_index("ix_audit_outbox_state_not_before", table_name="audit_outbox")
    op.drop_index("ix_audit_events_correlation", table_name="audit_events")
    op.drop_index("ix_audit_events_action_occurred", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_event", table_name="audit_events")
    op.drop_table("audit_heartbeats")
    op.drop_table("audit_delivery_attempts")
    op.drop_table("audit_outbox")
    for column in reversed(AUDIT_EVENT_COLUMNS):
        op.drop_column("audit_events", column.name)
