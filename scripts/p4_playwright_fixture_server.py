from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HTML = """<!doctype html>
<html>
  <head><title>P4 Playwright Observation Fixture</title></head>
  <body>
    <main>
      <h1>P4 observation fixture</h1>
      <p id="status">Loading runtime state</p>
    </main>
    <script src="/app.js"></script>
  </body>
</html>
"""

APP_JS = """fetch('/state')
  .then((response) => response.text())
  .then((value) => {
    document.getElementById('status').textContent = value;
    console.log('P4_RUNTIME_SENTINEL');
    console.error('P4_RUNTIME_CONSOLE_ERROR');
    fetch('/missing');
  });
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._send(200, "text/html; charset=utf-8", HTML)
            return
        if self.path == "/app.js":
            self._send(200, "application/javascript; charset=utf-8", APP_JS)
            return
        if self.path == "/state":
            self._send(200, "text/plain; charset=utf-8", "Runtime Ready")
            return
        if self.path == "/missing":
            self._send(404, "text/plain; charset=utf-8", "expected missing resource")
            return
        self._send(404, "text/plain; charset=utf-8", "not found")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, content_type: str, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
