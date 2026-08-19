from datetime import datetime, timedelta, timezone

from alarm_clock.calendar import AlarmCalculator, CalendarEvent


def test_alarm_uses_nine_hours_before_ninety_minutes_before_first_timed_event() -> None:
    now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    event_time = datetime(2026, 8, 20, 8, 30, tzinfo=timezone.utc)
    events = [CalendarEvent(event_time)]

    message = AlarmCalculator().message_for(events, now)

    assert message.text == "22.00 - 07.00"


def test_alarm_ignores_all_day_events() -> None:
    now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    timed_event = CalendarEvent(datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc))
    all_day_event = CalendarEvent(datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc), all_day=True)

    message = AlarmCalculator().message_for([all_day_event, timed_event], now)

    assert message.text == "21.30 - 06.30"