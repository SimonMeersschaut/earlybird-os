"""Google Calendar access and alarm calculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from threading import Event
from typing import Any, Callable, Protocol

from .message import Message


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
SLEEP_ICON = "/icons/night.png"


@dataclass(frozen=True)
class CalendarEvent:
    """The part of a calendar event needed by the alarm clock."""

    starts_at: datetime
    all_day: bool = False


@dataclass(frozen=True)
class AlarmCalculation:
    """The alarm times calculated from the first timed calendar event."""

    sleep_at: datetime
    wake_at: datetime
    first_task_at: datetime


class Calendar(Protocol):
    def events_for(self, day: date) -> list[CalendarEvent]: ...


class GoogleCalendar:
    """Adapter around the Google Calendar API."""

    def __init__(
        self,
        credentials_file: Path = Path("credentials.json"),
        token_file: Path = Path("token.json"),
        service_factory: Callable[[Any], Any] | None = None,
    ) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service_factory = service_factory

    def _service(self) -> Any:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        credentials = None
        if self.token_file.exists():
            credentials = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
                credentials = flow.run_local_server(port=0)
            self.token_file.write_text(credentials.to_json(), encoding="utf-8")

        if self.service_factory:
            return self.service_factory(credentials)

        from googleapiclient.discovery import build

        return build("calendar", "v3", credentials=credentials)

    def events_for(self, day: date) -> list[CalendarEvent]:
        local_zone = datetime.now().astimezone().tzinfo
        start = datetime.combine(day, time.min, local_zone)
        end = start + timedelta(days=1)
        response = self._service().events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in response.get("items", []):
            value = item.get("start", {}).get("dateTime")
            if value:
                events.append(CalendarEvent(datetime.fromisoformat(value.replace("Z", "+00:00"))))
        return events


class AlarmCalculator:
    """Converts the first timed event on a day into a sleep/wake message."""

    def __init__(self, sleep_duration: timedelta = timedelta(hours=9), wake_margin: timedelta = timedelta(minutes=90)) -> None:
        self.sleep_duration = sleep_duration
        self.wake_margin = wake_margin

    def message_for(self, events: list[CalendarEvent], now: datetime) -> Message:
        calculation = self.calculate(events, now)
        if calculation is None:
            return Message(SLEEP_ICON, "No alarm scheduled")
        return Message(SLEEP_ICON, f"{self._format(calculation.sleep_at)} - {self._format(calculation.wake_at)}")

    def calculate(self, events: list[CalendarEvent], now: datetime) -> AlarmCalculation | None:
        timed_events = [
            event for event in events
            if not event.all_day and event.starts_at.date() == (now.date() + timedelta(days=1))
        ]
        if not timed_events:
            return None

        first_task_at = min(event.starts_at for event in timed_events)
        wake_at = first_task_at - self.wake_margin
        sleep_at = wake_at - self.sleep_duration
        return AlarmCalculation(sleep_at, wake_at, first_task_at)

    @staticmethod
    def _format(value: datetime) -> str:
        return value.strftime("%H.%M")


class CalendarMessageProvider:
    """Builds the current alarm message from a calendar and a clock."""

    def __init__(
        self,
        calendar: Calendar,
        calculator: AlarmCalculator | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.calendar = calendar
        self.calculator = calculator or AlarmCalculator()
        self.clock = clock or (lambda: datetime.now().astimezone())

    def get_message(self) -> Message:
        now = self.clock()
        return self.calculator.message_for(self.calendar.events_for(now.date() + timedelta(days=1)), now)

    def get_alarm_calculation(self) -> AlarmCalculation | None:
        now = self.clock()
        return self.calculator.calculate(self.calendar.events_for(now.date() + timedelta(days=1)), now)


class RefreshingMessageProvider:
    """Refreshes a message in the background while serving the last known value."""

    def __init__(self, provider: CalendarMessageProvider, interval: timedelta = timedelta(minutes=10)) -> None:
        self.provider = provider
        self.interval = interval
        self.message = Message(SLEEP_ICON, "Checking calendar")
        self._stop = Event()

    def refresh(self) -> None:
        try:
            self.message = self.provider.get_message()
        except Exception:
            self.message = Message(SLEEP_ICON, "Calendar unavailable")

    def get_message(self) -> Message:
        return self.message

    def run(self) -> None:
        self.refresh()
        while not self._stop.wait(self.interval.total_seconds()):
            self.refresh()

    def stop(self) -> None:
        self._stop.set()