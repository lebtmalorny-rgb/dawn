from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cloud_ui.audit.models import AuditOutcome

MetadataPolicy = Literal["allowlisted", "summary_only"]

DKB_MANDATORY_FIELD_MAP = {
    "ДКБ-49.01": ("occurred_at",),
    "ДКБ-49.02": ("actor_id", "actor_display"),
    "ДКБ-49.03": ("action",),
    "ДКБ-49.04": ("event_type",),
    "ДКБ-49.05": ("outcome",),
    "ДКБ-49.08": ("target_type", "target_id"),
}


@dataclass(frozen=True)
class AuditActionDefinition:
    action: str
    event_type: str
    allowed_outcomes: frozenset[AuditOutcome]
    metadata_policy: MetadataPolicy
    dkb_fields: frozenset[str]


class UnknownAuditAction(ValueError):
    def __init__(self, action: str) -> None:
        super().__init__(f"unknown audit action: {action}")
        self.action = action


_ALL_DKB_49_FIELDS = frozenset(DKB_MANDATORY_FIELD_MAP)


def _definition(
    action: str,
    event_type: str,
    outcomes: set[AuditOutcome],
    *,
    metadata_policy: MetadataPolicy = "allowlisted",
    dkb_fields: frozenset[str] = _ALL_DKB_49_FIELDS,
) -> AuditActionDefinition:
    return AuditActionDefinition(
        action=action,
        event_type=event_type,
        allowed_outcomes=frozenset(outcomes),
        metadata_policy=metadata_policy,
        dkb_fields=dkb_fields,
    )


REGISTERED_ACTIONS: tuple[AuditActionDefinition, ...] = (
    _definition("session.login", "auth", {"success", "failure"}),
    _definition("session.logout", "auth", {"success"}),
    _definition("session.revoke", "auth", {"success", "failure"}),
    _definition("session.timeout", "auth", {"failure"}),
    _definition("session.limit_reached", "auth", {"failure"}),
    _definition("session.required", "auth", {"failure"}),
    _definition("csrf.denied", "security_denial", {"failure"}),
    _definition("origin.denied", "security_denial", {"failure"}),
    _definition("authorization.denied", "authorization", {"failure"}),
    _definition("openstack.denied", "authorization", {"failure"}),
    _definition("instance.refresh.requested", "inventory", {"success", "failure"}),
    _definition("group.create", "group", {"success", "failure"}),
    _definition("group.update", "group", {"success", "failure"}),
    _definition("group.delete", "group", {"success", "failure"}),
    _definition("group.member.add", "group", {"success", "failure"}),
    _definition("group.member.remove", "group", {"success", "failure"}),
    _definition("group.preview", "group", {"success", "failure"}),
    _definition("operation.accepted", "operation", {"success"}),
    _definition("operation.dispatched", "operation", {"success", "unknown", "failure"}),
    _definition("operation.completed", "operation", {"success", "failure", "unknown"}),
    _definition("operation.cancelled", "operation", {"success", "failure"}),
    _definition("watcher.view", "openstack_module", {"success", "failure"}),
    _definition("masakari.view", "openstack_module", {"success", "failure"}),
    _definition("audit.events.list", "audit_access", {"success", "failure"}),
    _definition("audit.event.detail", "audit_access", {"success", "failure"}),
    _definition("audit.export.requested", "audit_access", {"success", "failure"}),
    _definition("audit.delivery.failed", "audit_delivery", {"failure"}),
    _definition("audit.delivery.recovered", "audit_delivery", {"success"}),
    _definition("audit.delivery.heartbeat", "audit_delivery", {"success", "failure", "unknown"}),
)

_ACTION_INDEX = {definition.action: definition for definition in REGISTERED_ACTIONS}


def get_action_definition(action: str) -> AuditActionDefinition:
    try:
        return _ACTION_INDEX[action]
    except KeyError as exc:
        raise UnknownAuditAction(action) from exc

