import logging
import math

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(self, url, queries, username=None, password=None, timeout=(3.0, 7.0)):
        self.url = url.rstrip("/")
        self.queries = queries
        self.timeout = timeout

        self.combined_query = " or ".join(
            f'label_replace({expr}, "key", "{name}", "", "")'
            for name, expr in queries.items()
        )

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "E-Ink-Dashboard/1.0"})
        if username and password:
            self.session.auth = HTTPBasicAuth(username, password)

        logger.info(
            "PrometheusClient initialized for %s (auth: %s, %d metrics in 1 request)",
            self.url,
            "yes" if self.session.auth else "no",
            len(queries),
        )
        logger.debug("Combined query:\n%s", self.combined_query)

    def _empty(self, error):
        return {"stats": {}, "error": error, "missing": sorted(self.queries)}

    def _log_result(self, result, stats, missing, elapsed):
        if not logger.isEnabledFor(logging.DEBUG):
            return

        rows = []
        for series in result:
            labels = dict(series.get("metric", {}))
            key = labels.pop("key", "<no key>")
            value = series.get("value")
            raw = str(value[1]) if isinstance(value, list) and len(value) > 1 else "?"
            stray = f"   stray labels: {labels}" if labels else ""
            rows.append(f"  {key:<14}{raw:>24}{stray}")

        logger.debug(
            "Prometheus returned %d series in %.0f ms:\n%s",
            len(result),
            elapsed * 1000,
            "\n".join(rows) or "  (empty)",
        )
        logger.debug(
            "Parsed %d/%d metrics:\n%s%s",
            len(stats),
            len(self.queries),
            "\n".join(f"  {k:<14}{v:>24.4f}" for k, v in sorted(stats.items()))
            or "  (none)",
            f"\n  missing: {', '.join(missing)}" if missing else "",
        )

    def fetch_all(self):
        try:
            resp = self.session.get(
                f"{self.url}/api/v1/query",
                params={"query": self.combined_query},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("Prometheus unreachable: %s", e)
            return self._empty("Prometheus Unreachable")
        except ValueError as e:
            logger.error("Prometheus returned invalid JSON: %s", e)
            return self._empty("Parse Error")

        if payload.get("status") != "success":
            logger.error("Prometheus rejected the query: %s", payload.get("error"))
            return self._empty("Query Error")

        result = payload.get("data", {}).get("result", [])

        stats = {}
        for series in result:
            labels = series.get("metric", {})
            name = labels.get("key")
            if name not in self.queries:
                continue
            try:
                value = float(series["value"][1])
            except KeyError, IndexError, TypeError, ValueError:
                logger.warning(
                    "Unparseable value for %s: %r", name, series.get("value")
                )
                continue
            if math.isnan(value):
                logger.debug("Dropping NaN value for %s", name)
                continue
            stats[name] = value

        missing = sorted(set(self.queries) - set(stats))
        self._log_result(result, stats, missing, resp.elapsed.total_seconds())

        return {"stats": stats, "error": None, "missing": missing}
