"""Protocol-3 runtime snapshot and duplicate-safe harmless command transport."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import MutableMapping
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from time import monotonic
from typing import Awaitable, Callable, Protocol

from .diagnostics import GoalDiagnosticRecord, hash_identifier
from ..registry import ITEM_TABLE_HASH, LOCATION_TABLE_HASH, MISSION_TABLE_HASH
from ..versions import (
    BRIDGE_RUNTIME_VERSION,
    GAME_INTEGRATION_VERSION,
    ITEM_TABLE_VERSION,
    LOCATION_TABLE_VERSION,
    MISSION_TABLE_VERSION,
    PROTOCOL_VERSION,
    SLOT_DATA_VERSION,
    STATE_SCHEMA_VERSION,
)

PING_INTERVAL_SECONDS = 1.0
COMMAND_TIMEOUT_SECONDS = 3.0
SNAPSHOT_POLL_SECONDS = 0.05
DIAGNOSTIC_ACK_TIMEOUT_SECONDS = 0.25
RECENT_RECEIPT_LIMIT = 8
WIRE_INT32_MIN = -(2**31)
WIRE_INT32_MAX = 2**31 - 1


class ClientStatus(IntEnum):
    STARTING = 0
    AP_DISCONNECTED = 1
    AP_CONNECTED = 2
    STOPPING = 3
    ERROR = 4


class GameStatus(IntEnum):
    SOURCE_LOADED = 1
    READY = 2
    INCOMPATIBLE = 3
    CLIENT_DISCONNECTED = 4
    ERROR = 5


class ProtocolCommand(IntEnum):
    NONE = 0
    HELLO = 1
    PING = 2
    QUERY_STATE = 3
    DISCONNECT = 4
    SET_TEST_TARGET = 100
    TEST_ADDITIVE_EFFECT = 101


class ProtocolResult(IntEnum):
    NONE = 0
    OK = 1
    PONG = 2
    APPLIED = 3
    ALREADY_APPLIED = 4
    QUEUED = 5
    UNSAFE_NOW = 6
    INCOMPATIBLE = 7
    INVALID_PAYLOAD = 8
    FAILED = 9


class ProtocolError(IntEnum):
    NONE = 0
    PROTOCOL_MISMATCH = 1
    GAME_INTEGRATION_MISMATCH = 2
    STATE_SCHEMA_MISMATCH = 3
    SLOT_DATA_MISMATCH = 4
    ITEM_TABLE_MISMATCH = 5
    LOCATION_TABLE_MISMATCH = 6
    MISSION_TABLE_MISMATCH = 7
    INVALID_CLIENT_SESSION = 8
    INVALID_GAME_SESSION = 9
    OUT_OF_ORDER_COMMAND_ID = 10
    DUPLICATE_COMMAND_CONFLICT = 11
    UNKNOWN_COMMAND = 12
    INVALID_PAYLOAD = 13
    AP_STATE_NOT_LOADED = 14
    AP_STATE_NOT_BOUND = 15
    SAVE_NOT_LOADED = 16
    UNSAFE_GAME_STATE = 17
    ADDITIVE_EFFECT_FORBIDDEN = 18
    INTERNAL_FAILURE = 19


class NativeSaveEligibility(IntEnum):
    UNKNOWN = 0
    FRESH_UNPROGRESSED = 1
    INELIGIBLE = 2


class ProtocolCompatibilityError(ConnectionError):
    """The Python client and loaded GOAL integration cannot communicate."""


class ProtocolVersionMismatch(ProtocolCompatibilityError):
    def __init__(self, found: int) -> None:
        self.expected = PROTOCOL_VERSION
        self.found = found
        super().__init__(
            f"Jak 3 protocol mismatch: client expects {self.expected}, game reports {found}. "
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


class DataContractMismatch(ProtocolCompatibilityError):
    def __init__(self, field: str, expected: int | str, found: int | str) -> None:
        self.field = field
        self.expected = expected
        self.found = found
        super().__init__(
            f"Jak 3 {field} mismatch: client expects {expected}, game reports {found}."
        )


@dataclass(frozen=True)
class CommandReceipt:
    command_id: int
    command_kind: ProtocolCommand | int
    payload: int
    result: ProtocolResult
    error_code: ProtocolError = ProtocolError.NONE


@dataclass(frozen=True)
class BridgeSnapshot:
    snapshot_revision: int = 0
    protocol_version: int = PROTOCOL_VERSION
    game_integration_version: int = GAME_INTEGRATION_VERSION
    bridge_runtime_version: int = BRIDGE_RUNTIME_VERSION
    bridge_activation_generation: int = 1
    state_schema_version: int = STATE_SCHEMA_VERSION
    slot_data_version: int = SLOT_DATA_VERSION
    item_table_version: int = ITEM_TABLE_VERSION
    location_table_version: int = LOCATION_TABLE_VERSION
    mission_table_version: int = MISSION_TABLE_VERSION
    item_table_hash: str = ITEM_TABLE_HASH
    location_table_hash: str = LOCATION_TABLE_HASH
    mission_table_hash: str = MISSION_TABLE_HASH
    connection_ready: bool = False
    client_session_id: str | None = None
    session_nonce: str | None = None
    client_heartbeat: int = -1
    client_status: ClientStatus = ClientStatus.STARTING
    game_heartbeat: int = 0
    game_status: GameStatus = GameStatus.SOURCE_LOADED
    game_running: bool = True
    source_loaded: bool = True
    save_loaded: bool = False
    native_save_slot: int = -1
    native_save_identity: str | None = None
    consumed_save_identity: str | None = None
    native_save_eligibility: NativeSaveEligibility = NativeSaveEligibility.UNKNOWN
    ap_state_loaded: bool = False
    ap_state_bound: bool = False
    current_level: str | None = None
    current_act: int = 0
    current_task: int = -1
    current_task_node: int = -1
    at_title_menu: bool = True
    loading: bool = False
    in_cutscene: bool = False
    dying_or_dead: bool = False
    mission_restarting: bool = False
    level_transition: bool = False
    in_vehicle: bool = False
    safe_to_apply_permanent_item: bool = False
    safe_to_apply_consumable: bool = False
    safe_to_mutate_mission_state: bool = False
    test_target: bool = False
    last_command_id: int = -1
    last_command_kind: ProtocolCommand | int = ProtocolCommand.NONE
    last_command_result: ProtocolResult = ProtocolResult.NONE
    last_error_code: ProtocolError = ProtocolError.NONE
    last_error_message: str = "none"
    recent_command_receipts: tuple[CommandReceipt, ...] = ()
    diagnostic_schema_version: int | None = 1
    diagnostic_manifest_version: int | None = 1
    diagnostic_activation_generation: int | None = 1
    diagnostic_dropped_count: int = 0
    diagnostic_next_sequence: int = 0
    diagnostic_events: tuple[GoalDiagnosticRecord, ...] = ()
    diagnostic_malformed: bool = False

    @property
    def session_id(self) -> str:
        """Compatibility alias for diagnostic callers from protocol 2."""

        return self.client_session_id or "-"

    @property
    def last_command(self) -> ProtocolCommand:
        if isinstance(self.last_command_kind, ProtocolCommand):
            return self.last_command_kind
        return ProtocolCommand.NONE

    @property
    def last_result(self) -> ProtocolResult:
        return self.last_command_result

    @property
    def message(self) -> str:
        return self.last_error_message


class ReplTransport(Protocol):
    async def send_form(self, form: str, timeout: float = 10.0) -> str: ...

    async def send_form_unacknowledged(
        self, form: str, timeout: float = DIAGNOSTIC_ACK_TIMEOUT_SECONDS
    ) -> None: ...


EventSink = Callable[..., None]
GoalEventSink = Callable[[tuple[GoalDiagnosticRecord, ...], int], int | None]


def goal_string_literal(value: str, *, limit: int = 96) -> str:
    """Encode a bounded printable ASCII string for an nREPL GOAL form."""

    if (
        not value
        or len(value) > limit
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(
            f"GOAL protocol strings must contain 1-{limit} printable characters"
        )
    safe = "".join(character if ord(character) < 127 else "?" for character in value)
    return '"' + safe.replace("\\", "\\\\").replace('"', '\\"') + '"'


def goal_path_literal(value: str) -> str:
    """Encode an absolute shared-state path without the short status-string limit."""

    if not value or len(value) > 500 or any(ord(character) < 32 for character in value):
        raise ValueError(
            "JAK3_AP_STATE must be a non-empty path of at most 500 characters"
        )
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _parse_int(value: str) -> int:
    if not value or not value.lstrip("-").isdigit():
        raise ValueError(value)
    return int(value)


def _parse_command_kind(value: str) -> ProtocolCommand | int:
    """Preserve rejected or future command kinds without losing the snapshot."""

    parsed = _parse_int(value)
    try:
        return ProtocolCommand(parsed)
    except ValueError:
        return parsed


def _parse_bool(value: str) -> bool:
    parsed = _parse_int(value)
    if parsed not in (0, 1):
        raise ValueError(value)
    return bool(parsed)


def _parse_optional(value: str, *, limit: int = 128) -> str | None:
    if value == "-":
        return None
    if (
        not value
        or len(value) > limit
        or any(character.isspace() for character in value)
    ):
        raise ValueError(value)
    return value


_INT_FIELDS = {
    "protocol_version",
    "game_integration_version",
    "bridge_runtime_version",
    "bridge_activation_generation",
    "state_schema_version",
    "slot_data_version",
    "item_table_version",
    "location_table_version",
    "mission_table_version",
    "client_heartbeat",
    "client_status",
    "game_heartbeat",
    "game_status",
    "native_save_slot",
    "native_save_eligibility",
    "current_act",
    "current_task",
    "current_task_node",
    "last_command_id",
    "last_command_kind",
    "last_command_result",
    "last_error_code",
    "recent_command_count",
}
_BOOL_FIELDS = {
    "connection_ready",
    "game_running",
    "source_loaded",
    "save_loaded",
    "ap_state_loaded",
    "ap_state_bound",
    "at_title_menu",
    "loading",
    "in_cutscene",
    "dying_or_dead",
    "mission_restarting",
    "level_transition",
    "in_vehicle",
    "safe_to_apply_permanent_item",
    "safe_to_apply_consumable",
    "safe_to_mutate_mission_state",
    "test_target",
}
_TEXT_FIELDS = {
    "item_table_hash",
    "location_table_hash",
    "mission_table_hash",
    "client_session_id",
    "session_nonce",
    "native_save_identity",
    "consumed_save_identity",
    "current_level",
    "last_error_message",
}
_REQUIRED_FIELDS = _INT_FIELDS | _BOOL_FIELDS | _TEXT_FIELDS


def parse_snapshot_text(text: str) -> BridgeSnapshot | None:
    """Parse one complete forward-safe snapshot; ignore torn/malformed data."""

    lines = text.splitlines()
    if len(lines) < 2:
        return None
    first_key, separator, first_value = lines[0].partition(" ")
    last_key, last_separator, last_value = lines[-1].partition(" ")
    if (
        not separator
        or not last_separator
        or first_key != "snapshot_begin"
        or last_key != "snapshot_end"
    ):
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
        key, line_separator, value = line.partition(" ")
        if not line_separator or not key or key in values:
            return None
        values[key] = value
    if not _REQUIRED_FIELDS <= values.keys():
        return None

    try:
        receipt_count = _parse_int(values["recent_command_count"])
        if not 0 <= receipt_count <= RECENT_RECEIPT_LIMIT:
            return None
        receipts: list[CommandReceipt] = []
        for index in range(receipt_count):
            prefix = f"recent_command_{index}_"
            receipts.append(
                CommandReceipt(
                    command_id=_parse_int(values[prefix + "id"]),
                    command_kind=_parse_command_kind(values[prefix + "kind"]),
                    payload=_parse_int(values[prefix + "payload"]),
                    result=ProtocolResult(_parse_int(values[prefix + "result"])),
                    error_code=ProtocolError(_parse_int(values[prefix + "error"])),
                )
            )
        error_message = values["last_error_message"]
        if len(error_message) > 160 or any(
            ord(character) < 32 for character in error_message
        ):
            return None
        diagnostic_schema: int | None = None
        diagnostic_manifest: int | None = None
        diagnostic_activation: int | None = None
        diagnostic_dropped = 0
        diagnostic_next = 0
        diagnostic_events: tuple[GoalDiagnosticRecord, ...] = ()
        diagnostic_malformed = False
        if any(key.startswith("diagnostic_") for key in values):
            try:
                diagnostic_schema = _parse_int(values["diagnostic_schema_version"])
                diagnostic_manifest = _parse_int(values["diagnostic_manifest_version"])
                diagnostic_activation = _parse_int(
                    values["diagnostic_activation_generation"]
                )
                diagnostic_dropped = _parse_int(values["diagnostic_dropped_count"])
                diagnostic_next = _parse_int(values["diagnostic_next_sequence"])
                diagnostic_count = _parse_int(values["diagnostic_event_count"])
                if (
                    diagnostic_schema != 1
                    or diagnostic_manifest != 1
                    or diagnostic_activation < 1
                    or diagnostic_dropped < 0
                    or diagnostic_next < 0
                    or not 0 <= diagnostic_count <= 64
                ):
                    raise ValueError("invalid diagnostic header")
                parsed_events: list[GoalDiagnosticRecord] = []
                for index in range(diagnostic_count):
                    event_values = values[f"diagnostic_event_{index}"].split()
                    if len(event_values) != 11:
                        raise ValueError("invalid diagnostic record")
                    parsed_events.append(
                        GoalDiagnosticRecord(
                            *(_parse_int(value) for value in event_values)
                        )
                    )
                if any(
                    event.source_sequence < 0
                    or event.source_sequence >= diagnostic_next
                    for event in parsed_events
                ):
                    raise ValueError("invalid diagnostic source sequence")
                if any(
                    current.source_sequence >= following.source_sequence
                    for current, following in zip(
                        parsed_events, parsed_events[1:], strict=False
                    )
                ):
                    raise ValueError("unordered diagnostic records")
                diagnostic_events = tuple(parsed_events)
            except (KeyError, ValueError):
                diagnostic_schema = None
                diagnostic_manifest = None
                diagnostic_activation = None
                diagnostic_dropped = 0
                diagnostic_next = 0
                diagnostic_events = ()
                diagnostic_malformed = True
        snapshot = BridgeSnapshot(
            snapshot_revision=begin_revision,
            protocol_version=_parse_int(values["protocol_version"]),
            game_integration_version=_parse_int(values["game_integration_version"]),
            bridge_runtime_version=_parse_int(values["bridge_runtime_version"]),
            bridge_activation_generation=_parse_int(
                values["bridge_activation_generation"]
            ),
            state_schema_version=_parse_int(values["state_schema_version"]),
            slot_data_version=_parse_int(values["slot_data_version"]),
            item_table_version=_parse_int(values["item_table_version"]),
            location_table_version=_parse_int(values["location_table_version"]),
            mission_table_version=_parse_int(values["mission_table_version"]),
            item_table_hash=values["item_table_hash"],
            location_table_hash=values["location_table_hash"],
            mission_table_hash=values["mission_table_hash"],
            connection_ready=_parse_bool(values["connection_ready"]),
            client_session_id=_parse_optional(values["client_session_id"]),
            session_nonce=_parse_optional(values["session_nonce"]),
            client_heartbeat=_parse_int(values["client_heartbeat"]),
            client_status=ClientStatus(_parse_int(values["client_status"])),
            game_heartbeat=_parse_int(values["game_heartbeat"]),
            game_status=GameStatus(_parse_int(values["game_status"])),
            game_running=_parse_bool(values["game_running"]),
            source_loaded=_parse_bool(values["source_loaded"]),
            save_loaded=_parse_bool(values["save_loaded"]),
            native_save_slot=_parse_int(values["native_save_slot"]),
            native_save_identity=_parse_optional(values["native_save_identity"]),
            consumed_save_identity=_parse_optional(values["consumed_save_identity"]),
            native_save_eligibility=NativeSaveEligibility(
                _parse_int(values["native_save_eligibility"])
            ),
            ap_state_loaded=_parse_bool(values["ap_state_loaded"]),
            ap_state_bound=_parse_bool(values["ap_state_bound"]),
            current_level=_parse_optional(values["current_level"]),
            current_act=_parse_int(values["current_act"]),
            current_task=_parse_int(values["current_task"]),
            current_task_node=_parse_int(values["current_task_node"]),
            at_title_menu=_parse_bool(values["at_title_menu"]),
            loading=_parse_bool(values["loading"]),
            in_cutscene=_parse_bool(values["in_cutscene"]),
            dying_or_dead=_parse_bool(values["dying_or_dead"]),
            mission_restarting=_parse_bool(values["mission_restarting"]),
            level_transition=_parse_bool(values["level_transition"]),
            in_vehicle=_parse_bool(values["in_vehicle"]),
            safe_to_apply_permanent_item=_parse_bool(
                values["safe_to_apply_permanent_item"]
            ),
            safe_to_apply_consumable=_parse_bool(values["safe_to_apply_consumable"]),
            safe_to_mutate_mission_state=_parse_bool(
                values["safe_to_mutate_mission_state"]
            ),
            test_target=_parse_bool(values["test_target"]),
            last_command_id=_parse_int(values["last_command_id"]),
            last_command_kind=_parse_command_kind(values["last_command_kind"]),
            last_command_result=ProtocolResult(
                _parse_int(values["last_command_result"])
            ),
            last_error_code=ProtocolError(_parse_int(values["last_error_code"])),
            last_error_message=error_message,
            recent_command_receipts=tuple(receipts),
            diagnostic_schema_version=diagnostic_schema,
            diagnostic_manifest_version=diagnostic_manifest,
            diagnostic_activation_generation=diagnostic_activation,
            diagnostic_dropped_count=diagnostic_dropped,
            diagnostic_next_sequence=diagnostic_next,
            diagnostic_events=diagnostic_events,
            diagnostic_malformed=diagnostic_malformed,
        )
    except (KeyError, ValueError):
        return None
    if snapshot.client_heartbeat < -1 or snapshot.game_heartbeat < 0:
        return None
    if snapshot.bridge_activation_generation < 1:
        return None
    if snapshot.native_save_slot not in (-1, 0, 1, 2, 3):
        return None
    if snapshot.current_act not in (0, 1, 2, 3):
        return None
    if any(receipt.command_id < 0 for receipt in snapshot.recent_command_receipts):
        return None
    return snapshot


def read_snapshot(path: Path) -> BridgeSnapshot | None:
    try:
        return parse_snapshot_text(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError):
        return None


def read_reported_versions(path: Path) -> tuple[int | None, int | None]:
    """Read primary versions even from a legacy or malformed snapshot."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        return None, None
    found: dict[str, int] = {}
    for line in lines:
        key, separator, value = line.partition(" ")
        if separator:
            try:
                found[key] = _parse_int(value)
            except ValueError:
                pass
    return found.get("protocol_version", found.get("version")), found.get(
        "game_integration_version"
    )


def _wire_optional(value: str | None) -> str:
    return value if value is not None else "-"


def format_snapshot(snapshot: BridgeSnapshot) -> str:
    """Render the GOAL-owned wire format for fakes and contract tests."""

    fields: list[tuple[str, object]] = [
        ("protocol_version", snapshot.protocol_version),
        ("game_integration_version", snapshot.game_integration_version),
        ("bridge_runtime_version", snapshot.bridge_runtime_version),
        ("bridge_activation_generation", snapshot.bridge_activation_generation),
        ("state_schema_version", snapshot.state_schema_version),
        ("slot_data_version", snapshot.slot_data_version),
        ("item_table_version", snapshot.item_table_version),
        ("location_table_version", snapshot.location_table_version),
        ("mission_table_version", snapshot.mission_table_version),
        ("item_table_hash", snapshot.item_table_hash),
        ("location_table_hash", snapshot.location_table_hash),
        ("mission_table_hash", snapshot.mission_table_hash),
        ("connection_ready", int(snapshot.connection_ready)),
        ("client_session_id", _wire_optional(snapshot.client_session_id)),
        ("session_nonce", _wire_optional(snapshot.session_nonce)),
        ("client_heartbeat", snapshot.client_heartbeat),
        ("client_status", int(snapshot.client_status)),
        ("game_heartbeat", snapshot.game_heartbeat),
        ("game_status", int(snapshot.game_status)),
        ("game_running", int(snapshot.game_running)),
        ("source_loaded", int(snapshot.source_loaded)),
        ("save_loaded", int(snapshot.save_loaded)),
        ("native_save_slot", snapshot.native_save_slot),
        ("native_save_identity", _wire_optional(snapshot.native_save_identity)),
        ("consumed_save_identity", _wire_optional(snapshot.consumed_save_identity)),
        ("native_save_eligibility", int(snapshot.native_save_eligibility)),
        ("ap_state_loaded", int(snapshot.ap_state_loaded)),
        ("ap_state_bound", int(snapshot.ap_state_bound)),
        ("current_level", _wire_optional(snapshot.current_level)),
        ("current_act", snapshot.current_act),
        ("current_task", snapshot.current_task),
        ("current_task_node", snapshot.current_task_node),
        ("at_title_menu", int(snapshot.at_title_menu)),
        ("loading", int(snapshot.loading)),
        ("in_cutscene", int(snapshot.in_cutscene)),
        ("dying_or_dead", int(snapshot.dying_or_dead)),
        ("mission_restarting", int(snapshot.mission_restarting)),
        ("level_transition", int(snapshot.level_transition)),
        ("in_vehicle", int(snapshot.in_vehicle)),
        ("safe_to_apply_permanent_item", int(snapshot.safe_to_apply_permanent_item)),
        ("safe_to_apply_consumable", int(snapshot.safe_to_apply_consumable)),
        ("safe_to_mutate_mission_state", int(snapshot.safe_to_mutate_mission_state)),
        ("test_target", int(snapshot.test_target)),
        ("last_command_id", snapshot.last_command_id),
        ("last_command_kind", int(snapshot.last_command_kind)),
        ("last_command_result", int(snapshot.last_command_result)),
        ("last_error_code", int(snapshot.last_error_code)),
        ("last_error_message", snapshot.last_error_message),
        ("recent_command_count", len(snapshot.recent_command_receipts)),
    ]
    for index, receipt in enumerate(snapshot.recent_command_receipts):
        prefix = f"recent_command_{index}_"
        fields.extend(
            (
                (prefix + "id", receipt.command_id),
                (prefix + "kind", int(receipt.command_kind)),
                (prefix + "payload", receipt.payload),
                (prefix + "result", int(receipt.result)),
                (prefix + "error", int(receipt.error_code)),
            )
        )
    if snapshot.diagnostic_schema_version is not None:
        fields.extend(
            (
                ("diagnostic_schema_version", snapshot.diagnostic_schema_version),
                (
                    "diagnostic_manifest_version",
                    snapshot.diagnostic_manifest_version or 1,
                ),
                (
                    "diagnostic_activation_generation",
                    snapshot.diagnostic_activation_generation
                    if snapshot.diagnostic_activation_generation is not None
                    else 1,
                ),
                ("diagnostic_dropped_count", snapshot.diagnostic_dropped_count),
                ("diagnostic_next_sequence", snapshot.diagnostic_next_sequence),
                ("diagnostic_event_count", len(snapshot.diagnostic_events)),
            )
        )
        for index, event in enumerate(snapshot.diagnostic_events):
            fields.append(
                (
                    f"diagnostic_event_{index}",
                    " ".join(
                        str(value)
                        for value in (
                            event.source_sequence,
                            event.game_tick,
                            event.severity,
                            event.event_code,
                            event.correlation_kind,
                            event.correlation_value,
                            event.result,
                            event.error,
                            event.arg0,
                            event.arg1,
                            event.arg2,
                        )
                    ),
                )
            )
    lines = [f"snapshot_begin {snapshot.snapshot_revision}"]
    lines.extend(f"{key} {value}" for key, value in fields)
    lines.extend((f"snapshot_end {snapshot.snapshot_revision}", ""))
    return "\n".join(lines)


_EXPECTED_CONTRACT: tuple[tuple[str, int | str], ...] = (
    ("bridge_runtime_version", BRIDGE_RUNTIME_VERSION),
    ("state_schema_version", STATE_SCHEMA_VERSION),
    ("slot_data_version", SLOT_DATA_VERSION),
    ("item_table_version", ITEM_TABLE_VERSION),
    ("location_table_version", LOCATION_TABLE_VERSION),
    ("mission_table_version", MISSION_TABLE_VERSION),
    ("item_table_hash", ITEM_TABLE_HASH),
    ("location_table_hash", LOCATION_TABLE_HASH),
    ("mission_table_hash", MISSION_TABLE_HASH),
)


def validate_compatibility(snapshot: BridgeSnapshot) -> None:
    if snapshot.protocol_version != PROTOCOL_VERSION:
        raise ProtocolVersionMismatch(snapshot.protocol_version)
    if snapshot.game_integration_version != GAME_INTEGRATION_VERSION:
        raise GameIntegrationVersionMismatch(snapshot.game_integration_version)
    for field, expected in _EXPECTED_CONTRACT:
        found = getattr(snapshot, field)
        if found != expected:
            raise DataContractMismatch(field, expected, found)


class BridgeProtocol:
    """Drive a client session while preserving the game session and receipts."""

    def __init__(
        self,
        repl: ReplTransport,
        state_path: Path,
        session_id: str,
        save_identity_factory: Callable[[], str] | None = None,
        *,
        command_timeout: float = COMMAND_TIMEOUT_SECONDS,
        poll_interval: float = SNAPSHOT_POLL_SECONDS,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        event_sink: EventSink | None = None,
        goal_event_sink: GoalEventSink | None = None,
        goal_event_reset: Callable[[], bool] | None = None,
        goal_source_state: MutableMapping[str, int] | None = None,
        timed_out_commands: MutableMapping[tuple[str, int], ProtocolCommand]
        | None = None,
    ) -> None:
        goal_string_literal(session_id)
        self.repl = repl
        self.state_path = state_path
        self.session_id = session_id
        self.proposed_session_nonce = str(uuid.uuid4())
        self._save_identity_factory = save_identity_factory or (
            lambda: str(uuid.uuid4())
        )
        self.proposed_save_identity: str | None = None
        self.save_identity_authorized = False
        self.command_timeout = command_timeout
        self.poll_interval = poll_interval
        self.sleeper = sleeper
        self._event_sink = event_sink
        self._goal_event_sink = goal_event_sink
        self._goal_event_reset = goal_event_reset
        self._goal_source_state = (
            goal_source_state if goal_source_state is not None else {}
        )
        self._timed_out_commands = (
            timed_out_commands if timed_out_commands is not None else {}
        )
        self._goal_ack_pending: tuple[int, int] | None = None
        self._goal_ack_task: asyncio.Task[None] | None = None
        self.next_sequence = 0
        self.next_command_id = 0
        # Keep the request and its snapshot acknowledgement in one critical
        # section.  nREPL serializes form evaluation, but without this wider
        # lock a heartbeat can replace the command's last-result snapshot
        # before the command waiter observes it.
        self._operation_lock = asyncio.Lock()
        self.session_nonce: str | None = None
        self.last_snapshot: BridgeSnapshot | None = None
        self.ap_state_loaded = False
        self.ap_state_bound = False
        self.ap_state_native_save_slot = -1
        self.ap_state_native_save_identity: str | None = None

    def _emit(self, event_name: str, **fields: object) -> None:
        if self._event_sink is None:
            return
        try:
            self._event_sink(event_name, source_component="protocol", **fields)
        except BaseException:
            pass

    def set_ap_state_status(
        self,
        *,
        loaded: bool,
        bound: bool,
        native_save_slot: int | None = None,
        native_save_identity: str | None = None,
    ) -> None:
        if bound and not loaded:
            raise ValueError("Bound AP state must also be loaded.")
        if loaded:
            if native_save_slot is None or native_save_slot not in range(4):
                raise ValueError(
                    "Loaded AP state requires its native save identity and slot."
                )
            if native_save_identity is None:
                raise ValueError(
                    "Loaded AP state requires its native save identity and slot."
                )
            goal_string_literal(native_save_identity)
        else:
            bound = False
            native_save_slot = -1
            native_save_identity = None
        self.ap_state_loaded = loaded
        self.ap_state_bound = bound
        self.ap_state_native_save_slot = native_save_slot
        self.ap_state_native_save_identity = native_save_identity

    def _ap_state_wire_fields(self) -> str:
        state_flags = int(self.ap_state_loaded) | (int(self.ap_state_bound) << 1)
        return (
            f"{state_flags} {self.ap_state_native_save_slot} "
            f"{goal_string_literal(self.ap_state_native_save_identity or '-')}"
        )

    def set_save_identity_authorized(self, authorized: bool) -> None:
        """Create save identity entropy only after slot authentication."""

        if not authorized:
            if self.save_identity_authorized:
                self._emit(
                    "save.identity.invalidated",
                    message="Native-save identity proposal authorization cleared.",
                )
            self.save_identity_authorized = False
            self.proposed_save_identity = None
            return
        if self.proposed_save_identity is None:
            self.proposed_save_identity = self._create_save_identity()
            self._emit(
                "save.identity.proposed",
                message="Authenticated native-save identity proposal created.",
                context={
                    "native_save_hash": hash_identifier(self.proposed_save_identity)
                },
            )
        self.save_identity_authorized = True
        self._emit(
            "save.identity.authorized",
            message="Native-save identity proposal authorized.",
        )

    def _create_save_identity(self) -> str:
        try:
            proposed = self._save_identity_factory()
        except Exception as exc:
            raise ValueError(
                f"Could not durably authorize proposed native-save identity: {exc}"
            ) from exc
        try:
            parsed = uuid.UUID(proposed)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                "Proposed native-save identity must be a canonical UUID."
            ) from exc
        if str(parsed) != proposed:
            raise ValueError("Proposed native-save identity must be a canonical UUID.")
        goal_string_literal(proposed)
        return proposed

    def _observe_snapshot(self, snapshot: BridgeSnapshot) -> int | None:
        self.last_snapshot = snapshot
        acknowledge = self._observe_goal_diagnostics(snapshot)
        self._observe_command_recovery(snapshot)
        if (
            self.save_identity_authorized
            and self.proposed_save_identity is not None
            and (
                snapshot.consumed_save_identity == self.proposed_save_identity
                or (
                    snapshot.save_loaded
                    and snapshot.native_save_identity == self.proposed_save_identity
                )
            )
        ):
            # The explicit game-owned acknowledgement survives save switches
            # and descriptor invalidation. The live descriptor check remains a
            # compatibility fallback for a snapshot published before the ack.
            # The factory durably records authenticated-slot provenance before
            # this new UUID can be published to the game.
            consumed = self.proposed_save_identity
            self.proposed_save_identity = self._create_save_identity()
            self._emit(
                "save.identity.consumed",
                message="Game acknowledged the proposed native-save identity.",
                context={"native_save_hash": hash_identifier(consumed)},
            )
        return acknowledge

    def _schedule_goal_acknowledgement(
        self, activation_generation: int, acknowledge: int
    ) -> None:
        pending = self._goal_ack_pending
        if pending is not None and pending[0] == activation_generation:
            self._goal_ack_pending = (
                activation_generation,
                max(pending[1], acknowledge),
            )
        else:
            # A source reload resets its sequence space. Never coalesce a high
            # acknowledgement from the old producer into the new generation.
            self._goal_ack_pending = (activation_generation, acknowledge)
        if self._goal_ack_task is None or self._goal_ack_task.done():
            task = asyncio.create_task(
                self._drain_goal_acknowledgements(),
                name="Jak3-GOAL-diagnostic-ack",
            )
            self._goal_ack_task = task
            task.add_done_callback(self._goal_acknowledgement_done)

    def _goal_acknowledgement_done(self, task: asyncio.Task[None]) -> None:
        if self._goal_ack_task is task:
            self._goal_ack_task = None
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except BaseException:
            # The worker is failure-isolated, but retain this last-resort guard
            # so a future transport implementation cannot create an unobserved
            # background-task exception.
            self._emit(
                "diagnostics.capture_gap",
                message="GOAL diagnostic acknowledgement task failed.",
                context={"reason": "goal_ack_task_failure"},
            )

    async def _drain_goal_acknowledgements(self) -> None:
        while self._goal_ack_pending is not None:
            activation_generation, acknowledge = self._goal_ack_pending
            self._goal_ack_pending = None
            form = f"(ap-diagnostic-ack! {activation_generation} {acknowledge})"
            try:
                sender = getattr(self.repl, "send_form_unacknowledged", None)
                operation = (
                    sender(form, timeout=DIAGNOSTIC_ACK_TIMEOUT_SECONDS)
                    if callable(sender)
                    else self.repl.send_form(
                        form, timeout=DIAGNOSTIC_ACK_TIMEOUT_SECONDS
                    )
                )
                await asyncio.wait_for(
                    operation, timeout=DIAGNOSTIC_ACK_TIMEOUT_SECONDS
                )
                self._goal_source_state["ack_failed"] = 0
            except asyncio.CancelledError:
                raise
            except BaseException:
                if self._goal_source_state.get("ack_failed") != 1:
                    self._emit(
                        "diagnostics.capture_gap",
                        message="GOAL diagnostic acknowledgement failed.",
                        context={"reason": "goal_ack_failure"},
                    )
                    self._goal_source_state["ack_failed"] = 1

    def _observe_goal_diagnostics(self, snapshot: BridgeSnapshot) -> int | None:
        state = self._goal_source_state
        channel_state = (
            -1
            if snapshot.diagnostic_malformed
            else 1
            if (
                snapshot.diagnostic_schema_version == 1
                and snapshot.diagnostic_manifest_version == 1
                and snapshot.diagnostic_activation_generation is not None
            )
            else 0
        )
        previous_channel = state.get("channel_state")
        if channel_state != 1:
            if previous_channel != channel_state:
                self._emit(
                    "diagnostics.capture_gap",
                    message=(
                        "Malformed optional GOAL diagnostics were ignored."
                        if channel_state == -1
                        else "The optional GOAL diagnostic channel is unavailable."
                    ),
                    context={
                        "reason": (
                            "malformed_goal_snapshot"
                            if channel_state == -1
                            else "goal_channel_missing"
                        )
                    },
                )
            state["channel_state"] = channel_state
            return None

        assert snapshot.diagnostic_activation_generation is not None
        activation = snapshot.diagnostic_activation_generation
        previous_activation = state.get("activation_generation")
        previous_next = state.get("next_sequence")
        source_changed = (
            (previous_activation is not None and activation != previous_activation)
            or (
                previous_next is not None
                and snapshot.diagnostic_next_sequence < previous_next
            )
            or (previous_channel is not None and previous_channel != 1)
        )
        if source_changed and self._goal_event_reset is not None:
            try:
                reset = self._goal_event_reset()
            except BaseException:
                reset = False
            if not reset:
                if state.get("reset_failed") != 1:
                    self._emit(
                        "diagnostics.capture_gap",
                        message="GOAL diagnostic source reset callback failed.",
                        context={"reason": "goal_source_reset_failure"},
                    )
                    state["reset_failed"] = 1
                return None
            state.clear()
            self._emit(
                "bridge.event_channel.ready",
                message="GOAL diagnostic source generation changed.",
                context={"source": "goal", "status": "generation_changed"},
            )

        state["channel_state"] = 1
        state["activation_generation"] = activation
        state["next_sequence"] = snapshot.diagnostic_next_sequence
        state["reset_failed"] = 0
        if self._goal_event_sink is None:
            return None
        dropped_delta = max(
            0,
            snapshot.diagnostic_dropped_count - state.get("dropped_count", 0),
        )
        try:
            acknowledge = self._goal_event_sink(
                snapshot.diagnostic_events, dropped_delta
            )
        except BaseException:
            if state.get("drain_failed") != 1:
                self._emit(
                    "diagnostics.capture_gap",
                    message="GOAL diagnostic drain callback failed.",
                    context={"reason": "goal_drain_failure"},
                )
                state["drain_failed"] = 1
            return None
        state["drain_failed"] = 0
        state["dropped_count"] = snapshot.diagnostic_dropped_count
        return acknowledge

    def _observe_command_recovery(self, snapshot: BridgeSnapshot) -> None:
        nonce = snapshot.session_nonce
        if nonce is None:
            return
        # A command receipt cannot migrate to a different game session. Drop
        # stale in-memory candidates without affecting command allocation or
        # any game-owned receipt state.
        for key in tuple(self._timed_out_commands):
            if key[0] != nonce:
                del self._timed_out_commands[key]
        for receipt in snapshot.recent_command_receipts:
            key = (nonce, receipt.command_id)
            kind = self._timed_out_commands.get(key)
            if kind is None or int(receipt.command_kind) != int(kind):
                continue
            self._emit(
                "protocol.command.recovered",
                message="A receipt was observed after the command previously timed out.",
                correlation_id=f"command:{receipt.command_id}",
                runtime_state_sequence=snapshot.snapshot_revision,
                context={
                    "command_id": receipt.command_id,
                    "command_kind": int(receipt.command_kind),
                    "result": int(receipt.result),
                    "error_code": int(receipt.error_code),
                },
            )
            del self._timed_out_commands[key]

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
                acknowledge = self._observe_snapshot(snapshot)
                if (
                    acknowledge is not None
                    and snapshot.diagnostic_activation_generation is not None
                ):
                    self._schedule_goal_acknowledgement(
                        snapshot.diagnostic_activation_generation,
                        acknowledge,
                    )
                if check_versions:
                    try:
                        validate_compatibility(snapshot)
                    except ProtocolCompatibilityError as exc:
                        self._emit(
                            "compatibility.contract.reported",
                            message=str(exc),
                            severity="ERROR",
                            context={"status": "rejected"},
                        )
                        raise
                if predicate(snapshot):
                    return snapshot
            if check_versions:
                protocol_version, integration_version = read_reported_versions(
                    self.state_path
                )
                if (
                    protocol_version is not None
                    and protocol_version != PROTOCOL_VERSION
                ):
                    raise ProtocolVersionMismatch(protocol_version)
                if protocol_version == PROTOCOL_VERSION and integration_version not in (
                    None,
                    GAME_INTEGRATION_VERSION,
                ):
                    raise GameIntegrationVersionMismatch(integration_version)
            await self.sleeper(self.poll_interval)
        raise ConnectionError(
            f"OpenGOAL did not publish {description} within {self.command_timeout:g} seconds"
        )

    async def initialize(self, client_status: ClientStatus) -> BridgeSnapshot:
        self._emit(
            "compatibility.contract.reported",
            message="Python compatibility contract prepared.",
            context={"status": "submitted"},
        )
        try:
            self.state_path.unlink(missing_ok=True)
        except OSError as exc:
            raise ConnectionError(
                f"Could not reset temporary bridge state {self.state_path}: {exc}"
            ) from exc
        await self.repl.send_form(
            f"(ap-set-state-path! {goal_path_literal(str(self.state_path))})"
        )
        await self._wait_for(
            lambda snapshot: True, "a complete bridge snapshot", check_versions=True
        )
        form = (
            f"(ap-client-hello! {PROTOCOL_VERSION} {GAME_INTEGRATION_VERSION} "
            f"{STATE_SCHEMA_VERSION} {SLOT_DATA_VERSION} {ITEM_TABLE_VERSION} "
            f"{LOCATION_TABLE_VERSION} {MISSION_TABLE_VERSION} "
            f"{goal_string_literal(ITEM_TABLE_HASH)} {goal_string_literal(LOCATION_TABLE_HASH)} "
            f"{goal_string_literal(MISSION_TABLE_HASH)} {goal_string_literal(self.session_id)} "
            f"{goal_string_literal(self.proposed_session_nonce)} "
            f"{goal_string_literal(self.proposed_save_identity or '-')} {int(client_status)} "
            f"{self._ap_state_wire_fields()})"
        )
        await self.repl.send_form(form)
        snapshot = await self._wait_for(
            lambda current: (
                current.client_session_id == self.session_id
                and current.connection_ready
                and current.session_nonce is not None
                and current.last_command_kind == ProtocolCommand.HELLO
                and current.last_command_result == ProtocolResult.OK
            ),
            "an accepted client hello",
            check_versions=True,
        )
        self.session_nonce = snapshot.session_nonce
        self.next_sequence = max(0, snapshot.client_heartbeat + 1)
        self.next_command_id = (
            max(
                (receipt.command_id for receipt in snapshot.recent_command_receipts),
                default=snapshot.last_command_id,
            )
            + 1
        )
        self._emit(
            "protocol.handshake.accepted",
            message="Protocol 3 handshake accepted.",
            runtime_state_sequence=snapshot.snapshot_revision,
            context={"status": "accepted"},
        )
        return snapshot

    async def ping(
        self, client_status: ClientStatus, *, sequence: int | None = None
    ) -> BridgeSnapshot:
        async with self._operation_lock:
            return await self._ping(client_status, sequence=sequence)

    async def _ping(
        self, client_status: ClientStatus, *, sequence: int | None = None
    ) -> BridgeSnapshot:
        command_sequence = self.next_sequence if sequence is None else sequence
        if command_sequence < 0:
            raise ValueError("Ping sequences must be non-negative")
        if self.session_nonce is None:
            raise ConnectionError("The game session has not completed a hello.")
        before = read_snapshot(self.state_path) or self.last_snapshot
        previous_revision = before.snapshot_revision if before is not None else -1
        await self.repl.send_form(
            f"(ap-ping! {goal_string_literal(self.session_id)} "
            f"{goal_string_literal(self.session_nonce)} {command_sequence} "
            f"{int(client_status)} {self._ap_state_wire_fields()} "
            f"{goal_string_literal(self.proposed_save_identity or '-')})"
        )
        snapshot = await self._wait_for(
            lambda current: (
                current.client_session_id == self.session_id
                and current.session_nonce == self.session_nonce
                and current.connection_ready
                and current.client_heartbeat == command_sequence
                and current.last_command_kind == ProtocolCommand.PING
                and current.last_command_result == ProtocolResult.PONG
                and current.snapshot_revision > previous_revision
            ),
            f"pong {command_sequence + 1}",
            check_versions=True,
        )
        if sequence is None:
            self.next_sequence = command_sequence + 1
        return snapshot

    async def query(self, client_status: ClientStatus) -> BridgeSnapshot:
        async with self._operation_lock:
            return await self._query(client_status)

    async def _query(self, client_status: ClientStatus) -> BridgeSnapshot:
        if self.session_nonce is None:
            raise ConnectionError("The game session has not completed a hello.")
        previous_revision = (
            self.last_snapshot.snapshot_revision if self.last_snapshot else -1
        )
        await self.repl.send_form(
            f"(ap-query-state! {goal_string_literal(self.session_id)} "
            f"{goal_string_literal(self.session_nonce)} {int(client_status)} "
            f"{self._ap_state_wire_fields()})"
        )
        return await self._wait_for(
            lambda current: (
                current.snapshot_revision > previous_revision
                and current.last_command_kind == ProtocolCommand.QUERY_STATE
                and current.last_command_result == ProtocolResult.OK
            ),
            "a query result",
            check_versions=True,
        )

    async def send_command(
        self,
        kind: ProtocolCommand,
        payload: int,
        *,
        command_id: int | None = None,
    ) -> BridgeSnapshot:
        if kind not in (
            ProtocolCommand.SET_TEST_TARGET,
            ProtocolCommand.TEST_ADDITIVE_EFFECT,
        ):
            raise ValueError(
                "Only Milestone 7 harmless test commands use command receipts."
            )
        async with self._operation_lock:
            if self.session_nonce is None:
                raise ConnectionError("The game session has not completed a hello.")
            selected_id = self.next_command_id if command_id is None else command_id
            if (
                type(selected_id) is not int
                or selected_id < 0
                or selected_id > WIRE_INT32_MAX
            ):
                raise ValueError(
                    f"Command IDs must be integers from 0 through {WIRE_INT32_MAX}."
                )
            if (
                type(payload) is not int
                or payload < WIRE_INT32_MIN
                or payload > WIRE_INT32_MAX
            ):
                raise ValueError("Command payloads must be signed 32-bit integers.")

            # Reserve before transmission. If the transport outcome is uncertain,
            # a later automatic command must never reuse this ID with new content.
            self.next_command_id = max(self.next_command_id, selected_id + 1)
            correlation = f"command:{selected_id}"
            self._emit(
                "protocol.command.submitted",
                message="Harmless Protocol 3 command submitted.",
                correlation_id=correlation,
                context={"command_id": selected_id, "command_kind": int(kind)},
            )
            previous_revision = (
                self.last_snapshot.snapshot_revision if self.last_snapshot else -1
            )
            contract = (
                f"{PROTOCOL_VERSION} {GAME_INTEGRATION_VERSION} {STATE_SCHEMA_VERSION} "
                f"{SLOT_DATA_VERSION} {ITEM_TABLE_VERSION} {LOCATION_TABLE_VERSION} "
                f"{MISSION_TABLE_VERSION} {goal_string_literal(ITEM_TABLE_HASH)} "
                f"{goal_string_literal(LOCATION_TABLE_HASH)} "
                f"{goal_string_literal(MISSION_TABLE_HASH)}"
            )
            try:
                await self.repl.send_form(
                    f"(ap-command! {goal_string_literal(self.session_id)} "
                    f"{goal_string_literal(self.session_nonce)} {selected_id} {int(kind)} "
                    f"{payload} {self._ap_state_wire_fields()} {contract})"
                )
                snapshot = await self._wait_for(
                    lambda current: (
                        current.snapshot_revision > previous_revision
                        and current.last_command_id == selected_id
                        and current.last_command_kind == kind
                    ),
                    f"command receipt {selected_id}",
                    check_versions=True,
                )
            except Exception as exc:
                failure_message = str(exc).casefold()
                timed_out = any(
                    marker in failure_message
                    for marker in (
                        "did not publish",
                        "did not acknowledge",
                        "timed out",
                    )
                )
                self._emit(
                    "protocol.command.timed_out"
                    if timed_out
                    else "protocol.command.failed",
                    message=str(exc),
                    correlation_id=correlation,
                    context={"command_id": selected_id, "reason": type(exc).__name__},
                )
                if timed_out:
                    key = (self.session_nonce, selected_id)
                    self._timed_out_commands[key] = kind
                    while len(self._timed_out_commands) > 64:
                        del self._timed_out_commands[
                            next(iter(self._timed_out_commands))
                        ]
                raise
            result_event = {
                ProtocolResult.APPLIED: "protocol.command.applied",
                ProtocolResult.ALREADY_APPLIED: "protocol.command.replayed",
                ProtocolResult.QUEUED: "protocol.command.queued",
                ProtocolResult.UNSAFE_NOW: "protocol.command.unsafe",
                ProtocolResult.FAILED: "protocol.command.failed",
                ProtocolResult.INCOMPATIBLE: "protocol.command.rejected",
                ProtocolResult.INVALID_PAYLOAD: "protocol.command.rejected",
            }.get(snapshot.last_command_result, "protocol.command.accepted")
            self._emit(
                result_event,
                message="Harmless Protocol 3 command receipt observed.",
                correlation_id=correlation,
                runtime_state_sequence=snapshot.snapshot_revision,
                context={
                    "command_id": selected_id,
                    "command_kind": int(kind),
                    "result": int(snapshot.last_command_result),
                    "error_code": int(snapshot.last_error_code),
                },
            )
            return snapshot

    async def set_test_target(
        self, value: bool, *, command_id: int | None = None
    ) -> BridgeSnapshot:
        return await self.send_command(
            ProtocolCommand.SET_TEST_TARGET, int(value), command_id=command_id
        )

    async def disconnect(self) -> None:
        async with self._operation_lock:
            if self.session_nonce is None:
                return
            await self.repl.send_form(
                f"(ap-client-disconnect! {goal_string_literal(self.session_id)} "
                f"{goal_string_literal(self.session_nonce)} {self.next_sequence} "
                f"{int(ClientStatus.STOPPING)})"
            )
            self._emit(
                "bridge.client.disconnected",
                message="Python client disconnect sent to OpenGOAL.",
            )
