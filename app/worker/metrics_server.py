"""
Metrics HTTP Server for Worker

Provides a simple HTTP endpoint for Prometheus to scrape worker metrics.
Runs in a separate thread alongside the main worker loop.

SPRINT 1 DAY 4: Solves multi-process metrics visibility issue.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from threading import Thread
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for /metrics endpoint"""

    def do_GET(self):
        if self.path == '/metrics':
            try:
                metrics_data = generate_latest()
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                self.end_headers()
                self.wfile.write(metrics_data)
            except Exception as e:
                logger.error(f"Error generating metrics: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        logger.debug(f"Metrics request: {format % args}")


class MetricsServer:
    """
    Lightweight HTTP server for exposing worker metrics.

    Runs in a background thread and serves Prometheus metrics
    on a dedicated port separate from the main API server.
    """

    def __init__(self, port: int = 9090):
        """
        Initialize metrics server.

        Args:
            port: Port to listen on (default: 9090)
        """
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the metrics server in a background thread"""
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), MetricsHandler)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"Worker metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    def stop(self):
        """Stop the metrics server"""
        if self.server:
            self.server.shutdown()
            logger.info("Worker metrics server stopped")
