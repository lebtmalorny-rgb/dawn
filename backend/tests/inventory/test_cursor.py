import base64
import json

from cloud_ui.inventory.cursor import CursorCodec, CursorTampered


def test_cursor_round_trip_preserves_payload() -> None:
    codec = CursorCodec(signing_key="dev-inventory-cursor-key")
    payload = {
        "resource": "instances",
        "sort": "name.asc",
        "filters_hash": "abc",
        "last": {"name": "vm-0001", "id": "instance-0001"},
    }

    cursor_value = codec.encode(payload)

    assert codec.decode(cursor_value) == payload
    assert "vm-0001" not in cursor_value


def test_cursor_tampering_is_rejected() -> None:
    codec = CursorCodec(signing_key="dev-inventory-cursor-key")
    cursor_value = codec.encode({"resource": "instances", "last": {"id": "i-1"}})

    bad_cursor = cursor_value[:-2] + "aa"

    try:
        codec.decode(bad_cursor)
    except CursorTampered as exc:
        assert exc.code == "cursor_tampered"
    else:
        raise AssertionError("expected CursorTampered")


def test_cursor_payload_is_signed_not_encrypted() -> None:
    codec = CursorCodec(signing_key="dev-inventory-cursor-key")
    cursor_value = codec.encode({"resource": "instances", "last": {"name": "vm-0001"}})

    encoded_payload, _signature = cursor_value.split(".")
    decoded_payload = base64.urlsafe_b64decode(
        f"{encoded_payload}{'=' * (-len(encoded_payload) % 4)}"
    )

    assert json.loads(decoded_payload) == {"last": {"name": "vm-0001"}, "resource": "instances"}
