from dataclasses import FrozenInstanceError
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

from nova_eink_display.compose import Composer
from nova_eink_display.poses import PoseImages
from nova_eink_display.world import Mode, Screen, World

TZ = ZoneInfo("Europe/Warsaw")
NOON = datetime(2026, 3, 17, 12, 0, tzinfo=TZ)


def test_dashboard_screen_carries_alerts_and_pose() -> None:
    screen = Screen.dashboard({"stats": {"cpu": 97.0}}, NOON)

    assert screen.alerts == ("CPU 97%",)
    assert screen.pose == "concerned"
    assert screen.mode is Mode.DASHBOARD
    assert screen.frame == "base"


def test_a_fetch_error_leads_the_alerts_and_disconnects() -> None:
    since = NOON.replace(hour=11)
    screen = Screen.dashboard({"stats": {}, "error": "Query Error"}, NOON, since)

    assert screen.alerts == ("API ERR: Query Error",)
    assert screen.error_since == since
    assert screen.pose == "disconnected"


def test_asleep_and_offline_pick_their_own_poses() -> None:
    assert Screen.asleep(NOON.replace(hour=23), 6).pose == "sleep"
    assert Screen.offline(NOON).pose == "disconnected"


def test_showing_changes_only_the_frame() -> None:
    screen = Screen.dashboard({"stats": {"cpu": 10.0}}, NOON)
    blink = screen.showing("blink")

    assert blink.frame == "blink"
    assert blink.stats == screen.stats
    assert blink.pose == screen.pose
    assert screen.frame == "base"


@pytest.mark.parametrize("field", ["pose", "frame", "stats"])
def test_screens_are_immutable(field: str) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(Screen(now=NOON), field, None)


@pytest.fixture
def art(tmp_path):
    for name, shade in (("happy", 0), ("happy-eyes-closed", 1), ("smug", 2)):
        image = Image.new("1", (100, 96), 255)
        image.putpixel((shade, 0), 0)
        image.save(tmp_path / f"character-{name}.png")
    return PoseImages(str(tmp_path))


def ink(image: Image.Image | None) -> tuple[int, int] | None:
    assert image is not None
    return next((x, 0) for x in range(image.width) if image.getpixel((x, 0)) == 0)


def test_a_missing_pose_falls_back_to_happy(art: PoseImages) -> None:
    assert ink(art.frame("music")) == (0, 0)


def test_a_missing_frame_falls_back_to_its_own_pose(art: PoseImages) -> None:
    assert ink(art.frame("smug", "blink")) == (2, 0)


def test_blink_uses_the_eyes_closed_file(art: PoseImages) -> None:
    assert ink(art.frame("happy", "blink")) == (1, 0)


def test_no_art_at_all_is_none(tmp_path) -> None:
    assert PoseImages(str(tmp_path)).frame("happy") is None


def test_compose_is_deterministic(art: PoseImages) -> None:
    compose = Composer(296, 128, art)
    world = World(Screen.dashboard({"stats": {"cpu": 10.0}}, NOON))

    assert compose(world).tobytes() == compose(world).tobytes()
    assert compose(world, invert=True).tobytes() != compose(world).tobytes()
