"""Atomic, versioned Archipelago state and one-time native-save binding.

The Python client is the sole persistent writer.  OpenGOAL's protocol snapshot
is a separate temporary observation channel and never shares this boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import platformdirs

from .canonical import canonical_json_bytes
from .registry import (
    FIRST_RELEASE_ITEMS,
    FIRST_RELEASE_LOCATIONS,
    ITEM_TABLE_HASH,
    LOCATION_TABLE_HASH,
    MISSION_TABLE_HASH,
)
from .slot_data import SUPPORTED_RESOLVED_OPTIONS_HASH, validate_slot_data
from .versions import (
    DESIGN_VERSION,
    GAME_INTEGRATION_VERSION,
    PROTOCOL_VERSION,
    SLOT_DATA_VERSION,
    STATE_SCHEMA_VERSION,
)


STATE_FORMAT = "jak3-ap-state"
CHECKSUM_ALGORITHM = "sha256"
SAVE_IDENTITY_AUTHORIZATION_FORMAT = "jak3-ap-save-identity-authorization"
SAVE_IDENTITY_AUTHORIZATION_VERSION = 1
GAME_APPLICATION_JOURNAL_VERSION = 1
NATIVE_SAVE_SLOT_COUNT = 4
NETWORK_ID_ABSOLUTE_LIMIT = (1 << 53) - 1
STATE_DIRECTORY_ENV = "JAK3_AP_STATE_DIR"

_ITEM_IDS = frozenset(record.code for record in FIRST_RELEASE_ITEMS)
_LOCATION_IDS = frozenset(record.code for record in FIRST_RELEASE_LOCATIONS)
_PROCESS_LOCK_GUARD = threading.Lock()
_PROCESS_LOCKED_ROOTS: set[Path] = set()
DiagnosticEventSink = Callable[..., None]


def _diagnostic_hash(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:16]


class StateError(RuntimeError):
    """Base error for persistent Jak 3 AP state."""


class StateCompatibilityError(StateError):
    """The state or authenticated slot uses an unsupported data contract."""


class StateBindingError(StateError):
    """A native save or AP slot does not match an existing binding."""


class StateCorruptionError(StateError):
    """State bytes are malformed, incomplete, or fail their checksum."""


class StateEligibilityError(StateError):
    """A missing state cannot be created for this native save."""


class StateWriterLockedError(StateError):
    """Another Jak 3 client owns the persistent writer lease."""


class StaleStateRevisionError(StateError):
    """A commit was attempted from an obsolete in-memory state revision."""


class _StateFileMissing(StateError):
    pass


class NativeSaveEligibility(str, Enum):
    FRESH_UNPROGRESSED = "fresh_unprogressed"
    INELIGIBLE = "ineligible"


class ReceivedItemState(str, Enum):
    RECEIVED = "received"
    PENDING = "pending"
    APPLIED = "applied"


class StateOpenStatus(str, Enum):
    CREATED = "created"
    LOADED = "loaded"
    BOUND = "bound"
    RECOVERED_BACKUP = "recovered_backup"


@dataclass(frozen=True, slots=True)
class NativeSaveDescriptor:
    slot: int
    identity: str
    eligibility: NativeSaveEligibility = NativeSaveEligibility.INELIGIBLE

    def __post_init__(self) -> None:
        _validate_native_save_slot(self.slot)
        try:
            _validate_identity_text("native save identity", self.identity, maximum=256)
        except StateCorruptionError as exc:
            raise StateBindingError(str(exc)) from exc
        if not isinstance(self.eligibility, NativeSaveEligibility):
            raise StateEligibilityError(
                "Native save eligibility must be explicitly attested."
            )


@dataclass(frozen=True, slots=True)
class AuthenticatedSlot:
    seed_identifier: str
    team: int
    slot: int
    slot_name: str
    contract: dict[str, Any]

    def __post_init__(self) -> None:
        try:
            validate_slot_data(self.contract)
            _validate_nonnegative_int("team", self.team)
            _validate_nonnegative_int("slot", self.slot)
            _validate_identity_text("slot name", self.slot_name, maximum=128)
        except StateCompatibilityError:
            raise
        except (StateError, TypeError, ValueError) as exc:
            raise StateCompatibilityError(str(exc)) from exc
        if self.seed_identifier != self.contract["seed_identifier"]:
            raise StateCompatibilityError(
                "Authenticated seed identifier does not match the slot-data contract."
            )

    @classmethod
    def from_connected_packet(
        cls,
        slot_data: Mapping[str, Any],
        *,
        team: int,
        slot: int,
        slot_name: str,
    ) -> "AuthenticatedSlot":
        try:
            contract = json.loads(json.dumps(dict(slot_data)))
        except (TypeError, ValueError) as exc:
            raise StateCompatibilityError(str(exc)) from exc
        if "seed_identifier" not in contract:
            raise StateCompatibilityError(
                "Authenticated slot data is missing `seed_identifier`."
            )
        return cls(
            seed_identifier=contract["seed_identifier"],
            team=team,
            slot=slot,
            slot_name=slot_name,
            contract=contract,
        )


@dataclass(frozen=True, slots=True)
class ReceivedItemJournalEntry:
    index: int
    item_id: int
    location_id: int
    source_player: int
    flags: int
    state: ReceivedItemState


@dataclass(frozen=True, slots=True)
class GameCommandReceipt:
    command_id: str
    command_kind: str
    result: str


@dataclass(frozen=True, slots=True)
class PersistentState:
    state_instance_id: str
    state_revision: int

    state_schema_version: int
    protocol_version: int
    game_integration_version: int
    slot_data_version: int
    item_table_hash: str
    location_table_hash: str
    mission_table_hash: str
    resolved_options_hash: str
    design_version: str

    seed_identifier: str | None
    team: int | None
    slot: int | None
    slot_name: str | None
    native_save_slot: int
    native_save_identity: str

    next_received_item_index: int
    received_item_journal: tuple[ReceivedItemJournalEntry, ...]
    received_item_counts: tuple[tuple[int, int], ...]
    pending_item_application_indices: tuple[int, ...]
    game_application_journal_version: int
    last_observed_game_command_receipt: GameCommandReceipt | None

    checked_location_bits: tuple[int, ...]
    server_confirmed_location_bits: tuple[int, ...]
    pending_location_outbox: tuple[int, ...]

    local_earned_precursor_orbs: int
    local_earned_skull_gems: int

    active_bootstrap_overlay: dict[str, Any] | None
    active_shadow_story_state: dict[str, Any] | None
    pending_traps: tuple[dict[str, Any], ...]

    goal_completed: bool
    goal_status_sent: bool
    last_clean_shutdown: bool

    def __post_init__(self) -> None:
        validate_state(self)

    @classmethod
    def create_unbound(
        cls,
        native_save: NativeSaveDescriptor,
        *,
        state_instance_id: str | None = None,
    ) -> "PersistentState":
        if native_save.eligibility is not NativeSaveEligibility.FRESH_UNPROGRESSED:
            raise StateEligibilityError(
                "Jak 3 AP state can only be created for a verified fresh, "
                "unprogressed native save."
            )
        state = cls(
            state_instance_id=state_instance_id or str(uuid.uuid4()),
            state_revision=0,
            state_schema_version=STATE_SCHEMA_VERSION,
            protocol_version=PROTOCOL_VERSION,
            game_integration_version=GAME_INTEGRATION_VERSION,
            slot_data_version=SLOT_DATA_VERSION,
            item_table_hash=ITEM_TABLE_HASH,
            location_table_hash=LOCATION_TABLE_HASH,
            mission_table_hash=MISSION_TABLE_HASH,
            resolved_options_hash=SUPPORTED_RESOLVED_OPTIONS_HASH,
            design_version=DESIGN_VERSION,
            seed_identifier=None,
            team=None,
            slot=None,
            slot_name=None,
            native_save_slot=native_save.slot,
            native_save_identity=native_save.identity,
            next_received_item_index=0,
            received_item_journal=(),
            received_item_counts=(),
            pending_item_application_indices=(),
            game_application_journal_version=GAME_APPLICATION_JOURNAL_VERSION,
            last_observed_game_command_receipt=None,
            checked_location_bits=(),
            server_confirmed_location_bits=(),
            pending_location_outbox=(),
            local_earned_precursor_orbs=0,
            local_earned_skull_gems=0,
            active_bootstrap_overlay=None,
            active_shadow_story_state=None,
            pending_traps=(),
            goal_completed=False,
            goal_status_sent=False,
            last_clean_shutdown=True,
        )
        validate_state(state, native_save=native_save)
        return state

    @property
    def is_bound(self) -> bool:
        values = (
            self.seed_identifier,
            self.team,
            self.slot,
            self.slot_name,
        )
        if all(value is None for value in values):
            return False
        if all(value is not None for value in values):
            return True
        raise StateCorruptionError("Jak 3 AP state has a partial slot binding.")

    def bind(self, authenticated_slot: AuthenticatedSlot) -> "PersistentState":
        if self.is_bound:
            _validate_authenticated_binding(self, authenticated_slot)
            return self
        state = replace(
            self,
            seed_identifier=authenticated_slot.seed_identifier,
            team=authenticated_slot.team,
            slot=authenticated_slot.slot,
            slot_name=authenticated_slot.slot_name,
        )
        validate_state(state, authenticated_slot=authenticated_slot)
        return state

    def to_payload(self) -> dict[str, Any]:
        receipt = self.last_observed_game_command_receipt
        return {
            "state_instance_id": self.state_instance_id,
            "state_revision": self.state_revision,
            "state_schema_version": self.state_schema_version,
            "protocol_version": self.protocol_version,
            "game_integration_version": self.game_integration_version,
            "slot_data_version": self.slot_data_version,
            "item_table_hash": self.item_table_hash,
            "location_table_hash": self.location_table_hash,
            "mission_table_hash": self.mission_table_hash,
            "resolved_options_hash": self.resolved_options_hash,
            "design_version": self.design_version,
            "seed_identifier": self.seed_identifier,
            "team": self.team,
            "slot": self.slot,
            "slot_name": self.slot_name,
            "native_save_slot": self.native_save_slot,
            "native_save_identity": self.native_save_identity,
            "next_received_item_index": self.next_received_item_index,
            "received_item_journal": [
                {
                    "index": entry.index,
                    "item_id": entry.item_id,
                    "location_id": entry.location_id,
                    "source_player": entry.source_player,
                    "flags": entry.flags,
                    "state": entry.state.value,
                }
                for entry in self.received_item_journal
            ],
            "received_item_counts": {
                str(item_id): count for item_id, count in self.received_item_counts
            },
            "pending_item_application_indices": list(
                self.pending_item_application_indices
            ),
            "game_application_journal_version": self.game_application_journal_version,
            "last_observed_game_command_receipt": (
                None
                if receipt is None
                else {
                    "command_id": receipt.command_id,
                    "command_kind": receipt.command_kind,
                    "result": receipt.result,
                }
            ),
            "checked_location_bits": list(self.checked_location_bits),
            "server_confirmed_location_bits": list(self.server_confirmed_location_bits),
            "pending_location_outbox": list(self.pending_location_outbox),
            "local_earned_precursor_orbs": self.local_earned_precursor_orbs,
            "local_earned_skull_gems": self.local_earned_skull_gems,
            "active_bootstrap_overlay": self.active_bootstrap_overlay,
            "active_shadow_story_state": self.active_shadow_story_state,
            "pending_traps": list(self.pending_traps),
            "goal_completed": self.goal_completed,
            "goal_status_sent": self.goal_status_sent,
            "last_clean_shutdown": self.last_clean_shutdown,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "PersistentState":
        schema_version = payload.get("state_schema_version")
        if not isinstance(schema_version, int) or isinstance(schema_version, bool):
            raise StateCorruptionError("State schema version is not an integer.")
        if schema_version != STATE_SCHEMA_VERSION:
            direction = "newer" if schema_version > STATE_SCHEMA_VERSION else "older"
            raise StateCompatibilityError(
                f"Jak 3 AP state schema {schema_version} is {direction} than supported "
                f"schema {STATE_SCHEMA_VERSION}."
            )
        if set(payload) != PERSISTENT_STATE_KEYS:
            missing = sorted(PERSISTENT_STATE_KEYS - set(payload))
            unknown = sorted(set(payload) - PERSISTENT_STATE_KEYS)
            raise StateCorruptionError(
                f"Invalid Jak 3 AP state keys: missing={missing}, unknown={unknown}."
            )
        try:
            journal_entries = _require_list(
                payload["received_item_journal"], "received-item journal"
            )
            journal = tuple(
                _deserialize_received_item_entry(entry) for entry in journal_entries
            )
            count_mapping = _require_mapping(
                payload["received_item_counts"], "received item counts"
            )
            counts = tuple(
                sorted(
                    (_parse_decimal_id(key), value)
                    for key, value in count_mapping.items()
                )
            )
            raw_receipt = payload["last_observed_game_command_receipt"]
            receipt = None
            if raw_receipt is not None:
                receipt_mapping = _require_mapping(raw_receipt, "game command receipt")
                if set(receipt_mapping) != {"command_id", "command_kind", "result"}:
                    raise StateCorruptionError(
                        "Game command receipt has an incompatible shape."
                    )
                receipt = GameCommandReceipt(
                    command_id=receipt_mapping["command_id"],
                    command_kind=receipt_mapping["command_kind"],
                    result=receipt_mapping["result"],
                )
            state = cls(
                state_instance_id=payload["state_instance_id"],
                state_revision=payload["state_revision"],
                state_schema_version=schema_version,
                protocol_version=payload["protocol_version"],
                game_integration_version=payload["game_integration_version"],
                slot_data_version=payload["slot_data_version"],
                item_table_hash=payload["item_table_hash"],
                location_table_hash=payload["location_table_hash"],
                mission_table_hash=payload["mission_table_hash"],
                resolved_options_hash=payload["resolved_options_hash"],
                design_version=payload["design_version"],
                seed_identifier=payload["seed_identifier"],
                team=payload["team"],
                slot=payload["slot"],
                slot_name=payload["slot_name"],
                native_save_slot=payload["native_save_slot"],
                native_save_identity=payload["native_save_identity"],
                next_received_item_index=payload["next_received_item_index"],
                received_item_journal=journal,
                received_item_counts=counts,
                pending_item_application_indices=tuple(
                    _require_list(
                        payload["pending_item_application_indices"],
                        "pending item application indices",
                    )
                ),
                game_application_journal_version=payload[
                    "game_application_journal_version"
                ],
                last_observed_game_command_receipt=receipt,
                checked_location_bits=tuple(
                    _require_list(payload["checked_location_bits"], "checked locations")
                ),
                server_confirmed_location_bits=tuple(
                    _require_list(
                        payload["server_confirmed_location_bits"],
                        "server-confirmed locations",
                    )
                ),
                pending_location_outbox=tuple(
                    _require_list(
                        payload["pending_location_outbox"], "pending location outbox"
                    )
                ),
                local_earned_precursor_orbs=payload["local_earned_precursor_orbs"],
                local_earned_skull_gems=payload["local_earned_skull_gems"],
                active_bootstrap_overlay=_optional_mapping(
                    payload["active_bootstrap_overlay"], "bootstrap overlay"
                ),
                active_shadow_story_state=_optional_mapping(
                    payload["active_shadow_story_state"], "shadow story state"
                ),
                pending_traps=tuple(
                    dict(_require_mapping(trap, "pending trap"))
                    for trap in _require_list(payload["pending_traps"], "pending traps")
                ),
                goal_completed=payload["goal_completed"],
                goal_status_sent=payload["goal_status_sent"],
                last_clean_shutdown=payload["last_clean_shutdown"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StateCorruptionError(f"Invalid Jak 3 AP state value: {exc}") from exc
        validate_state(state)
        return state


PERSISTENT_STATE_KEYS = frozenset(
    {
        "state_instance_id",
        "state_revision",
        "state_schema_version",
        "protocol_version",
        "game_integration_version",
        "slot_data_version",
        "item_table_hash",
        "location_table_hash",
        "mission_table_hash",
        "resolved_options_hash",
        "design_version",
        "seed_identifier",
        "team",
        "slot",
        "slot_name",
        "native_save_slot",
        "native_save_identity",
        "next_received_item_index",
        "received_item_journal",
        "received_item_counts",
        "pending_item_application_indices",
        "game_application_journal_version",
        "last_observed_game_command_receipt",
        "checked_location_bits",
        "server_confirmed_location_bits",
        "pending_location_outbox",
        "local_earned_precursor_orbs",
        "local_earned_skull_gems",
        "active_bootstrap_overlay",
        "active_shadow_story_state",
        "pending_traps",
        "goal_completed",
        "goal_status_sent",
        "last_clean_shutdown",
    }
)

ENVELOPE_KEYS = frozenset({"format", "checksum_algorithm", "payload_sha256", "payload"})
SAVE_IDENTITY_AUTHORIZATION_KEYS = frozenset(
    {
        "authorization_version",
        "native_save_identity",
        "seed_identifier",
        "team",
        "slot",
        "slot_name",
    }
)


@dataclass(frozen=True, slots=True)
class StatePaths:
    primary: Path
    backup: Path


@dataclass(frozen=True, slots=True)
class StateInspection:
    state: PersistentState
    path: Path


class _StateWriterLease:
    def __init__(
        self, root: Path, event_sink: DiagnosticEventSink | None = None
    ) -> None:
        self.root = root.resolve()
        self.path = self.root / ".writer.lock"
        self._event_sink = event_sink
        self._stream: Any = None
        self._locked = False

    def acquire(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with _PROCESS_LOCK_GUARD:
            if self.root in _PROCESS_LOCKED_ROOTS:
                self._emit("persistence.writer_lock.refused", "process_lock")
                raise StateWriterLockedError(
                    f"Another Jak 3 state writer already owns {self.root}."
                )
            _PROCESS_LOCKED_ROOTS.add(self.root)
        try:
            self._stream = self.path.open("a+b")
            self._stream.seek(0, os.SEEK_END)
            if self._stream.tell() == 0:
                self._stream.write(b"\0")
                self._stream.flush()
                os.fsync(self._stream.fileno())
            self._stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(  # type: ignore[attr-defined]
                    self._stream.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,  # type: ignore[attr-defined]
                )
            self._locked = True
            self._emit("persistence.writer_lock.acquired", "acquired")
        except (OSError, PermissionError) as exc:
            self.release()
            self._emit("persistence.writer_lock.refused", type(exc).__name__)
            raise StateWriterLockedError(
                f"Could not acquire the Jak 3 state writer lock at {self.path}: {exc}"
            ) from exc

    def release(self) -> None:
        was_locked = self._locked
        try:
            if self._locked and self._stream is not None:
                if os.name == "nt":
                    import msvcrt

                    self._stream.seek(0)
                    msvcrt.locking(self._stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(  # type: ignore[attr-defined]
                        self._stream.fileno(),
                        fcntl.LOCK_UN,  # type: ignore[attr-defined]
                    )
        finally:
            self._locked = False
            if self._stream is not None:
                self._stream.close()
                self._stream = None
            with _PROCESS_LOCK_GUARD:
                _PROCESS_LOCKED_ROOTS.discard(self.root)
            if was_locked:
                self._emit("persistence.writer_lock.released", "released")

    def _emit(self, event_name: str, status: str) -> None:
        if self._event_sink is None:
            return
        try:
            self._event_sink(
                event_name,
                message="Persistent writer lock transition.",
                context={
                    "path_hash": _diagnostic_hash(self.path),
                    "status": status,
                },
            )
        except BaseException:
            pass


class StateRepository:
    def __init__(
        self,
        root: Path | None = None,
        *,
        fault_injector: Callable[[str], None] | None = None,
        state_id_factory: Callable[[], str] | None = None,
        event_sink: DiagnosticEventSink | None = None,
    ) -> None:
        self.root = (root or default_state_root()).expanduser().resolve()
        self._fault_injector = fault_injector
        self._state_id_factory = state_id_factory or (lambda: str(uuid.uuid4()))
        self._event_sink = event_sink

    def _emit(self, event_name: str, **fields: object) -> None:
        if self._event_sink is None:
            return
        try:
            self._event_sink(event_name, source_component="persistence", **fields)
        except BaseException:
            pass

    def paths_for(self, native_save_identity: str) -> StatePaths:
        _validate_identity_text(
            "native save identity", native_save_identity, maximum=256
        )
        digest = hashlib.sha256(native_save_identity.encode("utf-8")).hexdigest()
        primary = self.root / f"{digest}.json"
        self._emit(
            "persistence.path.selected",
            message="Persistent state path selected from native-save identity hash.",
            correlation_id=digest[:16],
            context={
                "native_save_hash": digest[:16],
                "path_hash": _diagnostic_hash(primary),
            },
        )
        return StatePaths(primary=primary, backup=primary.with_suffix(".json.bak"))

    def save_identity_authorization_path_for(self, native_save_identity: str) -> Path:
        """Return the separate version-1 authorization record for a save UUID."""

        _validate_uuid("proposed native save identity", native_save_identity)
        digest = hashlib.sha256(native_save_identity.encode("utf-8")).hexdigest()
        return (
            self.root
            / f"save-identity-authorizations-v{SAVE_IDENTITY_AUTHORIZATION_VERSION}"
            / f"{digest}.json"
        )

    def create_authorized_save_identity(
        self, authenticated_slot: AuthenticatedSlot
    ) -> str:
        """Durably bind fresh UUID entropy to an authenticated AP slot."""

        native_save_identity = str(uuid.uuid4())
        self.authorize_save_identity(native_save_identity, authenticated_slot)
        return native_save_identity

    def authorize_save_identity(
        self,
        native_save_identity: str,
        authenticated_slot: AuthenticatedSlot,
    ) -> None:
        """Persist proposal provenance before exposing its UUID to the game."""

        path = self.save_identity_authorization_path_for(native_save_identity)
        payload = _save_identity_authorization_payload(
            native_save_identity, authenticated_slot
        )
        serialized = _serialize_checked_envelope(
            SAVE_IDENTITY_AUTHORIZATION_FORMAT, payload
        )
        if path.exists():
            existing = _load_save_identity_authorization(path)
            _validate_save_identity_authorization(
                existing, native_save_identity, authenticated_slot
            )
            self._emit(
                "save.identity.authorized",
                message="Existing save-identity authorization validated.",
                context={"native_save_hash": _diagnostic_hash(native_save_identity)},
            )
            return
        try:
            _write_new_primary(path, serialized)
            self._emit(
                "save.identity.authorized",
                message="Save-identity authorization persisted.",
                context={
                    "native_save_hash": _diagnostic_hash(native_save_identity),
                    "seed_hash": _diagnostic_hash(authenticated_slot.seed_identifier),
                    "slot_hash": _diagnostic_hash(authenticated_slot.slot_name),
                },
            )
        except OSError as exc:
            self._emit(
                "persistence.commit.failed",
                message="Save-identity authorization persistence failed.",
                context={
                    "category": "save_identity_authorization",
                    "reason": type(exc).__name__,
                },
            )
            raise StateCorruptionError(
                f"Could not persist native-save identity authorization: {exc}"
            ) from exc

    def open_live(
        self,
        native_save: NativeSaveDescriptor,
        authenticated_slot: AuthenticatedSlot,
    ) -> "StateSession":
        """Open game-observed state with first-binding provenance enforced."""

        return self._open(
            native_save,
            authenticated_slot,
            require_save_identity_authorization=True,
        )

    def inspect(
        self,
        native_save: NativeSaveDescriptor,
        authenticated_slot: AuthenticatedSlot | None = None,
    ) -> StateInspection:
        paths = self.paths_for(native_save.identity)
        state = _load_state_file(paths.primary)
        validate_state(
            state,
            native_save=native_save,
            authenticated_slot=authenticated_slot,
        )
        return StateInspection(state=state, path=paths.primary)

    def open(
        self,
        native_save: NativeSaveDescriptor,
        authenticated_slot: AuthenticatedSlot | None = None,
    ) -> "StateSession":
        return self._open(
            native_save,
            authenticated_slot,
            require_save_identity_authorization=False,
        )

    def _open(
        self,
        native_save: NativeSaveDescriptor,
        authenticated_slot: AuthenticatedSlot | None,
        *,
        require_save_identity_authorization: bool,
    ) -> "StateSession":
        lease = _StateWriterLease(self.root, self._emit)
        try:
            lease.acquire()
        except StateWriterLockedError as exc:
            self._emit(
                "persistence.concurrent_writer.rejected",
                message="Persistent writer lease was refused.",
                context={"reason": type(exc).__name__},
            )
            raise
        try:
            paths = self.paths_for(native_save.identity)
            if require_save_identity_authorization and authenticated_slot is not None:
                self._preflight_save_identity_authorization(
                    paths, native_save.identity, authenticated_slot
                )
            state, status = self._load_or_create(paths, native_save, authenticated_slot)
            changed = False
            commit_categories: list[str] = []
            binding_performed = False
            if authenticated_slot is not None and not state.is_bound:
                if require_save_identity_authorization:
                    self._require_save_identity_authorization(
                        native_save.identity, authenticated_slot
                    )
                state = state.bind(authenticated_slot)
                binding_performed = True
                self._emit(
                    "persistence.state.bound",
                    message="Persistent state bound to authenticated slot.",
                    persistent_state_revision=state.state_revision,
                    context={
                        "seed_hash": _diagnostic_hash(
                            authenticated_slot.seed_identifier
                        ),
                        "slot_hash": _diagnostic_hash(authenticated_slot.slot_name),
                    },
                )
                if status is not StateOpenStatus.RECOVERED_BACKUP:
                    status = StateOpenStatus.BOUND
                changed = True
                commit_categories.append("binding")
            validate_state(
                state,
                native_save=native_save,
                authenticated_slot=authenticated_slot,
            )
            if state.last_clean_shutdown:
                state = replace(state, last_clean_shutdown=False)
                changed = True
                commit_categories.append("session_open")
                self._emit(
                    "persistence.shutdown.clean",
                    message="Prior persistent session closed cleanly.",
                    persistent_state_revision=state.state_revision,
                )
            elif status is not StateOpenStatus.CREATED:
                self._emit(
                    "persistence.shutdown.unclean",
                    message="Persistent state indicates a prior unclean shutdown.",
                    persistent_state_revision=state.state_revision,
                )
            if changed:
                state = self._commit(
                    paths,
                    state,
                    expected_revision=state.state_revision,
                    category="+".join(commit_categories) or "session_open",
                )
            self._quarantine_orphan_temps(paths)
            return StateSession(
                repository=self,
                paths=paths,
                native_save=native_save,
                authenticated_slot=authenticated_slot,
                lease=lease,
                state=state,
                status=status,
                binding_performed=binding_performed,
            )
        except BaseException as exc:
            rejection = (
                "persistence.compatibility.rejected"
                if isinstance(exc, StateCompatibilityError)
                else "persistence.binding.rejected"
                if isinstance(exc, StateBindingError)
                else "persistence.eligibility.rejected"
                if isinstance(exc, StateEligibilityError)
                else "persistence.concurrent_writer.rejected"
                if isinstance(exc, StateWriterLockedError)
                else "persistence.corruption.detected"
                if isinstance(exc, StateCorruptionError)
                else None
            )
            if rejection is not None:
                self._emit(
                    rejection,
                    message="Persistent state open was rejected.",
                    context={"reason": type(exc).__name__},
                )
            lease.release()
            raise

    def _require_save_identity_authorization(
        self,
        native_save_identity: str,
        authenticated_slot: AuthenticatedSlot,
    ) -> None:
        path = self.save_identity_authorization_path_for(native_save_identity)
        authorization = _load_save_identity_authorization(path)
        _validate_save_identity_authorization(
            authorization, native_save_identity, authenticated_slot
        )

    def _preflight_save_identity_authorization(
        self,
        paths: StatePaths,
        native_save_identity: str,
        authenticated_slot: AuthenticatedSlot,
    ) -> None:
        """Check first-binding provenance before recovery can change disk state."""

        try:
            state = _load_state_file(paths.primary)
        except _StateFileMissing:
            try:
                state = _load_state_file(paths.backup)
            except _StateFileMissing:
                self._require_save_identity_authorization(
                    native_save_identity, authenticated_slot
                )
                return
            except (StateCompatibilityError, StateCorruptionError):
                # Preserve the normal backup diagnostics/quarantine path.
                return
        except StateCompatibilityError:
            # An incompatible primary is never recovered from a backup.
            return
        except StateCorruptionError:
            try:
                state = _load_state_file(paths.backup)
            except (
                _StateFileMissing,
                StateCompatibilityError,
                StateCorruptionError,
            ):
                # Preserve the normal primary/backup recovery diagnostics.
                return
        if not state.is_bound:
            self._require_save_identity_authorization(
                native_save_identity, authenticated_slot
            )

    def _load_or_create(
        self,
        paths: StatePaths,
        native_save: NativeSaveDescriptor,
        authenticated_slot: AuthenticatedSlot | None,
    ) -> tuple[PersistentState, StateOpenStatus]:
        try:
            state = _load_state_file(paths.primary)
        except _StateFileMissing:
            if paths.backup.exists():
                try:
                    state = _load_state_file(paths.backup)
                    validate_state(
                        state,
                        native_save=native_save,
                        authenticated_slot=authenticated_slot,
                    )
                except (StateCompatibilityError, StateBindingError):
                    raise
                except StateCorruptionError as backup_error:
                    self._quarantine(paths.backup, "corrupt")
                    raise StateCorruptionError(
                        f"The primary Jak 3 AP state is missing and its backup "
                        f"is corrupt: {backup_error}."
                    ) from backup_error
                self._restore_backup(paths)
                self._emit(
                    "persistence.state.loaded",
                    message="Persistent state loaded from backup.",
                    persistent_state_revision=state.state_revision,
                    context={"status": "recovered_backup"},
                )
                return state, StateOpenStatus.RECOVERED_BACKUP
            if self._quarantine_candidates(paths):
                raise StateCorruptionError(
                    "Jak 3 AP state is quarantined or has an interrupted write; "
                    "refusing to create a replacement."
                )
            state = PersistentState.create_unbound(
                native_save, state_instance_id=self._state_id_factory()
            )
            _write_new_primary(paths.primary, serialize_state(state))
            self._emit(
                "persistence.state.created",
                message="New unbound persistent state created.",
                persistent_state_revision=state.state_revision,
                context={"state_id_hash": _diagnostic_hash(state.state_instance_id)},
            )
            return state, StateOpenStatus.CREATED
        except StateCompatibilityError:
            raise
        except StateCorruptionError as primary_error:
            try:
                state = _load_state_file(paths.backup)
                validate_state(
                    state,
                    native_save=native_save,
                    authenticated_slot=authenticated_slot,
                )
            except _StateFileMissing:
                self._quarantine(paths.primary, "corrupt")
                raise StateCorruptionError(
                    f"{primary_error} No valid backup is available."
                ) from primary_error
            except (StateCompatibilityError, StateBindingError):
                raise
            except StateCorruptionError as backup_error:
                self._quarantine(paths.primary, "corrupt")
                self._quarantine(paths.backup, "corrupt")
                raise StateCorruptionError(
                    f"Primary and backup Jak 3 AP state are corrupt: "
                    f"primary={primary_error}; backup={backup_error}."
                ) from backup_error
            self._emit(
                "persistence.corruption.detected",
                message="Primary persistent state corruption was detected.",
                context={"reason": "primary_corrupt", "status": "recoverable"},
            )
            self._quarantine(paths.primary, "corrupt")
            self._restore_backup(paths)
            self._emit(
                "persistence.state.loaded",
                message="Persistent state recovered after primary corruption.",
                persistent_state_revision=state.state_revision,
                context={"status": "recovered_backup"},
            )
            return state, StateOpenStatus.RECOVERED_BACKUP

        validate_state(
            state,
            native_save=native_save,
            authenticated_slot=authenticated_slot,
        )
        self._emit(
            "persistence.state.loaded",
            message="Persistent state loaded.",
            persistent_state_revision=state.state_revision,
            context={"status": "loaded"},
        )
        return state, StateOpenStatus.LOADED

    def _commit(
        self,
        paths: StatePaths,
        state: PersistentState,
        *,
        expected_revision: int,
        category: str = "state_update",
    ) -> PersistentState:
        self._emit(
            "persistence.commit.attempted",
            message="Persistent state commit attempted.",
            persistent_state_revision=expected_revision,
            context={
                "category": category,
                "revision": expected_revision,
                "old_revision": expected_revision,
                "new_revision": expected_revision + 1,
            },
        )
        try:
            committed = self._commit_impl(
                paths, state, expected_revision=expected_revision
            )
        except BaseException as exc:
            if isinstance(exc, StaleStateRevisionError):
                self._emit(
                    "persistence.revision.stale",
                    message="Persistent state revision was stale.",
                    persistent_state_revision=expected_revision,
                    context={
                        "revision": expected_revision,
                        "old_revision": expected_revision,
                        "new_revision": expected_revision + 1,
                        "reason": type(exc).__name__,
                    },
                )
            self._emit(
                "persistence.commit.failed",
                message="Persistent state commit failed.",
                persistent_state_revision=expected_revision,
                context={
                    "category": category,
                    "old_revision": expected_revision,
                    "new_revision": expected_revision + 1,
                    "reason": type(exc).__name__,
                },
            )
            raise
        self._emit(
            "persistence.commit.succeeded",
            message="Persistent state commit succeeded.",
            persistent_state_revision=committed.state_revision,
            context={
                "category": category,
                "revision": committed.state_revision,
                "old_revision": expected_revision,
                "new_revision": committed.state_revision,
            },
        )
        return committed

    def _commit_impl(
        self,
        paths: StatePaths,
        state: PersistentState,
        *,
        expected_revision: int,
    ) -> PersistentState:
        if state.state_revision != expected_revision:
            raise StaleStateRevisionError(
                "The proposed Jak 3 AP state does not match the expected revision."
            )
        try:
            previous = paths.primary.read_bytes()
        except FileNotFoundError as exc:
            raise StaleStateRevisionError(
                "The persistent Jak 3 AP state disappeared before commit."
            ) from exc
        except OSError as exc:
            raise StateCorruptionError(
                f"Could not read Jak 3 AP state before commit: {exc}"
            ) from exc
        current = deserialize_state(previous)
        if current.state_instance_id != state.state_instance_id:
            raise StaleStateRevisionError(
                "The persistent Jak 3 AP state instance changed on disk."
            )
        if current.state_revision != expected_revision:
            raise StaleStateRevisionError(
                f"Jak 3 AP state revision changed from {expected_revision} "
                f"to {current.state_revision}."
            )
        committed = replace(state, state_revision=expected_revision + 1)
        validate_state(committed)
        self._write_state(
            paths,
            committed,
            previous=previous,
            previous_revision=current.state_revision,
        )
        return committed

    def _write_state(
        self,
        paths: StatePaths,
        state: PersistentState,
        *,
        previous: bytes,
        previous_revision: int,
    ) -> None:
        payload = serialize_state(state)
        temporary = _write_temporary(paths.primary, payload)
        replaced = False
        try:
            self._fault("after_temp_sync")
            _atomic_replace_bytes(paths.backup, previous)
            self._emit(
                "persistence.backup.refreshed",
                message="Persistent state backup refreshed.",
                persistent_state_revision=previous_revision,
                context={
                    "path_hash": _diagnostic_hash(paths.backup),
                    "revision": previous_revision,
                },
            )
            self._fault("after_backup_replace")
            self._fault("before_primary_replace")
            os.replace(temporary, paths.primary)
            replaced = True
            _sync_directory(paths.primary.parent)
            self._fault("after_primary_replace")
        finally:
            if replaced:
                temporary.unlink(missing_ok=True)

    def _restore_backup(self, paths: StatePaths) -> None:
        backup_bytes = paths.backup.read_bytes()
        _write_new_primary(paths.primary, backup_bytes)
        self._emit(
            "persistence.backup.restored",
            message="Persistent state backup restored.",
            context={
                "path_hash": _diagnostic_hash(paths.primary),
                "status": "restored",
            },
        )

    def _quarantine(self, path: Path, reason: str) -> Path | None:
        if not path.exists():
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = path.with_name(
            f"{path.name}.{reason}.{timestamp}.{uuid.uuid4().hex[:8]}"
        )
        os.replace(path, target)
        _sync_directory(path.parent)
        self._emit(
            "persistence.quarantine.performed",
            message="Unsafe persistence artifact quarantined.",
            context={
                "path_hash": _diagnostic_hash(path),
                "reason": reason,
            },
        )
        return target

    def _quarantine_candidates(self, paths: StatePaths) -> tuple[Path, ...]:
        patterns = (
            f"{paths.primary.name}.corrupt.*",
            f"{paths.backup.name}.corrupt.*",
            f".{paths.primary.name}.*.tmp",
            f".{paths.primary.name}.*.tmp.interrupted.*",
        )
        return tuple(path for pattern in patterns for path in self.root.glob(pattern))

    def _quarantine_orphan_temps(self, paths: StatePaths) -> None:
        for path in self.root.glob(f".{paths.primary.name}.*.tmp"):
            self._quarantine(path, "interrupted")

    def _fault(self, stage: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(stage)


class StateSession:
    def __init__(
        self,
        *,
        repository: StateRepository,
        paths: StatePaths,
        native_save: NativeSaveDescriptor,
        authenticated_slot: AuthenticatedSlot | None,
        lease: _StateWriterLease,
        state: PersistentState,
        status: StateOpenStatus,
        binding_performed: bool,
    ) -> None:
        self.repository = repository
        self.paths = paths
        self.native_save = native_save
        self.authenticated_slot = authenticated_slot
        self._lease = lease
        self.state = state
        self.status = status
        self.binding_performed = binding_performed
        self._closed = False

    def commit(
        self, state: PersistentState, *, category: str = "state_update"
    ) -> PersistentState:
        self._require_open()
        if state.state_instance_id != self.state.state_instance_id:
            raise StaleStateRevisionError(
                "Cannot replace the persistent state instance."
            )
        if _binding_tuple(state) != _binding_tuple(self.state):
            raise StateBindingError(
                "Slot binding may only change through the one-time bind operation."
            )
        validate_state(
            state,
            native_save=self.native_save,
            authenticated_slot=self.authenticated_slot,
        )
        self.state = self.repository._commit(
            self.paths,
            state,
            expected_revision=self.state.state_revision,
            category=category,
        )
        return self.state

    def bind(self, authenticated_slot: AuthenticatedSlot) -> PersistentState:
        self._require_open()
        try:
            bound = self.state.bind(authenticated_slot)
        except StateBindingError as exc:
            self.repository._emit(
                "persistence.binding.rejected",
                message="Open persistent state binding was rejected.",
                persistent_state_revision=self.state.state_revision,
                context={"reason": type(exc).__name__},
            )
            raise
        if bound == self.state:
            self.authenticated_slot = authenticated_slot
            return self.state
        validate_state(
            bound,
            native_save=self.native_save,
            authenticated_slot=authenticated_slot,
        )
        self.state = self.repository._commit(
            self.paths,
            bound,
            expected_revision=self.state.state_revision,
            category="binding",
        )
        self.authenticated_slot = authenticated_slot
        self.binding_performed = True
        self.repository._emit(
            "persistence.state.bound",
            message="Open persistent session bound to authenticated slot.",
            persistent_state_revision=self.state.state_revision,
            context={
                "seed_hash": _diagnostic_hash(authenticated_slot.seed_identifier),
                "slot_hash": _diagnostic_hash(authenticated_slot.slot_name),
            },
        )
        return self.state

    def switch(
        self,
        native_save: NativeSaveDescriptor,
        authenticated_slot: AuthenticatedSlot | None = None,
    ) -> "StateSession":
        repository = self.repository
        self.close(clean=True)
        switched = repository.open(native_save, authenticated_slot)
        repository._emit(
            "persistence.state.switched",
            message="Persistent state session switched native-save identity.",
            persistent_state_revision=switched.state.state_revision,
            context={"native_save_hash": _diagnostic_hash(native_save.identity)},
        )
        return switched

    def close(self, *, clean: bool = True) -> None:
        if self._closed:
            return
        clean_commit = False
        try:
            if clean and not self.state.last_clean_shutdown:
                self.commit(
                    replace(self.state, last_clean_shutdown=True),
                    category="clean_shutdown",
                )
            clean_commit = clean
        finally:
            self._closed = True
            self._lease.release()
            self.repository._emit(
                "persistence.shutdown.clean"
                if clean_commit
                else "persistence.shutdown.unclean",
                message="Persistent state session closed.",
                persistent_state_revision=self.state.state_revision,
                context={"status": "clean" if clean_commit else "unclean"},
            )
            self.repository._emit(
                "persistence.state.closed",
                message="Persistent state writer session closed.",
                persistent_state_revision=self.state.state_revision,
            )

    def _require_open(self) -> None:
        if self._closed:
            raise StateError("The Jak 3 AP state session is closed.")

    def __enter__(self) -> "StateSession":
        self._require_open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close(clean=exc_type is None)


def default_state_root() -> Path:
    override = os.environ.get(STATE_DIRECTORY_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return (
        Path(platformdirs.user_data_path("Archipelago", appauthor=False))
        / "Jak3"
        / "state-v1"
    ).resolve()


def serialize_state(state: PersistentState) -> bytes:
    validate_state(state)
    return _serialize_checked_envelope(STATE_FORMAT, state.to_payload())


def _serialize_checked_envelope(
    envelope_format: str, payload: Mapping[str, Any]
) -> bytes:
    payload_sha256 = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    envelope = {
        "format": envelope_format,
        "checksum_algorithm": CHECKSUM_ALGORITHM,
        "payload_sha256": payload_sha256,
        "payload": payload,
    }
    return canonical_json_bytes(envelope)


def deserialize_state(data: bytes) -> PersistentState:
    if not data:
        raise StateCorruptionError("Jak 3 AP state file is empty.")
    try:
        envelope = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateCorruptionError(
            f"Jak 3 AP state is not valid UTF-8 JSON: {exc}"
        ) from exc
    if not isinstance(envelope, dict):
        raise StateCorruptionError("Jak 3 AP state envelope has an incompatible shape.")
    if "format" in envelope and envelope["format"] != STATE_FORMAT:
        raise StateCompatibilityError(
            f"Unsupported Jak 3 AP state format: {envelope['format']!r}."
        )
    if (
        "checksum_algorithm" in envelope
        and envelope["checksum_algorithm"] != CHECKSUM_ALGORITHM
    ):
        raise StateCompatibilityError(
            "Unsupported Jak 3 AP state checksum algorithm: "
            f"{envelope['checksum_algorithm']!r}."
        )
    if set(envelope) != ENVELOPE_KEYS:
        raise StateCorruptionError("Jak 3 AP state envelope has an incompatible shape.")
    payload = _require_mapping(envelope["payload"], "state payload")
    checksum = envelope["payload_sha256"]
    if not isinstance(checksum, str) or len(checksum) != 64:
        raise StateCorruptionError("Jak 3 AP state checksum has an invalid shape.")
    try:
        canonical_payload = canonical_json_bytes(payload)
    except (TypeError, ValueError) as exc:
        raise StateCorruptionError(
            f"Jak 3 AP state payload is not canonical JSON data: {exc}"
        ) from exc
    actual_checksum = hashlib.sha256(canonical_payload).hexdigest()
    if checksum != actual_checksum:
        raise StateCorruptionError(
            "Jak 3 AP state checksum does not match its payload."
        )
    return PersistentState.from_payload(payload)


def validate_state(
    state: PersistentState,
    *,
    native_save: NativeSaveDescriptor | None = None,
    authenticated_slot: AuthenticatedSlot | None = None,
) -> None:
    expected_contract = {
        "state_schema_version": STATE_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "game_integration_version": GAME_INTEGRATION_VERSION,
        "slot_data_version": SLOT_DATA_VERSION,
        "item_table_hash": ITEM_TABLE_HASH,
        "location_table_hash": LOCATION_TABLE_HASH,
        "mission_table_hash": MISSION_TABLE_HASH,
        "resolved_options_hash": SUPPORTED_RESOLVED_OPTIONS_HASH,
        "design_version": DESIGN_VERSION,
    }
    for field_name, expected in expected_contract.items():
        found = getattr(state, field_name)
        if type(found) is not type(expected):
            raise StateCorruptionError(
                f"Jak 3 AP state `{field_name}` must be a {type(expected).__name__}."
            )
        if found != expected:
            raise StateCompatibilityError(
                f"Incompatible Jak 3 AP state `{field_name}`: "
                f"expected {expected!r}, found {found!r}."
            )

    _validate_uuid("state instance ID", state.state_instance_id)
    _validate_nonnegative_int("state revision", state.state_revision)
    _validate_native_save_slot(state.native_save_slot, error_type=StateCorruptionError)
    _validate_identity_text(
        "native save identity", state.native_save_identity, maximum=256
    )
    if native_save is not None:
        if state.native_save_identity != native_save.identity:
            raise StateBindingError(
                "The loaded native save identity does not match this Jak 3 AP state."
            )
        if state.native_save_slot != native_save.slot:
            raise StateBindingError(
                f"This bound native save belongs to slot {state.native_save_slot}, "
                f"not slot {native_save.slot}. Save-slot copies are unsupported."
            )

    if state.is_bound:
        _validate_identity_text(
            "seed identifier",
            state.seed_identifier,
            maximum=128,  # type: ignore[arg-type]
        )
        _validate_nonnegative_int("team", state.team)  # type: ignore[arg-type]
        _validate_nonnegative_int("slot", state.slot)  # type: ignore[arg-type]
        _validate_identity_text(
            "slot name",
            state.slot_name,
            maximum=128,  # type: ignore[arg-type]
        )
    if authenticated_slot is not None and state.is_bound:
        _validate_authenticated_binding(state, authenticated_slot)

    _validate_nonnegative_int(
        "next received item index", state.next_received_item_index
    )
    if type(state.received_item_journal) is not tuple:
        raise StateCorruptionError("Jak 3 AP received-item journal must be a tuple.")
    if state.next_received_item_index != len(state.received_item_journal):
        raise StateCorruptionError(
            "Next received-item index does not match the journal length."
        )
    computed_counts: dict[int, int] = {}
    for expected_index, entry in enumerate(state.received_item_journal):
        if type(entry) is not ReceivedItemJournalEntry:
            raise StateCorruptionError(
                "Jak 3 AP received-item journal must contain journal records."
            )
        _validate_nonnegative_int("received item journal index", entry.index)
        if entry.index != expected_index:
            raise StateCorruptionError(
                "Received-item journal indices are not contiguous."
            )
        if not isinstance(entry.state, ReceivedItemState):
            raise StateCorruptionError(
                "Received-item journal state must be received, pending, or applied."
            )
        _validate_nonnegative_int("received item ID", entry.item_id)
        if entry.item_id not in _ITEM_IDS:
            raise StateCompatibilityError(
                f"Received-item journal contains unknown item ID {entry.item_id}."
            )
        _validate_network_location_id(entry.location_id)
        _validate_nonnegative_int("received item source player", entry.source_player)
        _validate_nonnegative_int("received item flags", entry.flags)
        computed_counts[entry.item_id] = computed_counts.get(entry.item_id, 0) + 1
    expected_counts = tuple(sorted(computed_counts.items()))
    if type(state.received_item_counts) is not tuple:
        raise StateCorruptionError("Jak 3 AP received-item counts must be a tuple.")
    for count_record in state.received_item_counts:
        if type(count_record) is not tuple or len(count_record) != 2:
            raise StateCorruptionError(
                "Jak 3 AP received-item counts must contain item/count pairs."
            )
        item_id, count = count_record
        _validate_nonnegative_int("received item count ID", item_id)
        if item_id not in _ITEM_IDS:
            raise StateCompatibilityError(
                f"Received-item counts contain unknown item ID {item_id}."
            )
        _validate_nonnegative_int("received item count", count)
    if state.received_item_counts != expected_counts:
        raise StateCorruptionError(
            "Received-item counts do not match the per-index journal."
        )
    _validate_sorted_unique_ints(
        "pending item application indices",
        state.pending_item_application_indices,
        allowed=frozenset(range(state.next_received_item_index)),
    )
    pending_from_journal = tuple(
        entry.index
        for entry in state.received_item_journal
        if entry.state is ReceivedItemState.PENDING
    )
    if state.pending_item_application_indices != pending_from_journal:
        raise StateCorruptionError(
            "Pending item indices do not match journal application states."
        )
    if type(state.game_application_journal_version) is not int:
        raise StateCorruptionError(
            "Jak 3 AP game-application journal version must be an int."
        )
    if state.game_application_journal_version != GAME_APPLICATION_JOURNAL_VERSION:
        raise StateCompatibilityError(
            "Unsupported game-application journal version "
            f"{state.game_application_journal_version}."
        )
    if state.last_observed_game_command_receipt is not None:
        receipt = state.last_observed_game_command_receipt
        if type(receipt) is not GameCommandReceipt:
            raise StateCorruptionError(
                "Jak 3 AP game command receipt must be a receipt record."
            )
        _validate_identity_text("command ID", receipt.command_id, maximum=128)
        _validate_identity_text("command kind", receipt.command_kind, maximum=64)
        _validate_identity_text("command result", receipt.result, maximum=64)

    _validate_sorted_unique_ints(
        "checked locations", state.checked_location_bits, allowed=_LOCATION_IDS
    )
    _validate_sorted_unique_ints(
        "server-confirmed locations",
        state.server_confirmed_location_bits,
        allowed=_LOCATION_IDS,
    )
    _validate_sorted_unique_ints(
        "pending location outbox",
        state.pending_location_outbox,
        allowed=_LOCATION_IDS,
    )
    checked = set(state.checked_location_bits)
    confirmed = set(state.server_confirmed_location_bits)
    outbox = set(state.pending_location_outbox)
    if not confirmed <= checked:
        raise StateCorruptionError(
            "Server-confirmed locations are not a subset of checked locations."
        )
    if not outbox <= checked:
        raise StateCorruptionError(
            "Pending outbox locations are not a subset of checked locations."
        )
    if confirmed & outbox:
        raise StateCorruptionError(
            "Server-confirmed locations cannot remain in the pending outbox."
        )

    _validate_nonnegative_int(
        "local earned Precursor Orbs", state.local_earned_precursor_orbs
    )
    _validate_nonnegative_int("local earned Skull Gems", state.local_earned_skull_gems)
    _validate_optional_json_mapping(
        "active bootstrap overlay", state.active_bootstrap_overlay
    )
    _validate_optional_json_mapping(
        "active shadow story state", state.active_shadow_story_state
    )
    if not isinstance(state.pending_traps, tuple):
        raise StateCorruptionError("Jak 3 AP pending traps must be a tuple.")
    for trap in state.pending_traps:
        _validate_json_mapping("pending trap", trap)
    _validate_bool("goal completed", state.goal_completed)
    _validate_bool("goal status sent", state.goal_status_sent)
    _validate_bool("last clean shutdown", state.last_clean_shutdown)
    if state.goal_status_sent and not state.goal_completed:
        raise StateCorruptionError(
            "Goal status cannot be sent before local goal completion."
        )


def _validate_authenticated_binding(
    state: PersistentState, authenticated_slot: AuthenticatedSlot
) -> None:
    expected = {
        "seed_identifier": authenticated_slot.seed_identifier,
        "team": authenticated_slot.team,
        "slot": authenticated_slot.slot,
        "slot_name": authenticated_slot.slot_name,
    }
    for field_name, expected_value in expected.items():
        found = getattr(state, field_name)
        if found != expected_value:
            raise StateBindingError(
                f"Bound Jak 3 AP state `{field_name}` does not match the "
                "authenticated slot."
            )
    state_contract = {
        "protocol_version": state.protocol_version,
        "game_integration_version": state.game_integration_version,
        "slot_data_version": state.slot_data_version,
        "state_schema_version": state.state_schema_version,
        "item_table_hash": state.item_table_hash,
        "location_table_hash": state.location_table_hash,
        "mission_table_hash": state.mission_table_hash,
        "resolved_options_hash": state.resolved_options_hash,
        "design_version": state.design_version,
    }
    for field_name, found in state_contract.items():
        expected_value = authenticated_slot.contract[field_name]
        if found != expected_value:
            raise StateCompatibilityError(
                f"Bound state `{field_name}` does not match authenticated slot data."
            )


def _binding_tuple(state: PersistentState) -> tuple[object, ...]:
    return (state.seed_identifier, state.team, state.slot, state.slot_name)


def _save_identity_authorization_payload(
    native_save_identity: str,
    authenticated_slot: AuthenticatedSlot,
) -> dict[str, object]:
    return {
        "authorization_version": SAVE_IDENTITY_AUTHORIZATION_VERSION,
        "native_save_identity": native_save_identity,
        "seed_identifier": authenticated_slot.seed_identifier,
        "team": authenticated_slot.team,
        "slot": authenticated_slot.slot,
        "slot_name": authenticated_slot.slot_name,
    }


def _load_save_identity_authorization(path: Path) -> Mapping[str, Any]:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise StateBindingError(
            "Native save identity has no durable authenticated-slot authorization; "
            "refusing its first AP binding."
        ) from exc
    except OSError as exc:
        raise StateCorruptionError(
            f"Could not read native-save identity authorization {path}: {exc}"
        ) from exc
    if not data:
        raise StateCorruptionError("Native-save identity authorization is empty.")
    try:
        envelope = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateCorruptionError(
            f"Native-save identity authorization is not valid UTF-8 JSON: {exc}"
        ) from exc
    if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_KEYS:
        raise StateCorruptionError(
            "Native-save identity authorization envelope has an incompatible shape."
        )
    if envelope["format"] != SAVE_IDENTITY_AUTHORIZATION_FORMAT:
        raise StateCompatibilityError(
            "Unsupported native-save identity authorization format: "
            f"{envelope['format']!r}."
        )
    if envelope["checksum_algorithm"] != CHECKSUM_ALGORITHM:
        raise StateCompatibilityError(
            "Unsupported native-save identity authorization checksum algorithm: "
            f"{envelope['checksum_algorithm']!r}."
        )
    payload = _require_mapping(
        envelope["payload"], "native-save identity authorization payload"
    )
    if set(payload) != SAVE_IDENTITY_AUTHORIZATION_KEYS:
        raise StateCorruptionError(
            "Native-save identity authorization payload has an incompatible shape."
        )
    checksum = envelope["payload_sha256"]
    if not isinstance(checksum, str) or len(checksum) != 64:
        raise StateCorruptionError(
            "Native-save identity authorization checksum has an invalid shape."
        )
    try:
        actual_checksum = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    except (TypeError, ValueError) as exc:
        raise StateCorruptionError(
            "Native-save identity authorization is not canonical JSON data."
        ) from exc
    if checksum != actual_checksum:
        raise StateCorruptionError(
            "Native-save identity authorization checksum does not match its payload."
        )
    if type(payload["authorization_version"]) is not int:
        raise StateCorruptionError(
            "Native-save identity authorization version must be an integer."
        )
    if payload["authorization_version"] != SAVE_IDENTITY_AUTHORIZATION_VERSION:
        raise StateCompatibilityError(
            "Unsupported native-save identity authorization version: "
            f"{payload['authorization_version']!r}."
        )
    _validate_uuid("authorized native save identity", payload["native_save_identity"])
    _validate_identity_text(
        "authorized seed identifier", payload["seed_identifier"], maximum=256
    )
    _validate_nonnegative_int("authorized team", payload["team"])
    _validate_nonnegative_int("authorized slot", payload["slot"])
    _validate_identity_text("authorized slot name", payload["slot_name"], maximum=128)
    return payload


def _validate_save_identity_authorization(
    authorization: Mapping[str, Any],
    native_save_identity: str,
    authenticated_slot: AuthenticatedSlot,
) -> None:
    expected = _save_identity_authorization_payload(
        native_save_identity, authenticated_slot
    )
    if dict(authorization) != expected:
        raise StateBindingError(
            "Native save identity was authorized for a different AP "
            "seed/team/slot; refusing its first AP binding."
        )


def _load_state_file(path: Path) -> PersistentState:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise _StateFileMissing(str(path)) from exc
    except OSError as exc:
        raise StateCorruptionError(
            f"Could not read Jak 3 AP state {path}: {exc}"
        ) from exc
    return deserialize_state(data)


def _write_temporary(target: Path, data: bytes) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _write_new_primary(target: Path, data: bytes) -> None:
    temporary = _write_temporary(target, data)
    try:
        os.replace(temporary, target)
        _sync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_replace_bytes(target: Path, data: bytes) -> None:
    temporary = _write_temporary(target, data)
    try:
        os.replace(temporary, target)
        _sync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _sync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise StateCorruptionError(f"Jak 3 AP {label} must be a string-keyed object.")
    return value


def _optional_mapping(value: object, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return dict(_require_mapping(value, label))


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise StateCorruptionError(f"Jak 3 AP {label} must be an array.")
    return value


def _parse_decimal_id(value: object) -> int:
    if not isinstance(value, str) or not value.isdecimal():
        raise StateCorruptionError("Received-item count keys must be decimal item IDs.")
    return int(value)


def _deserialize_received_item_entry(value: object) -> ReceivedItemJournalEntry:
    entry = _require_mapping(value, "received-item journal entry")
    expected_keys = {
        "index",
        "item_id",
        "location_id",
        "source_player",
        "flags",
        "state",
    }
    if set(entry) != expected_keys:
        raise StateCorruptionError(
            "Received-item journal entry has an incompatible shape."
        )
    return ReceivedItemJournalEntry(
        index=entry["index"],
        item_id=entry["item_id"],
        location_id=entry["location_id"],
        source_player=entry["source_player"],
        flags=entry["flags"],
        state=ReceivedItemState(entry["state"]),
    )


def _validate_native_save_slot(
    value: object, *, error_type: type[StateError] = StateBindingError
) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not 0 <= value < NATIVE_SAVE_SLOT_COUNT
    ):
        raise error_type(
            f"Native save slot must be 0-{NATIVE_SAVE_SLOT_COUNT - 1}; found {value!r}."
        )


def _validate_nonnegative_int(label: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise StateCorruptionError(f"Jak 3 AP {label} must be a nonnegative integer.")


def _validate_network_location_id(value: object) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or abs(value) > NETWORK_ID_ABSOLUTE_LIMIT
    ):
        raise StateCorruptionError(
            "Jak 3 AP received item location must be an integer in the AP "
            "network-ID range."
        )


def _validate_bool(label: str, value: object) -> None:
    if not isinstance(value, bool):
        raise StateCorruptionError(f"Jak 3 AP {label} must be a boolean.")


def _validate_optional_json_mapping(label: str, value: object) -> None:
    if value is None:
        return
    _validate_json_mapping(label, value)


def _validate_json_mapping(label: str, value: object) -> None:
    if type(value) is not dict:
        raise StateCorruptionError(f"Jak 3 AP {label} must be an object.")
    _validate_json_value(label, value)


def _validate_json_value(label: str, value: object) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(label, item)
        return
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise StateCorruptionError(f"Jak 3 AP {label} object keys must be strings.")
        for item in value.values():
            _validate_json_value(label, item)
        return
    detail = (
        "floating-point values" if isinstance(value, float) else type(value).__name__
    )
    raise StateCorruptionError(
        f"Jak 3 AP {label} must use normalized JSON containers; "
        f"{detail} are unsupported."
    )


def _validate_identity_text(label: str, value: object, *, maximum: int) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise StateCorruptionError(
            f"Jak 3 AP {label} must contain 1-{maximum} characters."
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise StateCorruptionError(f"Jak 3 AP {label} contains control characters.")


def _validate_uuid(label: str, value: object) -> None:
    if not isinstance(value, str):
        raise StateCorruptionError(f"Jak 3 AP {label} must be a UUID string.")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise StateCorruptionError(f"Jak 3 AP {label} is not a UUID.") from exc
    if str(parsed) != value:
        raise StateCorruptionError(f"Jak 3 AP {label} must use canonical UUID text.")


def _validate_sorted_unique_ints(
    label: str, values: tuple[int, ...], *, allowed: frozenset[int]
) -> None:
    if type(values) is not tuple:
        raise StateCorruptionError(f"Jak 3 AP {label} must be a tuple.")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        raise StateCorruptionError(f"Jak 3 AP {label} must contain integers.")
    if tuple(sorted(set(values))) != values:
        raise StateCorruptionError(f"Jak 3 AP {label} must be sorted and unique.")
    unknown = set(values) - allowed
    if unknown:
        raise StateCompatibilityError(
            f"Jak 3 AP {label} contains unsupported IDs: {sorted(unknown)}."
        )
