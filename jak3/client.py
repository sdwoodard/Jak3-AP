"""Archipelago client for the Jak 3 OpenGOAL bridge.

OpenGOAL's nREPL handles commands going into the game.  A tiny text snapshot
written by the GOAL mod handles completed task IDs coming back out.  The
protocol is deliberately append/order independent and all operations include
the Archipelago receive index, making reconnects safe.
"""

from __future__ import annotations

import asyncio
import logging
import os
import struct
import tempfile
import zlib
from collections import Counter, deque
from pathlib import Path

import colorama
import Utils
from CommonClient import ClientCommandProcessor, CommonContext, gui_enabled, server_loop
from NetUtils import ClientStatus

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
    TRAPS,
)


# Use CommonClient's logger so command and bridge status messages are visible
# in both the text console and the Archipelago GUI log pane.
logger = logging.getLogger("Client")
ITEM_ID_TO_TASK = {
    ITEM_NAME_TO_ID[mission.item_name]: mission.task_id
    for mission in MISSIONS
    if mission.task_id != STARTING_MISSION_ID
}
TRAP_ID_TO_INDEX = {ITEM_NAME_TO_ID[name]: index for index, name in enumerate(TRAPS)}
EQUIPMENT_ID_TO_DATA = {ITEM_NAME_TO_ID[item.name]: item for item in EQUIPMENT}
ITEM_ID_TO_NAME = {item_id: name for name, item_id in ITEM_NAME_TO_ID.items()}
FILLER_ID_TO_KIND = {
    ITEM_NAME_TO_ID[name]: kind for name, kind in FILLER_KIND_BY_NAME.items()
}


class OpenGoalRepl:
    def __init__(self, host: str = "127.0.0.1", port: int = 8181) -> None:
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing()

    async def connect(self) -> None:
        if self.connected:
            return
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        try:
            welcome_data = await asyncio.wait_for(self.reader.read(1024), timeout=10.0)
        except asyncio.TimeoutError as exc:
            await self.close()
            raise ConnectionError("Timed out waiting for the OpenGOAL nREPL greeting") from exc
        welcome = welcome_data.decode(errors="replace")
        if "nREPL" not in welcome:
            await self.close()
            raise ConnectionError(f"Unexpected OpenGOAL nREPL greeting: {welcome!r}")
        logger.info("Connected to the Jak 3 OpenGOAL nREPL socket.")
        attach_response = await self.send_form("(lt)", timeout=30.0)
        if "nREPL" not in attach_response:
            raise ConnectionError(
                "OpenGOAL did not attach to the game. Start a fresh goalc, run (mi), "
                "and let /repl connect issue (lt): " + attach_response.strip()
            )
        logger.info("OpenGOAL attached to the Jak 3 game target.")

    async def send_form(self, form: str, timeout: float = 10.0) -> str:
        if not self.connected or self.reader is None or self.writer is None:
            raise ConnectionError("OpenGOAL nREPL is not connected")
        encoded = form.encode("utf-8")
        eval_packet = struct.pack("<II", len(encoded), 10) + encoded
        ping_packet = struct.pack("<II", 0, 0)
        async with self.lock:
            # This OpenGOAL nREPL intentionally sends no evaluation result.
            # A following PING is processed only after EVAL returns because the
            # server handles both serially; its greeting is our completion barrier.
            self.writer.write(eval_packet + ping_packet)
            await self.writer.drain()
            try:
                response = await asyncio.wait_for(self.reader.read(4096), timeout=timeout)
            except asyncio.TimeoutError as exc:
                raise ConnectionError(
                    f"OpenGOAL did not acknowledge this command within {timeout:g} seconds: {form}"
                ) from exc
            decoded = response.decode(errors="replace")
            if "nREPL" not in decoded:
                raise ConnectionError(
                    f"Unexpected OpenGOAL completion-barrier response for {form}: {decoded!r}"
                )
            return decoded

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None


class Jak3CommandProcessor(ClientCommandProcessor):
    ctx: "Jak3Context"

    def _cmd_repl(self, action: str = "status") -> None:
        """Connect to OpenGOAL (`/repl connect`) or show bridge status."""
        if action == "connect":
            self.output("Connecting to the Jak 3 OpenGOAL compiler on 127.0.0.1:8181...")
            asyncio.create_task(self.ctx.connect_repl())
        else:
            server_status = "connected" if self.ctx.server else "disconnected"
            repl_status = "connected" if self.ctx.repl.connected else "disconnected"
            bridge_status = "ready" if self.ctx.bridge_ready else "not bound"
            self.output(f"Archipelago server: {server_status}")
            self.output(f"OpenGOAL nREPL: {repl_status}")
            self.output(f"Jak 3 bridge: {bridge_status}")
            self.output(f"Slot: {self.ctx.auth or 'not authenticated'}")
            self.output(f"State file: {self.ctx.state_path}")

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
            asyncio.create_task(self.ctx.start_game())
        elif action == "title":
            self.output("Opening the normal Jak 3 title screen...")
            asyncio.create_task(self.ctx.open_title())
        else:
            self.output("Reapplying this slot's received AP inventory...")
            asyncio.create_task(self.ctx.sync_items())

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
        asyncio.create_task(self.ctx.play_task(task_id))


class Jak3Context(CommonContext):
    game = GAME_NAME
    items_handling = 0b111
    command_processor = Jak3CommandProcessor

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.repl = OpenGoalRepl()
        configured_state = os.environ.get("JAK3_AP_STATE")
        if configured_state:
            self.state_path = Path(configured_state).expanduser().resolve()
        else:
            self.state_path = (
                Path(tempfile.gettempdir()) / f"jak3-ap-{os.getpid()}.tmp"
            ).resolve()
        self.slot_data: dict = {}
        self.room_seed = ""
        self.sent_item_index = 0
        self.completed_tasks: set[int] = set()
        self.bridge_ready = False
        self.bound_game: tuple[int, int] | None = None
        self.received_history_ready = False
        self.pending_notifications: deque[tuple[int, str]] = deque()

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "RoomInfo":
            self.room_seed = args.get("seed_name", "")
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            self.bridge_ready = False
            self.received_history_ready = False
            self.pending_notifications.clear()
            asyncio.create_task(self.setup_bridge())
        if cmd == "ReceivedItems":
            # CommonClient has already appended this packet before invoking
            # this hook. The first packet is connection history/replay; later
            # packets are genuinely new receipts and receive HUD notices.
            if self.received_history_ready:
                start_index = int(args.get("index", len(self.items_received)))
                for offset, item in enumerate(args.get("items", ())):
                    name = ITEM_ID_TO_NAME.get(int(item[0]), "Unknown Item")
                    self.pending_notifications.append(
                        (start_index + offset, f"Received: {name}"[:96])
                    )
            else:
                self.received_history_ready = True
        self.watcher_event.set()

    async def connect_repl(self) -> None:
        try:
            await self.repl.connect()
            await self.repl.send_form(
                '(ml "goal_src/jak3/pc/features/archipelago.gc")', timeout=60.0
            )
            await self.repl.send_form("(ap-init!)")
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
            self.watcher_event.set()
        except (ConnectionError, OSError) as exc:
            await self.repl.close()
            self.bridge_ready = False
            logger.error("Could not connect to OpenGOAL: %s", exc)

    async def setup_bridge(self) -> None:
        if not self.repl.connected or not self.auth or not self.room_seed:
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
            logger.info("Bound the Jak 3 bridge to the current Archipelago slot and seed.")
            self.watcher_event.set()
        except (ConnectionError, OSError) as exc:
            self.bridge_ready = False
            logger.warning("Could not bind OpenGOAL to this slot and seed: %s", exc)

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
            logger.warning("That mission is not unlocked.")
            return
        try:
            await self.repl.send_form(f"(ap-play-task! (the-as game-task {task_id}))")
            logger.info("OpenGOAL finished dispatching Jak 3 task %d.", task_id)
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


def parse_state(path: Path) -> tuple[int, set[int]]:
    """Return `(received_index, completed_tasks)` from a bridge snapshot."""
    received_index = 0
    completed: set[int] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        return received_index, completed
    for line in lines:
        key, _, values = line.partition(" ")
        if key == "received" and values.isdigit():
            received_index = int(values)
        elif key == "completed":
            completed.update(int(value) for value in values.split() if value.isdigit())
    return received_index, completed & set(CHECK_BY_TASK)


def parse_binding(path: Path) -> tuple[int, int] | None:
    """Return the slot/seed keys confirmed by a bridge snapshot."""
    values: dict[str, int] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        return None
    for line in lines:
        key, _, value = line.partition(" ")
        if key in {"slot", "seed"} and value.isdigit():
            values[key] = int(value)
    if "slot" in values and "seed" in values:
        return values["slot"], values["seed"]
    return None


def parse_notification_index(path: Path) -> int:
    """Return the latest HUD notification index acknowledged by the bridge."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        return -1
    for line in lines:
        key, _, value = line.partition(" ")
        if key == "notification" and value.lstrip("-").isdigit():
            return int(value)
    return -1


async def sync_items(ctx: Jak3Context, game_received_index: int) -> None:
    if not ctx.repl.connected or not ctx.bridge_ready:
        return
    ctx.sent_item_index = min(ctx.sent_item_index, game_received_index)
    while ctx.sent_item_index < len(ctx.items_received):
        index = ctx.sent_item_index
        item_id = ctx.items_received[index].item
        if item_id in ITEM_ID_TO_TASK:
            form = f"(ap-receive-mission! (the-as game-task {ITEM_ID_TO_TASK[item_id]}) {index})"
        elif item_id in EQUIPMENT_ID_TO_DATA:
            equipment = EQUIPMENT_ID_TO_DATA[item_id]
            level = sum(received.item == item_id for received in ctx.items_received[:index + 1])
            form = f"(ap-receive-upgrade! {equipment.kind} {level} {index})"
        elif item_id in TRAP_ID_TO_INDEX:
            duration = int(ctx.slot_data.get("trap_duration", 30))
            form = f"(ap-receive-trap! {TRAP_ID_TO_INDEX[item_id]} {duration} {index})"
        elif item_id in FILLER_ID_TO_KIND:
            form = f"(ap-receive-filler! {FILLER_ID_TO_KIND[item_id]} {index})"
        else:
            # Foreign filler has no safe Jak 3 effect, but still advances the
            # idempotent receive index.
            form = f"(ap-receive-filler! -1 {index})"
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
        await ctx.repl.send_form(f"(ap-try-notification! {message} {item_index})")
    except (ConnectionError, OSError) as exc:
        logger.warning("OpenGOAL notification sync paused: %s", exc)
        await ctx.repl.close()


async def game_watcher(ctx: Jak3Context) -> None:
    while not ctx.exit_event.is_set():
        game_received_index, completed = parse_state(ctx.state_path)
        if not ctx.bridge_ready:
            completed = set()
        ctx.completed_tasks |= completed
        new_locations = {
            LOCATION_NAME_TO_ID[CHECK_BY_TASK[task_id].location_name]
            for task_id in ctx.completed_tasks
            if task_id in CHECK_BY_TASK
        }
        if new_locations and ctx.server and ctx.bridge_ready:
            await ctx.check_locations(new_locations)

        if ctx.server and ctx.slot_data and ctx.bridge_ready and not ctx.finished_game:
            mode = int(ctx.slot_data.get("completion_condition", 1))
            specific = int(ctx.slot_data.get("specific_mission", 71))
            count = int(ctx.slot_data.get("mission_count", 66))
            completed_story = ctx.completed_tasks & set(MISSION_BY_ID)
            won = specific in completed_story if mode == 0 else len(completed_story) >= count
            if won:
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
    Utils.init_logging("Jak3Client", exception_logger="Client")
    ctx = Jak3Context(None, None)
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    watcher = asyncio.create_task(game_watcher(ctx), name="Jak3 game watcher")
    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()
    await ctx.exit_event.wait()
    watcher.cancel()
    try:
        await watcher
    except asyncio.CancelledError:
        pass
    await ctx.repl.close()
    await ctx.shutdown()


def launch() -> None:
    colorama.just_fix_windows_console()
    asyncio.run(main())
    colorama.deinit()
