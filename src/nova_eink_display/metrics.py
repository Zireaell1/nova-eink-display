import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()

        self.refresh_total: dict[str, int] = {"full": 0, "partial": 0}
        self.fetch_errors_total: dict[str, int] = {}
        self.tick_failures_total = 0

        self.partials_since_full = 0
        self.panel_asleep = 0
        self.alerts_active = 0
        self.metrics_missing = 0
        self.fetch_duration_seconds = 0.0
        self.last_render_timestamp = 0.0
        self.mood = "unknown"

    def record_refresh(self, kind: str, partials_since_full: int) -> None:
        with self._lock:
            self.refresh_total[kind] = self.refresh_total.get(kind, 0) + 1
            self.partials_since_full = partials_since_full
            self.last_render_timestamp = time.time()

    def record_fetch(self, duration: float, error: str | None, missing: int) -> None:
        with self._lock:
            self.fetch_duration_seconds = duration
            self.metrics_missing = missing
            if error:
                self.fetch_errors_total[error] = (
                    self.fetch_errors_total.get(error, 0) + 1
                )

    def record_tick(self, alerts: int, mood: str, asleep: bool) -> None:
        with self._lock:
            self.alerts_active = alerts
            self.mood = mood
            self.panel_asleep = int(asleep)

    def record_failure(self) -> None:
        with self._lock:
            self.tick_failures_total += 1

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP eink_refresh_total Panel refreshes issued, by kind.",
                "# TYPE eink_refresh_total counter",
            ]
            for kind, count in sorted(self.refresh_total.items()):
                lines.append(f'eink_refresh_total{{kind="{kind}"}} {count}')

            lines += [
                "# HELP eink_partials_since_full Partial refreshes since the last full one.",
                "# TYPE eink_partials_since_full gauge",
                f"eink_partials_since_full {self.partials_since_full}",
                "# HELP eink_panel_asleep 1 while the panel is in deep sleep.",
                "# TYPE eink_panel_asleep gauge",
                f"eink_panel_asleep {self.panel_asleep}",
                "# HELP eink_alerts_active Alerts currently on screen.",
                "# TYPE eink_alerts_active gauge",
                f"eink_alerts_active {self.alerts_active}",
                "# HELP eink_metrics_missing Queries that returned no data.",
                "# TYPE eink_metrics_missing gauge",
                f"eink_metrics_missing {self.metrics_missing}",
                "# HELP eink_fetch_duration_seconds Duration of the last Prometheus query.",
                "# TYPE eink_fetch_duration_seconds gauge",
                f"eink_fetch_duration_seconds {self.fetch_duration_seconds:.6f}",
                "# HELP eink_last_render_timestamp_seconds When the panel was last written.",
                "# TYPE eink_last_render_timestamp_seconds gauge",
                f"eink_last_render_timestamp_seconds {self.last_render_timestamp:.3f}",
                "# HELP eink_tick_failures_total Ticks that raised.",
                "# TYPE eink_tick_failures_total counter",
                f"eink_tick_failures_total {self.tick_failures_total}",
                "# HELP eink_character_mood The reaction currently displayed.",
                "# TYPE eink_character_mood gauge",
                f'eink_character_mood{{mood="{self.mood}"}} 1',
            ]

            if self.fetch_errors_total:
                lines += [
                    "# HELP eink_fetch_errors_total Failed fetches, by reason.",
                    "# TYPE eink_fetch_errors_total counter",
                ]
                for reason, count in sorted(self.fetch_errors_total.items()):
                    label = reason.replace("\\", "\\\\").replace('"', '\\"')
                    lines.append(f'eink_fetch_errors_total{{reason="{label}"}} {count}')

            return "\n".join(lines) + "\n"


METRICS = Metrics()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.split("?")[0] != "/metrics":
            self.send_error(404)
            return

        body = METRICS.render().encode()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        logger.debug("metrics: " + format, *args)


def serve(address: str, port: int) -> ThreadingHTTPServer | None:
    if not port:
        logger.info("Metrics endpoint disabled")
        return None

    try:
        server = ThreadingHTTPServer((address, port), _Handler)
    except OSError:
        logger.exception("Could not bind metrics endpoint on %s:%d", address, port)
        return None

    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Metrics endpoint on http://%s:%d/metrics", address, port)
    return server
