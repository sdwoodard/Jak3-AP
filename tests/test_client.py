import asyncio
import unittest

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from CommonClient import CommonContext

from worlds.jak3.agents.diagnostics import BundleExportResult
from worlds.jak3.agents.protocol import (
    BridgeSnapshot,
    CommandReceipt,
    NativeSaveEligibility as SnapshotSaveEligibility,
    ProtocolCommand,
    ProtocolError,
    ProtocolResult,
    ProtocolVersionMismatch,
)
from worlds.jak3.client import (
    BACKGROUND_TASKS,
    Jak3CommandProcessor,
    Jak3Context,
    _goal_path_literal,
    _goal_string_literal,
    _loaded_bridge_matches_current_contract,
    _loaded_diagnostics_matches_current_contract,
)
from worlds.jak3.option_resolution import SUPPORTED_FIRST_RELEASE_OPTIONS
from worlds.jak3.persistence import (
    AuthenticatedSlot,
    NativeSaveDescriptor,
    NativeSaveEligibility,
    StateError,
    StateRepository,
)
from worlds.jak3.slot_data import build_slot_data


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SOURCE = (
    REPOSITORY_ROOT
    / "mod"
    / "opengoal"
    / "goal_src"
    / "jak3"
    / "pc"
    / "features"
    / "archipelago.gc"
)
LIVE_SAVE_ID = "00000000-0000-4000-8000-000000000071"
SWITCHED_SAVE_ID = "00000000-0000-4000-8000-000000000072"


class ClientProtocolTest(unittest.TestCase):
    def connected_context(self) -> Jak3Context:
        context = object.__new__(Jak3Context)
        context.auth = "Mutable Alias"
        context.slot_info = {3: SimpleNamespace(name="Canonical Jak Slot")}
        context.authenticated_slot = None
        context.slot_contract_error = ""
        context.persistence_contract_status = "not authenticated"
        context.persistence_binding_status = "not attempted"
        context.persistence_recovery_status = "not attempted"
        context.persistence_quarantine_status = "not attempted"
        context.persistence_read_only_failure = ""
        context.room_seed = ""
        context.state_session = None
        context.protocol = None
        context.protocol_sync_event = asyncio.Event()
        return context

    def authenticated_slot(self) -> AuthenticatedSlot:
        return AuthenticatedSlot(
            seed_identifier="authenticated-seed-identifier",
            team=2,
            slot=3,
            slot_name="Canonical Jak Slot",
            contract=build_slot_data(
                SUPPORTED_FIRST_RELEASE_OPTIONS,
                seed_identifier="authenticated-seed-identifier",
            ),
        )

    def test_goal_protocol_string_is_escaped(self) -> None:
        self.assertEqual(_goal_string_literal("session\\value"), '"session\\\\value"')
        self.assertEqual(_goal_string_literal('session"value'), '"session\\"value"')

    def test_goal_protocol_string_is_ascii_and_bounded(self) -> None:
        self.assertEqual(_goal_string_literal("session-\u00e9"), '"session-?"')
        with self.assertRaises(ValueError):
            _goal_string_literal("x" * 97)

    def test_goal_state_path_is_escaped_without_short_string_limit(self) -> None:
        encoded = _goal_path_literal("D:\\AP State\\jak3-\u00e9.tmp")
        self.assertEqual(encoded, '"D:\\\\AP State\\\\jak3-\u00e9.tmp"')

    def test_goal_state_path_rejects_control_characters(self) -> None:
        with self.assertRaises(ValueError):
            _goal_path_literal("D:\\bad\npath")

    def test_client_requests_full_received_items_stream(self) -> None:
        self.assertEqual(Jak3Context.items_handling, 0b111)

    def test_server_rejection_disconnect_and_nrepl_timeout_are_distinct(self) -> None:
        emitted: list[str] = []
        context = object.__new__(Jak3Context)
        context.diagnostics = SimpleNamespace(
            emit=lambda event_name, **_fields: emitted.append(event_name)
        )
        context.server = object()
        with patch.object(
            CommonContext, "connection_closed", new_callable=AsyncMock
        ) as parent_close:
            asyncio.run(context.connection_closed())
            parent_close.assert_awaited_once()
        with self.assertRaisesRegex(Exception, "Invalid Slot"):
            context.event_invalid_slot()

        class TimeoutRepl:
            writer = object()
            connected = True

            async def close(self) -> None:
                self.writer = None
                self.connected = False

        context.repl = TimeoutRepl()
        context.state_session = None
        context.protocol = None
        context.bridge_ready = True
        context.source_loaded = True
        context.game_attached = True
        context.last_bridge_error = ""
        context._communication_lost = False
        asyncio.run(
            context.mark_bridge_unavailable(
                ConnectionError("Timed out waiting for nREPL")
            )
        )
        self.assertIn("server.disconnected", emitted)
        self.assertIn("server.rejected", emitted)
        self.assertIn("nrepl.timeout", emitted)
        self.assertIn("nrepl.closed", emitted)
        self.assertIn("runtime.communication.lost", emitted)

    def test_connected_uses_authenticated_seed_team_slot_and_canonical_name(
        self,
    ) -> None:
        context = self.connected_context()
        context.on_package("RoomInfo", {"seed_name": "diagnostic-room-name"})
        context.on_package(
            "Connected",
            {
                "team": 2,
                "slot": 3,
                "slot_data": build_slot_data(
                    SUPPORTED_FIRST_RELEASE_OPTIONS,
                    seed_identifier="authenticated-seed-identifier",
                ),
            },
        )

        self.assertEqual("diagnostic-room-name", context.room_seed)
        self.assertIsNotNone(context.authenticated_slot)
        assert context.authenticated_slot is not None
        self.assertEqual(
            "authenticated-seed-identifier",
            context.authenticated_slot.seed_identifier,
        )
        self.assertEqual(2, context.authenticated_slot.team)
        self.assertEqual(3, context.authenticated_slot.slot)
        self.assertEqual("Canonical Jak Slot", context.authenticated_slot.slot_name)
        self.assertEqual("validated", context.persistence_contract_status)
        self.assertEqual(
            "awaiting native save identity", context.persistence_binding_status
        )

    def test_slot_authentication_controls_save_identity_proposal(self) -> None:
        context = self.connected_context()
        authorizations: list[bool] = []
        context.protocol = SimpleNamespace(
            set_ap_state_status=lambda **_status: None,
            set_save_identity_authorized=authorizations.append,
        )

        context.on_package("RoomInfo", {"seed_name": "room"})
        self.assertTrue(context.protocol_sync_event.is_set())
        context.protocol_sync_event.clear()
        context.on_package(
            "Connected",
            {
                "team": 2,
                "slot": 3,
                "slot_data": build_slot_data(
                    SUPPORTED_FIRST_RELEASE_OPTIONS,
                    seed_identifier="authenticated-seed-identifier",
                ),
            },
        )

        self.assertEqual(authorizations, [False, True])
        self.assertTrue(context.protocol_sync_event.is_set())

    def test_loaded_bridge_probe_requires_the_complete_contract(self) -> None:
        snapshot = BridgeSnapshot()
        self.assertTrue(_loaded_bridge_matches_current_contract(snapshot))
        self.assertTrue(_loaded_diagnostics_matches_current_contract(snapshot))
        diagnostic_mismatch = replace(snapshot, diagnostic_schema_version=None)
        self.assertTrue(_loaded_bridge_matches_current_contract(diagnostic_mismatch))
        self.assertFalse(
            _loaded_diagnostics_matches_current_contract(diagnostic_mismatch)
        )
        self.assertFalse(
            _loaded_diagnostics_matches_current_contract(
                replace(snapshot, diagnostic_activation_generation=None)
            )
        )
        self.assertFalse(
            _loaded_bridge_matches_current_contract(
                replace(snapshot, item_table_hash="0" * 64)
            )
        )
        self.assertFalse(
            _loaded_bridge_matches_current_contract(
                replace(snapshot, state_schema_version=99)
            )
        )
        self.assertFalse(
            _loaded_bridge_matches_current_contract(
                replace(snapshot, bridge_runtime_version=0)
            )
        )
        for field in (
            "items_module_active",
            "locations_module_active",
            "reward_module_active",
        ):
            with self.subTest(module_attestation=field):
                self.assertFalse(
                    _loaded_bridge_matches_current_contract(
                        replace(snapshot, **{field: False})
                    )
                )

    def test_steady_heartbeats_do_not_emit_info_noise(self) -> None:
        emitted: list[str] = []
        context = object.__new__(Jak3Context)
        context.diagnostics = SimpleNamespace(
            emit=lambda event_name, **_fields: emitted.append(event_name)
        )
        snapshot = BridgeSnapshot(snapshot_revision=1)
        for revision in range(1, 10_001):
            context.observe_runtime_diagnostics(
                replace(snapshot, snapshot_revision=revision)
            )
        self.assertEqual(emitted, ["runtime.state.changed", "runtime.safety.changed"])

    def test_deferred_binding_condition_emits_only_on_transition(self) -> None:
        emitted: list[str] = []
        context = self.connected_context()
        context.diagnostics = SimpleNamespace(
            emit=lambda event_name, **_fields: emitted.append(event_name)
        )
        context._last_native_descriptor = None
        context._binding_deferred_projection = None
        context._binding_rejection_projection = None
        snapshot = BridgeSnapshot(
            save_loaded=True,
            native_save_slot=0,
            native_save_identity=LIVE_SAVE_ID,
        )

        for revision in range(1, 10_001):
            context.sync_persistence(replace(snapshot, snapshot_revision=revision))

        self.assertEqual(emitted, ["binding.deferred"])

    def test_client_persistence_sink_suppresses_identical_retry_noise(self) -> None:
        emitted: list[str] = []
        context = object.__new__(Jak3Context)
        context.diagnostics = SimpleNamespace(
            event_sink=lambda event_name, **_fields: emitted.append(event_name)
        )
        context._persistence_event_projections = {}
        fields = {
            "persistent_state_revision": 4,
            "context": {"path_hash": "safe-hash", "status": "acquired"},
        }

        context._persistence_event_sink("persistence.writer_lock.acquired", **fields)
        context._persistence_event_sink("persistence.writer_lock.acquired", **fields)
        context._persistence_event_sink("persistence.state.loaded")
        context._persistence_event_sink("persistence.writer_lock.acquired", **fields)

        self.assertEqual(
            emitted,
            [
                "persistence.writer_lock.acquired",
                "persistence.state.loaded",
                "persistence.writer_lock.acquired",
            ],
        )

    def test_closed_persistence_summary_retains_revision_and_clean_state(self) -> None:
        with TemporaryDirectory() as directory:
            context = self.connected_context()
            context.diagnostics = SimpleNamespace(emit=lambda *_args, **_fields: None)
            repository = StateRepository(Path(directory))
            context.state_session = repository.open(
                NativeSaveDescriptor(
                    slot=0,
                    identity=LIVE_SAVE_ID,
                    eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
                )
            )

            context.close_persistence(clean=True)
            summary = context._diagnostic_persistence()

            self.assertFalse(summary["open"])
            self.assertEqual(summary["binding_status"], "closed cleanly")
            self.assertIsInstance(summary["revision"], int)
            self.assertTrue(summary["last_clean_shutdown"])

    def test_diagnostics_export_command_reports_partial_bundle(self) -> None:
        output: list[str] = []
        processor = object.__new__(Jak3CommandProcessor)
        processor.ctx = SimpleNamespace(
            log_diagnostic_snapshot=lambda _reason: True,
            diagnostics=SimpleNamespace(
                export_bundle=lambda: BundleExportResult(
                    "partial", Path("Jak3Support_test.zip"), ("runtime.json",)
                )
            ),
        )
        processor.output = output.append

        async def run_export() -> None:
            processor._cmd_diagnostics("export")
            await asyncio.gather(*tuple(BACKGROUND_TASKS))

        asyncio.run(run_export())
        self.assertIn("started in the background", output[0])
        self.assertIn("Diagnostic export partial", output[1])
        self.assertIn("runtime.json", output[2])

    def test_packaged_source_update_survives_failed_client_and_forces_reload(
        self,
    ) -> None:
        class FakeRepl:
            def __init__(
                self,
                *,
                fail_reload: bool = False,
                activates_reload: bool = True,
                activates_diagnostics: bool = True,
                activates_items: bool = True,
                activates_locations: bool = True,
                activates_rewards: bool = True,
                initial_generation: int = 10,
            ) -> None:
                self.forms: list[str] = []
                self.fail_reload = fail_reload
                self.activates_reload = activates_reload
                self.activates_diagnostics = activates_diagnostics
                self.activates_items = activates_items
                self.activates_locations = activates_locations
                self.activates_rewards = activates_rewards
                self.activation_generation = initial_generation
                self.diagnostic_activation_generation = initial_generation
                self.items_module_active = True
                self.locations_module_active = True
                self.reward_module_active = True

            async def connect(self) -> None:
                return None

            async def attach(self) -> None:
                return None

            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                self.forms.append(form)
                if self.fail_reload and form.startswith('(ml "goal_src/jak3'):
                    raise ConnectionError("simulated interrupted source reload")
                if self.activates_reload and form == (
                    '(ml "goal_src/jak3/pc/features/archipelago.gc")'
                ):
                    self.activation_generation += 1
                    self.items_module_active = False
                    self.locations_module_active = False
                    self.reward_module_active = False
                if self.activates_diagnostics and form == (
                    '(ml "goal_src/jak3/pc/features/archipelago-diagnostics.gc")'
                ):
                    self.diagnostic_activation_generation += 1
                if self.activates_items and form == (
                    '(ml "goal_src/jak3/pc/features/archipelago-items.gc")'
                ):
                    self.items_module_active = True
                if self.activates_locations and form == (
                    '(ml "goal_src/jak3/pc/features/archipelago-locations.gc")'
                ):
                    self.locations_module_active = True
                if self.activates_rewards and form == (
                    '(ml "goal_src/jak3/pc/features/archipelago-rewards.gc")'
                ):
                    self.reward_module_active = True
                return "nREPL"

            async def close(self) -> None:
                return None

        class CompatibleProtocol:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.last_snapshot = None
                self.repl = args[0]

            def set_save_identity_authorized(self, authorized: bool) -> None:
                return None

            def set_ap_state_status(self, *, loaded: bool, bound: bool) -> None:
                return None

            async def initialize(self, status: object) -> BridgeSnapshot:
                return BridgeSnapshot(
                    connection_ready=True,
                    bridge_activation_generation=self.repl.activation_generation,
                    diagnostic_activation_generation=(
                        self.repl.diagnostic_activation_generation
                    ),
                )

        with TemporaryDirectory() as directory:
            reload_marker = Path(directory) / ".archipelago-reload-required"
            reload_marker.write_text("pending\n", encoding="ascii")
            active_repl: FakeRepl | None = None

            def make_context(repl: FakeRepl) -> Jak3Context:
                nonlocal active_repl
                active_repl = repl
                context = object.__new__(Jak3Context)
                context.repl = repl
                context.state_path = Path(directory) / "bridge.tmp"
                context.diagnostics = SimpleNamespace(
                    session_id="source-update-test",
                    opengoal_log=Path(directory) / "opengoal.log",
                    note_opengoal=lambda source, message: None,
                )
                context.authenticated_slot = None
                context.server = object()
                context.auth = "slot"
                context._stopping = False
                context.protocol = None
                context.state_session = None
                context.source_loaded = False
                context.bridge_ready = False
                context.compatibility_error = False
                context.last_bridge_error = ""
                context.game_attached = False
                context.bridge_source_reload_required = True
                context.bridge_source_reload_marker = reload_marker
                context.sync_persistence = lambda snapshot: None
                context.log_diagnostic_snapshot = lambda reason: True
                return context

            def read_live_snapshot(_path: Path) -> BridgeSnapshot | None:
                assert active_repl is not None
                if active_repl.activation_generation == 0:
                    return None
                return BridgeSnapshot(
                    bridge_activation_generation=active_repl.activation_generation,
                    items_module_active=active_repl.items_module_active,
                    locations_module_active=active_repl.locations_module_active,
                    reward_module_active=active_repl.reward_module_active,
                    diagnostic_activation_generation=(
                        active_repl.diagnostic_activation_generation
                    ),
                )

            with (
                patch("worlds.jak3.client.BridgeProtocol", CompatibleProtocol),
                patch(
                    "worlds.jak3.client.read_snapshot",
                    side_effect=read_live_snapshot,
                ),
            ):
                interrupted = make_context(FakeRepl(fail_reload=True))
                connected = asyncio.run(interrupted.connect_repl(report_errors=False))
                self.assertFalse(connected)
                self.assertTrue(reload_marker.is_file())
                self.assertTrue(interrupted.bridge_source_reload_required)

                not_activated = make_context(FakeRepl(activates_reload=False))
                connected = asyncio.run(not_activated.connect_repl(report_errors=False))
                self.assertFalse(connected)
                self.assertTrue(reload_marker.is_file())
                self.assertTrue(not_activated.bridge_source_reload_required)
                self.assertIn(
                    "without publishing new compatible bridge module activation generations",
                    not_activated.last_bridge_error,
                )

                diagnostic_not_activated = make_context(
                    FakeRepl(activates_diagnostics=False)
                )
                connected = asyncio.run(
                    diagnostic_not_activated.connect_repl(report_errors=False)
                )
                self.assertFalse(connected)
                self.assertTrue(reload_marker.is_file())
                self.assertTrue(diagnostic_not_activated.bridge_source_reload_required)

                items_not_activated = make_context(FakeRepl(activates_items=False))
                connected = asyncio.run(
                    items_not_activated.connect_repl(report_errors=False)
                )
                self.assertFalse(connected)
                self.assertTrue(reload_marker.is_file())
                self.assertTrue(items_not_activated.bridge_source_reload_required)

                locations_not_activated = make_context(
                    FakeRepl(activates_locations=False)
                )
                connected = asyncio.run(
                    locations_not_activated.connect_repl(report_errors=False)
                )
                self.assertFalse(connected)
                self.assertTrue(reload_marker.is_file())
                self.assertTrue(locations_not_activated.bridge_source_reload_required)

                rewards_not_activated = make_context(FakeRepl(activates_rewards=False))
                connected = asyncio.run(
                    rewards_not_activated.connect_repl(report_errors=False)
                )
                self.assertFalse(connected)
                self.assertTrue(reload_marker.is_file())
                self.assertTrue(rewards_not_activated.bridge_source_reload_required)

                context = make_context(FakeRepl())
                connected = asyncio.run(context.connect_repl(report_errors=False))
                self.assertTrue(connected)
                self.assertIn(
                    '(ml "goal_src/jak3/pc/features/archipelago.gc")',
                    context.repl.forms,
                )
                self.assertFalse(context.bridge_source_reload_required)
                self.assertFalse(reload_marker.exists())

                reload_marker.write_text("pending\n", encoding="ascii")
                first_install = make_context(FakeRepl(initial_generation=0))
                connected = asyncio.run(first_install.connect_repl(report_errors=False))
                self.assertTrue(connected)
                self.assertEqual(
                    2,
                    first_install.repl.forms.count(
                        '(ml "goal_src/jak3/pc/features/archipelago.gc")'
                    ),
                )
                self.assertFalse(first_install.bridge_source_reload_required)
                self.assertFalse(reload_marker.exists())

    def test_compatible_bridge_resets_goal_source_only_for_a_restarted_game(
        self,
    ) -> None:
        class FakeRepl:
            def __init__(self) -> None:
                self.forms: list[str] = []
                self.connected = True

            async def connect(self) -> None:
                return None

            async def attach(self) -> None:
                return None

            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                self.forms.append(form)
                return "nREPL"

            async def close(self) -> None:
                return None

        class CompatibleProtocol:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.last_snapshot = None

            def set_save_identity_authorized(self, authorized: bool) -> None:
                return None

            def set_ap_state_status(self, *, loaded: bool, bound: bool) -> None:
                return None

            async def initialize(self, status: object) -> BridgeSnapshot:
                return BridgeSnapshot(connection_ready=True, session_nonce="new-game")

        def connect(
            candidate_nonce: str | None, *, diagnostics_ready: bool = True
        ) -> tuple[Jak3Context, list[str]]:
            resets: list[str] = []
            context = object.__new__(Jak3Context)
            context.repl = FakeRepl()
            context.state_path = Path(directory) / "restart-bridge.tmp"
            context.diagnostics = SimpleNamespace(
                session_id="goal-generation-test",
                note_opengoal=lambda source, message: None,
                reset_goal_event_source=lambda: resets.append("reset"),
                emit=lambda event_name, **fields: None,
            )
            context.authenticated_slot = None
            context.server = object()
            context.auth = "slot"
            context._stopping = False
            context.protocol = None
            context.state_session = None
            context.source_loaded = False
            context.bridge_ready = False
            context.compatibility_error = False
            context.last_bridge_error = ""
            context.game_attached = False
            context.bridge_source_reload_required = False
            context.bridge_source_reload_marker = None
            context.bridge_source_set_hash = "current"
            context._goal_game_session_nonce = "old-game"
            context._communication_lost = False
            context._item_native_rebuild_event_scope = ("stale-source",)
            context._item_native_rebuild_location_ids = {743_001_010}
            context._item_native_rebuild_reward_sequence = 41
            context.sync_persistence = lambda snapshot: None
            candidate = BridgeSnapshot(
                session_nonce=candidate_nonce,
                diagnostic_schema_version=1 if diagnostics_ready else None,
                diagnostic_manifest_version=1 if diagnostics_ready else None,
            )
            with (
                patch("worlds.jak3.client.read_snapshot", return_value=candidate),
                patch("worlds.jak3.client.BridgeProtocol", CompatibleProtocol),
            ):
                self.assertTrue(asyncio.run(context.connect_repl(report_errors=False)))
            return context, resets

        with TemporaryDirectory() as directory:
            restarted, restarted_resets = connect(None)
            transient, transient_resets = connect("old-game")
            diagnostic_repair, diagnostic_resets = connect(
                "old-game", diagnostics_ready=False
            )

        self.assertEqual(restarted_resets, ["reset"])
        self.assertEqual(restarted._goal_game_session_nonce, "new-game")
        self.assertIsNone(restarted._item_native_rebuild_event_scope)
        self.assertEqual(restarted._item_native_rebuild_location_ids, set())
        self.assertEqual(restarted._item_native_rebuild_reward_sequence, -1)
        self.assertEqual(transient_resets, [])
        self.assertEqual(transient._goal_game_session_nonce, "new-game")
        self.assertEqual(transient._item_native_rebuild_event_scope, ("stale-source",))
        self.assertFalse(any(form.startswith('(ml "') for form in restarted.repl.forms))
        self.assertEqual(diagnostic_resets, [])
        self.assertIn(
            '(ml "goal_src/jak3/pc/features/archipelago-diagnostics.gc")',
            diagnostic_repair.repl.forms,
        )
        self.assertNotIn(
            '(ml "goal_src/jak3/pc/features/archipelago.gc")',
            diagnostic_repair.repl.forms,
        )

    def test_incompatible_connected_contract_refuses_binding_read_only(self) -> None:
        context = self.connected_context()
        invalid = build_slot_data(
            SUPPORTED_FIRST_RELEASE_OPTIONS,
            seed_identifier="authenticated-seed-identifier",
        )
        invalid["item_table_hash"] = "0" * 64
        context.on_package(
            "Connected",
            {"team": 2, "slot": 3, "slot_data": invalid},
        )

        self.assertIsNone(context.authenticated_slot)
        self.assertEqual("rejected", context.persistence_contract_status)
        self.assertEqual("refused read-only", context.persistence_binding_status)
        self.assertIn("item_table_hash", context.persistence_read_only_failure)

    def test_connected_rejects_boolean_integer_version_alias(self) -> None:
        context = self.connected_context()
        invalid = build_slot_data(
            SUPPORTED_FIRST_RELEASE_OPTIONS,
            seed_identifier="authenticated-seed-identifier",
        )
        invalid["game_integration_version"] = True
        context.on_package(
            "Connected",
            {"team": 2, "slot": 3, "slot_data": invalid},
        )

        self.assertIsNone(context.authenticated_slot)
        self.assertEqual("rejected", context.persistence_contract_status)
        self.assertEqual("refused read-only", context.persistence_binding_status)
        self.assertIn("game_integration_version", context.persistence_read_only_failure)

    def test_goal_bridge_has_only_metadata_and_test_target_hooks(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        self.assertIn("AP-NATIVE-SAVE-TAG 900", source)
        self.assertIn("ap3-save-game-wrapper", source)
        self.assertIn("ap3-load-game-wrapper", source)
        self.assertIn("AP-COMMAND-SET-TEST-TARGET 100", source)
        for forbidden in (
            "ap-receive-",
            "ap-play-task!",
            "ap-start-game!",
            "ap-resync-items!",
            "task-resolution-close!",
            "send-event",
            "LocationChecks",
            "StatusUpdate",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_goal_bridge_exports_unquoted_protocol_strings(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        self.assertIn('(format file "session_nonce ~S~%"', source)
        self.assertIn('(format file "last_error_message ~S~%"', source)

    def test_goal_command_refreshes_runtime_before_checking_mutation_safety(
        self,
    ) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        command = source.split("(defun ap3-command-core!", 1)[1].split(
            "(defun ap-client-disconnect!", 1
        )[0]

        self.assertLess(
            command.index("(ap3-observe-runtime!)"),
            command.index("((zero? (-> *ap-runtime* safe-permanent))"),
        )

    def test_goal_save_switch_requires_a_new_sidecar_acknowledgement(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        publication = source.split("(defun ap3-publish-pending-native-save!", 1)[
            1
        ].split("(defbehavior ap3-auto-save-done-code", 1)[0]

        identity_publish = publication.index(
            "(ap3-copy-string! *ap3-native-save-identity*"
        )
        self.assertLess(
            publication.index("(set! (-> *ap-runtime* ap-state-loaded) 0)"),
            identity_publish,
        )
        self.assertLess(
            publication.index("(set! (-> *ap-runtime* ap-state-bound) 0)"),
            identity_publish,
        )
        self.assertIn("*ap3-pending-save-identity*", publication)
        self.assertIn("(!= (-> *ap-runtime* native-save-slot) slot)", publication)
        self.assertIn("(set! (-> *ap-runtime* native-save-slot) slot)", publication)

    def test_goal_sidecar_acknowledgement_matches_identity_and_slot(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        acknowledgement = source.split("(defun ap3-apply-sidecar-state!", 1)[1].split(
            "(defun ap3-update-client-state!", 1
        )[0]
        command = source.split("(defun ap3-command-core!", 1)[1].split(
            "(defun ap-client-disconnect!", 1
        )[0]

        self.assertIn("state-save-slot", acknowledgement)
        self.assertIn("(-> *ap-runtime* native-save-slot)", acknowledgement)
        self.assertIn("state-save-identity", acknowledgement)
        self.assertIn("*ap3-native-save-identity*", acknowledgement)
        self.assertLess(
            command.index("(ap3-apply-sidecar-state!"),
            command.index("(ap3-observe-runtime!)"),
        )

    def test_goal_identity_publication_requires_matching_native_success(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        done_hook = source.split("(defbehavior ap3-auto-save-done-code", 1)[1].split(
            "(defbehavior ap3-auto-save-error-code", 1
        )[0]
        error_hook = source.split("(defbehavior ap3-auto-save-error-code", 1)[1].split(
            "(defun ap3-set-contract-versions!", 1
        )[0]
        publisher = source.split("(defun ap3-publish-pending-native-save!", 1)[1].split(
            "(defbehavior ap3-auto-save-done-code", 1
        )[0]
        observer = source.split("(defun ap3-observe-runtime!", 1)[1].split(
            "(defun ap-export-state!", 1
        )[0]

        self.assertLess(
            done_hook.index("(set! *ap3-pending-save-succeeded* 1)"),
            done_hook.index("(ap3-publish-pending-native-save! (-> self which))"),
        )
        self.assertLess(
            done_hook.index("(ap3-publish-pending-native-save! (-> self which))"),
            done_hook.index("*ap3-native-auto-save-done-code*"),
        )
        self.assertNotIn("ap3-pending-operation-matches?", done_hook)
        self.assertIn("(set! *ap3-pending-save-valid* 0)", error_hook)
        self.assertIn('"native-save-io-failed"', error_hook)
        self.assertIn("(= *ap3-pending-save-succeeded* 1)", publisher)
        self.assertIn("((slot int))", publisher)
        self.assertIn("*ap3-reload-save-identity*", publisher)
        self.assertNotIn("auto-save-proc", publisher)
        self.assertIn(
            "(ap3-publish-pending-native-save! (-> *game-info* auto-save-which))",
            observer,
        )

    def test_goal_native_hooks_preserve_originals_across_bridge_reload(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        installer = source.split("(defun ap3-install-native-hooks!", 1)[1].split(
            "(defun ap3-init!", 1
        )[0]
        initializer = source.split("(defun ap3-init!", 1)[1]

        self.assertIn("(define-perm *ap3-activation-generation* int 0)", source)
        self.assertIn("(+! *ap3-activation-generation* 1)", initializer)
        self.assertIn(
            '"bridge_activation_generation ~D~%"',
            source,
        )

        for current, installed, native in (
            (
                "current-initialize",
                "*ap3-installed-game-info-initialize-wrapper*",
                "*ap3-native-game-info-initialize*",
            ),
            (
                "current-save",
                "*ap3-installed-save-wrapper*",
                "*ap3-native-save-game*",
            ),
            (
                "current-load",
                "*ap3-installed-load-wrapper*",
                "*ap3-native-load-game*",
            ),
            (
                "current-done-code",
                "*ap3-installed-auto-save-done-code*",
                "*ap3-native-auto-save-done-code*",
            ),
            (
                "current-error-code",
                "*ap3-installed-auto-save-error-code*",
                "*ap3-native-auto-save-error-code*",
            ),
        ):
            with self.subTest(native=native):
                guard = f"(!= {current} {installed})"
                self.assertIn(guard, installer)
                self.assertLess(
                    installer.index(guard), installer.index(f"(set! {native}")
                )

        self.assertIn(
            "(method-set! game-info 9 ap3-game-info-initialize-wrapper)", installer
        )
        self.assertIn("(method-set! game-info 22 ap3-save-game-wrapper)", installer)
        self.assertIn("(method-set! game-info 23 ap3-load-game-wrapper)", installer)
        self.assertIn("(set! (-> done-state code) ap3-auto-save-done-code)", installer)
        self.assertIn(
            "(set! (-> error-state code) ap3-auto-save-error-code)", installer
        )

    def test_goal_unsaved_game_initialization_invalidates_prior_binding(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        wrapper = source.split("(defun ap3-game-info-initialize-wrapper", 1)[1].split(
            "(defun ap3-publish-pending-native-save!", 1
        )[0]
        invalidation = source.split("(defun ap3-invalidate-native-save-binding!", 1)[
            1
        ].split("(defun ap3-stage-native-operation!", 1)[0]
        done_hook = source.split("(defbehavior ap3-auto-save-done-code", 1)[1].split(
            "(defbehavior ap3-auto-save-error-code", 1
        )[0]

        self.assertIn("(and (= mode 'game) (not save))", wrapper)
        self.assertIn("(= *ap3-saved-new-game-ready* 1)", wrapper)
        self.assertNotIn("handle->process", wrapper)
        self.assertIn("(= (-> *ap-runtime* save-loaded) 1)", wrapper)
        self.assertIn("(ap3-valid-uuid-shape? *ap3-native-save-identity*)", wrapper)
        self.assertNotIn("(set! *ap3-saved-new-game-ready* 0)", wrapper)
        self.assertIn("(ap3-invalidate-native-save-binding!)", wrapper)
        self.assertLess(
            wrapper.index("(ap3-invalidate-native-save-binding!)"),
            wrapper.index("(*ap3-native-game-info-initialize*"),
        )

        self.assertIn("(ap3-clear-reload-save-state!)", invalidation)
        self.assertIn(
            '(ap3-copy-string! *ap3-native-save-identity* "-" 96)', invalidation
        )
        self.assertIn("(set! (-> *ap-runtime* save-loaded) 0)", invalidation)
        self.assertIn("(set! (-> *ap-runtime* ap-state-loaded) 0)", invalidation)
        self.assertIn("(set! (-> *ap-runtime* ap-state-bound) 0)", invalidation)
        self.assertIn('"native-save-not-loaded"', invalidation)

        self.assertIn("(= *ap3-pending-save-new-game* 1)", done_hook)
        self.assertIn("(set! *ap3-saved-new-game-ready* 1)", done_hook)

    def test_goal_new_game_guard_spans_native_done_notification_only(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        done_hook = source.split("(defbehavior ap3-auto-save-done-code", 1)[1].split(
            "(defbehavior ap3-auto-save-error-code", 1
        )[0]
        error_hook = source.split("(defbehavior ap3-auto-save-error-code", 1)[1].split(
            "(defun ap3-set-contract-versions!", 1
        )[0]

        observer = source.split("(defun ap3-observe-runtime!", 1)[1].split(
            "(defun ap-export-state!", 1
        )[0]

        native_done = done_hook.index("*ap3-native-auto-save-done-code*")
        publication = done_hook.index(
            "(ap3-publish-pending-native-save! (-> self which))"
        )
        guard_clear = done_hook.index("(set! *ap3-saved-new-game-ready* 0)")
        self.assertLess(publication, native_done)
        self.assertLess(native_done, guard_clear)
        self.assertIn("(not (handle->process *ap3-pending-save-process*))", observer)
        self.assertIn("(ap3-clear-pending-native-operation!)", observer)
        self.assertIn("(set! *ap3-saved-new-game-ready* 0)", error_hook)

    def test_goal_published_save_descriptor_survives_bridge_reload(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        publisher = source.split("(defun ap3-publish-pending-native-save!", 1)[1].split(
            "(defbehavior ap3-auto-save-done-code", 1
        )[0]
        initializer = source.split("(defun ap3-init!", 1)[1].split(
            "(ap3-install-native-hooks!)", 1
        )[0]
        tag_reader = source.split("(defun ap3-read-native-save-tag!", 1)[1].split(
            "(defun ap3-save-game-wrapper", 1
        )[0]

        for name in (
            "*ap3-reload-save-identity*",
            "*ap3-reload-save-loaded*",
            "*ap3-reload-save-slot*",
            "*ap3-reload-save-eligibility*",
        ):
            self.assertIn(f"(define-extern {name}", source)
            self.assertIn(f"(define-perm {name}", source)
            self.assertIn(name, publisher)
            self.assertIn(name, initializer)
        self.assertIn("(ap3-clear-reload-save-state!)", tag_reader)
        self.assertIn("(ap3-valid-uuid-shape? *ap3-reload-save-identity*)", initializer)
        self.assertIn(
            "(ap3-copy-string! *ap3-native-save-identity*\n"
            "                          *ap3-reload-save-identity* 96)",
            initializer,
        )

    def test_goal_in_flight_native_operation_survives_bridge_reload(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        initializer = source.split("(defun ap3-init!", 1)[1].split(
            "(ap3-install-native-hooks!)", 1
        )[0]

        for name in (
            "*ap3-pending-save-identity*",
            "*ap3-pending-save-valid*",
            "*ap3-pending-save-succeeded*",
            "*ap3-pending-save-new-game*",
            "*ap3-saved-new-game-ready*",
            "*ap3-pending-save-process*",
            "*ap3-pending-save-eligibility*",
        ):
            with self.subTest(name=name):
                self.assertIn(f"(define-extern {name}", source)
                self.assertIn(f"(define-perm {name}", source)

        self.assertNotIn("(set! *ap3-pending-save-valid* 0)", initializer)
        self.assertNotIn("(set! *ap3-saved-new-game-ready* 0)", initializer)
        self.assertNotIn("(ap3-clear-pending-native-operation!)", initializer)

    def test_goal_save_proposals_are_live_authenticated_and_one_shot(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        wrapper = source.split("(defun ap3-save-game-wrapper", 1)[1].split(
            "(defun ap3-load-game-wrapper", 1
        )[0]
        liveness = source.split("(defun ap3-save-identity-proposal-usable?", 1)[
            1
        ].split("(defun ap3-game-has-progress?", 1)[0]
        publisher = source.split("(defun ap3-publish-pending-native-save!", 1)[1].split(
            "(defbehavior ap3-auto-save-done-code", 1
        )[0]
        proposal_update = source.split("(defun ap3-update-proposed-save-identity!", 1)[
            1
        ].split("(defmacro ap-client-hello!", 1)[0]
        disconnect = source.split("(defun ap-client-disconnect!", 1)[1].split(
            "(defun ap3-install-native-hooks!", 1
        )[0]

        self.assertIn("(ap3-save-identity-proposal-usable?)", wrapper)
        self.assertIn("connection-ready", liveness)
        self.assertIn("AP-CLIENT-STATUS-AP-CONNECTED", liveness)
        self.assertIn("*ap3-last-client-contact-frame*", liveness)
        self.assertIn("(seconds 5)", liveness)
        self.assertIn("(string= *ap3-proposed-save-identity*", publisher)
        self.assertIn("*ap3-native-save-identity*)", publisher)
        self.assertIn("(ap3-copy-string! *ap3-consumed-save-identity*", publisher)
        self.assertIn(
            '(ap3-copy-string! *ap3-proposed-save-identity* "-" 96)', publisher
        )
        self.assertLess(
            publisher.index("(ap3-copy-string! *ap3-consumed-save-identity*"),
            publisher.index('(ap3-copy-string! *ap3-proposed-save-identity* "-" 96)'),
        )
        self.assertIn(
            "(not (string= proposed-save *ap3-native-save-identity*))",
            proposal_update,
        )
        self.assertIn(
            "(not (string= proposed-save *ap3-consumed-save-identity*))",
            proposal_update,
        )
        self.assertIn(
            '(format file "consumed_save_identity ~S~%" *ap3-consumed-save-identity*)',
            source,
        )
        self.assertIn("(set! *ap3-last-client-contact-frame* -1)", disconnect)
        self.assertIn(
            '(ap3-copy-string! *ap3-proposed-save-identity* "-" 96)', disconnect
        )

    def test_goal_new_game_prefers_fresh_proposal_over_current_identity(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        wrapper = source.split("(defun ap3-save-game-wrapper", 1)[1].split(
            "(defun ap3-load-game-wrapper", 1
        )[0]

        new_game_guard = "(if (= (-> result new-game) 1)"
        self.assertIn(new_game_guard, wrapper)
        self.assertLess(
            wrapper.index(new_game_guard),
            wrapper.index("(ap3-valid-uuid-shape? *ap3-native-save-identity*)"),
        )
        self.assertLess(
            wrapper.index("*ap3-proposed-save-identity*"),
            wrapper.index("*ap3-native-save-identity*"),
        )
        new_game_branch = wrapper.split(new_game_guard, 1)[1].split(
            "(if (ap3-valid-uuid-shape? *ap3-native-save-identity*)", 1
        )[0]
        self.assertIn("(if (ap3-save-identity-proposal-usable?)", new_game_branch)
        self.assertIn('"-"', new_game_branch)
        self.assertNotIn("*ap3-native-save-identity*", new_game_branch)

    def test_goal_native_restore_records_io_outcomes_at_state_boundaries(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        load_wrapper = source.split("(defun ap3-load-game-wrapper", 1)[1].split(
            "(defbehavior ap3-auto-save-restore-code", 1
        )[0]
        restore_wrapper = source.split("(defbehavior ap3-auto-save-restore-code", 1)[
            1
        ].split("(defun ap3-game-info-initialize-wrapper", 1)[0]
        done_wrapper = source.split("(defbehavior ap3-auto-save-done-code", 1)[1].split(
            "(defbehavior ap3-auto-save-error-code", 1
        )[0]
        error_wrapper = source.split("(defbehavior ap3-auto-save-error-code", 1)[
            1
        ].split("(defun ap3-set-contract-versions!", 1)[0]

        self.assertNotIn("AP-DIAG-EVENT-SAVE-STARTED", load_wrapper)
        self.assertNotIn("AP-DIAG-EVENT-SAVE-SUCCEEDED", load_wrapper)
        self.assertIn("AP-DIAG-NATIVE-OP-LOAD", restore_wrapper)
        self.assertLess(
            restore_wrapper.index("ap3-diagnostic-stage-native-operation!"),
            restore_wrapper.index("*ap3-native-auto-save-restore-code*"),
        )
        self.assertEqual(done_wrapper.count("AP-DIAG-EVENT-SAVE-SUCCEEDED"), 1)
        self.assertIn("*ap3-diagnostic-native-operation-kind*", done_wrapper)
        self.assertLess(
            done_wrapper.index("AP-DIAG-EVENT-SAVE-SUCCEEDED"),
            done_wrapper.index("*ap3-native-auto-save-done-code*"),
        )
        self.assertIn("AP-DIAG-EVENT-SAVE-FAILED", error_wrapper)
        self.assertLess(
            error_wrapper.index("AP-DIAG-EVENT-SAVE-FAILED"),
            error_wrapper.index("*ap3-pending-save-valid*"),
        )

    def test_goal_uuid_validation_checks_length_before_reading_bytes(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        validator = source.split("(defun ap3-valid-uuid-shape?", 1)[1].split(
            "(defun ap3-clear-reload-save-state!", 1
        )[0]

        length_guard = "(if (!= (length identity) 36)"
        self.assertIn(length_guard, validator)
        self.assertLess(
            validator.index(length_guard), validator.index("(dotimes (index 36)")
        )

    def test_goal_query_and_disconnect_validate_status_before_mutation(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        query = source.split("(defun ap-query-state!", 1)[1].split(
            "(defun ap3-find-receipt", 1
        )[0]
        disconnect = source.split("(defun ap-client-disconnect!", 1)[1].split(
            "(defun ap3-install-native-hooks!", 1
        )[0]
        validation = "(not (ap3-valid-client-status? client-status))"

        self.assertIn(validation, query)
        self.assertLess(
            query.index(validation), query.index("(ap3-update-client-state!")
        )
        self.assertIn(validation, disconnect)
        self.assertLess(
            disconnect.index(validation),
            disconnect.index("(set! (-> *ap-runtime* client-status) client-status)"),
        )

    def test_goal_eligibility_monotonicity_is_scoped_to_one_identity(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        eligibility = source.split("(defun ap3-note-save-eligibility!", 1)[1].split(
            "(defun ap3-append-native-save-tag!", 1
        )[0]

        self.assertIn("AP-SAVE-ELIGIBILITY-INELIGIBLE", eligibility)
        self.assertIn(
            "(string= *ap3-pending-save-identity*\n"
            "                      *ap3-native-save-identity*)",
            eligibility,
        )

    def test_goal_tag_append_failure_invalidates_live_binding(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        append = source.split("(defun ap3-append-native-save-tag!", 1)[1].split(
            "(defun ap3-read-native-save-tag!", 1
        )[0]
        failure = append.split("(begin", 1)[1].split("(let*", 1)[0]

        self.assertIn("(ap3-clear-reload-save-state!)", failure)
        self.assertIn('(ap3-copy-string! *ap3-native-save-identity* "-" 96)', failure)
        self.assertIn("(set! (-> *ap-runtime* save-loaded) 0)", failure)
        self.assertIn("(set! (-> *ap-runtime* ap-state-loaded) 0)", failure)
        self.assertIn("(set! (-> *ap-runtime* ap-state-bound) 0)", failure)
        self.assertIn('"native-save-tag-append-failed"', failure)

    def test_goal_safety_requires_live_target_and_level_without_latching(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        task_observer = source.split("(defun ap3-observe-task!", 1)[1].split(
            "(defun ap3-observe-runtime!", 1
        )[0]
        runtime_observer = source.split("(defun ap3-observe-runtime!", 1)[1].split(
            "(defun ap-export-state!", 1
        )[0]
        stable = runtime_observer.split("(set! stable", 1)[1].split(
            "(set! (-> *ap-runtime* safe-permanent)", 1
        )[0]

        reset = "(set! (-> *ap-runtime* current-level) (the-as symbol #f))"
        self.assertIn(reset, task_observer)
        self.assertLess(task_observer.index(reset), task_observer.index("(dotimes"))
        normalized = " ".join(stable.split())
        self.assertIn("(not (not *target*))", normalized)
        self.assertIn("(not (not level))", normalized)

    def test_goal_freshness_uses_only_the_serialized_save(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        freshness = source.split("(defun ap3-save-fresh-unprogressed?", 1)[1].split(
            "(defun ap3-clear-pending-native-operation!", 1
        )[0]

        self.assertNotIn("*game-info*", freshness)
        for tag in (
            "(game-save-elt money-total)",
            "(game-save-elt gem-total)",
            "(game-save-elt skill-total)",
            "(game-save-elt task-list)",
        ):
            self.assertIn(tag, freshness)
        self.assertIn("(< (-> tag 0 elt-count) 138)", freshness)
        self.assertIn("(let ((task-id (+ offset 6)))", freshness)
        self.assertIn("(entity-perm-status complete)", freshness)
        self.assertIn("(the-as entity-perm", freshness)
        self.assertNotIn("(pointer entity-perm)", freshness)

    def test_goal_transformation_guard_includes_dark_and_light_jak(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        vehicle_guard = source.split("(vehicle (and *target*", 1)[1].split(
            "(stable #f)", 1
        )[0]

        self.assertIn("dark light", " ".join(vehicle_guard.split()))

    def test_goal_native_tag_failures_remain_snapshot_visible(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        tag_reader = source.split("(defun ap3-read-native-save-tag!", 1)[1].split(
            "(defun ap3-save-game-wrapper", 1
        )[0]
        exporter = source.split("(defun ap-export-state!", 1)[1].split(
            "(defun ap-set-state-path!", 1
        )[0]
        initializer = source.split("(defun ap3-init!", 1)[1].split(
            "(ap3-install-native-hooks!)", 1
        )[0]

        self.assertIn('"native-save-tag-missing"', tag_reader)
        self.assertIn('"native-save-tag-malformed"', tag_reader)
        self.assertIn('"native-save-tag-duplicate"', tag_reader)
        self.assertIn("*ap3-native-save-error-code*", exporter)
        self.assertIn("*ap3-native-save-error-message*", exporter)
        for name in (
            "*ap3-native-save-error-code*",
            "*ap3-native-save-error-message*",
        ):
            self.assertIn(f"(define-extern {name}", source)
            self.assertIn(f"(define-perm {name}", source)
        self.assertNotIn("(ap3-clear-native-save-error!)", initializer)

    def test_goal_contract_hashes_require_exact_wire_length(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        setter = source.split("(defun ap3-set-contract-hashes!", 1)[1].split(
            "(defun ap3-contract-error", 1
        )[0]

        for name in ("item-hash", "location-hash", "mission-hash"):
            self.assertIn(f"(= (length {name}) 64)", setter)
        self.assertEqual(setter.count("(if (= (length"), 3)

    def test_goal_rejects_values_wider_than_receipt_fields_before_mutation(
        self,
    ) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        command = source.split("(defun ap3-command-core!", 1)[1].split(
            "(defun ap-client-disconnect!", 1
        )[0]

        self.assertIn("(ap3-wire-int32? command-id)", command)
        self.assertIn("(ap3-wire-int32? kind)", command)
        self.assertIn("(ap3-wire-int32? payload)", command)
        rejection = command.index('"wire-integer-out-of-range"')
        self.assertLess(rejection, command.index("(ap3-record-receipt!"))
        self.assertLess(rejection, command.index("(set! (-> *ap-runtime* test-target)"))

    def test_incompatible_reconnect_releases_live_persistence_session(self) -> None:
        closed_clean: list[bool] = []
        protocol_state: list[tuple[bool, bool]] = []
        incompatible_snapshot = BridgeSnapshot(protocol_version=2)

        class FakeRepl:
            def __init__(self) -> None:
                self.closed = False

            async def connect(self) -> None:
                return None

            async def attach(self) -> None:
                return None

            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                return "nREPL"

            async def close(self) -> None:
                self.closed = True

        class IncompatibleProtocol:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.last_snapshot = incompatible_snapshot

            def set_save_identity_authorized(self, authorized: bool) -> None:
                return None

            def set_ap_state_status(self, *, loaded: bool, bound: bool) -> None:
                protocol_state.append((loaded, bound))

            async def initialize(self, status: object) -> BridgeSnapshot:
                raise ProtocolVersionMismatch(2)

        with TemporaryDirectory() as directory:
            context = object.__new__(Jak3Context)
            context.repl = FakeRepl()
            context.state_path = Path(directory) / "bridge.tmp"
            context.diagnostics = SimpleNamespace(
                session_id="compatibility-test",
                opengoal_log=Path(directory) / "opengoal.log",
                note_opengoal=lambda source, message: None,
            )
            context.authenticated_slot = None
            context.server = object()
            context.auth = "slot"
            context._stopping = False
            context.protocol = None
            context.state_session = SimpleNamespace(
                close=lambda *, clean: closed_clean.append(clean),
                native_save=SimpleNamespace(identity=LIVE_SAVE_ID),
                state=SimpleNamespace(state_revision=1),
            )
            context.source_loaded = False
            context.bridge_ready = True
            context.compatibility_error = False
            context.last_bridge_error = ""
            context.game_attached = False

            with (
                patch(
                    "worlds.jak3.client.read_snapshot",
                    return_value=incompatible_snapshot,
                ),
                patch("worlds.jak3.client.BridgeProtocol", IncompatibleProtocol),
            ):
                connected = asyncio.run(context.connect_repl(report_errors=False))

        self.assertFalse(connected)
        self.assertEqual(closed_clean, [False])
        self.assertIsNone(context.state_session)
        self.assertEqual(protocol_state, [(False, False)])
        self.assertTrue(context.repl.closed)

    def test_live_fresh_save_binds_and_persists_harmless_receipt(self) -> None:
        with TemporaryDirectory() as directory:
            context = self.connected_context()
            context.authenticated_slot = self.authenticated_slot()
            context.state_repository = StateRepository(Path(directory))
            context.state_repository.authorize_save_identity(
                LIVE_SAVE_ID, context.authenticated_slot
            )
            statuses: list[dict[str, object]] = []
            context.protocol = SimpleNamespace(
                set_ap_state_status=lambda **status: statuses.append(status)
            )
            receipt = CommandReceipt(
                4,
                ProtocolCommand.SET_TEST_TARGET,
                1,
                ProtocolResult.APPLIED,
                ProtocolError.NONE,
            )
            snapshot = BridgeSnapshot(
                save_loaded=True,
                native_save_slot=1,
                native_save_identity=LIVE_SAVE_ID,
                native_save_eligibility=SnapshotSaveEligibility.FRESH_UNPROGRESSED,
                session_nonce="game-session",
                recent_command_receipts=(receipt,),
            )

            context.sync_persistence(snapshot)

            self.assertIsNotNone(context.state_session)
            assert context.state_session is not None
            self.assertTrue(context.state_session.state.is_bound)
            self.assertEqual(
                statuses[-1],
                {
                    "loaded": True,
                    "bound": True,
                    "native_save_slot": 1,
                    "native_save_identity": LIVE_SAVE_ID,
                },
            )
            persisted = context.state_session.state.last_observed_game_command_receipt
            self.assertIsNotNone(persisted)
            assert persisted is not None
            self.assertEqual(persisted.command_id, "game-session:4")

            rejected = CommandReceipt(
                5,
                ProtocolCommand.TEST_ADDITIVE_EFFECT,
                1,
                ProtocolResult.FAILED,
                ProtocolError.ADDITIVE_EFFECT_FORBIDDEN,
            )
            context.sync_persistence(
                replace(snapshot, recent_command_receipts=(receipt, rejected))
            )
            persisted = context.state_session.state.last_observed_game_command_receipt
            assert persisted is not None
            self.assertEqual(persisted.command_id, "game-session:5")
            self.assertEqual(persisted.command_kind, "TEST_ADDITIVE_EFFECT")
            self.assertEqual(persisted.result, "FAILED")
            context.close_persistence(clean=True)

    def test_save_switch_and_copied_slot_are_rejected_read_only(self) -> None:
        with TemporaryDirectory() as directory:
            context = self.connected_context()
            context.authenticated_slot = self.authenticated_slot()
            context.state_repository = StateRepository(Path(directory))
            context.state_repository.authorize_save_identity(
                SWITCHED_SAVE_ID, context.authenticated_slot
            )
            snapshot = BridgeSnapshot(
                save_loaded=True,
                native_save_slot=0,
                native_save_identity=SWITCHED_SAVE_ID,
                native_save_eligibility=SnapshotSaveEligibility.FRESH_UNPROGRESSED,
            )
            context.sync_persistence(snapshot)
            self.assertIsNotNone(context.state_session)

            context.sync_persistence(
                replace(
                    snapshot,
                    native_save_slot=1,
                    native_save_eligibility=SnapshotSaveEligibility.INELIGIBLE,
                )
            )
            self.assertIsNone(context.state_session)
            self.assertEqual("refused read-only", context.persistence_binding_status)
            self.assertIn("slot 0", context.persistence_read_only_failure)

    def test_binding_open_switch_and_close_events_follow_live_sessions(self) -> None:
        with TemporaryDirectory() as directory:
            emitted: list[str] = []
            context = self.connected_context()
            context.diagnostics = SimpleNamespace(
                emit=lambda event_name, **_fields: emitted.append(event_name)
            )
            context.authenticated_slot = self.authenticated_slot()
            context.state_repository = StateRepository(Path(directory))
            for identity in (LIVE_SAVE_ID, SWITCHED_SAVE_ID):
                context.state_repository.authorize_save_identity(
                    identity, context.authenticated_slot
                )
            context.protocol = SimpleNamespace(
                set_ap_state_status=lambda **_status: None
            )
            first = BridgeSnapshot(
                save_loaded=True,
                native_save_slot=0,
                native_save_identity=LIVE_SAVE_ID,
                native_save_eligibility=SnapshotSaveEligibility.FRESH_UNPROGRESSED,
            )
            context.sync_persistence(first)
            context.sync_persistence(
                replace(
                    first,
                    native_save_slot=1,
                    native_save_identity=SWITCHED_SAVE_ID,
                )
            )
            context.close_persistence(clean=True)
            self.assertIn("binding.opened", emitted)
            self.assertIn("binding.switched", emitted)
            self.assertEqual(emitted.count("binding.closed"), 2)

    def test_failed_clean_close_is_reported_as_unclean(self) -> None:
        emitted: list[tuple[str, dict[str, object]]] = []
        context = self.connected_context()
        context.diagnostics = SimpleNamespace(
            emit=lambda event_name, **fields: emitted.append((event_name, fields))
        )

        def fail_close(*, clean: bool) -> None:
            self.assertTrue(clean)
            raise StateError("synthetic clean-close failure")

        context.state_session = SimpleNamespace(
            native_save=SimpleNamespace(identity=LIVE_SAVE_ID),
            state=SimpleNamespace(state_revision=7),
            close=fail_close,
        )
        context.protocol = SimpleNamespace(set_ap_state_status=lambda **_status: None)

        context.close_persistence(clean=True)

        closed = next(fields for name, fields in emitted if name == "binding.closed")
        self.assertEqual(closed["persistent_state_revision"], 7)
        self.assertEqual(closed["context"]["binding_state"], "unclean")
        self.assertEqual(context.persistence_binding_status, "refused read-only")

    def test_crashed_proposal_cannot_first_bind_after_ap_slot_switch(self) -> None:
        with TemporaryDirectory() as directory:
            context = self.connected_context()
            authorized_slot = self.authenticated_slot()
            context.state_repository = StateRepository(Path(directory))
            context.state_repository.authorize_save_identity(
                LIVE_SAVE_ID, authorized_slot
            )

            context.authenticated_slot = AuthenticatedSlot.from_connected_packet(
                build_slot_data(
                    SUPPORTED_FIRST_RELEASE_OPTIONS,
                    seed_identifier="different-authenticated-seed",
                ),
                team=authorized_slot.team,
                slot=authorized_slot.slot,
                slot_name=authorized_slot.slot_name,
            )
            context.sync_persistence(
                BridgeSnapshot(
                    save_loaded=True,
                    native_save_slot=1,
                    native_save_identity=LIVE_SAVE_ID,
                    native_save_eligibility=(
                        SnapshotSaveEligibility.FRESH_UNPROGRESSED
                    ),
                )
            )

            self.assertIsNone(context.state_session)
            self.assertEqual("refused read-only", context.persistence_binding_status)
            self.assertIn("different AP", context.persistence_read_only_failure)
            self.assertFalse(
                context.state_repository.paths_for(LIVE_SAVE_ID).primary.exists()
            )


if __name__ == "__main__":
    unittest.main()
