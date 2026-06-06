import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
LIB_DIR = os.path.join(BASE_DIR, 'lib')

ASSETS_DIR = os.path.join(BASE_DIR, "assets")

FONT_DIR = os.path.join(ASSETS_DIR, "fonts")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

PROMETHEUS_URL = f"https://{os.getenv("PROMETHEUS_SUBDOMAIN", "")}.{os.getenv("PROMETHEUS_DOMAIN", "")}"
PROMETHEUS_API_USERNAME = os.getenv("PROMETHEUS_API_USERNAME", "")
PROMETHEUS_API_PASSWORD = os.getenv("PROMETHEUS_API_PASSWORD", "")

FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", "30"))
FULL_REFRESH_CYCLE = int(os.getenv("FULL_REFRESH_CYCLE", "10"))
HISTORY_LENGTH = int(os.getenv("HISTORY_LENGTH", "40"))

SIMULATE_MODE = os.getenv("SIMULATE", "false").lower() == "true"

QUERIES = {
    "cpu": '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',
    "mem": '100 * (1 - ((node_memory_MemFree_bytes + node_memory_Cached_bytes + node_memory_Buffers_bytes) / node_memory_MemTotal_bytes))',
    "ups_charge": 'ups_battery_charge',
    "uptime": 'time() - node_boot_time_seconds',
}

ALERT_RULES = {
    "cpu": (90.0, ">", "CPU Usage CRITICAL"),
    "mem": (90.0, ">", "RAM Usage CRITICAL"),
    "ups_charge": (95.0, "<", "UPS on Battery Power!"),
}
