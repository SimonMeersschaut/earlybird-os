"""Application composition for the alarm clock UI."""

from pathlib import Path
from threading import Thread

from .calendar import CalendarMessageProvider, GoogleCalendar, RefreshingMessageProvider
from .message import Message


class ClockApplication:
    """Owns the application configuration and web asset location."""

    def __init__(self, web_root: Path | None = None, message: Message | None = None, message_provider=None) -> None:
        self.web_root = web_root or Path(__file__).parent / "web"
        self.message_provider = message_provider or RefreshingMessageProvider(
            CalendarMessageProvider(GoogleCalendar())
        )
        if message:
            self.message_provider = _FixedMessageProvider(message)
        self._refresh_thread = None

    def create_server(self, host: str = "127.0.0.1", port: int = 8000):
        """Build the HTTP server without coupling callers to its implementation."""
        from .server import ClockServer

        if isinstance(self.message_provider, RefreshingMessageProvider):
            self._refresh_thread = Thread(target=self.message_provider.run, daemon=True)
            self._refresh_thread.start()
        return ClockServer(host, port, self.web_root, self.message_provider)


class _FixedMessageProvider:
    def __init__(self, message: Message) -> None:
        self.message = message

    def get_message(self) -> Message:
        return self.message
