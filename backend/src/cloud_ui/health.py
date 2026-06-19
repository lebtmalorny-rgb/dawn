from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from cloud_ui.config import Settings
from cloud_ui.db import check_database
from cloud_ui.mq import check_rabbitmq

DependencyStatus = Literal["ok", "down"]
HealthStatus = Literal["ok", "degraded"]


class DependencyState(BaseModel):
    status: DependencyStatus
    detail: str


class HealthReport(BaseModel):
    status: HealthStatus
    dependencies: dict[str, DependencyState]


ReadinessCheck = Callable[[], HealthReport]


def build_readiness_check(settings: Settings) -> ReadinessCheck:
    def check() -> HealthReport:
        dependencies = {
            "database": _probe_dependency(
                lambda: check_database(settings.database_url.unicode_string())
            ),
            "rabbitmq": _probe_dependency(
                lambda: check_rabbitmq(settings.rabbitmq_url.unicode_string())
            ),
        }
        overall_status: HealthStatus = (
            "degraded"
            if any(dependency.status == "down" for dependency in dependencies.values())
            else "ok"
        )
        return HealthReport(status=overall_status, dependencies=dependencies)

    return check


def _probe_dependency(probe: Callable[[], str]) -> DependencyState:
    try:
        detail = probe()
    except Exception:
        return DependencyState(status="down", detail="unreachable")
    return DependencyState(status="ok", detail=detail)
