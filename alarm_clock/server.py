"""HTTP transport for the alarm clock application."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from html import escape
import json
from datetime import datetime, timedelta
from pathlib import Path




class ClockRequestHandler(SimpleHTTPRequestHandler):
    """Serve the UI assets from the application web root."""

    def __init__(self, *args: object, message_provider, alarm_controller, **kwargs: object) -> None:
        self.message_provider = message_provider
        self.alarm_controller = alarm_controller
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/message":
            self._serve_message_json()
            return
        if self.path == "/api/alarm":
            self._serve_json(self.alarm_controller.get_status())
            return
        page_paths = {
            "/": "index.html",
            "/index.html": "index.html",
            "/weather": "weather.html",
            "/weather.html": "weather.html",
            "/alarm": "alarm.html",
            "/alarm.html": "alarm.html",
            "/morning-briefing": "morning-briefing.html",
            "/morning-briefing.html": "morning-briefing.html",
        }
        if self.path in page_paths:
            self._serve_page(page_paths[self.path], inject_message=self.path in {"/", "/index.html"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/alarm":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            if payload.get("action") == "automatic":
                self.alarm_controller.consume()
            elif payload.get("action") == "consume":
                self.alarm_controller.consume()
            else:
                value = datetime.strptime(payload["time"], "%H:%M").time()
                tomorrow = datetime.now().astimezone() + timedelta(days=1)
                wake_at = tomorrow.replace(hour=value.hour, minute=value.minute, second=0, microsecond=0)
                self.alarm_controller.set_manual_time(wake_at)
            self._serve_json(self.alarm_controller.get_status())
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send_error(400, "Expected JSON with a valid HH:MM time")

    def _serve_message_json(self) -> None:
        message = self.message_provider.get_message()
        body = json.dumps({"icon": message.icon, "text": message.text}).encode("utf-8")

        self._serve_json({"icon": message.icon, "text": message.text})

    def _serve_json(self, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_page(self, filename: str, inject_message: bool) -> None:
        page = (Path(self.directory) / filename).read_text(encoding="utf-8")
        if inject_message:
            message = self.message_provider.get_message()
            page = page.replace("{{MESSAGE_ICON}}", escape(message.icon, quote=True))
            page = page.replace("{{MESSAGE_TEXT}}", escape(message.text))
        body = page.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep the default request logging behavior explicit and replaceable."""
        super().log_message(format, *args)


class ClockServer(ThreadingHTTPServer):
    """HTTP server configured with the clock application's asset directory."""

    def __init__(self, host: str, port: int, web_root: Path, message_provider, alarm_controller=None) -> None:
        alarm_controller = alarm_controller or message_provider
        handler = partial(
            ClockRequestHandler,
            directory=str(web_root),
            message_provider=message_provider,
            alarm_controller=alarm_controller,
        )
        self.message_provider = message_provider
        self.alarm_controller = alarm_controller
        super().__init__((host, port), handler)

    def server_close(self) -> None:
        stop = getattr(self.alarm_controller, "stop", None)
        if stop:
            stop()
        super().server_close()
