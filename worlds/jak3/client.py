"""Archipelago client for the Protocol 3 Jak 3 bridge.

Milestone 9 adds two finite persistent outgoing checks. Goals, reward
suppression, consumables, and mission dispatch remain inactive.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from collections.abc import Awaitable
from dataclasses import replace
from pathlib import Path
from time import monotonic
from typing import Any

import CommonClient as common_client  # type: ignore[import-untyped]
import colorama  # type: ignore[import-untyped]
from CommonClient import ClientCommandProcessor, CommonContext, gui_enabled, server_loop
from NetUtils import encode  # type: ignore[import-untyped]

from .agents.bridge_manifest import load_packaged_manifest
from .agents.diagnostics import (
    GOAL_EVENT_REGISTRY,
    DiagnosticSession,
    GoalDiagnosticRecord,
    hash_identifier,
)
from .agents.launcher import (
    find_install,
    install_packaged_bridge,
    launch_missing_processes,
)
from .agents.protocol import (
    GAME_INTEGRATION_VERSION,
    PING_INTERVAL_SECONDS,
    PROTOCOL_VERSION,
    BridgeProtocol,
    BridgeSnapshot,
    ClientStatus,
    NativeSaveEligibility as SnapshotSaveEligibility,
    ProtocolCommand,
    ProtocolCompatibilityError,
    ProtocolResult,
    goal_path_literal,
    goal_string_literal,
    read_snapshot,
    validate_compatibility,
)
from .agents.repl_client import OpenGoalRepl
from .game_id import GAME_NAME
from .location_outbox import (
    DEBUG_LOCATION_ID,
    LOCATION_OBSERVED_GOAL_CODE,
    LOCATION_RETRY_SECONDS,
    LOCATION_SOURCES,
    LOCATION_TASK_IDS,
    LocationPacketError,
    diagnostic_batch_id,
    observe_local_location,
    parse_server_location_update,
    reconcile_connected,
    reconcile_room_update,
)
from .persistence import (
    AuthenticatedSlot,
    GameCommandReceipt,
    NativeSaveDescriptor,
    NativeSaveEligibility,
    PersistentState,
    StateBindingError,
    StateError,
    StateCompatibilityError,
    StateRepository,
    StateSession,
    default_state_root,
)
from .received_items import (
    PacketOutcome,
    ReceivedItemsPacket,
    ReceivedItemsPacketError,
    apply_received_items_packet,
    mark_pending_items_applied,
    known_jak3_item_name,
    parse_received_items_packet,
    permanent_item_target_mask,
)
from .versions import (
    BRIDGE_RUNTIME_VERSION,
    ITEM_TABLE_VERSION,
    LOCATION_TABLE_VERSION,
    MISSION_TABLE_VERSION,
    SLOT_DATA_VERSION,
    STATE_SCHEMA_VERSION,
)


logger = logging.getLogger("Client")
BACKGROUND_TASKS: set[asyncio.Task] = set()
_PREVALIDATED_RECEIVED_ITEMS_KEY = "__jak3_prevalidated_received_items_packet"
_PREVALIDATED_LOCATION_UPDATE_KEY = "__jak3_prevalidated_location_update"
_COMMONCLIENT_PROCESS_SERVER_CMD = common_client.process_server_cmd
_GOAL_NATIVE_OPERATION_LOAD = 2


async def _jak3_process_server_cmd(ctx: CommonContext, args: dict) -> None:
    """Validate Jak 3 packets before CommonClient mutates local mirrors."""

    if args.get("cmd") in {"Connected", "RoomUpdate"}:
        preprocessor = getattr(ctx, "_preprocess_location_update", None)
        if callable(preprocessor):
            prepared = preprocessor(args)
            if prepared is None:
                return
            args = prepared

    if args.get("cmd") == "ReceivedItems":
        preprocessor = getattr(ctx, "_preprocess_received_items_packet", None)
        if callable(preprocessor):
            prepared = preprocessor(args)
            if prepared is None:
                return
            args = prepared
    await _COMMONCLIENT_PROCESS_SERVER_CMD(ctx, args)


# CommonClient intentionally calls ``on_package`` after its generic packet
# mutation. Install a context-qualified pre-dispatch hook so malformed Jak 3
# packets can be rejected atomically while every other game/context continues
# through the unmodified CommonClient handler.
common_client.process_server_cmd = _jak3_process_server_cmd


def _loaded_bridge_matches_current_contract(snapshot: BridgeSnapshot) -> bool:
    """Preserve a live Protocol 3 control module when its contract matches."""

    try:
        validate_compatibility(snapshot)
    except ProtocolCompatibilityError:
        return False
    return True


def _loaded_diagnostics_matches_current_contract(snapshot: BridgeSnapshot) -> bool:
    """Treat the optional diagnostic channel independently from control state."""

    return (
        not snapshot.diagnostic_malformed
        and snapshot.diagnostic_schema_version == 1
        and snapshot.diagnostic_manifest_version == 1
        and snapshot.diagnostic_activation_generation is not None
        and snapshot.diagnostic_activation_generation >= 1
    )


def create_logged_task(
    awaitable: Awaitable[Any],
    name: str,
    diagnostics: DiagnosticSession | None = None,
) -> asyncio.Task:
    """Run a background action without losing its exception from diagnostics."""

    async def run_and_log() -> Any:
        try:
            return await awaitable
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Background task %s failed.", name)
            if diagnostics is not None:
                diagnostics.capture_exception("asyncio", exc)
            return None
        finally:
            current = asyncio.current_task()
            if current is not None:
                BACKGROUND_TASKS.discard(current)

    task = asyncio.create_task(run_and_log(), name=name)
    BACKGROUND_TASKS.add(task)
    return task


class Jak3CommandProcessor(ClientCommandProcessor):
    ctx: "Jak3Context"

    def _cmd_repl(self, action: str = "status") -> None:
        """Reconnect OpenGOAL (`/repl connect`) or show handshake status."""

        if action.casefold() == "connect":
            self.output("Requesting a fresh Jak 3/OpenGOAL handshake...")
            self.ctx.request_reconnect()
            return
        snapshot = self.ctx.latest_snapshot
        self.output(
            f"Archipelago server: {'connected' if self.ctx.server else 'disconnected'}"
        )
        self.output(
            f"OpenGOAL nREPL: {'connected' if self.ctx.repl.connected else 'disconnected'}"
        )
        self.output(
            f"Game target attached: {'yes' if self.ctx.game_attached else 'no'}"
        )
        self.output(f"AP source loaded: {'yes' if self.ctx.source_loaded else 'no'}")
        self.output(f"Handshake ready: {'yes' if self.ctx.bridge_ready else 'no'}")
        self.output(
            f"Expected protocol/integration: {PROTOCOL_VERSION}/{GAME_INTEGRATION_VERSION}"
        )
        self.output(
            "Data contract: "
            f"slot={SLOT_DATA_VERSION} state={STATE_SCHEMA_VERSION} "
            f"tables={ITEM_TABLE_VERSION}/{LOCATION_TABLE_VERSION}/{MISSION_TABLE_VERSION}"
        )
        if snapshot is not None:
            self.output(
                "Game protocol/integration: "
                f"{snapshot.protocol_version}/{snapshot.game_integration_version}"
            )
            self.output(f"Session: {snapshot.session_id}")
            self.output(
                f"Heartbeat: client {snapshot.client_heartbeat}, game {snapshot.game_heartbeat}"
            )
            self.output(
                "Last command/result: "
                f"{snapshot.last_command.name.lower()}/{snapshot.last_result.name.lower()} "
                f"({snapshot.message})"
            )
        else:
            self.output(f"Session: {self.ctx.diagnostics.session_id}")
        if self.ctx.last_bridge_error:
            self.output(f"Last bridge error: {self.ctx.last_bridge_error}")
        self.output(f"Temporary bridge snapshot: {self.ctx.state_path}")
        self.output(f"Persistent state root: {self.ctx.persistence_root}")
        self.output(
            f"Persistence contract validation: {self.ctx.persistence_contract_status}"
        )
        if self.ctx.authenticated_slot is not None:
            binding = self.ctx.authenticated_slot
            self.output(
                "Authenticated state contract: "
                f"seed_hash={hash_identifier(binding.seed_identifier)} "
                f"team={binding.team} slot={binding.slot} "
                f"slot_hash={hash_identifier(binding.slot_name)}"
            )
            self.output(f"Native save binding: {self.ctx.persistence_binding_status}")
        elif self.ctx.slot_contract_error:
            self.output(
                f"Authenticated state contract: rejected ({self.ctx.slot_contract_error})"
            )
        else:
            self.output("Authenticated state contract: unavailable")
        self.output(f"Recovery: {self.ctx.persistence_recovery_status}")
        self.output(f"Quarantine: {self.ctx.persistence_quarantine_status}")
        if self.ctx.persistence_read_only_failure:
            self.output(
                f"Persistence read-only failure: {self.ctx.persistence_read_only_failure}"
            )

    def _cmd_diagnostics(self, action: str = "summary") -> None:
        """Record a snapshot or export a local sanitized support bundle."""

        if action.casefold() == "export":

            async def export() -> None:
                await asyncio.to_thread(
                    self.ctx.log_diagnostic_snapshot,
                    "manual /diagnostics export command",
                )
                result = await asyncio.to_thread(self.ctx.diagnostics.export_bundle)
                if result.status == "failed":
                    self.output(
                        f"Diagnostic export failed: {result.error or 'unknown error'}"
                    )
                else:
                    self.output(f"Diagnostic export {result.status}: {result.path}")
                    if result.missing:
                        self.output(
                            "Missing optional artifacts: " + ", ".join(result.missing)
                        )
                    if result.truncated:
                        self.output(
                            "Older sanitized log segments omitted: "
                            + ", ".join(result.truncated)
                        )

            self.output("Diagnostic export started in the background.")
            create_logged_task(
                export(), "diagnostic support bundle export", self.ctx.diagnostics
            )
            return
        if action.casefold() not in {"", "summary", "status"}:
            self.output("Usage: /diagnostics [summary|export]")
            return

        written = self.ctx.log_diagnostic_snapshot("manual /diagnostics command")
        if written:
            self.output(
                "Diagnostic snapshot written. The paired logs and timeline are:"
            )
        else:
            self.output(
                "Diagnostic snapshot failed; the logs still contain the failure traceback:"
            )
        self.output(f"Client/protocol: {self.ctx.diagnostics.client_log}")
        self.output(f"Game/compiler: {self.ctx.diagnostics.opengoal_log}")
        self.output(f"Structured timeline: {self.ctx.diagnostics.events_log}")


class Jak3Context(CommonContext):
    game = GAME_NAME
    items_handling = 0b111
    command_processor = Jak3CommandProcessor

    def emit_diagnostic(self, event_name: str, **fields: object) -> None:
        diagnostics = getattr(self, "diagnostics", None)
        emit = getattr(diagnostics, "emit", None)
        if emit is None:
            return
        try:
            emit(event_name, **fields)
        except BaseException:
            pass

    def _persistence_event_sink(self, event_name: str, **fields: object) -> None:
        """Suppress identical retry noise without affecting persistence calls."""

        repeatable = {
            "persistence.writer_lock.acquired",
            "persistence.writer_lock.refused",
            "persistence.writer_lock.released",
            "persistence.path.selected",
            "persistence.compatibility.rejected",
            "persistence.binding.rejected",
            "persistence.eligibility.rejected",
            "persistence.concurrent_writer.rejected",
            "persistence.commit.attempted",
            "persistence.commit.failed",
            "persistence.revision.stale",
        }
        projections = getattr(self, "_persistence_event_projections", None)
        if projections is None:
            projections = {}
            setattr(self, "_persistence_event_projections", projections)
        context = fields.get("context")
        context_projection = (
            tuple(sorted((str(key), str(value)) for key, value in context.items()))
            if isinstance(context, dict)
            else ()
        )
        projection = (
            fields.get("correlation_id"),
            fields.get("persistent_state_revision"),
            context_projection,
        )
        if event_name in repeatable:
            if projections.get(event_name) == projection:
                return
            projections[event_name] = projection
        elif event_name in {
            "persistence.state.created",
            "persistence.state.loaded",
            "persistence.state.bound",
            "persistence.state.switched",
            "persistence.commit.succeeded",
            "persistence.backup.restored",
        }:
            projections.clear()
        try:
            self.diagnostics.event_sink(event_name, **fields)
        except BaseException:
            pass

    def __init__(
        self,
        server_address: str | None,
        password: str | None,
        diagnostics: DiagnosticSession,
    ) -> None:
        super().__init__(server_address, password)
        self.diagnostics = diagnostics
        self.repl = OpenGoalRepl()
        configured_state = os.environ.get("JAK3_AP_STATE")
        if configured_state:
            self.state_path = Path(configured_state).expanduser().resolve()
        else:
            self.state_path = (
                Path(tempfile.gettempdir()) / f"jak3-ap-{diagnostics.session_id}.tmp"
            ).resolve()
        self.persistence_root = default_state_root()
        self.room_seed = ""
        self.authenticated_slot: AuthenticatedSlot | None = None
        self.slot_contract_error = ""
        self.persistence_contract_status = "not authenticated"
        self.persistence_binding_status = "not attempted"
        self.persistence_recovery_status = "not attempted"
        self.persistence_quarantine_status = "not attempted"
        self.persistence_read_only_failure = ""
        self._persistence_event_projections: dict[str, tuple[object, ...]] = {}
        self._last_persistence_summary: dict[str, object] = {
            "bound": False,
            "revision": None,
            "received_item_count": 0,
            "location_count": 0,
            "has_recent_command": False,
            "last_clean_shutdown": None,
        }
        self.state_repository = StateRepository(
            self.persistence_root, event_sink=self._persistence_event_sink
        )
        self.state_session: StateSession | None = None
        self.protocol: BridgeProtocol | None = None
        self.game_attached = False
        self.source_loaded = False
        self.bridge_ready = False
        self.last_bridge_error = ""
        self.compatibility_error = False
        self.compile_completed = False
        # A packaged source update must replace an already-running bridge even
        # when its public protocol/schema/table contract did not change. Keep
        # this latched until nREPL acknowledges the actual source load so a
        # failed connection attempt cannot silently fall back to stale code.
        self.bridge_source_reload_required = False
        self.bridge_source_reload_marker: Path | None = None
        self.bridge_source_set_hash = "unknown"
        self._runtime_projection: tuple[object, ...] | None = None
        self._safety_projection: tuple[bool, bool, bool] | None = None
        self._communication_lost = False
        self._last_native_descriptor: tuple[int, str, str] | None = None
        self._binding_deferred_projection: tuple[object, ...] | None = None
        self._binding_rejection_projection: tuple[object, ...] | None = None
        self._timed_out_commands: dict[tuple[str, int], ProtocolCommand] = {}
        self._goal_game_session_nonce: str | None = None
        self._received_item_packets: list[tuple[ReceivedItemsPacket, bool]] = []
        self._item_worker_task: asyncio.Task | None = None
        self._item_worker_lock = asyncio.Lock()
        self._item_sync_projection: tuple[object, ...] | None = None
        self._item_runtime_projection: tuple[object, ...] | None = None
        self._item_confirmed_projection: tuple[object, ...] | None = None
        self._item_queued_projection: tuple[object, ...] | None = None
        self._item_failure_projection: tuple[object, ...] | None = None
        self._item_rejection_projection: tuple[object, ...] | None = None
        self._item_native_load_projection: tuple[object, ...] | None = None
        self._item_diagnostic_drop_projection: tuple[int | None, int] | None = None
        self._commonclient_received_item_count: int | None = None
        self._item_reconcile_dirty = False
        self._item_recovery_pending = False
        self._location_read_only = False
        self._location_read_only_failure = ""
        self._server_checked_locations: frozenset[int] | None = None
        self._location_server_updates: list[tuple[bool, tuple[int, ...]]] = []
        self._location_reconciled_state_instance: str | None = None
        self._location_send_task: asyncio.Task | None = None
        self._location_last_send_projection: tuple[object, ...] | None = None
        self._location_last_send_at = float("-inf")
        self._location_connection_generation = 0
        self._location_authenticated_server: object | None = None
        # This state survives BridgeProtocol recreation so a reconnect cannot
        # mistake a restarted or reloaded GOAL diagnostic ring for duplicates.
        self._goal_source_state: dict[str, int] = {}
        self.startup_lock = asyncio.Lock()
        self.reconnect_event = asyncio.Event()
        self.protocol_sync_event = asyncio.Event()
        self._stopping = False
        diagnostics.register_context_provider("runtime", self._diagnostic_runtime)
        diagnostics.register_context_provider(
            "persistence", self._diagnostic_persistence
        )
        diagnostics.register_context_provider("versions", self._diagnostic_versions)
        diagnostics.register_context_provider("commands", self._diagnostic_commands)
        diagnostics.register_context_provider(
            "capture_gaps", diagnostics.capture_gap_snapshot
        )

    def _diagnostic_runtime(self) -> dict[str, object]:
        snapshot = self.latest_snapshot
        return {
            "server_connected": bool(self.server),
            "authenticated": bool(self.auth),
            "repl_connected": self.repl.connected,
            "game_attached": self.game_attached,
            "source_loaded": self.source_loaded,
            "bridge_ready": self.bridge_ready,
            "client_status": self.client_status.name,
            "snapshot_revision": snapshot.snapshot_revision if snapshot else None,
            "game_status": snapshot.game_status.name if snapshot else None,
            "game_session_nonce_hash": (
                hash_identifier(snapshot.session_nonce)
                if snapshot and snapshot.session_nonce
                else None
            ),
            "save_loaded": snapshot.save_loaded if snapshot else None,
            "native_save_slot": snapshot.native_save_slot if snapshot else None,
            "native_save_hash": (
                hash_identifier(snapshot.native_save_identity)
                if snapshot and snapshot.native_save_identity
                else None
            ),
            "safe_permanent": (
                snapshot.safe_to_apply_permanent_item if snapshot else None
            ),
            "safe_consumable": (
                snapshot.safe_to_apply_consumable if snapshot else None
            ),
            "safe_mission": (
                snapshot.safe_to_mutate_mission_state if snapshot else None
            ),
            "last_bridge_error_present": bool(self.last_bridge_error),
        }

    def _diagnostic_persistence(self) -> dict[str, object]:
        session = self.state_session
        state = session.state if session else None
        previous = getattr(self, "_last_persistence_summary", {})
        return {
            "contract_status": self.persistence_contract_status,
            "binding_status": self.persistence_binding_status,
            "recovery_status": self.persistence_recovery_status,
            "quarantine_status": self.persistence_quarantine_status,
            "read_only_failure_present": bool(self.persistence_read_only_failure),
            "open": session is not None,
            "bound": state.is_bound if state else previous.get("bound", False),
            "revision": (state.state_revision if state else previous.get("revision")),
            "received_item_count": (
                sum(count for _, count in state.received_item_counts)
                if state
                else previous.get("received_item_count", 0)
            ),
            "location_count": (
                len(state.checked_location_bits)
                if state
                else previous.get("location_count", 0)
            ),
            "has_recent_command": bool(
                state and state.last_observed_game_command_receipt
            )
            if state
            else previous.get("has_recent_command", False),
            "last_clean_shutdown": (
                state.last_clean_shutdown
                if state
                else previous.get("last_clean_shutdown")
            ),
        }

    def _diagnostic_versions(self) -> dict[str, object]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "game_integration_version": GAME_INTEGRATION_VERSION,
            "bridge_runtime_version": BRIDGE_RUNTIME_VERSION,
            "state_schema_version": STATE_SCHEMA_VERSION,
            "slot_data_version": SLOT_DATA_VERSION,
            "item_table_version": ITEM_TABLE_VERSION,
            "location_table_version": LOCATION_TABLE_VERSION,
            "mission_table_version": MISSION_TABLE_VERSION,
            "source_set_sha256": self.bridge_source_set_hash,
            "bridge_manifest_version": 1,
        }

    def _diagnostic_commands(self) -> dict[str, object]:
        snapshot = self.latest_snapshot
        if snapshot is None:
            return {"recent": []}
        return {
            "recent": [
                {
                    "command_id": receipt.command_id,
                    "command_kind": int(receipt.command_kind),
                    "result": int(receipt.result),
                    "error": int(receipt.error_code),
                }
                for receipt in snapshot.recent_command_receipts
            ]
        }

    @property
    def latest_snapshot(self) -> BridgeSnapshot | None:
        snapshot = read_snapshot(self.state_path)
        if snapshot is not None:
            return snapshot
        if self.protocol is not None:
            return self.protocol.last_snapshot
        return None

    @property
    def client_status(self) -> ClientStatus:
        if self._stopping:
            return ClientStatus.STOPPING
        if self.server and self.auth:
            return ClientStatus.AP_CONNECTED
        return ClientStatus.AP_DISCONNECTED

    async def server_auth(self, password_requested: bool = False) -> None:
        self.emit_diagnostic(
            "server.connecting",
            message="Archipelago server authentication started.",
            source_component="client",
        )
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    async def send_msgs(self, msgs: list[Any]) -> None:
        """Keep CommonClient's volatile location mirror off the wire."""

        messages = [
            message
            for message in msgs
            if not (
                isinstance(message, dict) and message.get("cmd") == "LocationChecks"
            )
        ]
        if not messages:
            return
        if any(
            isinstance(message, dict) and message.get("cmd") == "Sync"
            for message in messages
        ):
            await self._send_sync_with_location_outbox(messages)
            return
        await super().send_msgs(messages)

    async def connection_closed(self) -> None:
        was_connected = self.server is not None
        self._invalidate_location_transport()
        try:
            await super().connection_closed()
        finally:
            if was_connected:
                self.emit_diagnostic(
                    "server.disconnected",
                    message="Archipelago server connection closed.",
                    source_component="client",
                    context={"status": "disconnected"},
                )

    def event_invalid_slot(self) -> None:
        self.emit_diagnostic(
            "server.rejected",
            message="Archipelago server rejected the slot.",
            source_component="client",
            context={"reason": "invalid_slot", "status": "rejected"},
        )
        super().event_invalid_slot()

    def event_invalid_game(self) -> None:
        self.emit_diagnostic(
            "server.rejected",
            message="Archipelago server rejected the game.",
            source_component="client",
            context={"reason": "invalid_game", "status": "rejected"},
        )
        super().event_invalid_game()

    async def close_repl(self, reason: str) -> None:
        was_open = getattr(self.repl, "writer", None) is not None or bool(
            getattr(self.repl, "connected", False)
        )
        await self.repl.close()
        if was_open:
            self.emit_diagnostic(
                "nrepl.closed",
                message="OpenGOAL nREPL connection closed.",
                source_component="client",
                context={"reason": reason},
            )

    def close_persistence(self, *, clean: bool) -> None:
        self._ensure_location_runtime()
        session = self.state_session
        self.state_session = None
        self._location_reconciled_state_instance = None
        self._item_runtime_projection = None
        self._item_confirmed_projection = None
        self._item_queued_projection = None
        self._item_failure_projection = None
        self._item_diagnostic_drop_projection = None
        self._item_reconcile_dirty = True
        if session is not None:
            native_save_hash = hash_identifier(session.native_save.identity)
            closed_cleanly = False
            try:
                session.close(clean=clean)
                closed_cleanly = clean
            except StateError as exc:
                self.persistence_binding_status = "refused read-only"
                self.persistence_read_only_failure = str(exc)
                logger.error("Could not close the AP state session cleanly: %s", exc)
            else:
                self.persistence_binding_status = (
                    "closed cleanly" if closed_cleanly else "closed uncleanly"
                )
            state = session.state
            self._last_persistence_summary = {
                "bound": bool(getattr(state, "is_bound", False)),
                "revision": state.state_revision,
                "received_item_count": sum(
                    count for _, count in getattr(state, "received_item_counts", ())
                ),
                "location_count": len(getattr(state, "checked_location_bits", ())),
                "has_recent_command": bool(
                    getattr(state, "last_observed_game_command_receipt", None)
                ),
                "last_clean_shutdown": getattr(
                    state, "last_clean_shutdown", closed_cleanly
                ),
            }
            self.emit_diagnostic(
                "binding.closed",
                message="Persistent state binding closed.",
                source_component="client",
                persistent_state_revision=session.state.state_revision,
                context={
                    "native_save_hash": native_save_hash,
                    "binding_state": "clean" if closed_cleanly else "unclean",
                },
            )
        if self.protocol is not None:
            self.protocol.set_ap_state_status(loaded=False, bound=False)

    def _create_authorized_save_identity(self) -> str:
        authenticated_slot = self.authenticated_slot
        if authenticated_slot is None:
            raise StateBindingError(
                "Cannot authorize a native-save identity before AP slot authentication."
            )
        return self.state_repository.create_authorized_save_identity(authenticated_slot)

    def _set_protocol_save_identity_authorized(self, authorized: bool) -> bool:
        protocol = self.protocol
        if protocol is None:
            return True
        try:
            protocol.set_save_identity_authorized(authorized)
        except (StateError, ValueError) as exc:
            protocol.set_save_identity_authorized(False)
            self.persistence_binding_status = "refused read-only"
            self.persistence_read_only_failure = str(exc)
            logger.error(
                "Native-save identity proposal is unavailable; AP binding remains "
                "read-only: %s",
                exc,
            )
            return False
        return True

    def sync_persistence(self, snapshot: BridgeSnapshot) -> None:
        """Open/switch state only for an authenticated, identified native save."""

        native_save_identity = snapshot.native_save_identity
        descriptor_ready = (
            snapshot.save_loaded
            and native_save_identity is not None
            and snapshot.native_save_slot in range(4)
        )
        if not descriptor_ready or self.authenticated_slot is None:
            self._binding_rejection_projection = None
            if not descriptor_ready:
                self._binding_deferred_projection = None
            previous_descriptor = getattr(self, "_last_native_descriptor", None)
            if previous_descriptor is not None and not descriptor_ready:
                self.emit_diagnostic(
                    "save.native.unloaded",
                    message="Native-save descriptor is no longer loaded.",
                    source_component="client",
                    context={"native_save_hash": previous_descriptor[1]},
                )
                self._last_native_descriptor = None
            elif descriptor_ready and self.authenticated_slot is None:
                deferred_projection = (
                    "slot_not_authenticated",
                    snapshot.native_save_slot,
                    hash_identifier(native_save_identity),
                )
                if deferred_projection != getattr(
                    self, "_binding_deferred_projection", None
                ):
                    self.emit_diagnostic(
                        "binding.deferred",
                        message="Native-save binding awaits authenticated slot data.",
                        source_component="client",
                        context={"reason": "slot_not_authenticated"},
                    )
                    self._binding_deferred_projection = deferred_projection
            else:
                self._binding_deferred_projection = None
            if self.state_session is not None:
                self.close_persistence(clean=True)
            self.persistence_binding_status = (
                "awaiting authenticated slot"
                if self.authenticated_slot is None
                else "awaiting valid native save identity"
            )
            return
        assert native_save_identity is not None
        self._binding_deferred_projection = None

        descriptor_projection = (
            snapshot.native_save_slot,
            hash_identifier(native_save_identity),
        )
        previous_descriptor = getattr(self, "_last_native_descriptor", None)
        previous_identity = (
            previous_descriptor[:2] if previous_descriptor is not None else None
        )
        identity_changed = descriptor_projection != previous_identity

        eligibility = (
            NativeSaveEligibility.FRESH_UNPROGRESSED
            if snapshot.native_save_eligibility
            is SnapshotSaveEligibility.FRESH_UNPROGRESSED
            else NativeSaveEligibility.INELIGIBLE
        )
        eligibility_changed = (
            previous_descriptor is None or previous_descriptor[2] != eligibility.value
        )
        if identity_changed or eligibility_changed:
            self.emit_diagnostic(
                "save.native.observed",
                message="Valid native-save descriptor observed.",
                source_component="client",
                context={
                    "native_save_hash": descriptor_projection[1],
                    "status": "observed",
                },
            )
        if identity_changed:
            self.emit_diagnostic(
                "save.native.loaded"
                if previous_descriptor is None
                else "save.native.switched",
                message="Native-save descriptor changed.",
                source_component="client",
                context={
                    "native_save_hash": descriptor_projection[1],
                    "status": "loaded" if previous_descriptor is None else "switched",
                },
            )
        if identity_changed or eligibility_changed:
            self.emit_diagnostic(
                "save.native.eligible"
                if eligibility is NativeSaveEligibility.FRESH_UNPROGRESSED
                else "save.native.ineligible",
                message="Native-save AP eligibility observed.",
                source_component="client",
                context={
                    "native_save_hash": descriptor_projection[1],
                    "status": eligibility.value,
                },
            )
            self._last_native_descriptor = (
                descriptor_projection[0],
                descriptor_projection[1],
                eligibility.value,
            )
        descriptor = NativeSaveDescriptor(
            slot=snapshot.native_save_slot,
            identity=native_save_identity,
            eligibility=eligibility,
        )
        binding_switched = (
            self.state_session is not None
            and self.state_session.native_save != descriptor
        )
        if binding_switched:
            self.close_persistence(clean=True)

        try:
            if self.state_session is None:
                self.state_session = self.state_repository.open_live(
                    descriptor, self.authenticated_slot
                )
                self.persistence_binding_status = (
                    "bound automatically"
                    if self.state_session.binding_performed
                    else "bound and loaded"
                )
                self.persistence_recovery_status = self.state_session.status.value
                self.persistence_read_only_failure = ""
                self._binding_rejection_projection = None
                self.emit_diagnostic(
                    "binding.switched" if binding_switched else "binding.opened",
                    message=(
                        "Persistent state binding switched."
                        if binding_switched
                        else "Persistent state binding opened."
                    ),
                    source_component="client",
                    persistent_state_revision=self.state_session.state.state_revision,
                    context={
                        "native_save_hash": descriptor_projection[1],
                        "binding_state": self.persistence_binding_status,
                    },
                )
            self._persist_latest_harmless_receipt(snapshot)
        except StateError as exc:
            failed_session = self.state_session
            self.state_session = None
            if failed_session is not None:
                try:
                    failed_session.close(clean=False)
                except StateError:
                    logger.exception("Failed to release the rejected AP state session")
            self.persistence_binding_status = "refused read-only"
            self.persistence_read_only_failure = str(exc)
            logger.error("Native save AP binding is unavailable: %s", exc)
            rejection_projection = (
                descriptor_projection,
                type(exc).__name__,
                hash_identifier(str(exc)),
            )
            if rejection_projection != getattr(
                self, "_binding_rejection_projection", None
            ):
                self.emit_diagnostic(
                    "binding.rejected",
                    message="Native-save AP state binding was rejected.",
                    source_component="client",
                    context={"reason": type(exc).__name__},
                )
                self._binding_rejection_projection = rejection_projection

        if self.protocol is not None:
            session = self.state_session
            native_save = session.native_save if session is not None else None
            self.protocol.set_ap_state_status(
                loaded=session is not None,
                bound=session is not None and session.state.is_bound,
                native_save_slot=(
                    native_save.slot if native_save is not None else None
                ),
                native_save_identity=(
                    native_save.identity if native_save is not None else None
                ),
            )
        self._drain_location_server_updates()
        self._pump_location_outbox("heartbeat")
        self._note_permanent_item_runtime(snapshot)

    def _persist_latest_harmless_receipt(self, snapshot: BridgeSnapshot) -> None:
        session = self.state_session
        if session is None or snapshot.session_nonce is None:
            return
        receipt = max(
            (
                candidate
                for candidate in snapshot.recent_command_receipts
                if candidate.command_kind
                in (
                    ProtocolCommand.SET_TEST_TARGET,
                    ProtocolCommand.TEST_ADDITIVE_EFFECT,
                )
            ),
            key=lambda candidate: candidate.command_id,
            default=None,
        )
        if receipt is None:
            return
        receipt_kind = ProtocolCommand(receipt.command_kind)
        persisted = GameCommandReceipt(
            command_id=f"{snapshot.session_nonce}:{receipt.command_id}",
            command_kind=receipt_kind.name,
            result=receipt.result.name,
        )
        previous = session.state.last_observed_game_command_receipt
        if previous is not None:
            previous_nonce, separator, previous_id = previous.command_id.rpartition(":")
            if (
                separator
                and previous_nonce == snapshot.session_nonce
                and previous_id.isdecimal()
                and int(previous_id) >= receipt.command_id
            ):
                return
        if session.state.last_observed_game_command_receipt != persisted:
            session.commit(
                replace(session.state, last_observed_game_command_receipt=persisted),
                category="command_receipt",
            )

    def _ensure_location_runtime(self) -> None:
        """Initialize Milestone 9 fields for lightweight test contexts too."""

        defaults: dict[str, object] = {
            "_location_read_only": False,
            "_location_read_only_failure": "",
            "_server_checked_locations": None,
            "_location_server_updates": [],
            "_location_reconciled_state_instance": None,
            "_location_send_task": None,
            "_location_last_send_projection": None,
            "_location_last_send_at": float("-inf"),
            "_location_connection_generation": 0,
            "_location_authenticated_server": None,
        }
        for name, value in defaults.items():
            if not hasattr(self, name):
                setattr(self, name, value)

    def _invalidate_location_transport(self) -> None:
        """Invalidate every send captured for the prior AP connection."""

        self._ensure_location_runtime()
        task = self._location_send_task
        if task is not None and not task.done():
            task.cancel()
        self._location_send_task = None
        self._location_connection_generation += 1
        self._location_authenticated_server = None
        self._location_last_send_projection = None

    def _activate_location_transport(self) -> None:
        """Authorize location sends only after a valid Connected packet."""

        self._ensure_location_runtime()
        self._location_connection_generation += 1
        self._location_authenticated_server = self.server
        self._location_last_send_projection = None

    def _location_transport_ready(self) -> bool:
        server = getattr(self, "server", None)
        return bool(
            server is not None
            and server is self._location_authenticated_server
            and getattr(self, "authenticated_slot", None) is not None
            and not self._location_read_only
        )

    def _current_location_projection(
        self, session: StateSession, pending: tuple[int, ...]
    ) -> tuple[object, ...]:
        return (
            session.state.state_instance_id,
            pending,
            self._location_connection_generation,
        )

    def _reserve_location_batch(
        self, requested_pending: tuple[int, ...] | None = None
    ) -> tuple[StateSession, tuple[int, ...], tuple[object, ...]] | None:
        """Reserve one current authenticated batch under the shared retry bound."""

        self._ensure_location_runtime()
        session = self.state_session
        if session is None or not self._location_transport_ready():
            return None
        pending = tuple(session.state.pending_location_outbox)
        if not pending or (
            requested_pending is not None and tuple(requested_pending) != pending
        ):
            return None
        projection = self._current_location_projection(session, pending)
        now = monotonic()
        if (
            projection == self._location_last_send_projection
            and now - self._location_last_send_at < LOCATION_RETRY_SECONDS
        ):
            return None
        self._location_last_send_projection = projection
        self._location_last_send_at = now
        return session, pending, projection

    def _reject_location_update(self, exc: Exception, *, source: str) -> None:
        self._ensure_location_runtime()
        self._location_read_only = True
        self._location_read_only_failure = str(exc)
        self.compatibility_error = True
        self.persistence_read_only_failure = str(exc)
        self.emit_diagnostic(
            "location.reconciliation.rejected",
            message="Server location state was rejected before CommonClient mutation.",
            source_component="client",
            context={
                "source": source,
                "outcome": "rejected",
                "reason": type(exc).__name__,
            },
        )
        logger.error("Jak 3 location handling entered read-only mode: %s", exc)

    def _preprocess_location_update(self, args: dict[str, Any]) -> dict | None:
        """Validate Connected/RoomUpdate location IDs before generic mutation."""

        self._ensure_location_runtime()
        connected = args.get("cmd") == "Connected"
        if connected:
            slot_data = args.get("slot_data")
        else:
            authenticated = getattr(self, "authenticated_slot", None)
            slot_data = authenticated.contract if authenticated is not None else None
        try:
            update = parse_server_location_update(
                args,
                connected=connected,
                slot_data=slot_data,
            )
        except (LocationPacketError, TypeError, ValueError) as exc:
            self._reject_location_update(
                exc, source="connected" if connected else "room_update"
            )
            return None
        prepared = dict(args)
        prepared[_PREVALIDATED_LOCATION_UPDATE_KEY] = update
        return prepared

    def _queue_server_location_update(self, args: dict[str, Any]) -> None:
        self._ensure_location_runtime()
        update = args.get(_PREVALIDATED_LOCATION_UPDATE_KEY)
        if update is None:
            prepared = self._preprocess_location_update(args)
            if prepared is None:
                return
            update = prepared[_PREVALIDATED_LOCATION_UPDATE_KEY]
        checked = tuple(update.checked_locations)
        if update.full:
            self._server_checked_locations = frozenset(checked)
            self._location_server_updates = [(True, checked)]
        else:
            current = self._server_checked_locations or frozenset()
            self._server_checked_locations = current | frozenset(checked)
            if checked:
                self._location_server_updates.append((False, checked))
        self._drain_location_server_updates()

    def _emit_location_event(
        self,
        event_name: str,
        message: str,
        *,
        location_id: int | None = None,
        location_ids: tuple[int, ...] | None = None,
        task_id: int | None = None,
        task_ids: tuple[int, ...] | None = None,
        source: str,
        outcome: str,
        reason: str | None = None,
        state: PersistentState | None = None,
        batch_id: str | None = None,
    ) -> None:
        revision = getattr(state, "state_revision", None)
        if batch_id is None and state is not None:
            batch_id = diagnostic_batch_id(state)
        context: dict[str, object] = {
            "source": source,
            "outcome": outcome,
        }
        if location_id is not None:
            context["location_id"] = location_id
        if location_ids is not None:
            context["location_ids"] = list(location_ids)
        if task_id is not None:
            context["task_id"] = task_id
        if task_ids is not None:
            context["task_ids"] = list(task_ids)
        if batch_id is not None:
            context["batch_id"] = batch_id
        if type(revision) is int:
            context["revision"] = revision
        if reason is not None:
            context["reason"] = reason
        self.emit_diagnostic(
            event_name,
            message=message,
            source_component="client",
            correlation_id=(
                f"location:{location_id}" if location_id is not None else batch_id
            ),
            persistent_state_revision=(revision if type(revision) is int else None),
            context=context,
        )

    @staticmethod
    def _location_batch_metadata(
        location_ids: tuple[int, ...],
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        normalized = tuple(sorted(set(location_ids)))
        task_ids = tuple(
            LOCATION_TASK_IDS[location_id]
            for location_id in normalized
            if location_id in LOCATION_TASK_IDS
        )
        return normalized, task_ids

    async def _send_location_messages_checked(
        self,
        messages: list[Any],
        projection: tuple[object, ...],
    ) -> None:
        """Send location-bearing messages without CommonClient's closed no-op."""

        session = self.state_session
        if session is None or not self._location_transport_ready():
            raise ConnectionError(
                "Archipelago location transport is not authenticated."
            )
        pending = tuple(session.state.pending_location_outbox)
        if projection != self._current_location_projection(session, pending):
            raise ConnectionError("Archipelago location send projection is stale.")
        server = getattr(self, "server", None)
        if server is None:
            raise ConnectionError("Archipelago server is disconnected.")
        socket = getattr(server, "socket", None)
        if socket is None:
            raise ConnectionError("Archipelago server endpoint has no socket.")
        if getattr(socket, "open", True) is False or bool(
            getattr(socket, "closed", False)
        ):
            raise ConnectionError("Archipelago server socket is closed.")
        await socket.send(encode(messages))

    async def _send_reserved_location_batch(
        self,
        base_messages: list[Any],
        *,
        source: str,
        reason: str,
        requested_pending: tuple[int, ...] | None = None,
    ) -> bool:
        reservation = self._reserve_location_batch(requested_pending)
        if reservation is None:
            return False
        session, pending, projection = reservation
        state = session.state
        batch_id = diagnostic_batch_id(state)
        location_ids, task_ids = self._location_batch_metadata(pending)
        messages = list(base_messages)
        messages.append({"cmd": "LocationChecks", "locations": list(sorted(pending))})
        try:
            await self._send_location_messages_checked(messages, projection)
        except Exception as exc:
            self._emit_location_event(
                "location.outbox.send_failed",
                "LocationChecks batch send failed; durable entries remain pending.",
                location_ids=location_ids,
                task_ids=task_ids,
                source=source,
                outcome="failed",
                reason=type(exc).__name__,
                state=state,
                batch_id=batch_id,
            )
            raise
        self._emit_location_event(
            "location.outbox.batch_sent",
            "LocationChecks batch sent; entries remain pending until server state confirms.",
            location_ids=location_ids,
            task_ids=task_ids,
            source=source,
            outcome="sent",
            reason=reason,
            state=state,
            batch_id=batch_id,
        )
        return True

    async def _send_sync_with_location_outbox(self, messages: list[Any]) -> None:
        sent_with_locations = await self._send_reserved_location_batch(
            messages,
            source="item_gap_sync",
            reason="item_gap_sync",
        )
        if not sent_with_locations:
            await super().send_msgs(messages)

    def _commit_goal_location_observation(
        self, record: GoalDiagnosticRecord
    ) -> dict[str, object]:
        """Commit the local bit and outbox before permitting a GOAL ack."""

        self._ensure_location_runtime()
        location_id = record.correlation_value
        task_id = record.arg0
        source_code = record.arg1
        expected_task = LOCATION_TASK_IDS.get(location_id)
        expected_source_code = 1 if location_id == DEBUG_LOCATION_ID else 0
        if (
            record.event_code != LOCATION_OBSERVED_GOAL_CODE
            or record.correlation_kind != 3
            or expected_task is None
            or task_id != expected_task
            or source_code != expected_source_code
        ):
            error = LocationPacketError("Malformed GOAL location observation.")
            self._reject_location_update(error, source="goal")
            raise error
        if self._location_read_only:
            raise LocationPacketError(self._location_read_only_failure)
        session = self.state_session
        if session is None or not session.state.is_bound:
            raise StateBindingError(
                "GOAL location observation awaits its exact bound persistent state."
            )
        source = LOCATION_SOURCES[location_id]
        transition = observe_local_location(session.state, location_id)
        if transition.changed:
            try:
                session.commit(transition.state, category="location_observed")
            except StateError as exc:
                self._location_read_only = True
                self._location_read_only_failure = str(exc)
                self._emit_location_event(
                    "location.reconciliation.rejected",
                    "Local location observation could not be committed durably.",
                    location_id=location_id,
                    task_id=task_id,
                    source=source,
                    outcome="rejected",
                    reason=type(exc).__name__,
                    state=session.state,
                )
                raise
            committed = session.state
            batch_id = diagnostic_batch_id(committed)
            self._emit_location_event(
                "location.committed_local",
                "Local location completion was committed durably.",
                location_id=location_id,
                task_id=task_id,
                source=source,
                outcome="committed",
                reason="first_observation",
                state=committed,
                batch_id=batch_id,
            )
            self._emit_location_event(
                "location.outbox.enqueued",
                "Durable location check was added to the outgoing outbox.",
                location_id=location_id,
                task_id=task_id,
                source=source,
                outcome="pending",
                reason="awaiting_server_confirmation",
                state=committed,
                batch_id=batch_id,
            )
            self._pump_location_outbox("local_observation")
            outcome = "committed"
            reason = "first_observation"
        else:
            committed = session.state
            batch_id = diagnostic_batch_id(committed)
            self._emit_location_event(
                "location.duplicate_ignored",
                "Duplicate local location observation was ignored idempotently.",
                location_id=location_id,
                task_id=task_id,
                source=source,
                outcome="duplicate",
                reason="already_checked",
                state=committed,
                batch_id=batch_id,
            )
            self._pump_location_outbox("duplicate_observation")
            outcome = "duplicate"
            reason = "already_checked"
        return {
            "location_id": location_id,
            "task_id": task_id,
            "batch_id": batch_id,
            "revision": committed.state_revision,
            "source": source,
            "outcome": outcome,
            "reason": reason,
        }

    def _ingest_goal_events(
        self, records: tuple[GoalDiagnosticRecord, ...], dropped: int
    ) -> int | None:
        """Withhold location-event acknowledgement until its durable commit."""

        safe_records: list[GoalDiagnosticRecord] = []
        enrichments: dict[int, dict[str, object]] = {}
        for record in sorted(records, key=lambda item: item.source_sequence):
            if record.event_code == LOCATION_OBSERVED_GOAL_CODE:
                try:
                    enrichment = self._commit_goal_location_observation(record)
                except (StateError, ValueError):
                    break
                enrichments[record.source_sequence] = enrichment
            safe_records.append(record)
        ingest = getattr(self.diagnostics, "ingest_goal_events", None)
        if not callable(ingest):
            return None
        return ingest(
            tuple(safe_records),
            dropped_count=dropped,
            record_context=enrichments,
        )

    def _drain_location_server_updates(self) -> None:
        self._ensure_location_runtime()
        session = self.state_session
        if session is None or self._location_read_only:
            return
        if self._location_reconciled_state_instance != session.state.state_instance_id:
            self._location_reconciled_state_instance = session.state.state_instance_id
            if self._server_checked_locations is not None:
                canonical = (True, tuple(sorted(self._server_checked_locations)))
                # The accumulated server mirror is authoritative for a newly
                # bound state. Replaying the earlier Connected/RoomUpdate
                # history after it would manufacture a transient rollback.
                self._location_server_updates = [canonical]
        while self._location_server_updates:
            full, checked = self._location_server_updates[0]
            source = "connected" if full else "room_update"
            before = session.state
            transition = (
                reconcile_connected(before, checked)
                if full
                else reconcile_room_update(before, checked)
            )
            reconciliation_ids, reconciliation_task_ids = self._location_batch_metadata(
                tuple(
                    sorted(
                        set(checked)
                        | set(transition.checked_added)
                        | set(transition.confirmed_added)
                        | set(transition.confirmed_removed)
                        | set(transition.pending_added)
                        | set(transition.pending_removed)
                    )
                )
            )
            self._emit_location_event(
                "location.reconciliation.started",
                "Authoritative server location reconciliation started.",
                location_ids=reconciliation_ids,
                task_ids=reconciliation_task_ids,
                source=source,
                outcome="started",
                state=before,
            )
            try:
                if transition.changed:
                    session.commit(transition.state, category="location_reconciliation")
            except StateError as exc:
                self._location_read_only = True
                self._location_read_only_failure = str(exc)
                self._emit_location_event(
                    "location.reconciliation.rejected",
                    "Authoritative server location reconciliation failed durably.",
                    location_ids=reconciliation_ids,
                    task_ids=reconciliation_task_ids,
                    source=source,
                    outcome="rejected",
                    reason=type(exc).__name__,
                    state=session.state,
                )
                return
            self._location_server_updates.pop(0)
            for location_id in transition.confirmed_added:
                self._emit_location_event(
                    "location.server_confirmed",
                    "Server confirmed a durable local location check.",
                    location_id=location_id,
                    task_id=LOCATION_TASK_IDS.get(location_id),
                    source=source,
                    outcome="confirmed",
                    reason="authoritative_server_state",
                    state=session.state,
                )
            self._emit_location_event(
                "location.reconciliation.completed",
                "Authoritative server location reconciliation completed.",
                location_ids=reconciliation_ids,
                task_ids=reconciliation_task_ids,
                source=source,
                outcome="completed",
                reason=(
                    "server_rollback_to_pending"
                    if transition.confirmed_removed
                    else "authoritative_merge"
                ),
                state=session.state,
            )
        self._pump_location_outbox("server_reconciliation")

    def _pump_location_outbox(self, reason: str) -> None:
        self._ensure_location_runtime()
        session = self.state_session
        if (
            session is None
            or not session.state.pending_location_outbox
            or not self._location_transport_ready()
        ):
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        task = self._location_send_task
        if task is not None and not task.done():
            return
        pending = tuple(session.state.pending_location_outbox)
        projection = self._current_location_projection(session, pending)
        now = monotonic()
        if (
            projection == self._location_last_send_projection
            and now - self._location_last_send_at < LOCATION_RETRY_SECONDS
        ):
            return
        self._location_send_task = create_logged_task(
            self._send_location_outbox(projection, pending, reason=reason),
            "Milestone 9 persistent location outbox",
            getattr(self, "diagnostics", None),
        )

    async def _send_location_outbox(
        self,
        projection: tuple[object, ...],
        pending: tuple[int, ...],
        *,
        reason: str,
    ) -> None:
        session = self.state_session
        if session is None or projection != self._current_location_projection(
            session, tuple(session.state.pending_location_outbox)
        ):
            return
        await self._send_reserved_location_batch(
            [],
            source="client_outbox",
            reason=reason,
            requested_pending=pending,
        )

    def _ensure_item_runtime(self) -> None:
        """Initialize Milestone 8 fields for lightweight test contexts too."""

        if not hasattr(self, "_received_item_packets"):
            self._received_item_packets = []
        if not hasattr(self, "_item_worker_task"):
            self._item_worker_task = None
        if not hasattr(self, "_item_worker_lock"):
            self._item_worker_lock = asyncio.Lock()
        for name in (
            "_item_sync_projection",
            "_item_runtime_projection",
            "_item_confirmed_projection",
            "_item_queued_projection",
            "_item_failure_projection",
            "_item_rejection_projection",
            "_item_native_load_projection",
            "_item_diagnostic_drop_projection",
        ):
            if not hasattr(self, name):
                setattr(self, name, None)
        if not hasattr(self, "_item_reconcile_dirty"):
            self._item_reconcile_dirty = False
        if not hasattr(self, "_item_recovery_pending"):
            self._item_recovery_pending = False
        if not hasattr(self, "_commonclient_received_item_count"):
            self._commonclient_received_item_count = None

    def _note_permanent_item_runtime(self, snapshot: BridgeSnapshot) -> None:
        self._ensure_item_runtime()
        session = self.state_session
        if session is None:
            return
        native_load_projection = self._latest_native_load_projection(snapshot)
        native_load_completed = (
            native_load_projection is not None
            and native_load_projection != self._item_native_load_projection
        )
        if native_load_projection is not None:
            self._item_native_load_projection = native_load_projection
        diagnostic_drop_projection = (
            snapshot.diagnostic_activation_generation,
            snapshot.diagnostic_dropped_count,
        )
        previous_drop_projection = self._item_diagnostic_drop_projection
        diagnostic_loss_detected = previous_drop_projection is not None and (
            (
                diagnostic_drop_projection[0] == previous_drop_projection[0]
                and diagnostic_drop_projection[1] > previous_drop_projection[1]
            )
            or (
                diagnostic_drop_projection[0] != previous_drop_projection[0]
                and diagnostic_drop_projection[1] > 0
            )
        )
        self._item_diagnostic_drop_projection = diagnostic_drop_projection
        reconstruction_boundary = native_load_completed or diagnostic_loss_detected
        projection = (
            session.state.state_instance_id,
            id(session),
            snapshot.session_nonce,
            snapshot.native_save_slot,
            snapshot.native_save_identity,
            snapshot.safe_to_apply_permanent_item,
        )
        previous = self._item_runtime_projection
        lifecycle_changed = previous is None or projection[:5] != previous[:5]
        became_safe = (
            previous is not None
            and not bool(previous[5])
            and snapshot.safe_to_apply_permanent_item
        )
        if lifecycle_changed or became_safe or reconstruction_boundary:
            self._item_reconcile_dirty = True
            self._item_failure_projection = None
        if lifecycle_changed or reconstruction_boundary:
            self._item_confirmed_projection = None
            self._item_queued_projection = None
            self._item_recovery_pending = bool(
                session.state.received_item_journal
                or session.state.pending_item_application_indices
            )
            if self._item_recovery_pending:
                self._emit_item_event(
                    "item.recovery.started",
                    "Permanent-item recovery started from the durable ledger.",
                    snapshot=snapshot,
                    revision=session.state.state_revision,
                    target_mask=permanent_item_target_mask(session.state),
                    outcome="started",
                )
            if (
                not self._received_item_packets
                and self._item_rejection_projection is None
            ):
                self._request_item_sync_once("binding_or_reconnect")
        self._item_runtime_projection = projection
        self._schedule_item_worker()

    @staticmethod
    def _latest_native_load_projection(
        snapshot: BridgeSnapshot,
    ) -> tuple[object, ...] | None:
        load_sequences = tuple(
            event.source_sequence
            for event in snapshot.diagnostic_events
            if (
                (definition := GOAL_EVENT_REGISTRY.get(event.event_code)) is not None
                and definition.name == "save.native_operation.succeeded"
                and event.arg0 == _GOAL_NATIVE_OPERATION_LOAD
            )
        )
        if not load_sequences:
            return None
        return snapshot.diagnostic_activation_generation, max(load_sequences)

    def _emit_received_items_packet_observed(self, args: dict[str, Any]) -> None:
        raw_items = args.get("items")
        packet_index = args.get("index")
        session = self.state_session
        self._emit_item_event(
            "ap.received_items.packet_observed",
            "ReceivedItems packet observed.",
            index=packet_index,
            count=len(raw_items) if isinstance(raw_items, (list, tuple)) else None,
            expected_index=(
                session.state.next_received_item_index if session is not None else None
            ),
            revision=(session.state.state_revision if session is not None else None),
            outcome="observed",
        )

    def _reject_received_items_packet(
        self,
        args: dict[str, Any],
        error: ReceivedItemsPacketError,
        *,
        already_sent: bool,
    ) -> None:
        session = self.state_session
        packet_index = args.get("index")
        expected_index = (
            session.state.next_received_item_index if session is not None else None
        )
        # The canonical index-zero response to a rejected incremental packet
        # repeats the same invalid history. Exclude its transport index from the
        # latch so one rejection produces exactly one diagnostic and one Sync.
        rejection_projection = (
            error.reason,
            error.item_id,
            error.item_index,
            error.location_id,
            error.source_player,
            error.flags,
        )
        if self._item_rejection_projection == rejection_projection:
            return
        attribution = {
            key: value
            for key, value in (
                ("location_id", error.location_id),
                ("source_player", error.source_player),
                ("flags", error.flags),
            )
            if value is not None
        }
        self._emit_item_event(
            "item.receipt.rejected",
            "ReceivedItems packet rejected before persistent mutation.",
            item_id=error.item_id,
            index=(error.item_index if error.item_index is not None else packet_index),
            outcome="rejected",
            reason=error.reason,
            revision=(session.state.state_revision if session else None),
            expected_index=expected_index,
            target_mask=(
                permanent_item_target_mask(session.state) if session else None
            ),
            attribution=attribution or None,
        )
        self._item_rejection_projection = rejection_projection
        self._request_item_sync_once(
            "packet_rejected",
            packet_index,
            already_sent=already_sent,
        )

    def _preprocess_received_items_packet(
        self, args: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Validate and normalize ReceivedItems before CommonClient sees it."""

        self._ensure_item_runtime()
        self._emit_received_items_packet_observed(args)
        try:
            packet = parse_received_items_packet(args)
        except ReceivedItemsPacketError as exc:
            self._reject_received_items_packet(args, exc, already_sent=False)
            return None

        prepared = dict(args)
        prepared["index"] = packet.index
        prepared["items"] = [
            (entry.item_id, entry.location_id, entry.source_player, entry.flags)
            for entry in packet.entries
        ]
        prepared[_PREVALIDATED_RECEIVED_ITEMS_KEY] = packet
        return prepared

    def _observe_received_items(self, args: dict[str, Any]) -> None:
        self._ensure_item_runtime()
        raw_items = args.get("items") if isinstance(args, dict) else None
        raw_count = len(raw_items) if isinstance(raw_items, (list, tuple)) else 0
        packet_index = args.get("index") if isinstance(args, dict) else None
        current_commonclient_count = len(getattr(self, "items_received", ()))
        previous_commonclient_count = self._commonclient_received_item_count
        if type(packet_index) is int and packet_index != 0:
            commonclient_sync_sent = (
                packet_index != previous_commonclient_count
                if previous_commonclient_count is not None
                else current_commonclient_count != packet_index + raw_count
            )
        else:
            commonclient_sync_sent = False
        self._commonclient_received_item_count = current_commonclient_count
        prevalidated = args.get(_PREVALIDATED_RECEIVED_ITEMS_KEY)
        if isinstance(prevalidated, ReceivedItemsPacket):
            packet = prevalidated
        else:
            self._emit_received_items_packet_observed(args)
            try:
                packet = parse_received_items_packet(args)
            except ReceivedItemsPacketError as exc:
                self._reject_received_items_packet(
                    args, exc, already_sent=commonclient_sync_sent
                )
                return
        self._received_item_packets.append((packet, commonclient_sync_sent))
        if packet.index == 0:
            self._item_sync_projection = None
            self._item_rejection_projection = None
        self._schedule_item_worker()

    def _schedule_item_worker(self) -> None:
        self._ensure_item_runtime()
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        task = self._item_worker_task
        if task is not None and not task.done():
            return
        self._item_worker_task = create_logged_task(
            self._run_item_worker(),
            "Milestone 8 ReceivedItems coordinator",
            getattr(self, "diagnostics", None),
        )

    async def _run_item_worker(self) -> None:
        async with self._item_worker_lock:
            while True:
                session = self.state_session
                if session is None:
                    return
                if self._received_item_packets:
                    packet, commonclient_sync_sent = self._received_item_packets.pop(0)
                    if not await self._commit_received_items_packet(
                        session, packet, commonclient_sync_sent=commonclient_sync_sent
                    ):
                        return
                    continue
                await self._reconcile_permanent_items(session)
                return

    async def _commit_received_items_packet(
        self,
        session: StateSession,
        packet: ReceivedItemsPacket,
        *,
        commonclient_sync_sent: bool = False,
    ) -> bool:
        prior_target_mask = permanent_item_target_mask(session.state)
        transition = apply_received_items_packet(session.state, packet)
        expected = session.state.next_received_item_index
        if transition.outcome in {
            PacketOutcome.GAP,
            PacketOutcome.CONFLICT,
            PacketOutcome.PARTIAL_OVERLAP,
        }:
            event = (
                "item.receipt.index_gap"
                if transition.outcome is PacketOutcome.GAP
                else "item.receipt.rejected"
            )
            self._emit_item_event(
                event,
                "ReceivedItems history does not match the durable expected index.",
                index=packet.index,
                count=len(packet.entries),
                expected_index=expected,
                revision=session.state.state_revision,
                target_mask=permanent_item_target_mask(session.state),
                outcome=transition.outcome.value,
                reason=transition.outcome.value,
            )
            self._request_item_sync_once(
                transition.outcome.value,
                packet.index,
                already_sent=commonclient_sync_sent,
            )
            return True
        if transition.outcome is PacketOutcome.DUPLICATE:
            self._emit_item_event(
                "item.receipt.duplicate",
                "Exact historical ReceivedItems packet replayed idempotently.",
                index=packet.index,
                count=len(packet.entries),
                expected_index=expected,
                revision=session.state.state_revision,
                target_mask=permanent_item_target_mask(session.state),
                outcome="duplicate",
            )
            return True

        replay = transition.outcome is PacketOutcome.REPLACED
        if replay:
            self._emit_item_event(
                "item.replay.started",
                "Canonical index-zero item replay started.",
                index=0,
                count=len(packet.entries),
                expected_index=expected,
                revision=session.state.state_revision,
                target_mask=prior_target_mask,
                outcome="started",
            )
        if transition.changed:
            try:
                session.commit(transition.state, category="received_items")
            except StateError as exc:
                self._emit_item_event(
                    "item.receipt.rejected",
                    "Durable ReceivedItems commit failed.",
                    index=packet.index,
                    expected_index=expected,
                    revision=session.state.state_revision,
                    outcome="failed",
                    reason=type(exc).__name__,
                )
                await self.mark_bridge_unavailable(exc)
                return False

        self._item_rejection_projection = None

        if (
            (transition.outcome is PacketOutcome.ACCEPTED and bool(packet.entries))
            or replay
            or prior_target_mask != permanent_item_target_mask(session.state)
            or bool(session.state.pending_item_application_indices)
        ):
            self._item_reconcile_dirty = True
        self._item_failure_projection = None
        for entry in packet.entries:
            self._emit_item_event(
                "item.receipt.accepted",
                "Permanent-item receipt durably accepted.",
                item_id=entry.item_id,
                index=entry.index,
                expected_index=session.state.next_received_item_index,
                revision=session.state.state_revision,
                target_mask=permanent_item_target_mask(session.state),
                outcome="accepted",
                attribution={
                    "location_id": entry.location_id,
                    "source_player": entry.source_player,
                    "flags": entry.flags,
                },
            )
        if replay:
            self._emit_item_event(
                "item.replay.completed",
                "Canonical index-zero item replay completed.",
                index=0,
                count=len(packet.entries),
                expected_index=session.state.next_received_item_index,
                revision=session.state.state_revision,
                target_mask=permanent_item_target_mask(session.state),
                outcome=(
                    "history_mismatch"
                    if transition.history_discrepancies
                    else "complete"
                ),
                discrepancies=transition.history_discrepancies,
            )
        return True

    async def _reconcile_permanent_items(self, session: StateSession) -> None:
        protocol = self.protocol
        snapshot = protocol.last_snapshot if protocol is not None else None
        if protocol is None or snapshot is None or snapshot.session_nonce is None:
            return
        target_mask = permanent_item_target_mask(session.state)
        projection = (
            session.state.state_instance_id,
            id(session),
            snapshot.session_nonce,
            snapshot.native_save_slot,
            snapshot.native_save_identity,
            target_mask,
        )
        if (
            not self._item_reconcile_dirty
            and not session.state.pending_item_application_indices
            and self._item_confirmed_projection == projection
        ):
            return
        if self._item_failure_projection == projection:
            return
        if not snapshot.safe_to_apply_permanent_item:
            queued = projection + (self._permanent_item_safety_reason(snapshot),)
            if self._item_queued_projection != queued:
                self._emit_item_event(
                    "item.application.queued",
                    "Permanent-item reconciliation is queued until gameplay is safe.",
                    snapshot=snapshot,
                    revision=session.state.state_revision,
                    target_mask=target_mask,
                    outcome="unsafe_now",
                    safety_reason=queued[-1],
                )
                self._item_queued_projection = queued
            return

        self._item_queued_projection = None
        pending_entries = tuple(
            session.state.received_item_journal[index]
            for index in session.state.pending_item_application_indices
        )
        command_id = protocol.next_command_id
        self._emit_item_event(
            "item.reconciliation.started",
            "Permanent-item native target reconciliation started.",
            snapshot=snapshot,
            revision=session.state.state_revision,
            target_mask=target_mask,
            command_id=command_id,
            outcome="started",
        )
        for entry in pending_entries:
            self._emit_item_event(
                "item.application.command_submitted",
                "Permanent-item native command submitted.",
                snapshot=snapshot,
                item_id=entry.item_id,
                index=entry.index,
                revision=session.state.state_revision,
                target_mask=target_mask,
                command_id=command_id,
                outcome="submitted",
                attribution={
                    "location_id": entry.location_id,
                    "source_player": entry.source_player,
                    "flags": entry.flags,
                },
            )
        try:
            result_snapshot = await protocol.send_command(
                ProtocolCommand.RECONCILE_PERMANENT_ITEMS, target_mask
            )
        except (ConnectionError, OSError) as exc:
            self._emit_item_event(
                "item.application.failed",
                "Permanent-item command outcome was not durably observed.",
                snapshot=snapshot,
                revision=session.state.state_revision,
                target_mask=target_mask,
                command_id=command_id,
                outcome="transport_lost",
                reason=type(exc).__name__,
            )
            await self.mark_bridge_unavailable(exc)
            return
        except ValueError as exc:
            self._item_failure_projection = projection
            self._emit_item_event(
                "item.application.failed",
                "Permanent-item command was rejected by the local transport.",
                snapshot=snapshot,
                revision=session.state.state_revision,
                target_mask=target_mask,
                command_id=command_id,
                outcome="failed",
                reason=type(exc).__name__,
            )
            return

        result = result_snapshot.last_command_result
        if result in (ProtocolResult.APPLIED, ProtocolResult.ALREADY_APPLIED):
            receipt = GameCommandReceipt(
                command_id=(
                    f"{result_snapshot.session_nonce}:{result_snapshot.last_command_id}"
                ),
                command_kind=ProtocolCommand.RECONCILE_PERMANENT_ITEMS.name,
                result=result.name,
            )
            if self.state_session is not session:
                self._item_reconcile_dirty = True
                return
            applied = mark_pending_items_applied(session.state, receipt)
            try:
                if applied != session.state:
                    session.commit(applied, category="permanent_items_applied")
            except StateError as exc:
                self._emit_item_event(
                    "item.application.failed",
                    "Native target changed but its result was not durably committed.",
                    snapshot=result_snapshot,
                    revision=session.state.state_revision,
                    target_mask=target_mask,
                    command_id=result_snapshot.last_command_id,
                    outcome="durable_observation_failed",
                    reason=type(exc).__name__,
                )
                await self.mark_bridge_unavailable(exc)
                return
            event = (
                "item.application.completed"
                if result is ProtocolResult.APPLIED
                else "item.application.already_applied"
            )
            for entry in pending_entries:
                self._emit_item_event(
                    event,
                    "Permanent-item application durably observed.",
                    snapshot=result_snapshot,
                    item_id=entry.item_id,
                    index=entry.index,
                    revision=session.state.state_revision,
                    target_mask=target_mask,
                    command_id=result_snapshot.last_command_id,
                    outcome=result.name.casefold(),
                    attribution={
                        "location_id": entry.location_id,
                        "source_player": entry.source_player,
                        "flags": entry.flags,
                    },
                )
            self._item_confirmed_projection = projection
            self._item_diagnostic_drop_projection = (
                result_snapshot.diagnostic_activation_generation,
                result_snapshot.diagnostic_dropped_count,
            )
            self._item_reconcile_dirty = False
            self._item_failure_projection = None
            self._emit_item_event(
                "item.reconciliation.completed",
                "Permanent-item native target reconciliation completed.",
                snapshot=result_snapshot,
                revision=session.state.state_revision,
                target_mask=target_mask,
                command_id=result_snapshot.last_command_id,
                outcome=result.name.casefold(),
            )
            if self._item_recovery_pending:
                self._emit_item_event(
                    "item.recovery.completed",
                    "Permanent-item recovery completed from the durable ledger.",
                    snapshot=result_snapshot,
                    revision=session.state.state_revision,
                    target_mask=target_mask,
                    command_id=result_snapshot.last_command_id,
                    outcome=result.name.casefold(),
                )
                self._item_recovery_pending = False
            return

        if result is ProtocolResult.UNSAFE_NOW:
            self._item_reconcile_dirty = True
            self._item_queued_projection = None
            self._emit_item_event(
                "item.application.queued",
                "Native safety changed before permanent-item dispatch completed.",
                snapshot=result_snapshot,
                revision=session.state.state_revision,
                target_mask=target_mask,
                command_id=result_snapshot.last_command_id,
                outcome="unsafe_now",
                safety_reason="command_time_safety_gate",
            )
            return

        self._item_failure_projection = projection
        self._emit_item_event(
            "item.application.failed",
            "Permanent-item native reconciliation failed without ledger advancement.",
            snapshot=result_snapshot,
            revision=session.state.state_revision,
            target_mask=target_mask,
            command_id=result_snapshot.last_command_id,
            outcome=result.name.casefold(),
            reason=result_snapshot.last_error_code.name.casefold(),
        )

    def _request_item_sync_once(
        self, reason: str, index: object = None, *, already_sent: bool = False
    ) -> None:
        self._ensure_item_runtime()
        session = self.state_session
        expected = session.state.next_received_item_index if session else None
        projection = (reason, index, expected)
        if self._item_sync_projection == projection:
            return
        self._item_sync_projection = projection
        if already_sent:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        create_logged_task(
            self._send_item_sync(projection),
            "Milestone 8 canonical item Sync",
            getattr(self, "diagnostics", None),
        )

    async def _send_item_sync(self, projection: tuple[object, ...]) -> None:
        if not self.server:
            if self._item_sync_projection == projection:
                self._item_sync_projection = None
            return
        await self.send_msgs([{"cmd": "Sync"}])

    def _emit_item_event(
        self,
        event_name: str,
        message: str,
        *,
        snapshot: BridgeSnapshot | None = None,
        item_id: object = None,
        index: object = None,
        count: object = None,
        expected_index: object = None,
        revision: object = None,
        target_mask: object = None,
        command_id: object = None,
        safety_reason: object = None,
        outcome: object = None,
        reason: object = None,
        attribution: object = None,
        discrepancies: tuple[int, ...] | None = None,
    ) -> None:
        context = {
            "item_id": item_id,
            "item_name": (
                known_jak3_item_name(item_id) if type(item_id) is int else None
            ),
            "item_index": index,
            "packet_count": count,
            "expected_index": expected_index,
            "ledger_revision": revision,
            "target_mask": target_mask,
            "command_id": command_id,
            "safety_reason": safety_reason,
            "outcome": outcome,
            "reason": reason,
            "attribution": attribution,
            "history_discrepancy_count": (
                len(discrepancies) if discrepancies is not None else None
            ),
        }
        self.emit_diagnostic(
            event_name,
            message=message,
            source_component="client",
            correlation_id=(
                f"command:{command_id}"
                if type(command_id) is int
                else f"item:{index}"
                if type(index) is int
                else None
            ),
            runtime_state_sequence=(
                snapshot.snapshot_revision if snapshot is not None else None
            ),
            persistent_state_revision=(revision if type(revision) is int else None),
            context={key: value for key, value in context.items() if value is not None},
        )

    @staticmethod
    def _permanent_item_safety_reason(snapshot: BridgeSnapshot) -> str:
        if snapshot.loading:
            return "loading"
        if snapshot.in_cutscene:
            return "cutscene"
        if snapshot.dying_or_dead:
            return "dying_or_dead"
        if snapshot.mission_restarting:
            return "mission_restarting"
        if snapshot.level_transition:
            return "level_transition"
        if snapshot.in_vehicle:
            return "vehicle"
        if not snapshot.save_loaded:
            return "save_not_loaded"
        return "control_plane_unsafe"

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "RoomInfo":
            self._ensure_item_runtime()
            self._ensure_location_runtime()
            self._invalidate_location_transport()
            self._received_item_packets.clear()
            self._item_sync_projection = None
            self._item_runtime_projection = None
            self._item_confirmed_projection = None
            self._item_rejection_projection = None
            self._commonclient_received_item_count = len(
                getattr(self, "items_received", ())
            )
            self._item_reconcile_dirty = False
            self._location_read_only = False
            self._location_read_only_failure = ""
            self._server_checked_locations = None
            self._location_server_updates.clear()
            self._location_reconciled_state_instance = None
            self._location_last_send_projection = None
            self.close_persistence(clean=True)
            self._set_protocol_save_identity_authorized(False)
            self.protocol_sync_event.set()
            self.room_seed = args.get("seed_name", "")
            self.authenticated_slot = None
            self.slot_contract_error = ""
            self.persistence_contract_status = "awaiting Connected slot data"
            self.persistence_binding_status = "not attempted"
            self.persistence_read_only_failure = ""
            logger.info(
                "Received diagnostic RoomInfo seed_hash=%s; binding uses authenticated slot data.",
                hash_identifier(self.room_seed),
            )
        elif cmd == "Connected":
            self._invalidate_location_transport()
            try:
                slot_name = self.slot_info[args["slot"]].name
                self.authenticated_slot = AuthenticatedSlot.from_connected_packet(
                    args["slot_data"],
                    team=args["team"],
                    slot=args["slot"],
                    slot_name=slot_name,
                )
            except (
                AttributeError,
                KeyError,
                TypeError,
                StateCompatibilityError,
            ) as exc:
                self.authenticated_slot = None
                self._set_protocol_save_identity_authorized(False)
                self.protocol_sync_event.set()
                self.slot_contract_error = str(exc)
                self.persistence_contract_status = "rejected"
                self.persistence_binding_status = "refused read-only"
                self.persistence_read_only_failure = str(exc)
                logger.error(
                    "Authenticated Jak 3 slot data is incompatible; persistence binding "
                    "is disabled: %s",
                    exc,
                )
                self.emit_diagnostic(
                    "slot.contract.rejected",
                    message=str(exc),
                    source_component="client",
                    context={"reason": type(exc).__name__},
                )
                return
            self.slot_contract_error = ""
            self.compatibility_error = False
            proposal_ready = self._set_protocol_save_identity_authorized(True)
            self.protocol_sync_event.set()
            self.persistence_contract_status = "validated"
            if proposal_ready:
                self.persistence_binding_status = "awaiting native save identity"
                self.persistence_read_only_failure = ""
            logger.info(
                "Authenticated state contract seed_hash=%s team=%d slot=%d slot_hash=%s; "
                "native save binding awaits a valid runtime descriptor.",
                hash_identifier(self.authenticated_slot.seed_identifier),
                self.authenticated_slot.team,
                self.authenticated_slot.slot,
                hash_identifier(self.authenticated_slot.slot_name),
            )
            self.emit_diagnostic(
                "server.authenticated",
                message="Archipelago server slot authenticated.",
                source_component="client",
                context={
                    "seed_hash": hash_identifier(
                        self.authenticated_slot.seed_identifier
                    ),
                    "slot_hash": hash_identifier(self.authenticated_slot.slot_name),
                    "status": "authenticated",
                },
            )
            self.emit_diagnostic(
                "slot.contract.accepted",
                message="Authenticated slot contract accepted.",
                source_component="client",
                context={"status": "accepted"},
            )
            self._activate_location_transport()
            self._queue_server_location_update(args)
            self._ensure_item_runtime()
            self._item_reconcile_dirty = True
            self._item_confirmed_projection = None
            self._item_failure_projection = None
            if self.state_session is not None:
                self._request_item_sync_once("server_reconnect")
                self._schedule_item_worker()
            self._pump_location_outbox("server_reconnect")
        elif cmd == "RoomUpdate":
            self._queue_server_location_update(args)
        elif cmd == "ReceivedItems":
            self._observe_received_items(args)

    def _write_diagnostic_snapshot(self, reason: str) -> None:
        diagnostic: dict[str, object] = {
            "reason": reason,
            "runtime": self._diagnostic_runtime(),
            "persistence": self._diagnostic_persistence(),
            "versions": self._diagnostic_versions(),
            "commands": self._diagnostic_commands(),
        }
        logger.info("DIAGNOSTIC SNAPSHOT %r", diagnostic)
        self.diagnostics.note_opengoal(
            "CLIENT", f"diagnostic snapshot recorded: {reason}"
        )
        self.diagnostics.flush()

    def log_diagnostic_snapshot(self, reason: str) -> bool:
        try:
            self._write_diagnostic_snapshot(reason)
            return True
        except Exception:
            logger.exception("Could not write diagnostic snapshot reason=%r.", reason)
            return False

    def observe_runtime_diagnostics(self, snapshot: BridgeSnapshot) -> None:
        projection = (
            snapshot.game_status.name,
            snapshot.connection_ready,
            snapshot.save_loaded,
            snapshot.native_save_slot,
            hash_identifier(snapshot.native_save_identity)
            if snapshot.native_save_identity
            else None,
            snapshot.ap_state_loaded,
            snapshot.ap_state_bound,
            snapshot.current_level,
            snapshot.current_act,
            snapshot.current_task,
        )
        previous_projection = getattr(self, "_runtime_projection", None)
        if projection != previous_projection:
            self.emit_diagnostic(
                "runtime.state.changed",
                message="Observed runtime projection changed.",
                source_component="client",
                runtime_state_sequence=snapshot.snapshot_revision,
                context={
                    "runtime_state": {
                        "game_status": projection[0],
                        "connected": projection[1],
                        "save_loaded": projection[2],
                        "native_save_slot": projection[3],
                        "native_save_hash": projection[4],
                        "ap_state_loaded": projection[5],
                        "ap_state_bound": projection[6],
                        "level": projection[7],
                        "act": projection[8],
                        "task": projection[9],
                    }
                },
                details={"old": previous_projection, "new": projection},
            )
            self._runtime_projection = projection
        safety = (
            snapshot.safe_to_apply_permanent_item,
            snapshot.safe_to_apply_consumable,
            snapshot.safe_to_mutate_mission_state,
        )
        previous_safety = getattr(self, "_safety_projection", None)
        if safety != previous_safety:
            self.emit_diagnostic(
                "runtime.safety.changed",
                message="Observed runtime safety projection changed.",
                source_component="client",
                runtime_state_sequence=snapshot.snapshot_revision,
                context={
                    "safety_projection": {
                        "permanent": safety[0],
                        "consumable": safety[1],
                        "mission": safety[2],
                    }
                },
                details={"old": previous_safety, "new": safety},
            )
            self._safety_projection = safety

    def request_reconnect(self) -> None:
        self.compatibility_error = False
        self.last_bridge_error = "manual reconnect requested"
        self.bridge_ready = False
        self.reconnect_event.set()
        self.protocol_sync_event.set()
        create_logged_task(
            self.close_repl("manual_reconnect"),
            "close stale OpenGOAL connection",
            self.diagnostics,
        )

    async def mark_bridge_unavailable(self, error: Exception | str) -> None:
        self.last_bridge_error = str(error)
        self.bridge_ready = False
        self.source_loaded = False
        self.game_attached = False
        self.close_persistence(clean=False)
        if not getattr(self, "_communication_lost", False):
            if isinstance(error, Exception):
                timeout_failure = any(
                    marker in str(error).casefold()
                    for marker in ("timed out", "did not acknowledge")
                )
                self.emit_diagnostic(
                    "nrepl.timeout" if timeout_failure else "nrepl.failed",
                    message=str(error),
                    source_component="client",
                    context={"reason": type(error).__name__},
                )
            self.emit_diagnostic(
                "runtime.communication.lost",
                message=str(error),
                source_component="client",
                context={"reason": type(error).__name__},
            )
            self._communication_lost = True
        await self.close_repl("bridge_unavailable")

    def mark_bridge_reconnected(self) -> None:
        if not getattr(self, "_communication_lost", False):
            return
        self.emit_diagnostic(
            "runtime.communication.reconnected",
            message="OpenGOAL communication restored.",
            source_component="client",
        )
        self._communication_lost = False

    async def connect_repl(
        self, recompile: bool = False, report_errors: bool = True
    ) -> bool:
        startup_wait_visible = False
        protocol: BridgeProtocol | None = None
        self.protocol = None
        manifest = load_packaged_manifest()
        startup_source = str(
            next(
                module for module in manifest.modules if module.phase == "pre_mi"
            ).destination
        )
        runtime_sources = tuple(
            str(module.destination) for module in manifest.runtime_modules
        )
        diagnostic_source = str(
            next(
                module
                for module in manifest.runtime_modules
                if module.name == "diagnostics"
            ).destination
        )

        goal_source_state = getattr(self, "_goal_source_state", None)
        if goal_source_state is None:
            goal_source_state = {}
            self._goal_source_state = goal_source_state

        def reset_goal_source() -> bool:
            reset = getattr(self.diagnostics, "reset_goal_event_source", None)
            if callable(reset):
                try:
                    reset()
                except BaseException:
                    return False
            goal_source_state.clear()
            return True

        async def load_runtime_modules(
            sources: tuple[str, ...] = runtime_sources,
        ) -> None:
            for source in sources:
                await self.repl.send_form(f'(ml "{source}")', timeout=60.0)
                self.emit_diagnostic(
                    "bridge.source.loaded",
                    message="Manifest-declared OpenGOAL bridge module loaded.",
                    source_component="client",
                    context={"source": Path(source).name},
                )

        try:
            self.emit_diagnostic(
                "nrepl.connecting",
                message="Connecting to OpenGOAL nREPL.",
                source_component="client",
            )
            await self.repl.connect()
            await self.repl.attach()
            self.emit_diagnostic(
                "nrepl.attached",
                message="Attached to OpenGOAL compiler target.",
                source_component="client",
            )
            self.game_attached = True
            if recompile:
                logger.info("Recompiling Jak 3. This may take a few minutes...")
                self.diagnostics.note_opengoal(
                    "CLIENT", "starting full Jak 3 (mi) compilation"
                )
                await self.repl.send_form("(set! *debug-segment* #t)")
                await self.repl.send_form(
                    '(m "goal_src/jak3/pc/features/archipelago-bootstrap-types.gc")',
                    timeout=120.0,
                )
                self.diagnostics.note_opengoal(
                    "CLIENT",
                    "Jak 3 bootstrap type database compiled for startup overlay",
                )
                await self.repl.send_form(
                    f'(ml "{startup_source}")',
                    timeout=60.0,
                )
                await self.repl.send_form("(ap-bootstrap-show-startup-wait!)")
                startup_wait_visible = True
                logger.info(
                    "The game is compiling. Wait for the flashing in-game message to disappear."
                )
                await self.repl.send_form("(mi)", timeout=600.0)
                self.compile_completed = True
                self.diagnostics.note_opengoal(
                    "CLIENT", "(mi) completion barrier acknowledged"
                )

            # Re-loading an unchanged protocol-3 source would also reset its
            # game-session nonce and receipt ring. Probe first unless the
            # installer found changed source that must replace the live object.
            force_source_reload = getattr(self, "bridge_source_reload_required", False)
            source_already_loaded = False
            diagnostics_already_loaded = False
            pre_reload_activation_generation: int | None = None
            pre_reload_diagnostic_activation_generation: int | None = None
            probed_snapshot: BridgeSnapshot | None = None
            self.state_path.unlink(missing_ok=True)
            await self.repl.send_form(
                f"(ap-set-state-path! {goal_path_literal(str(self.state_path))})"
            )
            for _probe in range(10):
                candidate = read_snapshot(self.state_path)
                if candidate is not None:
                    probed_snapshot = candidate
                    pre_reload_activation_generation = (
                        candidate.bridge_activation_generation
                    )
                    pre_reload_diagnostic_activation_generation = (
                        candidate.diagnostic_activation_generation
                    )
                    if not force_source_reload:
                        source_already_loaded = _loaded_bridge_matches_current_contract(
                            candidate
                        )
                        diagnostics_already_loaded = (
                            _loaded_diagnostics_matches_current_contract(candidate)
                        )
                    break
                await asyncio.sleep(0.05)
            previous_game_nonce = getattr(self, "_goal_game_session_nonce", None)
            if (
                source_already_loaded
                and previous_game_nonce is not None
                and probed_snapshot is not None
                and probed_snapshot.session_nonce != previous_game_nonce
            ):
                # A fresh game process starts with no game-session nonce and a
                # new diagnostic ring even though its manifest-loaded bridge
                # already matches the public contract. Reset Python's GOAL
                # high-water mark before the preliminary snapshot is drained.
                reset_goal_source()
            if source_already_loaded and not diagnostics_already_loaded:
                # Diagnostic compatibility is optional and must never reset a
                # healthy Protocol 3 control module (nonce, receipts, or test
                # target). Repair only the diagnostic sibling, best effort.
                try:
                    await load_runtime_modules((diagnostic_source,))
                    self.state_path.unlink(missing_ok=True)
                    await self.repl.send_form(
                        f"(ap-set-state-path! {goal_path_literal(str(self.state_path))})"
                    )
                    for _probe in range(10):
                        candidate = read_snapshot(self.state_path)
                        if (
                            candidate is not None
                            and _loaded_bridge_matches_current_contract(candidate)
                            and _loaded_diagnostics_matches_current_contract(candidate)
                            and candidate.diagnostic_activation_generation
                            != pre_reload_diagnostic_activation_generation
                        ):
                            diagnostics_already_loaded = True
                            reset_goal_source()
                            break
                        await asyncio.sleep(0.05)
                    if not diagnostics_already_loaded:
                        raise ValueError(
                            "diagnostic activation generation was not observed"
                        )
                except (ConnectionError, OSError, ValueError) as exc:
                    self.emit_diagnostic(
                        "diagnostics.capture_gap",
                        message="Optional GOAL diagnostic module could not be loaded.",
                        source_component="client",
                        context={"reason": type(exc).__name__},
                    )
                    self.diagnostics.note_opengoal(
                        "CLIENT", f"optional diagnostic module load failed: {exc}"
                    )
            if not source_already_loaded:
                if force_source_reload:
                    self.diagnostics.note_opengoal(
                        "CLIENT",
                        "reloading live bridge because packaged source changed",
                    )
                    self.emit_diagnostic(
                        "bridge.reload.started",
                        message="Manifest-ordered live bridge reload started.",
                        source_component="client",
                        context={
                            "source_set_hash": getattr(
                                self, "bridge_source_set_hash", "unknown"
                            )
                        },
                    )
                await load_runtime_modules()
                reset_goal_source()
                if force_source_reload and pre_reload_activation_generation is None:
                    # A first install or legacy bridge has no comparable
                    # generation. Establish a current-source baseline, then
                    # load once more so activation can still be proven rather
                    # than trusting the transport completion barrier.
                    self.state_path.unlink(missing_ok=True)
                    await self.repl.send_form(
                        f"(ap-set-state-path! {goal_path_literal(str(self.state_path))})"
                    )
                    for _probe in range(10):
                        candidate = read_snapshot(self.state_path)
                        if (
                            candidate is not None
                            and _loaded_bridge_matches_current_contract(candidate)
                            and _loaded_diagnostics_matches_current_contract(candidate)
                        ):
                            pre_reload_activation_generation = (
                                candidate.bridge_activation_generation
                            )
                            pre_reload_diagnostic_activation_generation = (
                                candidate.diagnostic_activation_generation
                            )
                            break
                        await asyncio.sleep(0.05)
                    if pre_reload_activation_generation is None:
                        raise ConnectionError(
                            "OpenGOAL did not publish current bridge module activation "
                            "generations after source load; the reload marker was retained."
                        )
                    await load_runtime_modules()
                    reset_goal_source()
                if force_source_reload:
                    self.state_path.unlink(missing_ok=True)
                    await self.repl.send_form(
                        f"(ap-set-state-path! {goal_path_literal(str(self.state_path))})"
                    )
                    activated_snapshot = None
                    for _probe in range(10):
                        candidate = read_snapshot(self.state_path)
                        if (
                            candidate is not None
                            and _loaded_bridge_matches_current_contract(candidate)
                            and _loaded_diagnostics_matches_current_contract(candidate)
                            and candidate.bridge_activation_generation
                            != pre_reload_activation_generation
                            and candidate.diagnostic_activation_generation
                            != pre_reload_diagnostic_activation_generation
                        ):
                            activated_snapshot = candidate
                            break
                        await asyncio.sleep(0.05)
                    if activated_snapshot is None:
                        raise ConnectionError(
                            "OpenGOAL completed the source-load request without "
                            "publishing new compatible bridge module activation generations; "
                            "the reload marker was retained."
                        )
                    reload_marker = getattr(self, "bridge_source_reload_marker", None)
                    if reload_marker is not None:
                        reload_marker.unlink(missing_ok=True)
                    self.bridge_source_reload_required = False
                    self.emit_diagnostic(
                        "bridge.reload.activated",
                        message="New bridge activation generation verified.",
                        source_component="client",
                        runtime_state_sequence=activated_snapshot.snapshot_revision,
                        context={
                            "source_set_hash": getattr(
                                self, "bridge_source_set_hash", "unknown"
                            )
                        },
                    )
            if startup_wait_visible:
                await self.repl.send_form(
                    '(kill-by-name "ap-startup-wait" *display-pool*)'
                )
                startup_wait_visible = False
                self.diagnostics.note_opengoal(
                    "CLIENT", "flashing in-game compilation wait message removed"
                )
            if recompile:
                await self.repl.send_form("(set! *debug-segment* #f)")
                await self.repl.send_form("(set! *cheat-mode* #f)")

            event_sink = getattr(self.diagnostics, "event_sink", None)
            timed_out_commands = getattr(self, "_timed_out_commands", None)
            if timed_out_commands is None:
                timed_out_commands = {}
                self._timed_out_commands = timed_out_commands
            protocol = BridgeProtocol(
                self.repl,
                self.state_path,
                self.diagnostics.session_id,
                self._create_authorized_save_identity,
                event_sink=event_sink if callable(event_sink) else None,
                goal_event_sink=self._ingest_goal_events,
                goal_event_reset=reset_goal_source,
                goal_source_state=goal_source_state,
                timed_out_commands=timed_out_commands,
            )
            self.protocol = protocol
            self._set_protocol_save_identity_authorized(
                self.authenticated_slot is not None
            )
            snapshot = await protocol.initialize(self.client_status)
            self._goal_game_session_nonce = snapshot.session_nonce
            self.sync_persistence(snapshot)
            self.source_loaded = True
            self.bridge_ready = True
            self.compatibility_error = False
            self.last_bridge_error = ""
            self.observe_runtime_diagnostics(snapshot)
            self.mark_bridge_reconnected()
            logger.info(
                "Jak 3 handshake ready protocol=%d integration=%d session=%s status=%s.",
                snapshot.protocol_version,
                snapshot.game_integration_version,
                snapshot.session_id,
                snapshot.game_status.name,
            )
            self.diagnostics.note_opengoal(
                "CLIENT",
                f"handshake ready protocol={snapshot.protocol_version} "
                f"integration={snapshot.game_integration_version} session={snapshot.session_id}",
            )
            self.log_diagnostic_snapshot("handshake ready")
            return True
        except ProtocolCompatibilityError as exc:
            self.source_loaded = (
                self.protocol is not None and self.protocol.last_snapshot is not None
            )
            self.bridge_ready = False
            self.compatibility_error = True
            self.last_bridge_error = str(exc)
            logger.error("%s", exc)
            self.diagnostics.note_opengoal("CLIENT", f"compatibility failure: {exc}")
            self.emit_diagnostic(
                "protocol.handshake.rejected",
                message=str(exc),
                source_component="client",
                context={"reason": type(exc).__name__},
            )
            self.close_persistence(clean=False)
            await self.close_repl("compatibility_rejected")
            self.game_attached = False
            return False
        except (ConnectionError, OSError, ValueError) as exc:
            if self.bridge_source_reload_required:
                self.emit_diagnostic(
                    "bridge.reload.failed",
                    message=str(exc),
                    source_component="client",
                    context={"reason": type(exc).__name__},
                )
                if "activation generation" in str(exc).casefold():
                    self.emit_diagnostic(
                        "bridge.restart_required",
                        message=(
                            "Live bridge activation could not be proven; restart "
                            "OpenGOAL before retrying."
                        ),
                        source_component="client",
                        context={"reason": "activation_generation_not_observed"},
                    )
            await self.mark_bridge_unavailable(exc)
            logger.debug("OpenGOAL connection/handshake attempt failed: %s", exc)
            self.diagnostics.note_opengoal(
                "CLIENT", f"connection/handshake attempt failed: {exc}"
            )
            if report_errors:
                logger.error("Could not establish the Jak 3 handshake: %s", exc)
                logger.debug("OpenGOAL handshake failure traceback", exc_info=True)
            return False

    async def auto_start_opengoal(self) -> bool:
        """Install the bridge, start missing processes, and establish the handshake."""

        async with self.startup_lock:
            try:
                install = await asyncio.to_thread(find_install)
                logger.info(
                    "Resolved OpenGOAL install binaries=%s project=%s iso=%s.",
                    install.binary_directory,
                    install.project_directory,
                    install.iso_directory,
                )
                self.emit_diagnostic(
                    "opengoal.install.discovered",
                    message="OpenGOAL Jak 3 installation discovered.",
                    source_component="client",
                    context={"path_hash": hash_identifier(install.project_directory)},
                )
                result = await asyncio.to_thread(install_packaged_bridge, install)
                self.bridge_source_reload_marker = result.reload_marker_path
                self.bridge_source_reload_required = result.reload_required
                self.bridge_source_set_hash = result.source_set_hash
                logger.info(
                    "Installed/verified handshake source=%s source_updated=%s "
                    "reload_required=%s project_updated=%s "
                    "startup_updated=%s bootstrap_types_updated=%s sha256=%s.",
                    result.source_path,
                    result.source_updated,
                    result.reload_required,
                    result.project_updated,
                    result.startup_updated,
                    result.bootstrap_types_updated,
                    result.source_set_hash,
                )
                self.emit_diagnostic(
                    "bridge.install.repaired"
                    if result.modules_updated
                    or result.project_updated
                    or result.manifest_updated
                    else "bridge.install.verified",
                    message="Manifest-declared OpenGOAL bridge installation verified.",
                    source_component="client",
                    context={
                        "source_set_hash": result.source_set_hash,
                        "status": "repaired"
                        if result.modules_updated
                        or result.project_updated
                        or result.manifest_updated
                        else "verified",
                    },
                    details={"count": len(result.modules_updated)},
                )
                if result.reload_required:
                    self.emit_diagnostic(
                        "bridge.reload.required",
                        message="Installed bridge source set requires live activation.",
                        source_component="client",
                        context={"source_set_hash": result.source_set_hash},
                    )
                launch_result = await asyncio.to_thread(
                    launch_missing_processes, install, self.diagnostics
                )
                logger.info(
                    "OpenGOAL startup game_started=%s game_pid=%s "
                    "compiler_started=%s compiler_pid=%s.",
                    launch_result.game_started,
                    launch_result.game_pid,
                    launch_result.compiler_started,
                    launch_result.compiler_pid,
                )
                logger.debug(
                    "OpenGOAL gk command: %s",
                    subprocess.list2cmdline(launch_result.game_command),
                )
                logger.debug(
                    "OpenGOAL goalc command: %s",
                    subprocess.list2cmdline(launch_result.compiler_command),
                )
            except (FileNotFoundError, OSError, ValueError, KeyError) as exc:
                logger.error("Automatic OpenGOAL startup failed: %s", exc)
                logger.debug("Automatic OpenGOAL startup traceback", exc_info=True)
                self.diagnostics.note_opengoal(
                    "CLIENT", f"automatic startup failed: {exc}"
                )
                self.emit_diagnostic(
                    "bridge.install.failed",
                    message=str(exc),
                    source_component="client",
                    context={"reason": type(exc).__name__},
                )
                self.last_bridge_error = str(exc)
                return False

            for _attempt in range(30):
                should_recompile = not self.compile_completed
                if await self.connect_repl(
                    recompile=should_recompile, report_errors=False
                ):
                    return True
                if self.compatibility_error:
                    return False
                await asyncio.sleep(2)
            logger.error(
                "OpenGOAL did not become handshake-ready within 60 seconds; use /repl connect "
                "to retry. Review %s.",
                self.diagnostics.opengoal_log,
            )
            self.log_diagnostic_snapshot("OpenGOAL handshake timeout")
            return False


async def protocol_supervisor(ctx: Jak3Context) -> None:
    """Maintain a harmless versioned heartbeat across either process restarting."""

    while not ctx.exit_event.is_set():
        ctx.diagnostics.refresh_session_marker()
        if not ctx.bridge_ready or ctx.protocol is None:
            if not ctx.compatibility_error:
                await ctx.auto_start_opengoal()
            if ctx.bridge_ready and ctx.protocol is not None:
                # A Connected packet may have arrived while hello was in
                # flight. Do not add the normal retry delay before the first
                # ping publishes its authorized save-identity proposal.
                ctx.reconnect_event.clear()
                continue
            try:
                await asyncio.wait_for(ctx.reconnect_event.wait(), timeout=2.0)
                ctx.reconnect_event.clear()
                ctx.compatibility_error = False
            except asyncio.TimeoutError:
                pass
            continue

        try:
            # Consume authorization/state changes already reflected in Python;
            # changes arriving during this ping remain set and trigger another
            # immediate synchronization below.
            ctx.protocol_sync_event.clear()
            snapshot = await ctx.protocol.ping(ctx.client_status)
            ctx.sync_persistence(snapshot)
            ctx.observe_runtime_diagnostics(snapshot)
            logger.debug(
                "Jak 3 heartbeat client=%d game=%d status=%s message=%s.",
                snapshot.client_heartbeat,
                snapshot.game_heartbeat,
                snapshot.game_status.name,
                snapshot.message,
            )
        except (ConnectionError, OSError, ValueError) as exc:
            logger.warning(
                "Jak 3 heartbeat lost; reconnecting without touching gameplay: %s", exc
            )
            ctx.diagnostics.note_opengoal("CLIENT", f"heartbeat lost: {exc}")
            await ctx.mark_bridge_unavailable(exc)
            continue

        try:
            await asyncio.wait_for(
                ctx.protocol_sync_event.wait(), timeout=PING_INTERVAL_SECONDS
            )
        except asyncio.TimeoutError:
            pass
        if ctx.reconnect_event.is_set():
            ctx.reconnect_event.clear()
            ctx.protocol_sync_event.clear()
            await ctx.mark_bridge_unavailable("reconnect requested")


async def main() -> None:
    diagnostics = DiagnosticSession.create()
    diagnostics.initialize()
    diagnostics.install_exception_capture(asyncio.get_running_loop())
    diagnostics.emit(
        "client.started",
        message="Jak 3 Archipelago client started.",
        source_component="client",
    )
    ctx = Jak3Context(None, None, diagnostics)
    logger.info("Temporary bridge snapshot path=%s.", ctx.state_path)
    logger.info("Persistent AP state root=%s.", ctx.persistence_root)
    logger.info("Use /repl status or /diagnostics to inspect the handshake.")
    ctx.server_task = create_logged_task(server_loop(ctx), "server loop", diagnostics)
    supervisor = create_logged_task(
        protocol_supervisor(ctx), "Jak3 protocol supervisor", diagnostics
    )
    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()
    await ctx.exit_event.wait()
    ctx._stopping = True
    diagnostics.emit(
        "client.stopping",
        message="Jak 3 Archipelago client stopping.",
        source_component="client",
    )
    supervisor.cancel()
    try:
        await supervisor
    except asyncio.CancelledError:
        pass
    if ctx.bridge_ready and ctx.protocol is not None:
        try:
            await asyncio.wait_for(ctx.protocol.disconnect(), timeout=2.0)
        except (asyncio.TimeoutError, ConnectionError, OSError):
            logger.debug("Could not publish clean client disconnect.", exc_info=True)
    ctx.close_persistence(clean=True)
    ctx.log_diagnostic_snapshot("client shutdown")
    diagnostics.note_opengoal("CLIENT", "Jak 3 client shutdown requested")
    await ctx.close_repl("client_shutdown")
    await ctx.shutdown()
    diagnostics.emit(
        "client.stopped",
        message="Jak 3 Archipelago client stopped.",
        source_component="client",
    )
    diagnostics.close(clean=True)


def _goal_string_literal(value: str) -> str:
    """Compatibility alias for tests and controlled protocol strings."""

    return goal_string_literal(value)


def _goal_path_literal(value: str) -> str:
    """Compatibility alias for tests and temporary state paths."""

    return goal_path_literal(value)


def launch() -> None:
    colorama.just_fix_windows_console()
    asyncio.run(main())
    colorama.deinit()
