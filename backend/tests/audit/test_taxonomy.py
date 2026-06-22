from __future__ import annotations

import pytest

from cloud_ui.audit.taxonomy import (
    DKB_MANDATORY_FIELD_MAP,
    REGISTERED_ACTIONS,
    UnknownAuditAction,
    get_action_definition,
)


def test_existing_security_action_is_registered_with_dkb_mapping() -> None:
    definition = get_action_definition("session.login")

    assert definition.action == "session.login"
    assert definition.event_type == "auth"
    assert definition.allowed_outcomes == frozenset({"success", "failure"})
    assert "ДКБ-49.02" in definition.dkb_fields
    assert definition.metadata_policy == "allowlisted"


def test_e07_delivery_and_audit_access_actions_are_registered() -> None:
    actions = {definition.action for definition in REGISTERED_ACTIONS}

    assert "audit.events.list" in actions
    assert "audit.export.requested" in actions
    assert "audit.delivery.failed" in actions
    assert "audit.delivery.recovered" in actions
    assert "audit.delivery.heartbeat" in actions


def test_unknown_audit_action_fails_closed() -> None:
    with pytest.raises(UnknownAuditAction):
        get_action_definition("raw.unreviewed.action")


def test_dkb_49_mandatory_field_map_covers_portal_event_fields() -> None:
    assert DKB_MANDATORY_FIELD_MAP == {
        "ДКБ-49.01": ("occurred_at",),
        "ДКБ-49.02": ("actor_id", "actor_display"),
        "ДКБ-49.03": ("action",),
        "ДКБ-49.04": ("event_type",),
        "ДКБ-49.05": ("outcome",),
        "ДКБ-49.08": ("target_type", "target_id"),
    }
