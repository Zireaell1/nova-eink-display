#!/usr/bin/python3
import logging
import time
import sys
import signal
import random
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.dashboard.config import (
    FETCH_INTERVAL, FULL_REFRESH_CYCLE, QUERIES, ALERT_RULES,
    PROMETHEUS_URL, PROMETHEUS_API_USERNAME, PROMETHEUS_API_PASSWORD, SIMULATE_MODE
)
from src.dashboard.prometheus import PrometheusClient
from src.dashboard.display import EPDDisplay, SimulatedDisplay
from src.dashboard.renderer import UIRenderer

def evaluate_alerts(stats):
    active_alerts = []

    for key, (threshold, operator, message) in ALERT_RULES.items():
        if key not in stats: 
            continue

        val = stats[key]
        if (operator == ">" and val > threshold) or (operator == "<" and val < threshold):
            active_alerts.append(f"{message} ({int(val)})")

    return active_alerts

def main():
    logger.info("Starting dashboard...")

    if SIMULATE_MODE:
        display = SimulatedDisplay()
    else:
        try:
            display = EPDDisplay()
        except ImportError as e:
            logger.critical(f"Waveshare library not found: {e}")
            sys.exit(1)

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
        PROMETHEUS_URL, QUERIES, PROMETHEUS_API_USERNAME, PROMETHEUS_API_PASSWORD
    )

    refresh_counter = 0

    while True:
        try:
            data = prom_client.fetch_all()
            stats = data.get('stats', {})
            error = data.get('error')

            active_alerts = evaluate_alerts(stats)
            if error:
                active_alerts.insert(0, f"API ERR: {error}")

            image_buffer = ui.render_frame(data, active_alerts, is_blinking=False)
            blink_buffer = ui.render_frame(data, active_alerts, is_blinking=True)
            
            force_full = bool(active_alerts) or (refresh_counter % FULL_REFRESH_CYCLE == 0)
            display.render(image_buffer, full_refresh=force_full)

            refresh_counter = (refresh_counter + 1) % FULL_REFRESH_CYCLE

            for _ in range(FETCH_INTERVAL):
                if not active_alerts:
                    if random.random() < 0.12:
                        display.render(blink_buffer, full_refresh=False) 
                        time.sleep(1)
                        display.render(image_buffer, full_refresh=False) 

                time.sleep(1)

        except Exception as e:
            logger.error(f"Main loop exception: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
