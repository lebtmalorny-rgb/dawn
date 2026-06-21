"""create inventory read model tables"""

import sqlalchemy as sa
from alembic import op

revision = "0003_inventory_read_model"
down_revision = "0002_security_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clouds",
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("cloud_id"),
    )
    op.create_table(
        "regions",
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("cloud_id", "region_id"),
        sa.ForeignKeyConstraint(["cloud_id"], ["clouds.cloud_id"], ondelete="CASCADE"),
    )
    op.create_table(
        "inventory_sync_runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("sync_mode", sa.String(length=32), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("items_seen", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_upserted", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_deleted", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
        sa.ForeignKeyConstraint(
            ["cloud_id", "region_id"],
            ["regions.cloud_id", "regions.region_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "inventory_sync_cursors",
        sa.Column("cursor_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("cursor_value", sa.String(length=1024), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cursor_id"),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["inventory_sync_runs.run_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "inventory_sync_failures",
        sa.Column("failure_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("chunk_cursor", sa.String(length=1024), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=False),
        sa.Column("safe_message", sa.String(length=1024), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("failure_id"),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["inventory_sync_runs.run_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_inventory_sync_failures_recent",
        "inventory_sync_failures",
        ["cloud_id", "region_id", "resource_type", "occurred_at", "failure_id"],
    )
    op.create_table(
        "instances",
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("instance_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("power_state", sa.String(length=32), nullable=False),
        sa.Column("task_state", sa.String(length=64), nullable=True),
        sa.Column("vm_state", sa.String(length=32), nullable=False),
        sa.Column("host_name", sa.String(length=255), nullable=True),
        sa.Column("hypervisor_id", sa.String(length=128), nullable=True),
        sa.Column("availability_zone", sa.String(length=128), nullable=True),
        sa.Column("flavor_id", sa.String(length=128), nullable=True),
        sa.Column("vcpus", sa.Integer(), nullable=False),
        sa.Column("ram_mb", sa.Integer(), nullable=False),
        sa.Column("disk_gb", sa.Integer(), nullable=False),
        sa.Column("image_id", sa.String(length=128), nullable=True),
        sa.Column("boot_volume_id", sa.String(length=128), nullable=True),
        sa.Column("addresses_json", sa.JSON(), nullable=False),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_generation", sa.Integer(), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_hash", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("cloud_id", "region_id", "instance_id"),
        sa.ForeignKeyConstraint(
            ["cloud_id", "region_id"],
            ["regions.cloud_id", "regions.region_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_instances_name_page",
        "instances",
        ["cloud_id", "region_id", "deleted_at", "name", "instance_id"],
    )
    op.create_index(
        "ix_instances_project_status",
        "instances",
        ["cloud_id", "region_id", "deleted_at", "project_id", "status", "instance_id"],
    )
    op.create_index(
        "ix_instances_host_status",
        "instances",
        ["cloud_id", "region_id", "deleted_at", "host_name", "status", "instance_id"],
    )
    op.create_index(
        "ix_instances_az_status",
        "instances",
        ["cloud_id", "region_id", "deleted_at", "availability_zone", "status", "instance_id"],
    )
    op.create_index(
        "ix_instances_observed",
        "instances",
        ["cloud_id", "region_id", "observed_at"],
    )
    op.create_table(
        "hypervisors",
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("hypervisor_id", sa.String(length=128), nullable=False),
        sa.Column("host_name", sa.String(length=255), nullable=False),
        sa.Column("service_id", sa.String(length=128), nullable=True),
        sa.Column("service_status", sa.String(length=32), nullable=False),
        sa.Column("service_state", sa.String(length=32), nullable=False),
        sa.Column("hypervisor_type", sa.String(length=64), nullable=True),
        sa.Column("hypervisor_version", sa.String(length=64), nullable=True),
        sa.Column("availability_zone", sa.String(length=128), nullable=True),
        sa.Column("aggregates_json", sa.JSON(), nullable=False),
        sa.Column("vcpus_total", sa.Integer(), nullable=False),
        sa.Column("vcpus_used", sa.Integer(), nullable=False),
        sa.Column("ram_mb_total", sa.Integer(), nullable=False),
        sa.Column("ram_mb_used", sa.Integer(), nullable=False),
        sa.Column("disk_gb_total", sa.Integer(), nullable=False),
        sa.Column("disk_gb_used", sa.Integer(), nullable=False),
        sa.Column("running_vms", sa.Integer(), nullable=False),
        sa.Column("disabled_reason", sa.String(length=1024), nullable=True),
        sa.Column("maintenance_status", sa.String(length=32), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_generation", sa.Integer(), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_hash", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("cloud_id", "region_id", "hypervisor_id"),
        sa.ForeignKeyConstraint(
            ["cloud_id", "region_id"],
            ["regions.cloud_id", "regions.region_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_hypervisors_host_page",
        "hypervisors",
        ["cloud_id", "region_id", "deleted_at", "host_name", "hypervisor_id"],
    )
    op.create_index(
        "ix_hypervisors_service",
        "hypervisors",
        [
            "cloud_id",
            "region_id",
            "deleted_at",
            "service_status",
            "service_state",
            "hypervisor_id",
        ],
    )
    op.create_index(
        "ix_hypervisors_az",
        "hypervisors",
        ["cloud_id", "region_id", "availability_zone", "hypervisor_id"],
    )
    op.create_index(
        "ix_hypervisors_observed",
        "hypervisors",
        ["cloud_id", "region_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_hypervisors_observed", table_name="hypervisors")
    op.drop_index("ix_hypervisors_az", table_name="hypervisors")
    op.drop_index("ix_hypervisors_service", table_name="hypervisors")
    op.drop_index("ix_hypervisors_host_page", table_name="hypervisors")
    op.drop_index("ix_instances_observed", table_name="instances")
    op.drop_index("ix_instances_az_status", table_name="instances")
    op.drop_index("ix_instances_host_status", table_name="instances")
    op.drop_index("ix_instances_project_status", table_name="instances")
    op.drop_index("ix_instances_name_page", table_name="instances")
    op.drop_table("hypervisors")
    op.drop_table("instances")
    op.drop_index("ix_inventory_sync_failures_recent", table_name="inventory_sync_failures")
    op.drop_table("inventory_sync_failures")
    op.drop_table("inventory_sync_cursors")
    op.drop_table("inventory_sync_runs")
    op.drop_table("regions")
    op.drop_table("clouds")
