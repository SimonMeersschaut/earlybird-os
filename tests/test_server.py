from http.client import HTTPConnection
import json
from threading import Thread
from pathlib import Path

from alarm_clock.alarm import AlarmController
from alarm_clock.application import ClockApplication
from alarm_clock.calendar import AlarmCalculator
from alarm_clock.message import Message
from alarm_clock.server import ClockServer


def test_server_serves_the_clock_ui(tmp_path: Path) -> None:
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "index.html").write_text(
        '<time id="current-time">00:00:00</time>'
        '<img src="{{MESSAGE_ICON}}"><span>{{MESSAGE_TEXT}}</span>',
        encoding="utf-8",
    )
    for filename in ("weather.html", "alarm.html", "morning-briefing.html"):
        (web_root / filename).write_text(f"<h1>{filename}</h1>", encoding="utf-8")

    message = Message("/icons/test.svg", "Time to go to sleep")
    server = ClockApplication(web_root, message).create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    live_connection = None
    live_response = None

    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        app_responses = []
        for path in ("/weather.html", "/alarm.html", "/morning-briefing.html"):
            connection.request("GET", path)
            app_response = connection.getresponse()
            app_responses.append((app_response.status, app_response.read().decode("utf-8")))

        live_connection = HTTPConnection("127.0.0.1", server.server_port)
        live_connection.request("GET", "/live")
        live_response = live_connection.getresponse()
        first_event = live_response.readline().decode("utf-8").strip()
        first_data = live_response.readline().decode("utf-8").strip()

        connection.request(
            "POST",
            "/api/wakeup",
            body=json.dumps({"action": "stop"}),
            headers={"Content-Type": "application/json"},
        )
        wakeup_response = connection.getresponse()
        wakeup_body = json.loads(wakeup_response.read().decode("utf-8"))
    finally:
        if live_response is not None:
            live_response.close()
        if live_connection is not None:
            live_connection.close()
        server.shutdown()
        server.server_close()
        thread.join()

    assert response.status == 200
    assert 'id="current-time"' in body
    assert 'src="/icons/test.svg"' in body
    assert "Time to go to sleep" in body
    assert all(status == 200 for status, _ in app_responses)
    assert [body for _, body in app_responses] == [
        "<h1>weather.html</h1>",
        "<h1>alarm.html</h1>",
        "<h1>morning-briefing.html</h1>",
    ]
    assert live_response.status == 200
    assert live_response.getheader("Content-Type") == "text/event-stream"
    assert first_event == "event: message"
    assert json.loads(first_data.removeprefix("data: ")) == {
        "icon": "/icons/test.svg",
        "text": "Time to go to sleep",
    }
    assert wakeup_response.status == 200
    assert wakeup_body == {"awake": False}


def test_alarm_api_accepts_a_manual_override(tmp_path: Path) -> None:
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "index.html").write_text("<p>clock</p>", encoding="utf-8")
    (web_root / "alarm.html").write_text("<p>alarm</p>", encoding="utf-8")

    class Provider:
        calculator = AlarmCalculator()

        def get_message(self) -> Message:
            return Message("/icons/night.png", "22.00 - 07.00")

    controller = AlarmController(Provider())
    server = ClockApplication(web_root, message_provider=controller).create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("POST", "/api/alarm", body=json.dumps({"time": "09:00"}), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    assert response.status == 200
    assert body["source"] == "manual"
    assert body["manual_override"] is True
    assert "T09:00:00" in body["wake_at"]


def test_do_awake_triggers_wakeup_sequence(tmp_path: Path) -> None:
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "index.html").write_text("<p>clock</p>", encoding="utf-8")

    class Provider:
        def get_message(self) -> Message:
            return Message("/icons/night.png", "07.00")

    class Alarm:
        def get_status(self) -> dict[str, str | bool | None]:
            return {"wake_at": "2026-08-20T07:00:00+00:00", "source": "google", "manual_override": False}

    class Wakeup:
        def __init__(self) -> None:
            self.awake = False
            self._listeners = []

        def add_listener(self, listener):
            self._listeners.append(listener)

        def trigger_now(self) -> None:
            self.awake = True
            for listener in tuple(self._listeners):
                listener()

        def get_status(self) -> dict[str, bool]:
            return {"awake": self.awake}

    wakeup = Wakeup()
    server = ClockServer("127.0.0.1", 0, web_root, Provider(), Alarm(), wakeup)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/do-awake")
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    assert response.status == 200
    assert body == {"awake": True}
