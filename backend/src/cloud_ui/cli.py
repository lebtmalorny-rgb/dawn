import argparse
import sys
from datetime import UTC, datetime

import uvicorn
from alembic import command
from alembic.config import Config

from cloud_ui.audit.delivery import AuditDeliveryWorker
from cloud_ui.audit.repository import AuditRepository
from cloud_ui.audit.sinks import LocalTestAuditSink
from cloud_ui.config import get_settings
from cloud_ui.db import create_db_engine
from cloud_ui.inventory.cursor import CursorCodec
from cloud_ui.inventory.reconciliation import InventoryReconciler
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.inventory.synthetic import SyntheticInventorySource
from cloud_ui.logging import configure_logging
from cloud_ui.operations.catalog import build_builtin_workflow_catalog
from cloud_ui.operations.mistral import InMemoryMistralAdapter
from cloud_ui.operations.repository import OperationRepository
from cloud_ui.operations.worker import OperationWorker
from cloud_ui.worker import run_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cloud-ui")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name in ("api", "inventory-sync-synthetic", "smoke"):
        subparsers.add_parser(command_name)
    db_parser = subparsers.add_parser("db-upgrade")
    db_parser.add_argument("--check", action="store_true")
    events_parser = subparsers.add_parser("events")
    events_parser.add_argument("--once", action="store_true")
    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument("--once", action="store_true")

    return parser


def run_api() -> None:
    settings = get_settings()
    uvicorn.run(
        "cloud_ui.api:create_app",
        factory=True,
        host=settings.api_bind_host,
        port=settings.api_port,
        log_config=None,
    )


def run_db_upgrade(*, check: bool = False) -> int:
    settings = get_settings()
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url.unicode_string())
    if check:
        command.current(cfg)
        print("db migration precheck ok")
        return 0

    command.upgrade(cfg, "head")
    print("db migration upgrade ok: revision=head")
    return 0


def run_inventory_sync_synthetic() -> int:
    settings = get_settings()
    if settings.environment == "production":
        raise RuntimeError("Synthetic inventory sync is not allowed in production")

    engine = create_db_engine(settings.database_url.unicode_string())
    try:
        repository = InventoryRepository(
            engine=engine,
            cursor_codec=CursorCodec(signing_key=settings.inventory_cursor_signing_key),
            default_limit=settings.inventory_default_limit,
            max_limit=settings.inventory_max_limit,
            stale_after_seconds=settings.inventory_stale_after_seconds,
        )
        source = SyntheticInventorySource(
            instance_count=settings.inventory_synthetic_instance_count,
            hypervisor_count=settings.inventory_synthetic_hypervisor_count,
        )
        result = InventoryReconciler(
            repository=repository,
            source=source,
            clock=lambda: datetime.now(UTC),
        ).run_full_sync(
            request_id="cli-inventory-sync-synthetic",
            correlation_id="cli-inventory-sync-synthetic",
        )
    finally:
        engine.dispose()

    if result.status == "partial":
        print(
            "inventory synthetic sync partial: "
            f"instances={result.instance_count} "
            f"hypervisors={result.hypervisor_count} "
            f"status={result.status}"
        )
        return 2

    print(
        "inventory synthetic sync ok: "
        f"instances={result.instance_count} "
        f"hypervisors={result.hypervisor_count} "
        f"status={result.status}"
    )
    return 0


def run_operation_worker_once() -> int:
    settings = get_settings()
    engine = create_db_engine(settings.database_url.unicode_string())
    try:
        result = OperationWorker(
            repository=OperationRepository(engine=engine),
            catalog=build_builtin_workflow_catalog(environment=settings.environment),
            mistral=InMemoryMistralAdapter(),
        ).run_once()
    finally:
        engine.dispose()

    if result.processed:
        print(
            "operation worker processed: "
            f"operation_id={result.operation_id} status={result.status}"
        )
    else:
        print("operation worker idle")
    return 0


def run_audit_delivery_once() -> int:
    settings = get_settings()
    engine = create_db_engine(settings.database_url.unicode_string())
    try:
        result = AuditDeliveryWorker(
            repository=AuditRepository(engine=engine),
            sink=LocalTestAuditSink(),
            retry_delay_seconds=settings.audit_delivery_retry_delay_seconds,
            max_attempts=settings.audit_delivery_max_attempts,
        ).run_once()
    finally:
        engine.dispose()

    if result.processed:
        print(f"audit delivery processed: event_id={result.event_id} status={result.status}")
    else:
        print("audit delivery idle")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "smoke":
        print("backend smoke ok")
        return 0

    settings = get_settings()
    configure_logging(settings.log_level)

    if args.command == "api":
        run_api()
    elif args.command == "worker":
        if args.once:
            return run_operation_worker_once()
        run_loop("worker")
    elif args.command == "events":
        if args.once:
            return run_audit_delivery_once()
        run_loop("events")
    elif args.command == "db-upgrade":
        return run_db_upgrade(check=args.check)
    elif args.command == "inventory-sync-synthetic":
        return run_inventory_sync_synthetic()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
