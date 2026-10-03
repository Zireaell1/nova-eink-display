import math
import random
from collections.abc import Callable
from dataclasses import replace

from nova_eink_display.config import BLINK_PROBABILITY, BLINK_SECONDS
from nova_eink_display.world import Mode, Motion, World

BLINK = (("blink", BLINK_SECONDS), ("base", 0.0))


def plan_blink(
    world: World,
    now: float,
    deadline: float,
    partials_left: int,
    rng: random.Random,
    shows_blink: Callable[[World], bool],
) -> World:
    screen = world.screen
    if (
        screen.mode is not Mode.DASHBOARD
        or screen.alerts
        or partials_left < 2
        or rng.random() >= BLINK_PROBABILITY
        or not shows_blink(world)
    ):
        return world

    room = deadline - now - BLINK_SECONDS - 1.0
    if room <= 0:
        return world

    return replace(world, motion=Motion(BLINK, now + rng.uniform(0, room)))


def on_wake(world: World, now: float) -> World:
    """Show the next frame of the clip and say when to wake for the one
    after; the last step returns to rest."""
    steps = world.motion.steps
    if not steps:
        return replace(world, motion=Motion())

    (frame, hold), rest = steps[0], steps[1:]
    return World(
        screen=world.screen.showing(frame),
        motion=Motion(rest, now + hold if rest else math.inf),
    )
