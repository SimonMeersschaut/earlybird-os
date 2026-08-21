"""Alarm scheduling, wakeup monitoring, and composed wakeup actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Condition, Event, Lock
from typing import Callable, Protocol

from ..calendar import AlarmCalculation, AlarmCalculator, CalendarMessageProvider, SLEEP_ICON
from ..message import Message
from .philips_hue import BRIDGE_IP, PhilipsHueSunrise
from .sound import PygameAudioAlarm


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
		changed = False
		with self._lock:
			if self._manual_wake_at is None:
				previous_schedule = self._schedule
				if calculation_getter:
					self._google_schedule = self._schedule_from_calculation(calculation, "google")
					self._schedule = self._google_schedule
				else:
					self._google_schedule = self._schedule_from_message(
						self.calendar_provider.get_message(), "google"
					)
					self._schedule = self._google_schedule
				changed = self._schedule != previous_schedule
		if changed:
			self._notify_changed()

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
		_ = sleep_text
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


class WakeupAction(Protocol):
	def wake(self) -> None:
		"""Start the configured wakeup behavior."""


class CombinedWakeupAction:
	"""Run all wakeup actions, allowing one hardware failure to be isolated."""

	def __init__(self, actions: list[WakeupAction]) -> None:
		self.actions = actions

	def wake(self) -> None:
		failures: list[Exception] = []
		for action in self.actions:
			try:
				action.wake()
			except Exception as error:
				failures.append(error)
		if failures and len(failures) == len(self.actions):
			raise failures[0]

	def stop_alarm(self) -> None:
		for action in self.actions:
			stop = getattr(action, "stop_alarm", None)
			if stop:
				stop()


class WakeupService:
	"""Watch an alarm controller and execute a wakeup action once per alarm."""

	def __init__(
		self,
		alarm_controller,
		action: WakeupAction,
		now: Callable[[], datetime] | None = None,
	) -> None:
		self.alarm_controller = alarm_controller
		self.action = action
		self.now = now or (lambda: datetime.now().astimezone())
		self._stop = Event()
		self._wake_condition = Condition()
		self._lock = Lock()
		self._triggered_alarm: str | None = None
		self._awake = False
		self._listeners: list[Callable[[], None]] = []
		add_listener = getattr(alarm_controller, "add_change_listener", None)
		if add_listener:
			add_listener(self._alarm_changed)

	def _alarm_changed(self) -> None:
		with self._wake_condition:
			self._wake_condition.notify_all()

	def check(self) -> bool:
		"""Trigger the action when the current alarm is due."""
		status = self.alarm_controller.get_status()
		wake_at = status.get("wake_at")
		if not wake_at:
			return False
		alarm_key = str(wake_at)
		with self._lock:
			if self._triggered_alarm == alarm_key:
				return False
		due_at = datetime.fromisoformat(alarm_key)
		if self.now() < due_at:
			return False
		self._run_wakeup_sequence(alarm_key)
		return True

	def trigger_now(self) -> None:
		"""Run the wakeup sequence immediately for testing and manual verification."""
		status = self.alarm_controller.get_status()
		wake_at = status.get("wake_at")
		alarm_key = str(wake_at) if wake_at else None
		self._run_wakeup_sequence(alarm_key)

	def _run_wakeup_sequence(self, alarm_key: str | None) -> None:
		print("Running wakeup sequence...")
		with self._lock:
			if alarm_key is not None:
				self._triggered_alarm = alarm_key
			self._awake = True
		try:
			self.action.wake()
		finally:
			consume = getattr(self.alarm_controller, "consume", None)
			if consume:
				consume()
		self._notify_listeners()

	def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
		with self._lock:
			self._listeners.append(listener)

		def remove_listener() -> None:
			with self._lock:
				if listener in self._listeners:
					self._listeners.remove(listener)

		return remove_listener

	def _notify_listeners(self) -> None:
		with self._lock:
			listeners = tuple(self._listeners)
		for listener in listeners:
			listener()

	def get_status(self) -> dict[str, bool]:
		with self._lock:
			return {"awake": self._awake}

	def stop_alarm(self) -> None:
		stop = getattr(self.action, "stop_alarm", None)
		if stop:
			stop()
		with self._lock:
			self._awake = False
		self._notify_listeners()

	def run(self) -> None:
		while not self._stop.is_set():
			status = self.alarm_controller.get_status()
			wake_at = status.get("wake_at")
			wait_seconds = 60.0
			if wake_at:
				due_at = datetime.fromisoformat(str(wake_at))
				wait_seconds = max(0.0, (due_at - self.now()).total_seconds())
			with self._wake_condition:
				print(f"waiting {wait_seconds} seconds...")
				self._wake_condition.wait(timeout=wait_seconds)
			if not self._stop.is_set():
				try:
					self.check()
				except Exception:
					pass

	def stop(self) -> None:
		stop_alarm = getattr(self.action, "stop_alarm", None)
		if stop_alarm:
			stop_alarm()
		self._stop.set()
		with self._wake_condition:
			self._wake_condition.notify_all()


__all__ = [
	"AlarmController",
	"AlarmSchedule",
	"BRIDGE_IP",
	"CombinedWakeupAction",
	"FixedAlarmController",
	"PhilipsHueSunrise",
	"PygameAudioAlarm",
	"WakeupAction",
	"WakeupService",
]
