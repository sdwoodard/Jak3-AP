"""Archipelago client for the protocol-3 Jak 3 observation/test bridge.

Milestone 7 binds persistent state to an observed native-save identity and
persists harmless command receipts.  It still does not request items, submit
locations, report a goal, intercept rewards, or modify mission state.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import tempfile
from collections.abc import Awaitable
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import colorama  # type: ignore[import-untyped]
from CommonClient import ClientCommandProcessor, CommonContext, gui_enabled, server_loop

from .agents.diagnostics import DiagnosticSession
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
    goal_path_literal,
    goal_string_literal,
    read_snapshot,
    validate_compatibility,
)
from .agents.repl_client import OpenGoalRepl
from .game_id import GAME_NAME
from .persistence import (
    AuthenticatedSlot,
    GameCommandReceipt,
    NativeSaveDescriptor,
    NativeSaveEligibility,
    StateBindingError,
    StateError,
    StateCompatibilityError,
    StateRepository,
    StateSession,
    default_state_root,
)
from .registry import ITEM_TABLE_HASH, LOCATION_TABLE_HASH, MISSION_TABLE_HASH
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


def _loaded_bridge_matches_current_contract(snapshot: BridgeSnapshot) -> bool:
    """Preserve a live bridge only when every protocol contract field matches."""

    try:
        validate_compatibility(snapshot)
    except ProtocolCompatibilityError:
        return False
    return True


def create_logged_task(awaitable: Awaitable[Any], name: str) -> asyncio.Task:
    """Run a background action without losing its exception from diagnostics."""

    async def run_and_log() -> Any:
        try:
            return await awaitable
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Background task %s failed.", name)
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
                f"seed={binding.seed_identifier} team={binding.team} "
                f"slot={binding.slot} name={binding.slot_name}"
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

    def _cmd_diagnostics(self) -> None:
        """Record current state and show the two files needed for troubleshooting."""

        written = self.ctx.log_diagnostic_snapshot("manual /diagnostics command")
        if written:
            self.output(
                "Diagnostic snapshot written. Provide both files when reporting an issue:"
            )
        else:
            self.output(
                "Diagnostic snapshot failed; the logs still contain the failure traceback:"
            )
        self.output(f"Client/protocol: {self.ctx.diagnostics.client_log}")
        self.output(f"Game/compiler: {self.ctx.diagnostics.opengoal_log}")


class Jak3Context(CommonContext):
    game = GAME_NAME
    # Milestone 7 deliberately asks the AP server for no ReceivedItems stream.
    items_handling = 0
    command_processor = Jak3CommandProcessor

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
        self.state_repository = StateRepository(self.persistence_root)
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
        self.startup_lock = asyncio.Lock()
        self.reconnect_event = asyncio.Event()
        self.protocol_sync_event = asyncio.Event()
        self._stopping = False

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
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def close_persistence(self, *, clean: bool) -> None:
        session = self.state_session
        self.state_session = None
        if session is not None:
            try:
                session.close(clean=clean)
            except StateError as exc:
                self.persistence_binding_status = "refused read-only"
                self.persistence_read_only_failure = str(exc)
                logger.error("Could not close the AP state session cleanly: %s", exc)
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
            if self.state_session is not None:
                self.close_persistence(clean=True)
            self.persistence_binding_status = (
                "awaiting authenticated slot"
                if self.authenticated_slot is None
                else "awaiting valid native save identity"
            )
            return
        assert native_save_identity is not None

        eligibility = (
            NativeSaveEligibility.FRESH_UNPROGRESSED
            if snapshot.native_save_eligibility
            is SnapshotSaveEligibility.FRESH_UNPROGRESSED
            else NativeSaveEligibility.INELIGIBLE
        )
        descriptor = NativeSaveDescriptor(
            slot=snapshot.native_save_slot,
            identity=native_save_identity,
            eligibility=eligibility,
        )
        if (
            self.state_session is not None
            and self.state_session.native_save != descriptor
        ):
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
        if session.state.last_observed_game_command_receipt != persisted:
            session.commit(
                replace(session.state, last_observed_game_command_receipt=persisted)
            )

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "RoomInfo":
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
                "Received diagnostic RoomInfo seed_name=%r; binding uses authenticated slot data.",
                self.room_seed,
            )
        elif cmd == "Connected":
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
                return
            self.slot_contract_error = ""
            proposal_ready = self._set_protocol_save_identity_authorized(True)
            self.protocol_sync_event.set()
            self.persistence_contract_status = "validated"
            if proposal_ready:
                self.persistence_binding_status = "awaiting native save identity"
                self.persistence_read_only_failure = ""
            logger.info(
                "Authenticated state contract seed=%r team=%d slot=%d name=%r; "
                "native save binding awaits a valid runtime descriptor.",
                self.authenticated_slot.seed_identifier,
                self.authenticated_slot.team,
                self.authenticated_slot.slot,
                self.authenticated_slot.slot_name,
            )

    def _write_diagnostic_snapshot(self, reason: str) -> None:
        snapshot = self.latest_snapshot
        diagnostic = {
            "reason": reason,
            "server_connected": bool(self.server),
            "authenticated": bool(self.auth),
            "slot_name": self.auth,
            "room_seed": self.room_seed,
            "repl_connected": self.repl.connected,
            "game_attached": self.game_attached,
            "source_loaded": self.source_loaded,
            "bridge_ready": self.bridge_ready,
            "client_status": self.client_status.name,
            "expected_protocol_version": PROTOCOL_VERSION,
            "expected_game_integration_version": GAME_INTEGRATION_VERSION,
            "expected_bridge_runtime_version": BRIDGE_RUNTIME_VERSION,
            "slot_data_version": SLOT_DATA_VERSION,
            "state_schema_version": STATE_SCHEMA_VERSION,
            "item_table_version": ITEM_TABLE_VERSION,
            "location_table_version": LOCATION_TABLE_VERSION,
            "mission_table_version": MISSION_TABLE_VERSION,
            "item_table_hash": ITEM_TABLE_HASH,
            "location_table_hash": LOCATION_TABLE_HASH,
            "mission_table_hash": MISSION_TABLE_HASH,
            "session_id": self.diagnostics.session_id,
            "state_path": str(self.state_path),
            "persistence_root": str(self.persistence_root),
            "persistence_contract_status": self.persistence_contract_status,
            "persistence_binding_status": self.persistence_binding_status,
            "persistence_recovery_status": self.persistence_recovery_status,
            "persistence_quarantine_status": self.persistence_quarantine_status,
            "persistence_read_only_failure": self.persistence_read_only_failure,
            "slot_contract": (
                None
                if self.authenticated_slot is None
                else {
                    "seed_identifier": self.authenticated_slot.seed_identifier,
                    "team": self.authenticated_slot.team,
                    "slot": self.authenticated_slot.slot,
                    "slot_name": self.authenticated_slot.slot_name,
                }
            ),
            "slot_contract_error": self.slot_contract_error,
            "bridge_state": asdict(snapshot) if snapshot is not None else None,
            "last_bridge_error": self.last_bridge_error,
            "client_log": str(self.diagnostics.client_log),
            "opengoal_log": str(self.diagnostics.opengoal_log),
        }
        logger.info(
            "DIAGNOSTIC SNAPSHOT %s",
            json.dumps(diagnostic, sort_keys=True, default=str),
        )
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

    def request_reconnect(self) -> None:
        self.compatibility_error = False
        self.last_bridge_error = "manual reconnect requested"
        self.bridge_ready = False
        self.reconnect_event.set()
        self.protocol_sync_event.set()
        create_logged_task(self.repl.close(), "close stale OpenGOAL connection")

    async def mark_bridge_unavailable(self, error: Exception | str) -> None:
        self.last_bridge_error = str(error)
        self.bridge_ready = False
        self.source_loaded = False
        self.game_attached = False
        self.close_persistence(clean=False)
        await self.repl.close()

    async def connect_repl(
        self, recompile: bool = False, report_errors: bool = True
    ) -> bool:
        startup_wait_visible = False
        protocol: BridgeProtocol | None = None
        self.protocol = None
        try:
            await self.repl.connect()
            await self.repl.attach()
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
                    '(ml "goal_src/jak3/pc/features/archipelago-startup.gc")',
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
            pre_reload_activation_generation: int | None = None
            self.state_path.unlink(missing_ok=True)
            await self.repl.send_form(
                f"(ap-set-state-path! {goal_path_literal(str(self.state_path))})"
            )
            for _probe in range(10):
                candidate = read_snapshot(self.state_path)
                if candidate is not None:
                    pre_reload_activation_generation = (
                        candidate.bridge_activation_generation
                    )
                    if not force_source_reload:
                        source_already_loaded = _loaded_bridge_matches_current_contract(
                            candidate
                        )
                    break
                await asyncio.sleep(0.05)
            if not source_already_loaded:
                if force_source_reload:
                    self.diagnostics.note_opengoal(
                        "CLIENT",
                        "reloading live bridge because packaged source changed",
                    )
                await self.repl.send_form(
                    '(ml "goal_src/jak3/pc/features/archipelago.gc")', timeout=60.0
                )
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
                        ):
                            pre_reload_activation_generation = (
                                candidate.bridge_activation_generation
                            )
                            break
                        await asyncio.sleep(0.05)
                    if pre_reload_activation_generation is None:
                        raise ConnectionError(
                            "OpenGOAL did not publish a current bridge activation "
                            "generation after source load; the reload marker was retained."
                        )
                    await self.repl.send_form(
                        '(ml "goal_src/jak3/pc/features/archipelago.gc")', timeout=60.0
                    )
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
                            and candidate.bridge_activation_generation
                            != pre_reload_activation_generation
                        ):
                            activated_snapshot = candidate
                            break
                        await asyncio.sleep(0.05)
                    if activated_snapshot is None:
                        raise ConnectionError(
                            "OpenGOAL completed the source-load request without "
                            "publishing a new compatible bridge activation generation; "
                            "the reload marker was retained."
                        )
                    reload_marker = getattr(self, "bridge_source_reload_marker", None)
                    if reload_marker is not None:
                        reload_marker.unlink(missing_ok=True)
                    self.bridge_source_reload_required = False
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

            log_path = goal_path_literal(str(self.diagnostics.opengoal_log))
            await self.repl.send_form(f"(ap-set-log-path! {log_path})")
            protocol = BridgeProtocol(
                self.repl,
                self.state_path,
                self.diagnostics.session_id,
                self._create_authorized_save_identity,
            )
            self.protocol = protocol
            self._set_protocol_save_identity_authorized(
                self.authenticated_slot is not None
            )
            snapshot = await protocol.initialize(self.client_status)
            self.sync_persistence(snapshot)
            self.source_loaded = True
            self.bridge_ready = True
            self.compatibility_error = False
            self.last_bridge_error = ""
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
            self.close_persistence(clean=False)
            await self.repl.close()
            self.game_attached = False
            return False
        except (ConnectionError, OSError, ValueError) as exc:
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
                result = await asyncio.to_thread(install_packaged_bridge, install)
                self.bridge_source_reload_marker = result.reload_marker_path
                self.bridge_source_reload_required = result.reload_required
                bridge_hash = hashlib.sha256(
                    result.source_path.read_bytes()
                ).hexdigest()
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
                    bridge_hash,
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
    ctx = Jak3Context(None, None, diagnostics)
    logger.info("Temporary bridge snapshot path=%s.", ctx.state_path)
    logger.info("Persistent AP state root=%s.", ctx.persistence_root)
    logger.info("Use /repl status or /diagnostics to inspect the handshake.")
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    supervisor = create_logged_task(
        protocol_supervisor(ctx), "Jak3 protocol supervisor"
    )
    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()
    await ctx.exit_event.wait()
    ctx._stopping = True
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
    await ctx.repl.close()
    await ctx.shutdown()
    diagnostics.flush()


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
