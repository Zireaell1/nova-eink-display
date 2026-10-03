import datetime
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum

from nova_eink_display.alerts import evaluate_alerts
from nova_eink_display.character import choose_pose


class Mode(StrEnum):
    DASHBOARD = "dashboard"
    ASLEEP = "asleep"
    OFFLINE = "offline"


@dataclass(frozen=True)
class Screen:
    """Everything a frame depends on, as plain values. compose() reads only
    this; the same Screen always draws the same pixels."""

    now: datetime.datetime
    stats: Mapping[str, float] = field(default_factory=dict)
    error: str | None = None
    error_since: datetime.datetime | None = None
    alerts: tuple[str, ...] = ()
    pose: str = "happy"
    frame: str = "base"
    mode: Mode = Mode.DASHBOARD
    wake_hour: int | None = None

    @classmethod
    def dashboard(
        cls,
        data: Mapping,
        now: datetime.datetime,
        error_since: datetime.datetime | None = None,
    ) -> Screen:
        stats = data.get("stats", {})
        error = data.get("error")

        alerts = evaluate_alerts(stats)
        if error:
            alerts.insert(0, f"API ERR: {error}")

        return cls(
            now=now,
            stats=stats,
            error=error,
            error_since=error_since,
            alerts=tuple(alerts),
            pose=choose_pose(stats, error, alerts, now),
        )

    @classmethod
    def asleep(cls, now: datetime.datetime, wake_hour: int) -> Screen:
        return cls(
            now=now,
            mode=Mode.ASLEEP,
            wake_hour=wake_hour,
            pose=choose_pose({}, None, [], now),
        )

    @classmethod
    def offline(cls, now: datetime.datetime) -> Screen:
        return cls(
            now=now,
            mode=Mode.OFFLINE,
            pose=choose_pose({}, "OFFLINE", [], now),
        )

    def showing(self, frame: str) -> Screen:
        return replace(self, frame=frame)


@dataclass(frozen=True)
class Motion:
    """The scheduler's state: the frames still to play and when to show the
    next one. `next_wake` is wall-clock seconds; inf means nothing pending."""

    steps: tuple[tuple[str, float], ...] = ()
    next_wake: float = math.inf


@dataclass(frozen=True)
class World:
    """The whole state. Presence and memory join as their phases land."""

    screen: Screen
    motion: Motion = Motion()
