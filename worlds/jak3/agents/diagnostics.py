"""Resilient structured diagnostics and local sanitized support bundles.

This module is the sole writer of Jak 3 support artifacts.  GOAL contributes
bounded integer events through the normal temporary snapshot channel; it never
writes a support-facing file.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import pkgutil
import platform
import re
import sys
import tempfile
import threading
import traceback
import unicodedata
import zipfile
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic, sleep, time
from types import MappingProxyType
from typing import Any, Iterator, cast

import Utils

from ..versions import GAME_INTEGRATION_VERSION, PROTOCOL_VERSION


DIAGNOSTIC_SCHEMA_VERSION = 1
BUNDLE_MANIFEST_VERSION = 1
CLIENT_LOG_FORMAT = "[%(levelname)s] [%(name)s at %(asctime)s]: %(message)s"
ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
UUID_PATTERN = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)
CREDENTIAL_URL = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s,;]+@[^\s,;]+")
AUTHORIZATION_VALUE = re.compile(
    r"(?im)(?<![a-z0-9_-])"
    r"(?P<key_quote>['\"]?)(?P<key>proxy-authorization|authorization)"
    r"(?P=key_quote)\s*(?P<delimiter>[:=])\s*"
    r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|<redacted>|[^\r\n]+)"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?<![a-z0-9_])"
    r"(?P<key_quote>['\"]?)"
    r"(?P<key>(?:(?:[a-z0-9]+[_-])*"
    r"(?:password|passwd|token|secret|authorization|auth|api[_-]?key)"
    r"|[a-z0-9]+(?:password|passwd|token|secret|api[_-]?key)))"
    r"(?P=key_quote)\s*(?P<delimiter>[:=])\s*"
    r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|<redacted>|[^\r\n]+)"
)
WINDOWS_USER_PATH = re.compile(r"(?i)\b([a-z]:\\users\\)[^\\/\s]+")
POSIX_USER_PATH = re.compile(r"(?i)(/(?:home|users)/)[^/\s]+")
MANAGED_ARTIFACT = re.compile(
    r"^Jak3(?:Client|OpenGOAL|Events|Support)_[A-Za-z0-9_.-]+(?:\.txt|\.jsonl|\.zip)(?:\.[1-9][0-9]*)?$"
)
ORPHANED_SUPPORT_TEMP = re.compile(r"^Jak3Support_[A-Za-z0-9_.-]+\.zip\.tmp$")
MAX_BUNDLE_TEXT_CHARS = 32 * 1024 * 1024
TRUNCATED_LOG_NOTICE = "[Jak3 diagnostics: earlier sanitized log content omitted]\n"
SESSION_MARKER_RESERVE_BYTES = 1024
SESSION_MARKER_REFRESH_SECONDS = 60.0
SESSION_MARKER_LEASE_SECONDS = 30 * 60
INTERPROCESS_LOCK_TIMEOUT_SECONDS = 30.0
INTERPROCESS_LOCK_STALE_SECONDS = 30 * 60.0
_INTERPROCESS_LOCK_STATE = threading.local()
EVENT_ENVELOPE_FIELDS = frozenset(
    {
        "diagnostic_schema_version",
        "event_sequence",
        "observed_utc",
        "source_component",
        "source_sequence",
        "source_monotonic_or_game_tick",
        "severity",
        "event_name",
        "message",
        "session_id",
        "correlation_id",
        "process_id",
        "thread_or_task",
        "protocol_version",
        "game_integration_version",
        "runtime_state_sequence",
        "persistent_state_revision",
        "context",
        "details",
    }
)


@dataclass(frozen=True)
class DiagnosticPolicy:
    segment_bytes: int = 8 * 1024 * 1024
    backups_per_artifact: int = 3
    retained_sessions: int = 10
    retention_days: int = 14
    managed_bytes: int = 256 * 1024 * 1024

    @classmethod
    def from_environment(cls) -> DiagnosticPolicy:
        names = {
            "segment_bytes": "JAK3_DIAGNOSTICS_SEGMENT_BYTES",
            "backups_per_artifact": "JAK3_DIAGNOSTICS_BACKUPS",
            "retained_sessions": "JAK3_DIAGNOSTICS_SESSIONS",
            "retention_days": "JAK3_DIAGNOSTICS_DAYS",
            "managed_bytes": "JAK3_DIAGNOSTICS_MANAGED_BYTES",
        }
        values: dict[str, int] = {}
        for field_name, variable in names.items():
            raw = os.environ.get(variable)
            if raw is None:
                continue
            try:
                values[field_name] = int(raw)
            except ValueError as exc:
                raise ValueError(f"{variable} must be an integer.") from exc
        policy = cls(**values)
        policy.validate()
        return policy

    def validate(self) -> None:
        values = (
            self.segment_bytes,
            self.backups_per_artifact,
            self.retained_sessions,
            self.retention_days,
            self.managed_bytes,
        )
        if any(type(value) is not int or value <= 0 for value in values):
            raise ValueError("Diagnostic policy values must be positive integers.")
        if not 1024 <= self.segment_bytes <= 64 * 1024 * 1024:
            raise ValueError("Diagnostic segment size must be 1 KiB through 64 MiB.")
        if self.backups_per_artifact > 16:
            raise ValueError("Diagnostic backup count cannot exceed 16.")
        if self.retained_sessions > 100:
            raise ValueError("Diagnostic retained-session count cannot exceed 100.")
        if self.retention_days > 365:
            raise ValueError("Diagnostic retention cannot exceed 365 days.")
        if self.managed_bytes > 2 * 1024 * 1024 * 1024:
            raise ValueError("Diagnostic managed capacity cannot exceed 2 GiB.")
        active_rotation_capacity = (
            3 * (self.backups_per_artifact + 1) * self.segment_bytes
        )
        if active_rotation_capacity + SESSION_MARKER_RESERVE_BYTES > self.managed_bytes:
            raise ValueError(
                "Diagnostic active rotation capacity cannot exceed the managed cap."
            )


@dataclass(frozen=True)
class EventDefinition:
    name: str
    default_severity: str
    goal_code: int | None
    context_fields: frozenset[str]
    detail_fields: frozenset[str]
    context_object_fields: Mapping[str, frozenset[str]]


def _fields(*names: str) -> frozenset[str]:
    return frozenset(names)


_EMPTY_FIELDS: frozenset[str] = frozenset()
_DIAGNOSTIC_CONTEXT = _fields(
    "artifact",
    "bundle_path",
    "capture",
    "dropped_count",
    "exception_type",
    "fingerprint",
    "gap_end",
    "gap_start",
    "mode",
    "process",
    "reason",
    "source",
    "source_sequence",
    "status",
)
_PROCESS_CONTEXT = _fields("capture", "pid", "process", "reason", "return_code")
_BRIDGE_CONTEXT = _fields(
    "manifest_version", "path_hash", "reason", "source", "source_set_hash", "status"
)
_SAVE_CONTEXT = _fields(
    "native_save_hash",
    "native_save_slot",
    "reason",
    "seed_hash",
    "slot_hash",
    "status",
)
_RUNTIME_CONTEXT = _fields(
    "native_save_hash", "reason", "runtime_state", "safety_projection", "status"
)
_RUNTIME_STATE_FIELDS = _fields(
    "act",
    "ap_state_bound",
    "ap_state_loaded",
    "connected",
    "game_status",
    "level",
    "native_save_hash",
    "native_save_slot",
    "save_loaded",
    "task",
)
_SAFETY_PROJECTION_FIELDS = _fields("consumable", "mission", "permanent")
_COMMAND_CONTEXT = _fields(
    "command_id", "command_kind", "error_code", "reason", "result", "status"
)
_ITEM_CONTEXT = _fields(
    "attribution",
    "command_id",
    "expected_index",
    "history_discrepancy_count",
    "item_id",
    "item_index",
    "item_name",
    "ledger_revision",
    "outcome",
    "packet_count",
    "reason",
    "safety_reason",
    "target_mask",
)
_ITEM_ATTRIBUTION_FIELDS = _fields("flags", "location_id", "source_player")
_LOCATION_CONTEXT = _fields(
    "batch_id",
    "location_id",
    "location_ids",
    "outcome",
    "reason",
    "reward_node_id",
    "revision",
    "source",
    "task_id",
    "task_ids",
)
_REWARD_CONTEXT = _fields(
    "ap_applying_item",
    "decision",
    "location_id",
    "outcome",
    "reward_node_id",
    "task_id",
    "target_mask",
)
_GOAL_STATUS_CONTEXT = _fields(
    "connection_generation",
    "location_ids",
    "outcome",
    "reason",
    "revision",
    "status",
    "task_id",
)
_PERSISTENCE_CONTEXT = _fields(
    "category",
    "native_save_hash",
    "new_revision",
    "old_revision",
    "path_hash",
    "reason",
    "revision",
    "seed_hash",
    "slot_hash",
    "state_id_hash",
    "status",
)
_GOAL_CONTEXT = _fields(
    "command_id",
    "error_code",
    "game_tick",
    "native_save_slot",
    "result",
    "source_generation",
    "source_sequence",
)

_PROVIDER_FIELDS = MappingProxyType(
    {
        "runtime": _fields(
            "authenticated",
            "bridge_ready",
            "client_status",
            "game_attached",
            "game_session_nonce_hash",
            "game_status",
            "items_module_active",
            "last_bridge_error_present",
            "locations_module_active",
            "native_save_hash",
            "native_save_slot",
            "repl_connected",
            "reward_module_active",
            "safe_consumable",
            "safe_mission",
            "safe_permanent",
            "save_loaded",
            "server_connected",
            "snapshot_revision",
            "source_loaded",
        ),
        "persistence": _fields(
            "binding_status",
            "bound",
            "contract_status",
            "has_recent_command",
            "last_clean_shutdown",
            "location_count",
            "open",
            "quarantine_status",
            "read_only_failure_present",
            "received_item_count",
            "recovery_status",
            "revision",
        ),
        "versions": _fields(
            "bridge_manifest_version",
            "bridge_runtime_version",
            "game_integration_version",
            "item_table_version",
            "location_table_version",
            "mission_table_version",
            "protocol_version",
            "slot_data_version",
            "source_set_sha256",
            "state_schema_version",
        ),
        "commands": _fields("recent"),
    }
)
_PROVIDER_COMMAND_FIELDS = _fields("command_id", "command_kind", "error", "result")
_PROVIDER_CAPTURE_GAP_FIELDS = _fields("component", "reason")


def _context_allowlist(name: str, goal_code: int | None) -> frozenset[str]:
    if name.startswith("diagnostics."):
        selected = _DIAGNOSTIC_CONTEXT
    elif name.startswith("process."):
        selected = _PROCESS_CONTEXT
    elif name.startswith(("opengoal.", "bridge.", "nrepl.")):
        selected = _BRIDGE_CONTEXT
    elif name.startswith(("save.", "binding.")):
        selected = _SAVE_CONTEXT | _fields("binding_state")
    elif name.startswith("runtime."):
        selected = _RUNTIME_CONTEXT
    elif name.startswith("protocol.command."):
        selected = _COMMAND_CONTEXT
    elif name.startswith(("ap.received_items.", "item.")):
        selected = _ITEM_CONTEXT
    elif name.startswith("location."):
        selected = _LOCATION_CONTEXT
    elif name.startswith("reward."):
        selected = _REWARD_CONTEXT
    elif name.startswith("goal."):
        selected = _GOAL_STATUS_CONTEXT
    elif name.startswith("persistence."):
        selected = _PERSISTENCE_CONTEXT
    elif name.startswith("server."):
        selected = _fields("reason", "seed_hash", "slot_hash", "status")
    elif name.startswith("slot."):
        selected = _fields("reason", "seed_hash", "slot_hash", "status")
    elif name.startswith(("compatibility.", "protocol.handshake.")):
        selected = _fields("reason", "status")
    elif name == "diagnostics.session.started":
        selected = _fields("mode")
    elif name == "client.stopped":
        selected = _fields("status")
    else:
        selected = _EMPTY_FIELDS
    return selected | (_GOAL_CONTEXT if goal_code is not None else _EMPTY_FIELDS)


def _detail_allowlist(name: str, goal_code: int | None) -> frozenset[str]:
    selected = _EMPTY_FIELDS
    if name in {
        "diagnostics.event.rejected",
        "diagnostics.events_dropped_or_suppressed",
        "diagnostics.goal.drain.completed",
        "diagnostics.retention.completed",
        "bridge.install.verified",
        "bridge.install.repaired",
    }:
        selected |= _fields("count")
    if name.startswith("diagnostics.exception."):
        selected |= _fields("exception")
    if name.startswith("diagnostics.bundle.export."):
        selected |= _fields("missing", "truncated")
    if name in {"runtime.state.changed", "runtime.safety.changed"}:
        selected |= _fields("new", "old")
    if goal_code is not None:
        selected |= _fields("new")
    return selected


def _context_object_allowlist(name: str) -> Mapping[str, frozenset[str]]:
    if name == "runtime.state.changed":
        return MappingProxyType({"runtime_state": _RUNTIME_STATE_FIELDS})
    if name == "runtime.safety.changed":
        return MappingProxyType({"safety_projection": _SAFETY_PROJECTION_FIELDS})
    if name.startswith(("ap.received_items.", "item.")):
        return MappingProxyType({"attribution": _ITEM_ATTRIBUTION_FIELDS})
    return MappingProxyType({})


def _registry() -> Mapping[str, EventDefinition]:
    error_names = {
        "diagnostics.prior_session.unclean",
        "diagnostics.capture_gap",
        "diagnostics.event.rejected",
        "diagnostics.writer.failed",
        "diagnostics.exception.main",
        "diagnostics.exception.asyncio",
        "diagnostics.exception.thread",
        "diagnostics.bundle.export.failed",
        "bridge.install.failed",
        "process.crashed",
        "nrepl.failed",
        "bridge.reload.failed",
        "slot.contract.rejected",
        "protocol.handshake.rejected",
        "save.native_operation.failed",
        "binding.rejected",
        "protocol.command.failed",
        "persistence.commit.failed",
        "persistence.corruption.detected",
        "persistence.compatibility.rejected",
        "persistence.binding.rejected",
        "persistence.eligibility.rejected",
        "persistence.concurrent_writer.rejected",
        "item.receipt.rejected",
        "item.application.failed",
        "item.native_target.failed",
        "location.outbox.send_failed",
        "location.reconciliation.rejected",
        "reward.shape_mismatch",
        "goal.status.failed",
    }
    warning_names = {
        "diagnostics.events_dropped_or_suppressed",
        "diagnostics.bundle.export.partial",
        "diagnostics.goal.gap",
        "diagnostics.goal.overflow",
        "process.capture_gap",
        "nrepl.timeout",
        "bridge.restart_required",
        "save.identity.invalidated",
        "save.native.ineligible",
        "runtime.communication.lost",
        "protocol.command.unsafe",
        "protocol.command.rejected",
        "protocol.command.timed_out",
        "persistence.writer_lock.refused",
        "persistence.revision.stale",
        "persistence.shutdown.unclean",
        "item.receipt.index_gap",
        "item.application.queued",
        "location.duplicate_ignored",
        "reward.native_preserved",
    }
    names = (
        "diagnostics.session.started",
        "diagnostics.session.stopped",
        "diagnostics.prior_session.clean",
        "diagnostics.prior_session.unclean",
        "diagnostics.capture_gap",
        "diagnostics.events_dropped_or_suppressed",
        "diagnostics.event.rejected",
        "diagnostics.writer.failed",
        "diagnostics.rotation.completed",
        "diagnostics.retention.completed",
        "diagnostics.exception.main",
        "diagnostics.exception.asyncio",
        "diagnostics.exception.thread",
        "diagnostics.bundle.export.started",
        "diagnostics.bundle.export.completed",
        "diagnostics.bundle.export.partial",
        "diagnostics.bundle.export.failed",
        "diagnostics.goal.drain.completed",
        "diagnostics.goal.duplicate",
        "diagnostics.goal.gap",
        "diagnostics.goal.overflow",
        "client.started",
        "client.stopping",
        "client.stopped",
        "server.connecting",
        "server.authenticated",
        "server.disconnected",
        "server.rejected",
        "bridge.client.disconnected",
        "opengoal.install.discovered",
        "bridge.install.verified",
        "bridge.install.repaired",
        "bridge.install.failed",
        "process.started",
        "process.already_running",
        "process.capture_gap",
        "process.exited",
        "process.crashed",
        "nrepl.connecting",
        "nrepl.attached",
        "nrepl.closed",
        "nrepl.timeout",
        "nrepl.failed",
        "bridge.source.loaded",
        "bridge.event_channel.ready",
        "bridge.reload.required",
        "bridge.reload.started",
        "bridge.reload.activated",
        "bridge.reload.failed",
        "bridge.restart_required",
        "compatibility.contract.reported",
        "slot.contract.accepted",
        "slot.contract.rejected",
        "protocol.handshake.accepted",
        "protocol.handshake.rejected",
        "save.identity.proposed",
        "save.identity.authorized",
        "save.identity.consumed",
        "save.identity.published",
        "save.identity.invalidated",
        "save.native_operation.started",
        "save.native_operation.succeeded",
        "save.native_operation.failed",
        "save.native.observed",
        "save.native.loaded",
        "save.native.unloaded",
        "save.native.switched",
        "save.native.eligible",
        "save.native.ineligible",
        "binding.deferred",
        "binding.opened",
        "binding.switched",
        "binding.rejected",
        "binding.closed",
        "runtime.state.changed",
        "runtime.safety.changed",
        "runtime.communication.lost",
        "runtime.communication.reconnected",
        "protocol.command.submitted",
        "protocol.command.accepted",
        "protocol.command.applied",
        "protocol.command.replayed",
        "protocol.command.queued",
        "protocol.command.unsafe",
        "protocol.command.rejected",
        "protocol.command.timed_out",
        "protocol.command.failed",
        "protocol.command.recovered",
        "ap.received_items.packet_observed",
        "item.receipt.accepted",
        "item.receipt.duplicate",
        "item.receipt.index_gap",
        "item.receipt.rejected",
        "item.replay.started",
        "item.replay.completed",
        "item.application.queued",
        "item.application.command_submitted",
        "item.application.completed",
        "item.application.already_applied",
        "item.application.failed",
        "item.reconciliation.started",
        "item.reconciliation.completed",
        "item.recovery.started",
        "item.recovery.completed",
        "item.native_target.applied",
        "item.native_target.already_correct",
        "item.native_target.failed",
        "location.observed",
        "location.duplicate_ignored",
        "location.committed_local",
        "location.outbox.enqueued",
        "location.outbox.batch_sent",
        "location.outbox.send_failed",
        "location.server_confirmed",
        "location.reconciliation.started",
        "location.reconciliation.completed",
        "location.reconciliation.rejected",
        "reward.native_preserved",
        "reward.permanent_suppressed",
        "reward.shape_mismatch",
        "reward.item_application_guarded",
        "goal.completed",
        "goal.status.queued",
        "goal.status.sent",
        "goal.status.resent",
        "goal.status.failed",
        "persistence.writer_lock.acquired",
        "persistence.writer_lock.refused",
        "persistence.writer_lock.released",
        "persistence.path.selected",
        "persistence.state.created",
        "persistence.state.loaded",
        "persistence.state.bound",
        "persistence.state.switched",
        "persistence.state.closed",
        "persistence.commit.attempted",
        "persistence.commit.succeeded",
        "persistence.commit.failed",
        "persistence.backup.refreshed",
        "persistence.backup.restored",
        "persistence.corruption.detected",
        "persistence.quarantine.performed",
        "persistence.compatibility.rejected",
        "persistence.binding.rejected",
        "persistence.eligibility.rejected",
        "persistence.shutdown.clean",
        "persistence.shutdown.unclean",
        "persistence.revision.stale",
        "persistence.concurrent_writer.rejected",
    )
    goal_codes = {
        "bridge.source.loaded": 100,
        "bridge.event_channel.ready": 101,
        "save.identity.proposed": 200,
        "save.identity.published": 202,
        "save.identity.invalidated": 203,
        "save.native_operation.started": 210,
        "save.native_operation.succeeded": 211,
        "save.native_operation.failed": 212,
        "runtime.state.changed": 300,
        "runtime.safety.changed": 301,
        "protocol.handshake.accepted": 400,
        "protocol.handshake.rejected": 401,
        "protocol.command.applied": 411,
        "protocol.command.replayed": 412,
        "protocol.command.unsafe": 413,
        "protocol.command.rejected": 414,
        "protocol.command.failed": 415,
        "bridge.client.disconnected": 420,
        "item.native_target.applied": 500,
        "item.native_target.already_correct": 501,
        "item.native_target.failed": 502,
        "location.observed": 600,
        "reward.native_preserved": 700,
        "reward.permanent_suppressed": 701,
        "reward.shape_mismatch": 702,
        "reward.item_application_guarded": 703,
    }
    definitions = {
        name: EventDefinition(
            name=name,
            default_severity=(
                "ERROR"
                if name in error_names
                else "WARNING"
                if name in warning_names
                else "INFO"
            ),
            goal_code=goal_codes.get(name),
            context_fields=_context_allowlist(name, goal_codes.get(name)),
            detail_fields=_detail_allowlist(name, goal_codes.get(name)),
            context_object_fields=_context_object_allowlist(name),
        )
        for name in names
    }
    return MappingProxyType(definitions)


EVENT_REGISTRY = _registry()
GOAL_EVENT_REGISTRY = MappingProxyType(
    {
        definition.goal_code: definition
        for definition in EVENT_REGISTRY.values()
        if definition.goal_code is not None
    }
)

REWARD_NATIVE_PRESERVED_GOAL_CODE = 700
REWARD_PERMANENT_SUPPRESSED_GOAL_CODE = 701
REWARD_SHAPE_MISMATCH_GOAL_CODE = 702
REWARD_ITEM_GUARD_GOAL_CODE = 703


@dataclass(frozen=True)
class GoalDiagnosticRecord:
    source_sequence: int
    game_tick: int
    severity: int
    event_code: int
    correlation_kind: int
    correlation_value: int
    result: int
    error: int
    arg0: int
    arg1: int
    arg2: int


@dataclass(frozen=True)
class BundleExportResult:
    status: str
    path: Path | None
    missing: tuple[str, ...] = ()
    error: str | None = None
    truncated: tuple[str, ...] = ()


def hash_identifier(value: object) -> str:
    """Return a stable diagnostic correlation without exposing the input."""

    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:16]


def _redacted_assignment(match: re.Match[str]) -> str:
    quote = match.group("key_quote")
    return f"{quote}{match.group('key')}{quote}{match.group('delimiter')}<redacted>"


def _process_is_running(process_id: int) -> bool:
    """Best-effort local liveness check used only for marker classification."""

    if process_id <= 0:
        return False
    if process_id == os.getpid():
        return True
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, OverflowError):
        return False
    return True


def _process_start_identity(process_id: int) -> str | None:
    """Return an OS start identity that distinguishes processes reusing a PID."""

    if process_id <= 0:
        return None
    if os.name == "nt":
        try:
            import ctypes

            class _FileTime(ctypes.Structure):
                _fields_ = (
                    ("low", ctypes.c_uint32),
                    ("high", ctypes.c_uint32),
                )

            loader = getattr(ctypes, "WinDLL", None)
            if loader is None:
                return None
            kernel32: Any = loader("kernel32", use_last_error=True)
            open_process = kernel32.OpenProcess
            open_process.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
            open_process.restype = ctypes.c_void_p
            get_process_times = kernel32.GetProcessTimes
            file_time_pointer = ctypes.POINTER(_FileTime)
            get_process_times.argtypes = (
                ctypes.c_void_p,
                file_time_pointer,
                file_time_pointer,
                file_time_pointer,
                file_time_pointer,
            )
            get_process_times.restype = ctypes.c_int
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = (ctypes.c_void_p,)
            close_handle.restype = ctypes.c_int
            handle = open_process(0x1000, 0, process_id)
            if not handle:
                return None
            try:
                created = _FileTime()
                exited = _FileTime()
                kernel = _FileTime()
                user = _FileTime()
                if not get_process_times(
                    handle,
                    ctypes.byref(created),
                    ctypes.byref(exited),
                    ctypes.byref(kernel),
                    ctypes.byref(user),
                ):
                    return None
                value = (created.high << 32) | created.low
                return f"windows-filetime:{value}"
            finally:
                close_handle(handle)
        except Exception:
            return None

    try:
        stat = Path(f"/proc/{process_id}/stat").read_text(encoding="ascii")
        close_paren = stat.rfind(")")
        if close_paren < 0:
            return None
        fields = stat[close_paren + 1 :].split()
        if len(fields) <= 19:
            return None
        start_ticks = int(fields[19])
        if start_ticks < 0:
            return None
        return f"procfs-startticks:{start_ticks}"
    except Exception:
        return None


def _lock_owner_age(lock_directory: Path, payload: Mapping[str, object]) -> float:
    created_unix = payload.get("created_unix")
    if isinstance(created_unix, (int, float)) and not isinstance(created_unix, bool):
        return max(0.0, time() - float(created_unix))
    try:
        return max(0.0, time() - lock_directory.stat().st_mtime)
    except OSError:
        return 0.0


def _recover_stale_interprocess_lock(
    lock_directory: Path, *, stale_seconds: float
) -> bool:
    """Remove only a demonstrably stale lock directory created by this module."""

    owner_path = lock_directory / "owner.json"
    try:
        observed = owner_path.read_bytes()
        document = json.loads(observed.decode("utf-8"))
        payload = document if isinstance(document, Mapping) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        observed = None
        payload = {}
    age = _lock_owner_age(lock_directory, payload)
    process_id = payload.get("process_id")
    host = payload.get("host")
    local_host = platform.node() or "local-host"
    if type(process_id) is int and isinstance(host, str) and host == local_host:
        # Age alone must never evict a live same-host owner. Installation and
        # support export are expected to be short, but a slow filesystem or
        # debugger pause cannot be allowed to destroy mutual exclusion.
        running = _process_is_running(process_id)
        stale = not running
        if running:
            owner_identity = payload.get("process_start_identity")
            current_identity = _process_start_identity(process_id)
            # Missing start identities are intentionally conservative for
            # compatibility and on platforms that cannot expose one. When
            # both are available, a mismatch proves that the PID was reused.
            if (
                isinstance(owner_identity, str)
                and owner_identity
                and isinstance(current_identity, str)
                and current_identity
            ):
                stale = owner_identity != current_identity
    else:
        # Remote and malformed owners cannot be inspected. Their bounded lease
        # prevents a crashed machine or half-written owner record from blocking
        # diagnostics forever.
        stale = age > stale_seconds
    if not stale:
        return False
    try:
        if observed is not None and owner_path.read_bytes() != observed:
            return False
        owner_path.unlink(missing_ok=True)
        lock_directory.rmdir()
        return True
    except OSError:
        return False


@contextmanager
def interprocess_directory_lock(
    lock_directory: Path,
    *,
    timeout_seconds: float = INTERPROCESS_LOCK_TIMEOUT_SECONDS,
    stale_seconds: float = INTERPROCESS_LOCK_STALE_SECONDS,
) -> Iterator[None]:
    """Serialize a short transaction across Python and standalone installers."""

    if timeout_seconds <= 0 or stale_seconds <= 0:
        raise ValueError("Interprocess lock timeouts must be positive.")
    lock_key = os.path.normcase(str(lock_directory.resolve(strict=False)))
    held_paths = getattr(_INTERPROCESS_LOCK_STATE, "held_paths", None)
    if held_paths is None:
        held_paths = set()
        _INTERPROCESS_LOCK_STATE.held_paths = held_paths
    if lock_key in held_paths:
        # A writer failure can enter temporary-storage fallback while its outer
        # capacity transaction is still active. Preserve the one on-disk owner
        # and make that same-thread path safely reentrant.
        yield
        return
    lock_directory.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}-{threading.get_ident()}-{time():.9f}"
    owner_path = lock_directory / "owner.json"
    deadline = monotonic() + timeout_seconds
    while True:
        try:
            lock_directory.mkdir()
        except FileExistsError:
            if _recover_stale_interprocess_lock(
                lock_directory, stale_seconds=stale_seconds
            ):
                continue
            if monotonic() >= deadline:
                raise TimeoutError(
                    f"Timed out waiting for interprocess lock {lock_directory.name}."
                )
            sleep(0.025)
            continue
        try:
            owner_path.write_text(
                json.dumps(
                    {
                        "token": token,
                        "process_id": os.getpid(),
                        "process_start_identity": _process_start_identity(os.getpid()),
                        "host": platform.node() or "local-host",
                        "created_unix": time(),
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        except BaseException:
            try:
                owner_path.unlink(missing_ok=True)
                lock_directory.rmdir()
            except OSError:
                pass
            raise
        break
    held_paths.add(lock_key)
    try:
        yield
    finally:
        held_paths.discard(lock_key)
        try:
            document = json.loads(owner_path.read_text("utf-8"))
            if isinstance(document, Mapping) and document.get("token") == token:
                owner_path.unlink(missing_ok=True)
                lock_directory.rmdir()
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass


def _goal_correlation(kind: int, value: int) -> tuple[str | None, dict[str, int]]:
    if kind == 1:
        return f"native-slot:{value}", {"native_save_slot": value}
    if kind == 2:
        return f"command:{value}", {"command_id": value}
    if kind == 3:
        return f"location:{value}", {"location_id": value}
    if kind:
        return f"goal-kind-{kind}:{value}", {}
    return None, {}


def _world_metadata() -> dict[str, object]:
    package = __package__.rsplit(".", 1)[0]
    try:
        payload = pkgutil.get_data(package, "archipelago.json")
        document = json.loads(payload.decode("utf-8")) if payload else {}
        return document if isinstance(document, dict) else {}
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
        return {}


def _normalize_text(value: object, *, limit: int | None = 4096) -> str:
    text = unicodedata.normalize("NFC", str(value))
    text = ANSI_ESCAPE.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    text = CREDENTIAL_URL.sub("<credential-url:redacted>", text)
    text = AUTHORIZATION_VALUE.sub(_redacted_assignment, text)
    text = SECRET_ASSIGNMENT.sub(_redacted_assignment, text)
    text = WINDOWS_USER_PATH.sub(r"\1<user>", text)
    text = POSIX_USER_PATH.sub(r"\1<user>", text)
    text = UUID_PATTERN.sub(
        lambda match: f"<uuid:{hash_identifier(match.group(0))}>", text
    )
    return text if limit is None else text[:limit]


def _safe_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Non-finite diagnostic number")
        return value
    if isinstance(value, str):
        return _normalize_text(value, limit=1024)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:64]]
    if isinstance(value, Mapping):
        return {
            _normalize_text(key, limit=80): _safe_value(item)
            for key, item in list(value.items())[:64]
            if isinstance(key, str)
        }
    raise TypeError(f"Unsupported diagnostic value: {type(value).__name__}")


def _safe_event_leaf(value: object) -> object:
    """Sanitize an event value while prohibiting undeclared nested objects."""

    if isinstance(value, Mapping):
        raise ValueError("Nested diagnostic object is not allowlisted")
    if isinstance(value, (list, tuple)):
        return [_safe_event_leaf(item) for item in value[:64]]
    return _safe_value(value)


def _encode_event_envelope(envelope: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            envelope,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _compact_event_value(value: object) -> object:
    """Retain a small forensic projection when one event exceeds its segment."""

    if isinstance(value, str):
        return _normalize_text(value, limit=96)
    if isinstance(value, list):
        return [_compact_event_value(item) for item in value[:8]]
    if isinstance(value, Mapping):
        return {
            key: _compact_event_value(item)
            for key, item in list(value.items())[:8]
            if isinstance(key, str)
        }
    return value


def _bounded_event_payload(
    envelope: Mapping[str, object], maximum_bytes: int
) -> tuple[bytes, bool]:
    """Serialize an event, compacting details instead of dropping the event."""

    payload = _encode_event_envelope(envelope)
    if len(payload) <= maximum_bytes:
        return payload, False

    compact = dict(envelope)
    original_message = _normalize_text(compact.get("message", ""), limit=160)
    compact["message"] = f"[diagnostic payload truncated] {original_message}"
    compact["source_component"] = _normalize_text(
        compact.get("source_component", "python"), limit=32
    )
    compact["session_id"] = _normalize_text(compact.get("session_id", ""), limit=64)
    compact["thread_or_task"] = _normalize_text(
        compact.get("thread_or_task", ""), limit=32
    )
    correlation = compact.get("correlation_id")
    compact["correlation_id"] = (
        None if correlation is None else _normalize_text(correlation, limit=64)
    )
    context = compact.get("context")
    compact["context"] = (
        {
            key: _compact_event_value(value)
            for key, value in list(context.items())[:8]
            if isinstance(key, str)
        }
        if isinstance(context, Mapping)
        else {}
    )
    original_details = compact.get("details")
    compact["details"] = {}

    # Exception tracebacks are the most useful oversized payload. Preserve the
    # newest suffix that fits because it contains the exception type/message
    # and innermost frames. Other events retain their stable envelope/context.
    exception_text = (
        original_details.get("exception")
        if isinstance(original_details, Mapping)
        else None
    )
    if isinstance(exception_text, str):
        marker = "[earlier traceback text truncated]\n"
        low = 0
        high = len(exception_text)
        best = b""
        while low <= high:
            length = (low + high) // 2
            compact["details"] = {
                "exception": marker + (exception_text[-length:] if length else "")
            }
            candidate = _encode_event_envelope(compact)
            if len(candidate) <= maximum_bytes:
                best = candidate
                low = length + 1
            else:
                high = length - 1
        if best:
            return best, True
        compact["details"] = {}

    payload = _encode_event_envelope(compact)
    if len(payload) <= maximum_bytes:
        return payload, True

    # The 1 KiB validated minimum fits this required-field-only projection.
    compact["message"] = "[diagnostic payload truncated]"
    compact["context"] = {}
    compact["details"] = {}
    compact["source_component"] = _normalize_text(
        compact.get("source_component", "python"), limit=16
    )
    compact["session_id"] = _normalize_text(compact.get("session_id", ""), limit=32)
    compact["thread_or_task"] = _normalize_text(
        compact.get("thread_or_task", ""), limit=16
    )
    compact["correlation_id"] = None
    payload = _encode_event_envelope(compact)
    if len(payload) > maximum_bytes:
        raise ValueError(
            "Diagnostic event envelope exceeds the configured segment size"
        )
    return payload, True


def _allowlisted_mapping(
    values: Mapping[str, object] | None,
    allowed: frozenset[str],
    object_fields: Mapping[str, frozenset[str]] | None = None,
) -> dict[str, object]:
    if not values:
        return {}
    unexpected = set(values) - allowed
    if unexpected:
        raise ValueError(f"Fields are not allowlisted: {sorted(unexpected)}")
    nested = object_fields or {}
    sanitized: dict[str, object] = {}
    for key, value in values.items():
        if isinstance(value, Mapping):
            nested_allowed = nested.get(key)
            if nested_allowed is None:
                raise ValueError(f"Nested diagnostic object is not allowlisted: {key}")
            unexpected_nested = set(value) - nested_allowed
            if unexpected_nested:
                raise ValueError(
                    f"Nested fields are not allowlisted for {key}: "
                    f"{sorted(unexpected_nested)}"
                )
            clean_nested: dict[str, object] = {}
            for nested_key, nested_value in value.items():
                clean_nested[nested_key] = _safe_event_leaf(nested_value)
            sanitized[key] = clean_nested
            continue
        sanitized[key] = _safe_event_leaf(value)
    return sanitized


def _validated_event_envelope(event: object) -> dict[str, object]:
    """Return one sanitized schema-v1 envelope while ignoring future fields."""

    if not isinstance(event, Mapping) or not EVENT_ENVELOPE_FIELDS <= set(event):
        raise ValueError("Diagnostic event envelope is missing schema v1 fields")

    def integer(name: str, *, minimum: int | None = None) -> int:
        value = event[name]
        if type(value) is not int or (minimum is not None and value < minimum):
            raise ValueError(f"Diagnostic event field {name} is not a valid integer")
        return value

    def optional_integer(name: str) -> int | None:
        value = event[name]
        if value is None:
            return None
        return integer(name)

    event_name = event["event_name"]
    if not isinstance(event_name, str) or event_name not in EVENT_REGISTRY:
        raise ValueError("Diagnostic event name is not registered")
    definition = EVENT_REGISTRY[event_name]
    if event["diagnostic_schema_version"] != DIAGNOSTIC_SCHEMA_VERSION:
        raise ValueError("Diagnostic event schema version is unsupported")
    severity = event["severity"]
    if severity not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("Diagnostic event severity is invalid")
    observed_utc = event["observed_utc"]
    if not isinstance(observed_utc, str) or not observed_utc.endswith("Z"):
        raise ValueError("Diagnostic event timestamp is not UTC")
    try:
        observed = datetime.fromisoformat(observed_utc[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("Diagnostic event timestamp is invalid") from exc
    if observed.utcoffset() != timedelta(0):
        raise ValueError("Diagnostic event timestamp is not UTC")

    string_fields = (
        "source_component",
        "message",
        "session_id",
        "thread_or_task",
    )
    if any(not isinstance(event[name], str) for name in string_fields):
        raise ValueError("Diagnostic event string field is invalid")
    correlation_id = event["correlation_id"]
    if correlation_id is not None and not isinstance(correlation_id, str):
        raise ValueError("Diagnostic event correlation is invalid")
    context = event["context"]
    details = event["details"]
    if not isinstance(context, Mapping) or not isinstance(details, Mapping):
        raise ValueError("Diagnostic event context/details must be objects")

    return {
        "diagnostic_schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "event_sequence": integer("event_sequence", minimum=1),
        "observed_utc": _normalize_text(observed_utc, limit=64),
        "source_component": _normalize_text(event["source_component"], limit=64),
        "source_sequence": integer("source_sequence", minimum=0),
        "source_monotonic_or_game_tick": optional_integer(
            "source_monotonic_or_game_tick"
        ),
        "severity": severity,
        "event_name": event_name,
        "message": _normalize_text(event["message"]),
        "session_id": _normalize_text(event["session_id"], limit=128),
        "correlation_id": (
            None
            if correlation_id is None
            else _normalize_text(correlation_id, limit=128)
        ),
        "process_id": integer("process_id", minimum=0),
        "thread_or_task": _normalize_text(event["thread_or_task"], limit=96),
        "protocol_version": integer("protocol_version", minimum=0),
        "game_integration_version": integer("game_integration_version", minimum=0),
        "runtime_state_sequence": optional_integer("runtime_state_sequence"),
        "persistent_state_revision": optional_integer("persistent_state_revision"),
        "context": _allowlisted_mapping(
            context, definition.context_fields, definition.context_object_fields
        ),
        "details": _allowlisted_mapping(details, definition.detail_fields),
    }


class _RoutingFilter(logging.Filter):
    """Preserve Archipelago's stream/file routing conventions."""

    def __init__(self, excluded_flag: str, *, exclude_carriage_return: bool = False):
        super().__init__()
        self.excluded_flag = excluded_flag
        self.exclude_carriage_return = exclude_carriage_return

    def filter(self, record: logging.LogRecord) -> bool:
        if bool(getattr(record, self.excluded_flag, False)):
            return False
        return not (
            self.exclude_carriage_return
            and (
                bool(getattr(record, "_jak3_had_carriage_return", False))
                or "\r" in record.getMessage()
            )
        )


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if not hasattr(record, "_jak3_had_carriage_return"):
                setattr(
                    record,
                    "_jak3_had_carriage_return",
                    "\r" in record.getMessage(),
                )
            record.msg = _normalize_text(record.getMessage())
            record.args = ()
            if record.exc_info is not None:
                record.exc_text = _normalize_text(
                    "".join(traceback.format_exception(*record.exc_info)), limit=8192
                )
            if record.stack_info is not None:
                record.stack_info = _normalize_text(record.stack_info, limit=8192)
        except Exception:
            record.msg = "<diagnostic log message unavailable>"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


class _ClientDiagnosticHandler(logging.Handler):
    """Route Python logging through the same serialized resilient writer."""

    def __init__(self, session: DiagnosticSession) -> None:
        super().__init__(logging.DEBUG)
        self.session = session

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.session._append_text(
                self.session.client_log, self.format(record) + "\n"
            )
        except Exception:
            self.handleError(record)


@dataclass
class DiagnosticSession:
    """Three support-facing artifacts produced during one client run."""

    session_id: str
    client_log: Path
    opengoal_log: Path
    events_log: Path
    policy: DiagnosticPolicy = field(default_factory=DiagnosticPolicy)
    storage_mode: str = "primary"
    _write_lock: threading.RLock = field(
        default_factory=threading.RLock, compare=False, repr=False
    )
    _event_sequence: int = field(default=0, init=False, repr=False)
    _source_sequences: dict[str, int] = field(
        default_factory=dict, init=False, repr=False
    )
    _last_goal_sequence: int = field(default=-1, init=False, repr=False)
    _last_goal_duplicate_sequence: int = field(default=-1, init=False, repr=False)
    _goal_source_generation: int = field(default=0, init=False, repr=False)
    _providers: dict[str, Callable[[], object]] = field(
        default_factory=dict, init=False, repr=False
    )
    _writer_failed: bool = field(default=False, init=False, repr=False)
    _rejected_count: int = field(default=0, init=False, repr=False)
    _suppressed_count: int = field(default=0, init=False, repr=False)
    _capture_gaps: list[dict[str, object]] = field(
        default_factory=list, init=False, repr=False
    )
    _closed: bool = field(default=False, init=False, repr=False)
    _old_sys_hook: Any = field(default=None, init=False, repr=False)
    _old_thread_hook: Any = field(default=None, init=False, repr=False)
    _installed_sys_hook: Any = field(default=None, init=False, repr=False)
    _installed_thread_hook: Any = field(default=None, init=False, repr=False)
    _exception_fingerprints: set[str] = field(
        default_factory=set, init=False, repr=False
    )
    _logger_handler: logging.Handler | None = field(
        default=None, init=False, repr=False
    )
    _loop_exception_handlers: dict[
        asyncio.AbstractEventLoop,
        tuple[
            Callable[[asyncio.AbstractEventLoop, dict[str, Any]], object] | None,
            Callable[[asyncio.AbstractEventLoop, dict[str, Any]], None],
        ],
    ] = field(default_factory=dict, init=False, repr=False)
    _reporting_rotation: bool = field(default=False, init=False, repr=False)
    _reporting_writer_failure: bool = field(default=False, init=False, repr=False)
    _export_lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False
    )
    _protected_exports: set[Path] = field(default_factory=set, init=False, repr=False)
    _artifact_history: dict[str, list[Path]] = field(
        default_factory=lambda: {"client": [], "opengoal": [], "events": []},
        init=False,
        repr=False,
    )
    _known_directories: set[Path] = field(default_factory=set, init=False, repr=False)
    _started_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        init=False,
        repr=False,
    )
    _last_marker_refresh: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._providers["capture_gaps"] = self.capture_gap_snapshot

    @classmethod
    def create(
        cls,
        log_directory: Path | None = None,
        session_id: str | None = None,
        *,
        policy: DiagnosticPolicy | None = None,
    ) -> DiagnosticSession:
        selected_policy = policy or DiagnosticPolicy.from_environment()
        selected_policy.validate()
        identifier = session_id or (
            datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f") + f"_{os.getpid()}"
        )
        primary = log_directory or Path(Utils.user_path("logs"))
        candidates = (
            (primary, "primary"),
            (Path(tempfile.gettempdir()) / "Jak3Diagnostics", "temporary"),
        )
        for directory, mode in candidates:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                paths = (
                    directory / f"Jak3Client_{identifier}.txt",
                    directory / f"Jak3OpenGOAL_{identifier}.txt",
                    directory / f"Jak3Events_{identifier}.jsonl",
                )
                for path in paths:
                    path.touch(exist_ok=True)
                session = cls(identifier, *paths, selected_policy, mode)
                session._known_directories.update(path for path, _ in candidates)
                return session
            except OSError:
                continue
        unavailable = Path(tempfile.gettempdir()) / f"Jak3Unavailable_{identifier}"
        session = cls(
            identifier,
            unavailable.with_suffix(".client.txt"),
            unavailable.with_suffix(".opengoal.txt"),
            unavailable.with_suffix(".events.jsonl"),
            selected_policy,
            "console",
        )
        session._known_directories.update(path for path, _ in candidates)
        return session

    @property
    def directory(self) -> Path:
        return self.events_log.parent

    @property
    def marker_path(self) -> Path:
        return self.directory / f".Jak3Session_{self.session_id}.json"

    @staticmethod
    def _capacity_lock_path() -> Path:
        return (
            Path(tempfile.gettempdir())
            / "Jak3Diagnostics"
            / ".Jak3DiagnosticsCapacity.lock"
        )

    def initialize(self) -> None:
        """Configure paired logs, marker, retention, and exception capture."""

        self._install_logging()
        try:
            # Publish this session's full reservation before any other process
            # can make a capacity decision that omits it.
            with self._write_lock:
                with interprocess_directory_lock(self._capacity_lock_path()):
                    if not self._write_marker(clean=False, active=True):
                        raise OSError(
                            "Unable to publish the diagnostic capacity lease."
                        )
        except OSError as exc:
            self._emergency(f"diagnostic capacity reservation failed: {exc}")
            self._activate_fallback(self.events_log)
        self._report_prior_markers()
        self._cleanup_orphaned_support_temps()
        metadata = _world_metadata()
        common = [
            "Jak 3 Archipelago diagnostic session",
            f"session_id={self.session_id}",
            f"created_utc={datetime.now(UTC).isoformat()}",
            f"apworld_version={metadata.get('world_version', 'unknown')}",
            f"archipelago_version={getattr(Utils, '__version__', 'unknown')}",
            f"python={platform.python_version()} frozen={bool(getattr(sys, 'frozen', False))}",
            f"platform={platform.platform()}",
            f"storage_mode={self.storage_mode}",
            f"client_log={self.client_log.name}",
            f"opengoal_log={self.opengoal_log.name}",
            f"events_log={self.events_log.name}",
        ]
        self._append_text(
            self.opengoal_log,
            "=== "
            + common[0]
            + " ===\n"
            + "\n".join(common[1:])
            + "\noutput_encoding=UTF-8; ANSI control sequences stripped by collector\n"
            + "This file combines [GK], [GOALC], [JAK3-AP], and [CLIENT] events.\n\n",
        )
        logger = logging.getLogger("Client")
        logger.info("=== %s ===", common[0])
        for line in common[1:]:
            logger.info("DIAGNOSTIC %s", line)
        self.emit(
            "diagnostics.session.started",
            message="Diagnostic session initialized.",
            context={"mode": self.storage_mode},
        )
        self.install_exception_capture()
        over_capacity = self.storage_mode == "console"
        if not over_capacity:
            try:
                with self._write_lock:
                    with interprocess_directory_lock(self._capacity_lock_path()):
                        self.refresh_session_marker(force=True)
                        reserved_growth = self._live_reserved_growth()
                        self._prune_retention(reserved_bytes=reserved_growth)
                        over_capacity = (
                            self._managed_usage_bytes() + reserved_growth
                            > self.policy.managed_bytes
                        )
                        if over_capacity:
                            self._write_marker(clean=True, active=False)
            except OSError as exc:
                self._emergency(f"diagnostic capacity check failed: {exc}")
                over_capacity = True
                self._write_marker(clean=True, active=False)
        if over_capacity:
            self._emergency(
                "file diagnostics disabled because live-session reservations "
                "exceed the managed cap"
            )
            self.storage_mode = "console"

    def _install_logging(self) -> None:
        try:
            root = logging.getLogger()
            for handler in tuple(root.handlers):
                root.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
            root.setLevel(logging.INFO)
            logging.getLogger("websockets").setLevel(logging.INFO)
            if sys.stdout is not None:
                stream_handler = logging.StreamHandler(sys.stdout)
                stream_handler.addFilter(_RoutingFilter("NoStream"))
                stream_handler.addFilter(_RedactingFilter())
                root.addHandler(stream_handler)
            if self.storage_mode != "console":
                handler = _ClientDiagnosticHandler(self)
                handler.setFormatter(logging.Formatter(CLIENT_LOG_FORMAT))
                handler.addFilter(
                    _RoutingFilter("NoFile", exclude_carriage_return=True)
                )
                handler.addFilter(_RedactingFilter())
                root.addHandler(handler)
                self._logger_handler = handler
            logging.getLogger("Client").setLevel(logging.DEBUG)
            logging.captureWarnings(True)
        except Exception as exc:
            self._emergency(f"diagnostic client-log handler failed: {exc}")

    def event_sink(self, event_name: str, **fields: object) -> None:
        """Dependency-injection adapter used by persistence and protocol code."""

        try:
            allowed = {
                "message",
                "severity",
                "source_component",
                "source_sequence",
                "source_monotonic_or_game_tick",
                "correlation_id",
                "runtime_state_sequence",
                "persistent_state_revision",
                "context",
                "details",
            }
            self.emit(
                event_name,
                **cast(
                    Any,
                    {key: value for key, value in fields.items() if key in allowed},
                ),
            )
        except BaseException as exc:
            self._emergency(f"event sink failed: {exc}")

    def emit(
        self,
        event_name: str,
        *,
        message: object = "",
        severity: str | None = None,
        source_component: str = "python",
        source_sequence: int | None = None,
        source_monotonic_or_game_tick: int | None = None,
        correlation_id: object | None = None,
        runtime_state_sequence: int | None = None,
        persistent_state_revision: int | None = None,
        context: Mapping[str, object] | None = None,
        details: Mapping[str, object] | None = None,
    ) -> bool:
        """Append one registered, allowlisted schema-v1 event without raising."""

        try:
            definition = EVENT_REGISTRY[event_name]
            selected_severity = severity or definition.default_severity
            if selected_severity not in {
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR",
                "CRITICAL",
            }:
                raise ValueError("Invalid diagnostic severity")
            clean_context = self._allowlisted(
                context,
                definition.context_fields,
                definition.context_object_fields,
            )
            clean_details = self._allowlisted(details, definition.detail_fields)
            with self._write_lock:
                self._event_sequence += 1
                if source_sequence is None:
                    source_sequence = (
                        self._source_sequences.get(source_component, 0) + 1
                    )
                    self._source_sequences[source_component] = source_sequence
                else:
                    if type(source_sequence) is not int or source_sequence < 0:
                        raise ValueError(
                            "Diagnostic source sequence must be a non-negative integer"
                        )
                    self._source_sequences[source_component] = max(
                        self._source_sequences.get(source_component, 0),
                        source_sequence,
                    )
                envelope = {
                    "diagnostic_schema_version": DIAGNOSTIC_SCHEMA_VERSION,
                    "event_sequence": self._event_sequence,
                    "observed_utc": datetime.now(UTC)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                    "source_component": _normalize_text(source_component, limit=64),
                    "source_sequence": source_sequence,
                    "source_monotonic_or_game_tick": source_monotonic_or_game_tick,
                    "severity": selected_severity,
                    "event_name": event_name,
                    "message": _normalize_text(message),
                    "session_id": self.session_id,
                    "correlation_id": None
                    if correlation_id is None
                    else _normalize_text(correlation_id, limit=128),
                    "process_id": os.getpid(),
                    "thread_or_task": self._thread_or_task(),
                    "protocol_version": PROTOCOL_VERSION,
                    "game_integration_version": GAME_INTEGRATION_VERSION,
                    "runtime_state_sequence": runtime_state_sequence,
                    "persistent_state_revision": persistent_state_revision,
                    "context": clean_context,
                    "details": clean_details,
                }
                payload, compacted = _bounded_event_payload(
                    envelope, self.policy.segment_bytes
                )
                if compacted:
                    self._rejected_count += 1
                written = self._append_bytes(self.events_log, payload)
                if written and event_name in {
                    "diagnostics.capture_gap",
                    "process.capture_gap",
                }:
                    component = clean_context.get("process", source_component)
                    if event_name == "process.capture_gap":
                        reason = clean_context.get(
                            "capture", clean_context.get("reason", event_name)
                        )
                    else:
                        reason = clean_context.get(
                            "reason", clean_context.get("capture", event_name)
                        )
                    self._capture_gaps.append(
                        {
                            "component": _normalize_text(component, limit=64),
                            "reason": _normalize_text(reason, limit=128),
                        }
                    )
                    del self._capture_gaps[:-64]
                if written:
                    self.refresh_session_marker()
                return written
        except Exception as exc:
            self._rejected_count += 1
            self._emergency(f"diagnostic event rejected ({event_name!r}): {exc}")
            if event_name != "diagnostics.event.rejected":
                self.emit(
                    "diagnostics.event.rejected",
                    message="A malformed or unregistered diagnostic event was rejected.",
                    context={"reason": type(exc).__name__, "source": source_component},
                    details={"count": self._rejected_count},
                )
            return False

    @staticmethod
    def _allowlisted(
        values: Mapping[str, object] | None,
        allowed: frozenset[str],
        object_fields: Mapping[str, frozenset[str]] | None = None,
    ) -> dict[str, object]:
        return _allowlisted_mapping(values, allowed, object_fields)

    @staticmethod
    def _thread_or_task() -> str:
        thread = threading.current_thread().name
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        return _normalize_text(task.get_name() if task else thread, limit=96)

    def note_opengoal(self, source: str, message: str) -> None:
        timestamp = (
            datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )
        clean = _normalize_text(message).replace("\n", "\\n")
        self._append_text(
            self.opengoal_log,
            f"[{timestamp}] [{_normalize_text(source, limit=32)}] {clean}\n",
        )

    def append_process_output(self, source: str, output: str) -> None:
        clean = _normalize_text(output, limit=max(4096, len(output) * 2))
        if not clean:
            return
        rendered = "".join(
            f"[{_normalize_text(source, limit=32)}] {line}\n"
            for line in clean.splitlines()
        )
        self._append_text(self.opengoal_log, rendered)

    def _append_text(self, path: Path, value: str) -> bool:
        # Four bytes per Unicode code point keeps each serialized chunk within
        # one configured segment without splitting UTF-8 sequences.
        chunk_characters = max(1, self.policy.segment_bytes // 4)
        written = True
        for offset in range(0, len(value), chunk_characters):
            written = (
                self._append_bytes(
                    path,
                    value[offset : offset + chunk_characters].encode(
                        "utf-8", errors="replace"
                    ),
                )
                and written
            )
        return written

    def _append_bytes(self, path: Path, payload: bytes) -> bool:
        if self.storage_mode == "console":
            self._emergency(payload.decode("utf-8", errors="replace").rstrip())
            return False
        try:
            with self._write_lock:
                rotated = False
                if (
                    path.is_file()
                    and path.stat().st_size + len(payload) > self.policy.segment_bytes
                ):
                    self._rotate(path)
                    rotated = True
                with path.open("ab") as stream:
                    stream.write(payload)
                    stream.flush()
                recovered = self._writer_failed
                self._writer_failed = False
                if rotated and not self._reporting_rotation:
                    self._reporting_rotation = True
                    try:
                        self.emit(
                            "diagnostics.rotation.completed",
                            message="Diagnostic artifact segment rotated.",
                            context={"artifact": path.name},
                        )
                    finally:
                        self._reporting_rotation = False
                if recovered and not self._reporting_writer_failure:
                    self._reporting_writer_failure = True
                    try:
                        self.emit(
                            "diagnostics.writer.failed",
                            message="Diagnostic writer recovered after an earlier failure.",
                            context={"artifact": path.name, "status": "recovered"},
                        )
                    finally:
                        self._reporting_writer_failure = False
            return True
        except Exception as exc:
            if not self._writer_failed:
                self._writer_failed = True
                self._emergency(f"diagnostic writer disabled after failure: {exc}")
            fallback_path = self._activate_fallback(path)
            if fallback_path is not None:
                return self._append_bytes(fallback_path, payload)
            return False

    def _activate_fallback(self, failed_path: Path) -> Path | None:
        if self.storage_mode == "console":
            return None
        if self.storage_mode == "temporary":
            self.storage_mode = "console"
            return None
        try:
            directory = Path(tempfile.gettempdir()) / "Jak3Diagnostics"
            directory.mkdir(parents=True, exist_ok=True)
            with self._write_lock:
                with interprocess_directory_lock(self._capacity_lock_path()):
                    self._known_directories.add(directory)
                    old_paths = (self.client_log, self.opengoal_log, self.events_log)
                    old_marker = self.marker_path
                    new_paths = (
                        directory / f"Jak3Client_{self.session_id}.txt",
                        directory / f"Jak3OpenGOAL_{self.session_id}.txt",
                        directory / f"Jak3Events_{self.session_id}.jsonl",
                    )
                    for selected in new_paths:
                        selected.touch(exist_ok=True)
                    mapping = dict(zip(old_paths, new_paths, strict=True))
                    for label, old_path, new_path in zip(
                        ("client", "opengoal", "events"),
                        old_paths,
                        new_paths,
                        strict=True,
                    ):
                        if old_path != new_path:
                            self._artifact_history[label].append(old_path)
                    self.client_log, self.opengoal_log, self.events_log = new_paths
                    self.storage_mode = "temporary"
                    if not self._write_marker(clean=False, active=True):
                        raise OSError(
                            "Unable to publish the temporary diagnostic capacity lease."
                        )
                    if old_marker != self.marker_path and self.marker_path.is_file():
                        try:
                            old_marker.unlink(missing_ok=True)
                        except OSError:
                            pass
                    reserved_growth = self._live_reserved_growth()
                    self._prune_retention(reserved_bytes=reserved_growth)
                    if (
                        self._managed_usage_bytes() + reserved_growth
                        > self.policy.managed_bytes
                    ):
                        self._write_marker(clean=True, active=False)
                        self.storage_mode = "console"
                        self._emergency(
                            "temporary diagnostics disabled because the managed cap "
                            "cannot preserve both current-session storage generations"
                        )
                        return None
            self._emergency(f"diagnostics fell back to temporary storage: {directory}")
            return mapping.get(failed_path, self.events_log)
        except OSError as exc:
            self.storage_mode = "console"
            self._emergency(f"temporary diagnostic fallback failed: {exc}")
            return None

    def _rotate(self, path: Path) -> None:
        for index in range(self.policy.backups_per_artifact, 0, -1):
            destination = Path(f"{path}.{index}")
            if index == self.policy.backups_per_artifact:
                destination.unlink(missing_ok=True)
            source = path if index == 1 else Path(f"{path}.{index - 1}")
            if source.exists():
                os.replace(source, destination)
        path.touch()

    def ingest_goal_events(
        self,
        records: tuple[GoalDiagnosticRecord, ...],
        *,
        dropped_count: int = 0,
        record_context: Mapping[int, Mapping[str, object]] | None = None,
    ) -> int | None:
        """Drain idempotently ordered GOAL ring records into the Python timeline."""

        accepted = 0
        highest: int | None = None
        if dropped_count:
            self.emit(
                "diagnostics.goal.overflow",
                message="GOAL diagnostic ring dropped its oldest records.",
                source_component="python",
                context={"dropped_count": dropped_count},
            )
        for record in sorted(records, key=lambda item: item.source_sequence):
            if record.source_sequence <= self._last_goal_sequence:
                if record.source_sequence > self._last_goal_duplicate_sequence:
                    self.emit(
                        "diagnostics.goal.duplicate",
                        message="Duplicate GOAL diagnostic record ignored.",
                        source_component="python",
                        context={"source_sequence": record.source_sequence},
                    )
                    self._last_goal_duplicate_sequence = record.source_sequence
                else:
                    self._suppressed_count += 1
                highest = (
                    record.source_sequence
                    if highest is None
                    else max(highest, record.source_sequence)
                )
                continue
            if (
                self._last_goal_sequence >= 0
                and record.source_sequence > self._last_goal_sequence + 1
            ):
                self.emit(
                    "diagnostics.goal.gap",
                    message="GOAL diagnostic source sequence gap detected.",
                    context={
                        "gap_start": self._last_goal_sequence + 1,
                        "gap_end": record.source_sequence - 1,
                    },
                )
            definition = GOAL_EVENT_REGISTRY.get(record.event_code)
            if definition is None:
                written = self.emit(
                    "diagnostics.event.rejected",
                    message="Unknown GOAL diagnostic event code ignored.",
                    context={
                        "reason": "unknown_goal_code",
                        "source_sequence": record.source_sequence,
                    },
                )
                if not written:
                    break
                self._last_goal_sequence = record.source_sequence
                highest = record.source_sequence
                accepted += 1
                continue
            severity = {
                0: "DEBUG",
                1: "INFO",
                2: "WARNING",
                3: "ERROR",
                4: "CRITICAL",
            }.get(record.severity)
            if severity is None:
                severity = definition.default_severity
            correlation, correlation_context = _goal_correlation(
                record.correlation_kind, record.correlation_value
            )
            goal_context: dict[str, object] = {
                "source_sequence": record.source_sequence,
                "source_generation": self._goal_source_generation,
                "game_tick": record.game_tick,
                "result": record.result,
                "error_code": record.error,
                **correlation_context,
            }
            if record_context is not None:
                goal_context.update(record_context.get(record.source_sequence, {}))
            written = self.emit(
                definition.name,
                message="GOAL bridge event.",
                severity=severity,
                source_component="goal",
                source_sequence=record.source_sequence,
                source_monotonic_or_game_tick=record.game_tick,
                correlation_id=correlation,
                context=goal_context,
                details={"new": [record.arg0, record.arg1, record.arg2]},
            )
            if not written:
                break
            self._last_goal_sequence = record.source_sequence
            highest = record.source_sequence
            accepted += 1
        if accepted:
            self.emit(
                "diagnostics.goal.drain.completed",
                message="GOAL diagnostic records drained.",
                details={"count": accepted},
            )
        return highest

    def capture_gap_snapshot(self) -> tuple[dict[str, object], ...]:
        """Return the bounded authoritative capture-gap support summary."""

        with self._write_lock:
            return tuple(dict(gap) for gap in self._capture_gaps[-64:])

    def reset_goal_event_source(self) -> None:
        """Start a new GOAL sequence generation after an intentional reload."""

        with self._write_lock:
            self._last_goal_sequence = -1
            self._last_goal_duplicate_sequence = -1
            self._goal_source_generation += 1

    def register_context_provider(
        self, name: str, provider: Callable[[], object]
    ) -> None:
        if name not in {
            "runtime",
            "persistence",
            "versions",
            "commands",
            "capture_gaps",
        }:
            raise ValueError(f"Unsupported diagnostic context provider: {name}")
        self._providers[name] = provider

    @staticmethod
    def _sanitize_provider_payload(name: str, payload: object) -> object:
        """Validate one support snapshot against its explicit schema."""

        def scalar(value: object) -> object:
            if value is None or isinstance(value, (bool, int, float, str)):
                return _safe_value(value)
            raise TypeError("Support snapshot fields must be scalar values")

        if name == "capture_gaps":
            if not isinstance(payload, (list, tuple)):
                raise TypeError("capture_gaps provider must return a list")
            sanitized_gaps: list[dict[str, object]] = []
            for item in payload[:64]:
                if not isinstance(item, Mapping):
                    raise TypeError("capture gap entries must be mappings")
                unexpected = set(item) - _PROVIDER_CAPTURE_GAP_FIELDS
                if unexpected:
                    raise ValueError(
                        f"Capture gap fields are not allowlisted: {sorted(unexpected)}"
                    )
                sanitized_gaps.append(
                    {key: scalar(value) for key, value in item.items()}
                )
            return sanitized_gaps
        if not isinstance(payload, Mapping):
            raise TypeError(f"{name} provider must return a mapping")
        allowed = _PROVIDER_FIELDS[name]
        unexpected = set(payload) - allowed
        if unexpected:
            raise ValueError(
                f"{name} provider fields are not allowlisted: {sorted(unexpected)}"
            )
        sanitized = (
            {}
            if name == "commands"
            else {key: scalar(value) for key, value in payload.items()}
        )
        if name == "commands" and "recent" in payload:
            recent = payload["recent"]
            if not isinstance(recent, (list, tuple)):
                raise TypeError("commands.recent must be a list")
            sanitized_recent: list[dict[str, object]] = []
            for item in recent[:64]:
                if not isinstance(item, Mapping):
                    raise TypeError("recent command entries must be mappings")
                unexpected = set(item) - _PROVIDER_COMMAND_FIELDS
                if unexpected:
                    raise ValueError(
                        "Recent command fields are not allowlisted: "
                        f"{sorted(unexpected)}"
                    )
                sanitized_recent.append(
                    {key: scalar(value) for key, value in item.items()}
                )
            sanitized["recent"] = sanitized_recent
        return sanitized

    def install_exception_capture(
        self, loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        if self._old_sys_hook is None:
            self._old_sys_hook = sys.excepthook

            def sys_hook(
                exc_type: type[BaseException], exc: BaseException, tb: Any
            ) -> None:
                self.capture_exception("main", exc, tb)
                if self._old_sys_hook:
                    self._old_sys_hook(exc_type, exc, tb)

            sys.excepthook = sys_hook
            self._installed_sys_hook = sys_hook
        if hasattr(threading, "excepthook") and self._old_thread_hook is None:
            self._old_thread_hook = threading.excepthook

            def thread_hook(args: threading.ExceptHookArgs) -> None:
                exception = args.exc_value or RuntimeError(
                    "Background thread failed without an exception value."
                )
                self.capture_exception("thread", exception, args.exc_traceback)
                if self._old_thread_hook:
                    self._old_thread_hook(args)

            threading.excepthook = thread_hook
            self._installed_thread_hook = thread_hook
        if loop is not None and loop not in self._loop_exception_handlers:
            old_handler = loop.get_exception_handler()

            def asyncio_handler(
                selected_loop: asyncio.AbstractEventLoop, context: dict[str, Any]
            ) -> None:
                exception = context.get("exception") or RuntimeError(
                    str(context.get("message", "asyncio task failed"))
                )
                self.capture_exception("asyncio", exception, exception.__traceback__)
                if old_handler:
                    old_handler(selected_loop, context)
                else:
                    selected_loop.default_exception_handler(context)

            loop.set_exception_handler(asyncio_handler)
            self._loop_exception_handlers[loop] = (old_handler, asyncio_handler)

    def capture_exception(
        self, source: str, exception: BaseException, tb: Any = None
    ) -> None:
        kind = source if source in {"main", "asyncio", "thread"} else "thread"
        rendered = "".join(
            traceback.format_exception(
                type(exception), exception, tb or exception.__traceback__
            )
        )
        fingerprint = hash_identifier(f"{type(exception).__name__}:{rendered[-2048:]}")
        if fingerprint in self._exception_fingerprints:
            return
        self._exception_fingerprints.add(fingerprint)
        self.emit(
            f"diagnostics.exception.{kind}",
            message=str(exception),
            context={
                "exception_type": type(exception).__name__,
                "fingerprint": fingerprint,
                "source": source,
            },
            details={"exception": _normalize_text(rendered, limit=8192)},
        )

    def export_bundle(self, *, _fallback_attempted: bool = False) -> BundleExportResult:
        """Write a local sanitized ZIP containing only allowlisted artifacts."""

        with self._export_lock:
            return self._export_bundle_locked(_fallback_attempted=_fallback_attempted)

    def _export_bundle_locked(self, *, _fallback_attempted: bool) -> BundleExportResult:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        filename = f"Jak3Support_{self.session_id}_{timestamp}.zip"
        missing: list[str] = []
        truncated: list[str] = []
        output: Path | None = None
        temporary: Path | None = None
        try:
            with self._write_lock:
                pre_export_events = self._merged_events([])
                self.emit(
                    "diagnostics.bundle.export.started",
                    message="Support bundle export started.",
                    context={"bundle_path": filename},
                )
            # The start event itself can trigger the primary-to-temporary
            # fallback. Resolve the archive path after that write completes.
            output = self.directory / filename
            temporary = output.with_suffix(".zip.tmp")
            provider_payloads: dict[str, bytes] = {}
            for name in (
                "runtime",
                "persistence",
                "versions",
                "commands",
                "capture_gaps",
            ):
                provider = self._providers.get(name)
                if provider is None:
                    missing.append(f"{name}.json")
                    continue
                try:
                    safe = self._sanitize_provider_payload(name, provider())
                    provider_payloads[f"{name}.json"] = (
                        json.dumps(
                            safe, ensure_ascii=False, indent=2, sort_keys=True
                        ).encode("utf-8")
                        + b"\n"
                    )
                except Exception:
                    missing.append(f"{name}.json")
            # Snapshot every support-facing segment under the writer lock so a
            # concurrent rotation cannot rename files between reads. Provider
            # callbacks run above the lock because they may consult other
            # independently synchronized subsystems.
            with self._write_lock:
                event_payload = self._combine_event_payloads(
                    pre_export_events, self._merged_events([])
                )
                if not event_payload:
                    missing.append("events.jsonl")
                entries: dict[str, bytes] = {
                    "events.jsonl": event_payload,
                    **provider_payloads,
                }
                for archive_name, label, path in (
                    ("client.txt", "client", self.client_log),
                    ("opengoal.txt", "opengoal", self.opengoal_log),
                ):
                    merged = self._merged_text(label, path)
                    if merged is None:
                        missing.append(archive_name)
                    else:
                        payload, was_truncated = merged
                        entries[archive_name] = payload
                        if was_truncated:
                            truncated.append(archive_name)
                status = "partial" if missing or truncated else "complete"
                entries["README.txt"] = self._bundle_readme(missing, truncated).encode(
                    "utf-8"
                )
                manifest = {
                    "bundle_manifest_version": BUNDLE_MANIFEST_VERSION,
                    "diagnostic_schema_version": DIAGNOSTIC_SCHEMA_VERSION,
                    "status": status,
                    "created_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "session_id_hash": hash_identifier(self.session_id),
                    "redaction": "field-allowlist-v1",
                    "missing": sorted(set(missing)),
                    "truncated": sorted(set(truncated)),
                    "artifacts": {
                        name: {
                            "sha256": hashlib.sha256(payload).hexdigest(),
                            "bytes": len(payload),
                        }
                        for name, payload in sorted(entries.items())
                    },
                }
                entries["manifest.json"] = (
                    json.dumps(
                        manifest, ensure_ascii=False, indent=2, sort_keys=True
                    ).encode("utf-8")
                    + b"\n"
                )
            # ZIP temporary creation, capacity reservation, and publication are
            # one cross-process transaction. Temporary archives are deliberately
            # not managed artifacts, so checking without this lock would allow
            # two clients to overcommit the hard byte cap concurrently.
            self.refresh_session_marker(force=True)
            pruned = 0
            with interprocess_directory_lock(self._capacity_lock_path()):
                with zipfile.ZipFile(
                    temporary, "w", compression=zipfile.ZIP_DEFLATED
                ) as archive:
                    for name, payload in sorted(entries.items()):
                        archive.writestr(name, payload)
                reserved_bytes = temporary.stat().st_size + self._live_reserved_growth()
                pruned = self._prune_retention(
                    reserved_bytes=reserved_bytes, report=False
                )
                if (
                    self._managed_usage_bytes() + reserved_bytes
                    > self.policy.managed_bytes
                ):
                    raise ValueError(
                        "The managed diagnostic capacity cannot retain another "
                        "support bundle while preserving the current session."
                    )
                os.replace(temporary, output)
            with self._write_lock:
                self._protected_exports.add(output)
            if pruned:
                self.emit(
                    "diagnostics.retention.completed",
                    message="Old managed diagnostic artifacts pruned.",
                    details={"count": pruned},
                )
            event_name = (
                "diagnostics.bundle.export.partial"
                if status == "partial"
                else "diagnostics.bundle.export.completed"
            )
            self.emit(
                event_name,
                message=f"Support bundle export {status}.",
                context={"bundle_path": output.name, "status": status},
                details={"missing": missing, "truncated": truncated},
            )
            return BundleExportResult(
                status,
                output,
                tuple(sorted(set(missing))),
                truncated=tuple(sorted(set(truncated))),
            )
        except Exception as exc:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            if (
                isinstance(exc, OSError)
                and not _fallback_attempted
                and self.storage_mode == "primary"
                and self._activate_fallback(self.events_log) is not None
            ):
                return self._export_bundle_locked(_fallback_attempted=True)
            self.emit(
                "diagnostics.bundle.export.failed",
                message="Support bundle export failed.",
                context={
                    "bundle_path": output.name if output is not None else filename,
                    "reason": type(exc).__name__,
                },
            )
            self._emergency(f"support bundle export failed: {exc}")
            return BundleExportResult(
                "failed",
                None,
                tuple(sorted(set(missing))),
                _normalize_text(exc),
                tuple(sorted(set(truncated))),
            )

    def _bundle_readme(self, missing: list[str], truncated: list[str]) -> str:
        declared_missing = sorted(set(missing))
        declared_truncated = sorted(set(truncated))
        return (
            "Jak 3 Archipelago local support bundle\n\n"
            "This archive was sanitized with the diagnostic schema v1 field allowlist.\n"
            "It contains no native save, AP persistence sidecar, memory dump, password, token, or raw packet.\n"
            "Missing optional artifacts: "
            f"{', '.join(declared_missing) if declared_missing else 'none'}\n"
            "Artifacts retaining only their newest sanitized content: "
            f"{', '.join(declared_truncated) if declared_truncated else 'none'}\n"
        )

    def _segments(self, path: Path) -> list[Path]:
        backups = [
            Path(f"{path}.{index}")
            for index in range(self.policy.backups_per_artifact, 0, -1)
            if Path(f"{path}.{index}").is_file()
        ]
        return backups + ([path] if path.is_file() else [])

    def _artifact_bases(self, label: str, current: Path) -> tuple[Path, ...]:
        return tuple(self._artifact_history[label]) + (current,)

    def _merged_events(self, missing: list[str]) -> bytes:
        events: list[dict[str, object]] = []
        for base in self._artifact_bases("events", self.events_log):
            for segment in self._segments(base):
                try:
                    with segment.open("r", encoding="utf-8") as stream:
                        for line in stream:
                            try:
                                events.append(
                                    _validated_event_envelope(json.loads(line))
                                )
                            except (
                                json.JSONDecodeError,
                                RecursionError,
                                TypeError,
                                ValueError,
                            ):
                                continue
                except OSError:
                    continue
        if not events:
            missing.append("events.jsonl")
            return b""
        events.sort(key=lambda item: cast(int, item["event_sequence"]))
        return b"".join(
            json.dumps(
                _safe_value(event),
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
            for event in events
        )

    @staticmethod
    def _combine_event_payloads(*payloads: bytes) -> bytes:
        events: dict[int, dict[str, object]] = {}
        for payload in payloads:
            for line in payload.splitlines():
                try:
                    event = _validated_event_envelope(json.loads(line))
                except (
                    json.JSONDecodeError,
                    RecursionError,
                    TypeError,
                    ValueError,
                ):
                    continue
                events[cast(int, event["event_sequence"])] = event
        return b"".join(
            json.dumps(
                _safe_value(events[sequence]),
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
            for sequence in sorted(events)
        )

    def _merged_text(self, label: str, path: Path) -> tuple[bytes, bool] | None:
        segments = [
            segment
            for base in self._artifact_bases(label, path)
            for segment in self._segments(base)
        ]
        if not segments:
            return None
        chunks: list[str] = []
        for segment in segments:
            try:
                chunks.append(segment.read_text("utf-8", errors="replace"))
            except OSError:
                continue
        if not chunks:
            return None
        clean = _normalize_text("".join(chunks), limit=None)
        truncated = len(clean) > MAX_BUNDLE_TEXT_CHARS
        if truncated:
            retained = max(0, MAX_BUNDLE_TEXT_CHARS - len(TRUNCATED_LOG_NOTICE))
            clean = TRUNCATED_LOG_NOTICE + (clean[-retained:] if retained else "")
        return clean.encode("utf-8"), truncated

    @staticmethod
    def _marker_session_id(marker: Path) -> str | None:
        prefix = ".Jak3Session_"
        suffix = ".json"
        if not marker.name.startswith(prefix) or not marker.name.endswith(suffix):
            return None
        session_id = marker.name[len(prefix) : -len(suffix)]
        return session_id or None

    @staticmethod
    def _marker_is_live(payload: Mapping[str, object]) -> bool:
        if payload.get("clean") is True or payload.get("active") is not True:
            return False
        process_id = payload.get("process_id")
        host_hash = payload.get("host_hash")
        if type(process_id) is not int or not isinstance(host_hash, str):
            return False
        last_seen_value = payload.get("last_seen_utc")
        if not isinstance(last_seen_value, str):
            return False
        try:
            last_seen = datetime.fromisoformat(last_seen_value.replace("Z", "+00:00"))
            if last_seen.tzinfo is None:
                return False
            age = datetime.now(UTC) - last_seen.astimezone(UTC)
        except (OverflowError, ValueError):
            return False
        lease = timedelta(seconds=SESSION_MARKER_LEASE_SECONDS)
        if not -lease <= age <= lease:
            return False
        current_host = hash_identifier(platform.node() or "local-host")
        if host_hash != current_host:
            # A shared/network log directory cannot inspect the remote PID.
            # Use the writer-renewed lease so a remote crash cannot protect
            # artifacts from age/byte retention forever.
            return True
        # Requiring the lease as well as PID liveness prevents an unrelated
        # process that later reuses a crashed client's PID from protecting that
        # session forever.
        return _process_is_running(process_id)

    def _live_session_markers(self) -> dict[Path, str]:
        live: dict[Path, str] = {}
        for directory in self._managed_directories():
            try:
                markers = directory.glob(".Jak3Session_*.json")
                for marker in markers:
                    session_id = self._marker_session_id(marker)
                    if session_id is None:
                        continue
                    try:
                        payload = json.loads(marker.read_text("utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        continue
                    if isinstance(payload, Mapping) and self._marker_is_live(payload):
                        live[marker] = session_id
            except OSError:
                continue
        return live

    def _write_marker(self, *, clean: bool, active: bool = True) -> bool:
        if self.storage_mode == "console":
            return False
        try:
            reserved_bytes = self._future_active_log_growth() if active else 0
        except OSError:
            reserved_bytes = (
                3 * (self.policy.backups_per_artifact + 1) * self.policy.segment_bytes
                if active
                else 0
            )
        payload = {
            "session_id_hash": hash_identifier(self.session_id),
            "started_utc": self._started_utc,
            "last_seen_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "clean": clean,
            "active": active,
            "process_id": os.getpid(),
            "host_hash": hash_identifier(platform.node() or "local-host"),
            "reserved_bytes": reserved_bytes,
        }
        temporary_path: Path | None = None
        descriptor = -1
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.marker_path.name}.",
                suffix=".tmp",
                dir=self.marker_path.parent,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                json.dump(payload, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.marker_path)
            if active:
                self._last_marker_refresh = monotonic()
            return True
        except OSError as exc:
            self._emergency(f"session marker write failed: {exc}")
            return False
        finally:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def refresh_session_marker(self, *, force: bool = False) -> None:
        """Renew the active marker lease without making diagnostics fallible."""

        if self.storage_mode == "console" or self._closed:
            return
        try:
            with self._write_lock:
                if self._closed:
                    return
                if (
                    not force
                    and monotonic() - self._last_marker_refresh
                    < SESSION_MARKER_REFRESH_SECONDS
                ):
                    return
                self._write_marker(clean=False, active=True)
        except BaseException as exc:
            self._emergency(f"session marker refresh failed: {exc}")

    def _live_reserved_growth(self) -> int:
        """Return conservative remaining log reservations for every live session."""

        total = 0
        current_seen = False
        default_reservation = (
            3 * (self.policy.backups_per_artifact + 1) * self.policy.segment_bytes
        )
        for directory in self._managed_directories():
            try:
                markers = directory.glob(".Jak3Session_*.json")
                for marker in markers:
                    try:
                        payload = json.loads(marker.read_text("utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        continue
                    if not isinstance(payload, Mapping) or not self._marker_is_live(
                        payload
                    ):
                        continue
                    reservation = payload.get("reserved_bytes")
                    if type(reservation) is not int or reservation < 0:
                        reservation = default_reservation
                    total += min(reservation, self.policy.managed_bytes)
                    current_seen = current_seen or marker == self.marker_path
            except OSError:
                continue
        if not current_seen and self.storage_mode != "console":
            total += self._future_active_log_growth()
        return total

    def _report_prior_markers(self) -> None:
        if self.storage_mode == "console":
            return
        markers: list[Path] = []
        for directory in self._managed_directories():
            try:
                markers.extend(directory.glob(".Jak3Session_*.json"))
            except OSError:
                continue
        for marker in sorted(set(markers)):
            if marker == self.marker_path:
                continue
            try:
                payload = json.loads(marker.read_text("utf-8"))
                if isinstance(payload, Mapping) and self._marker_is_live(payload):
                    continue
                clean = payload.get("clean") is True
                self.emit(
                    f"diagnostics.prior_session.{'clean' if clean else 'unclean'}",
                    message="Prior diagnostic session marker observed.",
                    correlation_id=payload.get("session_id_hash"),
                )
                marker.unlink(missing_ok=True)
            except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
                continue

    def _cleanup_orphaned_support_temps(self) -> None:
        """Remove incomplete archives left by an abnormal prior process exit."""

        if self.storage_mode == "console":
            return
        try:
            with interprocess_directory_lock(self._capacity_lock_path()):
                for directory in self._managed_directories():
                    try:
                        for path in directory.iterdir():
                            if path.is_file() and ORPHANED_SUPPORT_TEMP.match(
                                path.name
                            ):
                                path.unlink(missing_ok=True)
                    except OSError as exc:
                        self._emergency(
                            f"orphaned support archive cleanup failed: {exc}"
                        )
        except (OSError, TimeoutError) as exc:
            self._emergency(f"orphaned support archive cleanup lock failed: {exc}")

    @staticmethod
    def _artifact_session_id(path: Path) -> str | None:
        ordinary = re.match(
            r"^Jak3(?:Client|OpenGOAL|Events)_(.+?)\.(?:txt|jsonl)(?:\.[1-9][0-9]*)?$",
            path.name,
        )
        if ordinary:
            return ordinary.group(1)
        support = re.match(r"^Jak3Support_(.+)_\d{8}T\d{12,20}Z\.zip$", path.name)
        return support.group(1) if support else None

    def _protected_artifacts(self) -> set[Path]:
        protected = {
            self.client_log,
            self.opengoal_log,
            self.events_log,
            self.marker_path,
        } | self._protected_exports
        for active_log in (self.client_log, self.opengoal_log, self.events_log):
            protected.update(
                Path(f"{active_log}.{index}")
                for index in range(1, self.policy.backups_per_artifact + 1)
            )
        for label, current_base in (
            ("client", self.client_log),
            ("opengoal", self.opengoal_log),
            ("events", self.events_log),
        ):
            for historical in self._artifact_bases(label, current_base)[:-1]:
                protected.add(historical)
                protected.update(
                    Path(f"{historical}.{index}")
                    for index in range(1, self.policy.backups_per_artifact + 1)
                )
        live_markers = self._live_session_markers()
        protected.update(live_markers)
        live_session_ids = set(live_markers.values())
        if live_session_ids:
            for directory in self._managed_directories():
                try:
                    protected.update(
                        path
                        for path in directory.iterdir()
                        if path.is_file()
                        and self._artifact_session_id(path) in live_session_ids
                    )
                except OSError:
                    continue
        return protected

    def _managed_usage_bytes(self) -> int:
        paths = {path for path in self._protected_artifacts() if path.is_file()}
        for directory in self._managed_directories():
            paths.update(
                path
                for path in directory.iterdir()
                if path.is_file() and MANAGED_ARTIFACT.match(path.name)
            )
        return sum(path.stat().st_size for path in paths)

    def _managed_directories(self) -> set[Path]:
        directories = {
            self.directory,
            *self._known_directories,
            *(
                path.parent
                for paths in self._artifact_history.values()
                for path in paths
            ),
            *(path.parent for path in self._protected_exports),
        }
        return {directory for directory in directories if directory.is_dir()}

    def _future_active_log_growth(self) -> int:
        active_paths = {
            path
            for active_log in (self.client_log, self.opengoal_log, self.events_log)
            for path in (
                active_log,
                *(
                    Path(f"{active_log}.{index}")
                    for index in range(1, self.policy.backups_per_artifact + 1)
                ),
            )
            if path.is_file()
        }
        active_bytes = sum(path.stat().st_size for path in active_paths)
        active_capacity = (
            3 * (self.policy.backups_per_artifact + 1) * self.policy.segment_bytes
        )
        return max(0, active_capacity - active_bytes)

    def _prune_retention(self, *, reserved_bytes: int = 0, report: bool = True) -> int:
        if self.storage_mode == "console":
            return 0
        removed = 0
        protected = self._protected_artifacts()
        # Rotation segments from the active session are part of that session,
        # so neither the age/session policy nor the byte cap may prune them.
        try:
            artifacts = list(
                {
                    path
                    for directory in self._managed_directories()
                    for path in directory.iterdir()
                    if path.is_file()
                    and MANAGED_ARTIFACT.match(path.name)
                    and path not in protected
                }
            )
            cutoff = datetime.now(UTC) - timedelta(days=self.policy.retention_days)
            session_times: dict[str, float] = {}
            for path in artifacts:
                session_id = self._artifact_session_id(path)
                if session_id:
                    session_times[session_id] = max(
                        session_times.get(session_id, 0), path.stat().st_mtime
                    )
            retained_ids = {
                session
                for session, _ in sorted(
                    session_times.items(), key=lambda item: item[1], reverse=True
                )[: self.policy.retained_sessions - 1]
            }
            for path in list(artifacts):
                session_id = self._artifact_session_id(path)
                too_old = datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff
                beyond_sessions = bool(session_id and session_id not in retained_ids)
                if too_old or beyond_sessions:
                    path.unlink(missing_ok=True)
                    artifacts.remove(path)
                    removed += 1
            current_files = [path for path in protected if path.is_file()]
            total = sum(path.stat().st_size for path in artifacts + current_files)
            for path in sorted(artifacts, key=lambda item: item.stat().st_mtime):
                if total + reserved_bytes <= self.policy.managed_bytes:
                    break
                size = path.stat().st_size
                path.unlink(missing_ok=True)
                total -= size
                removed += 1
            if removed and report:
                self.emit(
                    "diagnostics.retention.completed",
                    message="Old managed diagnostic artifacts pruned.",
                    details={"count": removed},
                )
            return removed
        except OSError as exc:
            self._emergency(f"diagnostic retention failed: {exc}")
            return removed

    def flush(self) -> None:
        for handler in logging.getLogger().handlers:
            try:
                handler.flush()
            except Exception:
                pass

    def close(self, *, clean: bool = True) -> None:
        if self._closed:
            return
        suppressed_total = self._rejected_count + self._suppressed_count
        if suppressed_total:
            self.emit(
                "diagnostics.events_dropped_or_suppressed",
                message=(
                    "Oversized, malformed, or repeatedly duplicated diagnostic "
                    "records were suppressed."
                ),
                details={"count": suppressed_total},
            )
        self.emit(
            "diagnostics.session.stopped",
            message="Diagnostic session closed.",
            context={"status": "clean" if clean else "unclean"},
        )
        with self._write_lock:
            self._write_marker(clean=clean, active=False)
            self._closed = True
        self.flush()
        if self._logger_handler is not None:
            root = logging.getLogger()
            root.removeHandler(self._logger_handler)
            try:
                self._logger_handler.close()
            except Exception:
                pass
            self._logger_handler = None
        if (
            self._old_sys_hook is not None
            and sys.excepthook is self._installed_sys_hook
        ):
            sys.excepthook = self._old_sys_hook
        if (
            self._old_thread_hook is not None
            and threading.excepthook is self._installed_thread_hook
        ):
            threading.excepthook = self._old_thread_hook
        for loop, (old_handler, installed_handler) in tuple(
            self._loop_exception_handlers.items()
        ):
            try:
                if (
                    not loop.is_closed()
                    and loop.get_exception_handler() is installed_handler
                ):
                    loop.set_exception_handler(old_handler)
            except Exception:
                pass
        self._loop_exception_handlers.clear()

    @staticmethod
    def _emergency(message: object) -> None:
        try:
            sys.stderr.write(f"[Jak3 diagnostics] {_normalize_text(message)}\n")
            sys.stderr.flush()
        except Exception:
            pass
