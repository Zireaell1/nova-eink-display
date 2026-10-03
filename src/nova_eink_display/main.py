import logging
import random
import signal
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from nova_eink_display.compose import Composer
from nova_eink_display.config import (
    BLINK_PROBABILITY,
    BLINK_SECONDS,
    FETCH_INTERVAL,
    MAX_PARTIAL_REFRESHES,
    METRICS_ADDRESS,
    METRICS_PORT,
    NIGHT_END_HOUR,
    NIGHT_START_HOUR,
    PREVIEW_ADDRESS,
    PREVIEW_PORT,
    PROMETHEUS_API_PASSWORD,
    PROMETHEUS_API_USERNAME,
    PROMETHEUS_CONNECT_TIMEOUT,
    PROMETHEUS_READ_TIMEOUT,
    PROMETHEUS_URL,
    QUERIES,
    SIMULATE_MODE,
    STATE_DIRECTORY,
    TIMEZONE,
)
from nova_eink_display.display import EPDDisplay, SimulatedDisplay
from nova_eink_display.metrics import METRICS, PREVIEW_ROUTES, serve
from nova_eink_display.prometheus import PrometheusClient
from nova_eink_display.state import WearState, state_path
from nova_eink_display.world import Screen, World

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 5


def build_display():
    if SIMULATE_MODE:
        return SimulatedDisplay()

    try:
        return EPDDisplay()
    except Exception:
        logger.exception("Display hardware unavailable, falling back to simulation")
        return SimulatedDisplay()


def is_night(now):
    if NIGHT_START_HOUR == NIGHT_END_HOUR:
        return False

    if NIGHT_START_HOUR < NIGHT_END_HOUR:
        return NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR

    return now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR


class Dashboard:
    def __init__(self, display, compose, client, tz, wear):
        self.display = display
        self.compose = compose
        self.client = client
        self.tz = tz
        self.wear = wear

        self.stopping = threading.Event()
        self.previous_alerts = None
        self.sleeping = False
        self.failures = 0
        self.error_since = None
        self.world = None

    def request_stop(self, signum, frame):
        logger.info("Stop requested, finishing current tick...")
        self.stopping.set()

    def render(self, frame, full_refresh=False):
        before = self.display.partial_count
        self.display.render(frame, full_refresh=full_refresh)

        kind = "partial" if self.display.partial_count > before else "full"
        METRICS.record_refresh(kind, self.display.partial_count)
        METRICS.record_frame(frame)
        self.wear.save(METRICS.snapshot())

    def tick(self, now):
        started = time.monotonic()
        data = self.client.fetch_all()
        METRICS.record_fetch(
            time.monotonic() - started,
            data.get("error"),
            len(data.get("missing", [])),
        )

        error = data.get("error")
        self.error_since = (self.error_since or now) if error else None

        screen = Screen.dashboard(data, now, self.error_since)
        alerts = screen.alerts

        night = not alerts and is_night(now)

        try:
            if night and self.sleeping:
                return None, None

            if night:
                self.world = World(Screen.asleep(now, NIGHT_END_HOUR))
                frame = self.compose(self.world)
                self.render(frame, full_refresh=True)
                self.previous_alerts = alerts

                self.display.sleep()
                self.sleeping = True
                logger.info("Night mode: panel asleep until %02d:00", NIGHT_END_HOUR)
                return frame, None

            self.world = World(screen)
            frame = self.compose(self.world)

            alerts_changed = alerts != self.previous_alerts
            ghosted = self.display.partial_count >= MAX_PARTIAL_REFRESHES

            self.render(frame, full_refresh=alerts_changed or ghosted)
            self.previous_alerts = alerts

            self.sleeping = False

            budget_left = MAX_PARTIAL_REFRESHES - self.display.partial_count
            if alerts or budget_left < 2 or random.random() >= BLINK_PROBABILITY:
                return frame, None

            blink = self.compose(World(screen.showing("blink")))

            if blink.tobytes() == frame.tobytes():
                return frame, None

            return frame, blink
        finally:
            METRICS.record_tick(len(alerts), self.character_mood, self.display.asleep)

    def run(self):
        while not self.stopping.is_set():
            now = datetime.now(self.tz)

            try:
                frame, blink = self.tick(now)
                self.failures = 0
            except Exception:
                self.failures += 1
                METRICS.record_failure()
                logger.exception("Tick failed (%d in a row)", self.failures)
                if self.failures >= MAX_CONSECUTIVE_FAILURES:
                    raise
                frame, blink = None, None

            next_tick = (
                time.monotonic() + FETCH_INTERVAL - (time.time() % FETCH_INTERVAL)
            )

            if blink is not None:
                self.blink(frame, blink, next_tick)

            self.stopping.wait(max(0.0, next_tick - time.monotonic()))

    @property
    def character_mood(self):
        return self.world.screen.pose if self.world else "unknown"

    def shutdown(self):
        self.world = World(Screen.offline(datetime.now(self.tz)))
        frame = self.compose(self.world)
        self.render(frame, full_refresh=True)
        self.display.sleep()

    def blink(self, frame, blink_frame, next_tick):
        budget = next_tick - time.monotonic() - BLINK_SECONDS - 1.0
        if budget <= 0:
            return

        if self.stopping.wait(random.uniform(0, budget)):
            return

        self.render(blink_frame)
        METRICS.record_blink()

        if self.stopping.wait(BLINK_SECONDS):
            return

        self.render(frame)


def main():
    logger.info("Starting dashboard...")

    budget = PROMETHEUS_CONNECT_TIMEOUT + PROMETHEUS_READ_TIMEOUT
    if budget >= FETCH_INTERVAL:
        logger.warning(
            "HTTP timeout budget (%.0fs) >= FETCH_INTERVAL (%ds); ticks will overrun",
            budget,
            FETCH_INTERVAL,
        )

    display = build_display()

    simulated = isinstance(display, SimulatedDisplay)
    METRICS.record_display(
        simulated=simulated,
        fallback=simulated and not SIMULATE_MODE,
        partials_limit=MAX_PARTIAL_REFRESHES,
    )

    wear = WearState(state_path(STATE_DIRECTORY))
    saved = wear.load()
    METRICS.restore(saved.get("refresh_total"), saved.get("starts_total"))
    METRICS.record_start(wear.writable)

    w, h = display.dimensions
    dashboard = Dashboard(
        display,
        Composer(w, h),
        PrometheusClient(
            PROMETHEUS_URL,
            QUERIES,
            PROMETHEUS_API_USERNAME,
            PROMETHEUS_API_PASSWORD,
            timeout=(PROMETHEUS_CONNECT_TIMEOUT, PROMETHEUS_READ_TIMEOUT),
        ),
        ZoneInfo(TIMEZONE),
        wear,
    )

    signal.signal(signal.SIGTERM, dashboard.request_stop)
    signal.signal(signal.SIGINT, dashboard.request_stop)

    serve(METRICS_ADDRESS, METRICS_PORT)
    serve(PREVIEW_ADDRESS, PREVIEW_PORT, PREVIEW_ROUTES)

    display.init()
    wear.save(METRICS.snapshot())

    try:
        dashboard.run()
    finally:
        logger.info("Shutting down...")
        try:
            dashboard.shutdown()
        except Exception:
            logger.exception("Shutdown failed; the panel may still be powered")


if __name__ == "__main__":
    main()
