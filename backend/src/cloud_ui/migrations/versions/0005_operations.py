"""create operation workflow tables"""

import sqlalchemy as sa
from alembic import op

revision = "0005_operations"
down_revision = "0004_resource_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("workflow_key", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("input_schema_json", sa.JSON(), nullable=False),
        sa.Column("ui_schema_json", sa.JSON(), nullable=True),
        sa.Column("mistral_workflow_name", sa.String(length=255), nullable=False),
        sa.Column("required_capability", sa.String(length=128), nullable=False),
        sa.Column("required_scope_type", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("approval_mode", sa.String(length=32), nullable=False),
        sa.Column("cancel_policy", sa.String(length=32), nullable=False),
        sa.Column("enabled_environments_json", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workflow_key", "version"),
    )
    op.create_index(
        "ix_workflow_definitions_enabled",
        "workflow_definitions",
        ["enabled", "workflow_key", "version"],
    )
    op.create_table(
        "operations",
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_key", sa.String(length=128), nullable=False),
        sa.Column("workflow_version", sa.String(length=32), nullable=False),
        sa.Column("definition_checksum", sa.String(length=128), nullable=False),
        sa.Column("actor_subject_id", sa.String(length=128), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=128), nullable=False),
        sa.Column("target_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("external_execution_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("operation_id"),
    )
    op.create_index(
        "ix_operations_actor_status_created",
        "operations",
        ["actor_subject_id", "status", "created_at", "operation_id"],
    )
    op.create_index("ix_operations_correlation", "operations", ["correlation_id"], unique=True)
    op.create_index(
        "ix_operations_external_execution",
        "operations",
        ["external_execution_id"],
    )
    op.create_table(
        "operation_targets",
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "operation_id",
            "target_type",
            "cloud_id",
            "region_id",
            "resource_id",
        ),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.operation_id"], ondelete="CASCADE"),
    )
    op.create_table(
        "operation_events",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("safe_message", sa.String(length=1024), nullable=False),
        sa.Column("safe_error_code", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.operation_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_operation_events_operation_created",
        "operation_events",
        ["operation_id", "created_at", "event_id"],
    )
    op.create_table(
        "operation_attempts",
        sa.Column("attempt_id", sa.String(length=128), nullable=False),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("adapter_action", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("external_execution_id", sa.String(length=128), nullable=True),
        sa.Column("safe_error_code", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("attempt_id"),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.operation_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_operation_attempts_operation_created",
        "operation_attempts",
        ["operation_id", "created_at", "attempt_id"],
    )
    op.create_table(
        "operation_outbox",
        sa.Column("outbox_id", sa.String(length=128), nullable=False),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("not_before_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("outbox_id"),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.operation_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_operation_outbox_state_created",
        "operation_outbox",
        ["state", "created_at", "outbox_id"],
    )
    op.create_table(
        "operation_idempotency_keys",
        sa.Column("actor_subject_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_key", sa.String(length=128), nullable=False),
        sa.Column("workflow_version", sa.String(length=32), nullable=False),
        sa.Column("scope_hash", sa.String(length=128), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("actor_subject_id", "workflow_key", "scope_hash", "key_hash"),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.operation_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_operation_idempotency_created",
        "operation_idempotency_keys",
        ["created_at", "operation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_operation_idempotency_created", table_name="operation_idempotency_keys")
    op.drop_table("operation_idempotency_keys")
    op.drop_index("ix_operation_outbox_state_created", table_name="operation_outbox")
    op.drop_table("operation_outbox")
    op.drop_index("ix_operation_attempts_operation_created", table_name="operation_attempts")
    op.drop_table("operation_attempts")
    op.drop_index("ix_operation_events_operation_created", table_name="operation_events")
    op.drop_table("operation_events")
    op.drop_table("operation_targets")
    op.drop_index("ix_operations_external_execution", table_name="operations")
    op.drop_index("ix_operations_correlation", table_name="operations")
    op.drop_index("ix_operations_actor_status_created", table_name="operations")
    op.drop_table("operations")
    op.drop_index("ix_workflow_definitions_enabled", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
