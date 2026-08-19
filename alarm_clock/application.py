"""Application composition for the alarm clock UI."""

from pathlib import Path

from .message import Message


class ClockApplication:
    """Owns the application configuration and web asset location."""

    def __init__(self, web_root: Path | None = None, message: Message | None = None) -> None:
        self.web_root = web_root or Path(__file__).parent / "web"
        self.message = message or Message("/icons/night.png", "Time to go to sleep")

    def create_server(self, host: str = "127.0.0.1", port: int = 8000):
        """Build the HTTP server without coupling callers to its implementation."""
        from .server import ClockServer

        return ClockServer(host, port, self.web_root, self.message)
