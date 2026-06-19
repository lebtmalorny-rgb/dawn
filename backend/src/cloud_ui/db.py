from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DB_PROBE_TIMEOUT_SECONDS = 3


def create_db_engine(database_url: str) -> Engine:
    kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_size": 2,
        "max_overflow": 2,
    }
    if database_url.startswith("mysql+pymysql://"):
        kwargs["connect_args"] = {
            "connect_timeout": DB_PROBE_TIMEOUT_SECONDS,
            "read_timeout": DB_PROBE_TIMEOUT_SECONDS,
            "write_timeout": DB_PROBE_TIMEOUT_SECONDS,
        }
    return create_engine(database_url, **kwargs)


def check_database(database_url: str) -> str:
    engine = create_db_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "reachable"
    finally:
        engine.dispose()
