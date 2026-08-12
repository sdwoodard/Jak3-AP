import asyncio
import unittest

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from worlds.jak3.agents.protocol import (
    BridgeSnapshot,
    ProtocolCommand,
    ProtocolError,
    ProtocolResult,
)
from worlds.jak3.agents.diagnostics import GoalDiagnosticRecord
from worlds.jak3.client import Jak3Context, common_client

from worlds.jak3.persistence import (
    GameCommandReceipt,
    NativeSaveDescriptor,
    NativeSaveEligibility,
    PersistentState,
    ReceivedItemState,
    StateError,
    StateRepository,
)
from worlds.jak3.received_items import (
    ARMOR_STAGE_ONE_TARGET_BIT,
    BLASTER_ITEM_ID,
    BLASTER_TARGET_BIT,
    JETBOARD_ITEM_ID,
    JETBOARD_TARGET_BIT,
    PROGRESSIVE_ARMOR_ITEM_ID,
    PacketOutcome,
    ReceivedItemsPacketError,
    apply_received_items_packet,
    mark_pending_items_applied,
    parse_received_items_packet,
    permanent_item_target_mask,
)


SAVE_ID = "00000000-0000-4000-8000-000000000080"


def empty_state() -> PersistentState:
    return PersistentState.create_unbound(
        NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
    )


def packet(index: int, *items: tuple[int, int, int, int]):
    return parse_received_items_packet({"index": index, "items": list(items)})


class NativeMaskProtocol:
    def __init__(self, *, target_mask: int = 0) -> None:
        self.target_mask = target_mask
        self.apply_count = 0
        self.next_command_id = 0
        self.results: list[ProtocolResult] = []
        self.last_snapshot = BridgeSnapshot(
            session_nonce="crash-window-session",
            native_save_slot=0,
            native_save_identity=SAVE_ID,
            save_loaded=True,
            safe_to_apply_permanent_item=True,
        )

    async def send_command(
        self, kind: ProtocolCommand, target_mask: int
    ) -> BridgeSnapshot:
        if kind is not ProtocolCommand.RECONCILE_PERMANENT_ITEMS:
            raise AssertionError(f"Unexpected command: {kind!r}")
        result = ProtocolResult.ALREADY_APPLIED
        if self.target_mask != target_mask:
            self.target_mask = target_mask
            self.apply_count += 1
            result = ProtocolResult.APPLIED
        command_id = self.next_command_id
        self.next_command_id += 1
        self.results.append(result)
        self.last_snapshot = replace(
            self.last_snapshot,
            snapshot_revision=self.last_snapshot.snapshot_revision + 1,
            last_command_id=command_id,
            last_command_kind=kind,
            last_command_result=result,
            last_error_code=ProtocolError.NONE,
        )
        return self.last_snapshot


class FailingAppliedCommitSession:
    def __init__(self, session: object) -> None:
        self._session = session

    @property
    def state(self) -> PersistentState:
        return self._session.state  # type: ignore[attr-defined,no-any-return]

    def commit(
        self, state: PersistentState, *, category: str = "state_update"
    ) -> PersistentState:
        if category == "permanent_items_applied":
            raise StateError("simulated durable observation failure")
        return self._session.commit(state, category=category)  # type: ignore[attr-defined,no-any-return]


def reconciliation_context(
    session: object, protocol: NativeMaskProtocol
) -> Jak3Context:
    context = object.__new__(Jak3Context)
    context.diagnostics = SimpleNamespace(emit=lambda *_args, **_kw: None)
    context.state_session = session  # type: ignore[assignment]
    context.protocol = protocol  # type: ignore[assignment]
    context.mark_bridge_unavailable = AsyncMock()  # type: ignore[method-assign]
    context._ensure_item_runtime()
    context._item_reconcile_dirty = True
    return context


class ReceivedItemsLedgerTest(unittest.TestCase):
    def test_valid_packet_before_binding_is_held_only_in_memory(self) -> None:
        context = object.__new__(Jak3Context)
        context.diagnostics = SimpleNamespace(emit=lambda *_args, **_kw: None)
        context.state_session = None
        context.items_received = []

        context._observe_received_items(
            {"index": 0, "items": [(JETBOARD_ITEM_ID, -2, 1, 0)]}
        )

        self.assertEqual(len(context._received_item_packets), 1)
        self.assertEqual(
            context._received_item_packets[0][0].entries[0].item_id, JETBOARD_ITEM_ID
        )

    def test_rejection_requests_one_canonical_sync_across_index_zero_replay(
        self,
    ) -> None:
        async def scenario() -> None:
            accepted = apply_received_items_packet(
                empty_state(), packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
            ).state
            context = object.__new__(Jak3Context)
            emitted: list[str] = []
            context.diagnostics = SimpleNamespace(
                emit=lambda event_name, **_kw: emitted.append(event_name)
            )
            context.state_session = SimpleNamespace(state=accepted)
            context.server = object()
            context.locations_checked = {743_020_002}
            context.items_received = [(JETBOARD_ITEM_ID, 1, 1, 0)]
            context.send_msgs = AsyncMock()
            rejected = {
                "cmd": "ReceivedItems",
                "index": 1,
                "items": [(743_010_015, 2, 1, 0)],
            }
            canonical = {
                "cmd": "ReceivedItems",
                "index": 0,
                "items": [
                    (JETBOARD_ITEM_ID, 1, 1, 0),
                    (743_010_015, 2, 1, 0),
                ],
            }

            await common_client.process_server_cmd(context, rejected)
            await common_client.process_server_cmd(context, canonical)
            await asyncio.sleep(0)

            context.send_msgs.assert_awaited_once_with([{"cmd": "Sync"}])
            self.assertEqual(context._received_item_packets, [])
            self.assertEqual(emitted.count("item.receipt.rejected"), 1)

        asyncio.run(scenario())

    def test_commonclient_predispatch_rejects_malformed_packet_without_prefix(
        self,
    ) -> None:
        async def scenario() -> None:
            context = object.__new__(Jak3Context)
            emitted: list[str] = []
            context.diagnostics = SimpleNamespace(
                emit=lambda event_name, **_kw: emitted.append(event_name)
            )
            context.state_session = SimpleNamespace(state=empty_state())
            context.server = object()
            context.locations_checked = set()
            original_items = [object()]
            context.items_received = original_items.copy()
            context.send_msgs = AsyncMock()
            malformed = {
                "cmd": "ReceivedItems",
                "index": 0,
                "items": [
                    (JETBOARD_ITEM_ID, 1, 1, 0),
                    (BLASTER_ITEM_ID, 2),
                ],
            }

            await common_client.process_server_cmd(context, malformed)
            await asyncio.sleep(0)

            self.assertEqual(context.items_received, original_items)
            self.assertEqual(context._received_item_packets, [])
            context.send_msgs.assert_awaited_once_with([{"cmd": "Sync"}])
            self.assertEqual(emitted.count("item.receipt.rejected"), 1)

        asyncio.run(scenario())

    def test_rejection_reports_the_offending_entry_index_and_attribution(
        self,
    ) -> None:
        async def scenario() -> None:
            context = object.__new__(Jak3Context)
            emitted: list[tuple[str, dict[str, object]]] = []
            context.diagnostics = SimpleNamespace(
                emit=lambda event_name, **fields: emitted.append((event_name, fields))
            )
            context.state_session = SimpleNamespace(state=empty_state())
            context.server = object()
            context.locations_checked = set()
            context.items_received = []
            context.send_msgs = AsyncMock()
            rejected = {
                "cmd": "ReceivedItems",
                "index": 4,
                "items": [
                    (JETBOARD_ITEM_ID, 743_020_001, 2, 1),
                    (743_010_015, 743_020_099, 7, 4),
                ],
            }

            await common_client.process_server_cmd(context, rejected)
            await asyncio.sleep(0)

            rejection = next(
                fields
                for event_name, fields in emitted
                if event_name == "item.receipt.rejected"
            )
            self.assertEqual(rejection["correlation_id"], "item:5")
            self.assertEqual(
                rejection["context"],
                {
                    "item_id": 743_010_015,
                    "item_name": "Vulcan Fury",
                    "item_index": 5,
                    "expected_index": 0,
                    "ledger_revision": 0,
                    "target_mask": 0,
                    "outcome": "rejected",
                    "reason": "item_outside_milestone_8",
                    "attribution": {
                        "location_id": 743_020_099,
                        "source_player": 7,
                        "flags": 4,
                    },
                },
            )
            self.assertEqual(context.items_received, [])
            self.assertEqual(context._received_item_packets, [])
            context.send_msgs.assert_awaited_once_with([{"cmd": "Sync"}])

        asyncio.run(scenario())

    def test_commonclient_predispatch_forwards_normalized_valid_packet(self) -> None:
        async def scenario() -> None:
            context = object.__new__(Jak3Context)
            emitted: list[str] = []
            context.diagnostics = SimpleNamespace(
                emit=lambda event_name, **_kw: emitted.append(event_name)
            )
            context.state_session = None
            context.items_received = []
            context.watcher_event = asyncio.Event()
            valid = {
                "cmd": "ReceivedItems",
                "index": 0,
                "items": [(JETBOARD_ITEM_ID, -2, 7)],
            }

            await common_client.process_server_cmd(context, valid)
            await context._item_worker_task

            self.assertEqual(
                [tuple(item) for item in context.items_received],
                [(JETBOARD_ITEM_ID, -2, 7, 0)],
            )
            self.assertEqual(len(context._received_item_packets), 1)
            self.assertEqual(
                context._received_item_packets[0][0].entries[0].item_id,
                JETBOARD_ITEM_ID,
            )
            self.assertTrue(context.watcher_event.is_set())
            self.assertEqual(emitted.count("ap.received_items.packet_observed"), 1)

        asyncio.run(scenario())

    def test_commonclient_gap_sync_is_not_duplicated(self) -> None:
        async def scenario() -> None:
            accepted = apply_received_items_packet(
                empty_state(),
                packet(
                    0,
                    (JETBOARD_ITEM_ID, 1, 1, 0),
                    (BLASTER_ITEM_ID, 2, 1, 0),
                    (PROGRESSIVE_ARMOR_ITEM_ID, 3, 1, 0),
                ),
            ).state
            context = object.__new__(Jak3Context)
            context.diagnostics = SimpleNamespace(emit=lambda *_args, **_kw: None)
            context.state_session = SimpleNamespace(state=accepted)
            context.server = object()
            context.locations_checked = set()
            context.items_received = [object(), object(), object()]
            context.send_msgs = AsyncMock()
            context.protocol = None
            context._commonclient_received_item_count = 3

            context._observe_received_items(
                {"index": 2, "items": [(JETBOARD_ITEM_ID, 4, 1, 0)]}
            )
            await context._item_worker_task
            await asyncio.sleep(0)

            context.send_msgs.assert_not_awaited()

        asyncio.run(scenario())

    def test_durable_gap_after_commonclient_append_requests_sync(self) -> None:
        async def scenario() -> None:
            context = object.__new__(Jak3Context)
            context.diagnostics = SimpleNamespace(emit=lambda *_args, **_kw: None)
            context.state_session = SimpleNamespace(state=empty_state())
            context.server = object()
            context.locations_checked = set()
            context.items_received = [object(), object(), object(), object()]
            context.send_msgs = AsyncMock()
            context.protocol = None
            context._commonclient_received_item_count = 3

            context._observe_received_items(
                {"index": 3, "items": [(JETBOARD_ITEM_ID, 4, 1, 0)]}
            )
            await context._item_worker_task
            await asyncio.sleep(0)

            context.send_msgs.assert_awaited_once_with([{"cmd": "Sync"}])

        asyncio.run(scenario())

    def test_first_and_multi_item_receipt_is_one_pending_transition(self) -> None:
        original = empty_state()
        transition = apply_received_items_packet(
            original,
            packet(
                0,
                (JETBOARD_ITEM_ID, 743_020_001, 2, 1),
                (BLASTER_ITEM_ID, 743_020_002, 3, 0),
                (PROGRESSIVE_ARMOR_ITEM_ID, 743_020_003, 4, 2),
            ),
        )

        self.assertEqual(transition.outcome, PacketOutcome.REPLACED)
        self.assertEqual(transition.state.next_received_item_index, 3)
        self.assertEqual(transition.state.pending_item_application_indices, (0, 1, 2))
        self.assertEqual(
            permanent_item_target_mask(transition.state),
            JETBOARD_TARGET_BIT | BLASTER_TARGET_BIT | ARMOR_STAGE_ONE_TARGET_BIT,
        )
        self.assertEqual(original.next_received_item_index, 0)

    def test_exact_duplicate_is_idempotent_but_conflict_and_overlap_resync(
        self,
    ) -> None:
        first = packet(0, (JETBOARD_ITEM_ID, -2, 7, 0))
        state = apply_received_items_packet(empty_state(), first).state

        duplicate = apply_received_items_packet(
            state, packet(0, (JETBOARD_ITEM_ID, -2, 7, 0))
        )
        conflict = apply_received_items_packet(
            state, packet(0, (JETBOARD_ITEM_ID, -2, 8, 0))
        )
        appended = apply_received_items_packet(
            state, packet(1, (BLASTER_ITEM_ID, -1, 7, 0))
        ).state
        partial = apply_received_items_packet(
            appended,
            packet(
                1,
                (BLASTER_ITEM_ID, -1, 7, 0),
                (PROGRESSIVE_ARMOR_ITEM_ID, 0, 7, 0),
            ),
        )

        self.assertFalse(duplicate.changed)
        self.assertEqual(conflict.outcome, PacketOutcome.REPLACED)
        self.assertTrue(conflict.changed)  # Index zero is canonical replacement.
        self.assertEqual(partial.outcome, PacketOutcome.PARTIAL_OVERLAP)
        self.assertIs(partial.state, appended)

    def test_nonzero_duplicate_gap_and_conflict_do_not_advance(self) -> None:
        state = apply_received_items_packet(
            empty_state(), packet(0, (JETBOARD_ITEM_ID, 10, 1, 0))
        ).state
        duplicate = apply_received_items_packet(
            state, packet(0, (JETBOARD_ITEM_ID, 10, 1, 0))
        )
        gap = apply_received_items_packet(state, packet(2, (BLASTER_ITEM_ID, 11, 1, 0)))

        state = apply_received_items_packet(
            state, packet(1, (BLASTER_ITEM_ID, 11, 1, 0))
        ).state
        historical = apply_received_items_packet(
            state, packet(1, (BLASTER_ITEM_ID, 11, 1, 0))
        )
        conflicting = apply_received_items_packet(
            state, packet(1, (BLASTER_ITEM_ID, 12, 1, 0))
        )

        self.assertFalse(duplicate.changed)
        self.assertEqual(gap.outcome, PacketOutcome.GAP)
        self.assertEqual(historical.outcome, PacketOutcome.DUPLICATE)
        self.assertEqual(conflicting.outcome, PacketOutcome.CONFLICT)
        self.assertEqual(gap.state.next_received_item_index, 1)
        self.assertEqual(conflicting.state.next_received_item_index, 2)

    def test_complete_validation_rejects_packet_without_a_prefix(self) -> None:
        malformed_packets = (
            {"index": 0, "items": [(JETBOARD_ITEM_ID, 1)]},
            {
                "index": 0,
                "items": [
                    (JETBOARD_ITEM_ID, 1, 1, 0),
                    (999_999_999, 2, 1, 0),
                ],
            },
            {
                "index": 0,
                "items": [
                    (JETBOARD_ITEM_ID, 1, 1, 0),
                    (743_010_015, 2, 1, 0),  # Valid Jak 3 item, deferred slice.
                ],
            },
        )
        original = empty_state()
        for raw in malformed_packets:
            with self.subTest(raw=raw), self.assertRaises(ReceivedItemsPacketError):
                parse_received_items_packet(raw)
            self.assertEqual(original.next_received_item_index, 0)
            self.assertEqual(original.received_item_journal, ())

    def test_attribution_and_special_locations_are_persisted_verbatim(self) -> None:
        state = apply_received_items_packet(
            empty_state(),
            packet(
                0,
                (JETBOARD_ITEM_ID, -2, 17, 1),  # Starting inventory.
                (BLASTER_ITEM_ID, -1, 23, 2),  # Cheat/server location.
                (PROGRESSIVE_ARMOR_ITEM_ID, 743_020_001, 99, 4),
            ),
        ).state

        self.assertEqual(
            [
                (entry.location_id, entry.source_player, entry.flags)
                for entry in state.received_item_journal
            ],
            [(-2, 17, 1), (-1, 23, 2), (743_020_001, 99, 4)],
        )

    def test_index_zero_replacement_preserves_application_by_index_and_item(
        self,
    ) -> None:
        received = apply_received_items_packet(
            empty_state(),
            packet(
                0,
                (JETBOARD_ITEM_ID, 1, 1, 0),
                (BLASTER_ITEM_ID, 2, 1, 0),
                (PROGRESSIVE_ARMOR_ITEM_ID, 3, 1, 0),
            ),
        ).state
        applied = mark_pending_items_applied(
            received,
            GameCommandReceipt("nonce:1", "RECONCILE_PERMANENT_ITEMS", "APPLIED"),
        )
        replay = apply_received_items_packet(
            applied,
            packet(
                0,
                (JETBOARD_ITEM_ID, 101, 9, 4),  # Metadata-only change.
                (PROGRESSIVE_ARMOR_ITEM_ID, 2, 1, 0),  # Mismatched item history.
            ),
        )

        self.assertEqual(replay.history_discrepancies, (1, 2))
        self.assertEqual(replay.state.next_received_item_index, 2)
        self.assertEqual(
            replay.state.received_item_journal[0].state, ReceivedItemState.APPLIED
        )
        self.assertEqual(
            replay.state.received_item_journal[1].state, ReceivedItemState.PENDING
        )
        self.assertEqual(replay.state.pending_item_application_indices, (1,))
        self.assertEqual(
            permanent_item_target_mask(replay.state),
            JETBOARD_TARGET_BIT | ARMOR_STAGE_ONE_TARGET_BIT,
        )

    def test_metadata_only_index_zero_replacement_still_reconciles_native_target(
        self,
    ) -> None:
        descriptor = NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor)
            received = apply_received_items_packet(
                session.state, packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
            ).state
            session.commit(
                mark_pending_items_applied(
                    received,
                    GameCommandReceipt(
                        "earlier-session:1",
                        "RECONCILE_PERMANENT_ITEMS",
                        "APPLIED",
                    ),
                ),
                category="permanent_items_applied",
            )
            protocol = NativeMaskProtocol(target_mask=JETBOARD_TARGET_BIT)
            context = reconciliation_context(session, protocol)

            async def scenario() -> None:
                await context._reconcile_permanent_items(session)
                self.assertEqual(protocol.results, [ProtocolResult.ALREADY_APPLIED])

                replaced = await context._commit_received_items_packet(
                    session,
                    packet(0, (JETBOARD_ITEM_ID, 101, 9, 4)),
                )
                self.assertTrue(replaced)
                self.assertEqual(session.state.pending_item_application_indices, ())
                self.assertEqual(
                    (
                        session.state.received_item_journal[0].location_id,
                        session.state.received_item_journal[0].source_player,
                        session.state.received_item_journal[0].flags,
                        session.state.received_item_journal[0].state,
                    ),
                    (101, 9, 4, ReceivedItemState.APPLIED),
                )

                await context._reconcile_permanent_items(session)
                self.assertEqual(
                    protocol.results,
                    [
                        ProtocolResult.ALREADY_APPLIED,
                        ProtocolResult.ALREADY_APPLIED,
                    ],
                )
                self.assertEqual(protocol.target_mask, JETBOARD_TARGET_BIT)

            asyncio.run(scenario())
            session.close(clean=True)

    def test_duplicate_counts_remain_in_ledger_but_native_targets_are_capped(
        self,
    ) -> None:
        state = apply_received_items_packet(
            empty_state(),
            packet(
                0,
                *[(PROGRESSIVE_ARMOR_ITEM_ID, index, 1, 0) for index in range(6)],
            ),
        ).state

        self.assertEqual(dict(state.received_item_counts)[PROGRESSIVE_ARMOR_ITEM_ID], 6)
        self.assertEqual(permanent_item_target_mask(state), ARMOR_STAGE_ONE_TARGET_BIT)

    def test_item_transitions_leave_collectible_totals_byte_for_byte_unchanged(
        self,
    ) -> None:
        original = replace(
            empty_state(), local_earned_precursor_orbs=321, local_earned_skull_gems=45
        )
        received = apply_received_items_packet(
            original, packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
        ).state
        applied = mark_pending_items_applied(
            received,
            GameCommandReceipt("nonce:2", "RECONCILE_PERMANENT_ITEMS", "APPLIED"),
        )

        for state in (received, applied):
            self.assertEqual(state.local_earned_precursor_orbs, 321)
            self.assertEqual(state.local_earned_skull_gems, 45)

    def test_pending_receipt_recovery_dispatches_after_repository_reopen(self) -> None:
        descriptor = NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
        with TemporaryDirectory() as directory:
            repository = StateRepository(Path(directory))
            first = repository.open(descriptor)
            pending = apply_received_items_packet(
                first.state, packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
            ).state
            first.commit(pending, category="received_items")
            first.close(clean=False)  # Crash window 1: no native command yet.

            recovered = repository.open(descriptor)
            protocol = NativeMaskProtocol()
            context = reconciliation_context(recovered, protocol)

            asyncio.run(context._reconcile_permanent_items(recovered))

            self.assertEqual(protocol.results, [ProtocolResult.APPLIED])
            self.assertEqual(protocol.target_mask, JETBOARD_TARGET_BIT)
            self.assertEqual(recovered.state.pending_item_application_indices, ())
            self.assertEqual(
                recovered.state.received_item_journal[0].state,
                ReceivedItemState.APPLIED,
            )
            recovered.close(clean=True)

    def test_native_change_without_durable_observation_retries_already_correct(
        self,
    ) -> None:
        descriptor = NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
        with TemporaryDirectory() as directory:
            repository = StateRepository(Path(directory))
            session = repository.open(descriptor)
            session.commit(
                apply_received_items_packet(
                    session.state, packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
                ).state,
                category="received_items",
            )
            protocol = NativeMaskProtocol()
            failing_session = FailingAppliedCommitSession(session)
            failed_context = reconciliation_context(failing_session, protocol)

            asyncio.run(
                failed_context._reconcile_permanent_items(failing_session)  # type: ignore[arg-type]
            )

            self.assertEqual(protocol.results, [ProtocolResult.APPLIED])
            self.assertEqual(protocol.apply_count, 1)
            self.assertEqual(protocol.target_mask, JETBOARD_TARGET_BIT)
            self.assertEqual(session.state.pending_item_application_indices, (0,))
            failed_context.mark_bridge_unavailable.assert_awaited_once()
            session.close(clean=False)

            recovered = repository.open(descriptor)
            revision_before_retry = recovered.state.state_revision
            recovered_context = reconciliation_context(recovered, protocol)

            asyncio.run(recovered_context._reconcile_permanent_items(recovered))

            self.assertEqual(
                protocol.results,
                [ProtocolResult.APPLIED, ProtocolResult.ALREADY_APPLIED],
            )
            self.assertEqual(protocol.apply_count, 1)
            self.assertEqual(recovered.state.pending_item_application_indices, ())
            self.assertEqual(
                recovered.state.received_item_journal[0].state,
                ReceivedItemState.APPLIED,
            )
            self.assertEqual(
                recovered.state.state_revision,
                revision_before_retry + 1,
            )
            self.assertEqual(
                recovered.state.last_observed_game_command_receipt,
                GameCommandReceipt(
                    "crash-window-session:1",
                    "RECONCILE_PERMANENT_ITEMS",
                    "ALREADY_APPLIED",
                ),
            )
            recovered.close(clean=True)

    def test_all_permanent_item_unsafe_states_queue_without_dispatch(self) -> None:
        descriptor = NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
        unsafe_states = (
            {"in_cutscene": True},
            {"dying_or_dead": True, "mission_restarting": True},
            {"in_vehicle": True},
            {"loading": True},
            {"level_transition": True},
        )
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor)
            session.commit(
                apply_received_items_packet(
                    session.state, packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
                ).state,
                category="received_items",
            )
            for fields in unsafe_states:
                with self.subTest(fields=fields):
                    context = object.__new__(Jak3Context)
                    context.diagnostics = SimpleNamespace(
                        emit=lambda *_args, **_kw: None
                    )
                    context.state_session = session
                    context.protocol = SimpleNamespace(
                        last_snapshot=BridgeSnapshot(
                            session_nonce="unsafe-session",
                            native_save_slot=0,
                            native_save_identity=SAVE_ID,
                            save_loaded=True,
                            safe_to_apply_permanent_item=False,
                            **fields,
                        ),
                        next_command_id=1,
                        send_command=AsyncMock(),
                    )
                    context._ensure_item_runtime()
                    context._item_reconcile_dirty = True

                    asyncio.run(context._reconcile_permanent_items(session))

                    context.protocol.send_command.assert_not_awaited()
                    self.assertEqual(
                        session.state.pending_item_application_indices, (0,)
                    )
            session.close(clean=True)

    def test_safe_dispatch_marks_pending_only_after_successful_result(self) -> None:
        descriptor = NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor)
            session.commit(
                apply_received_items_packet(
                    session.state,
                    packet(
                        0,
                        (JETBOARD_ITEM_ID, 1, 1, 0),
                        (BLASTER_ITEM_ID, 2, 1, 0),
                    ),
                ).state,
                category="received_items",
            )
            snapshot = BridgeSnapshot(
                session_nonce="safe-session",
                native_save_slot=0,
                native_save_identity=SAVE_ID,
                save_loaded=True,
                safe_to_apply_permanent_item=True,
            )
            result_snapshot = replace(
                snapshot,
                snapshot_revision=2,
                last_command_id=7,
                last_command_kind=ProtocolCommand.RECONCILE_PERMANENT_ITEMS,
                last_command_result=ProtocolResult.APPLIED,
                last_error_code=ProtocolError.NONE,
            )
            send_command = AsyncMock(return_value=result_snapshot)
            context = object.__new__(Jak3Context)
            context.diagnostics = SimpleNamespace(emit=lambda *_args, **_kw: None)
            context.state_session = session
            context.protocol = SimpleNamespace(
                last_snapshot=snapshot,
                next_command_id=7,
                send_command=send_command,
            )
            context._ensure_item_runtime()
            context._item_reconcile_dirty = True

            asyncio.run(context._reconcile_permanent_items(session))

            send_command.assert_awaited_once_with(
                ProtocolCommand.RECONCILE_PERMANENT_ITEMS,
                JETBOARD_TARGET_BIT | BLASTER_TARGET_BIT,
            )
            self.assertEqual(session.state.pending_item_application_indices, ())
            self.assertTrue(
                all(
                    entry.state is ReceivedItemState.APPLIED
                    for entry in session.state.received_item_journal
                )
            )
            self.assertEqual(
                session.state.last_observed_game_command_receipt,
                GameCommandReceipt(
                    "safe-session:7", "RECONCILE_PERMANENT_ITEMS", "APPLIED"
                ),
            )
            session.close(clean=True)

    def test_same_descriptor_native_load_reconciles_even_when_safety_stays_true(
        self,
    ) -> None:
        descriptor = NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor)
            received = apply_received_items_packet(
                session.state, packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
            ).state
            session.commit(
                mark_pending_items_applied(
                    received,
                    GameCommandReceipt(
                        "earlier-session:1",
                        "RECONCILE_PERMANENT_ITEMS",
                        "APPLIED",
                    ),
                ),
                category="permanent_items_applied",
            )
            protocol = NativeMaskProtocol(target_mask=JETBOARD_TARGET_BIT)
            context = reconciliation_context(session, protocol)

            async def scenario() -> None:
                context._note_permanent_item_runtime(protocol.last_snapshot)
                await context._item_worker_task
                self.assertEqual(protocol.results, [ProtocolResult.ALREADY_APPLIED])

                # The native load starts and finishes between heartbeat snapshots:
                # descriptor and safety are unchanged, but the loaded save loses the
                # AP-owned feature. GOAL's durable diagnostic sequence is the load
                # boundary that must invalidate the confirmed native projection.
                protocol.target_mask = 0
                loaded_snapshot = replace(
                    protocol.last_snapshot,
                    snapshot_revision=protocol.last_snapshot.snapshot_revision + 1,
                    diagnostic_activation_generation=4,
                    diagnostic_next_sequence=13,
                    diagnostic_events=(
                        GoalDiagnosticRecord(
                            12,
                            100,
                            1,
                            211,
                            1,
                            0,
                            1,
                            0,
                            2,
                            0,
                            0,
                        ),
                    ),
                )
                protocol.last_snapshot = loaded_snapshot

                context._note_permanent_item_runtime(loaded_snapshot)
                await context._item_worker_task

                self.assertEqual(
                    protocol.results,
                    [ProtocolResult.ALREADY_APPLIED, ProtocolResult.APPLIED],
                )
                self.assertEqual(protocol.target_mask, JETBOARD_TARGET_BIT)

                # A delayed diagnostic acknowledgement can expose the same record
                # again; its generation/sequence pair must not send another command.
                context._note_permanent_item_runtime(loaded_snapshot)
                await context._item_worker_task
                self.assertEqual(len(protocol.results), 2)

            asyncio.run(scenario())
            session.close(clean=True)

    def test_diagnostic_overflow_reconciles_when_load_record_was_evicted(
        self,
    ) -> None:
        descriptor = NativeSaveDescriptor(
            slot=0,
            identity=SAVE_ID,
            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
        )
        with TemporaryDirectory() as directory:
            session = StateRepository(Path(directory)).open(descriptor)
            received = apply_received_items_packet(
                session.state, packet(0, (JETBOARD_ITEM_ID, 1, 1, 0))
            ).state
            session.commit(
                mark_pending_items_applied(
                    received,
                    GameCommandReceipt(
                        "earlier-session:1",
                        "RECONCILE_PERMANENT_ITEMS",
                        "APPLIED",
                    ),
                ),
                category="permanent_items_applied",
            )
            protocol = NativeMaskProtocol(target_mask=JETBOARD_TARGET_BIT)
            protocol.last_snapshot = replace(
                protocol.last_snapshot,
                diagnostic_activation_generation=4,
                diagnostic_dropped_count=0,
                diagnostic_next_sequence=12,
            )
            context = reconciliation_context(session, protocol)

            async def scenario() -> None:
                context._note_permanent_item_runtime(protocol.last_snapshot)
                await context._item_worker_task
                self.assertEqual(protocol.results, [ProtocolResult.ALREADY_APPLIED])

                # The bounded GOAL ring evicted the load-success record before the
                # next heartbeat. Its increased dropped counter must conservatively
                # invalidate the confirmed native projection.
                protocol.target_mask = 0
                overflow_snapshot = replace(
                    protocol.last_snapshot,
                    snapshot_revision=protocol.last_snapshot.snapshot_revision + 1,
                    diagnostic_dropped_count=1,
                    diagnostic_next_sequence=77,
                    diagnostic_events=(),
                )
                protocol.last_snapshot = overflow_snapshot

                context._note_permanent_item_runtime(overflow_snapshot)
                await context._item_worker_task

                self.assertEqual(
                    protocol.results,
                    [ProtocolResult.ALREADY_APPLIED, ProtocolResult.APPLIED],
                )
                self.assertEqual(protocol.target_mask, JETBOARD_TARGET_BIT)

                context._note_permanent_item_runtime(overflow_snapshot)
                await context._item_worker_task
                self.assertEqual(len(protocol.results), 2)

            asyncio.run(scenario())
            session.close(clean=True)


if __name__ == "__main__":
    unittest.main()
