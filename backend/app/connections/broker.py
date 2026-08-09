"""Per-Run connection broker (spec section 51).

A tiny localhost HTTP service that lets isolated test subprocesses use the
Run-owned sessions without ever seeing hosts or credentials. It exposes only
role + command; the ConnectionManager does the real work. Bound to 127.0.0.1 and
protected by a per-Run bearer token.
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.connections.manager import ConnectionError as DeviceConnectionError
from app.connections.manager import ConnectionManager

logger = logging.getLogger("drivetest.connections.broker")


class _Handler(BaseHTTPRequestHandler):
    # Silence default noisy logging; we log meaningful events ourselves.
    def log_message(self, *_args) -> None:  # noqa: D401
        return

    @property
    def _manager(self) -> ConnectionManager:
        return self.server.manager  # type: ignore[attr-defined]

    @property
    def _token(self) -> str:
        return self.server.token  # type: ignore[attr-defined]

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        expected = f"Bearer {self._token}"
        return secrets.compare_digest(header, expected)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok", "roles": self._manager.roles})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid JSON"})
            return

        role = payload.get("role")
        try:
            if self.path == "/exec":
                output = self._manager.run(role, payload.get("command", ""))
            elif self.path == "/config":
                output = self._manager.configure(role, list(payload.get("commands", [])))
            else:
                self._send(404, {"error": "not found"})
                return
        except DeviceConnectionError as exc:
            self._send(400, {"error": str(exc)})
            return
        self._send(200, {"output": output})


class ConnectionBroker:
    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager
        self.token = secrets.token_urlsafe(24)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.base_url: str | None = None

    def start(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        server.manager = self._manager  # type: ignore[attr-defined]
        server.token = self.token  # type: ignore[attr-defined]
        self._server = server
        port = server.server_address[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self._thread = threading.Thread(target=server.serve_forever, name="conn-broker", daemon=True)
        self._thread.start()
        logger.info("broker_started url=%s roles=%s", self.base_url, self._manager.roles)

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            logger.info("broker_stopped url=%s", self.base_url)
            self._server = None
