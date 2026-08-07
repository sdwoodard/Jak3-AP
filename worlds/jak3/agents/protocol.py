"""Versioned handshake protocol shared by the Python client and GOAL bridge."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from time import monotonic
from typing import Awaitable, Callable, Protocol

from ..versions import GAME_INTEGRATION_VERSION, PROTOCOL_VERSION

PING_INTERVAL_SECONDS = 1.0
COMMAND_TIMEOUT_SECONDS = 3.0
SNAPSHOT_POLL_SECONDS = 0.05


class ClientStatus(IntEnum):
    STARTING = 0
    AP_DISCONNECTED = 1
    AP_CONNECTED = 2
    STOPPING = 3
    ERROR = 4


class GameStatus(IntEnum):
    SOURCE_LOADED = 1
    READY = 2
    PROTOCOL_MISMATCH = 3
    INTEGRATION_MISMATCH = 4
    CLIENT_DISCONNECTED = 5
    ERROR = 6


class ProtocolCommand(IntEnum):
    NONE = 0
    HELLO = 1
    PING = 2
    DISCONNECT = 3


class ProtocolResult(IntEnum):
    NONE = 0
    OK = 1
    PONG = 2
    PROTOCOL_MISMATCH = 3
    INTEGRATION_MISMATCH = 4
    INVALID_SESSION = 5
    STALE_COMMAND = 6
    ERROR = 7


class ProtocolCompatibilityError(ConnectionError):
    """The Python client and loaded GOAL integration cannot communicate."""


class ProtocolVersionMismatch(ProtocolCompatibilityError):
    def __init__(self, found: int) -> None:
        self.expected = PROTOCOL_VERSION
        self.found = found
        super().__init__(
            f"Jak 3 protocol mismatch: client expects {self.expected}, game reports {self.found}. "
            "Reinstall the APWorld bridge so the client and OpenGOAL source match."
        )


class GameIntegrationVersionMismatch(ProtocolCompatibilityError):
    def __init__(self, found: int | None) -> None:
        self.expected = GAME_INTEGRATION_VERSION
        self.found = found
        rendered = "missing" if found is None else str(found)
        super().__init__(
            "Jak 3 game-integration mismatch: "
            f"client expects {self.expected}, game reports {rendered}. "
            "Reinstall the APWorld bridge so the client and OpenGOAL source match."
        )


@dataclass(frozen=True)
class BridgeSnapshot:
    snapshot_revision: int
    protocol_version: int
    game_integration_version: int
    connection_ready: bool
    session_id: str
    client_heartbeat: int
    client_status: ClientStatus
    game_heartbeat: int
    game_status: GameStatus
    last_command: ProtocolCommand
    last_command_sequence: int
    last_result: ProtocolResult
    message: str


class ReplTransport(Protocol):
    async def send_form(self, form: str, timeout: float = 10.0) -> str: ...


def goal_string_literal(value: str, *, limit: int = 96) -> str:
    """Encode a bounded printable ASCII string for an nREPL GOAL form."""

    if not value or len(value) > limit or any(ord(character) < 32 for character in value):
        raise ValueError(f"GOAL protocol strings must contain 1-{limit} printable characters")
    safe = "".join(character if ord(character) < 127 else "?" for character in value)
    return '"' + safe.replace("\\", "\\\\").replace('"', '\\"') + '"'


def goal_path_literal(value: str) -> str:
    """Encode an absolute shared-state path without the short status-string limit."""

    if not value or len(value) > 500 or any(ord(character) < 32 for character in value):
        raise ValueError("JAK3_AP_STATE must be a non-empty path of at most 500 characters")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _parse_int(value: str) -> int:
    if not value or not value.lstrip("-").isdigit():
        raise ValueError(value)
    return int(value)


def parse_snapshot_text(text: str) -> BridgeSnapshot | None:
    """Parse one complete snapshot; torn or malformed snapshots are ignored."""

    lines = text.splitlines()
    if len(lines) < 2:
        return None
    first_key, separator, first_value = lines[0].partition(" ")
    last_key, last_separator, last_value = lines[-1].partition(" ")
    if not separator or not last_separator:
        return None
    if first_key != "snapshot_begin" or last_key != "snapshot_end":
        return None
    try:
        begin_revision = _parse_int(first_value)
        end_revision = _parse_int(last_value)
    except ValueError:
        return None
    if begin_revision < 0 or begin_revision != end_revision:
        return None

    values: dict[str, str] = {}
    for line in lines[1:-1]:
        key, separator, value = line.partition(" ")
        if not separator or not key or key in values:
            return None
        values[key] = value

    required = {
        "protocol_version",
        "game_integration_version",
        "connection_ready",
        "session_id",
        "client_heartbeat",
        "client_status",
        "game_heartbeat",
        "game_status",
        "last_command",
        "last_command_sequence",
        "last_result",
        "message",
    }
    if set(values) != required:
        return None

    try:
        ready = _parse_int(values["connection_ready"])
        if ready not in {0, 1}:
            return None
        session_id = values["session_id"]
        message = values["message"]
        if (
            not session_id
            or len(session_id) > 96
            or any(character.isspace() for character in session_id)
        ):
            return None
        if len(message) > 127 or any(ord(character) < 32 for character in message):
            return None
        snapshot = BridgeSnapshot(
            snapshot_revision=begin_revision,
            protocol_version=_parse_int(values["protocol_version"]),
            game_integration_version=_parse_int(values["game_integration_version"]),
            connection_ready=bool(ready),
            session_id=session_id,
            client_heartbeat=_parse_int(values["client_heartbeat"]),
            client_status=ClientStatus(_parse_int(values["client_status"])),
            game_heartbeat=_parse_int(values["game_heartbeat"]),
            game_status=GameStatus(_parse_int(values["game_status"])),
            last_command=ProtocolCommand(_parse_int(values["last_command"])),
            last_command_sequence=_parse_int(values["last_command_sequence"]),
            last_result=ProtocolResult(_parse_int(values["last_result"])),
            message=message,
        )
    except (ValueError, KeyError):
        return None
    if snapshot.protocol_version < 0 or snapshot.game_integration_version < 0:
        return None
    if snapshot.client_heartbeat < -1 or snapshot.game_heartbeat < 0:
        return None
    return snapshot


def read_snapshot(path: Path) -> BridgeSnapshot | None:
    try:
        return parse_snapshot_text(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError):
        return None


def read_reported_versions(path: Path) -> tuple[int | None, int | None]:
    """Read version lines even from a legacy or otherwise incompatible snapshot."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        return None, None
    protocol_version: int | None = None
    integration_version: int | None = None
    for line in lines:
        key, separator, value = line.partition(" ")
        if not separator:
            continue
        try:
            parsed = _parse_int(value)
        except ValueError:
            continue
        if key in {"protocol_version", "version"}:
            protocol_version = parsed
        elif key == "game_integration_version":
            integration_version = parsed
    return protocol_version, integration_version


def format_snapshot(snapshot: BridgeSnapshot) -> str:
    """Render the GOAL-owned wire format for fixtures and contract tests."""

    return "\n".join(
        (
            f"snapshot_begin {snapshot.snapshot_revision}",
            f"protocol_version {snapshot.protocol_version}",
            f"game_integration_version {snapshot.game_integration_version}",
            f"connection_ready {int(snapshot.connection_ready)}",
            f"session_id {snapshot.session_id}",
            f"client_heartbeat {snapshot.client_heartbeat}",
            f"client_status {int(snapshot.client_status)}",
            f"game_heartbeat {snapshot.game_heartbeat}",
            f"game_status {int(snapshot.game_status)}",
            f"last_command {int(snapshot.last_command)}",
            f"last_command_sequence {snapshot.last_command_sequence}",
            f"last_result {int(snapshot.last_result)}",
            f"message {snapshot.message}",
            f"snapshot_end {snapshot.snapshot_revision}",
            "",
        )
    )


def validate_compatibility(snapshot: BridgeSnapshot) -> None:
    if snapshot.protocol_version != PROTOCOL_VERSION:
        raise ProtocolVersionMismatch(snapshot.protocol_version)
    if snapshot.game_integration_version != GAME_INTEGRATION_VERSION:
        raise GameIntegrationVersionMismatch(snapshot.game_integration_version)


class BridgeProtocol:
    """Drive one temporary client/game handshake over nREPL plus a snapshot file."""

    def __init__(
        self,
        repl: ReplTransport,
        state_path: Path,
        session_id: str,
        *,
        command_timeout: float = COMMAND_TIMEOUT_SECONDS,
        poll_interval: float = SNAPSHOT_POLL_SECONDS,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        goal_string_literal(session_id)
        self.repl = repl
        self.state_path = state_path
        self.session_id = session_id
        self.command_timeout = command_timeout
        self.poll_interval = poll_interval
        self.sleeper = sleeper
        self.next_sequence = 0
        self.last_snapshot: BridgeSnapshot | None = None

    async def _wait_for(
        self,
        predicate: Callable[[BridgeSnapshot], bool],
        description: str,
        *,
        check_versions: bool = False,
    ) -> BridgeSnapshot:
        deadline = monotonic() + self.command_timeout
        while monotonic() < deadline:
            snapshot = read_snapshot(self.state_path)
            if snapshot is not None:
                self.last_snapshot = snapshot
                if check_versions:
                    validate_compatibility(snapshot)
                if predicate(snapshot):
                    return snapshot
            if check_versions:
                protocol_version, integration_version = read_reported_versions(self.state_path)
                if protocol_version is not None and protocol_version != PROTOCOL_VERSION:
                    raise ProtocolVersionMismatch(protocol_version)
                if (
                    protocol_version == PROTOCOL_VERSION
                    and integration_version is not None
                    and integration_version != GAME_INTEGRATION_VERSION
                ):
                    raise GameIntegrationVersionMismatch(integration_version)
            await self.sleeper(self.poll_interval)
        if check_versions:
            protocol_version, integration_version = read_reported_versions(self.state_path)
            if protocol_version is not None and protocol_version != PROTOCOL_VERSION:
                raise ProtocolVersionMismatch(protocol_version)
            if (
                protocol_version == PROTOCOL_VERSION
                and integration_version != GAME_INTEGRATION_VERSION
            ):
                raise GameIntegrationVersionMismatch(integration_version)
        raise ConnectionError(
            f"OpenGOAL did not publish {description} within {self.command_timeout:g} seconds"
        )

    async def initialize(self, client_status: ClientStatus) -> BridgeSnapshot:
        try:
            self.state_path.unlink(missing_ok=True)
        except OSError as exc:
            raise ConnectionError(
                f"Could not reset temporary bridge state {self.state_path}: {exc}"
            ) from exc

        state_path = goal_path_literal(str(self.state_path))
        await self.repl.send_form(f"(ap-set-state-path! {state_path})")
        await self._wait_for(
            lambda snapshot: True,
            "a complete bridge snapshot",
            check_versions=True,
        )

        session_id = goal_string_literal(self.session_id)
        await self.repl.send_form(
            f"(ap-client-hello! {PROTOCOL_VERSION} {GAME_INTEGRATION_VERSION} "
            f"{session_id} {int(client_status)})"
        )
        snapshot = await self._wait_for(
            lambda current: (
                current.session_id == self.session_id
                and current.connection_ready
                and current.last_command == ProtocolCommand.HELLO
                and current.last_result == ProtocolResult.OK
            ),
            "an accepted client hello",
            check_versions=True,
        )
        self.next_sequence = max(0, snapshot.client_heartbeat + 1)
        return snapshot

    async def ping(
        self,
        client_status: ClientStatus,
        *,
        sequence: int | None = None,
    ) -> BridgeSnapshot:
        command_sequence = self.next_sequence if sequence is None else sequence
        if command_sequence < 0:
            raise ValueError("Ping sequences must be non-negative")
        before_command = read_snapshot(self.state_path) or self.last_snapshot
        previous_revision = (
            before_command.snapshot_revision if before_command is not None else -1
        )
        session_id = goal_string_literal(self.session_id)
        await self.repl.send_form(
            f"(ap-ping! {session_id} {command_sequence} {int(client_status)})"
        )
        snapshot = await self._wait_for(
            lambda current: (
                current.session_id == self.session_id
                and current.connection_ready
                and current.client_heartbeat == command_sequence
                and current.game_heartbeat == command_sequence + 1
                and current.last_command == ProtocolCommand.PING
                and current.last_command_sequence == command_sequence
                and current.last_result == ProtocolResult.PONG
                and current.snapshot_revision > previous_revision
            ),
            f"pong {command_sequence + 1}",
            check_versions=True,
        )
        if sequence is None:
            self.next_sequence = command_sequence + 1
        return snapshot

    async def disconnect(self) -> None:
        session_id = goal_string_literal(self.session_id)
        await self.repl.send_form(
            "(ap-client-disconnect! "
            f"{session_id} {self.next_sequence} {int(ClientStatus.STOPPING)})"
        )
