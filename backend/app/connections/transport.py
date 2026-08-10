"""Pluggable device transports (spec section 51).

`SimulatedTransport` is the default so the platform runs without live devices; it
is backed by a small stateful DNOS model so config/commit/rollback and
`show interfaces description` behave realistically in dev. `SshTransport` uses a
single persistent paramiko shell so config mode/commit/rollback persist across
lines on a real box. paramiko is imported lazily so the app works without it when
the simulated transport is used.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.connections.devices import DeviceSpec

logger = logging.getLogger("drivetest.connections.transport")


@dataclass
class ExecResult:
    """Outcome of running one command on a device.

    `output` is the cleaned device output (echo + prompt stripped) used by tests.
    `raw` is the verbatim terminal text (device prompt with hostname + echoed
    command + output) so the session transcript reads like a real CLI session.
    """

    status: int
    output: str
    raw: str


class Transport(Protocol):
    name: str

    def open(self, spec: DeviceSpec, password: str | None) -> Any: ...

    def exec(self, client: Any, command: str, timeout: float) -> ExecResult: ...

    def banner(self, client: Any) -> str: ...

    def alive(self, client: Any) -> bool: ...

    def close(self, client: Any) -> None: ...


# --------------------------------------------------------------------------- #
# Simulated DNOS device (dev default)
# --------------------------------------------------------------------------- #

_DEFAULT_INTERFACES = [
    "ge100-0/0/0",
    "ge100-0/0/1",
    "ge100-0/0/2",
    "ge100-0/0/3",
    "mgmt0",
    "lo0",
]


class SimulatedDnosDevice:
    """A minimal, stateful DNOS model: enough for interface-description tests.

    Models operational/config modes, a running vs candidate description map, a
    commit history for `rollback`, and a parseable `show interfaces description`.
    Unknown commands return "ok" so simple demos (e.g. `show version`) still pass.
    """

    def __init__(self, spec: DeviceSpec) -> None:
        self.spec = spec
        self.hostname = (spec.host or "DUT").split(".")[0]
        self.interfaces = list(_DEFAULT_INTERFACES)
        self.running: dict[str, str] = {name: "" for name in self.interfaces}
        self.candidate: dict[str, str] | None = None
        self.history: list[dict[str, str]] = []
        self.mode = "operational"
        self._stack: list[str] = []
        self._current_iface: str | None = None

    # -- helpers -----------------------------------------------------------
    def prompt(self) -> str:
        """A DNOS-style prompt reflecting the current mode, e.g. `host#`."""
        if self.mode == "config":
            return f"{self.hostname}(config)# "
        return f"{self.hostname}# "

    def _ensure_candidate(self) -> dict[str, str]:
        if self.candidate is None:
            self.candidate = dict(self.running)
        return self.candidate

    def _render_show_interfaces_description(self) -> str:
        lines = ["Interface            Admin   Oper    Description"]
        for name in self.interfaces:
            desc = self.running.get(name, "")
            lines.append(f"{name:<20} up      up      {desc}".rstrip())
        return "\n".join(lines) + "\n"

    # -- command handling --------------------------------------------------
    def handle(self, raw: str) -> str:
        line = raw.strip()
        if not line:
            return ""

        low = line.lower()

        if low == "show interfaces description":
            return self._render_show_interfaces_description()

        if low == "configure":
            self.mode = "config"
            self._stack = []
            self._current_iface = None
            self._ensure_candidate()
            return ""

        if low in ("end", "top"):
            self._stack = []
            self._current_iface = None
            return ""

        if low == "exit" or line == "!":
            if self._stack:
                popped = self._stack.pop()
                if popped == self._current_iface:
                    self._current_iface = None
            elif low == "exit":
                self.mode = "operational"
            return ""

        if low == "commit":
            cand = self._ensure_candidate()
            self.history.append(dict(self.running))
            self.running = dict(cand)
            self.candidate = dict(self.running)
            return "commit complete\n"

        if low.startswith("rollback"):
            parts = line.split()
            n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            if len(self.history) >= n:
                target = self.history[-n]
                self.candidate = dict(target)
            else:
                self.candidate = dict(self.running)
            return ""

        if low == "interfaces":
            self._stack = ["interfaces"]
            self._current_iface = None
            return ""

        # No-op leaf remove.
        if low.startswith("no description"):
            if self._current_iface is not None:
                self._ensure_candidate()[self._current_iface] = ""
            return ""

        if low.startswith("description"):
            if self._current_iface is not None:
                self._ensure_candidate()[self._current_iface] = _parse_description(line)
            return ""

        # Inside the interfaces container, a bare token is an interface id
        # (auto-created on first reference, matching DNOS walk-in semantics).
        if self._stack and self._stack[-1] == "interfaces":
            iface = line
            if iface not in self.interfaces:
                self.interfaces.append(iface)
                self.running.setdefault(iface, "")
            self._ensure_candidate().setdefault(iface, self.running.get(iface, ""))
            self._stack.append(iface)
            self._current_iface = iface
            return ""

        # Anything else (e.g. "show version") -> benign ok.
        return "ok\n"


def _parse_description(line: str) -> str:
    # line like: description "some text"  OR  description some_text
    rest = line[len("description"):].strip()
    if len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"':
        return rest[1:-1]
    return rest


class SimulatedTransport:
    name = "simulated"

    def open(self, spec: DeviceSpec, password: str | None) -> Any:
        logger.info("sim_open role=%s host=%s", spec.role, spec.host)
        return SimulatedDnosDevice(spec)

    def exec(self, client: Any, command: str, timeout: float) -> ExecResult:
        # Capture the prompt as it is BEFORE the command runs (that's where the
        # user "typed" it), then render a realistic terminal exchange.
        prompt = client.prompt()
        output = client.handle(command)
        raw = f"{prompt}{command}\n{output}"
        return ExecResult(0, output, raw)

    def banner(self, client: Any) -> str:
        # The initial login line a real device prints before the first command.
        return f"Connected to {client.hostname} (simulated DNOS).\n"

    def alive(self, client: Any) -> bool:
        return isinstance(client, SimulatedDnosDevice)

    def close(self, client: Any) -> None:
        return None


# --------------------------------------------------------------------------- #
# Real SSH transport (persistent interactive shell)
# --------------------------------------------------------------------------- #

# Matches a DNOS-style prompt at the end of the buffer, operational or config.
_PROMPT_RE = re.compile(r"[\w.\-/:@]+(\([^)]*\))?#\s*$")


class SshTransport:
    """Real SSH via one persistent shell so config mode/commit/rollback persist."""

    name = "ssh"

    def __init__(self, connect_timeout: float, default_password: str = "") -> None:
        self._connect_timeout = connect_timeout
        self._default_password = default_password

    def open(self, spec: DeviceSpec, password: str | None) -> Any:
        import paramiko  # lazy import

        # Password precedence: per-device credential_ref secret, else platform default.
        resolved_password = password or self._default_password or None

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info("ssh_connect host=%s port=%s user=%s", spec.host, spec.port, spec.username)
        client.connect(
            hostname=spec.host,
            port=spec.port,
            username=spec.username,
            password=resolved_password,
            timeout=self._connect_timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        chan = client.invoke_shell(width=200, height=1000)
        session = {"client": client, "chan": chan}
        # Drain the login banner / first prompt and keep it verbatim so the
        # transcript starts like a real session (hostname prompt included).
        session["banner"] = self._read_until_prompt(chan, timeout=self._connect_timeout)
        return session

    def exec(self, client: Any, command: str, timeout: float) -> ExecResult:
        chan = client["chan"]
        chan.send(command + "\n")
        buf = self._read_until_prompt(chan, timeout=timeout)
        # `buf` is the raw terminal exchange: echoed command + output + the next
        # prompt (with hostname). Keep it verbatim for the transcript; hand tests
        # a cleaned version with the echo/prompt removed.
        return ExecResult(0, _strip_echo_and_prompt(buf, command), buf)

    def banner(self, client: Any) -> str:
        return client.get("banner", "")

    def alive(self, client: Any) -> bool:
        try:
            transport = client["client"].get_transport()
            chan = client["chan"]
            return bool(transport and transport.is_active() and not chan.closed)
        except Exception:  # noqa: BLE001
            return False

    def close(self, client: Any) -> None:
        try:
            client["client"].close()
        except Exception:  # noqa: BLE001
            logger.warning("ssh_close_error")

    @staticmethod
    def _read_until_prompt(chan, timeout: float) -> str:
        buf = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if chan.recv_ready():
                chunk = chan.recv(65535).decode("utf-8", errors="replace")
                buf += chunk
                if _PROMPT_RE.search(buf):
                    break
            else:
                time.sleep(0.05)
        return buf


def _strip_echo_and_prompt(output: str, command: str) -> str:
    lines = output.splitlines()
    # Drop the echoed command (first line) if present.
    if lines and command.strip() and command.strip() in lines[0]:
        lines = lines[1:]
    # Drop a trailing prompt line.
    if lines and _PROMPT_RE.search(lines[-1]):
        lines = lines[:-1]
    return "\n".join(lines).strip("\n")


def get_transport() -> Transport:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.ssh_transport == "ssh":
        return SshTransport(
            connect_timeout=settings.ssh_connect_timeout_seconds,
            default_password=settings.ssh_default_password,
        )
    return SimulatedTransport()
