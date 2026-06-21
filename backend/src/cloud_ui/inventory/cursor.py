from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any


class CursorTampered(Exception):
    code = "cursor_tampered"

    def __init__(self) -> None:
        super().__init__("Inventory cursor is malformed or signature verification failed")


class CursorCodec:
    def __init__(self, *, signing_key: str) -> None:
        self._signing_key = signing_key.encode("utf-8")

    def encode(self, payload: dict[str, Any]) -> str:
        raw_payload = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        encoded_payload = _base64url_encode(raw_payload)
        signature = hmac.new(
            self._signing_key,
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{encoded_payload}.{_base64url_encode(signature)}"

    def decode(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 2:
            raise CursorTampered()
        encoded_payload, encoded_signature = parts

        try:
            signature = _base64url_decode(encoded_signature)
            encoded_payload_bytes = encoded_payload.encode("ascii")
        except (ValueError, UnicodeEncodeError) as exc:
            raise CursorTampered() from exc

        expected_signature = hmac.new(
            self._signing_key,
            encoded_payload_bytes,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise CursorTampered()

        try:
            raw_payload = _base64url_decode(encoded_payload)
            payload = json.loads(raw_payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            raise CursorTampered() from exc

        if not isinstance(payload, dict):
            raise CursorTampered()
        return payload


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(
            f"{value}{padding}".encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("invalid base64url value") from exc
