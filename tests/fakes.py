import math
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image

from nova_eink_display.clock import Clock
from nova_eink_display.display import SimulatedDisplay
from nova_eink_display.loop import Event, Inbox, Loop, Stop
from nova_eink_display.metrics import Metrics
from nova_eink_display.panel import Panel
from nova_eink_display.state import WearState
from nova_eink_display.world import World

TZ = ZoneInfo("Europe/Warsaw")
NOON = datetime(2026, 3, 17, 12, 0, tzinfo=TZ)


class FakeClock(Clock):
    def __init__(self, start: datetime = NOON) -> None:
        super().__init__(TZ)
        self.t = start.timestamp()

    def time(self) -> float:
        return self.t


class FakeInbox(Inbox):
    def __init__(self, clock: FakeClock) -> None:
        super().__init__(clock)
        self.fake_clock = clock
        self.script: list[tuple[float, Event]] = []

    def at(self, when: datetime, event: Event) -> None:
        self.script.append((when.timestamp(), event))
        self.script.sort(key=lambda item: item[0])

    def wait(self, deadline: float) -> Event | None:
        if self.script and self.script[0][0] <= deadline:
            when, event = self.script.pop(0)
            self.fake_clock.t = max(self.fake_clock.t, when)
            return event
        if math.isinf(deadline):
            raise AssertionError("nothing scheduled and no events left")
        self.fake_clock.t = max(self.fake_clock.t, deadline)
        return None


class Client:
    def __init__(self, stats: dict | None = None) -> None:
        self.stats = stats if stats is not None else {"cpu": 10.0, "mem": 40.0}
        self.error: str | None = None
        self.calls = 0

    def fetch_all(self) -> dict:
        self.calls += 1
        if self.error:
            return {"stats": {}, "error": self.error, "missing": []}
        return {"stats": dict(self.stats), "error": None, "missing": []}


class Compose:
    def __init__(self) -> None:
        self.worlds: list[World] = []

    def __call__(self, world: World) -> Image.Image:
        self.worlds.append(world)
        image = Image.new("1", (296, 128), 255)
        if world.screen.frame == "blink":
            image.putpixel((0, 0), 0)
        image.putpixel((1 + len(self.worlds) % 290, 1), 0)
        return image


class Driver(SimulatedDisplay):
    def __init__(self, clock: FakeClock) -> None:
        super().__init__()
        self.clock = clock
        self.calls: list[str] = []
        self.shown: list[tuple[float, bool]] = []

    def _record(self, kind: str, image: Image.Image) -> None:
        self.calls.append(kind)
        self.shown.append((self.clock.t, image.getpixel((0, 0)) == 0))

    def full(self, image: Image.Image) -> None:
        self._record("full", image)

    def partial(self, image: Image.Image) -> None:
        self._record("partial", image)

    def sleep(self) -> None:
        self.calls.append("sleep")


def build(
    start: datetime = NOON,
    limit: int = 16,
    client: Client | None = None,
    rng=None,
    metrics: Metrics | None = None,
) -> tuple[Loop, FakeInbox, Driver]:
    clock = FakeClock(start)
    inbox = FakeInbox(clock)
    driver = Driver(clock)
    panel = Panel(driver, WearState(None), limit, metrics or Metrics())
    loop = Loop(panel, Compose(), client or Client(), clock, inbox, 60, rng)
    return loop, inbox, driver


def run_until(loop: Loop, inbox: FakeInbox, when: datetime) -> None:
    inbox.at(when, Stop())
    loop.run()
