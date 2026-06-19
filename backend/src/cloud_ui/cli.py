import argparse
import sys

import uvicorn
from alembic import command
from alembic.config import Config

from cloud_ui.config import get_settings
from cloud_ui.logging import configure_logging
from cloud_ui.worker import run_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cloud-ui")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name in ("api", "worker", "events", "db-upgrade", "smoke"):
        subparsers.add_parser(command_name)

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


def run_db_upgrade() -> None:
    settings = get_settings()
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url.unicode_string())
    command.upgrade(cfg, "head")


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
        run_loop("worker")
    elif args.command == "events":
        run_loop("events")
    elif args.command == "db-upgrade":
        run_db_upgrade()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
