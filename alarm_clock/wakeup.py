"""Wakeup monitoring and Philips Hue sunrise behavior."""

from __future__ import annotations

from datetime import datetime
from threading import Event, Lock
from typing import Callable, Protocol

from phue import Bridge

BRIDGE_IP = '10.2.1.210'

bridge = Bridge(BRIDGE_IP)
bridge.connect()


class WakeupAction(Protocol):
    def wake(self) -> None:
        """Start the configured wakeup behavior."""


class PhilipsHueSunrise:
    """Trigger a gradual sunrise on the configured Philips Hue group."""

    def __init__(self, group_name: str) -> None:
        
        self.group_name = group_name

    def wake(self) -> None:
        
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
        interval: float = 1.0,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.alarm_controller = alarm_controller
        self.action = action
        self.interval = interval
        self.now = now or (lambda: datetime.now().astimezone())
        self._stop = Event()
        self._lock = Lock()
        self._triggered_alarm: str | None = None
        self._awake = False

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
        self.action.wake()
        with self._lock:
            self._triggered_alarm = alarm_key
            self._awake = True
        self.alarm_controller.consume()
        return True

    def get_status(self) -> dict[str, bool]:
        with self._lock:
            return {"awake": self._awake}

    def run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.check()
            except Exception:
                # Keep the service alive if the bridge or calendar is unavailable.
                pass

    def stop(self) -> None:
        self._stop.set()