import logging
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, SimpleQueue

from nova_eink_display import scheduler
from nova_eink_display.clock import Clock
from nova_eink_display.config import (
    FETCH_INTERVAL,
    NIGHT_END_HOUR,
    NIGHT_START_HOUR,
)
from nova_eink_display.metrics import METRICS
from nova_eink_display.world import Mode, Screen, World

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 5


@dataclass(frozen=True)
class Stop:
    pass


type Event = Stop


class Inbox:
    """The one queue every thread may write to."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.queue: SimpleQueue[Event] = SimpleQueue()

    def put(self, event: Event) -> None:
        self.queue.put(event)

    def wait(self, deadline: float) -> Event | None:
        """The next event, or None once `deadline` (wall-clock seconds) has
        passed with nothing arriving."""
        timeout = deadline - self.clock.time()
        try:
            if timeout <= 0:
                return self.queue.get_nowait()
            return self.queue.get(timeout=timeout)
        except Empty:
            return None


def is_night(now: datetime) -> bool:
    if NIGHT_START_HOUR == NIGHT_END_HOUR:
        return False

    if NIGHT_START_HOUR < NIGHT_END_HOUR:
        return NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR

    return now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR


def on_data(world: World | None, data: dict, now: datetime, night: bool) -> World:
    """A fetch result becomes the next World. Pure: no panel, no clock."""
    previous = world.screen if world else None

    since = None
    if data.get("error"):
        since = (previous.error_since if previous else None) or now

    screen = Screen.dashboard(data, now, since)

    if night and not screen.alerts:
        if world is not None and world.screen.mode is Mode.ASLEEP:
            return world
        return World(Screen.asleep(now, NIGHT_END_HOUR))

    return World(screen)


class Loop:
    """Waits for the earliest of the next data tick, the scheduler's next
    wake-up, or an event; hands it to its handler; draws the World if it
    changed."""

    def __init__(
        self,
        panel,
        compose,
        client,
        clock: Clock,
        inbox: Inbox,
        interval: int = FETCH_INTERVAL,
        rng: random.Random | None = None,
    ) -> None:
        self.panel = panel
        self.compose = compose
        self.client = client
        self.clock = clock
        self.inbox = inbox
        self.interval = interval
        self.rng = rng or random.Random()

        self.world: World | None = None
        self.frame = None
        self.next_tick = clock.time()
        self.failures = 0

    @property
    def mood(self) -> str:
        return self.world.screen.pose if self.world else "unknown"

    def _boundary(self) -> float:
        return (self.clock.time() // self.interval + 1) * self.interval

    def run(self) -> None:
        while True:
            wake = self.world.motion.next_wake if self.world else math.inf
            event = self.inbox.wait(min(self.next_tick, wake))

            if isinstance(event, Stop):
                logger.info("Stop requested")
                return

            now = self.clock.time()
            if now >= self.next_tick:
                self._guarded(self.data_tick)
                self.next_tick = self._boundary()
            elif now >= wake:
                self._guarded(self.wake)

    def _guarded(self, step) -> None:
        try:
            step()
            self.failures = 0
        except Exception:
            self.failures += 1
            METRICS.record_failure()
            logger.exception("Tick failed (%d in a row)", self.failures)
            if self.failures >= MAX_CONSECUTIVE_FAILURES:
                raise

    def data_tick(self) -> None:
        started = time.monotonic()
        data = self.client.fetch_all()
        METRICS.record_fetch(
            time.monotonic() - started,
            data.get("error"),
            len(data.get("missing", [])),
        )

        now = self.clock.now()
        new = on_data(self.world, data, now, is_night(now))
        try:
            self.present(new)
            self.world = scheduler.plan_blink(
                new,
                self.clock.time(),
                self._boundary(),
                self.panel.partials_left,
                self.rng,
                self._shows_blink,
            )
        finally:
            METRICS.record_tick(
                len(new.screen.alerts), new.screen.pose, self.panel.asleep
            )

    def wake(self) -> None:
        assert self.world is not None
        old = self.world
        new = scheduler.on_wake(old, self.clock.time())
        self.present(new)
        if new.screen.frame == "blink" and old.screen.frame != "blink":
            METRICS.record_blink()

    def present(self, new: World) -> None:
        """Draw `new` if it differs from what is on the glass. A change of
        alerts or of mode (dashboard / asleep) is a full refresh."""
        old = self.world
        if old is not None and new.screen == old.screen:
            self.world = new
            return

        self.frame = self.compose(new)
        full = (
            old is None
            or new.screen.alerts != old.screen.alerts
            or new.screen.mode is not old.screen.mode
        )
        self.panel.show(self.frame, full=full)
        self.world = new

        if new.screen.mode is Mode.ASLEEP:
            self.panel.sleep()
            logger.info("Night mode: panel asleep until %02d:00", NIGHT_END_HOUR)

    def _shows_blink(self, world: World) -> bool:
        blink = self.compose(World(world.screen.showing("blink")))
        return self.frame is not None and blink.tobytes() != self.frame.tobytes()

    def shutdown(self) -> None:
        offline = World(Screen.offline(self.clock.now()))
        self.panel.show(self.compose(offline), full=True)
        self.panel.sleep()
        self.world = offline
