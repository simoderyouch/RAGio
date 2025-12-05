"""
HTTP server to expose Prometheus metrics from Celery workers.
This runs in a background thread alongside the Celery worker.
"""

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint."""
    
    def do_GET(self):
        """Handle GET requests to /metrics endpoint."""
        if self.path == '/metrics':
            try:
                output = generate_latest()
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                self.end_headers()
                self.wfile.write(output)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error generating metrics: {str(e)}".encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass


def start_metrics_server(port: int = 8081):
    """
    Start a simple HTTP server to expose Prometheus metrics.
    Runs in a background daemon thread.
    
    Args:
        port: Port to listen on (default: 8081)
    """
    def run_server():
        try:
            server = HTTPServer(('0.0.0.0', port), MetricsHandler)
            print(f"✓ Prometheus metrics server started on port {port}")
            server.serve_forever()
        except Exception as e:
            print(f"✗ Failed to start metrics server: {e}")
    
    # Start server in daemon thread so it doesn't block Celery worker shutdown
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    # Allow port to be configured via environment variable
    port = int(os.getenv("CELERY_METRICS_PORT", "8081"))
    start_metrics_server(port)
    # Keep main thread alive
    import time
    while True:
        time.sleep(1)

