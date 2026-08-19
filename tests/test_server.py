from http.client import HTTPConnection
from threading import Thread
from pathlib import Path

from alarm_clock.application import ClockApplication
from alarm_clock.message import Message


def test_server_serves_the_clock_ui(tmp_path: Path) -> None:
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "index.html").write_text(
        '<time id="current-time">00:00:00</time>'
        '<img src="{{MESSAGE_ICON}}"><span>{{MESSAGE_TEXT}}</span>',
        encoding="utf-8",
    )

    message = Message("/icons/test.svg", "Time to go to sleep")
    server = ClockApplication(web_root, message).create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    assert response.status == 200
    assert 'id="current-time"' in body
    assert 'src="/icons/test.svg"' in body
    assert "Time to go to sleep" in body
