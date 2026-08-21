"""Alarm state and manual override behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Event, Lock
from typing import Callable
from .calendar import AlarmCalculation, AlarmCalculator, CalendarMessageProvider, SLEEP_ICON
from .message import Message


@dataclass(frozen=True)
class AlarmSchedule:
    """The next sleep and wake times shown to the user."""

    sleep_at: datetime
    wake_at: datetime
    source: str
    first_task_at: datetime | None = None

    @property
    def message(self) -> Message:
        return Message(
            SLEEP_ICON,
            f"{self.wake_at.strftime('%H.%M')}",
        )


class AlarmController:
    """Owns the next alarm and one-cycle manual override."""

    def __init__(
        self,
        calendar_provider: CalendarMessageProvider,
        calculator: AlarmCalculator | None = None,
        interval: timedelta = timedelta(minutes=10),
    ) -> None:
        self.calendar_provider = calendar_provider
        self.calculator = calculator or AlarmCalculator()
        self.interval = interval
        self._schedule: AlarmSchedule | None = None
        self._google_schedule: AlarmSchedule | None = None
        self._manual_wake_at: datetime | None = None
        self._lock = Lock()
        self._stop = Event()
        self._changed: list[Callable[[], None]] = []
        try:
            self.refresh()
        except Exception:
            self._schedule = None

    def refresh(self) -> None:
        with self._lock:
            if self._manual_wake_at is not None:
                return
        try:
            calculation_getter = getattr(self.calendar_provider, "get_alarm_calculation", None)
            calculation = calculation_getter() if calculation_getter else None
        except Exception:
            return
        with self._lock:
            if self._manual_wake_at is None:
                if calculation_getter:
                    self._google_schedule = self._schedule_from_calculation(calculation, "google")
                    self._schedule = self._google_schedule
                else:
                    self._google_schedule = self._schedule_from_message(
                        self.calendar_provider.get_message(), "google"
                    )
                    self._schedule = self._google_schedule

    def set_manual_time(self, wake_at: datetime) -> AlarmSchedule:
        sleep_at = wake_at - self.calculator.wake_margin - self.calculator.sleep_duration
        with self._lock:
            self._manual_wake_at = wake_at
            self._schedule = AlarmSchedule(sleep_at, wake_at, "manual")
            self._notify_changed()
            return self._schedule

    def consume(self) -> None:
        with self._lock:
            self._manual_wake_at = None
        self.refresh()
        self._notify_changed()

    def add_change_listener(self, listener: Callable[[], None]) -> None:
        self._changed.append(listener)

    def _notify_changed(self) -> None:
        for listener in tuple(self._changed):
            listener()

    def get_message(self) -> Message:
        with self._lock:
            if self._schedule is None:
                return Message(SLEEP_ICON, "No alarm scheduled")
            return self._schedule.message

    def get_status(self) -> dict[str, str | bool | None]:
        with self._lock:
            schedule = self._schedule
            google_schedule = self._google_schedule
            return {
                "sleep_at": schedule.sleep_at.isoformat() if schedule else None,
                "wake_at": schedule.wake_at.isoformat() if schedule else None,
                "source": schedule.source if schedule else "google",
                "manual_override": self._manual_wake_at is not None,
                "google_sleep_at": google_schedule.sleep_at.isoformat() if google_schedule else None,
                "google_wake_at": google_schedule.wake_at.isoformat() if google_schedule else None,
                "first_task_at": google_schedule.first_task_at.isoformat()
                if google_schedule and google_schedule.first_task_at
                else None,
                "wake_margin_minutes": int(self.calculator.wake_margin.total_seconds() // 60),
            }

    def run(self) -> None:
        while not self._stop.wait(self.interval.total_seconds()):
            try:
                self.refresh()
            except Exception:
                # Keep the last known schedule when Calendar is unavailable.
                pass

    def stop(self) -> None:
        self._stop.set()
        self._notify_changed()

    def _schedule_from_message(self, message: Message, source: str) -> AlarmSchedule | None:
        if message.text == "No alarm scheduled":
            return None
        sleep_text, wake_text = message.text.split(" - ")
        now = datetime.now().astimezone()
        wake_at = now + timedelta(days=1)
        wake_at = wake_at.replace(
            hour=int(wake_text[:2]), minute=int(wake_text[3:]), second=0, microsecond=0
        )
        sleep_at = wake_at - self.calculator.wake_margin - self.calculator.sleep_duration
        return AlarmSchedule(sleep_at, wake_at, source)

    @staticmethod
    def _schedule_from_calculation(
        calculation: AlarmCalculation | None, source: str
    ) -> AlarmSchedule | None:
        if calculation is None:
            return None
        return AlarmSchedule(
            calculation.sleep_at,
            calculation.wake_at,
            source,
            calculation.first_task_at,
        )


class FixedAlarmController:
    """Small adapter used when the application is configured with a fixed message."""

    def __init__(self, message: Message) -> None:
        self.message = message

    def get_message(self) -> Message:
        return self.message

    def get_status(self) -> dict[str, str | bool | None]:
        return {
            "sleep_at": None,
            "wake_at": None,
            "source": "fixed",
            "manual_override": False,
            "google_sleep_at": None,
            "google_wake_at": None,
            "first_task_at": None,
            "wake_margin_minutes": None,
        }
