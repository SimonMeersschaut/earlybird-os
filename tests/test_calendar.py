from datetime import datetime, timedelta, timezone

from alarm_clock.alarm import AlarmController, WakeupService
from alarm_clock.calendar import AlarmCalculator, CalendarEvent
from alarm_clock.message import Message
from alarm_clock.wakeup import WakeupService as LegacyWakeupService


def test_alarm_uses_nine_hours_before_ninety_minutes_before_first_timed_event() -> None:
    now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    event_time = datetime(2026, 8, 20, 8, 30, tzinfo=timezone.utc)
    events = [CalendarEvent(event_time)]

    message = AlarmCalculator().message_for(events, now)

    assert message.text == "07.00"


def test_alarm_ignores_all_day_events() -> None:
    now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    timed_event = CalendarEvent(datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc))
    all_day_event = CalendarEvent(datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc), all_day=True)

    message = AlarmCalculator().message_for([all_day_event, timed_event], now)

    assert message.text == "06.30"


class FakeMessageProvider:
    def __init__(self) -> None:
        self.message = Message("/icons/night.png", "22.00 - 07.00")

    def get_message(self) -> Message:
        return self.message


def test_manual_alarm_override_survives_refresh_until_consumed() -> None:
    provider = FakeMessageProvider()
    controller = AlarmController(provider)
    wake_at = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)

    controller.set_manual_time(wake_at)
    provider.message = Message("/icons/night.png", "21.00 - 06.00")
    controller.refresh()

    status = controller.get_status()
    assert status["manual_override"] is True
    assert status["source"] == "manual"
    assert status["wake_at"] == wake_at.isoformat()

    controller.consume()

    assert controller.get_status()["manual_override"] is False
    assert controller.get_status()["source"] == "google"


def test_alarm_module_exposes_wakeup_service_and_keeps_legacy_alias() -> None:
    assert WakeupService is LegacyWakeupService


def test_wakeup_triggers_due_alarm_once() -> None:
    now = datetime(2026, 8, 20, 7, 0, tzinfo=timezone.utc)

    class Controller:
        def __init__(self) -> None:
            self.consumed = False

        def get_status(self) -> dict[str, str]:
            return {"wake_at": "2026-08-20T06:30:00+00:00"}

        def consume(self) -> None:
            self.consumed = True

    class Action:
        def __init__(self) -> None:
            self.calls = 0

        def wake(self) -> None:
            self.calls += 1

    controller = Controller()
    action = Action()
    service = WakeupService(controller, action, now=lambda: now)

    assert service.check() is True
    assert action.calls == 1
    assert controller.consumed is True
    assert service.get_status() == {"awake": True}
    assert service.check() is False
    assert action.calls == 1