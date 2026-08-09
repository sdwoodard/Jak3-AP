import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from worlds.jak3.canonical import canonical_json_bytes
from worlds.jak3.option_resolution import SUPPORTED_FIRST_RELEASE_OPTIONS
from worlds.jak3.persistence import (
    AuthenticatedSlot,
    NativeSaveDescriptor,
    NativeSaveEligibility,
    PERSISTENT_STATE_KEYS,
    PersistentState,
    ReceivedItemJournalEntry,
    ReceivedItemState,
    StateBindingError,
    StateCompatibilityError,
    StateCorruptionError,
    StateEligibilityError,
    StateOpenStatus,
    StateRepository,
    StateWriterLockedError,
    StaleStateRevisionError,
    default_state_root,
    deserialize_state,
    serialize_state,
)
from worlds.jak3.registry import (
    FIRST_RELEASE_ITEMS,
    FIRST_RELEASE_LOCATIONS,
    ITEM_TABLE_HASH,
    LOCATION_TABLE_HASH,
    MISSION_TABLE_HASH,
)
from worlds.jak3.slot_data import build_slot_data
from worlds.jak3.versions import GAME_INTEGRATION_VERSION, PROTOCOL_VERSION


STATE_ID = "00000000-0000-4000-8000-000000000006"
AUTHORIZED_SAVE_ID = "00000000-0000-4000-8000-000000000007"


def native_save(
    identity: str = "native-save-alpha",
    *,
    slot: int = 0,
    fresh: bool = True,
) -> NativeSaveDescriptor:
    return NativeSaveDescriptor(
        slot=slot,
        identity=identity,
        eligibility=(
            NativeSaveEligibility.FRESH_UNPROGRESSED
            if fresh
            else NativeSaveEligibility.INELIGIBLE
        ),
    )


def authenticated_slot(
    seed: str = "AP_M6_SEED",
    *,
    team: int = 0,
    slot: int = 1,
    name: str = "Jak",
) -> AuthenticatedSlot:
    contract = build_slot_data(
        SUPPORTED_FIRST_RELEASE_OPTIONS,
        seed_identifier=seed,
    )
    return AuthenticatedSlot.from_connected_packet(
        contract,
        team=team,
        slot=slot,
        slot_name=name,
    )


def rewrite_payload(path: Path, **changes: object) -> bytes:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"].update(changes)
    envelope["payload_sha256"] = hashlib.sha256(
        canonical_json_bytes(envelope["payload"])
    ).hexdigest()
    data = canonical_json_bytes(envelope)
    path.write_bytes(data)
    return data


def encode_payload(payload: dict[str, object]) -> bytes:
    return canonical_json_bytes(
        {
            "format": "jak3-ap-state",
            "checksum_algorithm": "sha256",
            "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
            "payload": payload,
        }
    )


class PersistentStateSchemaTest(unittest.TestCase):
    def test_new_state_contains_the_complete_schema_and_checksum(self) -> None:
        persistent = PersistentState.create_unbound(
            native_save(), state_instance_id=STATE_ID
        )
        payload = persistent.to_payload()
        self.assertEqual(PERSISTENT_STATE_KEYS, set(payload))
        self.assertFalse(persistent.is_bound)
        self.assertEqual(0, persistent.next_received_item_index)
        self.assertEqual((), persistent.received_item_journal)
        self.assertEqual((), persistent.received_item_counts)
        self.assertEqual((), persistent.pending_item_application_indices)
        self.assertIsNone(persistent.last_observed_game_command_receipt)
        self.assertEqual((), persistent.checked_location_bits)
        self.assertEqual((), persistent.server_confirmed_location_bits)
        self.assertEqual((), persistent.pending_location_outbox)
        self.assertEqual(0, persistent.local_earned_precursor_orbs)
        self.assertEqual(0, persistent.local_earned_skull_gems)
        self.assertIsNone(persistent.active_bootstrap_overlay)
        self.assertIsNone(persistent.active_shadow_story_state)
        self.assertEqual((), persistent.pending_traps)
        self.assertFalse(persistent.goal_completed)
        self.assertFalse(persistent.goal_status_sent)

        encoded = serialize_state(persistent)
        envelope = json.loads(encoded)
        self.assertEqual(
            hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
            envelope["payload_sha256"],
        )
        self.assertEqual(persistent, deserialize_state(encoded))

    def test_all_received_item_journal_states_round_trip_by_explicit_index(
        self,
    ) -> None:
        item_id = FIRST_RELEASE_ITEMS[0].code
        for application_state in ReceivedItemState:
            with self.subTest(application_state=application_state):
                persistent = PersistentState.create_unbound(
                    native_save(), state_instance_id=STATE_ID
                )
                entry = ReceivedItemJournalEntry(
                    index=0,
                    item_id=item_id,
                    location_id=-1,
                    source_player=1,
                    flags=0,
                    state=application_state,
                )
                changed = replace(
                    persistent,
                    next_received_item_index=1,
                    received_item_journal=(entry,),
                    received_item_counts=((item_id, 1),),
                    pending_item_application_indices=(
                        (0,) if application_state is ReceivedItemState.PENDING else ()
                    ),
                )
                self.assertEqual(changed, deserialize_state(serialize_state(changed)))

    def test_location_sets_store_sorted_explicit_registry_ids(self) -> None:
        persistent = PersistentState.create_unbound(
            native_save(), state_instance_id=STATE_ID
        )
        location_ids = tuple(
            sorted(record.code for record in FIRST_RELEASE_LOCATIONS[:3])
        )
        changed = replace(
            persistent,
            checked_location_bits=location_ids,
            server_confirmed_location_bits=location_ids[:1],
            pending_location_outbox=location_ids[1:],
        )
        decoded = deserialize_state(serialize_state(changed))
        self.assertEqual(location_ids, decoded.checked_location_bits)
        self.assertGreater(location_ids[0], 3)

    def test_unknown_fields_and_invalid_relationships_are_rejected(self) -> None:
        persistent = PersistentState.create_unbound(
            native_save(), state_instance_id=STATE_ID
        )
        location_id = FIRST_RELEASE_LOCATIONS[0].code
        invalid_payloads = []

        unknown = persistent.to_payload()
        unknown["unexpected_field"] = True
        invalid_payloads.append(unknown)

        impossible_goal = persistent.to_payload()
        impossible_goal["goal_status_sent"] = True
        invalid_payloads.append(impossible_goal)

        impossible_outbox = persistent.to_payload()
        impossible_outbox["pending_location_outbox"] = [location_id]
        invalid_payloads.append(impossible_outbox)

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(StateCorruptionError):
                    deserialize_state(encode_payload(payload))

    def test_deferred_state_containers_require_round_trip_safe_shapes(self) -> None:
        persistent = PersistentState.create_unbound(
            native_save(), state_instance_id=STATE_ID
        )
        invalid_changes = (
            {"active_bootstrap_overlay": []},
            {"active_shadow_story_state": []},
            {"active_bootstrap_overlay": {"nested": ("not", "normalized")}},
            {"active_shadow_story_state": {"float": 1.5}},
            {"pending_traps": []},
            {"pending_traps": ("not-an-object",)},
        )

        for changes in invalid_changes:
            with self.subTest(changes=changes):
                with self.assertRaises(StateCorruptionError):
                    replace(persistent, **changes)

    def test_integer_contract_versions_reject_booleans_before_serialization(
        self,
    ) -> None:
        persistent = PersistentState.create_unbound(
            native_save(), state_instance_id=STATE_ID
        )

        for field_name in (
            "state_schema_version",
            "protocol_version",
            "game_integration_version",
            "slot_data_version",
            "game_application_journal_version",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(StateCorruptionError):
                    replace(persistent, **{field_name: True})

    def test_received_item_journal_requires_tuple_records_and_integer_indices(
        self,
    ) -> None:
        persistent = PersistentState.create_unbound(
            native_save(), state_instance_id=STATE_ID
        )
        item_id = FIRST_RELEASE_ITEMS[0].code
        valid_entry = ReceivedItemJournalEntry(
            index=0,
            item_id=item_id,
            location_id=-1,
            source_player=1,
            flags=0,
            state=ReceivedItemState.RECEIVED,
        )

        invalid_changes = (
            {"received_item_journal": []},
            {
                "next_received_item_index": 1,
                "received_item_journal": ({"index": 0},),
                "received_item_counts": ((item_id, 1),),
            },
            {
                "next_received_item_index": 1,
                "received_item_journal": (replace(valid_entry, index=False),),
                "received_item_counts": ((item_id, 1),),
            },
            {"received_item_counts": ((float(item_id), 0),)},
            {"received_item_counts": ((item_id,),)},
        )
        for changes in invalid_changes:
            with self.subTest(changes=changes):
                with self.assertRaises(StateCorruptionError):
                    replace(persistent, **changes)

    def test_authenticated_slot_constructor_rejects_seed_contract_mismatch(
        self,
    ) -> None:
        contract = build_slot_data(
            SUPPORTED_FIRST_RELEASE_OPTIONS,
            seed_identifier="contract-seed",
        )
        with self.assertRaisesRegex(StateCompatibilityError, "seed identifier"):
            AuthenticatedSlot(
                seed_identifier="different-seed",
                team=0,
                slot=1,
                slot_name="Jak",
                contract=contract,
            )

    def test_default_root_is_outside_the_workspace_reference_trees(self) -> None:
        old_override = os.environ.pop("JAK3_AP_STATE_DIR", None)
        try:
            root = default_state_root()
        finally:
            if old_override is not None:
                os.environ["JAK3_AP_STATE_DIR"] = old_override
        workspace = Path(__file__).resolve().parents[2]
        for reference in ("jak-project", "Archipelago", "openGOAL-decompile"):
            with self.subTest(reference=reference):
                self.assertFalse(root.is_relative_to(workspace / reference))

    def test_environment_override_selects_the_state_root(self) -> None:
        override = Path(tempfile.gettempdir()) / "jak3-ap-state-override"
        old_override = os.environ.get("JAK3_AP_STATE_DIR")
        os.environ["JAK3_AP_STATE_DIR"] = str(override)
        try:
            self.assertEqual(override.resolve(), default_state_root())
        finally:
            if old_override is None:
                os.environ.pop("JAK3_AP_STATE_DIR", None)
            else:
                os.environ["JAK3_AP_STATE_DIR"] = old_override


class PersistentStateRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "state"
        self.repository = StateRepository(
            self.root,
            state_id_factory=lambda: STATE_ID,
        )
        self.native = native_save()
        self.auth = authenticated_slot()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_new_state_creation_and_clean_reload(self) -> None:
        session = self.repository.open(self.native)
        self.assertEqual(StateOpenStatus.CREATED, session.status)
        self.assertFalse(session.state.is_bound)
        self.assertFalse(session.state.last_clean_shutdown)
        primary = session.paths.primary
        self.assertTrue(primary.is_file())
        session.close(clean=True)

        inspected = self.repository.inspect(native_save(fresh=False))
        self.assertTrue(inspected.state.last_clean_shutdown)
        self.assertEqual(STATE_ID, inspected.state.state_instance_id)

    def test_opaque_native_identity_selects_a_sha256_sidecar_filename(self) -> None:
        paths = self.repository.paths_for(self.native.identity)
        expected = hashlib.sha256(self.native.identity.encode("utf-8")).hexdigest()
        self.assertEqual(f"{expected}.json", paths.primary.name)
        self.assertEqual(f"{expected}.json.bak", paths.backup.name)

    def test_missing_state_rejects_a_progressed_or_unverified_save(self) -> None:
        with self.assertRaisesRegex(StateEligibilityError, "fresh"):
            self.repository.open(native_save(fresh=False))
        self.assertFalse(
            self.repository.paths_for(self.native.identity).primary.exists()
        )

    def test_live_first_binding_requires_matching_durable_authorization(self) -> None:
        native = native_save(identity=AUTHORIZED_SAVE_ID)
        primary = self.repository.paths_for(native.identity).primary
        with self.assertRaisesRegex(StateBindingError, "no durable"):
            self.repository.open_live(native, self.auth)
        self.assertFalse(primary.exists())

        self.repository.authorize_save_identity(native.identity, self.auth)
        authorization_path = self.repository.save_identity_authorization_path_for(
            native.identity
        )
        self.assertTrue(authorization_path.is_file())
        with self.assertRaisesRegex(StateBindingError, "different AP"):
            self.repository.open_live(native, authenticated_slot(seed="DIFFERENT_SEED"))
        self.assertFalse(primary.exists())

        with self.repository.open_live(native, self.auth) as session:
            self.assertTrue(session.binding_performed)
            self.assertTrue(session.state.is_bound)

    def test_live_unbound_crash_state_keeps_proposal_slot_provenance(self) -> None:
        native = native_save(identity=AUTHORIZED_SAVE_ID)
        self.repository.authorize_save_identity(native.identity, self.auth)
        unbound = self.repository.open(native)
        unbound.close(clean=False)
        original = self.repository.paths_for(native.identity).primary.read_bytes()

        with self.assertRaisesRegex(StateBindingError, "different AP"):
            self.repository.open_live(
                native_save(identity=native.identity, fresh=False),
                authenticated_slot(team=1),
            )
        self.assertEqual(
            original, self.repository.paths_for(native.identity).primary.read_bytes()
        )

        with self.repository.open_live(
            native_save(identity=native.identity, fresh=False), self.auth
        ) as recovered:
            self.assertTrue(recovered.binding_performed)
            self.assertTrue(recovered.state.is_bound)

    def test_live_unbound_backup_checks_provenance_before_restore(self) -> None:
        native = native_save(identity=AUTHORIZED_SAVE_ID)
        self.repository.authorize_save_identity(native.identity, self.auth)
        unbound = self.repository.open(native)
        unbound.close(clean=True)
        paths = self.repository.paths_for(native.identity)
        paths.primary.unlink()
        original_backup = paths.backup.read_bytes()

        with self.assertRaisesRegex(StateBindingError, "different AP"):
            self.repository.open_live(
                native_save(identity=native.identity, fresh=False),
                authenticated_slot(name="Another Slot"),
            )
        self.assertFalse(paths.primary.exists())
        self.assertEqual(original_backup, paths.backup.read_bytes())

    def test_save_identity_authorization_is_idempotent_but_not_rebindable(self) -> None:
        self.repository.authorize_save_identity(AUTHORIZED_SAVE_ID, self.auth)
        path = self.repository.save_identity_authorization_path_for(AUTHORIZED_SAVE_ID)
        original = path.read_bytes()
        self.repository.authorize_save_identity(AUTHORIZED_SAVE_ID, self.auth)
        self.assertEqual(original, path.read_bytes())

        with self.assertRaisesRegex(StateBindingError, "different AP"):
            self.repository.authorize_save_identity(
                AUTHORIZED_SAVE_ID, authenticated_slot(slot=2)
            )
        self.assertEqual(original, path.read_bytes())

    def test_bind_reload_and_duplicate_load_preserve_identity(self) -> None:
        with self.repository.open(self.native) as session:
            first_revision = session.state.state_revision
        with self.repository.open(native_save(fresh=False), self.auth) as session:
            self.assertEqual(StateOpenStatus.BOUND, session.status)
            self.assertTrue(session.binding_performed)
            self.assertTrue(session.state.is_bound)
            self.assertGreater(session.state.state_revision, first_revision)
            instance_id = session.state.state_instance_id
        with self.repository.open(native_save(fresh=False), self.auth) as session:
            self.assertEqual(StateOpenStatus.LOADED, session.status)
            self.assertFalse(session.binding_performed)
            self.assertEqual(instance_id, session.state.state_instance_id)

    def test_authenticated_binding_mismatches_are_read_only(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        path = self.repository.paths_for(self.native.identity).primary
        original = path.read_bytes()
        mismatches = (
            authenticated_slot(seed="OTHER_SEED"),
            authenticated_slot(team=1),
            authenticated_slot(slot=2),
            authenticated_slot(name="Other Jak"),
        )
        for mismatch in mismatches:
            with self.subTest(mismatch=mismatch):
                with self.assertRaises(StateBindingError) as rejection:
                    self.repository.open(native_save(fresh=False), mismatch)
                rendered = str(rejection.exception)
                for identity in ("AP_M6_SEED", "OTHER_SEED", "Other Jak"):
                    self.assertNotIn(identity, rendered)
                self.assertEqual(original, path.read_bytes())
                self.assertEqual([], list(self.root.glob("*.corrupt.*")))

    def test_native_slot_copy_is_rejected_without_rewriting(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        path = self.repository.paths_for(self.native.identity).primary
        original = path.read_bytes()
        copied = native_save(identity=self.native.identity, slot=1, fresh=False)
        with self.assertRaisesRegex(StateBindingError, "slot"):
            self.repository.open(copied, self.auth)
        self.assertEqual(original, path.read_bytes())

    def test_wrong_native_identity_cannot_create_state(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        with self.assertRaises(StateEligibilityError):
            self.repository.open(
                native_save(identity="different-save", fresh=False), self.auth
            )

    def test_binding_can_only_change_through_one_time_bind(self) -> None:
        session = self.repository.open(self.native)
        forged = replace(
            session.state,
            seed_identifier=self.auth.seed_identifier,
            team=self.auth.team,
            slot=self.auth.slot,
            slot_name=self.auth.slot_name,
        )
        with self.assertRaises(StateBindingError):
            session.commit(forged)
        session.bind(self.auth)
        with self.assertRaises(StateBindingError):
            session.bind(authenticated_slot(seed="ANOTHER_SEED"))
        session.close()

    def test_save_slot_switch_closes_the_old_state_and_selects_another(self) -> None:
        first = self.repository.open(self.native, self.auth)
        first_path = first.paths.primary
        second_native = native_save(identity="native-save-beta", slot=1)
        second = first.switch(second_native, self.auth)
        try:
            self.assertNotEqual(first_path, second.paths.primary)
            self.assertEqual(1, second.state.native_save_slot)
            self.assertTrue(
                self.repository.inspect(
                    native_save(fresh=False)
                ).state.last_clean_shutdown
            )
        finally:
            second.close()

    def test_unclean_restart_is_recorded_and_recoverable(self) -> None:
        session = self.repository.open(self.native, self.auth)
        session.close(clean=False)
        self.assertFalse(
            self.repository.inspect(
                native_save(fresh=False), self.auth
            ).state.last_clean_shutdown
        )
        with self.repository.open(native_save(fresh=False), self.auth):
            pass
        self.assertTrue(
            self.repository.inspect(
                native_save(fresh=False), self.auth
            ).state.last_clean_shutdown
        )

    def test_stale_revision_is_rejected(self) -> None:
        session = self.repository.open(self.native)
        stale = replace(
            session.state,
            state_revision=session.state.state_revision + 1,
        )
        with self.assertRaises(StaleStateRevisionError):
            session.commit(stale)
        session.close()

    def test_missing_primary_during_a_session_is_a_stale_write(self) -> None:
        session = self.repository.open(self.native)
        session.paths.primary.unlink()
        with self.assertRaisesRegex(StaleStateRevisionError, "disappeared"):
            session.commit(session.state)
        session.close(clean=False)

    def test_second_writer_is_rejected(self) -> None:
        session = self.repository.open(self.native)
        try:
            other = StateRepository(self.root)
            with self.assertRaises(StateWriterLockedError):
                other.open(native_save(identity="other-save"))
            self.assertEqual(self.repository.inspect(self.native).state, session.state)
        finally:
            session.close()

    def test_operating_system_lock_rejects_a_second_process(self) -> None:
        session = self.repository.open(self.native)
        script = "\n".join(
            (
                "import sys",
                "from pathlib import Path",
                "from worlds.jak3.persistence import (",
                "    NativeSaveDescriptor, NativeSaveEligibility, StateRepository,",
                "    StateWriterLockedError,",
                ")",
                "try:",
                "    StateRepository(Path(sys.argv[1])).open(",
                "        NativeSaveDescriptor(",
                "            slot=0, identity='child-save',",
                "            eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,",
                "        )",
                "    )",
                "except StateWriterLockedError:",
                "    raise SystemExit(0)",
                "raise SystemExit(9)",
            )
        )
        try:
            result = subprocess.run(
                [sys.executable, "-c", script, str(self.root)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
                env=os.environ.copy(),
            )
            self.assertEqual(0, result.returncode, result.stderr)
        finally:
            session.close()

    def test_missing_primary_recovers_from_retained_backup(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        paths = self.repository.paths_for(self.native.identity)
        self.assertTrue(paths.backup.is_file())
        paths.primary.unlink()
        session = self.repository.open(native_save(fresh=False), self.auth)
        try:
            self.assertEqual(StateOpenStatus.RECOVERED_BACKUP, session.status)
            self.assertTrue(paths.primary.is_file())
            self.assertTrue(paths.backup.is_file())
        finally:
            session.close()

    def test_corrupt_primary_is_quarantined_and_backup_recovers(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        paths = self.repository.paths_for(self.native.identity)
        paths.primary.write_bytes(b'{"truncated":')
        session = self.repository.open(native_save(fresh=False), self.auth)
        try:
            self.assertEqual(StateOpenStatus.RECOVERED_BACKUP, session.status)
            self.assertTrue(paths.primary.is_file())
            self.assertTrue(paths.backup.is_file())
            self.assertEqual(
                1, len(list(self.root.glob(f"{paths.primary.name}.corrupt.*")))
            )
        finally:
            session.close()

    def test_recoverable_primary_corruption_emits_detection_before_recovery(
        self,
    ) -> None:
        events: list[str] = []

        def collect(event_name: str, **fields: object) -> None:
            events.append(event_name)

        repository = StateRepository(
            self.root,
            state_id_factory=lambda: "00000000-0000-4000-8000-000000000090",
            event_sink=collect,
        )
        with repository.open(self.native, self.auth):
            pass
        paths = repository.paths_for(self.native.identity)
        paths.primary.write_bytes(b'{"truncated":')
        events.clear()

        with repository.open(native_save(fresh=False), self.auth) as session:
            self.assertEqual(StateOpenStatus.RECOVERED_BACKUP, session.status)

        self.assertEqual(events.count("persistence.corruption.detected"), 1)
        self.assertLess(
            events.index("persistence.corruption.detected"),
            events.index("persistence.quarantine.performed"),
        )
        self.assertLess(
            events.index("persistence.quarantine.performed"),
            events.index("persistence.backup.restored"),
        )

    def test_noncanonical_payload_recovers_and_quarantines_instead_of_leaking_type_error(
        self,
    ) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        paths = self.repository.paths_for(self.native.identity)
        envelope = json.loads(paths.primary.read_text(encoding="utf-8"))
        envelope["payload"]["active_bootstrap_overlay"] = {"invalid": 1.5}
        paths.primary.write_text(json.dumps(envelope), encoding="utf-8")

        with self.repository.open(native_save(fresh=False), self.auth) as session:
            self.assertEqual(StateOpenStatus.RECOVERED_BACKUP, session.status)
            self.assertIsNone(session.state.active_bootstrap_overlay)

        quarantined = list(self.root.glob(f"{paths.primary.name}.corrupt.*"))
        self.assertEqual(1, len(quarantined))
        self.assertIn(b'"invalid": 1.5', quarantined[0].read_bytes())

    def test_recovery_status_is_preserved_when_recovered_state_is_then_bound(
        self,
    ) -> None:
        with self.repository.open(self.native):
            pass
        paths = self.repository.paths_for(self.native.identity)
        paths.primary.write_bytes(b"{")

        with self.repository.open(native_save(fresh=False), self.auth) as session:
            self.assertEqual(StateOpenStatus.RECOVERED_BACKUP, session.status)
            self.assertTrue(session.binding_performed)
            self.assertTrue(session.state.is_bound)

        self.assertEqual(
            1, len(list(self.root.glob(f"{paths.primary.name}.corrupt.*")))
        )

    def test_empty_corrupt_state_without_backup_is_quarantined_and_not_recreated(
        self,
    ) -> None:
        paths = self.repository.paths_for(self.native.identity)
        paths.primary.parent.mkdir(parents=True)
        paths.primary.write_bytes(b"")
        with self.assertRaises(StateCorruptionError):
            self.repository.open(self.native)
        quarantined = list(self.root.glob(f"{paths.primary.name}.corrupt.*"))
        self.assertEqual(1, len(quarantined))
        self.assertEqual(b"", quarantined[0].read_bytes())
        with self.assertRaises(StateCorruptionError):
            self.repository.open(self.native)

    def test_primary_and_backup_corruption_are_both_quarantined(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        paths = self.repository.paths_for(self.native.identity)
        paths.primary.write_bytes(b"{")
        paths.backup.write_bytes(b"[]")
        with self.assertRaisesRegex(StateCorruptionError, "Primary and backup"):
            self.repository.open(native_save(fresh=False), self.auth)
        self.assertFalse(paths.primary.exists())
        self.assertFalse(paths.backup.exists())
        self.assertEqual(2, len(list(self.root.glob("*.corrupt.*"))))

    def test_missing_primary_with_corrupt_backup_quarantines_backup_only(self) -> None:
        paths = self.repository.paths_for(self.native.identity)
        paths.backup.parent.mkdir(parents=True)
        paths.backup.write_bytes(b"not-json")
        with self.assertRaisesRegex(StateCorruptionError, "primary.*missing"):
            self.repository.open(self.native)
        self.assertFalse(paths.primary.exists())
        self.assertFalse(paths.backup.exists())
        quarantined = list(self.root.glob(f"{paths.backup.name}.corrupt.*"))
        self.assertEqual(1, len(quarantined))
        self.assertEqual(b"not-json", quarantined[0].read_bytes())

    def test_checksum_corruption_uses_backup(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        path = self.repository.paths_for(self.native.identity).primary
        envelope = json.loads(path.read_text(encoding="utf-8"))
        envelope["payload"]["goal_completed"] = True
        path.write_bytes(canonical_json_bytes(envelope))
        with self.repository.open(native_save(fresh=False), self.auth) as session:
            self.assertEqual(StateOpenStatus.RECOVERED_BACKUP, session.status)
            self.assertFalse(session.state.goal_completed)

    def test_incompatible_backup_keeps_corrupt_primary_read_only(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        paths = self.repository.paths_for(self.native.identity)
        paths.primary.write_bytes(b"not-json")
        incompatible_backup = rewrite_payload(paths.backup, state_schema_version=2)
        with self.assertRaises(StateCompatibilityError):
            self.repository.open(native_save(fresh=False), self.auth)
        self.assertEqual(b"not-json", paths.primary.read_bytes())
        self.assertEqual(incompatible_backup, paths.backup.read_bytes())
        self.assertEqual([], list(self.root.glob("*.corrupt.*")))

    def test_old_new_and_table_mismatches_are_preserved_read_only(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        path = self.repository.paths_for(self.native.identity).primary
        for changes, error in (
            ({"state_schema_version": 0}, StateCompatibilityError),
            ({"state_schema_version": 2}, StateCompatibilityError),
            ({"protocol_version": 2}, StateCompatibilityError),
            ({"protocol_version": 999}, StateCompatibilityError),
            ({"game_integration_version": 999}, StateCompatibilityError),
            ({"slot_data_version": 999}, StateCompatibilityError),
            ({"item_table_hash": "0" * 64}, StateCompatibilityError),
            ({"location_table_hash": "0" * 64}, StateCompatibilityError),
            ({"mission_table_hash": "0" * 64}, StateCompatibilityError),
            ({"resolved_options_hash": "0" * 64}, StateCompatibilityError),
            ({"design_version": "unsupported"}, StateCompatibilityError),
        ):
            with self.subTest(changes=changes):
                original = rewrite_payload(path, **changes)
                with self.assertRaises(error):
                    self.repository.open(native_save(fresh=False), self.auth)
                self.assertEqual(original, path.read_bytes())
                self.assertEqual([], list(self.root.glob("*.corrupt.*")))
                rewrite_payload(
                    path,
                    state_schema_version=1,
                    protocol_version=PROTOCOL_VERSION,
                    game_integration_version=GAME_INTEGRATION_VERSION,
                    slot_data_version=2,
                    item_table_hash=ITEM_TABLE_HASH,
                    location_table_hash=LOCATION_TABLE_HASH,
                    mission_table_hash=MISSION_TABLE_HASH,
                    resolved_options_hash=self.auth.contract["resolved_options_hash"],
                    design_version=self.auth.contract["design_version"],
                )

    def test_unsupported_location_id_is_preserved_as_read_only_failure(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        path = self.repository.paths_for(self.native.identity).primary
        original = rewrite_payload(path, checked_location_bits=[999_999_999])
        with self.assertRaises(StateCompatibilityError):
            self.repository.open(native_save(fresh=False), self.auth)
        self.assertEqual(original, path.read_bytes())
        self.assertEqual([], list(self.root.glob("*.corrupt.*")))

    def test_read_only_inspection_never_recovers_or_quarantines(self) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        paths = self.repository.paths_for(self.native.identity)
        paths.primary.write_bytes(b"not-json")
        backup = paths.backup.read_bytes()
        with self.assertRaises(StateCorruptionError):
            self.repository.inspect(native_save(fresh=False), self.auth)
        self.assertEqual(b"not-json", paths.primary.read_bytes())
        self.assertEqual(backup, paths.backup.read_bytes())
        self.assertEqual([], list(self.root.glob("*.corrupt.*")))

    def test_interrupted_write_leaves_the_previous_primary_and_quarantines_temp(
        self,
    ) -> None:
        with self.repository.open(self.native, self.auth):
            pass
        paths = self.repository.paths_for(self.native.identity)
        original = paths.primary.read_bytes()

        def fail_after_temp(stage: str) -> None:
            if stage == "after_temp_sync":
                raise OSError("simulated interruption")

        interrupted = StateRepository(self.root, fault_injector=fail_after_temp)
        with self.assertRaisesRegex(OSError, "simulated interruption"):
            interrupted.open(native_save(fresh=False), self.auth)
        self.assertEqual(original, paths.primary.read_bytes())
        self.assertEqual(1, len(list(self.root.glob(f".{paths.primary.name}.*.tmp"))))

        with self.repository.open(native_save(fresh=False), self.auth):
            pass
        self.assertEqual([], list(self.root.glob(f".{paths.primary.name}.*.tmp")))
        self.assertEqual(1, len(list(self.root.glob("*.interrupted.*"))))

    def test_diagnostic_sink_failure_cannot_change_persistence_results(self) -> None:
        calls: list[str] = []

        class SyntheticDiagnosticFailure(BaseException):
            pass

        def failing_sink(event_name: str, **fields: object) -> None:
            calls.append(event_name)
            raise SyntheticDiagnosticFailure("synthetic diagnostics failure")

        repository = StateRepository(
            self.root,
            state_id_factory=lambda: "00000000-0000-4000-8000-000000000088",
            event_sink=failing_sink,
        )
        with repository.open(self.native, self.auth) as session:
            before = session.state.state_revision
            committed = session.commit(
                replace(session.state, local_earned_precursor_orbs=1)
            )
            self.assertEqual(committed.state_revision, before + 1)
            self.assertEqual(committed.local_earned_precursor_orbs, 1)
        inspected = repository.inspect(native_save(fresh=False), self.auth)
        self.assertEqual(inspected.state.local_earned_precursor_orbs, 1)
        self.assertTrue(calls)

    def test_persistence_lifecycle_emits_revisioned_registered_events(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []

        def collect(event_name: str, **fields: object) -> None:
            events.append((event_name, fields))

        repository = StateRepository(
            self.root,
            state_id_factory=lambda: "00000000-0000-4000-8000-000000000089",
            event_sink=collect,
        )
        with repository.open(self.native, self.auth) as session:
            session.commit(replace(session.state, local_earned_precursor_orbs=1))
        names = [name for name, _fields in events]
        for required in (
            "persistence.writer_lock.acquired",
            "persistence.path.selected",
            "persistence.state.created",
            "persistence.state.bound",
            "persistence.commit.attempted",
            "persistence.commit.succeeded",
            "persistence.backup.refreshed",
            "persistence.shutdown.clean",
            "persistence.writer_lock.released",
        ):
            self.assertIn(required, names)
        revisions = [
            fields["persistent_state_revision"]
            for name, fields in events
            if name == "persistence.commit.succeeded"
        ]
        self.assertEqual(revisions, sorted(revisions))
        succeeded = [
            fields for name, fields in events if name == "persistence.commit.succeeded"
        ]
        self.assertEqual(
            [fields["context"]["category"] for fields in succeeded],
            ["binding+session_open", "state_update", "clean_shutdown"],
        )
        self.assertTrue(
            all(
                fields["context"]["new_revision"]
                == fields["context"]["old_revision"] + 1
                for fields in succeeded
            )
        )
        backup_revisions = [
            fields["persistent_state_revision"]
            for name, fields in events
            if name == "persistence.backup.refreshed"
        ]
        self.assertEqual(
            backup_revisions,
            [fields["context"]["old_revision"] for fields in succeeded],
        )


if __name__ == "__main__":
    unittest.main()
