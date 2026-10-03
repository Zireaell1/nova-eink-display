from datetime import datetime, timedelta

import pytest
from fakes import NOON, Client, build, run_until

from nova_eink_display.screens.main_screen import MainScreen

MINUTE = timedelta(minutes=1)
HALF = timedelta(seconds=30)


class NeverBlink:
    def random(self) -> float:
        return 1.0

    def uniform(self, a: float, b: float) -> float:
        return a


def ticks(script: list[str | None]) -> list[datetime | None]:
    client = Client()
    loop, inbox, _ = build(client=client, rng=NeverBlink())
    for minute, error in enumerate(script):
        client.error = error
        run_until(loop, inbox, NOON + minute * MINUTE + HALF)
    return [world.screen.error_since for world in loop.compose.worlds]


def test_since_is_the_first_failed_tick_and_clears_on_success() -> None:
    down = "Prometheus Unreachable"

    assert ticks([None, down, down, None]) == [None, NOON + MINUTE, NOON + MINUTE, None]


def test_a_new_outage_starts_a_new_since() -> None:
    since = ticks(["Query Error", None, "Query Error"])

    assert since[-1] == NOON + 2 * MINUTE


@pytest.mark.parametrize(
    ("since", "expected"),
    [
        (NOON, ["> PROMETHEUS", "  UNREACHABLE", "SINCE 12:00"]),
        (None, ["> PROMETHEUS", "  UNREACHABLE"]),
    ],
)
def test_error_lines(since: datetime | None, expected: list[str]) -> None:
    assert MainScreen.error_lines("PROMETHEUS UNREACHABLE", since, 14) == expected
