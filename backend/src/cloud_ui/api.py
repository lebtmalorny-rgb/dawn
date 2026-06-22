from uuid import uuid4

from fastapi import APIRouter, FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from cloud_ui.config import get_settings
from cloud_ui.groups.repository import GroupRepository
from cloud_ui.groups.routes import GroupServices, build_group_router
from cloud_ui.health import HealthReport, ReadinessCheck, build_readiness_check
from cloud_ui.inventory.routes import (
    InventoryServices,
    build_inventory_router_with_groups,
    build_inventory_services,
    unavailable_inventory_services,
)
from cloud_ui.operations.catalog import build_builtin_workflow_catalog
from cloud_ui.operations.repository import OperationRepository
from cloud_ui.operations.routes import OperationServices, build_operation_router
from cloud_ui.security.dependencies import SecurityServices, build_security_services
from cloud_ui.security.routes import build_security_router


def build_health_router(check: ReadinessCheck) -> APIRouter:
    router = APIRouter()

    @router.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @router.get(
        "/health/ready",
        response_model=HealthReport,
        responses={503: {"model": HealthReport}},
    )
    def health_ready(response: Response) -> HealthReport:
        report = check()
        response.status_code = 200 if report.status == "ok" else 503
        return report

    return router


def create_app(
    readiness_check: ReadinessCheck | None = None,
    security_services: SecurityServices | None = None,
    inventory_services: InventoryServices | None = None,
    group_services: GroupServices | None = None,
    operation_services: OperationServices | None = None,
) -> FastAPI:
    check = readiness_check
    if check is None:
        settings = get_settings()
        check = build_readiness_check(settings)
    else:
        settings = None

    security = security_services
    if security is None:
        security = build_security_services(settings)

    inventory = inventory_services
    if inventory is None:
        if settings is None:
            inventory = unavailable_inventory_services()
        else:
            inventory = build_inventory_services(settings)

    groups = group_services
    if groups is None:
        group_repository = (
            GroupRepository(engine=inventory.engine) if inventory.engine is not None else None
        )
        groups = GroupServices(
            repository=group_repository,
            inventory_repository=inventory.repository,
        )

    operations = operation_services
    if operations is None:
        operation_repository = (
            OperationRepository(engine=inventory.engine) if inventory.engine is not None else None
        )
        environment = settings.environment if settings is not None else "local"
        operations = OperationServices(
            repository=operation_repository,
            inventory_repository=inventory.repository,
            group_repository=groups.repository,
            catalog=build_builtin_workflow_catalog(environment=environment),
        )

    app = FastAPI(title="Cloud UI API", version="0.1.0")
    app.state.security_services = security
    app.state.inventory_services = inventory
    app.state.group_services = groups
    app.state.operation_services = operations
    if inventory.engine is not None:
        app.state.inventory_engine = inventory.engine

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        has_sensitive_session_data = request.url.path.startswith(
            "/api/v1/session"
        ) or request.url.path == "/api/v1/capabilities"
        if has_sensitive_session_data:
            response.headers["cache-control"] = "no-store"
        return response

    app.include_router(build_health_router(check))
    app.include_router(build_health_router(check), prefix="/api/v1")
    app.include_router(build_security_router(security), prefix="/api/v1")
    app.include_router(build_operation_router(operations, security), prefix="/api/v1")
    app.include_router(build_group_router(groups, security), prefix="/api/v1")
    app.include_router(
        build_inventory_router_with_groups(inventory, security, groups),
        prefix="/api/v1",
    )

    return app
