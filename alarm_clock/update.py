"""Shared periodic updater for alarm-clock features."""

from __future__ import annotations

from datetime import timedelta
from threading import Event


class UpdateScheduler:
    """Run refresh hooks on a fixed interval using a single timer loop."""

    def __init__(
        self,
        alarm_controller=None,
        calendar_provider=None,
        interval: timedelta = timedelta(seconds=10),
    ) -> None:
        self.alarm_controller = alarm_controller
        self.calendar_provider = calendar_provider
        self.interval = interval
        self._stop = Event()

    def update(self) -> None:
        print("Updating")
        refresh = getattr(self.calendar_provider, "refresh", None)
        if refresh:
            try:
                refresh()
            except Exception:
                # Calendar data should stay best-effort.
                pass

        refresh = getattr(self.alarm_controller, "refresh", None)
        if refresh:
            try:
                refresh()
            except Exception:
                # Keep the previous alarm when a refresh temporarily fails.
                pass

    def run(self) -> None:
        self.update()
        while not self._stop.wait(self.interval.total_seconds()):
            self.update()

    def stop(self) -> None:
        self._stop.set()
