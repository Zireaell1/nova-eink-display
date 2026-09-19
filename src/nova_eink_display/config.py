import os

MAIN_DIR = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(MAIN_DIR))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONT_DIR = os.path.join(ASSETS_DIR, "fonts")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "")
PROMETHEUS_API_USERNAME = os.getenv("PROMETHEUS_API_USERNAME", "")
PROMETHEUS_API_PASSWORD = os.getenv("PROMETHEUS_API_PASSWORD", "")

PROMETHEUS_CONNECT_TIMEOUT = float(os.getenv("PROMETHEUS_CONNECT_TIMEOUT", "3"))
PROMETHEUS_READ_TIMEOUT = float(os.getenv("PROMETHEUS_READ_TIMEOUT", "7"))

FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", "120"))

MAX_PARTIAL_REFRESHES = int(os.getenv("MAX_PARTIAL_REFRESHES", "8"))

BLINK_PROBABILITY = float(os.getenv("BLINK_PROBABILITY", "0.4"))
BLINK_SECONDS = float(os.getenv("BLINK_SECONDS", "1"))

NIGHT_START_HOUR = int(os.getenv("NIGHT_START_HOUR", "23"))
NIGHT_END_HOUR = int(os.getenv("NIGHT_END_HOUR", "6"))

STATE_DIRECTORY = os.getenv("STATE_DIRECTORY", "")

METRICS_ADDRESS = os.getenv("METRICS_ADDRESS", "127.0.0.1")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9110"))

PREVIEW_ADDRESS = os.getenv("PREVIEW_ADDRESS", "")
PREVIEW_PORT = int(os.getenv("PREVIEW_PORT", "0"))

SIMULATE_MODE = os.getenv("SIMULATE", "false").lower() == "true"
INSTANCE = os.getenv("INSTANCE", "")

INVERT_COLORS = os.getenv("INVERT_COLORS", "false").lower() == "true"
TIMEZONE = os.getenv("TIMEZONE", "Europe/Warsaw")

QUERIES = {
    "cpu": f'avg(100 - (avg(rate(node_cpu_seconds_total{{mode="idle", instance="{INSTANCE}"}}[5m])) * 100))',
    "mem": f'avg((1 - (node_memory_MemAvailable_bytes{{instance="{INSTANCE}"}} / node_memory_MemTotal_bytes{{instance="{INSTANCE}"}})) * 100)',
    "ups_charge": "min(ups_battery_charge)",
    "uptime": f'max(time() - node_boot_time_seconds{{instance="{INSTANCE}"}})',
    "backup_status": "min(homelab_backup_success)",
}
