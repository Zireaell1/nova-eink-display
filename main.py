#!/usr/bin/python3

import logging
import time
import sys
import signal
from PIL import Image, ImageDraw
from typing import Optional

from config import (
    FETCH_INTERVAL, FULL_REFRESH_CYCLE, QUERIES, ALERT_RULES,
    PROMETHEUS_URL, PROMETHEUS_API_USERNAME, PROMETHEUS_API_PASSWORD, SIMULATE_MODE
)

from prometheus import PrometheusClient
from screens import MainScreen, AlertScreen

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

if not SIMULATE_MODE:
    try:
        from lib import epd2in9_V2
    except ImportError as e:
        logging.critical(f"Waveshare library not found in 'lib/': {e}")
        sys.exit(1)

epd: Optional['epd2in9_V2.EPD'] = None

def handle_exit(signum, frame):
    logging.info("Shutting down and cleaning up display...")
    if not SIMULATE_MODE and epd:
        epd.init()
        epd.Clear(0xFF)
        epd.sleep()
    sys.exit(0)

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
    global epd
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    logging.info("Starting dashboard...")

    # Hardware / Simulation Setup
    if SIMULATE_MODE:
        logging.info("Starting in SIMULATION MODE. Saving UI to 'preview.png'")
        w, h = 296, 128
    else:
        try:
            epd = epd2in9_V2.EPD()
            epd.init()
            epd.Clear(0xFF)
            w, h = epd.height, epd.width
        except Exception as e:
            logging.critical(f"Display init failed: {e}")
            sys.exit(1)

    # Init Components
    screen_main = MainScreen(w, h)
    screen_alert = AlertScreen(w, h)
    prom_client = PrometheusClient(
        PROMETHEUS_URL, QUERIES, PROMETHEUS_API_USERNAME, PROMETHEUS_API_PASSWORD
    )

    refresh_counter = 0

    # Main Loop
    while True:
        try:
            # 1. Fetch Data
            data = prom_client.fetch_all()
            stats = data.get('stats', {})
            error = data.get('error')

            # 2. Check for emergencies / API errors
            active_alerts = evaluate_alerts(stats)
            if error:
                active_alerts.insert(0, f"API ERR: {error}")

            # 3. Setup Image Buffer
            image = Image.new('1', (w, h), 255)
            draw = ImageDraw.Draw(image)

            # 4. Draw Screen
            if active_alerts:
                logging.warning(f"Active alerts: {active_alerts}")
                screen_alert.draw(image, draw, active_alerts)
                force_full_refresh = True 
            else:
                screen_main.draw(image, draw, data)
                force_full_refresh = False

            # 5. Output Frame (Simulation / Hardware)
            if SIMULATE_MODE:
                image.save("preview.png")
                logging.info("Preview updated -> preview.png")
            else:
                assert epd is not None 
                
                if force_full_refresh or refresh_counter % FULL_REFRESH_CYCLE == 0:
                    logging.info("Performing Full Screen Refresh")
                    epd.init() 
                    epd.display_Base(epd.getbuffer(image))
                else:
                    logging.info("Performing Fast Partial Refresh")
                    epd.display_Partial(epd.getbuffer(image))

            refresh_counter += 1
            time.sleep(FETCH_INTERVAL)

        except Exception as e:
            logging.error(f"Main loop exception: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
