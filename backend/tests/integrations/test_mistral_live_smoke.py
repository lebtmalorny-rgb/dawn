from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote
from uuid import uuid4

import httpx
import pytest


@dataclass(frozen=True)
class MistralSmokeConfig:
    endpoint: str
    token: str
    workflow_key: str
    workflow_name: str
    test_project_id: str
    no_production_action_proof: str
    cacert: str | None


def test_all_in_one_mistral_workflow_lookup_smoke(record_property: object) -> None:
    config = _load_config()
    correlation_id = f"e06-mistral-smoke-{uuid4()}"
    workflow_url = _workflow_url(config.endpoint, config.workflow_name)

    _record_property(record_property, "endpoint_source", "DAWN_MISTRAL_ENDPOINT")
    _record_property(record_property, "workflow_key", config.workflow_key)
    _record_property(record_property, "workflow_name", config.workflow_name)
    _record_property(record_property, "test_project_id", config.test_project_id)
    _record_property(record_property, "correlation_id", correlation_id)
    _record_property(record_property, "production_action", "none: read-only workflow lookup")

    verify: bool | str = config.cacert if config.cacert is not None else True
    with httpx.Client(timeout=10.0, verify=verify, follow_redirects=False) as client:
        response = client.get(
            workflow_url,
            headers={
                "accept": "application/json",
                "x-auth-token": config.token,
                "x-correlation-id": correlation_id,
            },
        )

    assert response.request.method == "GET"
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload.get("name") == config.workflow_name


def _load_config() -> MistralSmokeConfig:
    if os.environ.get("DAWN_MISTRAL_SMOKE") != "1":
        pytest.skip("Set DAWN_MISTRAL_SMOKE=1 with all-in-one Mistral test config to run")

    required = {
        "DAWN_MISTRAL_ENDPOINT": os.environ.get("DAWN_MISTRAL_ENDPOINT"),
        "DAWN_MISTRAL_TOKEN": os.environ.get("DAWN_MISTRAL_TOKEN"),
        "DAWN_MISTRAL_WORKFLOW_KEY": os.environ.get("DAWN_MISTRAL_WORKFLOW_KEY"),
        "DAWN_MISTRAL_WORKFLOW_NAME": os.environ.get("DAWN_MISTRAL_WORKFLOW_NAME"),
        "DAWN_MISTRAL_TEST_PROJECT_ID": os.environ.get("DAWN_MISTRAL_TEST_PROJECT_ID"),
        "DAWN_MISTRAL_NO_PRODUCTION_ACTION_PROOF": os.environ.get(
            "DAWN_MISTRAL_NO_PRODUCTION_ACTION_PROOF"
        ),
    }
    missing = [name for name, value in required.items() if value is None or value.strip() == ""]
    if missing:
        pytest.fail(f"Missing explicit Mistral smoke configuration: {', '.join(missing)}")

    no_production_action_proof = required["DAWN_MISTRAL_NO_PRODUCTION_ACTION_PROOF"]
    if no_production_action_proof != "read_only_workflow_lookup":
        pytest.fail(
            "DAWN_MISTRAL_NO_PRODUCTION_ACTION_PROOF must be "
            "'read_only_workflow_lookup' for the P2 smoke"
        )

    return MistralSmokeConfig(
        endpoint=_required(required, "DAWN_MISTRAL_ENDPOINT"),
        token=_required(required, "DAWN_MISTRAL_TOKEN"),
        workflow_key=_required(required, "DAWN_MISTRAL_WORKFLOW_KEY"),
        workflow_name=_required(required, "DAWN_MISTRAL_WORKFLOW_NAME"),
        test_project_id=_required(required, "DAWN_MISTRAL_TEST_PROJECT_ID"),
        no_production_action_proof=no_production_action_proof,
        cacert=os.environ.get("DAWN_MISTRAL_CACERT"),
    )


def _required(values: dict[str, str | None], name: str) -> str:
    value = values[name]
    assert value is not None
    return value


def _workflow_url(endpoint: str, workflow_name: str) -> str:
    base = endpoint.rstrip("/")
    encoded_name = quote(workflow_name, safe="")
    if base.endswith("/v2"):
        return f"{base}/workflows/{encoded_name}"
    return f"{base}/v2/workflows/{encoded_name}"


def _record_property(record_property: object, name: str, value: str) -> None:
    if callable(record_property):
        record_property(name, value)
