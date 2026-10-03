from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

from nova_eink_display import main
from nova_eink_display.display import SimulatedDisplay
from nova_eink_display.screens.main_screen import MainScreen
from nova_eink_display.state import WearState

TZ = ZoneInfo("Europe/Warsaw")
NOON = datetime(2026, 3, 17, 12, 0, tzinfo=TZ)
MINUTE = timedelta(minutes=1)


class Client:
    def __init__(self) -> None:
        self.error: str | None = None

    def fetch_all(self) -> dict:
        if self.error:
            return {"stats": {}, "error": self.error, "missing": []}
        return {"stats": {"cpu": 10.0}, "error": None, "missing": []}


class UI:
    character = SimpleNamespace(last_mood="happy")

    def __init__(self) -> None:
        self.seen: list[datetime | None] = []

    def render_frame(self, data, alerts, is_blinking=False, now=None):
        self.seen.append(data.get("error_since"))
        return Image.new("1", (296, 128), 255)


@pytest.fixture
def parts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main.random, "random", lambda: 1.0)
    client, ui = Client(), UI()
    dashboard = main.Dashboard(SimulatedDisplay(), ui, client, TZ, WearState(None))
    return dashboard, client, ui


def test_since_is_the_first_failed_tick_and_clears_on_success(parts) -> None:
    dashboard, client, ui = parts

    dashboard.tick(NOON)
    client.error = "Prometheus Unreachable"
    dashboard.tick(NOON + MINUTE)
    dashboard.tick(NOON + 2 * MINUTE)
    client.error = None
    dashboard.tick(NOON + 3 * MINUTE)

    assert ui.seen == [None, NOON + MINUTE, NOON + MINUTE, None]


def test_a_new_outage_starts_a_new_since(parts) -> None:
    dashboard, client, ui = parts

    client.error = "Query Error"
    dashboard.tick(NOON)
    client.error = None
    dashboard.tick(NOON + MINUTE)
    client.error = "Query Error"
    dashboard.tick(NOON + 2 * MINUTE)

    assert ui.seen[-1] == NOON + 2 * MINUTE


@pytest.mark.parametrize(
    ("since", "expected"),
    [
        (NOON, ["> PROMETHEUS", "  UNREACHABLE", "SINCE 12:00"]),
        (None, ["> PROMETHEUS", "  UNREACHABLE"]),
    ],
)
def test_error_lines(since: datetime | None, expected: list[str]) -> None:
    assert MainScreen.error_lines("PROMETHEUS UNREACHABLE", since, 14) == expected
