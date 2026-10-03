from datetime import timedelta

import pytest
from fakes import NOON, build, run_until

from nova_eink_display import loop as loop_module
from nova_eink_display.metrics import Metrics

LIMIT = 16
SECOND = timedelta(seconds=1)
MINUTE = timedelta(minutes=1)


class AlwaysBlink:
    def random(self) -> float:
        return 0.0

    def uniform(self, a: float, b: float) -> float:
        return a


@pytest.fixture
def metrics(monkeypatch: pytest.MonkeyPatch) -> Metrics:
    metrics = Metrics()
    monkeypatch.setattr(loop_module, "METRICS", metrics)
    return metrics


def peak_partials(calls: list[str]) -> int:
    peak = run = 0
    for call in calls:
        run = 0 if call == "full" else run + (call == "partial")
        peak = max(peak, run)
    return peak


@pytest.mark.parametrize("limit", [7, 8, 9, 16])
def test_partials_never_exceed_the_limit(metrics: Metrics, limit: int) -> None:
    loop, inbox, driver = build(limit=limit, rng=AlwaysBlink(), metrics=metrics)

    run_until(loop, inbox, NOON + 200 * MINUTE)

    assert metrics.blinks_total > 0
    assert peak_partials(driver.calls) <= limit


@pytest.mark.parametrize(
    ("before", "blinks"),
    [
        (LIMIT - 3, True),  # tick -> limit-2, blink -> limit
        (LIMIT - 2, False),  # tick -> limit-1, no room for two
        (LIMIT - 1, False),  # tick -> limit
    ],
)
def test_a_blink_needs_room_for_both_partials(
    metrics: Metrics, before: int, blinks: bool
) -> None:
    loop, inbox, _ = build(limit=LIMIT, rng=AlwaysBlink(), metrics=metrics)
    run_until(loop, inbox, NOON + 30 * SECOND)
    loop.panel.partials = before
    blinked = metrics.blinks_total

    run_until(loop, inbox, NOON + 90 * SECOND)

    assert (metrics.blinks_total > blinked) is blinks


def test_a_blink_is_counted_once_and_costs_two_partials(metrics: Metrics) -> None:
    loop, inbox, driver = build(rng=AlwaysBlink(), metrics=metrics)

    run_until(loop, inbox, NOON + 30 * SECOND)

    assert driver.calls == ["full", "partial", "partial"]
    assert metrics.blinks_total == 1
    assert metrics.refresh_total == {"full": 1, "partial": 2}
