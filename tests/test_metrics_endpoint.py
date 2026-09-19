import io
import socket
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest
from PIL import Image

import nova_eink_display.metrics as metrics_module
from nova_eink_display.metrics import (
    CONTENT_TYPE,
    PREVIEW_CONTENT_TYPE,
    Metrics,
    serve,
)

FAMILIES = [
    "eink_refresh_total",
    "eink_partials_since_full",
    "eink_panel_asleep",
    "eink_alerts_active",
    "eink_metrics_missing",
    "eink_fetch_duration_seconds",
    "eink_last_render_timestamp_seconds",
    "eink_tick_failures_total",
    "eink_starts_total",
    "eink_wear_persisted",
    "eink_character_mood",
]


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def metrics(monkeypatch: pytest.MonkeyPatch) -> Metrics:
    """A fresh Metrics in place of the module global, so tests cannot leak
    counters into each other. _Handler reads the global per request, so the
    running server picks this up too."""
    fresh = Metrics()
    monkeypatch.setattr(metrics_module, "METRICS", fresh)
    return fresh


@pytest.fixture(scope="session")
def endpoint() -> Iterator[str]:
    port = free_port()
    server = serve("127.0.0.1", port)
    assert server is not None, f"could not bind 127.0.0.1:{port}"

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


def get(url: str) -> tuple[int, str, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return (
                response.status,
                response.headers.get("Content-Type", ""),
                response.read(),
            )
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Content-Type", ""), error.read()


@pytest.fixture
def scraped(endpoint: str, metrics: Metrics) -> str:
    metrics.record_refresh("full", 0)
    metrics.record_refresh("partial", 1)
    metrics.record_fetch(0.25, None, 0)
    metrics.record_fetch(0.25, "timeout", 1)
    metrics.record_tick(2, "happy", asleep=False)
    metrics.record_tick(2, "sleep", asleep=True)
    metrics.record_failure()

    status, content_type, body = get(f"{endpoint}/metrics")
    assert status == 200
    assert content_type == CONTENT_TYPE
    return body.decode()


def test_body_is_newline_terminated(scraped: str) -> None:
    assert scraped.endswith("\n")


@pytest.mark.parametrize("family", FAMILIES)
def test_every_family_declares_a_type(scraped: str, family: str) -> None:
    assert f"# TYPE {family} " in scraped


@pytest.mark.parametrize(
    "sample",
    [
        'eink_refresh_total{kind="full"} 1',
        'eink_refresh_total{kind="partial"} 1',
        'eink_fetch_errors_total{reason="timeout"} 1',
        "eink_tick_failures_total 1",
        "eink_panel_asleep 1",
    ],
)
def test_expected_samples_are_present(scraped: str, sample: str) -> None:
    assert sample in scraped


def test_mood_is_an_enum_gauge(scraped: str) -> None:
    assert 'eink_character_mood{mood="sleep"} 1' in scraped
    assert 'eink_character_mood{mood="happy"} 0' in scraped
    assert 'eink_character_mood{mood="unknown"}' not in scraped


def test_every_sample_parses(scraped: str) -> None:
    for line in scraped.splitlines():
        if not line or line.startswith("#"):
            continue

        name, _, value = line.rpartition(" ")
        assert name, line
        float(value)


def test_preview_is_unavailable_before_the_first_render(
    endpoint: str, metrics: Metrics
) -> None:
    status, _, _ = get(f"{endpoint}/preview.png")
    assert status == 503


def test_preview_serves_the_last_frame(endpoint: str, metrics: Metrics) -> None:
    metrics.record_frame(Image.new("1", (296, 128), 255))

    status, content_type, body = get(f"{endpoint}/preview.png")
    assert status == 200
    assert content_type == PREVIEW_CONTENT_TYPE
    assert body[:8] == b"\x89PNG\r\n\x1a\n"

    with Image.open(io.BytesIO(body)) as image:
        assert image.size == (296, 128)


def test_unknown_routes_are_404(endpoint: str) -> None:
    status, _, _ = get(f"{endpoint}/nope")
    assert status == 404


def test_a_query_string_is_ignored(endpoint: str, metrics: Metrics) -> None:
    status, _, _ = get(f"{endpoint}/metrics?collect=all")
    assert status == 200


def test_port_zero_disables_the_endpoint() -> None:
    assert serve("127.0.0.1", 0) is None
