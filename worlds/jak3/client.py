"""Archipelago client and lifecycle supervisor for the Jak 3 handshake bridge.

Protocol 2 intentionally verifies only process attachment, source compatibility,
session status, and a harmless ping/pong. It does not process received items,
submit locations, report a goal, or modify missions or saves.
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
from dataclasses import asdict
from pathlib import Path
from typing import Any

import colorama
from CommonClient import ClientCommandProcessor, CommonContext, gui_enabled, server_loop

from .agents.diagnostics import DiagnosticSession
from .agents.launcher import find_install, install_packaged_bridge, launch_missing_processes
from .agents.protocol import (
    GAME_INTEGRATION_VERSION,
    PING_INTERVAL_SECONDS,
    PROTOCOL_VERSION,
    BridgeProtocol,
    BridgeSnapshot,
    ClientStatus,
    ProtocolCompatibilityError,
    goal_path_literal,
    goal_string_literal,
    read_snapshot,
)
from .agents.repl_client import OpenGoalRepl
from .data import GAME_NAME


logger = logging.getLogger("Client")
BACKGROUND_TASKS: set[asyncio.Task] = set()


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
        self.output(f"Archipelago server: {'connected' if self.ctx.server else 'disconnected'}")
        self.output(f"OpenGOAL nREPL: {'connected' if self.ctx.repl.connected else 'disconnected'}")
        self.output(f"Game target attached: {'yes' if self.ctx.game_attached else 'no'}")
        self.output(f"AP source loaded: {'yes' if self.ctx.source_loaded else 'no'}")
        self.output(f"Handshake ready: {'yes' if self.ctx.bridge_ready else 'no'}")
        self.output(f"Expected protocol/integration: {PROTOCOL_VERSION}/{GAME_INTEGRATION_VERSION}")
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
        self.output(f"State file: {self.ctx.state_path}")

    def _cmd_diagnostics(self) -> None:
        """Record current state and show the two files needed for troubleshooting."""

        written = self.ctx.log_diagnostic_snapshot("manual /diagnostics command")
        if written:
            self.output("Diagnostic snapshot written. Provide both files when reporting an issue:")
        else:
            self.output("Diagnostic snapshot failed; the logs still contain the failure traceback:")
        self.output(f"Client/protocol: {self.ctx.diagnostics.client_log}")
        self.output(f"Game/compiler: {self.ctx.diagnostics.opengoal_log}")


class Jak3Context(CommonContext):
    game = GAME_NAME
    # Protocol 2 deliberately asks the AP server for no ReceivedItems stream.
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
        self.room_seed = ""
        self.protocol: BridgeProtocol | None = None
        self.game_attached = False
        self.source_loaded = False
        self.bridge_ready = False
        self.last_bridge_error = ""
        self.compatibility_error = False
        self.compile_completed = False
        self.startup_lock = asyncio.Lock()
        self.reconnect_event = asyncio.Event()
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

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "RoomInfo":
            self.room_seed = args.get("seed_name", "")
            logger.info(
                "Received RoomInfo seed_name=%r; handshake remains save/room independent.",
                self.room_seed,
            )
        elif cmd == "Connected":
            logger.info(
                "Authenticated slot=%r; protocol 2 does not bind room or save state.",
                self.auth,
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
            "session_id": self.diagnostics.session_id,
            "state_path": str(self.state_path),
            "bridge_state": asdict(snapshot) if snapshot is not None else None,
            "last_bridge_error": self.last_bridge_error,
            "client_log": str(self.diagnostics.client_log),
            "opengoal_log": str(self.diagnostics.opengoal_log),
        }
        logger.info("DIAGNOSTIC SNAPSHOT %s", json.dumps(diagnostic, sort_keys=True, default=str))
        self.diagnostics.note_opengoal("CLIENT", f"diagnostic snapshot recorded: {reason}")
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
        create_logged_task(self.repl.close(), "close stale OpenGOAL connection")

    async def mark_bridge_unavailable(self, error: Exception | str) -> None:
        self.last_bridge_error = str(error)
        self.bridge_ready = False
        self.source_loaded = False
        self.game_attached = False
        await self.repl.close()

    async def connect_repl(self, recompile: bool = False, report_errors: bool = True) -> bool:
        startup_wait_visible = False
        protocol: BridgeProtocol | None = None
        self.protocol = None
        try:
            await self.repl.connect()
            await self.repl.attach()
            self.game_attached = True
            if recompile:
                logger.info("Recompiling Jak 3. This may take a few minutes...")
                self.diagnostics.note_opengoal("CLIENT", "starting full Jak 3 (mi) compilation")
                await self.repl.send_form("(set! *debug-segment* #t)")
                await self.repl.send_form(
                    '(m "goal_src/jak3/pc/features/archipelago-bootstrap-types.gc")',
                    timeout=120.0,
                )
                self.diagnostics.note_opengoal(
                    "CLIENT", "Jak 3 bootstrap type database compiled for startup overlay"
                )
                await self.repl.send_form(
                    '(ml "goal_src/jak3/pc/features/archipelago-startup.gc")', timeout=60.0
                )
                await self.repl.send_form("(ap-bootstrap-show-startup-wait!)")
                startup_wait_visible = True
                logger.info(
                    "The game is compiling. Wait for the flashing in-game message to disappear."
                )
                await self.repl.send_form("(mi)", timeout=600.0)
                self.compile_completed = True
                self.diagnostics.note_opengoal("CLIENT", "(mi) completion barrier acknowledged")

            await self.repl.send_form(
                '(ml "goal_src/jak3/pc/features/archipelago.gc")', timeout=60.0
            )
            if startup_wait_visible:
                await self.repl.send_form('(kill-by-name "ap-startup-wait" *display-pool*)')
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
            )
            self.protocol = protocol
            snapshot = await protocol.initialize(self.client_status)
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
                bridge_hash = hashlib.sha256(result.source_path.read_bytes()).hexdigest()
                logger.info(
                    "Installed/verified handshake source=%s source_updated=%s project_updated=%s "
                    "startup_updated=%s bootstrap_types_updated=%s sha256=%s.",
                    result.source_path,
                    result.source_updated,
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
                self.diagnostics.note_opengoal("CLIENT", f"automatic startup failed: {exc}")
                self.last_bridge_error = str(exc)
                return False

            for _attempt in range(30):
                should_recompile = not self.compile_completed
                if await self.connect_repl(recompile=should_recompile, report_errors=False):
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
            try:
                await asyncio.wait_for(ctx.reconnect_event.wait(), timeout=2.0)
                ctx.reconnect_event.clear()
                ctx.compatibility_error = False
            except asyncio.TimeoutError:
                pass
            continue

        try:
            snapshot = await ctx.protocol.ping(ctx.client_status)
            logger.debug(
                "Jak 3 heartbeat client=%d game=%d status=%s message=%s.",
                snapshot.client_heartbeat,
                snapshot.game_heartbeat,
                snapshot.game_status.name,
                snapshot.message,
            )
        except (ConnectionError, OSError, ValueError) as exc:
            logger.warning("Jak 3 heartbeat lost; reconnecting without touching gameplay: %s", exc)
            ctx.diagnostics.note_opengoal("CLIENT", f"heartbeat lost: {exc}")
            await ctx.mark_bridge_unavailable(exc)
            continue

        try:
            await asyncio.wait_for(ctx.reconnect_event.wait(), timeout=PING_INTERVAL_SECONDS)
            ctx.reconnect_event.clear()
            await ctx.mark_bridge_unavailable("reconnect requested")
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    diagnostics = DiagnosticSession.create()
    diagnostics.initialize()
    ctx = Jak3Context(None, None, diagnostics)
    logger.info("Temporary protocol state path=%s.", ctx.state_path)
    logger.info("Use /repl status or /diagnostics to inspect the handshake.")
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    supervisor = create_logged_task(protocol_supervisor(ctx), "Jak3 protocol supervisor")
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
