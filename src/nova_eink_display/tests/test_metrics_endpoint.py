import io
import socket
import sys
import urllib.error
import urllib.request

from PIL import Image

from nova_eink_display.metrics import CONTENT_TYPE, METRICS, PREVIEW_CONTENT_TYPE, serve

FAILURES: list[str] = []


def check(condition: object, description: str) -> None:
    if condition:
        print(f"ok   {description}")
        return

    print(f"FAIL {description}")
    FAILURES.append(description)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def get(url: str) -> tuple[int, str, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            content_type = response.headers.get("Content-Type", "")
            return response.status, content_type, response.read()
    except urllib.error.HTTPError as error:
        content_type = error.headers.get("Content-Type", "")
        return error.code, content_type, error.read()


def main() -> int:
    check(serve("127.0.0.1", 0) is None, "port 0 disables the endpoint")

    port = free_port()
    server = serve("127.0.0.1", port)
    if server is None:
        print(f"FAIL could not bind 127.0.0.1:{port}")
        return 1

    base = f"http://127.0.0.1:{port}"

    try:
        status, content_type, body = get(f"{base}/preview.png")
        check(
            status == 503, f"/preview.png is 503 before the first render (got {status})"
        )

        METRICS.record_refresh("full", 0)
        METRICS.record_refresh("partial", 1)
        METRICS.record_fetch(0.25, None, 0)
        METRICS.record_fetch(0.25, "timeout", 1)
        METRICS.record_tick(2, "happy", False)
        METRICS.record_failure()
        METRICS.record_frame(Image.new("1", (296, 128), 255))

        status, content_type, body = get(f"{base}/metrics")
        text = body.decode()
        check(status == 200, f"/metrics is 200 (got {status})")
        check(
            content_type == CONTENT_TYPE,
            f"/metrics content type (got {content_type!r})",
        )
        check(text.endswith("\n"), "/metrics body ends with a newline")

        for name in (
            "eink_refresh_total",
            "eink_partials_since_full",
            "eink_panel_asleep",
            "eink_alerts_active",
            "eink_metrics_missing",
            "eink_fetch_duration_seconds",
            "eink_last_render_timestamp_seconds",
            "eink_tick_failures_total",
            "eink_character_mood",
            "eink_fetch_errors_total",
        ):
            check(f"# TYPE {name} " in text, f"/metrics declares a TYPE for {name}")

        check('eink_refresh_total{kind="full"} 1' in text, "full refreshes counted")
        check(
            'eink_refresh_total{kind="partial"} 1' in text, "partial refreshes counted"
        )
        check(
            'eink_character_mood{mood="happy"} 1' in text, "mood is exported as a label"
        )
        check(
            'eink_fetch_errors_total{reason="timeout"} 1' in text,
            "fetch errors are labelled",
        )
        check("eink_tick_failures_total 1" in text, "tick failures counted")

        samples = [
            line for line in text.splitlines() if line and not line.startswith("#")
        ]
        check(
            all(len(line.rsplit(" ", 1)) == 2 for line in samples),
            "every sample line carries a value",
        )
        check(
            all(_is_number(line.rsplit(" ", 1)[1]) for line in samples),
            "every sample value parses as a float",
        )

        status, content_type, body = get(f"{base}/preview.png")
        check(status == 200, f"/preview.png is 200 after a render (got {status})")
        check(
            content_type == PREVIEW_CONTENT_TYPE,
            f"preview content type (got {content_type!r})",
        )
        check(body[:8] == b"\x89PNG\r\n\x1a\n", "preview body is a PNG")

        with Image.open(io.BytesIO(body)) as image:
            check(
                image.size == (296, 128), f"preview is panel sized (got {image.size})"
            )

        status, _, _ = get(f"{base}/nope")
        check(status == 404, f"unknown routes are 404 (got {status})")

        status, _, _ = get(f"{base}/metrics?collect=all")
        check(status == 200, f"/metrics ignores a query string (got {status})")
    finally:
        server.shutdown()
        server.server_close()

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed")
        return 1

    print("\nall checks passed")
    return 0


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
