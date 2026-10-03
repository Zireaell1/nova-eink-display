import pytest
from PIL import Image

from nova_eink_display.display import DisplayDriver
from nova_eink_display.metrics import Metrics
from nova_eink_display.panel import Panel
from nova_eink_display.state import WearState

LIMIT = 4
FRAME = Image.new("1", (296, 128), 255)


class Driver(DisplayDriver):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def init(self) -> None:
        self.calls.append("init")

    def full(self, image: Image.Image) -> None:
        self.calls.append("full")

    def partial(self, image: Image.Image) -> None:
        self.calls.append("partial")

    def sleep(self) -> None:
        self.calls.append("sleep")


@pytest.fixture
def parts(tmp_path) -> tuple[Panel, Driver, WearState, Metrics]:
    driver, metrics = Driver(), Metrics()
    wear = WearState(str(tmp_path / "wear.json"))
    return Panel(driver, wear, LIMIT, metrics), driver, wear, metrics


def test_partials_until_the_limit_then_a_full(parts) -> None:
    panel, driver, _, _ = parts

    for _ in range(LIMIT + 2):
        panel.show(FRAME)

    assert driver.calls == ["partial"] * LIMIT + ["full", "partial"]


def test_partials_left_counts_down_and_resets(parts) -> None:
    panel, _, _, _ = parts

    assert panel.partials_left == LIMIT
    panel.show(FRAME)
    panel.show(FRAME)
    assert panel.partials_left == LIMIT - 2
    panel.show(FRAME, full=True)
    assert panel.partials_left == LIMIT


def test_waking_from_sleep_is_always_a_full_refresh(parts) -> None:
    panel, driver, _, _ = parts

    panel.sleep()
    panel.show(FRAME)

    assert driver.calls == ["sleep", "full"]
    assert not panel.asleep


def test_sleep_is_idempotent(parts) -> None:
    panel, driver, _, _ = parts

    panel.sleep()
    panel.sleep()

    assert driver.calls == ["sleep"]
    assert panel.asleep


def test_start_resets_the_budget(parts) -> None:
    panel, driver, _, _ = parts
    panel.show(FRAME)
    panel.sleep()

    panel.start()

    assert driver.calls[-1] == "init"
    assert panel.partials == 0
    assert not panel.asleep


def test_every_refresh_is_recorded_and_persisted(parts) -> None:
    panel, _, wear, metrics = parts

    panel.show(FRAME, full=True)
    panel.show(FRAME)
    panel.show(FRAME)

    assert metrics.refresh_total == {"full": 1, "partial": 2}
    assert metrics.partials_since_full == 2
    assert wear.load()["refresh_total"] == {"full": 1, "partial": 2}
