"""Application composition for the alarm clock UI."""

from pathlib import Path
from threading import Thread

from .alarm import AlarmController, FixedAlarmController
from .calendar import CalendarMessageProvider, GoogleCalendar, RefreshingMessageProvider
from .message import Message
from .wakeup import CombinedWakeupAction, PhilipsHueSunrise, PygameAudioAlarm, WakeupService


class ClockApplication:
    """Owns the application configuration and web asset location."""

    def __init__(self, web_root: Path | None = None, message: Message | None = None, message_provider=None) -> None:
        self.web_root = web_root or Path(__file__).parent / "web"
        if message:
            self.message_provider = _FixedMessageProvider(message)
            self.alarm_controller = FixedAlarmController(message)
        elif message_provider:
            self.message_provider = message_provider
            self.alarm_controller = message_provider
        else:
            calendar_provider = CalendarMessageProvider(GoogleCalendar())
            self.alarm_controller = AlarmController(calendar_provider)
            self.message_provider = self.alarm_controller
        wakeup_actions = CombinedWakeupAction([
            PhilipsHueSunrise("Kamer Simon"),
            PygameAudioAlarm(Path(__file__).parent.parent / "alarm.mp3"),
        ])
        self.wakeup_service = WakeupService(
            self.alarm_controller,
            wakeup_actions,
        )
        self._refresh_thread = None
        self._wakeup_thread = None

    def create_server(self, host: str = "127.0.0.1", port: int = 8000):
        """Build the HTTP server without coupling callers to its implementation."""
        from .server import ClockServer

        server = ClockServer(
            host,
            port,
            self.web_root,
            self.message_provider,
            self.alarm_controller,
            self.wakeup_service,
        )
        if isinstance(self.alarm_controller, AlarmController):
            self._refresh_thread = Thread(target=self.alarm_controller.run, daemon=True)
            self._refresh_thread.start()
        self._wakeup_thread = Thread(target=self.wakeup_service.run, daemon=True)
        self._wakeup_thread.start()
        return server


class _FixedMessageProvider:
    def __init__(self, message: Message) -> None:
        self.message = message

    def get_message(self) -> Message:
        return self.message
