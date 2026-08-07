import re
import unittest

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from worlds.jak3.agents.protocol import (
    GAME_INTEGRATION_VERSION,
    PROTOCOL_VERSION,
    BridgeProtocol,
    BridgeSnapshot,
    ClientStatus,
    GameIntegrationVersionMismatch,
    GameStatus,
    ProtocolCommand,
    ProtocolResult,
    ProtocolVersionMismatch,
    format_snapshot,
    parse_snapshot_text,
)


class FakeGame:
    def __init__(
        self,
        state_path: Path,
        *,
        protocol_version: int = PROTOCOL_VERSION,
        integration_version: int = GAME_INTEGRATION_VERSION,
        running: bool = True,
    ) -> None:
        self.state_path = state_path
        self.protocol_version = protocol_version
        self.integration_version = integration_version
        self.running = running
        self.revision = 0
        self.unique_ping_count = 0
        self.publish_duplicate_pings = True
        self.reset_state()

    def reset_state(self) -> None:
        self.snapshot = BridgeSnapshot(
            snapshot_revision=0,
            protocol_version=self.protocol_version,
            game_integration_version=self.integration_version,
            connection_ready=False,
            session_id="-",
            client_heartbeat=-1,
            client_status=ClientStatus.STARTING,
            game_heartbeat=0,
            game_status=GameStatus.SOURCE_LOADED,
            last_command=ProtocolCommand.NONE,
            last_command_sequence=-1,
            last_result=ProtocolResult.NONE,
            message="source-loaded",
        )

    def publish(self) -> None:
        self.revision += 1
        self.snapshot = replace(self.snapshot, snapshot_revision=self.revision)
        self.state_path.write_text(format_snapshot(self.snapshot), encoding="utf-8")

    def restart(self) -> None:
        self.reset_state()
        if self.running:
            self.publish()

    def handle(self, form: str) -> None:
        if not self.running:
            raise ConnectionError("game is not running")
        if form.startswith("(ap-set-state-path! "):
            self.publish()
            return

        hello = re.fullmatch(r'\(ap-client-hello! (\d+) (\d+) "([^"]+)" (\d+)\)', form)
        if hello:
            protocol, integration, session, status = hello.groups()
            self.snapshot = replace(
                self.snapshot,
                connection_ready=True,
                session_id=session,
                client_heartbeat=-1,
                client_status=ClientStatus(int(status)),
                game_heartbeat=0,
                game_status=GameStatus.READY,
                last_command=ProtocolCommand.HELLO,
                last_command_sequence=-1,
                last_result=ProtocolResult.OK,
                message="ready",
            )
            if int(protocol) != self.protocol_version:
                self.snapshot = replace(
                    self.snapshot,
                    connection_ready=False,
                    game_status=GameStatus.PROTOCOL_MISMATCH,
                    last_result=ProtocolResult.PROTOCOL_MISMATCH,
                    message="protocol-mismatch",
                )
            elif int(integration) != self.integration_version:
                self.snapshot = replace(
                    self.snapshot,
                    connection_ready=False,
                    game_status=GameStatus.INTEGRATION_MISMATCH,
                    last_result=ProtocolResult.INTEGRATION_MISMATCH,
                    message="integration-mismatch",
                )
            self.publish()
            return

        ping = re.fullmatch(r'\(ap-ping! "([^"]+)" (\d+) (\d+)\)', form)
        if ping:
            session, sequence_text, status_text = ping.groups()
            sequence = int(sequence_text)
            if session != self.snapshot.session_id or not self.snapshot.connection_ready:
                self.snapshot = replace(
                    self.snapshot,
                    last_command=ProtocolCommand.PING,
                    last_command_sequence=sequence,
                    last_result=ProtocolResult.INVALID_SESSION,
                    message="invalid-session",
                )
            elif sequence > self.snapshot.client_heartbeat:
                self.unique_ping_count += 1
                self.snapshot = replace(
                    self.snapshot,
                    client_heartbeat=sequence,
                    client_status=ClientStatus(int(status_text)),
                    game_heartbeat=sequence + 1,
                    last_command=ProtocolCommand.PING,
                    last_command_sequence=sequence,
                    last_result=ProtocolResult.PONG,
                    message="pong",
                )
            elif not self.publish_duplicate_pings:
                return
            self.publish()
            return

        disconnect = re.fullmatch(r'\(ap-client-disconnect! "([^"]+)" (\d+) (\d+)\)', form)
        if disconnect:
            session, sequence, status = disconnect.groups()
            if session == self.snapshot.session_id:
                self.snapshot = replace(
                    self.snapshot,
                    connection_ready=False,
                    client_status=ClientStatus(int(status)),
                    game_status=GameStatus.CLIENT_DISCONNECTED,
                    last_command=ProtocolCommand.DISCONNECT,
                    last_command_sequence=int(sequence),
                    last_result=ProtocolResult.OK,
                    message="client-disconnected",
                )
            self.publish()
            return
        raise AssertionError(f"Unexpected form: {form}")


class FakeRepl:
    def __init__(self, game: FakeGame) -> None:
        self.game = game
        self.forms: list[str] = []

    async def send_form(self, form: str, timeout: float = 10.0) -> str:
        self.forms.append(form)
        self.game.handle(form)
        return "Connected to OpenGOAL test nREPL!"


class ProtocolLifecycleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state_path = Path(self.directory.name) / "bridge-state.tmp"

    def bridge(self, game: FakeGame, session: str) -> BridgeProtocol:
        return BridgeProtocol(
            FakeRepl(game),
            self.state_path,
            session,
            command_timeout=0.03,
            poll_interval=0.001,
        )

    async def test_client_starts_before_game(self) -> None:
        game = FakeGame(self.state_path, running=False)
        protocol = self.bridge(game, "client-before-game")
        with self.assertRaisesRegex(ConnectionError, "game is not running"):
            await protocol.initialize(ClientStatus.AP_DISCONNECTED)
        game.running = True
        snapshot = await protocol.initialize(ClientStatus.AP_DISCONNECTED)
        self.assertTrue(snapshot.connection_ready)

    async def test_game_starts_before_client(self) -> None:
        game = FakeGame(self.state_path)
        snapshot = await self.bridge(game, "game-before-client").initialize(
            ClientStatus.AP_DISCONNECTED
        )
        self.assertEqual(snapshot.session_id, "game-before-client")

    async def test_game_restart_requires_and_accepts_a_new_hello(self) -> None:
        game = FakeGame(self.state_path)
        protocol = self.bridge(game, "long-running-client")
        await protocol.initialize(ClientStatus.AP_CONNECTED)
        await protocol.ping(ClientStatus.AP_CONNECTED)
        game.restart()
        with self.assertRaisesRegex(ConnectionError, "pong"):
            await protocol.ping(ClientStatus.AP_CONNECTED)
        await protocol.initialize(ClientStatus.AP_CONNECTED)
        snapshot = await protocol.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(snapshot.game_heartbeat, 1)

    async def test_client_restart_replaces_session_without_restarting_game(self) -> None:
        game = FakeGame(self.state_path)
        first = self.bridge(game, "first-client")
        await first.initialize(ClientStatus.AP_CONNECTED)
        await first.ping(ClientStatus.AP_CONNECTED)
        second = self.bridge(game, "second-client")
        await second.initialize(ClientStatus.AP_CONNECTED)
        snapshot = await second.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(snapshot.session_id, "second-client")
        self.assertEqual(snapshot.client_heartbeat, 0)

    async def test_protocol_version_mismatch_is_explicit(self) -> None:
        game = FakeGame(self.state_path, protocol_version=1)
        with self.assertRaisesRegex(ProtocolVersionMismatch, "expects 2, game reports 1"):
            await self.bridge(game, "mismatch").initialize(ClientStatus.AP_DISCONNECTED)

    async def test_game_integration_mismatch_is_explicit(self) -> None:
        game = FakeGame(self.state_path, integration_version=99)
        with self.assertRaisesRegex(
            GameIntegrationVersionMismatch, "expects 1, game reports 99"
        ):
            await self.bridge(game, "mismatch").initialize(ClientStatus.AP_DISCONNECTED)

    async def test_duplicate_ping_is_idempotent(self) -> None:
        game = FakeGame(self.state_path)
        protocol = self.bridge(game, "duplicate-ping")
        await protocol.initialize(ClientStatus.AP_CONNECTED)
        first = await protocol.ping(ClientStatus.AP_CONNECTED, sequence=7)
        second = await protocol.ping(ClientStatus.AP_CONNECTED, sequence=7)
        self.assertEqual(first.game_heartbeat, 8)
        self.assertEqual(second.game_heartbeat, 8)
        self.assertGreater(second.snapshot_revision, first.snapshot_revision)
        self.assertEqual(game.unique_ping_count, 1)

    async def test_duplicate_ping_requires_a_fresh_snapshot(self) -> None:
        game = FakeGame(self.state_path)
        protocol = self.bridge(game, "stale-duplicate-ping")
        await protocol.initialize(ClientStatus.AP_CONNECTED)
        accepted = await protocol.ping(ClientStatus.AP_CONNECTED, sequence=7)
        game.publish_duplicate_pings = False

        with self.assertRaisesRegex(ConnectionError, "pong 8"):
            await protocol.ping(ClientStatus.AP_CONNECTED, sequence=7)

        self.assertEqual(game.snapshot.snapshot_revision, accepted.snapshot_revision)

    async def test_communication_loss_does_not_mutate_game_state(self) -> None:
        game = FakeGame(self.state_path)
        protocol = self.bridge(game, "communication-loss")
        await protocol.initialize(ClientStatus.AP_CONNECTED)
        before = game.snapshot
        game.running = False
        with self.assertRaisesRegex(ConnectionError, "game is not running"):
            await protocol.ping(ClientStatus.AP_CONNECTED)
        self.assertEqual(game.snapshot, before)
        self.assertEqual(game.unique_ping_count, 0)


class SnapshotContractTest(unittest.TestCase):
    def test_complete_snapshot_round_trips(self) -> None:
        snapshot = BridgeSnapshot(
            snapshot_revision=3,
            protocol_version=PROTOCOL_VERSION,
            game_integration_version=GAME_INTEGRATION_VERSION,
            connection_ready=True,
            session_id="session",
            client_heartbeat=4,
            client_status=ClientStatus.AP_CONNECTED,
            game_heartbeat=5,
            game_status=GameStatus.READY,
            last_command=ProtocolCommand.PING,
            last_command_sequence=4,
            last_result=ProtocolResult.PONG,
            message="pong",
        )
        self.assertEqual(parse_snapshot_text(format_snapshot(snapshot)), snapshot)

    def test_torn_snapshot_is_ignored(self) -> None:
        self.assertIsNone(parse_snapshot_text("snapshot_begin 2\nprotocol_version 2\n"))
        self.assertIsNone(
            parse_snapshot_text("snapshot_begin 2\nprotocol_version 2\nsnapshot_end 1\n")
        )


if __name__ == "__main__":
    unittest.main()
