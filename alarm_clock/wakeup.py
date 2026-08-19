"""Wakeup monitoring and Philips Hue sunrise behavior."""

from __future__ import annotations

from datetime import datetime
from threading import Condition, Event, Lock
from typing import Callable, Protocol

BRIDGE_IP = '10.2.1.210'


class WakeupAction(Protocol):
    def wake(self) -> None:
        """Start the configured wakeup behavior."""


class PhilipsHueSunrise:
    """Trigger a gradual sunrise on the configured Philips Hue group."""

    def __init__(self, group_name: str, bridge_ip: str = BRIDGE_IP) -> None:
        self.group_name = group_name
        self.bridge_ip = bridge_ip
        self._bridge = None

    def _get_bridge(self):
        if self._bridge is None:
            from phue import Bridge

            self._bridge = Bridge(self.bridge_ip)
            self._bridge.connect()
        return self._bridge

    def wake(self) -> None:
        bridge = self._get_bridge()
        group = bridge.get_group(bridge.get_group_id_by_name(self.group_name))
        command = {
            "on": True,
            "bri": 254,
            "hue": 5000,
            "sat": 200,
            "transitiontime": 200,
        }
        for light_id in group["lights"]:
            bridge.set_light(int(light_id), command)


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
        with self._lock:
            self._triggered_alarm = alarm_key
            self._awake = True
        try:
            self.action.wake()
        finally:
            self.alarm_controller.consume()
        self._notify_listeners()
        return True

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
                    # Keep the timer alive if Hue is unavailable.
                    pass

    def stop(self) -> None:
        self._stop.set()
        with self._wake_condition:
            self._wake_condition.notify_all()