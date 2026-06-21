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

    token = codec.encode(payload)

    assert codec.decode(token) == payload
    assert "vm-0001" not in token


def test_cursor_tampering_is_rejected() -> None:
    codec = CursorCodec(signing_key="dev-inventory-cursor-key")
    token = codec.encode({"resource": "instances", "last": {"id": "i-1"}})

    bad_token = token[:-2] + "aa"

    try:
        codec.decode(bad_token)
    except CursorTampered as exc:
        assert exc.code == "cursor_tampered"
    else:
        raise AssertionError("expected CursorTampered")


def test_cursor_payload_is_signed_not_encrypted() -> None:
    codec = CursorCodec(signing_key="dev-inventory-cursor-key")
    token = codec.encode({"resource": "instances", "last": {"name": "vm-0001"}})

    encoded_payload, _signature = token.split(".")
    decoded_payload = base64.urlsafe_b64decode(
        f"{encoded_payload}{'=' * (-len(encoded_payload) % 4)}"
    )

    assert json.loads(decoded_payload) == {"last": {"name": "vm-0001"}, "resource": "instances"}
