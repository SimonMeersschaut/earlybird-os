"""Google Calendar access and alarm calculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from threading import Event
from typing import Any, Callable

from .message import Message


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
SLEEP_ICON = "/icons/night.png"
WAKE_MARGIN = timedelta(minutes=90)
SLEEP_DURATION = timedelta(hours=9)


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


def _build_google_service(
    credentials_file: Path,
    token_file: Path,
    service_factory: Callable[[Any], Any] | None,
) -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            credentials = flow.run_local_server(port=0)
        token_file.write_text(credentials.to_json(), encoding="utf-8")

    if service_factory:
        return service_factory(credentials)

    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=credentials)


def _fetch_events_for_day(service: Any, day: date) -> list[CalendarEvent]:
    local_zone = datetime.now().astimezone().tzinfo
    start = datetime.combine(day, time.min, local_zone)
    end = start + timedelta(days=1)
    response = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events: list[CalendarEvent] = []
    for item in response.get("items", []):
        value = item.get("start", {}).get("dateTime")
        if value:
            events.append(CalendarEvent(datetime.fromisoformat(value.replace("Z", "+00:00"))))
    return events


def calculate_alarm(
    events: list[CalendarEvent],
    sleep_duration: timedelta = SLEEP_DURATION,
    wake_margin: timedelta = WAKE_MARGIN,
) -> AlarmCalculation | None:
    timed_events = [event for event in events if not event.all_day]
    if not timed_events:
        return None

    first_task_at = min(event.starts_at for event in timed_events)
    wake_at = first_task_at - wake_margin
    sleep_at = wake_at - sleep_duration
    return AlarmCalculation(sleep_at, wake_at, first_task_at)


def alarm_message_for(events: list[CalendarEvent]) -> Message:
    calculation = calculate_alarm(events)
    if calculation is None:
        return Message(SLEEP_ICON, "No alarm scheduled")
    return Message(SLEEP_ICON, calculation.wake_at.strftime("%H.%M"))


class GoogleCalendar:
    """Small adapter that returns timed events for a given day."""

    def __init__(
        self,
        credentials_file: Path = Path("credentials.json"),
        token_file: Path = Path("token.json"),
        service_factory: Callable[[Any], Any] | None = None,
    ) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service_factory = service_factory

    def events_for(self, day: date) -> list[CalendarEvent]:
        service = _build_google_service(self.credentials_file, self.token_file, self.service_factory)
        return _fetch_events_for_day(service, day)


class AlarmCalculator:
    """Compatibility wrapper over the simple alarm calculation functions."""

    def __init__(self, sleep_duration: timedelta = SLEEP_DURATION, wake_margin: timedelta = WAKE_MARGIN) -> None:
        self.sleep_duration = sleep_duration
        self.wake_margin = wake_margin

    def message_for(self, events: list[CalendarEvent], now: datetime) -> Message:
        _ = now
        calculation = self.calculate(events, now)
        if calculation is None:
            return Message(SLEEP_ICON, "No alarm scheduled")
        return Message(SLEEP_ICON, calculation.wake_at.strftime("%H.%M"))

    def calculate(self, events: list[CalendarEvent], now: datetime) -> AlarmCalculation | None:
        _ = now
        return calculate_alarm(events, self.sleep_duration, self.wake_margin)


class CalendarMessageProvider:
    """Gets tomorrow's events and returns the alarm message."""

    def __init__(
        self,
        calendar: Any,
        calculator: AlarmCalculator | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.calendar = calendar
        self.calculator = calculator or AlarmCalculator()
        self.clock = clock or (lambda: datetime.now().astimezone())

    def get_message(self) -> Message:
        now = self.clock()
        tomorrow = now.date() + timedelta(days=1)
        events = self.calendar.events_for(tomorrow)
        return self.calculator.message_for(events, now)

    def get_alarm_calculation(self) -> AlarmCalculation | None:
        now = self.clock()
        tomorrow = now.date() + timedelta(days=1)
        events = self.calendar.events_for(tomorrow)
        return self.calculator.calculate(events, now)


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