from cloud_ui.integrations.base import (
    AdapterRequestContext,
    OpenStackForbiddenError,
    OpenStackTemporaryError,
    OpenStackTimeoutError,
    RetryDecision,
    should_retry,
)


def test_adapter_error_repr_redacts_sensitive_values() -> None:
    error = OpenStackForbiddenError(
        service="nova",
        message="Authorization failed",
        status_code=403,
        request_id="request-1",
        correlation_id="corr-1",
        details={
            "authorization": "Bearer secret-token",
            "normal": "visible",
            "token": "secret-token",
        },
    )

    rendered = repr(error)

    assert "secret-token" not in rendered
    assert "Bearer" not in rendered
    assert "visible" in rendered
    assert error.code == "openstack_forbidden"


def test_retry_policy_retries_only_temporary_read_failures() -> None:
    context = AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )

    temporary = OpenStackTemporaryError(
        service="nova",
        message="temporary",
        status_code=503,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
    timeout = OpenStackTimeoutError(
        service="nova",
        message="timeout",
        status_code=None,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
    forbidden = OpenStackForbiddenError(
        service="nova",
        message="forbidden",
        status_code=403,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )

    assert should_retry("GET", temporary, attempt=1, max_attempts=2) == RetryDecision.RETRY
    assert should_retry("GET", timeout, attempt=1, max_attempts=2) == RetryDecision.RETRY
    assert should_retry("GET", temporary, attempt=2, max_attempts=2) == RetryDecision.STOP
    assert should_retry("GET", forbidden, attempt=1, max_attempts=2) == RetryDecision.STOP
    assert should_retry("POST", temporary, attempt=1, max_attempts=2) == RetryDecision.STOP
