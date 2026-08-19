"""Application composition for the alarm clock UI."""

from pathlib import Path


class ClockApplication:
    """Owns the application configuration and web asset location."""

    def __init__(self, web_root: Path | None = None) -> None:
        self.web_root = web_root or Path(__file__).parent / "web"

    def create_server(self, host: str = "127.0.0.1", port: int = 8000):
        """Build the HTTP server without coupling callers to its implementation."""
        from .server import ClockServer

        return ClockServer(host, port, self.web_root)
