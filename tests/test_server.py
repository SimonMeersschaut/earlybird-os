from http.client import HTTPConnection
from threading import Thread
from pathlib import Path

from alarm_clock.application import ClockApplication


def test_server_serves_the_placeholder_ui(tmp_path: Path) -> None:
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "index.html").write_text("<h1>Alarm clock</h1>", encoding="utf-8")

    server = ClockApplication(web_root).create_server(port=0)
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
    assert "Alarm clock" in body
