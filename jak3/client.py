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


logger = logging.getLogger("Jak3Client")
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
        welcome = (await self.reader.read(1024)).decode(errors="replace")
        if "nREPL" not in welcome:
            await self.close()
            raise ConnectionError(f"Unexpected OpenGOAL nREPL greeting: {welcome!r}")
        await self.send_form("(lt)")
        logger.info("Connected to the Jak 3 OpenGOAL nREPL.")

    async def send_form(self, form: str) -> str:
        if not self.connected or self.reader is None or self.writer is None:
            raise ConnectionError("OpenGOAL nREPL is not connected")
        packet = struct.pack("<II", len(form.encode("utf-8")), 10) + form.encode("utf-8")
        async with self.lock:
            self.writer.write(packet)
            await self.writer.drain()
            return (await self.reader.read(4096)).decode(errors="replace")

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
            asyncio.create_task(self.ctx.connect_repl())
        else:
            logger.info("OpenGOAL nREPL: %s", "connected" if self.ctx.repl.connected else "disconnected")

    def _cmd_missions(self) -> None:
        """List mission and challenge task IDs currently unlocked for this slot."""
        unlocked = self.ctx.unlocked_tasks()
        for task_id in sorted(unlocked):
            logger.info("%3d  %s", task_id, CHECK_BY_TASK[task_id].name)

    def _cmd_play(self, *mission: str) -> None:
        """Start an unlocked mission by native task ID or a unique part of its name."""
        query = " ".join(mission).strip()
        task_id = self.ctx.resolve_task(query)
        if task_id is None:
            logger.warning("Mission must be an unlocked task ID or a unique name fragment.")
            return
        asyncio.create_task(self.ctx.play_task(task_id))


class Jak3Context(CommonContext):
    game = GAME_NAME
    items_handling = 0b111
    command_processor = Jak3CommandProcessor

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.repl = OpenGoalRepl()
        self.state_path = Path(os.environ.get("JAK3_AP_STATE", "jak3-ap-state.tmp"))
        self.slot_data: dict = {}
        self.room_seed = ""
        self.sent_item_index = 0
        self.completed_tasks: set[int] = set()
        self.bridge_ready = False
        self.bound_game: tuple[int, int] | None = None
        self.received_history_ready = False
        self.pending_notifications: deque[str] = deque()

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
                for item in args.get("items", ()):
                    name = ITEM_ID_TO_NAME.get(int(item[0]), "Unknown Item")
                    self.pending_notifications.append(f"Received: {name}"[:96])
            else:
                self.received_history_ready = True
        self.watcher_event.set()

    async def connect_repl(self) -> None:
        try:
            await self.repl.connect()
            await self.repl.send_form("(ap-init!)")
            self.sent_item_index = 0
            self.bridge_ready = False
            await self.setup_bridge()
            self.watcher_event.set()
        except (ConnectionError, OSError) as exc:
            logger.error("Could not connect to OpenGOAL: %s", exc)

    async def setup_bridge(self) -> None:
        if not self.repl.connected or not self.auth or not self.room_seed:
            return
        slot_key = zlib.crc32(self.auth.encode("utf-8")) & 0x7FFF_FFFF
        seed_key = zlib.crc32(self.room_seed.encode("utf-8")) & 0x7FFF_FFFF
        try:
            await self.repl.send_form(f"(ap-setup! {slot_key} {seed_key})")
            game_key = (slot_key, seed_key)
            if self.bound_game != game_key:
                self.completed_tasks.clear()
                self.sent_item_index = 0
                self.finished_game = False
            self.bound_game = game_key
            self.bridge_ready = True
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
            response = await self.repl.send_form(f"(ap-play-task! (the-as game-task {task_id}))")
            if "OK!" not in response:
                logger.warning("OpenGOAL did not acknowledge the mission command: %s", response.strip())
        except ConnectionError as exc:
            logger.error("%s; run /repl connect first.", exc)


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
            response = await ctx.repl.send_form(form)
        except (ConnectionError, OSError) as exc:
            logger.warning("OpenGOAL item sync paused: %s", exc)
            await ctx.repl.close()
            return
        if "OK!" not in response:
            logger.error("OpenGOAL rejected item index %d; sync paused: %s", index, response.strip())
            return
        ctx.sent_item_index += 1


def _goal_string_literal(value: str) -> str:
    """Encode controlled notification text as a bounded GOAL string literal."""
    safe = "".join(character if 32 <= ord(character) < 127 else "?" for character in value[:96])
    return '"' + safe.replace("\\", "\\\\").replace('"', '\\"') + '"'


async def sync_notification(ctx: Jak3Context) -> None:
    """Show the next new receipt only when the game HUD can own the alert."""
    if not ctx.pending_notifications or not ctx.repl.connected or not ctx.bridge_ready:
        return
    try:
        ready = await ctx.repl.send_form("(ap-notification-ready?)")
        if "AP-NOTIFY-READY" not in ready:
            return
        message = _goal_string_literal(ctx.pending_notifications[0])
        response = await ctx.repl.send_form(f"(ap-show-notification! {message})")
        if "AP-NOTIFY-QUEUED" in response and "OK!" in response:
            ctx.pending_notifications.popleft()
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
        await sync_notification(ctx)
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
