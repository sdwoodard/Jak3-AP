import asyncio
import shlex
import unittest
import uuid

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from worlds.jak3.agents.protocol import (
    BRIDGE_RUNTIME_VERSION,
    GAME_INTEGRATION_VERSION,
    PROTOCOL_VERSION,
    BridgeProtocol,
    BridgeSnapshot,
    ClientStatus,
    CommandReceipt,
    DataContractMismatch,
    GameIntegrationVersionMismatch,
    GameStatus,
    NativeSaveEligibility,
    ProtocolCommand,
    ProtocolError,
    ProtocolResult,
    ProtocolVersionMismatch,
    WIRE_INT32_MAX,
    WIRE_INT32_MIN,
    format_snapshot,
    parse_snapshot_text,
)
from worlds.jak3.agents.diagnostics import GoalDiagnosticRecord


class FakeGame:
    """Protocol fake with the same nonce/high-watermark/receipt semantics."""

    def __init__(
        self,
        state_path: Path,
        *,
        protocol: int = PROTOCOL_VERSION,
        integration: int = GAME_INTEGRATION_VERSION,
        running: bool = True,
    ) -> None:
        self.state_path = state_path
        self.protocol = protocol
        self.integration = integration
        self.running = running
        self.revision = 0
        self.nonce = str(uuid.uuid4())
        self.client: str | None = None
        self.connected = False
        self.client_heartbeat = -1
        self.game_heartbeat = 0
        self.client_status = ClientStatus.STARTING
        self.ap_loaded = False
        self.ap_bound = False
        self.proposed_save_identity: str | None = None
        self.consumed_save_identity: str | None = None
        self.save_loaded = False
        self.save_slot = -1
        self.save_identity: str | None = None
        self.title = True
        self.loading = False
        self.cutscene = False
        self.dead = False
        self.restarting = False
        self.transition = False
        self.vehicle = False
        self.ambiguous = False
        self.target_available = True
        self.level_available = True
        self.test_target = False
        self.permanent_item_target_mask = 0
        self.apply_count = 0
        self.permanent_item_apply_count = 0
        self.high_watermark = -1
        self.receipts: list[CommandReceipt] = []
        self.last_id = -1
        self.last_kind: ProtocolCommand | int = ProtocolCommand.NONE
        self.last_result = ProtocolResult.NONE
        self.last_error = ProtocolError.NONE

    @property
    def safe(self) -> bool:
        return (
            self.connected
            and self.save_loaded
            and self.ap_loaded
            and self.ap_bound
            and self.target_available
            and self.level_available
            and not any(
                (
                    self.title,
                    self.loading,
                    self.cutscene,
                    self.dead,
                    self.restarting,
                    self.transition,
                    self.vehicle,
                    self.ambiguous,
                )
            )
        )

    def snapshot(self) -> BridgeSnapshot:
        return BridgeSnapshot(
            snapshot_revision=self.revision,
            protocol_version=self.protocol,
            game_integration_version=self.integration,
            connection_ready=self.connected,
            client_session_id=self.client,
            session_nonce=self.nonce,
            client_heartbeat=self.client_heartbeat,
            client_status=self.client_status,
            game_heartbeat=self.game_heartbeat,
            game_status=GameStatus.READY
            if self.connected
            else GameStatus.SOURCE_LOADED,
            save_loaded=self.save_loaded,
            native_save_slot=self.save_slot,
            native_save_identity=self.save_identity,
            consumed_save_identity=self.consumed_save_identity,
            native_save_eligibility=(
                NativeSaveEligibility.FRESH_UNPROGRESSED
                if self.save_loaded
                else NativeSaveEligibility.UNKNOWN
            ),
            ap_state_loaded=self.ap_loaded,
            ap_state_bound=self.ap_bound,
            current_level=None if self.title or not self.level_available else "city",
            current_act=0 if self.ambiguous else 1,
            current_task=-1 if self.ambiguous else 6,
            current_task_node=-1 if self.ambiguous else 42,
            at_title_menu=self.title,
            loading=self.loading,
            in_cutscene=self.cutscene,
            dying_or_dead=self.dead,
            mission_restarting=self.restarting,
            level_transition=self.transition,
            in_vehicle=self.vehicle,
            safe_to_apply_permanent_item=self.safe,
            safe_to_apply_consumable=False,
            safe_to_mutate_mission_state=self.safe,
            test_target=self.test_target,
            last_command_id=self.last_id,
            last_command_kind=self.last_kind,
            last_command_result=self.last_result,
            last_error_code=self.last_error,
            last_error_message=(
                self.last_error.name.lower().replace("_", "-")
                if self.last_error
                else "none"
            ),
            recent_command_receipts=tuple(self.receipts),
        )

    def publish(self) -> None:
        self.revision += 1
        snapshot = replace(self.snapshot(), snapshot_revision=self.revision)
        self.state_path.write_text(format_snapshot(snapshot), encoding="utf-8")

    def restart(self) -> None:
        self.nonce = str(uuid.uuid4())
        self.client = None
        self.connected = False
        self.client_heartbeat = -1
        self.game_heartbeat = 0
        self.proposed_save_identity = None
        self.consumed_save_identity = None
        self.high_watermark = -1
        self.receipts.clear()
        self.last_id = -1
        self.last_kind = ProtocolCommand.NONE
        self.last_result = ProtocolResult.NONE
        self.last_error = ProtocolError.NONE
        self.publish()

    def handle(self, form: str) -> None:
        if not self.running:
            raise ConnectionError("game is not running")
        tokens = shlex.split(form[1:-1], posix=True)
        action = tokens[0]
        if action == "ap-set-state-path!":
            self.publish()
        elif action == "ap-client-hello!":
            self._hello(tokens)
            self.publish()
        elif action == "ap-ping!":
            self._ping(tokens)
            self.publish()
        elif action == "ap-query-state!":
            self._query(tokens)
            self.publish()
        elif action == "ap-command!":
            self._command(tokens)
            self.publish()
        elif action == "ap-client-disconnect!":
            self._disconnect(tokens)
            self.publish()
        else:
            raise AssertionError(form)

    def _hello(self, tokens: list[str]) -> None:
        self.client = tokens[11]
        self.client_status = ClientStatus(int(tokens[14]))
        self.proposed_save_identity = (
            tokens[13]
            if (
                self.client_status is ClientStatus.AP_CONNECTED
                and tokens[13] != "-"
                and tokens[13] != self.save_identity
                and tokens[13] != self.consumed_save_identity
            )
            else None
        )
        self._update_sidecar_state(tokens[15], tokens[16], tokens[17])
        self.connected = True
        self.last_id = -1
        self.last_kind = ProtocolCommand.HELLO
        self.last_result = ProtocolResult.OK
        self.last_error = ProtocolError.NONE
        contract_error = self._contract_error(tokens, 1)
        if contract_error is not None:
            self._incompatible(contract_error)

    def _contract_error(self, tokens: list[str], start: int) -> ProtocolError | None:
        snapshot = self.snapshot()
        if int(tokens[start]) != self.protocol:
            return ProtocolError.PROTOCOL_MISMATCH
        if int(tokens[start + 1]) != self.integration:
            return ProtocolError.GAME_INTEGRATION_MISMATCH
        if int(tokens[start + 2]) != snapshot.state_schema_version:
            return ProtocolError.STATE_SCHEMA_MISMATCH
        if int(tokens[start + 3]) != snapshot.slot_data_version:
            return ProtocolError.SLOT_DATA_MISMATCH
        if (
            int(tokens[start + 4]) != snapshot.item_table_version
            or tokens[start + 7] != snapshot.item_table_hash
        ):
            return ProtocolError.ITEM_TABLE_MISMATCH
        if (
            int(tokens[start + 5]) != snapshot.location_table_version
            or tokens[start + 8] != snapshot.location_table_hash
        ):
            return ProtocolError.LOCATION_TABLE_MISMATCH
        if (
            int(tokens[start + 6]) != snapshot.mission_table_version
            or tokens[start + 9] != snapshot.mission_table_hash
        ):
            return ProtocolError.MISSION_TABLE_MISMATCH
        return None

    def _incompatible(self, error: ProtocolError) -> None:
        self.connected = False
        self.last_result = ProtocolResult.INCOMPATIBLE
        self.last_error = error

    def _ping(self, tokens: list[str]) -> None:
        self.last_id = -1
        self.last_kind = ProtocolCommand.PING
        if tokens[1] != self.client:
            self.last_result = ProtocolResult.FAILED
            self.last_error = ProtocolError.INVALID_CLIENT_SESSION
        elif tokens[2] != self.nonce:
            self.last_result = ProtocolResult.FAILED
            self.last_error = ProtocolError.INVALID_GAME_SESSION
        else:
            self.client_heartbeat = max(self.client_heartbeat, int(tokens[3]))
            self.game_heartbeat = self.client_heartbeat + 1
            self.client_status = ClientStatus(int(tokens[4]))
            self._update_sidecar_state(tokens[5], tokens[6], tokens[7])
            self.proposed_save_identity = (
                tokens[8]
                if (
                    self.client_status is ClientStatus.AP_CONNECTED
                    and tokens[8] != "-"
                    and tokens[8] != self.save_identity
                    and tokens[8] != self.consumed_save_identity
                )
                else None
            )
            self.last_result = ProtocolResult.PONG
            self.last_error = ProtocolError.NONE

    def _update_sidecar_state(
        self, state_flags: str, save_slot: str, save_identity: str
    ) -> None:
        flags = int(state_flags)
        descriptor_matches = (
            self.save_loaded
            and int(save_slot) == self.save_slot
            and save_identity == self.save_identity
            and flags & ~0b11 == 0
        )
        self.ap_loaded = bool(flags & 0b01) and descriptor_matches
        self.ap_bound = bool(flags & 0b10) and self.ap_loaded

    def _query(self, tokens: list[str]) -> None:
        self.last_id = -1
        self.last_kind = ProtocolCommand.QUERY_STATE
        if tokens[1] != self.client:
            self.last_result = ProtocolResult.FAILED
            self.last_error = ProtocolError.INVALID_CLIENT_SESSION
        elif tokens[2] != self.nonce:
            self.last_result = ProtocolResult.FAILED
            self.last_error = ProtocolError.INVALID_GAME_SESSION
        else:
            try:
                client_status = ClientStatus(int(tokens[3]))
            except ValueError:
                self.last_result = ProtocolResult.INVALID_PAYLOAD
                self.last_error = ProtocolError.INVALID_PAYLOAD
            else:
                self.client_status = client_status
                self._update_sidecar_state(tokens[4], tokens[5], tokens[6])
                self.last_result = ProtocolResult.OK
                self.last_error = ProtocolError.NONE

    def _disconnect(self, tokens: list[str]) -> None:
        self.last_id = -1
        self.last_kind = ProtocolCommand.DISCONNECT
        if not self.connected or tokens[1] != self.client:
            self.last_result = ProtocolResult.FAILED
            self.last_error = ProtocolError.INVALID_CLIENT_SESSION
        elif tokens[2] != self.nonce:
            self.last_result = ProtocolResult.FAILED
            self.last_error = ProtocolError.INVALID_GAME_SESSION
        else:
            try:
                client_status = ClientStatus(int(tokens[4]))
            except ValueError:
                self.last_result = ProtocolResult.INVALID_PAYLOAD
                self.last_error = ProtocolError.INVALID_PAYLOAD
            else:
                self.connected = False
                self.client_status = client_status
                self.proposed_save_identity = None
                self.last_result = ProtocolResult.OK
                self.last_error = ProtocolError.NONE

    def _record(
        self,
        command_id: int,
        kind: ProtocolCommand | int,
        payload: int,
        result: ProtocolResult,
        error: ProtocolError,
    ) -> None:
        self.receipts.append(CommandReceipt(command_id, kind, payload, result, error))
        self.receipts = self.receipts[-8:]
        self.high_watermark = command_id

    def _command(self, tokens: list[str]) -> None:
        command_id = int(tokens[3])
        raw_kind = int(tokens[4])
        try:
            kind: ProtocolCommand | int = ProtocolCommand(raw_kind)
        except ValueError:
            kind = raw_kind
        payload = int(tokens[5])
        wire_command_id = 0 <= command_id <= WIRE_INT32_MAX
        wire_kind = WIRE_INT32_MIN <= raw_kind <= WIRE_INT32_MAX
        wire_payload = WIRE_INT32_MIN <= payload <= WIRE_INT32_MAX
        self.last_id = command_id if wire_command_id else -1
        self.last_kind = kind if wire_kind else ProtocolCommand.NONE
        old = (
            next((r for r in self.receipts if r.command_id == command_id), None)
            if wire_command_id
            else None
        )
        record = False
        contract_error = self._contract_error(tokens, 9)
        if contract_error is not None:
            result, error = ProtocolResult.INCOMPATIBLE, contract_error
        elif tokens[1] != self.client:
            result, error = ProtocolResult.FAILED, ProtocolError.INVALID_CLIENT_SESSION
        elif tokens[2] != self.nonce:
            result, error = ProtocolResult.FAILED, ProtocolError.INVALID_GAME_SESSION
        elif not (wire_command_id and wire_kind and wire_payload):
            result, error = (
                ProtocolResult.INVALID_PAYLOAD,
                ProtocolError.INVALID_PAYLOAD,
            )
        else:
            self._update_sidecar_state(tokens[6], tokens[7], tokens[8])
            if old and (old.command_kind != kind or old.payload != payload):
                result, error = (
                    ProtocolResult.FAILED,
                    ProtocolError.DUPLICATE_COMMAND_CONFLICT,
                )
            elif old:
                result, error = old.result, old.error_code
            elif command_id <= self.high_watermark:
                result, error = (
                    ProtocolResult.FAILED,
                    ProtocolError.OUT_OF_ORDER_COMMAND_ID,
                )
            elif kind is ProtocolCommand.TEST_ADDITIVE_EFFECT:
                result, error, record = (
                    ProtocolResult.FAILED,
                    ProtocolError.ADDITIVE_EFFECT_FORBIDDEN,
                    True,
                )
            elif kind not in (
                ProtocolCommand.SET_TEST_TARGET,
                ProtocolCommand.RECONCILE_PERMANENT_ITEMS,
            ):
                result, error, record = (
                    ProtocolResult.FAILED,
                    ProtocolError.UNKNOWN_COMMAND,
                    True,
                )
            elif (
                kind is ProtocolCommand.SET_TEST_TARGET and payload not in (0, 1)
            ) or (
                kind is ProtocolCommand.RECONCILE_PERMANENT_ITEMS
                and payload not in range(8)
            ):
                result, error, record = (
                    ProtocolResult.INVALID_PAYLOAD,
                    ProtocolError.INVALID_PAYLOAD,
                    True,
                )
            elif not self.save_loaded:
                result, error, record = (
                    ProtocolResult.UNSAFE_NOW,
                    ProtocolError.SAVE_NOT_LOADED,
                    True,
                )
            elif not self.ap_loaded:
                result, error, record = (
                    ProtocolResult.UNSAFE_NOW,
                    ProtocolError.AP_STATE_NOT_LOADED,
                    True,
                )
            elif not self.ap_bound:
                result, error, record = (
                    ProtocolResult.UNSAFE_NOW,
                    ProtocolError.AP_STATE_NOT_BOUND,
                    True,
                )
            elif not self.safe:
                result, error, record = (
                    ProtocolResult.UNSAFE_NOW,
                    ProtocolError.UNSAFE_GAME_STATE,
                    True,
                )
            elif (
                kind is ProtocolCommand.RECONCILE_PERMANENT_ITEMS
                and self.permanent_item_target_mask == payload
            ):
                result, error, record = (
                    ProtocolResult.ALREADY_APPLIED,
                    ProtocolError.NONE,
                    True,
                )
            elif kind is ProtocolCommand.RECONCILE_PERMANENT_ITEMS:
                self.permanent_item_target_mask = payload
                self.permanent_item_apply_count += 1
                result, error, record = ProtocolResult.APPLIED, ProtocolError.NONE, True
            elif self.test_target == bool(payload):
                result, error, record = (
                    ProtocolResult.ALREADY_APPLIED,
                    ProtocolError.NONE,
                    True,
                )
            else:
                self.test_target = bool(payload)
                self.apply_count += 1
                result, error, record = ProtocolResult.APPLIED, ProtocolError.NONE, True
        if record:
            self._record(command_id, kind, payload, result, error)
        self.last_result, self.last_error = result, error


class FakeRepl:
    def __init__(self, game: FakeGame) -> None:
        self.game = game

    async def send_form(self, form: str, timeout: float = 10.0) -> str:
        self.game.handle(form)
        return "nREPL"


class YieldingCommandRepl(FakeRepl):
    async def send_form(self, form: str, timeout: float = 10.0) -> str:
        if form.startswith("(ap-command!"):
            await asyncio.sleep(0)
        return await super().send_form(form, timeout)


class CommandReceiptBarrierRepl(FakeRepl):
    """Expose whether a heartbeat can overtake a published command receipt."""

    def __init__(self, game: FakeGame) -> None:
        super().__init__(game)
        self.command_published = asyncio.Event()
        self.release_command = asyncio.Event()
        self.ping_started = asyncio.Event()

    async def send_form(self, form: str, timeout: float = 10.0) -> str:
        if form.startswith("(ap-command!"):
            response = await super().send_form(form, timeout)
            self.command_published.set()
            await self.release_command.wait()
            return response
        if form.startswith("(ap-ping!"):
            self.ping_started.set()
        return await super().send_form(form, timeout)


class ApplyThenFailCommandRepl(FakeRepl):
    async def send_form(self, form: str, timeout: float = 10.0) -> str:
        response = await super().send_form(form, timeout)
        if form.startswith("(ap-command!"):
            raise ConnectionError("command response was lost")
        return response


class ProtocolLifecycleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "bridge.tmp"

    def bridge(self, game: FakeGame, session: str) -> BridgeProtocol:
        return BridgeProtocol(
            FakeRepl(game),
            self.path,
            session,
            command_timeout=0.03,
            poll_interval=0.001,
        )

    async def ready(self, game: FakeGame, session: str = "client") -> BridgeProtocol:
        game.save_loaded = True
        game.save_slot = 0
        game.save_identity = str(uuid.uuid4())
        game.title = False
        bridge = self.bridge(game, session)
        bridge.set_ap_state_status(
            loaded=True,
            bound=True,
            native_save_slot=game.save_slot,
            native_save_identity=game.save_identity,
        )
        bridge.set_save_identity_authorized(True)
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        return bridge

    async def test_either_side_can_start_first(self) -> None:
        game = FakeGame(self.path, running=False)
        with self.assertRaisesRegex(ConnectionError, "game is not running"):
            await self.bridge(game, "early").initialize(ClientStatus.AP_DISCONNECTED)
        game.running = True
        snapshot = await self.bridge(game, "late").initialize(
            ClientStatus.AP_DISCONNECTED
        )
        self.assertTrue(snapshot.connection_ready)

    async def test_diagnostic_sink_failure_cannot_change_command_result(self) -> None:
        game = FakeGame(self.path)
        game.save_loaded = True
        game.save_slot = 0
        game.save_identity = str(uuid.uuid4())
        game.title = False

        class SyntheticDiagnosticFailure(BaseException):
            pass

        def failing_sink(event_name: str, **fields: object) -> None:
            raise SyntheticDiagnosticFailure("synthetic diagnostics failure")

        bridge = BridgeProtocol(
            FakeRepl(game),
            self.path,
            "diagnostic-failure",
            command_timeout=0.03,
            poll_interval=0.001,
            event_sink=failing_sink,
        )
        bridge.set_ap_state_status(
            loaded=True,
            bound=True,
            native_save_slot=0,
            native_save_identity=game.save_identity,
        )
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        result = await bridge.set_test_target(True)
        self.assertEqual(result.last_command_result, ProtocolResult.APPLIED)
        self.assertTrue(game.test_target)

    async def test_timed_out_command_is_recovered_once_from_later_receipt(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        timed_out: dict[tuple[str, int], ProtocolCommand] = {}

        class NoSnapshotRepl:
            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                return "nREPL"

        first = BridgeProtocol(
            NoSnapshotRepl(),
            self.path,
            "timeout-client",
            command_timeout=0.002,
            poll_interval=0.0001,
            timed_out_commands=timed_out,
        )
        first.session_nonce = "retained-game-session"
        with self.assertRaises(ConnectionError):
            await first.send_command(ProtocolCommand.SET_TEST_TARGET, 1, command_id=19)
        self.assertEqual(
            timed_out,
            {("retained-game-session", 19): ProtocolCommand.SET_TEST_TARGET},
        )

        reconnected = BridgeProtocol(
            NoSnapshotRepl(),
            self.path,
            "reconnected-client",
            timed_out_commands=timed_out,
            event_sink=lambda event_name, **fields: events.append((event_name, fields)),
        )
        receipt = CommandReceipt(
            19,
            ProtocolCommand.SET_TEST_TARGET,
            1,
            ProtocolResult.APPLIED,
            ProtocolError.NONE,
        )
        snapshot = BridgeSnapshot(
            snapshot_revision=22,
            session_nonce="retained-game-session",
            recent_command_receipts=(receipt,),
        )

        reconnected._observe_snapshot(snapshot)
        reconnected._observe_snapshot(snapshot)

        recovered = [
            event for event in events if event[0] == "protocol.command.recovered"
        ]
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0][1]["correlation_id"], "command:19")
        self.assertEqual(timed_out, {})

    async def test_nrepl_acknowledgement_timeout_is_a_command_timeout(self) -> None:
        events: list[str] = []

        class AckTimeoutRepl:
            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                raise ConnectionError(
                    "OpenGOAL did not acknowledge this command within 10 seconds"
                )

        def collect(event_name: str, **fields: object) -> None:
            events.append(event_name)

        bridge = BridgeProtocol(
            AckTimeoutRepl(),
            self.path,
            "command-ack-timeout",
            event_sink=collect,
        )
        bridge.session_nonce = "game-session"

        with self.assertRaises(ConnectionError):
            await bridge.send_command(ProtocolCommand.SET_TEST_TARGET, 1)

        self.assertIn("protocol.command.timed_out", events)
        self.assertNotIn("protocol.command.failed", events)

    async def test_failed_goal_acknowledgement_does_not_fail_protocol(self) -> None:
        game = FakeGame(self.path)
        original_snapshot = game.snapshot

        def diagnostic_snapshot() -> BridgeSnapshot:
            return replace(
                original_snapshot(),
                diagnostic_next_sequence=1,
                diagnostic_events=(
                    GoalDiagnosticRecord(0, 1, 1, 100, 0, 0, 1, 0, 0, 0, 0),
                ),
            )

        game.snapshot = diagnostic_snapshot  # type: ignore[method-assign]

        class SyntheticAckFailure(BaseException):
            pass

        class AckFailRepl(FakeRepl):
            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                if form.startswith("(ap-diagnostic-ack!"):
                    raise SyntheticAckFailure("synthetic ack failure")
                return await super().send_form(form, timeout)

        drained: list[int] = []
        events: list[tuple[str, dict[str, object]]] = []

        def drain(records: tuple[GoalDiagnosticRecord, ...], dropped: int) -> int:
            drained.extend(record.source_sequence for record in records)
            return max(record.source_sequence for record in records)

        bridge = BridgeProtocol(
            AckFailRepl(game),
            self.path,
            "ack-failure",
            command_timeout=0.03,
            poll_interval=0.001,
            goal_event_sink=drain,
            event_sink=lambda event_name, **fields: events.append((event_name, fields)),
        )
        snapshot = await bridge.initialize(ClientStatus.AP_DISCONNECTED)
        self.assertTrue(snapshot.connection_ready)
        self.assertIn(0, drained)
        await bridge.ping(ClientStatus.AP_DISCONNECTED)
        await asyncio.sleep(0)
        acknowledgement_gaps = [
            event
            for event in events
            if event[0] == "diagnostics.capture_gap"
            and event[1].get("context", {}).get("reason") == "goal_ack_failure"
        ]
        self.assertEqual(len(acknowledgement_gaps), 1)

    async def test_goal_generation_change_resets_python_drain_high_watermark(
        self,
    ) -> None:
        drained: list[int] = []
        resets: list[str] = []
        source_state: dict[str, int] = {}

        def drain(records: tuple[GoalDiagnosticRecord, ...], dropped: int) -> int:
            drained.extend(record.source_sequence for record in records)
            return max(record.source_sequence for record in records)

        bridge = BridgeProtocol(
            FakeRepl(FakeGame(self.path)),
            self.path,
            "goal-generations",
            goal_event_sink=drain,
            goal_event_reset=lambda: resets.append("reset") is None,
            goal_source_state=source_state,
        )
        bridge._observe_snapshot(
            BridgeSnapshot(
                diagnostic_activation_generation=7,
                diagnostic_next_sequence=12,
                diagnostic_events=(
                    GoalDiagnosticRecord(11, 20, 1, 100, 0, 0, 1, 0, 0, 0, 0),
                ),
            )
        )
        bridge._observe_snapshot(
            BridgeSnapshot(
                diagnostic_activation_generation=8,
                diagnostic_next_sequence=1,
                diagnostic_events=(
                    GoalDiagnosticRecord(0, 1, 1, 100, 0, 0, 1, 0, 0, 0, 0),
                ),
            )
        )

        self.assertEqual(drained, [11, 0])
        self.assertEqual(resets, ["reset"])
        self.assertEqual(source_state["activation_generation"], 8)

    async def test_delayed_goal_acknowledgement_cannot_drain_a_new_generation(
        self,
    ) -> None:
        forms: list[str] = []
        first_started = asyncio.Event()
        release_first = asyncio.Event()

        class DelayedAckRepl:
            async def send_form_unacknowledged(
                self, form: str, timeout: float = 0.25
            ) -> None:
                forms.append(form)
                if len(forms) == 1:
                    first_started.set()
                    await release_first.wait()

        bridge = BridgeProtocol(
            DelayedAckRepl(),
            self.path,
            "generation-qualified-ack",
        )
        bridge._schedule_goal_acknowledgement(7, 11)
        await asyncio.wait_for(first_started.wait(), timeout=0.1)
        bridge._schedule_goal_acknowledgement(8, 0)
        release_first.set()
        for _ in range(20):
            if bridge._goal_ack_task is None and bridge._goal_ack_pending is None:
                break
            await asyncio.sleep(0)

        self.assertEqual(
            forms,
            ["(ap-diagnostic-ack! 7 11)", "(ap-diagnostic-ack! 8 0)"],
        )

    async def test_persistent_goal_capture_failures_are_transition_latched(
        self,
    ) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        source_state: dict[str, int] = {}
        bridge = BridgeProtocol(
            FakeRepl(FakeGame(self.path)),
            self.path,
            "goal-gap-latches",
            event_sink=lambda event_name, **fields: events.append((event_name, fields)),
            goal_event_sink=lambda records, dropped: (_ for _ in ()).throw(
                RuntimeError("synthetic drain failure")
            ),
            goal_source_state=source_state,
        )
        malformed = BridgeSnapshot(
            diagnostic_schema_version=None,
            diagnostic_manifest_version=None,
            diagnostic_activation_generation=None,
            diagnostic_malformed=True,
        )
        for _ in range(10_000):
            bridge._observe_snapshot(malformed)
        valid = BridgeSnapshot(
            diagnostic_next_sequence=1,
            diagnostic_events=(
                GoalDiagnosticRecord(0, 1, 1, 100, 0, 0, 1, 0, 0, 0, 0),
            ),
        )
        for _ in range(10_000):
            bridge._observe_snapshot(valid)

        reasons = [
            event[1].get("context", {}).get("reason")
            for event in events
            if event[0] == "diagnostics.capture_gap"
        ]
        self.assertEqual(reasons.count("malformed_goal_snapshot"), 1)
        self.assertEqual(reasons.count("goal_drain_failure"), 1)

    async def test_goal_acknowledgement_cancellation_is_isolated_from_protocol(
        self,
    ) -> None:
        game = FakeGame(self.path)
        original_snapshot = game.snapshot

        def diagnostic_snapshot() -> BridgeSnapshot:
            return replace(
                original_snapshot(),
                diagnostic_next_sequence=1,
                diagnostic_events=(
                    GoalDiagnosticRecord(0, 1, 1, 100, 0, 0, 1, 0, 0, 0, 0),
                ),
            )

        game.snapshot = diagnostic_snapshot  # type: ignore[method-assign]

        class CancellingAckRepl(FakeRepl):
            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                if form.startswith("(ap-diagnostic-ack!"):
                    raise asyncio.CancelledError
                return await super().send_form(form, timeout)

        bridge = BridgeProtocol(
            CancellingAckRepl(game),
            self.path,
            "ack-cancellation",
            command_timeout=0.03,
            poll_interval=0.001,
            goal_event_sink=lambda records, dropped: max(
                record.source_sequence for record in records
            ),
        )

        snapshot = await bridge.initialize(ClientStatus.AP_DISCONNECTED)
        await asyncio.sleep(0)

        self.assertTrue(snapshot.connection_ready)

    async def test_slow_goal_acknowledgement_does_not_delay_protocol_result(
        self,
    ) -> None:
        game = FakeGame(self.path)
        original_snapshot = game.snapshot

        def diagnostic_snapshot() -> BridgeSnapshot:
            return replace(
                original_snapshot(),
                diagnostic_next_sequence=1,
                diagnostic_events=(
                    GoalDiagnosticRecord(0, 1, 1, 100, 0, 0, 1, 0, 0, 0, 0),
                ),
            )

        game.snapshot = diagnostic_snapshot  # type: ignore[method-assign]
        acknowledgement_started = asyncio.Event()
        acknowledgement_release = asyncio.Event()

        class SlowAckRepl(FakeRepl):
            async def send_form_unacknowledged(
                self, form: str, timeout: float = 0.25
            ) -> None:
                self.assert_diagnostic_form(form)
                acknowledgement_started.set()
                await acknowledgement_release.wait()

            @staticmethod
            def assert_diagnostic_form(form: str) -> None:
                if not form.startswith("(ap-diagnostic-ack!"):
                    raise AssertionError(form)

        bridge = BridgeProtocol(
            SlowAckRepl(game),
            self.path,
            "slow-ack",
            command_timeout=0.03,
            poll_interval=0.001,
            goal_event_sink=lambda records, dropped: max(
                record.source_sequence for record in records
            ),
        )
        started = asyncio.get_running_loop().time()

        snapshot = await bridge.initialize(ClientStatus.AP_DISCONNECTED)
        elapsed = asyncio.get_running_loop().time() - started

        self.assertTrue(snapshot.connection_ready)
        self.assertLess(elapsed, 0.1)
        await asyncio.wait_for(acknowledgement_started.wait(), timeout=0.1)
        acknowledgement_release.set()
        await asyncio.sleep(0)

    async def test_goal_ack_waiting_behind_heartbeat_is_not_a_capture_gap(
        self,
    ) -> None:
        acknowledgement_started = asyncio.Event()
        acknowledgement_release = asyncio.Event()
        events: list[tuple[str, dict[str, object]]] = []

        class ContendedAckRepl:
            async def send_form_unacknowledged(
                self, form: str, timeout: float = 0.25
            ) -> None:
                if not form.startswith("(ap-diagnostic-ack!"):
                    raise AssertionError(form)
                acknowledgement_started.set()
                await acknowledgement_release.wait()

        bridge = BridgeProtocol(
            ContendedAckRepl(),
            self.path,
            "contended-ack",
            command_timeout=1.0,
            event_sink=lambda event_name, **fields: events.append((event_name, fields)),
        )
        bridge._schedule_goal_acknowledgement(1, 5)
        await asyncio.wait_for(acknowledgement_started.wait(), timeout=0.1)
        await asyncio.sleep(0.3)
        acknowledgement_release.set()
        if bridge._goal_ack_task is not None:
            await bridge._goal_ack_task

        acknowledgement_gaps = [
            event
            for event in events
            if event[0] == "diagnostics.capture_gap"
            and event[1].get("context", {}).get("reason") == "goal_ack_failure"
        ]
        self.assertEqual(acknowledgement_gaps, [])

    async def test_save_identity_entropy_requires_authenticated_slot(self) -> None:
        game = FakeGame(self.path)
        bridge = self.bridge(game, "authorization")
        self.assertIsNone(bridge.proposed_save_identity)

        await bridge.initialize(ClientStatus.AP_DISCONNECTED)
        self.assertIsNone(game.proposed_save_identity)

        bridge.set_save_identity_authorized(True)
        await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(game.proposed_save_identity, bridge.proposed_save_identity)
        self.assertIsNotNone(game.proposed_save_identity)

        bridge.set_save_identity_authorized(False)
        await bridge.ping(ClientStatus.AP_DISCONNECTED)
        self.assertIsNone(game.proposed_save_identity)

        bridge.set_save_identity_authorized(True)
        await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertIsNotNone(game.proposed_save_identity)
        await bridge.disconnect()
        self.assertIsNone(game.proposed_save_identity)

    async def test_save_identity_factory_runs_before_proposal_is_exposed(self) -> None:
        game = FakeGame(self.path)
        proposed = "00000000-0000-4000-8000-000000000073"
        factory_calls: list[str] = []

        def durable_factory() -> str:
            factory_calls.append("persisted")
            return proposed

        bridge = BridgeProtocol(
            FakeRepl(game),
            self.path,
            "durable-proposal",
            durable_factory,
            command_timeout=0.03,
            poll_interval=0.001,
        )
        bridge.set_save_identity_authorized(True)
        self.assertEqual(["persisted"], factory_calls)
        self.assertEqual(proposed, bridge.proposed_save_identity)
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        self.assertEqual(proposed, game.proposed_save_identity)

    async def test_failed_save_identity_authorization_stays_unpublished(self) -> None:
        game = FakeGame(self.path)

        def failed_factory() -> str:
            raise OSError("disk unavailable")

        bridge = BridgeProtocol(
            FakeRepl(game),
            self.path,
            "failed-proposal",
            failed_factory,
            command_timeout=0.03,
            poll_interval=0.001,
        )
        with self.assertRaisesRegex(ValueError, "durably authorize"):
            bridge.set_save_identity_authorized(True)
        self.assertFalse(bridge.save_identity_authorized)
        self.assertIsNone(bridge.proposed_save_identity)
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        self.assertIsNone(game.proposed_save_identity)

    async def test_published_save_identity_consumes_and_rotates_proposal(self) -> None:
        game = FakeGame(self.path)
        bridge = self.bridge(game, "proposal-rotation")
        bridge.set_save_identity_authorized(True)
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        first_proposal = bridge.proposed_save_identity
        self.assertIsNotNone(first_proposal)
        self.assertEqual(game.proposed_save_identity, first_proposal)

        # Native publication consumes the game-side proposal but does not
        # export a snapshot. The first observing ping therefore still carries
        # Python's stale proposal and must not re-arm it.
        game.save_loaded = True
        game.save_slot = 0
        game.save_identity = first_proposal
        game.consumed_save_identity = first_proposal
        game.proposed_save_identity = None
        published = await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(published.native_save_identity, first_proposal)
        self.assertIsNone(game.proposed_save_identity)

        second_proposal = bridge.proposed_save_identity
        self.assertIsNotNone(second_proposal)
        self.assertNotEqual(second_proposal, first_proposal)
        await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(game.proposed_save_identity, second_proposal)

    async def test_consumed_identity_rotates_after_descriptor_is_cleared(self) -> None:
        game = FakeGame(self.path)
        bridge = self.bridge(game, "proposal-ack-after-invalidation")
        bridge.set_save_identity_authorized(True)
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        first_proposal = bridge.proposed_save_identity
        self.assertIsNotNone(first_proposal)

        # Publication consumes the proposal, but no-save initialization clears
        # the live descriptor before Python observes another snapshot.
        game.consumed_save_identity = first_proposal
        game.proposed_save_identity = None
        game.save_loaded = False
        game.save_slot = -1
        game.save_identity = None

        invalidated = await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(invalidated.consumed_save_identity, first_proposal)
        self.assertIsNone(game.proposed_save_identity)

        second_proposal = bridge.proposed_save_identity
        self.assertIsNotNone(second_proposal)
        self.assertNotEqual(second_proposal, first_proposal)
        await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(game.proposed_save_identity, second_proposal)

    async def test_client_restart_discovers_receipt_and_retains_game_nonce(
        self,
    ) -> None:
        game = FakeGame(self.path)
        first = await self.ready(game, "first")
        applied = await first.set_test_target(True)
        second = self.bridge(game, "second")
        second.set_ap_state_status(
            loaded=True,
            bound=True,
            native_save_slot=game.save_slot,
            native_save_identity=game.save_identity,
        )
        second.set_save_identity_authorized(True)
        discovered = await second.initialize(ClientStatus.AP_CONNECTED)
        self.assertEqual(discovered.session_nonce, applied.session_nonce)
        self.assertEqual(second.next_command_id, 1)

    async def test_game_restart_changes_nonce_and_rejects_old_nonce(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        old_nonce = bridge.session_nonce
        game.restart()
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        new_nonce = bridge.session_nonce
        bridge.session_nonce = old_nonce
        stale = await bridge.set_test_target(True)
        self.assertEqual(stale.last_error_code, ProtocolError.INVALID_GAME_SESSION)
        self.assertNotEqual(old_nonce, new_nonce)

    async def test_duplicate_conflict_and_out_of_order_ids(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        applied = await bridge.set_test_target(True, command_id=7)
        duplicate = await bridge.set_test_target(True, command_id=7)
        conflict = await bridge.set_test_target(False, command_id=7)
        old = await bridge.set_test_target(False, command_id=6)
        self.assertEqual(applied.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(duplicate.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(game.apply_count, 1)
        self.assertEqual(
            conflict.last_error_code, ProtocolError.DUPLICATE_COMMAND_CONFLICT
        )
        self.assertEqual(old.last_error_code, ProtocolError.OUT_OF_ORDER_COMMAND_ID)
        automatic = await bridge.set_test_target(False)
        self.assertEqual(automatic.last_command_id, 8)
        self.assertEqual(automatic.last_command_result, ProtocolResult.APPLIED)

    async def test_command_values_must_fit_game_receipt_fields(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)

        for invalid_id in (True, 1.5, WIRE_INT32_MAX + 1):
            with self.assertRaisesRegex(ValueError, "Command IDs"):
                await bridge.send_command(
                    ProtocolCommand.SET_TEST_TARGET,
                    1,
                    command_id=invalid_id,  # type: ignore[arg-type]
                )
        for invalid_payload in (True, WIRE_INT32_MIN - 1, WIRE_INT32_MAX + 1):
            with self.assertRaisesRegex(ValueError, "signed 32-bit"):
                await bridge.send_command(
                    ProtocolCommand.SET_TEST_TARGET,
                    invalid_payload,
                )

        self.assertEqual(bridge.next_command_id, 0)
        self.assertEqual(game.high_watermark, -1)
        self.assertEqual(game.apply_count, 0)
        self.assertEqual(game.receipts, [])

        applied = await bridge.set_test_target(True, command_id=WIRE_INT32_MAX)
        duplicate = await bridge.set_test_target(True, command_id=WIRE_INT32_MAX)
        self.assertEqual(applied.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(duplicate.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(game.apply_count, 1)

    async def test_concurrent_automatic_commands_reserve_distinct_ids(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        bridge.repl = YieldingCommandRepl(game)

        enabled, disabled = await asyncio.gather(
            bridge.set_test_target(True),
            bridge.set_test_target(False),
        )

        self.assertEqual((enabled.last_command_id, disabled.last_command_id), (0, 1))
        self.assertEqual(enabled.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(disabled.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(game.apply_count, 2)
        self.assertFalse(game.test_target)
        self.assertEqual(bridge.next_command_id, 2)

    async def test_heartbeat_waits_until_command_receipt_is_observed(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        repl = CommandReceiptBarrierRepl(game)
        bridge.repl = repl

        command_task = asyncio.create_task(bridge.set_test_target(True))
        await repl.command_published.wait()
        heartbeat_task = asyncio.create_task(bridge.ping(ClientStatus.AP_CONNECTED))
        await asyncio.sleep(0)
        heartbeat_overtook_receipt = repl.ping_started.is_set()
        repl.release_command.set()
        applied, heartbeat = await asyncio.gather(command_task, heartbeat_task)

        self.assertFalse(heartbeat_overtook_receipt)
        self.assertEqual(applied.last_command_id, 0)
        self.assertEqual(applied.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(heartbeat.last_command_kind, ProtocolCommand.PING)
        self.assertEqual(heartbeat.last_command_result, ProtocolResult.PONG)
        self.assertTrue(game.test_target)
        self.assertEqual(game.apply_count, 1)

    async def test_uncertain_send_does_not_reuse_automatic_command_id(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        bridge.repl = ApplyThenFailCommandRepl(game)

        with self.assertRaisesRegex(ConnectionError, "response was lost"):
            await bridge.set_test_target(True)

        self.assertTrue(game.test_target)
        self.assertEqual(bridge.next_command_id, 1)
        bridge.repl = FakeRepl(game)
        recovered = await bridge.set_test_target(False)
        self.assertEqual(recovered.last_command_id, 1)
        self.assertEqual(recovered.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(game.apply_count, 2)

    async def test_target_state_invalid_payload_and_additive_are_explicit(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        already = await bridge.set_test_target(False)
        invalid = await bridge.send_command(ProtocolCommand.SET_TEST_TARGET, 2)
        additive = await bridge.send_command(ProtocolCommand.TEST_ADDITIVE_EFFECT, 1)
        self.assertEqual(already.last_command_result, ProtocolResult.ALREADY_APPLIED)
        self.assertEqual(invalid.last_command_result, ProtocolResult.INVALID_PAYLOAD)
        self.assertEqual(
            additive.last_error_code, ProtocolError.ADDITIVE_EFFECT_FORBIDDEN
        )
        self.assertNotIn(
            ProtocolResult.QUEUED, [receipt.result for receipt in game.receipts]
        )

    async def test_permanent_item_mask_command_is_validated_and_idempotent(
        self,
    ) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)

        applied = await bridge.send_command(
            ProtocolCommand.RECONCILE_PERMANENT_ITEMS, 0b111, command_id=4
        )
        duplicate = await bridge.send_command(
            ProtocolCommand.RECONCILE_PERMANENT_ITEMS, 0b111, command_id=4
        )
        conflict = await bridge.send_command(
            ProtocolCommand.RECONCILE_PERMANENT_ITEMS, 0b001, command_id=4
        )
        invalid = await bridge.send_command(
            ProtocolCommand.RECONCILE_PERMANENT_ITEMS, 0b1000, command_id=5
        )

        self.assertEqual(applied.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(duplicate.last_command_result, ProtocolResult.APPLIED)
        self.assertEqual(game.permanent_item_apply_count, 1)
        self.assertEqual(game.permanent_item_target_mask, 0b111)
        self.assertEqual(
            conflict.last_error_code, ProtocolError.DUPLICATE_COMMAND_CONFLICT
        )
        self.assertEqual(invalid.last_command_result, ProtocolResult.INVALID_PAYLOAD)

    async def test_query_remains_available_at_title(self) -> None:
        game = FakeGame(self.path)
        bridge = self.bridge(game, "title")
        await bridge.initialize(ClientStatus.AP_DISCONNECTED)
        snapshot = await bridge.query(ClientStatus.AP_DISCONNECTED)
        self.assertTrue(snapshot.at_title_menu)
        self.assertEqual(snapshot.last_command_result, ProtocolResult.OK)

    async def test_unknown_command_receipt_remains_parseable(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game, "unknown-command")
        snapshot = game.snapshot()
        contract = (
            f"{snapshot.protocol_version} {snapshot.game_integration_version} "
            f"{snapshot.state_schema_version} {snapshot.slot_data_version} "
            f"{snapshot.item_table_version} {snapshot.location_table_version} "
            f'{snapshot.mission_table_version} "{snapshot.item_table_hash}" '
            f'"{snapshot.location_table_hash}" "{snapshot.mission_table_hash}"'
        )
        game.handle(
            f'(ap-command! "{bridge.session_id}" "{bridge.session_nonce}" '
            f"0 999 0 {bridge._ap_state_wire_fields()} {contract})"
        )

        rejected = parse_snapshot_text(self.path.read_text(encoding="utf-8"))
        self.assertIsNotNone(rejected)
        assert rejected is not None
        self.assertEqual(rejected.last_command_kind, 999)
        self.assertEqual(rejected.last_command, ProtocolCommand.NONE)
        self.assertEqual(rejected.last_command_result, ProtocolResult.FAILED)
        self.assertEqual(rejected.last_error_code, ProtocolError.UNKNOWN_COMMAND)
        self.assertEqual(rejected.recent_command_receipts[0].command_kind, 999)

        heartbeat = await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(heartbeat.last_command_result, ProtocolResult.PONG)
        self.assertEqual(heartbeat.recent_command_receipts[0].command_kind, 999)

    async def test_invalid_query_and_disconnect_statuses_do_not_publish_them(
        self,
    ) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game, "invalid-control-status")
        original_status = game.client_status
        state_fields = bridge._ap_state_wire_fields()

        game.handle(
            f'(ap-query-state! "{bridge.session_id}" "{bridge.session_nonce}" '
            f"99 {state_fields})"
        )
        rejected_query = parse_snapshot_text(self.path.read_text(encoding="utf-8"))
        self.assertIsNotNone(rejected_query)
        assert rejected_query is not None
        self.assertEqual(
            rejected_query.last_command_result, ProtocolResult.INVALID_PAYLOAD
        )
        self.assertEqual(rejected_query.last_error_code, ProtocolError.INVALID_PAYLOAD)
        self.assertEqual(rejected_query.client_status, original_status)
        self.assertTrue(rejected_query.connection_ready)

        game.handle(
            f'(ap-client-disconnect! "{bridge.session_id}" '
            f'"{bridge.session_nonce}" 0 99)'
        )
        rejected_disconnect = parse_snapshot_text(self.path.read_text(encoding="utf-8"))
        self.assertIsNotNone(rejected_disconnect)
        assert rejected_disconnect is not None
        self.assertEqual(
            rejected_disconnect.last_command_result, ProtocolResult.INVALID_PAYLOAD
        )
        self.assertEqual(
            rejected_disconnect.last_error_code, ProtocolError.INVALID_PAYLOAD
        )
        self.assertEqual(rejected_disconnect.client_status, original_status)
        self.assertTrue(rejected_disconnect.connection_ready)

        heartbeat = await bridge.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(heartbeat.last_command_result, ProtocolResult.PONG)

    async def test_all_runtime_unsafe_flags_reject_mutation(self) -> None:
        cases = (
            "title",
            "loading",
            "cutscene",
            "dead",
            "restarting",
            "transition",
            "vehicle",
            "ambiguous",
        )
        for index, field in enumerate(cases):
            with self.subTest(field=field):
                game = FakeGame(self.path)
                bridge = await self.ready(game, f"unsafe-{index}")
                setattr(game, field, True)
                snapshot = await bridge.set_test_target(True)
                self.assertEqual(
                    snapshot.last_command_result, ProtocolResult.UNSAFE_NOW
                )
                self.assertEqual(
                    snapshot.last_error_code, ProtocolError.UNSAFE_GAME_STATE
                )

        for index, field in enumerate(("target_available", "level_available")):
            with self.subTest(field=field):
                game = FakeGame(self.path)
                bridge = await self.ready(game, f"missing-runtime-{index}")
                setattr(game, field, False)
                snapshot = await bridge.set_test_target(True)
                self.assertEqual(
                    snapshot.last_command_result, ProtocolResult.UNSAFE_NOW
                )
                self.assertEqual(
                    snapshot.last_error_code, ProtocolError.UNSAFE_GAME_STATE
                )

    async def test_missing_save_and_unbound_state_are_distinct(self) -> None:
        game = FakeGame(self.path)
        bridge = self.bridge(game, "binding")
        bridge.set_ap_state_status(
            loaded=True,
            bound=True,
            native_save_slot=0,
            native_save_identity=str(uuid.uuid4()),
        )
        await bridge.initialize(ClientStatus.AP_CONNECTED)
        missing = await bridge.set_test_target(True)
        self.assertEqual(missing.last_error_code, ProtocolError.SAVE_NOT_LOADED)

        game.save_loaded = True
        game.save_slot = 0
        game.save_identity = str(uuid.uuid4())
        game.title = False
        bridge.set_ap_state_status(
            loaded=True,
            bound=False,
            native_save_slot=game.save_slot,
            native_save_identity=game.save_identity,
        )
        await bridge.ping(ClientStatus.AP_CONNECTED)
        unbound = await bridge.set_test_target(True)
        self.assertEqual(unbound.last_error_code, ProtocolError.AP_STATE_NOT_BOUND)

    async def test_stale_sidecar_ack_cannot_rebind_a_switched_save(self) -> None:
        for case in ("identity", "slot"):
            with self.subTest(case=case):
                game = FakeGame(self.path)
                bridge = await self.ready(game, f"stale-{case}")
                if case == "identity":
                    game.save_identity = str(uuid.uuid4())
                else:
                    game.save_slot = 1
                game.ap_loaded = False
                game.ap_bound = False

                heartbeat = await bridge.ping(ClientStatus.AP_CONNECTED)
                self.assertFalse(heartbeat.ap_state_loaded)
                self.assertFalse(heartbeat.ap_state_bound)
                self.assertFalse(heartbeat.safe_to_apply_permanent_item)

                rejected = await bridge.set_test_target(True)
                self.assertEqual(
                    rejected.last_error_code, ProtocolError.AP_STATE_NOT_LOADED
                )
                self.assertFalse(game.test_target)
                self.assertEqual(game.apply_count, 0)

    async def test_command_refreshes_cleared_sidecar_state_before_safety(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        bridge.set_ap_state_status(loaded=False, bound=False)

        self.assertTrue(game.ap_bound)
        rejected = await bridge.set_test_target(True)
        self.assertEqual(rejected.last_error_code, ProtocolError.AP_STATE_NOT_LOADED)
        self.assertFalse(game.ap_loaded)
        self.assertFalse(game.ap_bound)
        self.assertFalse(game.test_target)

    async def test_version_and_table_mismatches_are_explicit(self) -> None:
        with self.assertRaisesRegex(ProtocolVersionMismatch, "expects 3"):
            await self.bridge(FakeGame(self.path, protocol=2), "protocol").initialize(
                ClientStatus.AP_DISCONNECTED
            )
        with self.assertRaisesRegex(GameIntegrationVersionMismatch, "expects 2"):
            await self.bridge(
                FakeGame(self.path, integration=99), "integration"
            ).initialize(ClientStatus.AP_DISCONNECTED)

        game = FakeGame(self.path)
        game.publish()
        incompatible = replace(game.snapshot(), item_table_hash="wrong")
        self.path.write_text(format_snapshot(incompatible), encoding="utf-8")
        with self.assertRaises(DataContractMismatch):
            await self.bridge(game, "table")._wait_for(
                lambda _: True, "snapshot", check_versions=True
            )

        game = FakeGame(self.path)
        bridge = await self.ready(game, "overlength-table-hash")
        snapshot = game.snapshot()
        game.handle(
            f'(ap-command! "{bridge.session_id}" "{bridge.session_nonce}" '
            f"0 {int(ProtocolCommand.SET_TEST_TARGET)} 1 "
            f"{bridge._ap_state_wire_fields()} "
            f"{snapshot.protocol_version} {snapshot.game_integration_version} "
            f"{snapshot.state_schema_version} {snapshot.slot_data_version} "
            f"{snapshot.item_table_version} {snapshot.location_table_version} "
            f'{snapshot.mission_table_version} "{snapshot.item_table_hash}x" '
            f'"{snapshot.location_table_hash}" "{snapshot.mission_table_hash}")'
        )
        rejected = parse_snapshot_text(self.path.read_text(encoding="utf-8"))
        self.assertIsNotNone(rejected)
        assert rejected is not None
        self.assertEqual(rejected.last_command_result, ProtocolResult.INCOMPATIBLE)
        self.assertEqual(rejected.last_error_code, ProtocolError.ITEM_TABLE_MISMATCH)
        self.assertFalse(game.test_target)
        self.assertEqual(game.high_watermark, -1)
        self.assertEqual(game.receipts, [])

    async def test_receipt_ring_limit_and_communication_loss(self) -> None:
        game = FakeGame(self.path)
        bridge = await self.ready(game)
        for command_id in range(9):
            await bridge.set_test_target(bool(command_id % 2), command_id=command_id)
        self.assertEqual(len(game.receipts), 8)
        old = await bridge.set_test_target(False, command_id=0)
        self.assertEqual(old.last_error_code, ProtocolError.OUT_OF_ORDER_COMMAND_ID)

        before = game.test_target
        game.running = False
        with self.assertRaisesRegex(ConnectionError, "game is not running"):
            await bridge.set_test_target(not before)
        self.assertEqual(game.test_target, before)


class SnapshotContractTest(unittest.TestCase):
    def test_all_fields_and_receipts_round_trip(self) -> None:
        receipt = CommandReceipt(
            12,
            ProtocolCommand.SET_TEST_TARGET,
            1,
            ProtocolResult.APPLIED,
            ProtocolError.NONE,
        )
        snapshot = BridgeSnapshot(
            snapshot_revision=3,
            connection_ready=True,
            client_session_id="client",
            session_nonce=str(uuid.uuid4()),
            client_heartbeat=4,
            client_status=ClientStatus.AP_CONNECTED,
            game_heartbeat=5,
            game_status=GameStatus.READY,
            save_loaded=True,
            native_save_slot=2,
            native_save_identity=str(uuid.uuid4()),
            consumed_save_identity=str(uuid.uuid4()),
            native_save_eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
            ap_state_loaded=True,
            ap_state_bound=True,
            current_level="city",
            current_act=2,
            current_task=7,
            current_task_node=42,
            at_title_menu=False,
            safe_to_apply_permanent_item=True,
            test_target=True,
            last_command_id=12,
            last_command_kind=ProtocolCommand.SET_TEST_TARGET,
            last_command_result=ProtocolResult.APPLIED,
            recent_command_receipts=(receipt,),
        )
        self.assertEqual(parse_snapshot_text(format_snapshot(snapshot)), snapshot)

    def test_unknown_fields_are_forward_safe(self) -> None:
        text = format_snapshot(BridgeSnapshot()).replace(
            "snapshot_end", "future_optional_field value\nsnapshot_end"
        )
        self.assertIsNotNone(parse_snapshot_text(text))

    def test_optional_goal_diagnostics_round_trip(self) -> None:
        event = GoalDiagnosticRecord(7, 100, 1, 100, 0, 0, 1, 0, 3, 4, 5)
        snapshot = BridgeSnapshot(
            diagnostic_dropped_count=2,
            diagnostic_next_sequence=8,
            diagnostic_events=(event,),
        )
        self.assertEqual(parse_snapshot_text(format_snapshot(snapshot)), snapshot)

    def test_malformed_optional_goal_record_does_not_break_protocol_snapshot(
        self,
    ) -> None:
        text = format_snapshot(
            BridgeSnapshot(
                diagnostic_next_sequence=2,
                diagnostic_events=(
                    GoalDiagnosticRecord(1, 10, 1, 100, 0, 0, 1, 0, 0, 0, 0),
                ),
            )
        ).replace(
            "diagnostic_event_0 1 10 1 100 0 0 1 0 0 0 0",
            "diagnostic_event_0 malformed",
        )
        parsed = parse_snapshot_text(text)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertTrue(parsed.diagnostic_malformed)
        self.assertEqual(parsed.diagnostic_events, ())

    def test_missing_diagnostic_activation_is_an_optional_capture_gap(self) -> None:
        text = format_snapshot(BridgeSnapshot()).replace(
            "diagnostic_activation_generation 1\n", ""
        )
        parsed = parse_snapshot_text(text)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertTrue(parsed.diagnostic_malformed)
        self.assertIsNone(parsed.diagnostic_activation_generation)
        self.assertEqual(parsed.diagnostic_events, ())

    def test_torn_duplicate_and_malformed_snapshots_are_ignored(self) -> None:
        complete = format_snapshot(BridgeSnapshot())
        invalid = (
            complete.replace("snapshot_end 0", "snapshot_end 1"),
            complete.replace("loading 0", "loading maybe"),
            complete.replace("loading 0", "loading 0\nloading 0"),
            complete.replace(f"bridge_runtime_version {BRIDGE_RUNTIME_VERSION}\n", ""),
            complete.replace("bridge_activation_generation 1\n", ""),
            complete.replace(
                "bridge_activation_generation 1\n",
                "bridge_activation_generation 0\n",
            ),
            "snapshot_begin 2\nprotocol_version 3\n",
        )
        for text in invalid:
            self.assertIsNone(parse_snapshot_text(text))


if __name__ == "__main__":
    unittest.main()
