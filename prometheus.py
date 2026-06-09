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
            
            if not result:
                return None, "No data"
            
            val_str = result[0].get("value", [0, "0"])[1]
            return float(val_str), None
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Prometheus HTTP/Network Error: {e}")
            return None, "Unreachable"
        except Exception as e:
            logging.error(f"Prometheus query failed: {e}")
            return None, "Parse Error"

    def fetch_all(self):
        results = {}
        missing_metrics = []
        server_down = False
        
        for key, q in self.queries.items():
            val, err = self.query(q)
            
            if err == "Unreachable":
                server_down = True
                break
            elif err:
                missing_metrics.append(key)
            else:
                results[key] = val
                
        error_msg = None
        if server_down:
            error_msg = "Prometheus Unreachable"
        elif missing_metrics:
            error_msg = f"Missing: {', '.join(missing_metrics)}"
            
        return {
            "stats": results, 
            "error": error_msg
        }