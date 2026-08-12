import asyncio
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from worlds.jak3 import location_outbox
from worlds.jak3.agents.diagnostics import GoalDiagnosticRecord
from worlds.jak3.client import Jak3Context, common_client
from worlds.jak3.location_outbox import (
    ARENA_TRAINING_LOCATION_ID,
    DEBUG_LOCATION_ID,
    LOCATION_OBSERVED_GOAL_CODE,
    LocationPacketError,
    diagnostic_batch_id,
    observe_local_location,
    parse_server_location_update,
    reconcile_connected,
    reconcile_room_update,
)
from worlds.jak3.option_resolution import SUPPORTED_FIRST_RELEASE_OPTIONS
from worlds.jak3.persistence import (
    AuthenticatedSlot,
    NativeSaveDescriptor,
    NativeSaveEligibility,
    PersistentState,
    StateCorruptionError,
    StateError,
    StateRepository,
)
from worlds.jak3.registry import FIRST_RELEASE_LOCATIONS
from worlds.jak3.received_items import JETBOARD_ITEM_ID
from worlds.jak3.slot_data import build_slot_data


SAVE_ID = "00000000-0000-4000-8000-000000000090"
STATE_ID = "00000000-0000-4000-8000-000000000091"


def descriptor() -> NativeSaveDescriptor:
    return NativeSaveDescriptor(
        slot=0,
        identity=SAVE_ID,
        eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
    )


def slot() -> AuthenticatedSlot:
    contract = build_slot_data(
        SUPPORTED_FIRST_RELEASE_OPTIONS, seed_identifier="milestone-9-seed"
    )
    return AuthenticatedSlot.from_connected_packet(
        contract, team=0, slot=1, slot_name="Jak"
    )


def empty_state() -> PersistentState:
    return PersistentState.create_unbound(descriptor(), state_instance_id=STATE_ID)


def goal_observation(
    location_id: int, task_id: int, source: int, *, sequence: int = 4
) -> GoalDiagnosticRecord:
    return GoalDiagnosticRecord(
        source_sequence=sequence,
        game_tick=100,
        severity=1,
        event_code=LOCATION_OBSERVED_GOAL_CODE,
        correlation_kind=3,
        correlation_value=location_id,
        result=1,
        error=0,
        arg0=task_id,
        arg1=source,
        arg2=0,
    )


class LocationTransitionTest(unittest.TestCase):
    def test_first_completion_and_both_replays_are_idempotent(self) -> None:
        first = observe_local_location(empty_state(), ARENA_TRAINING_LOCATION_ID)
        self.assertTrue(first.changed)
        self.assertEqual(
            first.state.checked_location_bits, (ARENA_TRAINING_LOCATION_ID,)
        )
        self.assertEqual(
            first.state.pending_location_outbox, (ARENA_TRAINING_LOCATION_ID,)
        )
        self.assertEqual(first.state.server_confirmed_location_bits, ())

        mission_replay = observe_local_location(first.state, ARENA_TRAINING_LOCATION_ID)
        self.assertFalse(mission_replay.changed)
        debug = observe_local_location(first.state, DEBUG_LOCATION_ID)
        debug_replay = observe_local_location(debug.state, DEBUG_LOCATION_ID)
        self.assertTrue(debug.changed)
        self.assertFalse(debug_replay.changed)
        self.assertEqual(
            debug.state.pending_location_outbox,
            (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
        )

    def test_connected_room_update_and_server_rollback_preserve_local_bits(
        self,
    ) -> None:
        local = observe_local_location(empty_state(), ARENA_TRAINING_LOCATION_ID).state
        connected = reconcile_connected(local, {DEBUG_LOCATION_ID})
        self.assertEqual(
            connected.state.checked_location_bits,
            (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
        )
        self.assertEqual(
            connected.state.server_confirmed_location_bits, (DEBUG_LOCATION_ID,)
        )
        self.assertEqual(
            connected.state.pending_location_outbox, (ARENA_TRAINING_LOCATION_ID,)
        )

        partial = reconcile_room_update(connected.state, {ARENA_TRAINING_LOCATION_ID})
        self.assertEqual(partial.state.pending_location_outbox, ())
        rolled_back = reconcile_connected(partial.state, set())
        self.assertEqual(
            rolled_back.state.checked_location_bits,
            (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
        )
        self.assertEqual(
            rolled_back.state.pending_location_outbox,
            (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
        )

    def test_checked_ids_must_be_exactly_partitioned(self) -> None:
        with self.assertRaisesRegex(StateCorruptionError, "exactly partitioned"):
            replace(
                empty_state(),
                checked_location_bits=(ARENA_TRAINING_LOCATION_ID,),
            )

    def test_batch_id_uses_state_instance_and_committed_revision(self) -> None:
        state = empty_state()
        self.assertNotEqual(
            diagnostic_batch_id(state),
            diagnostic_batch_id(replace(state, state_revision=1)),
        )


class ServerPacketValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = slot().contract
        self.all_ids = sorted(record.code for record in FIRST_RELEASE_LOCATIONS)

    def connected(self, **changes: object) -> dict[str, object]:
        packet: dict[str, object] = {
            "cmd": "Connected",
            "slot_data": self.contract,
            "checked_locations": [],
            "missing_locations": self.all_ids,
        }
        packet.update(changes)
        return packet

    def test_connected_is_canonical_and_room_update_is_partial(self) -> None:
        connected = parse_server_location_update(
            self.connected(), connected=True, slot_data=self.contract
        )
        self.assertTrue(connected.full)
        partial = parse_server_location_update(
            {"cmd": "RoomUpdate", "checked_locations": [DEBUG_LOCATION_ID]},
            connected=False,
            slot_data=self.contract,
        )
        self.assertFalse(partial.full)
        self.assertEqual(partial.checked_locations, (DEBUG_LOCATION_ID,))

    def test_unknown_retired_disabled_malformed_and_table_mismatch_reject(self) -> None:
        malformed_packets = (
            self.connected(checked_locations="not-a-list"),
            self.connected(checked_locations=[True]),
            self.connected(checked_locations=[DEBUG_LOCATION_ID, DEBUG_LOCATION_ID]),
            self.connected(checked_locations=[999_999_999]),
            self.connected(checked_locations=[743_001_006]),
            self.connected(missing_locations=self.all_ids[:-1]),
        )
        for packet in malformed_packets:
            with self.subTest(packet=packet):
                with self.assertRaises(LocationPacketError):
                    parse_server_location_update(
                        packet, connected=True, slot_data=self.contract
                    )

        mismatched = dict(self.contract)
        mismatched["location_table_hash"] = "0" * 64
        with self.assertRaises(LocationPacketError):
            parse_server_location_update(
                self.connected(), connected=True, slot_data=mismatched
            )

        enabled_subset = frozenset(self.all_ids[:-1])
        with (
            patch.object(
                location_outbox, "enabled_location_ids", return_value=enabled_subset
            ),
            self.assertRaisesRegex(LocationPacketError, "slot-disabled"),
        ):
            parse_server_location_update(
                self.connected(), connected=True, slot_data=self.contract
            )


class LocationPersistenceAndClientTest(unittest.TestCase):
    @staticmethod
    def context(session: object) -> Jak3Context:
        context = object.__new__(Jak3Context)
        context.state_session = session
        context.server = None
        context.authenticated_slot = slot()
        context.compatibility_error = False
        context.persistence_read_only_failure = ""
        context.diagnostics = SimpleNamespace(
            emit=lambda *_args, **_kwargs: True,
            capture_exception=lambda *_args, **_kwargs: None,
            ingest_goal_events=lambda records, **_kwargs: (
                records[-1].source_sequence if records else None
            ),
        )
        context._ensure_location_runtime()
        return context

    @staticmethod
    def authenticate(context: Jak3Context) -> None:
        context._activate_location_transport()

    def test_goal_ack_is_withheld_until_atomic_commit_then_replay_is_duplicate(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor(), slot())
            context = self.context(session)
            record = goal_observation(ARENA_TRAINING_LOCATION_ID, 10, 0)

            self.assertEqual(context._ingest_goal_events((record,), 0), 4)
            committed_revision = session.state.state_revision
            self.assertEqual(
                session.state.pending_location_outbox,
                (ARENA_TRAINING_LOCATION_ID,),
            )
            self.assertEqual(context._ingest_goal_events((record,), 0), 4)
            self.assertEqual(session.state.state_revision, committed_revision)
            session.close(clean=False)

    def test_commit_failure_withholds_ack_and_does_not_mutate_state(self) -> None:
        class FailingSession:
            def __init__(self, state: PersistentState) -> None:
                self.state = state

            def commit(self, _state: PersistentState, *, category: str) -> None:
                raise StateError(f"failed {category}")

        bound = empty_state().bind(slot())
        failing = FailingSession(bound)
        context = self.context(failing)
        record = goal_observation(DEBUG_LOCATION_ID, 11, 1)

        self.assertIsNone(context._ingest_goal_events((record,), 0))
        self.assertEqual(failing.state.checked_location_bits, ())
        self.assertEqual(failing.state.pending_location_outbox, ())

    def test_diagnostic_failure_after_commit_withholds_ack_without_corruption(
        self,
    ) -> None:
        class FailingDiagnostics:
            attempts = 0

            @staticmethod
            def emit(*_args: object, **_kwargs: object) -> None:
                raise OSError("diagnostic writer unavailable")

            def ingest_goal_events(
                self, records: tuple[GoalDiagnosticRecord, ...], **_kwargs: object
            ) -> int | None:
                self.attempts += 1
                return None if self.attempts == 1 else records[-1].source_sequence

        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor(), slot())
            context = self.context(session)
            context.diagnostics = FailingDiagnostics()
            record = goal_observation(ARENA_TRAINING_LOCATION_ID, 10, 0)

            self.assertIsNone(context._ingest_goal_events((record,), 0))
            committed_revision = session.state.state_revision
            self.assertEqual(
                session.state.pending_location_outbox,
                (ARENA_TRAINING_LOCATION_ID,),
            )
            self.assertEqual(context._ingest_goal_events((record,), 0), 4)
            self.assertEqual(session.state.state_revision, committed_revision)
            session.close(clean=True)

    def test_invalid_room_update_is_rejected_before_commonclient_mutation(self) -> None:
        async def scenario() -> None:
            context = object.__new__(Jak3Context)
            context.authenticated_slot = slot()
            context.checked_locations = {ARENA_TRAINING_LOCATION_ID}
            context.missing_locations = {DEBUG_LOCATION_ID}
            context.compatibility_error = False
            context.persistence_read_only_failure = ""
            context.diagnostics = SimpleNamespace(emit=lambda *_args, **_kwargs: None)

            await common_client.process_server_cmd(
                context,
                {"cmd": "RoomUpdate", "checked_locations": [999_999_999]},
            )

            self.assertEqual(context.checked_locations, {ARENA_TRAINING_LOCATION_ID})
            self.assertEqual(context.missing_locations, {DEBUG_LOCATION_ID})
            self.assertTrue(context.compatibility_error)
            self.assertTrue(context._location_read_only)

        asyncio.run(scenario())

    def test_offline_restart_replay_confirmation_and_client_restart(self) -> None:
        with TemporaryDirectory() as directory:
            repository = StateRepository(Path(directory))
            first = repository.open(descriptor(), slot())
            first.commit(
                observe_local_location(first.state, ARENA_TRAINING_LOCATION_ID).state,
                category="location_observed",
            )
            first.close(clean=False)

            game_restart = repository.open(descriptor(), slot())
            self.assertEqual(
                game_restart.state.pending_location_outbox,
                (ARENA_TRAINING_LOCATION_ID,),
            )
            replay = observe_local_location(
                game_restart.state, ARENA_TRAINING_LOCATION_ID
            )
            self.assertFalse(replay.changed)
            game_restart.commit(
                reconcile_connected(
                    game_restart.state, {ARENA_TRAINING_LOCATION_ID}
                ).state,
                category="location_reconciliation",
            )
            game_restart.close(clean=False)

            client_restart = repository.open(descriptor(), slot())
            self.assertEqual(
                client_restart.state.checked_location_bits,
                (ARENA_TRAINING_LOCATION_ID,),
            )
            self.assertEqual(client_restart.state.pending_location_outbox, ())
            client_restart.close(clean=True)

    def test_new_binding_uses_one_canonical_accumulated_server_snapshot(self) -> None:
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor(), slot())
            session.commit(
                observe_local_location(session.state, ARENA_TRAINING_LOCATION_ID).state,
                category="location_observed",
            )
            context = self.context(None)
            all_ids = sorted(record.code for record in FIRST_RELEASE_LOCATIONS)
            context._queue_server_location_update(
                {
                    "cmd": "Connected",
                    "slot_data": slot().contract,
                    "checked_locations": [],
                    "missing_locations": all_ids,
                }
            )
            context._queue_server_location_update(
                {
                    "cmd": "RoomUpdate",
                    "checked_locations": [DEBUG_LOCATION_ID],
                }
            )
            self.assertEqual(len(context._location_server_updates), 2)

            revision = session.state.state_revision
            context.state_session = session
            context._drain_location_server_updates()

            self.assertEqual(session.state.state_revision, revision + 1)
            self.assertEqual(
                session.state.checked_location_bits,
                (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
            )
            self.assertEqual(
                session.state.server_confirmed_location_bits,
                (DEBUG_LOCATION_ID,),
            )
            self.assertEqual(
                session.state.pending_location_outbox,
                (ARENA_TRAINING_LOCATION_ID,),
            )
            self.assertEqual(context._location_server_updates, [])
            session.close(clean=True)

    def test_valid_connected_clears_a_prior_location_compatibility_latch(
        self,
    ) -> None:
        context = self.context(None)
        context.server = object()
        context.slot_info = {1: SimpleNamespace(name="Jak")}
        context.protocol_sync_event = asyncio.Event()
        context._set_protocol_save_identity_authorized = lambda _authorized: False
        context.compatibility_error = True
        context._location_read_only = False
        all_ids = sorted(record.code for record in FIRST_RELEASE_LOCATIONS)

        context.on_package(
            "Connected",
            {
                "cmd": "Connected",
                "team": 0,
                "slot": 1,
                "slot_data": slot().contract,
                "checked_locations": [],
                "missing_locations": all_ids,
            },
        )

        self.assertFalse(context.compatibility_error)
        self.assertTrue(context._location_transport_ready())

    def test_sorted_send_failure_duplicate_send_and_confirmation_do_not_compact_early(
        self,
    ) -> None:
        async def scenario() -> None:
            with TemporaryDirectory() as directory:
                session = StateRepository(Path(directory)).open(descriptor(), slot())
                both = observe_local_location(
                    observe_local_location(session.state, DEBUG_LOCATION_ID).state,
                    ARENA_TRAINING_LOCATION_ID,
                ).state
                session.commit(both, category="location_observed")
                context = self.context(session)
                socket_send = AsyncMock(side_effect=[OSError("offline"), None, None])
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=True, closed=False, send=socket_send)
                )
                self.authenticate(context)
                emitted: list[tuple[str, dict[str, object]]] = []
                context.diagnostics.emit = lambda event_name, **fields: emitted.append(
                    (event_name, fields)
                )

                with patch(
                    "worlds.jak3.client.encode", side_effect=lambda value: value
                ):
                    context._pump_location_outbox("offline")
                    await asyncio.sleep(0)
                    self.assertEqual(
                        session.state.pending_location_outbox,
                        (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
                    )
                    context._invalidate_location_transport()
                    self.authenticate(context)
                    context._pump_location_outbox("reconnect")
                    await asyncio.sleep(0)
                    self.assertEqual(
                        socket_send.await_args_list[-1].args[0],
                        [
                            {
                                "cmd": "LocationChecks",
                                "locations": [
                                    ARENA_TRAINING_LOCATION_ID,
                                    DEBUG_LOCATION_ID,
                                ],
                            }
                        ],
                    )
                    self.assertEqual(
                        session.state.pending_location_outbox,
                        (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
                    )
                    context._pump_location_outbox("early_retry")
                    await asyncio.sleep(0)
                    self.assertEqual(socket_send.await_count, 2)

                    context._location_last_send_at = float("-inf")
                    context._pump_location_outbox("duplicate_retry")
                    await asyncio.sleep(0)
                self.assertEqual(socket_send.await_count, 3)
                self.assertEqual(
                    session.state.pending_location_outbox,
                    (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
                )
                batch_events = [
                    fields
                    for event_name, fields in emitted
                    if event_name
                    in {
                        "location.outbox.batch_sent",
                        "location.outbox.send_failed",
                    }
                ]
                self.assertEqual(len(batch_events), 3)
                for fields in batch_events:
                    self.assertEqual(
                        fields["context"]["location_ids"],
                        [ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID],
                    )
                    self.assertEqual(fields["context"]["task_ids"], [10, 11])
                session.close(clean=True)

        asyncio.run(scenario())

    def test_open_socket_checked_sender_uses_the_real_transport(self) -> None:
        async def scenario() -> None:
            with TemporaryDirectory() as directory:
                session = StateRepository(Path(directory)).open(descriptor(), slot())
                session.commit(
                    observe_local_location(
                        session.state, ARENA_TRAINING_LOCATION_ID
                    ).state,
                    category="location_observed",
                )
                context = self.context(session)
                socket_send = AsyncMock()
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=True, closed=False, send=socket_send)
                )
                self.authenticate(context)
                messages = [
                    {
                        "cmd": "LocationChecks",
                        "locations": [ARENA_TRAINING_LOCATION_ID],
                    }
                ]
                projection = context._current_location_projection(
                    session, session.state.pending_location_outbox
                )

                with patch(
                    "worlds.jak3.client.encode", return_value="encoded"
                ) as encoder:
                    await context._send_location_messages_checked(messages, projection)

                encoder.assert_called_once_with(messages)
                socket_send.assert_awaited_once_with("encoded")
                session.close(clean=True)

        asyncio.run(scenario())

    def test_closed_socket_is_a_correlated_send_failure_for_both_paths(self) -> None:
        async def scenario() -> None:
            with TemporaryDirectory() as directory:
                session = StateRepository(Path(directory)).open(descriptor(), slot())
                pending = observe_local_location(
                    session.state, ARENA_TRAINING_LOCATION_ID
                ).state
                session.commit(pending, category="location_observed")
                context = self.context(session)
                socket_send = AsyncMock()
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=False, closed=True, send=socket_send)
                )
                self.authenticate(context)
                emitted: list[tuple[str, dict[str, object]]] = []
                context.diagnostics.emit = lambda event_name, **fields: emitted.append(
                    (event_name, fields)
                )
                projection = (
                    session.state.state_instance_id,
                    session.state.pending_location_outbox,
                    context._location_connection_generation,
                )

                with self.assertRaisesRegex(ConnectionError, "socket is closed"):
                    await context._send_location_outbox(
                        projection,
                        session.state.pending_location_outbox,
                        reason="closed_socket",
                    )
                context._location_last_send_at = float("-inf")
                with self.assertRaisesRegex(ConnectionError, "socket is closed"):
                    await context._send_item_sync(("item_gap", 1, 0))

                socket_send.assert_not_awaited()
                failures = [
                    fields
                    for event_name, fields in emitted
                    if event_name == "location.outbox.send_failed"
                ]
                self.assertEqual(len(failures), 2)
                self.assertEqual(
                    {fields["context"]["source"] for fields in failures},
                    {"client_outbox", "item_gap_sync"},
                )
                for fields in failures:
                    self.assertEqual(
                        fields["context"]["location_ids"],
                        [ARENA_TRAINING_LOCATION_ID],
                    )
                    self.assertEqual(fields["context"]["task_ids"], [10])
                    self.assertEqual(fields["context"]["reason"], "ConnectionError")
                self.assertEqual(
                    session.state.pending_location_outbox,
                    (ARENA_TRAINING_LOCATION_ID,),
                )
                session.close(clean=True)

        asyncio.run(scenario())

    def test_server_rollback_diagnostic_names_every_affected_location(self) -> None:
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor(), slot())
            both = observe_local_location(
                observe_local_location(session.state, DEBUG_LOCATION_ID).state,
                ARENA_TRAINING_LOCATION_ID,
            ).state
            session.commit(both, category="location_observed")
            confirmed = reconcile_connected(
                session.state, {ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID}
            ).state
            session.commit(confirmed, category="location_reconciliation")
            context = self.context(session)
            emitted: list[tuple[str, dict[str, object]]] = []
            context.diagnostics.emit = lambda event_name, **fields: emitted.append(
                (event_name, fields)
            )
            context._location_reconciled_state_instance = (
                session.state.state_instance_id
            )
            context._server_checked_locations = frozenset()
            context._location_server_updates = [(True, ())]

            context._drain_location_server_updates()

            completed = next(
                fields
                for event_name, fields in emitted
                if event_name == "location.reconciliation.completed"
            )
            self.assertEqual(
                completed["context"]["location_ids"],
                [ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID],
            )
            self.assertEqual(completed["context"]["task_ids"], [10, 11])
            self.assertEqual(
                completed["context"]["reason"], "server_rollback_to_pending"
            )
            self.assertEqual(
                session.state.pending_location_outbox,
                (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
            )
            session.close(clean=True)

    def test_item_gap_sync_uses_durable_sorted_outbox_without_compaction(self) -> None:
        async def scenario() -> None:
            with TemporaryDirectory() as directory:
                session = StateRepository(Path(directory)).open(descriptor(), slot())
                both = observe_local_location(
                    observe_local_location(session.state, DEBUG_LOCATION_ID).state,
                    ARENA_TRAINING_LOCATION_ID,
                ).state
                session.commit(both, category="location_observed")
                context = self.context(session)
                socket_send = AsyncMock()
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=True, closed=False, send=socket_send)
                )
                self.authenticate(context)

                with patch(
                    "worlds.jak3.client.encode", side_effect=lambda value: value
                ):
                    await context._send_item_sync(("item_gap", 2, 0))

                socket_send.assert_awaited_once_with(
                    [
                        {"cmd": "Sync"},
                        {
                            "cmd": "LocationChecks",
                            "locations": [
                                ARENA_TRAINING_LOCATION_ID,
                                DEBUG_LOCATION_ID,
                            ],
                        },
                    ]
                )
                self.assertEqual(
                    session.state.pending_location_outbox,
                    (ARENA_TRAINING_LOCATION_ID, DEBUG_LOCATION_ID),
                )
                session.close(clean=True)

        asyncio.run(scenario())

    def test_stale_generation_cannot_send_on_reauthenticated_connection(self) -> None:
        async def scenario() -> None:
            with TemporaryDirectory() as directory:
                session = StateRepository(Path(directory)).open(descriptor(), slot())
                session.commit(
                    observe_local_location(
                        session.state, ARENA_TRAINING_LOCATION_ID
                    ).state,
                    category="location_observed",
                )
                context = self.context(session)
                old_send = AsyncMock()
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=True, closed=False, send=old_send)
                )
                self.authenticate(context)
                pending = session.state.pending_location_outbox
                stale_projection = context._current_location_projection(
                    session, pending
                )

                context._invalidate_location_transport()
                new_send = AsyncMock()
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=True, closed=False, send=new_send)
                )
                self.authenticate(context)
                await context._send_location_outbox(
                    stale_projection, pending, reason="stale_generation"
                )

                old_send.assert_not_awaited()
                new_send.assert_not_awaited()
                with patch("CommonClient.encode", side_effect=lambda value: value):
                    await context.send_msgs(
                        [
                            {
                                "cmd": "LocationChecks",
                                "locations": [DEBUG_LOCATION_ID],
                            },
                            {"cmd": "Get", "keys": ["durable-only"]},
                        ]
                    )
                new_send.assert_awaited_once_with(
                    [{"cmd": "Get", "keys": ["durable-only"]}]
                )
                self.assertEqual(session.state.pending_location_outbox, pending)
                session.close(clean=True)

        asyncio.run(scenario())

    def test_commonclient_gap_sync_attaches_only_the_durable_outbox(self) -> None:
        async def scenario() -> None:
            with TemporaryDirectory() as directory:
                session = StateRepository(Path(directory)).open(descriptor(), slot())
                session.commit(
                    observe_local_location(
                        session.state, ARENA_TRAINING_LOCATION_ID
                    ).state,
                    category="location_observed",
                )
                context = self.context(session)
                socket_send = AsyncMock()
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=True, closed=False, send=socket_send)
                )
                self.authenticate(context)
                context.items_received = []
                context.locations_checked = {DEBUG_LOCATION_ID}
                context.watcher_event = asyncio.Event()
                context.on_package = lambda *_args: None

                with patch(
                    "worlds.jak3.client.encode", side_effect=lambda value: value
                ):
                    await common_client.process_server_cmd(
                        context,
                        {
                            "cmd": "ReceivedItems",
                            "index": 2,
                            "items": [(JETBOARD_ITEM_ID, 1, 1, 0)],
                        },
                    )

                socket_send.assert_awaited_once_with(
                    [
                        {"cmd": "Sync"},
                        {
                            "cmd": "LocationChecks",
                            "locations": [ARENA_TRAINING_LOCATION_ID],
                        },
                    ]
                )
                self.assertEqual(
                    session.state.pending_location_outbox,
                    (ARENA_TRAINING_LOCATION_ID,),
                )
                session.close(clean=True)

        asyncio.run(scenario())

    def test_item_sync_and_outbox_share_one_send_reservation(self) -> None:
        async def scenario() -> None:
            with TemporaryDirectory() as directory:
                session = StateRepository(Path(directory)).open(descriptor(), slot())
                both = observe_local_location(
                    observe_local_location(session.state, DEBUG_LOCATION_ID).state,
                    ARENA_TRAINING_LOCATION_ID,
                ).state
                session.commit(both, category="location_observed")
                context = self.context(session)
                socket_send = AsyncMock()
                context.server = SimpleNamespace(
                    socket=SimpleNamespace(open=True, closed=False, send=socket_send)
                )
                self.authenticate(context)
                emitted: list[tuple[str, dict[str, object]]] = []
                context.diagnostics.emit = lambda event_name, **fields: emitted.append(
                    (event_name, fields)
                )
                pending = session.state.pending_location_outbox
                projection = context._current_location_projection(session, pending)

                with (
                    patch("worlds.jak3.client.encode", side_effect=lambda value: value),
                    patch("CommonClient.encode", side_effect=lambda value: value),
                ):
                    await asyncio.gather(
                        context._send_location_outbox(
                            projection, pending, reason="concurrent"
                        ),
                        context._send_item_sync(("item_gap", 2, 0)),
                    )

                batches = [call.args[0] for call in socket_send.await_args_list]
                location_messages = [
                    message
                    for batch in batches
                    for message in batch
                    if message.get("cmd") == "LocationChecks"
                ]
                self.assertEqual(
                    location_messages,
                    [
                        {
                            "cmd": "LocationChecks",
                            "locations": [
                                ARENA_TRAINING_LOCATION_ID,
                                DEBUG_LOCATION_ID,
                            ],
                        }
                    ],
                )
                sent_events = [
                    fields
                    for event_name, fields in emitted
                    if event_name == "location.outbox.batch_sent"
                ]
                self.assertEqual(len(sent_events), 1)
                self.assertEqual(session.state.pending_location_outbox, pending)
                session.close(clean=True)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
