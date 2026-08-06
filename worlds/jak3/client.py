"""Archipelago client for the Jak 3 OpenGOAL bridge.

OpenGOAL's nREPL handles commands going into the game.  A tiny text snapshot
written by the GOAL mod handles completed task IDs coming back out.  The
protocol is deliberately append/order independent and all operations include
the Archipelago receive index, making reconnects safe.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import tempfile
import zlib
from collections import Counter, deque
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

import colorama
from CommonClient import ClientCommandProcessor, CommonContext, gui_enabled, server_loop
from NetUtils import ClientStatus

from .agents.diagnostics import DiagnosticSession
from .agents.launcher import find_install, install_packaged_bridge, launch_missing_processes
from .agents.repl_client import OpenGoalRepl

from .data import (
    ACTIVITIES,
    ACTIVITY_REQUIREMENTS,
    CHECK_BY_TASK,
    EQUIPMENT,
    FILLER_KIND_BY_NAME,
    GAME_NAME,
    ITEM_NAME_TO_ID,
    LOCATION_NAME_TO_ID,
    MISSION_BY_ID,
    MISSION_REQUIREMENTS,
    MISSIONS,
    STARTING_MISSION_ID,
    TRAP_KIND_BY_NAME,
)


# Use CommonClient's logger so command and bridge status messages are visible
# in both the text console and the Archipelago GUI log pane.
logger = logging.getLogger("Client")
BACKGROUND_TASKS: set[asyncio.Task] = set()
PROTOCOL_VERSION = 1
ITEM_ID_TO_TASK = {
    mission.item_id: mission.task_id
    for mission in MISSIONS
    if mission.item_id is not None
}
TRAP_ID_TO_KIND = {
    ITEM_NAME_TO_ID[name]: kind for name, kind in TRAP_KIND_BY_NAME.items()
}
EQUIPMENT_ID_TO_DATA = {ITEM_NAME_TO_ID[item.name]: item for item in EQUIPMENT}
ITEM_ID_TO_NAME = {item_id: name for name, item_id in ITEM_NAME_TO_ID.items()}
FILLER_ID_TO_KIND = {
    ITEM_NAME_TO_ID[name]: kind for name, kind in FILLER_KIND_BY_NAME.items()
}


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
        """Compile/connect OpenGOAL (`/repl connect`) or show bridge status."""
        if action == "connect":
            self.output("Installing, compiling, and connecting Jak 3 through OpenGOAL...")
            create_logged_task(self.ctx.auto_start_opengoal(), "manual OpenGOAL startup")
        else:
            server_status = "connected" if self.ctx.server else "disconnected"
            repl_status = "connected" if self.ctx.repl.connected else "disconnected"
            bridge_status = "ready" if self.ctx.bridge_ready else "not bound"
            self.output(f"Archipelago server: {server_status}")
            self.output(f"OpenGOAL nREPL: {repl_status}")
            self.output(f"Jak 3 bridge: {bridge_status}")
            self.output(f"Slot: {self.ctx.auth or 'not authenticated'}")
            self.output(f"State file: {self.ctx.state_path}")

    def _cmd_diagnostics(self) -> None:
        """Record current state and show the two files needed for troubleshooting."""

        written = self.ctx.log_diagnostic_snapshot("manual /diagnostics command")
        if written:
            self.output("Diagnostic snapshot written. Provide both files when reporting an issue:")
        else:
            self.output("Diagnostic snapshot failed; the logs still contain the failure traceback:")
        self.output(f"Client/logic: {self.ctx.diagnostics.client_log}")
        self.output(f"Game/compiler: {self.ctx.diagnostics.opengoal_log}")

    def _cmd_missions(self) -> None:
        """List mission and challenge task IDs currently unlocked for this slot."""
        unlocked = self.ctx.unlocked_tasks()
        if not unlocked:
            self.output("No missions are currently playable. Check /repl status and your received items.")
            return
        self.output(f"Playable Jak 3 missions ({len(unlocked)}):")
        for task_id in sorted(unlocked):
            self.output(f"{task_id:3d}  {CHECK_BY_TASK[task_id].name}")

    def _cmd_game(self, action: str = "status") -> None:
        """Boot gameplay: `/game start`, `/game title`, or `/game sync`."""
        action = action.casefold()
        if action not in {"start", "title", "sync"}:
            state = "ready" if self.ctx.bridge_ready else "not ready"
            self.output(
                f"Jak 3 AP game startup is {state}. Use /game start for a new game, "
                "/game title to load a save, or /game sync after loading it."
            )
            return
        if not self.ctx.bridge_ready:
            self.output("The Jak 3 bridge is not ready. Connect to the room, then run /repl connect.")
            return
        if action == "start":
            self.output("Starting a fresh Jak 3 Archipelago game...")
            create_logged_task(self.ctx.start_game(), "start Jak 3 game")
        elif action == "title":
            self.output("Opening the normal Jak 3 title screen...")
            create_logged_task(self.ctx.open_title(), "open Jak 3 title")
        else:
            self.output("Reapplying this slot's received AP inventory...")
            create_logged_task(self.ctx.sync_items(), "resynchronize Jak 3 items")

    def _cmd_play(self, *mission: str) -> None:
        """Start an unlocked mission by native task ID or a unique part of its name."""
        if not self.ctx.bridge_ready:
            self.output("The Jak 3 bridge is not ready. Connect to the room, then run /repl connect.")
            return
        query = " ".join(mission).strip()
        task_id = self.ctx.resolve_task(query)
        if task_id is None:
            self.output("Mission must be a task ID or unique name shown by /missions.")
            return
        self.output(f"Starting task {task_id}: {CHECK_BY_TASK[task_id].name}")
        create_logged_task(self.ctx.play_task(task_id), f"play Jak 3 task {task_id}")


class Jak3Context(CommonContext):
    game = GAME_NAME
    items_handling = 0b111
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
        self.slot_data: dict = {}
        self.room_seed = ""
        self.sent_item_index = 0
        self.completed_tasks: set[int] = set()
        self.bridge_ready = False
        self.bound_game: tuple[int, int] | None = None
        self.received_history_ready = False
        self.pending_notifications: deque[tuple[int, str]] = deque()
        self.notification_sequence = -1
        self.startup_lock = asyncio.Lock()
        self.last_logged_game_state: tuple[int, frozenset[int]] | None = None

    def queue_notification(self, message: str) -> None:
        """Queue one new-session HUD message behind the bridge acknowledgement."""

        acknowledged = parse_notification_index(self.state_path)
        self.notification_sequence = max(self.notification_sequence, acknowledged) + 1
        self.pending_notifications.append((self.notification_sequence, message[:96]))
        logger.info(
            "Queued HUD notification index=%d acknowledged=%d text=%r.",
            self.notification_sequence,
            acknowledged,
            message[:96],
        )

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "RoomInfo":
            self.room_seed = args.get("seed_name", "")
            logger.info("Received RoomInfo seed_name=%r.", self.room_seed)
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            self.bridge_ready = False
            self.received_history_ready = False
            self.pending_notifications.clear()
            logger.info(
                "Authenticated slot=%r slot_data=%s",
                self.auth,
                json.dumps(self.slot_data, sort_keys=True, default=str),
            )
            create_logged_task(self.setup_bridge(), "bind Jak 3 bridge")
        if cmd == "ReceivedItems":
            packet_items = list(args.get("items", ()))
            packet_index = args.get("index", "unknown")
            logger.info(
                "ReceivedItems packet index=%s count=%d replay=%s.",
                packet_index,
                len(packet_items),
                not self.received_history_ready,
            )
            for offset, item in enumerate(packet_items):
                item_id = int(item.item if hasattr(item, "item") else item[0])
                location_id = int(item.location if hasattr(item, "location") else item[1])
                sender = int(item.player if hasattr(item, "player") else item[2])
                logger.debug(
                    "Received item packet_offset=%d id=%d name=%r location=%d sender=%d.",
                    offset,
                    item_id,
                    ITEM_ID_TO_NAME.get(item_id, "Foreign or unknown item"),
                    location_id,
                    sender,
                )
            # CommonClient has already appended this packet before invoking
            # this hook. The first packet is connection history/replay; later
            # packets are genuinely new receipts and receive HUD notices.
            if self.received_history_ready:
                for item in packet_items:
                    item_id = int(item.item if hasattr(item, "item") else item[0])
                    name = ITEM_ID_TO_NAME.get(item_id, "Unknown Item")
                    self.queue_notification(f"Received: {name}")
            else:
                self.received_history_ready = True
        self.watcher_event.set()

    def on_print_json(self, args: dict) -> None:
        """Mirror newly sent items onto the in-game HUD."""

        if self.received_history_ready and args.get("type") == "ItemSend":
            item = args.get("item")
            recipient = args.get("receiving")
            if item is not None and recipient is not None and self.slot_concerns_self(item.player):
                item_name = self.item_names.lookup_in_slot(item.item, recipient)
                owner = "yourself" if self.slot_concerns_self(recipient) else self.player_names[recipient]
                self.queue_notification(f"Sent: {item_name} to {owner}")
                logger.info(
                    "Observed ItemSend item_id=%d item_name=%r recipient=%d owner=%r.",
                    item.item,
                    item_name,
                    recipient,
                    owner,
                )
        super().on_print_json(args)

    def _write_diagnostic_snapshot(self, reason: str) -> None:
        """Write enough AP and bridge state to investigate logic/protocol bugs."""

        received = [
            {
                "index": index,
                "item_id": int(item.item),
                "name": ITEM_ID_TO_NAME.get(int(item.item), "Foreign or unknown item"),
                "location_id": int(item.location),
                "sender": int(item.player),
            }
            for index, item in enumerate(self.items_received)
        ]
        snapshot = {
            "reason": reason,
            "server_connected": bool(self.server),
            "authenticated": bool(self.auth),
            "slot_name": self.auth,
            "room_seed": self.room_seed,
            "slot_data": self.slot_data,
            "repl_connected": self.repl.connected,
            "bridge_ready": self.bridge_ready,
            "bound_game": self.bound_game,
            "state_path": str(self.state_path),
            "bridge_state": parse_state_details(self.state_path),
            "received_count": len(received),
            "sent_item_index": self.sent_item_index,
            "received_items": received,
            "completed_tasks": sorted(self.completed_tasks),
            "unlocked_tasks": sorted(self.unlocked_tasks()),
            "locations_checked_local": sorted(self.locations_checked),
            "locations_checked_server": sorted(self.checked_locations),
            "pending_notifications": list(self.pending_notifications),
            "client_log": str(self.diagnostics.client_log),
            "opengoal_log": str(self.diagnostics.opengoal_log),
        }
        logger.info("DIAGNOSTIC SNAPSHOT %s", json.dumps(snapshot, sort_keys=True, default=str))
        self.diagnostics.note_opengoal("CLIENT", f"diagnostic snapshot recorded: {reason}")
        self.diagnostics.flush()

    def log_diagnostic_snapshot(self, reason: str) -> bool:
        """Write a snapshot without allowing diagnostics to disrupt gameplay."""

        try:
            self._write_diagnostic_snapshot(reason)
            return True
        except Exception:
            logger.exception("Could not write diagnostic snapshot reason=%r.", reason)
            return False

    async def connect_repl(self, recompile: bool = False, report_errors: bool = True) -> bool:
        startup_wait_visible = False
        try:
            await self.repl.connect()
            await self.repl.attach()
            if recompile:
                logger.info("Recompiling Jak 3. This may take a few minutes...")
                self.diagnostics.note_opengoal("CLIENT", "starting full Jak 3 (mi) compilation")
                await self.repl.send_form("(set! *debug-segment* #t)")
                # A fresh goalc process initially knows only the kernel types.
                # Compile a safe prefix of OpenGOAL's generated Jak 3 type
                # database so the small
                # display process can be compiled before the blocking full
                # build begins. Its generated object is not loaded into the
                # target and it does not replace the normal (mi) build.
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
                    "The game is compiling. Wait for the flashing in-game message to disappear "
                    "and the title menu to open."
                )
                self.diagnostics.note_opengoal(
                    "CLIENT", "flashing in-game compilation wait message requested"
                )
                await self.repl.send_form("(mi)", timeout=600.0)
                self.diagnostics.note_opengoal("CLIENT", "(mi) completion barrier acknowledged")
            await self.repl.send_form(
                '(ml "goal_src/jak3/pc/features/archipelago.gc")', timeout=60.0
            )
            if startup_wait_visible:
                # The full build has now imported the normal kernel globals,
                # so cleanup no longer depends on the bootstrap definitions
                # remaining in the compiler namespace.
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
            log_path = _goal_path_literal(str(self.diagnostics.opengoal_log))
            await self.repl.send_form(f"(ap-set-log-path! {log_path})")
            state_path = _goal_path_literal(str(self.state_path))
            await self.repl.send_form(f"(ap-set-state-path! {state_path})")
            await self.repl.send_form("(ap-init!)")
            for _attempt in range(20):
                if parse_state_details(self.state_path).get("version") == PROTOCOL_VERSION:
                    break
                await asyncio.sleep(0.1)
            else:
                raise ConnectionError(
                    "The loaded bridge did not write its protocol state file. Review the paired "
                    f"OpenGOAL log: {self.diagnostics.opengoal_log}"
                )
            # Match the Jak 1 client: compilation finishes at the normal title
            # sequence so the player can choose options, start, or load a save.
            await self.repl.send_form("(ap-open-title!)", timeout=30.0)
            logger.info("OpenGOAL compilation complete; the normal Jak 3 title menu was opened.")
            self.diagnostics.note_opengoal(
                "CLIENT", "bridge verified and normal Jak 3 title menu opened"
            )
            self.sent_item_index = 0
            self.bridge_ready = False
            await self.setup_bridge()
            if not self.auth or not self.room_seed:
                logger.warning(
                    "OpenGOAL is connected, but the client is not authenticated to an "
                    "Archipelago room. Connect to the room, then run /repl connect again."
                )
            elif self.bridge_ready:
                logger.info("Jak 3 bridge is ready for slot %s.", self.auth)
            self.log_diagnostic_snapshot("post-compile title ready")
            self.watcher_event.set()
            return True
        except (ConnectionError, OSError) as exc:
            await self.repl.close()
            self.bridge_ready = False
            logger.debug("OpenGOAL connection/compile attempt failed: %s", exc)
            self.diagnostics.note_opengoal("CLIENT", f"connection/compile attempt failed: {exc}")
            if report_errors:
                logger.error("Could not connect to OpenGOAL: %s", exc)
                logger.debug("OpenGOAL failure traceback", exc_info=True)
            return False

    async def auto_start_opengoal(self) -> None:
        """Start gk/goalc, compile, attach the bridge, and open the title screen."""

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
                startup_hash = hashlib.sha256(result.startup_path.read_bytes()).hexdigest()
                if (result.source_updated or result.project_updated or result.startup_updated
                        or result.bootstrap_types_updated):
                    logger.info(
                        "Installed the APWorld OpenGOAL sources into %s "
                        "(bridge_updated=%s startup_updated=%s bootstrap_types_updated=%s "
                        "project_updated=%s "
                        "bridge_sha256=%s startup_sha256=%s).",
                        install.project_directory,
                        result.source_updated,
                        result.startup_updated,
                        result.bootstrap_types_updated,
                        result.project_updated,
                        bridge_hash,
                        startup_hash,
                    )
                else:
                    logger.info(
                        "The installed OpenGOAL sources are already current "
                        "(bridge_sha256=%s startup_sha256=%s).",
                        bridge_hash,
                        startup_hash,
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
                if not launch_result.game_started or not launch_result.compiler_started:
                    logger.warning(
                        "An OpenGOAL process was already running, so its earlier output cannot be "
                        "included in this session's OpenGOAL log. For a complete reproduction, "
                        "close old gk/goalc processes and relaunch Jak 3 Client."
                    )
            except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
                logger.exception(
                    "Automatic OpenGOAL startup traceback.", extra={"NoStream": True}
                )
                logger.error("Automatic OpenGOAL startup failed: %s", exc)
                self.diagnostics.note_opengoal("CLIENT", f"automatic startup failed: {exc}")
                logger.error(
                    "Install Jak 3 in OpenGOAL Launcher or set JAK3_OPENGOAL_BIN and "
                    "JAK3_OPENGOAL_PROJECT, then use /repl connect."
                )
                return

            # The compiler opens its nREPL asynchronously. Retry for one minute
            # without blocking the Archipelago UI.
            for _attempt in range(30):
                await asyncio.sleep(2)
                if await self.connect_repl(recompile=True, report_errors=False):
                    return
            logger.error(
                "OpenGOAL goalc did not become ready within 60 seconds; use /repl connect to retry. "
                "Compiler diagnostics: %s",
                self.diagnostics.opengoal_log,
            )
            self.log_diagnostic_snapshot("OpenGOAL startup timeout")

    async def setup_bridge(self) -> None:
        if not self.repl.connected or not self.auth or not self.room_seed:
            logger.debug(
                "Bridge setup deferred repl_connected=%s authenticated=%s room_seed=%s.",
                self.repl.connected,
                bool(self.auth),
                bool(self.room_seed),
            )
            return
        slot_key = zlib.crc32(self.auth.encode("utf-8")) & 0x7FFF_FFFF
        seed_key = zlib.crc32(self.room_seed.encode("utf-8")) & 0x7FFF_FFFF
        try:
            state_path = _goal_path_literal(str(self.state_path))
            await self.repl.send_form(f"(ap-set-state-path! {state_path})")
            await self.repl.send_form(f"(ap-setup! {slot_key} {seed_key})")
            if parse_binding(self.state_path) != (slot_key, seed_key):
                raise ConnectionError(
                    "OpenGOAL finished setup, but the bridge state file did not confirm "
                    "the current slot and seed. Check the goalc window for a compilation error."
                )
            game_key = (slot_key, seed_key)
            if self.bound_game != game_key:
                self.completed_tasks.clear()
                self.sent_item_index = 0
                self.finished_game = False
            self.bound_game = game_key
            self.bridge_ready = True
            logger.info(
                "Bound the Jak 3 bridge slot=%r slot_key=%d seed_key=%d state=%s.",
                self.auth,
                slot_key,
                seed_key,
                json.dumps(parse_state_details(self.state_path), sort_keys=True),
            )
            self.watcher_event.set()
        except (ConnectionError, OSError) as exc:
            self.bridge_ready = False
            logger.warning("Could not bind OpenGOAL to this slot and seed: %s", exc)
            logger.debug("Bridge binding traceback", exc_info=True)

    def unlocked_tasks(self) -> set[int]:
        received = Counter(item.item for item in self.items_received)
        mission_unlock_count = sum(
            1 for item_id in ITEM_ID_TO_TASK if received[item_id]
        )
        tasks = {
            mission.task_id
            for mission in MISSIONS
            if (mission.task_id == STARTING_MISSION_ID
                or received[ITEM_NAME_TO_ID[mission.item_name]])
            and self._has_requirements(received, MISSION_REQUIREMENTS.get(mission.task_id, ()))
        }
        tasks.update(
            activity.task_id
            for activity in ACTIVITIES
            if mission_unlock_count >= activity.unlock_count
            and self._has_requirements(received, ACTIVITY_REQUIREMENTS.get(activity.task_id, ()))
        )
        return tasks

    @staticmethod
    def _has_requirements(
        received: Counter[int], requirements: tuple[tuple[str, int], ...]
    ) -> bool:
        return all(received[ITEM_NAME_TO_ID[name]] >= count for name, count in requirements)

    def resolve_task(self, query: str) -> int | None:
        if query.isdigit():
            task_id = int(query)
            return task_id if task_id in self.unlocked_tasks() else None
        matches = [
            task_id for task_id in self.unlocked_tasks()
            if query.casefold() in CHECK_BY_TASK[task_id].name.casefold()
        ]
        return matches[0] if query and len(matches) == 1 else None

    async def play_task(self, task_id: int) -> None:
        if task_id not in self.unlocked_tasks():
            logger.warning(
                "Task %d (%s) is not unlocked; currently unlocked=%s.",
                task_id,
                CHECK_BY_TASK.get(task_id).name if task_id in CHECK_BY_TASK else "unknown",
                sorted(self.unlocked_tasks()),
            )
            return
        try:
            await self.repl.send_form(f"(ap-play-task! (the-as game-task {task_id}))")
            logger.info(
                "OpenGOAL finished dispatching Jak 3 task %d (%s).",
                task_id,
                CHECK_BY_TASK[task_id].name,
            )
        except ConnectionError as exc:
            logger.error("%s; run /repl connect first.", exc)

    async def start_game(self) -> None:
        """Leave the Debug spawn and perform Jak 3's normal New Game transition."""
        try:
            await self.repl.send_form("(ap-start-game!)", timeout=30.0)
            # The GOAL initializer intentionally resets this index so the
            # watcher reapplies all previously received inventory safely.
            self.sent_item_index = 0
            logger.info(
                "Jak 3 New Game initialization dispatched. The intro may take a moment to load."
            )
            self.watcher_event.set()
        except ConnectionError as exc:
            logger.error("Could not start normal Jak 3 gameplay: %s", exc)

    async def open_title(self) -> None:
        """Open Jak 3's normal title UI so an existing AP save can be loaded."""
        try:
            await self.repl.send_form("(ap-open-title!)", timeout=30.0)
            logger.info("Jak 3 title initialization dispatched. Select the save for this AP slot.")
        except ConnectionError as exc:
            logger.error("Could not open the Jak 3 title screen: %s", exc)

    async def sync_items(self) -> None:
        """Reapply authoritative AP inventory after a vanilla save load."""
        try:
            await self.repl.send_form("(ap-resync-items!)")
            self.sent_item_index = 0
            self.watcher_event.set()
            logger.info("Received AP inventory is being reapplied.")
        except ConnectionError as exc:
            logger.error("Could not resynchronize AP inventory: %s", exc)


def parse_state_details(path: Path) -> dict[str, Any]:
    """Parse the complete small bridge snapshot for diagnostics and watchers."""

    details: dict[str, Any] = {
        "exists": False,
        "version": None,
        "slot": None,
        "seed": None,
        "received": 0,
        "notification": -1,
        "completed": [],
    }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return details
    except (OSError, UnicodeError) as exc:
        details["read_error"] = f"{type(exc).__name__}: {exc}"
        return details
    details["exists"] = True
    for line in lines:
        key, _, values = line.partition(" ")
        if key in {"version", "slot", "seed", "received"} and values.isdigit():
            details[key] = int(values)
        elif key == "notification" and values.lstrip("-").isdigit():
            details[key] = int(values)
        elif key == "completed":
            details[key] = sorted(
                int(value) for value in values.split() if value.isdigit()
            )
    return details


def parse_state(path: Path) -> tuple[int, set[int]]:
    """Return `(received_index, completed_tasks)` from a bridge snapshot."""

    details = parse_state_details(path)
    completed = set(details["completed"]) & set(CHECK_BY_TASK)
    return int(details["received"]), completed


def parse_binding(path: Path) -> tuple[int, int] | None:
    """Return the slot/seed keys confirmed by a bridge snapshot."""
    details = parse_state_details(path)
    if details["slot"] is not None and details["seed"] is not None:
        return int(details["slot"]), int(details["seed"])
    return None


def parse_notification_index(path: Path) -> int:
    """Return the latest HUD notification index acknowledged by the bridge."""
    return int(parse_state_details(path)["notification"])


async def sync_items(ctx: Jak3Context, game_received_index: int) -> None:
    if not ctx.repl.connected or not ctx.bridge_ready:
        return
    if ctx.sent_item_index != min(ctx.sent_item_index, game_received_index):
        logger.info(
            "Game receive cursor moved backward client_index=%d game_index=%d; replaying safely.",
            ctx.sent_item_index,
            game_received_index,
        )
    ctx.sent_item_index = min(ctx.sent_item_index, game_received_index)
    while ctx.sent_item_index < len(ctx.items_received):
        index = ctx.sent_item_index
        item_id = ctx.items_received[index].item
        item_name = ITEM_ID_TO_NAME.get(item_id, "Foreign or unknown item")
        dispatch = "foreign filler"
        if item_id in ITEM_ID_TO_TASK:
            form = f"(ap-receive-mission! (the-as game-task {ITEM_ID_TO_TASK[item_id]}) {index})"
            dispatch = f"mission task {ITEM_ID_TO_TASK[item_id]}"
        elif item_id in EQUIPMENT_ID_TO_DATA:
            equipment = EQUIPMENT_ID_TO_DATA[item_id]
            level = sum(received.item == item_id for received in ctx.items_received[:index + 1])
            form = f"(ap-receive-upgrade! {equipment.kind} {level} {index})"
            dispatch = f"upgrade kind {equipment.kind} level {level}"
        elif item_id in TRAP_ID_TO_KIND:
            duration = int(ctx.slot_data.get("trap_duration", 30))
            form = f"(ap-receive-trap! {TRAP_ID_TO_KIND[item_id]} {duration} {index})"
            dispatch = f"trap kind {TRAP_ID_TO_KIND[item_id]} duration {duration}"
        elif item_id in FILLER_ID_TO_KIND:
            form = f"(ap-receive-filler! {FILLER_ID_TO_KIND[item_id]} {index})"
            dispatch = f"filler kind {FILLER_ID_TO_KIND[item_id]}"
        else:
            # Foreign filler has no safe Jak 3 effect, but still advances the
            # idempotent receive index.
            form = f"(ap-receive-filler! -1 {index})"
        logger.info(
            "Applying received item index=%d id=%d name=%r dispatch=%s.",
            index,
            item_id,
            item_name,
            dispatch,
        )
        logger.debug("Item nREPL form: %s", form)
        try:
            await ctx.repl.send_form(form)
        except (ConnectionError, OSError) as exc:
            logger.warning("OpenGOAL item sync paused: %s", exc)
            await ctx.repl.close()
            return
        ctx.sent_item_index += 1


def _goal_string_literal(value: str) -> str:
    """Encode controlled notification text as a bounded GOAL string literal."""
    safe = "".join(character if 32 <= ord(character) < 127 else "?" for character in value[:96])
    return '"' + safe.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _goal_path_literal(value: str) -> str:
    """Encode an absolute shared-state path as a GOAL string literal."""
    if not value or len(value) > 500 or any(ord(character) < 32 for character in value):
        raise ValueError("JAK3_AP_STATE must be a non-empty path of at most 500 characters")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


async def sync_notification(ctx: Jak3Context, acknowledged_index: int) -> None:
    """Show the next new receipt only when the game HUD can own the alert."""
    if not ctx.pending_notifications or not ctx.repl.connected or not ctx.bridge_ready:
        return
    while ctx.pending_notifications and ctx.pending_notifications[0][0] <= acknowledged_index:
        ctx.pending_notifications.popleft()
    if not ctx.pending_notifications:
        return
    try:
        item_index, text = ctx.pending_notifications[0]
        message = _goal_string_literal(text)
        logger.debug("Attempting HUD notification index=%d text=%r.", item_index, text)
        await ctx.repl.send_form(f"(ap-try-notification! {message} {item_index})")
    except (ConnectionError, OSError) as exc:
        logger.warning("OpenGOAL notification sync paused: %s", exc)
        await ctx.repl.close()


async def game_watcher(ctx: Jak3Context) -> None:
    while not ctx.exit_event.is_set():
        game_received_index, completed = parse_state(ctx.state_path)
        if not ctx.bridge_ready:
            completed = set()
        state_key = (game_received_index, frozenset(completed))
        if state_key != ctx.last_logged_game_state:
            logger.debug(
                "Bridge state changed received_index=%d completed_tasks=%s ready=%s.",
                game_received_index,
                sorted(completed),
                ctx.bridge_ready,
            )
            ctx.last_logged_game_state = state_key
        newly_completed = completed - ctx.completed_tasks
        for task_id in sorted(newly_completed):
            check = CHECK_BY_TASK[task_id]
            logger.info(
                "Game completed task=%d check=%r location=%r location_id=%d.",
                task_id,
                check.name,
                check.location_name,
                LOCATION_NAME_TO_ID[check.location_name],
            )
        ctx.completed_tasks |= completed
        new_locations = {
            LOCATION_NAME_TO_ID[CHECK_BY_TASK[task_id].location_name]
            for task_id in ctx.completed_tasks
            if task_id in CHECK_BY_TASK
        }
        if new_locations and ctx.server and ctx.bridge_ready:
            unsent_locations = new_locations - ctx.locations_checked - ctx.checked_locations
            if unsent_locations:
                logger.info("Submitting location checks to server: %s.", sorted(unsent_locations))
            await ctx.check_locations(new_locations)

        if ctx.server and ctx.slot_data and ctx.bridge_ready and not ctx.finished_game:
            mode = int(ctx.slot_data.get("completion_condition", 1))
            specific = int(ctx.slot_data.get("specific_mission", 71))
            count = int(ctx.slot_data.get("mission_count", 66))
            completed_story = ctx.completed_tasks & set(MISSION_BY_ID)
            won = specific in completed_story if mode == 0 else len(completed_story) >= count
            if won:
                logger.info(
                    "Goal condition reached mode=%d specific=%d required_count=%d completed_story=%d.",
                    mode,
                    specific,
                    count,
                    len(completed_story),
                )
                await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                ctx.finished_game = True

        await sync_items(ctx, game_received_index)
        await sync_notification(ctx, parse_notification_index(ctx.state_path))
        try:
            await asyncio.wait_for(ctx.watcher_event.wait(), timeout=0.5)
            ctx.watcher_event.clear()
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    diagnostics = DiagnosticSession.create()
    diagnostics.initialize()
    ctx = Jak3Context(None, None, diagnostics)
    logger.info("Transient bridge state path=%s.", ctx.state_path)
    logger.info(
        "Use /diagnostics at any time to record logic state and display both support log paths."
    )
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    watcher = create_logged_task(game_watcher(ctx), "Jak3 game watcher")
    startup = create_logged_task(ctx.auto_start_opengoal(), "Jak3 OpenGOAL startup")
    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()
    await ctx.exit_event.wait()
    ctx.log_diagnostic_snapshot("client shutdown")
    diagnostics.note_opengoal("CLIENT", "Jak 3 client shutdown requested")
    watcher.cancel()
    startup.cancel()
    try:
        await watcher
    except asyncio.CancelledError:
        pass
    try:
        await startup
    except asyncio.CancelledError:
        pass
    await ctx.repl.close()
    await ctx.shutdown()
    diagnostics.flush()


def launch() -> None:
    colorama.just_fix_windows_console()
    asyncio.run(main())
    colorama.deinit()
