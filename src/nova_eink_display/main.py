import logging
import random
import signal
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from nova_eink_display.alerts import evaluate_alerts
from nova_eink_display.config import (
    BLINK_PROBABILITY,
    BLINK_SECONDS,
    FETCH_INTERVAL,
    MAX_PARTIAL_REFRESHES,
    NIGHT_END_HOUR,
    NIGHT_START_HOUR,
    PROMETHEUS_API_PASSWORD,
    PROMETHEUS_API_USERNAME,
    PROMETHEUS_CONNECT_TIMEOUT,
    PROMETHEUS_READ_TIMEOUT,
    PROMETHEUS_URL,
    QUERIES,
    SIMULATE_MODE,
    TIMEZONE,
)
from nova_eink_display.display import EPDDisplay, SimulatedDisplay
from nova_eink_display.prometheus import PrometheusClient
from nova_eink_display.renderer import UIRenderer

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
    def __init__(self, display, ui, client, tz):
        self.display = display
        self.ui = ui
        self.client = client
        self.tz = tz

        self.stopping = threading.Event()
        self.previous_alerts = None
        self.sleeping = False
        self.failures = 0

    def request_stop(self, signum, frame):
        logger.info("Stop requested, finishing current tick...")
        self.stopping.set()

    def tick(self, now):
        data = self.client.fetch_all()
        alerts = evaluate_alerts(data.get("stats", {}))

        error = data.get("error")
        if error:
            alerts.insert(0, f"API ERR: {error}")

        night = not alerts and is_night(now)

        if night and self.sleeping:
            return None, None

        frame = self.ui.render_frame(data, alerts, now=now)

        alerts_changed = alerts != self.previous_alerts
        ghosted = self.display.partial_count >= MAX_PARTIAL_REFRESHES

        self.display.render(frame, full_refresh=alerts_changed or ghosted)
        self.previous_alerts = alerts

        if night:
            self.display.sleep()
            self.sleeping = True
            logger.info("Night mode: panel asleep until %02d:00", NIGHT_END_HOUR)
            return frame, None

        self.sleeping = False

        if alerts or random.random() >= BLINK_PROBABILITY:
            return frame, None

        blink = self.ui.render_frame(data, alerts, is_blinking=True, now=now)

        if blink.tobytes() == frame.tobytes():
            return frame, None

        return frame, blink

    def run(self):
        next_tick = time.monotonic()

        while not self.stopping.is_set():
            next_tick += FETCH_INTERVAL
            now = datetime.now(self.tz)

            try:
                frame, blink = self.tick(now)
                self.failures = 0
            except Exception:
                self.failures += 1
                logger.exception("Tick failed (%d in a row)", self.failures)
                if self.failures >= MAX_CONSECUTIVE_FAILURES:
                    raise
                frame, blink = None, None

            if blink is not None:
                self.blink(frame, blink, next_tick)

            self.stopping.wait(max(0.0, next_tick - time.monotonic()))

    def blink(self, frame, blink_frame, next_tick):
        budget = next_tick - time.monotonic() - BLINK_SECONDS - 1.0
        if budget <= 0:
            return

        if self.stopping.wait(random.uniform(0, budget)):
            return

        self.display.render(blink_frame, full_refresh=False)

        if self.stopping.wait(BLINK_SECONDS):
            return

        self.display.render(frame, full_refresh=False)


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
    display.init()

    w, h = display.dimensions
    dashboard = Dashboard(
        display,
        UIRenderer(w, h),
        PrometheusClient(
            PROMETHEUS_URL,
            QUERIES,
            PROMETHEUS_API_USERNAME,
            PROMETHEUS_API_PASSWORD,
            timeout=(PROMETHEUS_CONNECT_TIMEOUT, PROMETHEUS_READ_TIMEOUT),
        ),
        ZoneInfo(TIMEZONE),
    )

    signal.signal(signal.SIGTERM, dashboard.request_stop)
    signal.signal(signal.SIGINT, dashboard.request_stop)

    try:
        dashboard.run()
    finally:
        logger.info("Shutting down...")
        display.cleanup()


if __name__ == "__main__":
    main()
