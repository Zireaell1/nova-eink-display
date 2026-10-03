from datetime import datetime, timedelta

import pytest
from fakes import NOON, TZ, Client, build, run_until

from nova_eink_display import loop as loop_module
from nova_eink_display.loop import MAX_CONSECUTIVE_FAILURES, Stop
from nova_eink_display.metrics import Metrics
from nova_eink_display.world import Mode

SECOND = timedelta(seconds=1)
MINUTE = timedelta(minutes=1)


class NeverBlink:
    def random(self) -> float:
        return 1.0

    def uniform(self, a: float, b: float) -> float:
        return a


class BlinkAfter:
    def __init__(self, delay: float) -> None:
        self.delay = delay

    def random(self) -> float:
        return 0.0

    def uniform(self, a: float, b: float) -> float:
        return self.delay


@pytest.fixture(autouse=True)
def metrics(monkeypatch: pytest.MonkeyPatch) -> Metrics:
    metrics = Metrics()
    monkeypatch.setattr(loop_module, "METRICS", metrics)
    return metrics


def drawn(loop) -> list[datetime]:
    return [world.screen.now for world in loop.compose.worlds]


def test_first_tick_is_immediate_then_aligned_to_the_minute() -> None:
    start = NOON + 17 * SECOND
    loop, inbox, _ = build(start=start, rng=NeverBlink())

    run_until(loop, inbox, NOON + 2 * MINUTE + SECOND)

    assert drawn(loop) == [start, NOON + MINUTE, NOON + 2 * MINUTE]


def test_alert_changes_are_full_refreshes() -> None:
    client = Client()
    loop, inbox, driver = build(client=client, rng=NeverBlink())

    run_until(loop, inbox, NOON + 30 * SECOND)
    client.stats["cpu"] = 97.0
    run_until(loop, inbox, NOON + 90 * SECOND)
    run_until(loop, inbox, NOON + 150 * SECOND)
    client.stats["cpu"] = 10.0
    run_until(loop, inbox, NOON + 210 * SECOND)

    assert driver.calls == ["full", "full", "partial", "full"]


def test_night_sleeps_once_and_wakes_with_a_full_refresh() -> None:
    start = datetime(2026, 3, 17, 22, 59, tzinfo=TZ)
    loop, inbox, driver = build(start=start, rng=NeverBlink())

    run_until(loop, inbox, datetime(2026, 3, 18, 6, 0, 30, tzinfo=TZ))

    assert driver.calls == ["full", "full", "sleep", "full"]
    assert loop.world is not None
    assert loop.world.screen.mode is Mode.DASHBOARD


def test_a_blink_lands_inside_the_minute(metrics: Metrics) -> None:
    loop, inbox, driver = build(rng=BlinkAfter(10.0))

    run_until(loop, inbox, NOON + 30 * SECOND)

    tick = NOON.timestamp()
    assert driver.shown == [(tick, False), (tick + 10, True), (tick + 11, False)]
    assert driver.calls == ["full", "partial", "partial"]
    assert metrics.blinks_total == 1
    assert loop.world is not None
    assert loop.world.motion.next_wake == float("inf")


def test_stop_ends_the_loop_and_shutdown_draws_offline() -> None:
    loop, inbox, driver = build(rng=NeverBlink())
    inbox.at(NOON + 5 * SECOND, Stop())

    loop.run()
    loop.shutdown()

    assert driver.calls == ["full", "full", "sleep"]
    assert loop.world is not None
    assert loop.world.screen.mode is Mode.OFFLINE


class Flaky(Client):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures

    def fetch_all(self) -> dict:
        if self.failures:
            self.failures -= 1
            raise RuntimeError("boom")
        return super().fetch_all()


def test_a_failing_tick_is_counted_and_the_loop_carries_on(metrics: Metrics) -> None:
    loop, inbox, driver = build(client=Flaky(2), rng=NeverBlink())

    run_until(loop, inbox, NOON + 2 * MINUTE + SECOND)

    assert metrics.tick_failures_total == 2
    assert driver.calls == ["full"]
    assert loop.failures == 0


def test_too_many_failures_in_a_row_stop_the_loop(metrics: Metrics) -> None:
    loop, inbox, _ = build(client=Flaky(99), rng=NeverBlink())
    inbox.at(NOON + 99 * MINUTE, Stop())

    with pytest.raises(RuntimeError):
        loop.run()

    assert metrics.tick_failures_total == MAX_CONSECUTIVE_FAILURES
