# Audit sample events

- Stage: E07
- Purpose: sanitized examples for contract review and SIEM field mapping.
- Rule: examples contain no real user, project, endpoint, token, cookie, password, private key or business data.

## Successful session event

```json
{
  "event_id": "audit-sample-login-success",
  "event_version": "1",
  "sink_id": "local-test",
  "occurred_at": "2026-06-22T12:00:03Z",
  "actor": {
    "type": "human",
    "id": "mock-user-operator",
    "display": "Operator",
    "authentication_method": "mock",
    "session_reference": "session-sample-1"
  },
  "action": "session.login",
  "event_type": "auth",
  "outcome": "success",
  "target": {
    "type": "session",
    "id": "session-sample-1"
  },
  "scope": {
    "cloud_id": "lab-cloud",
    "region_id": "RegionOne",
    "project_id": "project-sample",
    "scope_type": "project",
    "scope_id": "project-sample"
  },
  "source": {
    "ip": "192.0.2.10",
    "trusted_proxy_chain": []
  },
  "request_id": "request-login-1",
  "correlation_id": "request-login-1",
  "operation_id": null,
  "external_execution_id": null,
  "service": "cloud-ui-api",
  "component": "security",
  "safe_error_code": null,
  "delivery_state": "pending",
  "metadata": {
    "provider": "mock"
  }
}
```

## Authorization denial

```json
{
  "event_id": "audit-sample-denied",
  "event_version": "1",
  "sink_id": "local-test",
  "occurred_at": "2026-06-22T12:01:00Z",
  "actor": {
    "type": "human",
    "id": "mock-user-operator",
    "display": "Operator",
    "authentication_method": "mock",
    "session_reference": "session-sample-1"
  },
  "action": "authorization.denied",
  "event_type": "authorization",
  "outcome": "failure",
  "target": {
    "type": "audit_event",
    "id": null
  },
  "scope": {
    "cloud_id": null,
    "region_id": null,
    "project_id": null,
    "scope_type": "project",
    "scope_id": "project-sample"
  },
  "source": {
    "ip": "192.0.2.10",
    "trusted_proxy_chain": ["198.51.100.1"]
  },
  "request_id": "request-denied-1",
  "correlation_id": "request-denied-1",
  "operation_id": null,
  "external_execution_id": null,
  "service": "cloud-ui-api",
  "component": "audit-api",
  "safe_error_code": "forbidden",
  "delivery_state": "pending",
  "metadata": {
    "capability": "audit.read",
    "code": "forbidden"
  }
}
```

## Audit export request

```json
{
  "event_id": "audit-sample-export",
  "event_version": "1",
  "sink_id": "local-test",
  "occurred_at": "2026-06-22T12:02:00Z",
  "actor": {
    "type": "human",
    "id": "mock-user-admin",
    "display": "Portal Admin",
    "authentication_method": "mock",
    "session_reference": "session-admin-1"
  },
  "action": "audit.export.requested",
  "event_type": "audit_access",
  "outcome": "success",
  "target": {
    "type": "audit_export",
    "id": "audit-export-sample"
  },
  "scope": {
    "cloud_id": null,
    "region_id": null,
    "project_id": null,
    "scope_type": "system",
    "scope_id": null
  },
  "source": {
    "ip": "192.0.2.20",
    "trusted_proxy_chain": []
  },
  "request_id": "request-export-1",
  "correlation_id": "request-export-1",
  "operation_id": null,
  "external_execution_id": null,
  "service": "cloud-ui-api",
  "component": "audit-api",
  "safe_error_code": null,
  "delivery_state": "pending",
  "metadata": {
    "from": "2026-06-22T00:00:00+00:00",
    "to": "2026-06-23T00:00:00+00:00",
    "limit": 100
  }
}
```

## Delivery heartbeat

```json
{
  "event_id": "audit-heartbeat",
  "occurred_at": "2026-06-22T12:03:00Z",
  "queue_depth": 2,
  "oldest_pending_age_seconds": 31.0
}
```

## Fluentd HTTP wrapper

`FluentdHttpAuditSink.build_payload()` wraps the sanitized envelope without changing field names:

```json
{
  "tag": "cloud_ui.audit",
  "time": "2026-06-22T12:00:03Z",
  "record": {
    "event_id": "audit-sample-login-success",
    "occurred_at": "2026-06-22T12:00:03Z",
    "metadata": {
      "token": "***"
    }
  }
}
```
