import logging
import requests
from requests.auth import HTTPBasicAuth

class PrometheusClient:
    def __init__(self, url, queries, username=None, password=None):
        self.url = url.rstrip('/')
        self.queries = queries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "E-Ink-Dashboard/1.0"})
        
        if username and password:
            self.session.auth = HTTPBasicAuth(username, password)
            
        logging.info(f"PrometheusClient initialized for {self.url} (Auth: {'Yes' if self.session.auth else 'No'})")

    def query(self, query_str):
        try:
            resp = self.session.get(
                f"{self.url}/api/v1/query",
                params={"query": query_str},
                timeout=10
            )

            resp.raise_for_status()
            
            data = resp.json()
            result = data.get("data", {}).get("result", [])
            
            if result and len(result) > 0:
                val_str = result[0].get("value", [0, "0"])[1]
                return float(val_str)
            return 0.0
            
        except requests.exceptions.HTTPError as e:
            logging.error(f"Prometheus Auth/HTTP Error: {e}")
            return None
        except Exception as e:
            logging.error(f"Prometheus query failed: {e}")
            return None

    def fetch_all(self):
        results = {}
        error = False
        
        for key, q in self.queries.items():
            val = self.query(q)
            if val is None:
                error = True
            results[key] = val if val is not None else 0.0
            
        return {
            "stats": results, 
            "error": "Prometheus Unreachable" if error else None
        }
