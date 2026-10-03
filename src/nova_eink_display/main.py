import logging
import random
import signal
from zoneinfo import ZoneInfo

from nova_eink_display.clock import Clock
from nova_eink_display.compose import Composer
from nova_eink_display.config import (
    FETCH_INTERVAL,
    MAX_PARTIAL_REFRESHES,
    METRICS_ADDRESS,
    METRICS_PORT,
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
from nova_eink_display.loop import Inbox, Loop, Stop
from nova_eink_display.metrics import METRICS, PREVIEW_ROUTES, serve
from nova_eink_display.panel import Panel
from nova_eink_display.prometheus import PrometheusClient
from nova_eink_display.state import WearState, state_path

logger = logging.getLogger(__name__)


def build_display():
    if SIMULATE_MODE:
        return SimulatedDisplay()

    try:
        return EPDDisplay()
    except Exception:
        logger.exception("Display hardware unavailable, falling back to simulation")
        return SimulatedDisplay()


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

    panel = Panel(display, wear, MAX_PARTIAL_REFRESHES)
    clock = Clock(ZoneInfo(TIMEZONE))
    inbox = Inbox(clock)

    w, h = display.dimensions
    loop = Loop(
        panel,
        Composer(w, h),
        PrometheusClient(
            PROMETHEUS_URL,
            QUERIES,
            PROMETHEUS_API_USERNAME,
            PROMETHEUS_API_PASSWORD,
            timeout=(PROMETHEUS_CONNECT_TIMEOUT, PROMETHEUS_READ_TIMEOUT),
        ),
        clock,
        inbox,
        rng=random.Random(),
    )

    def request_stop(signum, frame):
        inbox.put(Stop())

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    serve(METRICS_ADDRESS, METRICS_PORT)
    serve(PREVIEW_ADDRESS, PREVIEW_PORT, PREVIEW_ROUTES)

    panel.start()
    wear.save(METRICS.snapshot())

    try:
        loop.run()
    finally:
        logger.info("Shutting down...")
        try:
            loop.shutdown()
        except Exception:
            logger.exception("Shutdown failed; the panel may still be powered")


if __name__ == "__main__":
    main()
