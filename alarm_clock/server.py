"""HTTP transport for the alarm clock application."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ClockRequestHandler(SimpleHTTPRequestHandler):
    """Serve the UI assets from the application web root."""

    def log_message(self, format: str, *args: object) -> None:
        """Keep the default request logging behavior explicit and replaceable."""
        super().log_message(format, *args)


class ClockServer(ThreadingHTTPServer):
    """HTTP server configured with the clock application's asset directory."""

    def __init__(self, host: str, port: int, web_root: Path) -> None:
        handler = partial(ClockRequestHandler, directory=str(web_root))
        super().__init__((host, port), handler)
