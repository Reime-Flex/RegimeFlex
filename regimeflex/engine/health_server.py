from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from .health import run_health

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health" or self.path == "/healthz":
            report = run_health()
            status = 200 if report.status != "FAIL" else 503
            
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "status": report.status,
                "timestamp": report.timestamp,
                "checks": [{"name": c.name, "status": c.status, "detail": c.detail} 
                          for c in report.checks]
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/ready":
            # Readiness check - lighter than full health
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress access logs


def start_health_server(port: int = 8080) -> threading.Thread:
    """Start health check server in background thread."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
