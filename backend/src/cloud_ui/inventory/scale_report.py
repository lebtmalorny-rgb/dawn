from __future__ import annotations

import math
import time
import tracemalloc
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.inventory import schema
from cloud_ui.inventory.cursor import CursorCodec
from cloud_ui.inventory.models import HypervisorFilters, InstanceFilters, InventorySort
from cloud_ui.inventory.reconciliation import InventoryReconciler
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.inventory.synthetic import SyntheticInventorySource

ResourceType = Literal["instances", "hypervisors"]

DEFAULT_OUTPUT_PATH = Path("docs/generated/e04-scale-report.md")
_CLOUD_ID = "synthetic"
_REGION_ID = "RegionOne"
_READ_MODEL_P95_BUDGET_SECONDS = 2.0
_QUERY_COUNT_BUDGET = 6


@dataclass(frozen=True)
class ScaleProfile:
    instance_count: int = 10_000
    hypervisor_count: int = 1_000
    page_size: int = 50
    max_page_size: int = 200
    sample_iterations: int = 20
    sync_chunk_size: int = 500
    stale_after_seconds: int = 900
    read_model_p95_budget_seconds: float = _READ_MODEL_P95_BUDGET_SECONDS

    def __post_init__(self) -> None:
        if self.instance_count < 0:
            raise ValueError("instance_count must be non-negative")
        if self.hypervisor_count < 0:
            raise ValueError("hypervisor_count must be non-negative")
        if self.instance_count > 0 and self.hypervisor_count == 0:
            raise ValueError("hypervisor_count must be positive when instances are generated")
        if self.page_size < 1:
            raise ValueError("page_size must be positive")
        if self.max_page_size < 1:
            raise ValueError("max_page_size must be positive")
        if self.page_size > self.max_page_size:
            raise ValueError("page_size must be less than or equal to max_page_size")
        if self.sample_iterations < 1:
            raise ValueError("sample_iterations must be positive")
        if self.sync_chunk_size < 1:
            raise ValueError("sync_chunk_size must be positive")
        if self.stale_after_seconds < 1:
            raise ValueError("stale_after_seconds must be positive")
        if self.read_model_p95_budget_seconds <= 0:
            raise ValueError("read_model_p95_budget_seconds must be positive")


@dataclass(frozen=True)
class DatasetCounts:
    instance_count: int
    hypervisor_count: int


@dataclass(frozen=True)
class SyncEvidence:
    status: str
    instance_count: int
    hypervisor_count: int
    generation: int
    elapsed_seconds: float


@dataclass(frozen=True)
class ScenarioEvidence:
    name: str
    resource: ResourceType
    page_size: int
    returned_count: int
    p95_seconds: float
    query_count_max: int
    query_count_p95: int
    explained_sql: str
    explain_summary: tuple[str, ...]


@dataclass(frozen=True)
class ScaleReport:
    profile: ScaleProfile
    dataset: DatasetCounts
    sync: SyncEvidence
    scenarios: tuple[ScenarioEvidence, ...]
    peak_memory_mib: float
    findings: tuple[str, ...]
    success: bool


@dataclass(frozen=True)
class _Scenario:
    name: str
    resource: ResourceType
    page_size: int
    list_page: Callable[[], int]


class _StepClock:
    def __init__(self) -> None:
        self._current = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        timestamp = self._current
        self._current = self._current + timedelta(seconds=1)
        return timestamp


@dataclass
class _StatementCounter:
    count: int = 0


@dataclass
class _CapturedStatement:
    statement: str | None = None
    parameters: Any = None


def generate_scale_report(
    profile: ScaleProfile,
    output_path: Path | None = None,
) -> ScaleReport:
    tracemalloc.start()
    try:
        engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
        try:
            schema.metadata.create_all(engine)
            repository = _repository(engine, profile)
            source = SyntheticInventorySource(
                instance_count=profile.instance_count,
                hypervisor_count=profile.hypervisor_count,
                cloud_id=_CLOUD_ID,
                region_id=_REGION_ID,
            )
            sync_started = time.perf_counter()
            sync_result = InventoryReconciler(
                repository=repository,
                source=source,
                clock=_StepClock(),
                chunk_size=profile.sync_chunk_size,
            ).run_full_sync(
                request_id="e04-scale-report",
                correlation_id="e04-scale-report",
            )
            sync_elapsed = time.perf_counter() - sync_started

            dataset = DatasetCounts(
                instance_count=_active_count(engine, schema.instances),
                hypervisor_count=_active_count(engine, schema.hypervisors),
            )
            scenarios = tuple(
                _run_scenario(engine, scenario, profile)
                for scenario in _scenarios(engine, repository, profile)
            )
            _, peak_bytes = tracemalloc.get_traced_memory()
            report = _build_report(
                profile=profile,
                dataset=dataset,
                sync=SyncEvidence(
                    status=sync_result.status,
                    instance_count=sync_result.instance_count,
                    hypervisor_count=sync_result.hypervisor_count,
                    generation=sync_result.generation,
                    elapsed_seconds=sync_elapsed,
                ),
                scenarios=scenarios,
                peak_memory_mib=peak_bytes / (1024 * 1024),
            )
        finally:
            engine.dispose()
    finally:
        tracemalloc.stop()

    if output_path is not None:
        write_markdown_report(report, output_path)
    return report


def write_markdown_report(report: ScaleReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_markdown(report), encoding="utf-8")


def _repository(engine: Engine, profile: ScaleProfile) -> InventoryRepository:
    return InventoryRepository(
        engine=engine,
        cursor_codec=CursorCodec(signing_key="e04-scale-report-cursor-key"),
        default_limit=profile.page_size,
        max_limit=profile.max_page_size,
        stale_after_seconds=profile.stale_after_seconds,
    )


def _scenarios(
    engine: Engine,
    repository: InventoryRepository,
    profile: ScaleProfile,
) -> Sequence[_Scenario]:
    instance_filter_values = _instance_filter_values(engine)
    hypervisor_filter_values = _hypervisor_filter_values(engine)

    instance_default_filters = InstanceFilters(cloud_id=_CLOUD_ID, region_id=_REGION_ID)
    instance_default_sort = InventorySort(field="name", direction="asc")
    instance_filtered_filters = InstanceFilters(
        cloud_id=_CLOUD_ID,
        region_id=_REGION_ID,
        project_id=instance_filter_values["project_id"],
        status=instance_filter_values["status"],
    )
    instance_filtered_sort = InventorySort(field="instance_id", direction="asc")
    hypervisor_default_filters = HypervisorFilters(cloud_id=_CLOUD_ID, region_id=_REGION_ID)
    hypervisor_default_sort = InventorySort(field="host_name", direction="asc")
    hypervisor_filtered_filters = HypervisorFilters(
        cloud_id=_CLOUD_ID,
        region_id=_REGION_ID,
        service_status=hypervisor_filter_values["service_status"],
        availability_zone=hypervisor_filter_values["availability_zone"],
    )
    hypervisor_filtered_sort = InventorySort(field="hypervisor_id", direction="asc")

    return (
        _Scenario(
            name="instances_default_page",
            resource="instances",
            page_size=profile.page_size,
            list_page=lambda: len(
                repository.list_instances(
                    filters=instance_default_filters,
                    sort=instance_default_sort,
                    limit=profile.page_size,
                    cursor=None,
                ).items
            ),
        ),
        _Scenario(
            name="instances_filtered_project_status",
            resource="instances",
            page_size=profile.page_size,
            list_page=lambda: len(
                repository.list_instances(
                    filters=instance_filtered_filters,
                    sort=instance_filtered_sort,
                    limit=profile.page_size,
                    cursor=None,
                ).items
            ),
        ),
        _Scenario(
            name="hypervisors_default_page",
            resource="hypervisors",
            page_size=profile.page_size,
            list_page=lambda: len(
                repository.list_hypervisors(
                    filters=hypervisor_default_filters,
                    sort=hypervisor_default_sort,
                    limit=profile.page_size,
                    cursor=None,
                ).items
            ),
        ),
        _Scenario(
            name="hypervisors_filtered_service_status_az",
            resource="hypervisors",
            page_size=profile.page_size,
            list_page=lambda: len(
                repository.list_hypervisors(
                    filters=hypervisor_filtered_filters,
                    sort=hypervisor_filtered_sort,
                    limit=profile.page_size,
                    cursor=None,
                ).items
            ),
        ),
    )


def _run_scenario(
    engine: Engine,
    scenario: _Scenario,
    profile: ScaleProfile,
) -> ScenarioEvidence:
    durations: list[float] = []
    query_counts: list[int] = []
    returned_count = 0
    captured_statement = _CapturedStatement()

    for _ in range(profile.sample_iterations):
        counter = _StatementCounter()
        before_cursor_execute = _statement_listener(
            counter=counter,
            capture=captured_statement,
            resource=scenario.resource,
        )

        sa.event.listen(engine, "before_cursor_execute", before_cursor_execute)
        started = time.perf_counter()
        try:
            returned_count = scenario.list_page()
        finally:
            durations.append(time.perf_counter() - started)
            query_counts.append(counter.count)
            sa.event.remove(engine, "before_cursor_execute", before_cursor_execute)

    return ScenarioEvidence(
        name=scenario.name,
        resource=scenario.resource,
        page_size=scenario.page_size,
        returned_count=returned_count,
        p95_seconds=_percentile(durations, 95),
        query_count_max=max(query_counts),
        query_count_p95=math.ceil(_percentile([float(count) for count in query_counts], 95)),
        explained_sql=_required_statement(captured_statement),
        explain_summary=_explain_summary(engine, captured_statement),
    )


def _statement_listener(
    *,
    counter: _StatementCounter,
    capture: _CapturedStatement,
    resource: ResourceType,
) -> Callable[[sa.Connection, object, str, object, object, bool], None]:
    def before_cursor_execute(
        _conn: sa.Connection,
        _cursor: object,
        _statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        counter.count += 1
        if capture.statement is None and _is_page_select(_statement, resource):
            capture.statement = _statement
            capture.parameters = _parameters

    return before_cursor_execute


def _is_page_select(statement: str, resource: ResourceType) -> bool:
    normalized = " ".join(statement.split()).lower()
    return (
        normalized.startswith("select ")
        and f" from {resource} " in f" {normalized} "
        and not normalized.startswith("select max(")
    )


def _required_statement(captured_statement: _CapturedStatement) -> str:
    if captured_statement.statement is None:
        raise RuntimeError("inventory list SELECT was not captured for EXPLAIN")
    return captured_statement.statement


def _build_report(
    *,
    profile: ScaleProfile,
    dataset: DatasetCounts,
    sync: SyncEvidence,
    scenarios: tuple[ScenarioEvidence, ...],
    peak_memory_mib: float,
) -> ScaleReport:
    findings: list[str] = []
    if sync.status != "success":
        findings.append(f"Full synthetic reconciliation ended with status {sync.status}.")
    if dataset.instance_count != profile.instance_count:
        findings.append(
            f"Instance count mismatch: expected {profile.instance_count}, "
            f"read model has {dataset.instance_count}."
        )
    if dataset.hypervisor_count != profile.hypervisor_count:
        findings.append(
            f"Hypervisor count mismatch: expected {profile.hypervisor_count}, "
            f"read model has {dataset.hypervisor_count}."
        )
    for scenario in scenarios:
        if scenario.p95_seconds > profile.read_model_p95_budget_seconds:
            findings.append(
                f"{scenario.name} p95 {scenario.p95_seconds:.6f}s exceeds "
                f"{profile.read_model_p95_budget_seconds:.3f}s budget."
            )
        if scenario.query_count_max > _QUERY_COUNT_BUDGET:
            findings.append(
                f"{scenario.name} used {scenario.query_count_max} SQL statements; "
                f"bounded query budget is {_QUERY_COUNT_BUDGET}."
            )
        if not scenario.explain_summary:
            findings.append(f"{scenario.name} did not produce EXPLAIN evidence.")
    if not findings:
        findings.append(
            "No blocking findings for synthetic SQLite read-model list scenarios."
        )
    success = (
        sync.status == "success"
        and dataset.instance_count == profile.instance_count
        and dataset.hypervisor_count == profile.hypervisor_count
        and all(
            scenario.p95_seconds <= profile.read_model_p95_budget_seconds
            and scenario.query_count_max <= _QUERY_COUNT_BUDGET
            and scenario.explain_summary
            for scenario in scenarios
        )
    )
    return ScaleReport(
        profile=profile,
        dataset=dataset,
        sync=sync,
        scenarios=scenarios,
        peak_memory_mib=peak_memory_mib,
        findings=tuple(findings),
        success=success,
    )


def _active_count(engine: Engine, table: sa.Table) -> int:
    with engine.connect() as connection:
        value = connection.execute(
            sa.select(sa.func.count()).select_from(table).where(table.c.deleted_at.is_(None))
        ).scalar_one()
    return int(value)


def _instance_filter_values(engine: Engine) -> dict[str, str]:
    statement = (
        sa.select(schema.instances.c.project_id, schema.instances.c.status)
        .where(
            schema.instances.c.cloud_id == _CLOUD_ID,
            schema.instances.c.region_id == _REGION_ID,
            schema.instances.c.deleted_at.is_(None),
        )
        .order_by(schema.instances.c.instance_id.asc())
        .limit(1)
    )
    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one_or_none()
    if row is None:
        return {"project_id": "none", "status": "none"}
    return {"project_id": str(row["project_id"]), "status": str(row["status"])}


def _hypervisor_filter_values(engine: Engine) -> dict[str, str]:
    statement = (
        sa.select(schema.hypervisors.c.service_status, schema.hypervisors.c.availability_zone)
        .where(
            schema.hypervisors.c.cloud_id == _CLOUD_ID,
            schema.hypervisors.c.region_id == _REGION_ID,
            schema.hypervisors.c.deleted_at.is_(None),
        )
        .order_by(schema.hypervisors.c.hypervisor_id.asc())
        .limit(1)
    )
    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one_or_none()
    if row is None:
        return {"service_status": "none", "availability_zone": "none"}
    return {
        "service_status": str(row["service_status"]),
        "availability_zone": str(row["availability_zone"]),
    }


def _explain_summary(
    engine: Engine,
    captured_statement: _CapturedStatement,
) -> tuple[str, ...]:
    statement = _required_statement(captured_statement)
    with engine.connect() as connection:
        rows = connection.exec_driver_sql(
            f"EXPLAIN QUERY PLAN {statement}",
            captured_statement.parameters,
        ).all()
    details = [str(row[-1]) for row in rows]
    return tuple(details[:4])


def _percentile(values: Sequence[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil((percentile / 100) * len(ordered)) - 1)
    return ordered[index]


def _markdown(report: ScaleReport) -> str:
    scenario_lines = "\n".join(
        (
            f"| `{scenario.name}` | {scenario.resource} | {scenario.page_size} | "
            f"{scenario.returned_count} | {scenario.p95_seconds:.6f} | "
            f"{scenario.query_count_p95} | {scenario.query_count_max} | "
            f"{'; '.join(scenario.explain_summary)} |"
        )
        for scenario in report.scenarios
    )
    finding_lines = "\n".join(f"- {finding}" for finding in report.findings)
    return (
        "# E04.6 Synthetic scale report\n\n"
        "Scope: synthetic/local evidence only; not production MariaDB/HA evidence.\n\n"
        "This report is generated from the portal read model populated by synthetic "
        "reconciliation in an in-memory SQLite database. It does not contact external "
        "OpenStack services, Docker, or live infrastructure.\n\n"
        "## Dataset\n\n"
        f"- instances: {report.dataset.instance_count}\n"
        f"- hypervisors: {report.dataset.hypervisor_count}\n"
        f"- default page size: {report.profile.page_size}\n"
        f"- max page size: {report.profile.max_page_size}\n"
        f"- sample iterations per scenario: {report.profile.sample_iterations}\n\n"
        "## Synchronization\n\n"
        f"- status: {report.sync.status}\n"
        f"- instances seen: {report.sync.instance_count}\n"
        f"- hypervisors seen: {report.sync.hypervisor_count}\n"
        f"- generation: {report.sync.generation}\n"
        f"- elapsed seconds: {report.sync.elapsed_seconds:.6f}\n"
        f"- peak Python memory MiB: {report.peak_memory_mib:.3f}\n\n"
        "## Read-model scenarios\n\n"
        "| Scenario | Resource | Page size | Rows returned | p95 seconds | "
        "SQL p95 | SQL max | SQLite EXPLAIN summary |\n"
        "|---|---|---:|---:|---:|---:|---:|---|\n"
        f"{scenario_lines}\n\n"
        "## Findings\n\n"
        f"{finding_lines}\n\n"
        "## DKB evidence\n\n"
        "- DKB-77/82: records reproducible synthetic evidence for documented list API "
        "performance and generated documentation.\n"
        "- DKB-01/03/12: demonstrates bounded read-model list access without browser-side "
        "full inventory loading.\n"
        "- DKB-46/49: includes sync status and freshness-related read-model evidence.\n"
    )
