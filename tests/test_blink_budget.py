from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

from nova_eink_display import main
from nova_eink_display.display import SimulatedDisplay
from nova_eink_display.metrics import Metrics
from nova_eink_display.panel import Panel
from nova_eink_display.state import WearState
from nova_eink_display.world import World

TZ = ZoneInfo("Europe/Warsaw")
LIMIT = 16
NOON = datetime(2026, 3, 17, 12, 0, tzinfo=TZ)


class Client:
    def fetch_all(self) -> dict:
        return {"stats": {"cpu": 10.0, "mem": 40.0}, "error": None, "missing": []}


def compose(world: World) -> Image.Image:
    return Image.new("1", (296, 128), 0 if world.screen.frame == "blink" else 255)


def build(limit: int = LIMIT, metrics: Metrics | None = None) -> main.Dashboard:
    panel = Panel(SimulatedDisplay(), WearState(None), limit, metrics or Metrics())
    return main.Dashboard(panel, compose, Client(), TZ)


@pytest.fixture(autouse=True)
def always_blink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main.random, "random", lambda: 0.0)


@pytest.fixture
def dashboard() -> main.Dashboard:
    return build()


def run_tick(dashboard: main.Dashboard) -> bool:
    frame, blink = dashboard.tick(NOON)
    if blink is None:
        return False

    dashboard.panel.show(blink)
    dashboard.panel.show(frame)
    return True


@pytest.mark.parametrize("limit", [7, 8, 9, 16])
def test_partials_never_exceed_the_limit(limit: int) -> None:
    dashboard = build(limit)

    peak = 0
    for _ in range(200):
        run_tick(dashboard)
        peak = max(peak, dashboard.panel.partials)

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
    dashboard.panel.partials = before

    assert run_tick(dashboard) is blinks


def test_a_blink_is_counted_once_and_costs_two_partials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "BLINK_SECONDS", 0)
    monkeypatch.setattr(main.random, "uniform", lambda a, b: 0)
    metrics = Metrics()
    monkeypatch.setattr(main, "METRICS", metrics)
    dashboard = build(metrics=metrics)

    run_tick(dashboard)
    frame, blink = dashboard.tick(NOON)
    assert blink is not None
    partials = metrics.refresh_total["partial"]

    dashboard.blink(frame, blink, next_tick=main.time.monotonic() + 30)

    assert metrics.blinks_total == 1
    assert metrics.refresh_total["partial"] - partials == 2
