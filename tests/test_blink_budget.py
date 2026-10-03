from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

from nova_eink_display import main
from nova_eink_display.display import SimulatedDisplay
from nova_eink_display.metrics import Metrics
from nova_eink_display.state import WearState

TZ = ZoneInfo("Europe/Warsaw")
LIMIT = 16
NOON = datetime(2026, 3, 17, 12, 0, tzinfo=TZ)


class Client:
    def fetch_all(self) -> dict:
        return {"stats": {"cpu": 10.0, "mem": 40.0}, "error": None, "missing": []}


class UI:
    character = SimpleNamespace(last_mood="happy")

    def render_frame(self, data, alerts, is_blinking=False, now=None):
        return Image.new("1", (296, 128), 0 if is_blinking else 255)


@pytest.fixture
def dashboard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> main.Dashboard:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main.random, "random", lambda: 0.0)
    monkeypatch.setattr(main, "MAX_PARTIAL_REFRESHES", LIMIT)
    return main.Dashboard(SimulatedDisplay(), UI(), Client(), TZ, WearState(None))


def run_tick(dashboard: main.Dashboard) -> bool:
    frame, blink = dashboard.tick(NOON)
    if blink is None:
        return False

    dashboard.render(blink)
    dashboard.render(frame)
    return True


@pytest.mark.parametrize("limit", [7, 8, 9, 16])
def test_partials_never_exceed_the_limit(
    dashboard: main.Dashboard, monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    monkeypatch.setattr(main, "MAX_PARTIAL_REFRESHES", limit)

    peak = 0
    for _ in range(200):
        run_tick(dashboard)
        peak = max(peak, dashboard.display.partial_count)

    assert peak <= limit


@pytest.mark.parametrize(
    ("before", "blinks"),
    [
        (LIMIT - 3, True),  # tick -> limit-2, blink -> limit
        (LIMIT - 2, False),  # tick -> limit-1, no room for two
        (LIMIT - 1, False),  # tick -> limit
    ],
)
def test_a_blink_needs_room_for_both_partials(
    dashboard: main.Dashboard, before: int, blinks: bool
) -> None:
    run_tick(dashboard)
    dashboard.display.partial_count = before

    assert run_tick(dashboard) is blinks


def test_a_blink_is_counted_once_and_costs_two_partials(
    dashboard: main.Dashboard, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "BLINK_SECONDS", 0)
    monkeypatch.setattr(main.random, "uniform", lambda a, b: 0)
    metrics = Metrics()
    monkeypatch.setattr(main, "METRICS", metrics)

    run_tick(dashboard)
    frame, blink = dashboard.tick(NOON)
    assert blink is not None
    partials = metrics.refresh_total["partial"]

    dashboard.blink(frame, blink, next_tick=main.time.monotonic() + 30)

    assert metrics.blinks_total == 1
    assert metrics.refresh_total["partial"] - partials == 2
