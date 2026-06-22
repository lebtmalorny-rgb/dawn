from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()

audit_events = sa.Table(
    "audit_events",
    metadata,
    sa.Column("event_id", sa.String(length=128), primary_key=True),
    sa.Column("event_version", sa.String(length=32), nullable=False),
    sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("actor_type", sa.String(length=32), nullable=False),
    sa.Column("actor_id", sa.String(length=128), nullable=False),
    sa.Column("actor_display", sa.String(length=255), nullable=True),
    sa.Column("authentication_method", sa.String(length=64), nullable=True),
    sa.Column("session_reference", sa.String(length=128), nullable=True),
    sa.Column("action", sa.String(length=128), nullable=False),
    sa.Column("event_type", sa.String(length=64), nullable=False),
    sa.Column("outcome", sa.String(length=32), nullable=False),
    sa.Column("target_type", sa.String(length=64), nullable=False),
    sa.Column("target_id", sa.String(length=128), nullable=True),
    sa.Column("cloud_id", sa.String(length=128), nullable=True),
    sa.Column("region_id", sa.String(length=128), nullable=True),
    sa.Column("project_id", sa.String(length=128), nullable=True),
    sa.Column("scope_type", sa.String(length=32), nullable=True),
    sa.Column("scope_id", sa.String(length=128), nullable=True),
    sa.Column("source_ip", sa.String(length=64), nullable=True),
    sa.Column("trusted_proxy_chain_json", sa.JSON(), nullable=True),
    sa.Column("request_id", sa.String(length=128), nullable=False),
    sa.Column("correlation_id", sa.String(length=128), nullable=False),
    sa.Column("operation_id", sa.String(length=128), nullable=True),
    sa.Column("external_execution_id", sa.String(length=128), nullable=True),
    sa.Column("service", sa.String(length=64), nullable=False),
    sa.Column("component", sa.String(length=64), nullable=True),
    sa.Column("safe_error_code", sa.String(length=128), nullable=True),
    sa.Column("delivery_state", sa.String(length=32), nullable=True),
    sa.Column("event_hash", sa.String(length=128), nullable=True),
    sa.Column("metadata_json", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
)

audit_outbox = sa.Table(
    "audit_outbox",
    metadata,
    sa.Column("outbox_id", sa.String(length=160), primary_key=True),
    sa.Column("event_id", sa.String(length=128), nullable=False),
    sa.Column("sink_id", sa.String(length=64), nullable=False),
    sa.Column("state", sa.String(length=32), nullable=False),
    sa.Column("attempt_count", sa.Integer(), nullable=False, default=0),
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

audit_delivery_attempts = sa.Table(
    "audit_delivery_attempts",
    metadata,
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

audit_heartbeats = sa.Table(
    "audit_heartbeats",
    metadata,
    sa.Column("sink_id", sa.String(length=64), primary_key=True),
    sa.Column("state", sa.String(length=32), nullable=False),
    sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("queue_depth", sa.Integer(), nullable=False),
    sa.Column("oldest_pending_age_seconds", sa.Integer(), nullable=True),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
)

sa.Index("ix_audit_events_occurred_event", audit_events.c.occurred_at, audit_events.c.event_id)
sa.Index("ix_audit_events_action_occurred", audit_events.c.action, audit_events.c.occurred_at)
sa.Index("ix_audit_events_correlation", audit_events.c.correlation_id)
sa.Index(
    "ix_audit_outbox_state_not_before",
    audit_outbox.c.state,
    audit_outbox.c.not_before_at,
    audit_outbox.c.outbox_id,
)
sa.Index(
    "ix_audit_delivery_attempts_outbox_created",
    audit_delivery_attempts.c.outbox_id,
    audit_delivery_attempts.c.created_at,
    audit_delivery_attempts.c.attempt_id,
)
