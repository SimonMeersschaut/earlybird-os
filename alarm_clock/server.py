"""HTTP transport for the alarm clock application."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from pathlib import Path




class ClockRequestHandler(SimpleHTTPRequestHandler):
    """Serve the UI assets from the application web root."""

    def __init__(self, *args: object, message_provider, **kwargs: object) -> None:
        self.message_provider = message_provider
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._serve_message_page()
            return
        super().do_GET()

    def _serve_message_page(self) -> None:
        page = (Path(self.directory) / "index.html").read_text(encoding="utf-8")
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

    def __init__(self, host: str, port: int, web_root: Path, message_provider) -> None:
        handler = partial(ClockRequestHandler, directory=str(web_root), message_provider=message_provider)
        self.message_provider = message_provider
        super().__init__((host, port), handler)

    def server_close(self) -> None:
        stop = getattr(self.message_provider, "stop", None)
        if stop:
            stop()
        super().server_close()
