import json
import time
from urllib.parse import urlparse
from urllib.request import urlopen


def _ensure_local_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("smoke checks may only call local HTTP endpoints")


def wait_json(url: str, attempts: int = 30) -> dict[str, object]:
    _ensure_local_http_url(url)
    last_error = "no response"
    for _ in range(attempts):
        try:
            with urlopen(url, timeout=3) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc.__class__.__name__
            time.sleep(2)
    raise RuntimeError(f"{url} did not return JSON: {last_error}")


def wait_http_ok(url: str, attempts: int = 30) -> None:
    _ensure_local_http_url(url)
    last_error = "no response"
    for _ in range(attempts):
        try:
            with urlopen(url, timeout=3) as response:  # noqa: S310
                if response.status == 200:
                    return
                last_error = f"HTTP {response.status}"
        except Exception as exc:
            last_error = exc.__class__.__name__
        time.sleep(2)
    raise RuntimeError(f"{url} did not return HTTP 200: {last_error}")


def main() -> int:
    live = wait_json("http://localhost:8080/health/live")
    if live.get("status") != "ok":
        raise RuntimeError("API liveness status is not ok")

    ready = wait_json("http://localhost:8080/api/v1/health/ready")
    if ready.get("status") != "ok":
        raise RuntimeError("API readiness status is not ok")

    wait_http_ok("http://localhost:3000")

    print("smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
