import logging
import random
import signal
import sys
import time

from nova_eink_display.alerts import evaluate_alerts
from nova_eink_display.config import (
    FETCH_INTERVAL,
    FULL_REFRESH_CYCLE,
    PROMETHEUS_API_PASSWORD,
    PROMETHEUS_API_USERNAME,
    PROMETHEUS_CONNECT_TIMEOUT,
    PROMETHEUS_READ_TIMEOUT,
    PROMETHEUS_URL,
    QUERIES,
    SIMULATE_MODE,
)
from nova_eink_display.display import EPDDisplay, SimulatedDisplay
from nova_eink_display.prometheus import PrometheusClient
from nova_eink_display.renderer import UIRenderer

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

    def handle_exit(signum, frame):
        logger.info("Shutting down...")
        display.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    display.init()
    w, h = display.dimensions
    ui = UIRenderer(w, h)
    prom_client = PrometheusClient(
        PROMETHEUS_URL,
        QUERIES,
        PROMETHEUS_API_USERNAME,
        PROMETHEUS_API_PASSWORD,
        timeout=(PROMETHEUS_CONNECT_TIMEOUT, PROMETHEUS_READ_TIMEOUT),
    )

    refresh_counter = 0

    while True:
        try:
            data = prom_client.fetch_all()
            stats = data.get("stats", {})
            error = data.get("error")

            active_alerts = evaluate_alerts(stats)
            if error:
                active_alerts.insert(0, f"API ERR: {error}")

            image_buffer = ui.render_frame(data, active_alerts, is_blinking=False)
            blink_buffer = ui.render_frame(data, active_alerts, is_blinking=True)

            force_full = bool(active_alerts) or (
                refresh_counter % FULL_REFRESH_CYCLE == 0
            )
            display.render(image_buffer, full_refresh=force_full)

            refresh_counter = (refresh_counter + 1) % FULL_REFRESH_CYCLE

            for _ in range(FETCH_INTERVAL):
                if not active_alerts and random.random() < 0.12:
                    display.render(blink_buffer, full_refresh=False)
                    time.sleep(1)
                    display.render(image_buffer, full_refresh=False)

                time.sleep(1)

        except Exception:
            logger.exception("Main loop exception")
            time.sleep(10)


if __name__ == "__main__":
    main()
