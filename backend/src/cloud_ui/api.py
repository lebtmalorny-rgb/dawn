from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from cloud_ui.config import get_settings
from cloud_ui.health import HealthReport, ReadinessCheck, build_readiness_check


def create_app(readiness_check: ReadinessCheck | None = None) -> FastAPI:
    check = readiness_check
    if check is None:
        settings = get_settings()
        check = build_readiness_check(settings)

    app = FastAPI(title="Cloud UI API", version="0.1.0")

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/health/ready",
        response_model=HealthReport,
        responses={503: {"model": HealthReport}},
    )
    def health_ready(response: Response) -> HealthReport:
        report = check()
        response.status_code = 200 if report.status == "ok" else 503
        return report

    return app
