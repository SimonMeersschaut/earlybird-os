"""Application composition for the alarm clock UI."""

from pathlib import Path
from threading import Thread

from .alarm import AlarmController, FixedAlarmController
from .calendar import CalendarMessageProvider, GoogleCalendar, RefreshingMessageProvider
from .message import Message
from .update import UpdateScheduler
from .alarm import CombinedWakeupAction, PhilipsHueSunrise, PygameAudioAlarm, WakeupService


class ClockApplication:
    """Owns the application configuration and web asset location."""

    def __init__(self, web_root: Path | None = None, message: Message | None = None, message_provider=None) -> None:
        self.web_root = web_root or Path(__file__).parent / "web"
        self.calendar_provider = None
        self.refreshing_calendar_provider = None
        self.updater = None
        if message:
            self.message_provider = _FixedMessageProvider(message)
            self.alarm_controller = FixedAlarmController(message)
        elif message_provider:
            self.message_provider = message_provider
            self.alarm_controller = message_provider
        else:
            self.calendar_provider = CalendarMessageProvider(GoogleCalendar())
            self.refreshing_calendar_provider = RefreshingMessageProvider(self.calendar_provider)
            self.alarm_controller = AlarmController(self.calendar_provider)
            self.message_provider = self.alarm_controller
        if hasattr(self.alarm_controller, "refresh"):
            self.updater = UpdateScheduler(
                alarm_controller=self.alarm_controller,
                calendar_provider=self.refreshing_calendar_provider,
            )
        wakeup_actions = CombinedWakeupAction([
            PhilipsHueSunrise("Kamer Simon"),
            PygameAudioAlarm(Path(__file__).parent.parent / "alarm.mp3"),
        ])
        self.wakeup_service = WakeupService(
            self.alarm_controller,
            wakeup_actions,
        )
        self._update_thread = None
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
            self.updater,
        )
        if self.updater:
            self._update_thread = Thread(target=self.updater.run, daemon=True)
            self._update_thread.start()
        self._wakeup_thread = Thread(target=self.wakeup_service.run, daemon=True)
        self._wakeup_thread.start()
        return server


class _FixedMessageProvider:
    def __init__(self, message: Message) -> None:
        self.message = message

    def get_message(self) -> Message:
        return self.message
