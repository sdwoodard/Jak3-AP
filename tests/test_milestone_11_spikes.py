import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest.mock import AsyncMock, patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPOSITORY_ROOT / "tools" / "run_milestone_11_spikes.py"


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m11_spikes", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()
EXPECTED_REVISIONS = TOOL.EXPECTED_REVISIONS
SOURCE_FILES = TOOL.SOURCE_FILES
SPIKES = TOOL.SPIKES
SpikeError = TOOL.SpikeError
audit_sources = TOOL.audit_sources
build_parser = TOOL.build_parser
bundle_run = TOOL.bundle_run
capture_checkpoint = TOOL.capture_checkpoint
evaluate_run = TOOL.evaluate_run
fallback_counts = TOOL.fallback_counts
fallback_versioning = TOOL.fallback_versioning
finish_run = TOOL.finish_run
load_state = TOOL.load_state
parse_assertions = TOOL.parse_assertions
parse_native_response = TOOL.parse_native_response
require_safe_artifact_path = TOOL.require_safe_artifact_path
review_run = TOOL.review_run
stage_run = TOOL.stage_run
start_run = TOOL.start_run


def snapshot_provenance(revision: int, slot: int) -> dict[str, object]:
    digest = hashlib.sha256(f"snapshot:{revision}:{slot}".encode()).hexdigest()
    return {
        "bridge_snapshot_sha256": digest,
        "bridge_snapshot_revision": revision,
        "bridge_snapshot_native_slot": slot,
        "bridge_snapshot_age_ms": 0,
    }


def attach_acceptance_provenance(run: Path) -> None:
    state_path, state = load_state(run)
    revision = 1
    uses: list[dict[str, object]] = []
    for checkpoint, record in state["checkpoints"].items():
        provenance = snapshot_provenance(revision, state["disposable_save_slot"])
        record["bridge_snapshot"] = provenance
        uses.append({**provenance, "boundary": f"capture:{checkpoint}"})
        revision += 1
    for preparation in state.get("preparations", []):
        provenance = snapshot_provenance(revision, state["disposable_save_slot"])
        preparation["bridge_snapshot"] = provenance
        uses.append({**provenance, "boundary": f"stage:{preparation['preset']}"})
        revision += 1
    state["bridge_snapshot_uses"] = uses
    TOOL.save_state(state_path, state)


class Milestone11SpikeTest(unittest.TestCase):
    def test_project_agent_loader_does_not_import_global_world_registry(self) -> None:
        existing_worlds = sys.modules.get("worlds")
        module = TOOL._load_project_agent_module("repl_client")
        self.assertEqual(
            Path(module.__file__).resolve(),
            REPOSITORY_ROOT / "worlds" / "jak3" / "agents" / "repl_client.py",
        )
        self.assertIs(sys.modules.get("worlds"), existing_worlds)
        with self.assertRaisesRegex(SpikeError, "not allowlisted"):
            TOOL._load_project_agent_module("client")

    def test_start_requires_disposable_slot_acknowledgement(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SpikeError, "acknowledgement"):
                start_run(
                    Path(directory),
                    "haven_task_35",
                    0,
                    acknowledged=False,
                )

    def test_reference_tree_artifact_paths_are_refused(self) -> None:
        with self.assertRaisesRegex(SpikeError, "reference tree"):
            require_safe_artifact_path(
                Path(__file__).resolve().parents[2] / "jak-project" / "evidence"
            )

    def test_terminal_pass_requires_provenance_and_is_immutable_after_finish(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "task_63_viewer",
                2,
                acknowledged=True,
            )
            for generation, (checkpoint, assertions) in enumerate(
                SPIKES["task_63_viewer"].items()
            ):
                expected_mask = 0 if checkpoint == "artifacts_clear" else 1984
                capture_checkpoint(
                    run,
                    checkpoint,
                    {name: "pass" for name in assertions},
                    {
                        "native_viewer_item_mask": expected_mask,
                        "native_viewer_scene_available": 1,
                        "native_viewer_scene_active": 1,
                        "native_actor_mask": 12,
                        "native_task_mask": 0,
                        "native_mission_mask": 0,
                        "native_reward_mask": 0,
                        "ap_relic_count": 0,
                        "ap_checked_mask": 0,
                    },
                    save_generation=generation,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            self.assertEqual(evaluate_run(load_state(run)[1]), ("pass", []))
            with self.assertRaisesRegex(SpikeError, "live bridge-snapshot provenance"):
                finish_run(run, "pass")
            attach_acceptance_provenance(run)
            status, reasons = finish_run(run)
            self.assertEqual((status, reasons), ("pass", []))
            with self.assertRaisesRegex(SpikeError, "started run"):
                capture_checkpoint(
                    run,
                    "artifacts_clear",
                    {},
                    {},
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )

    def test_checkpoint_recapture_requires_a_successor_correlation_id(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "task_63_viewer",
                2,
                acknowledged=True,
            )
            observations = {
                "native_viewer_item_mask": 0,
                "native_viewer_scene_available": 1,
                "native_viewer_scene_active": 1,
                "native_actor_mask": 12,
                "native_task_mask": 0,
                "native_mission_mask": 0,
                "native_reward_mask": 0,
                "ap_relic_count": 0,
                "ap_checked_mask": 0,
            }
            capture_checkpoint(
                run,
                "artifacts_clear",
                {name: "pass" for name in SPIKES["task_63_viewer"]["artifacts_clear"]},
                observations,
                save_generation=0,
                live=False,
                preset=None,
                mutation_acknowledged=False,
            )
            with self.assertRaisesRegex(SpikeError, "successor run"):
                capture_checkpoint(
                    run,
                    "artifacts_clear",
                    {
                        name: "pass"
                        for name in SPIKES["task_63_viewer"]["artifacts_clear"]
                    },
                    observations,
                    save_generation=1,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )

    def test_numeric_controls_override_contradictory_operator_passes(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "task_30_shadow",
                2,
                acknowledged=True,
            )
            for checkpoint, assertions in SPIKES["task_30_shadow"].items():
                capture_checkpoint(
                    run,
                    checkpoint,
                    {name: "pass" for name in assertions},
                    {
                        "native_task30_item_mask": 19,
                        "native_portal_present": 1,
                        "native_portal_open": 1,
                        "native_task30_node_closed": 1,
                        "ap_relic_count": 0,
                        "ap_checked_mask": 0,
                    },
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            _, state = load_state(run)
            status, reasons = evaluate_run(state)
            self.assertEqual(status, "blocked")
            self.assertIn("none/native_task30_item_mask=19 (expected 0)", reasons)
            with self.assertRaisesRegex(SpikeError, "PASS decision requires"):
                finish_run(run, "pass")

    def test_native_reconstruction_leak_cannot_be_called_pass(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "native_reconstruction",
                3,
                acknowledged=True,
            )
            observations = (
                ("before_save", 2015, 100, 7, 0),
                ("after_native_reload", 262143, 200, 7, 255),
                ("after_game_restart", 262143, 200, 7, 255),
                ("after_ap_reconcile", 262143, 200, 7, 255),
                ("after_item_replay", 262143, 200, 7, 255),
            )
            for (
                checkpoint,
                native_items,
                native_non_ap_features,
                native_target,
                checked,
            ) in observations:
                capture_checkpoint(
                    run,
                    checkpoint,
                    {
                        name: "pass"
                        for name in SPIKES["native_reconstruction"][checkpoint]
                    },
                    {
                        "native_items": native_items,
                        "native_features": native_non_ap_features + native_target,
                        "native_non_ap_feature_mask": native_non_ap_features,
                        "native_permanent_target_mask": native_target,
                        "native_reward_mask": native_items,
                        "native_task_mask": 0,
                        "native_mission_mask": 0,
                        "ap_inventory_mask": 1,
                        "ap_ledger_revision": 25,
                        "ap_checked_mask": checked,
                    },
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            with self.assertRaisesRegex(SpikeError, "PASS decision requires"):
                finish_run(run, "pass")
            status, reasons = finish_run(run)
            self.assertEqual(status, "blocked")
            self.assertTrue(any("native_items leaked" in reason for reason in reasons))
            _, state = load_state(run)
            self.assertEqual(state["evidence_status"], "pass")
            self.assertEqual(state["decision"], "BLOCKED")
            bundle_run(run)
            reviewed, _, _, _ = review_run(
                run,
                Path(directory) / "reviews",
                "release_blocking_reconstruction_leak",
            )
            _, reviewed_state = load_state(reviewed)
            self.assertEqual(reviewed_state["decision"], "BLOCKED")

    def test_native_reconstruction_review_rejects_an_incomplete_lifecycle(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = start_run(
                root / "source",
                "native_reconstruction",
                3,
                acknowledged=True,
            )
            finish_run(run)
            bundle_run(run)

            with self.assertRaisesRegex(
                SpikeError, "missing lifecycle checkpoint before_save"
            ):
                review_run(
                    run,
                    root / "reviews",
                    "release_blocking_reconstruction_leak",
                )

    def test_native_reconstruction_capture_rejects_missing_typed_fields(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "native_reconstruction",
                3,
                acknowledged=True,
            )
            with self.assertRaisesRegex(
                SpikeError, "omitted required typed observations"
            ):
                capture_checkpoint(
                    run,
                    "before_save",
                    {"targets_recorded": "pass"},
                    {"native_items": 2015},
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            self.assertEqual(load_state(run)[1]["checkpoints"], {})

    def test_native_reconstruction_derives_checksummed_ap_controls(self) -> None:
        with TemporaryDirectory() as directory:
            self.assertEqual(
                TOOL._canonical_json_bytes({"b": 2, "a": 1}),
                b'{"a":1,"b":2}\n',
            )
            root = Path(directory)
            snapshot = root / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "native_save_identity 56896cc5-e600-44d7-a859-82f4d45b68ba\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            payload = {
                "native_save_slot": 3,
                "native_save_identity": "56896cc5-e600-44d7-a859-82f4d45b68ba",
                "state_revision": 28,
                "received_item_counts": {
                    "743000108": 1,
                    "743000116": 2,
                    "743010016": 1,
                    "743012000": 2,
                },
                "checked_location_bits": [743001010, 743020036],
            }
            envelope = {
                "format": "jak3-ap-state",
                "checksum_algorithm": "sha256",
                "payload_sha256": hashlib.sha256(
                    TOOL._canonical_json_bytes(payload)
                ).hexdigest(),
                "payload": payload,
            }
            state = root / "state.json"
            state.write_bytes(TOOL._canonical_json_bytes(envelope))

            self.assertEqual(
                TOOL._ap_state_observations(
                    state, snapshot, expected_native_save_slot=3
                ),
                {
                    "ap_inventory_mask": 5,
                    "ap_ledger_revision": 28,
                    "ap_checked_mask": 129,
                    "ap_orb_pack_count": 2,
                    "ap_relic_count": 1,
                },
            )

            envelope["payload_sha256"] = "0" * 64
            state.write_bytes(TOOL._canonical_json_bytes(envelope))
            with self.assertRaisesRegex(SpikeError, "checksum does not match"):
                TOOL._ap_state_observations(
                    state, snapshot, expected_native_save_slot=3
                )

    def test_native_reconstruction_accepts_ledger_derived_repair(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "native_reconstruction",
                3,
                acknowledged=True,
            )
            observations = {
                "before_save": (2015, 100, 7),
                "after_native_reload": (262143, 200, 7),
                "after_game_restart": (2015, 100, 1),
                "after_ap_reconcile": (2015, 100, 1),
                "after_item_replay": (2015, 100, 1),
            }
            for generation, (checkpoint, values) in enumerate(observations.items()):
                native_items, non_ap_features, native_target = values
                capture_checkpoint(
                    run,
                    checkpoint,
                    {
                        name: "pass"
                        for name in SPIKES["native_reconstruction"][checkpoint]
                    },
                    {
                        "native_items": native_items,
                        "native_features": non_ap_features + native_target,
                        "native_non_ap_feature_mask": non_ap_features,
                        "native_permanent_target_mask": native_target,
                        "native_reward_mask": native_items,
                        "native_task_mask": 0,
                        "native_mission_mask": 0,
                        "ap_inventory_mask": 1,
                        "ap_ledger_revision": 25,
                        "ap_checked_mask": 0,
                    },
                    save_generation=generation,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            attach_acceptance_provenance(run)
            self.assertEqual(finish_run(run), ("pass", []))

    def test_native_reconstruction_detects_task_and_mission_leakage(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "native_reconstruction",
                3,
                acknowledged=True,
            )
            for generation, checkpoint in enumerate(SPIKES["native_reconstruction"]):
                leaked = checkpoint == "after_game_restart"
                capture_checkpoint(
                    run,
                    checkpoint,
                    {
                        name: "pass"
                        for name in SPIKES["native_reconstruction"][checkpoint]
                    },
                    {
                        "native_items": 7,
                        "native_features": 5,
                        "native_non_ap_feature_mask": 4,
                        "native_permanent_target_mask": 1,
                        "native_reward_mask": 7,
                        "native_task_mask": 1 if leaked else 0,
                        "native_mission_mask": 2 if leaked else 0,
                        "ap_inventory_mask": 1,
                        "ap_ledger_revision": 25,
                        "ap_checked_mask": 0,
                    },
                    save_generation=generation,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            status, reasons = finish_run(run)
            self.assertEqual(status, "blocked")
            self.assertIn(
                "after_game_restart/native_task_mask leaked: before=0, observed=1",
                reasons,
            )
            self.assertIn(
                "after_game_restart/native_mission_mask leaked: before=0, observed=2",
                reasons,
            )

    def test_only_machine_checked_haven_failure_can_select_fallback(self) -> None:
        self.assertNotIn("haven_task35_done34_fallback", TOOL.PRESET_FORMS)
        act_query = next(
            form for form in TOOL.NATIVE_QUERY_FORMS if "native_act=~D" in form
        )
        self.assertIn("(-> *ap-runtime* current-act)", act_query)
        self.assertNotIn(")) 2 1)", act_query)
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "haven_task_35",
                3,
                acknowledged=True,
            )
            common = {
                "native_task_mask": 0,
                "native_mission_mask": 0,
                "native_act": 1,
                "native_loaded_level_mask": 1,
                "native_actor_mask": 0,
                "native_items": 0,
                "native_reward_mask": 0,
                "ap_inventory_mask": 0,
                "ap_checked_mask": 0,
            }
            capture_checkpoint(
                run,
                "before_entry",
                {name: "pass" for name in SPIKES["haven_task_35"]["before_entry"]},
                common,
                save_generation=0,
                live=False,
                preset=None,
                mutation_acknowledged=False,
            )
            capture_checkpoint(
                run,
                "mission_start",
                {"geometry_playable": "pass", "required_actors_present": "fail"},
                common,
                save_generation=0,
                live=False,
                preset=None,
                mutation_acknowledged=False,
            )
            attach_acceptance_provenance(run)
            status, reasons = finish_run(run, "safe_fallback")
            self.assertEqual(status, "safe_fallback")
            self.assertTrue(
                any("required_actors_present=fail" in item for item in reasons)
            )
            _, state = load_state(run)
            self.assertEqual(state["fallback"]["implementation_milestones"], [18, 19])

    def test_haven_fallback_rejects_contradictory_actor_pass(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "haven_task_35",
                3,
                acknowledged=True,
            )
            common = {
                "native_task_mask": 0,
                "native_mission_mask": 0,
                "native_act": 2,
                "native_loaded_level_mask": 1,
                "native_actor_mask": 0,
                "native_items": 0,
                "native_reward_mask": 0,
                "ap_inventory_mask": 0,
                "ap_checked_mask": 0,
            }
            for checkpoint in ("before_entry", "mission_start"):
                capture_checkpoint(
                    run,
                    checkpoint,
                    {name: "pass" for name in SPIKES["haven_task_35"][checkpoint]},
                    common,
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            with self.assertRaisesRegex(SpikeError, "must agree"):
                finish_run(run, "safe_fallback")

    def test_haven_fallback_rejects_actor_mask_with_both_required_bits(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "haven_task_35",
                3,
                acknowledged=True,
            )
            common = {
                "native_task_mask": 0,
                "native_mission_mask": 0,
                "native_act": 2,
                "native_loaded_level_mask": 1,
                "native_actor_mask": 7,
                "native_items": 0,
                "native_reward_mask": 0,
                "ap_inventory_mask": 0,
                "ap_checked_mask": 0,
            }
            capture_checkpoint(
                run,
                "before_entry",
                {name: "pass" for name in SPIKES["haven_task_35"]["before_entry"]},
                common,
                save_generation=0,
                live=False,
                preset=None,
                mutation_acknowledged=False,
            )
            capture_checkpoint(
                run,
                "mission_start",
                {"geometry_playable": "pass", "required_actors_present": "fail"},
                common,
                save_generation=0,
                live=False,
                preset=None,
                mutation_acknowledged=False,
            )
            with self.assertRaisesRegex(SpikeError, "actors were present"):
                finish_run(run, "safe_fallback")

    def test_unimplemented_fallback_proofs_remain_blocked(self) -> None:
        with TemporaryDirectory() as directory:
            for spike in ("jetboard_launch", "orb_600"):
                run = start_run(
                    Path(directory) / spike,
                    spike,
                    3,
                    acknowledged=True,
                )
                with self.assertRaisesRegex(SpikeError, "no implemented positive"):
                    finish_run(run, "safe_fallback")

    def test_incomplete_matrix_finishes_blocked(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "orb_600",
                1,
                acknowledged=True,
            )
            _, state = load_state(run)
            self.assertEqual(evaluate_run(state)[0], "blocked")
            status, reasons = finish_run(run)
            self.assertEqual(status, "blocked")
            self.assertIn("missing checkpoint postgame_before", reasons)

    def test_orb_600_requires_every_source_family_at_600(self) -> None:
        def record_matrix(root: Path, include_families: bool) -> tuple[str, list[str]]:
            run = start_run(root, "orb_600", 3, acknowledged=True)
            for generation, checkpoint in enumerate(SPIKES["orb_600"]):
                observations = dict(TOOL.EXPECTED_OBSERVATIONS[("orb_600", checkpoint)])
                if checkpoint == "at_600" and include_families:
                    observations.update(
                        {
                            "orb_standalone_count": 300,
                            "orb_container_count": 150,
                            "orb_mission_reward_count": 100,
                            "orb_challenge_reward_count": 50,
                        }
                    )
                capture_checkpoint(
                    run,
                    checkpoint,
                    {name: "pass" for name in SPIKES["orb_600"][checkpoint]},
                    observations,
                    save_generation=generation,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            if include_families:
                attach_acceptance_provenance(run)
            return finish_run(run)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            status, reasons = record_matrix(root / "missing", False)
            self.assertEqual(status, "blocked")
            self.assertIn("at_600/orb_standalone_count=missing", reasons)
            self.assertEqual(record_matrix(root / "complete", True), ("pass", []))

    def test_live_orb_pack_count_is_derived_from_checksummed_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = start_run(root, "orb_600", 3, acknowledged=True)
            snapshot = root / "bridge.tmp"
            ap_state = root / "state.json"
            with self.assertRaisesRegex(SpikeError, "not supplied manually"):
                capture_checkpoint(
                    run,
                    "postgame_before",
                    {},
                    {"ap_orb_pack_count": 0},
                    save_generation=0,
                    live=True,
                    preset=None,
                    mutation_acknowledged=False,
                    bridge_snapshot=snapshot,
                    ap_state=ap_state,
                )

            async def live_capture(*args, **kwargs):
                del args
                kwargs["snapshot_provenance"].update(snapshot_provenance(1, 3))
                return {"native_hero_mode": 0, "native_postgame_complete": 1}

            with (
                patch.object(
                    TOOL,
                    "_live_capture",
                    new=AsyncMock(side_effect=live_capture),
                ),
                patch.object(
                    TOOL,
                    "_ap_state_observations",
                    return_value={
                        "ap_inventory_mask": 0,
                        "ap_ledger_revision": 9,
                        "ap_checked_mask": 0,
                        "ap_orb_pack_count": 0,
                    },
                ) as derive,
            ):
                record = capture_checkpoint(
                    run,
                    "postgame_before",
                    {name: "pass" for name in SPIKES["orb_600"]["postgame_before"]},
                    {},
                    save_generation=0,
                    live=True,
                    preset=None,
                    mutation_acknowledged=False,
                    bridge_snapshot=snapshot,
                    ap_state=ap_state,
                )
            self.assertEqual(record["observations"]["ap_orb_pack_count"], 0)
            derive.assert_called_once_with(
                ap_state,
                snapshot,
                expected_native_save_slot=3,
            )

    def test_live_haven_and_side_capture_derive_checksummed_ap_controls(
        self,
    ) -> None:
        cases = (
            (
                "haven_task_35",
                "before_entry",
                {
                    "native_task_mask": 0,
                    "native_mission_mask": 0,
                    "native_act": 0,
                    "native_actor_mask": 0,
                    "native_items": 0,
                    "native_loaded_level_mask": 7,
                    "native_reward_mask": 0,
                },
                {"ap_checked_mask": 3, "ap_inventory_mask": 5},
                "ap_inventory_mask",
            ),
            (
                "side_challenges",
                "zero_cost_before",
                {
                    **TOOL.EXPECTED_OBSERVATIONS[
                        ("side_challenges", "zero_cost_before")
                    ],
                    "native_purchase_secrets": 0,
                },
                {"ap_checked_mask": 3, "ap_relic_count": 2},
                "ap_relic_count",
            ),
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (spike, checkpoint, native, expected, manual_field) in enumerate(
                cases,
                start=1,
            ):
                with self.subTest(spike=spike):
                    run = start_run(root / spike, spike, 3, acknowledged=True)
                    snapshot = root / f"{spike}.tmp"
                    ap_state = root / f"{spike}-state.json"
                    assertions = {name: "pass" for name in SPIKES[spike][checkpoint]}

                    with self.assertRaisesRegex(SpikeError, "requires --ap-state"):
                        capture_checkpoint(
                            run,
                            checkpoint,
                            assertions,
                            {},
                            save_generation=0,
                            live=True,
                            preset=None,
                            mutation_acknowledged=False,
                            bridge_snapshot=snapshot,
                        )
                    self.assertEqual(load_state(run)[1]["checkpoints"], {})

                    with self.assertRaisesRegex(SpikeError, "not supplied manually"):
                        capture_checkpoint(
                            run,
                            checkpoint,
                            assertions,
                            {manual_field: expected[manual_field]},
                            save_generation=0,
                            live=True,
                            preset=None,
                            mutation_acknowledged=False,
                            bridge_snapshot=snapshot,
                            ap_state=ap_state,
                        )
                    self.assertEqual(load_state(run)[1]["checkpoints"], {})

                    async def live_capture(*args, **kwargs):
                        del args
                        kwargs["snapshot_provenance"].update(
                            snapshot_provenance(index, 3)
                        )
                        return native

                    state_observations = {
                        "ap_inventory_mask": 5,
                        "ap_ledger_revision": 9,
                        "ap_checked_mask": 3,
                        "ap_orb_pack_count": 0,
                        "ap_relic_count": 2,
                    }
                    with (
                        patch.object(
                            TOOL,
                            "_live_capture",
                            new=AsyncMock(side_effect=live_capture),
                        ),
                        patch.object(
                            TOOL,
                            "_ap_state_observations",
                            return_value=state_observations,
                        ) as derive,
                    ):
                        record = capture_checkpoint(
                            run,
                            checkpoint,
                            assertions,
                            {},
                            save_generation=0,
                            live=True,
                            preset=None,
                            mutation_acknowledged=False,
                            bridge_snapshot=snapshot,
                            ap_state=ap_state,
                        )
                    for field, value in expected.items():
                        self.assertEqual(record["observations"][field], value)
                    derive.assert_called_once_with(
                        ap_state,
                        snapshot,
                        expected_native_save_slot=3,
                    )

    def test_live_shadow_capture_derives_checksummed_ap_controls(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = start_run(root, "task_30_shadow", 3, acknowledged=True)
            snapshot = root / "bridge.tmp"
            ap_state = root / "state.json"
            procedure_assertions = {
                name: "pass" for name in SPIKES["task_30_shadow"]["none"]
            }

            with self.assertRaisesRegex(
                SpikeError, "omitted required procedure assertions"
            ):
                capture_checkpoint(
                    run,
                    "none",
                    {"portal_observed": "pass"},
                    {},
                    save_generation=0,
                    live=True,
                    preset="task30_none",
                    mutation_acknowledged=True,
                    bridge_snapshot=snapshot,
                    ap_state=ap_state,
                )
            self.assertEqual(load_state(run)[1]["checkpoints"], {})

            with self.assertRaisesRegex(SpikeError, "requires --ap-state"):
                capture_checkpoint(
                    run,
                    "none",
                    procedure_assertions,
                    {},
                    save_generation=0,
                    live=True,
                    preset="task30_none",
                    mutation_acknowledged=True,
                    bridge_snapshot=snapshot,
                )
            self.assertEqual(load_state(run)[1]["checkpoints"], {})

            async def live_capture(*args, **kwargs):
                del args
                kwargs["snapshot_provenance"].update(snapshot_provenance(1, 3))
                return dict(TOOL.EXPECTED_OBSERVATIONS[("task_30_shadow", "none")])

            with (
                patch.object(
                    TOOL,
                    "_live_capture",
                    new=AsyncMock(side_effect=live_capture),
                ),
                patch.object(
                    TOOL,
                    "_ap_state_observations",
                    return_value={
                        "ap_inventory_mask": 0,
                        "ap_ledger_revision": 9,
                        "ap_checked_mask": 0,
                        "ap_orb_pack_count": 0,
                        "ap_relic_count": 0,
                    },
                ) as derive,
            ):
                record = capture_checkpoint(
                    run,
                    "none",
                    procedure_assertions,
                    {},
                    save_generation=0,
                    live=True,
                    preset="task30_none",
                    mutation_acknowledged=True,
                    bridge_snapshot=snapshot,
                    ap_state=ap_state,
                )
            self.assertEqual(record["observations"]["ap_checked_mask"], 0)
            self.assertEqual(record["observations"]["ap_relic_count"], 0)
            derive.assert_called_once_with(
                ap_state,
                snapshot,
                expected_native_save_slot=3,
            )

    def test_shadow_spikes_reject_native_task_mission_or_reward_leakage(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for spike in ("task_30_shadow", "task_63_viewer"):
                run = start_run(root / spike, spike, 3, acknowledged=True)
                for checkpoint, assertions in SPIKES[spike].items():
                    observations = dict(TOOL.EXPECTED_OBSERVATIONS[(spike, checkpoint)])
                    observations.update({"ap_relic_count": 0, "ap_checked_mask": 0})
                    if checkpoint == next(iter(SPIKES[spike])):
                        observations["native_mission_mask"] = 1
                    capture_checkpoint(
                        run,
                        checkpoint,
                        {name: "pass" for name in assertions},
                        observations,
                        save_generation=0,
                        live=False,
                        preset=None,
                        mutation_acknowledged=False,
                    )
                status, reasons = finish_run(run)
                self.assertEqual(status, "blocked")
                self.assertTrue(
                    any(
                        "native_mission_mask=1 (expected 0)" in item for item in reasons
                    )
                )

    def test_preset_requires_live_matching_checkpoint_and_acknowledgement(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "jetboard_launch",
                0,
                acknowledged=True,
            )
            with self.assertRaisesRegex(SpikeError, "requires --live"):
                capture_checkpoint(
                    run,
                    "base_only",
                    {},
                    {},
                    save_generation=0,
                    live=False,
                    preset="jetboard_base_only",
                    mutation_acknowledged=True,
                )

    def test_task30_scene_staging_precedes_source_exact_activation(self) -> None:
        stage = TOOL.PRESET_FORMS["task30_scene_stage"][2]
        activate = TOOL.PRESET_FORMS["task30_scene_activate"][2]

        self.assertIn("task30_scene_stage", TOOL.CLEAN_START_STAGE_PRESETS)
        self.assertIn('get-continue-by-name *game-info* "templea-mardoor"', stage)
        self.assertIn("send-event *target* 'continue", stage)
        self.assertNotIn("task-node-close!", stage)
        self.assertNotIn("game-task-node-info-method-11", stage)
        self.assertIn('task-node-by-name "temple-tests-introduction"', activate)
        self.assertIn("logior! (-> node flags) (game-task-node-flag closed)", activate)
        self.assertNotIn("task-node-close!", activate)
        self.assertNotIn("task-close!", activate)
        self.assertIn('process-by-name "tpl-mardoor-4" *active-pool*', activate)
        self.assertIn("send-event door 'open", activate)
        self.assertNotIn("game-info* items", stage + activate)

    def test_task63_uses_stable_forest_staging_and_scene_owned_actor_handles(
        self,
    ) -> None:
        clear_stage = TOOL.PRESET_FORMS["task63_clear_scene_stage"][2]
        set_stage = TOOL.PRESET_FORMS["task63_set_scene_stage"][2]
        clear_intro_stage = TOOL.PRESET_FORMS["task63_clear_intro_stage"][2]
        set_intro_stage = TOOL.PRESET_FORMS["task63_set_intro_stage"][2]
        clear = TOOL.PRESET_FORMS["task63_clear"][2]
        artifact_set = TOOL.PRESET_FORMS["task63_set"][2]
        active_artifact_set = TOOL.PRESET_FORMS["task63_set_active_capture"][2]
        actor_query = next(
            form for form in TOOL.NATIVE_QUERY_FORMS if "viewer-active" in form
        )

        for stage in (clear_stage, set_stage):
            self.assertIn(
                'get-continue-by-name *game-info* "forest-pillar-start"', stage
            )
            self.assertIn("send-event *target* 'continue", stage)
            self.assertNotIn("scene-player", stage)
        for stage in (clear_intro_stage, set_intro_stage):
            self.assertIn("(play-clean #f)", stage)
            self.assertIn(
                'get-continue-by-name *game-info* "forest-pillar-start"', stage
            )
            self.assertIn("(start 'play", stage)
            self.assertNotIn("scene-player", stage)
        for activation in (clear, artifact_set):
            self.assertIn('"forest-turn-on-machine-res"', activation)
            self.assertIn("when (not *scene-player*)", activation)
            self.assertIn("(none)", activation)
            self.assertNotIn("play-clean", activation)
            self.assertNotIn("task-close!", activation)
            self.assertNotIn("debug-menu-scene-play", activation)
        self.assertIn("logior! (-> *game-info* items)", active_artifact_set)
        self.assertIn("artifact-av-map", active_artifact_set)
        self.assertNotIn("scene-player", active_artifact_set)
        self.assertNotIn("play-clean", active_artifact_set)
        self.assertIn("task63_set_active_capture", TOOL.CAPTURE_ONLY_PRESETS)
        self.assertNotIn("task63_clear_cleanup", TOOL.PRESET_FORMS)
        self.assertNotIn("task63_set_cleanup", TOOL.PRESET_FORMS)
        self.assertIn('"for-telescope-fma"', actor_query)
        self.assertIn('"time-map"', actor_query)
        self.assertIn("(-> *ap-runtime* in-cutscene)", actor_query)
        self.assertIn("handle->process (-> actor process)", actor_query)
        self.assertIn("native_viewer_scene_available=~D", actor_query)
        self.assertIn("native_viewer_scene_active=~D", actor_query)
        self.assertEqual(
            TOOL.EXPECTED_OBSERVATIONS[("task_63_viewer", "artifacts_clear")],
            {
                "native_task_mask": 0,
                "native_mission_mask": 0,
                "native_reward_mask": 0,
                "native_viewer_item_mask": 0,
                "native_viewer_scene_available": 1,
                "native_viewer_scene_active": 1,
                "native_actor_mask": 12,
            },
        )
        self.assertEqual(
            TOOL.EXPECTED_OBSERVATIONS[("task_63_viewer", "artifacts_set")],
            {
                "native_task_mask": 0,
                "native_mission_mask": 0,
                "native_reward_mask": 0,
                "native_viewer_item_mask": 1984,
                "native_viewer_scene_available": 1,
                "native_viewer_scene_active": 1,
                "native_actor_mask": 12,
            },
        )

    def test_task63_active_set_preset_cannot_be_used_as_a_stage(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "task_63_viewer",
                2,
                acknowledged=True,
            )
            with self.assertRaisesRegex(SpikeError, "capture-only"):
                stage_run(
                    run,
                    "task63_set_active_capture",
                    mutation_acknowledged=True,
                )

    def test_jetboard_uses_permanent_safe_controls_then_clean_task30_relocation(
        self,
    ) -> None:
        self.assertEqual(
            TOOL.JETBOARD_FEATURE_STAGE_PRESETS,
            {
                "jetboard_00",
                "jetboard_base_only",
                "jetboard_base_launch",
                "jetboard_launch_only",
            },
        )
        relocation = TOOL.PRESET_FORMS["jetboard_task30_scene_stage"][2]
        self.assertIn("jetboard_task30_scene_stage", TOOL.CLEAN_START_STAGE_PRESETS)
        self.assertIn("(play-clean #f)", relocation)
        self.assertIn('get-continue-by-name *game-info* "templec-start"', relocation)
        self.assertIn("(start 'play", relocation)
        self.assertNotIn("task-node-by-name", relocation)
        self.assertNotIn("game-task-node-info-method-11", relocation)
        restore = TOOL.PRESET_FORMS["jetboard_restore_reconciliation"][2]
        self.assertEqual(
            TOOL.JETBOARD_RECONCILIATION_RESTORE_PRESETS,
            {"jetboard_restore_reconciliation"},
        )
        self.assertIn("ap-rewards-permanent-item-reconciliation-suspended?", restore)
        self.assertNotIn("noop-reconciliation", restore)
        self.assertIn("jetboard_restore_reconciliation", TOOL.STAGE_ONLY_PRESETS)

    def test_side_challenge_uses_exact_clean_start_relocation_and_typed_cost(
        self,
    ) -> None:
        intro = TOOL.PRESET_FORMS["side_zero_cost_desb4_intro_stage"][2]
        activate = TOOL.PRESET_FORMS["side_zero_cost_desb4_activate_stage"][2]
        refresh = TOOL.PRESET_FORMS["side_zero_cost_desb4_refresh_stage"][2]
        suppress = TOOL.PRESET_FORMS[
            "side_zero_cost_desb4_suppress_parent_reward_stage"
        ][2]
        cost = TOOL.PRESET_FORMS["side_zero_cost_desb4"][2]

        self.assertIn("(play-clean #f)", intro)
        self.assertIn('get-continue-by-name *game-info* "desert-bbush-desb-4"', intro)
        self.assertIn("(start 'play", intro)
        self.assertNotIn("burning-bush-desb-4", intro)
        self.assertNotIn("purchase-secrets", intro)
        self.assertIn(
            "side_zero_cost_desb4_intro_stage", TOOL.CLEAN_START_STAGE_PRESETS
        )
        self.assertIn("haven_task35_hub_candidate", TOOL.CLEAN_START_STAGE_PRESETS)
        self.assertIn("(game-task-icon gaticon-00)", cost)
        self.assertNotIn("(set! (-> event tex) 0)", cost)
        self.assertIn("search-process-tree", cost)
        self.assertIn("type? candidate des-burning-bush", cost)
        self.assertIn("game-task-actor burning-bush-desb-4", cost)
        self.assertNotIn("process-by-name", cost)
        self.assertIn("(if raw", cost)
        self.assertIn("side_marker_available=0", cost)
        self.assertIn("side_zero_cost_desb4", TOOL.CAPTURE_ONLY_PRESETS)
        self.assertIn(
            "side_zero_cost_desb4_activate_stage", TOOL.SIDE_MARKER_STAGE_PRESETS
        )
        self.assertIn(
            "side_zero_cost_desb4_refresh_stage", TOOL.SIDE_MARKER_STAGE_PRESETS
        )
        self.assertIn(
            "side_zero_cost_desb4_suppress_parent_reward_stage",
            TOOL.SIDE_MARKER_STAGE_PRESETS,
        )
        self.assertIn("side_zero_cost_desb4_stage", TOOL.SIDE_MARKER_STAGE_PRESETS)
        self.assertIn(
            "side_observe_desb4_after",
            TOOL.SIDE_CHALLENGE_ACTIVE_CAPTURE_PRESETS,
        )
        self.assertNotIn(
            "side_observe_desb4_reload",
            TOOL.SIDE_CHALLENGE_ACTIVE_CAPTURE_PRESETS,
        )
        self.assertIn(
            "side_observe_desb4_reload",
            TOOL.SIDE_CHALLENGE_RELOAD_CAPTURE_PRESETS,
        )
        self.assertIn("courses_observe_reload", TOOL.CAPTURE_ONLY_PRESETS)
        self.assertEqual(
            TOOL.PRESET_FORMS["courses_observe_reload"][:2],
            ("side_challenges", "courses_shadow_reload"),
        )
        self.assertIn('"desert-beast-battle-resolution"', activate)
        self.assertIn('"desert-bbush-destroy-interceptors-introduction"', activate)
        self.assertIn("game-task-node-flag closed", activate)
        self.assertIn("game-task-node-info-method-11 intro 'event", activate)
        self.assertNotIn("eval-game-task-cmd!", activate)
        self.assertNotIn("task-node-close!", activate)
        self.assertIn("task-counter", refresh)
        self.assertNotIn("update-task-masks", refresh)
        self.assertNotIn("eval-game-task-cmd!", refresh)
        self.assertIn("command-index) #x3a", suppress)
        self.assertIn("command-count) 1", suppress)
        self.assertIn("artifact-av-reflector", suppress)
        self.assertIn("(set! (-> parent command-count) 0)", suppress)
        self.assertNotIn("eval-game-task-cmd!", suppress)
        self.assertIn("side_marker_desb4", TOOL.READ_ONLY_PROBE_FORMS)
        probe = TOOL.READ_ONLY_PROBE_FORMS["side_marker_desb4"]
        self.assertIn("search-process-tree", probe)
        self.assertIn("type? candidate des-burning-bush", probe)
        self.assertNotIn("process-by-name", probe)
        self.assertIn("side_parent_shadow_closed=~D", probe)
        self.assertIn("side_parent_command_suppressed=~D", probe)
        self.assertIn("side_intro_node_open=~D", probe)
        self.assertIn("game-task-node-info-method-12 intro", probe)
        self.assertEqual(
            TOOL.EXPECTED_OBSERVATIONS[("side_challenges", "zero_cost_before")][
                "side_marker_available"
            ],
            1,
        )
        self.assertEqual(
            TOOL.EXPECTED_OBSERVATIONS[("side_challenges", "zero_cost_before")][
                "side_event_resolved"
            ],
            1,
        )
        self.assertEqual(
            TOOL.EXPECTED_OBSERVATIONS[("side_challenges", "zero_cost_after")][
                "native_items"
            ],
            0,
        )

    def test_live_stage_rejects_compiler_error_from_managed_log(self) -> None:
        self.assertEqual(
            TOOL._repl_failure_marker("prefix REPL Error: Compilation Error"),
            "REPL Error:",
        )
        self.assertEqual(
            TOOL._repl_failure_marker("[GK] [ERROR] call_method_of_type failed!"),
            "call_method_of_type failed!",
        )

        class FailingRepl:
            def __init__(self) -> None:
                self.connected = False

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                raise AssertionError("reuse-attached-target must skip attach")

            async def send_form(self, form: str) -> str:
                del form
                with live_log.open("a", encoding="utf-8") as stream:
                    stream.write("-- Compilation Error! --\n")
                return "nREPL"

            async def close(self) -> None:
                self.connected = False

        fake_module = ModuleType("failing_repl_client")
        fake_module.OpenGoalRepl = FailingRepl
        with TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "safe_to_apply_permanent_item 1\n"
                "safe_to_mutate_mission_state 1\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            live_log = root / "managed.log"
            live_log.write_text("", encoding="utf-8")
            with patch.object(
                TOOL, "_load_project_agent_module", return_value=fake_module
            ):
                with self.assertRaisesRegex(
                    SpikeError, "rejected restricted preset.*Compilation Error"
                ):
                    asyncio.run(
                        TOOL._live_stage(
                            "task30_scene_activate",
                            snapshot,
                            live_log,
                            reuse_attached_target=True,
                            expected_native_save_slot=2,
                        )
                    )

    def test_live_stage_rejects_delayed_runtime_pointer_error(self) -> None:
        class FailingRepl:
            def __init__(self) -> None:
                self.connected = False

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                raise AssertionError("reuse-attached-target must skip attach")

            async def send_form(self, form: str) -> str:
                del form

                async def append_error() -> None:
                    await asyncio.sleep(0.1)
                    with live_log.open("a", encoding="utf-8") as stream:
                        stream.write("has invalid type ptr\n")

                asyncio.create_task(append_error())
                return "nREPL"

            async def close(self) -> None:
                self.connected = False

        fake_module = ModuleType("failing_repl_client")
        fake_module.OpenGoalRepl = FailingRepl
        with TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "safe_to_apply_permanent_item 1\n"
                "safe_to_mutate_mission_state 1\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            live_log = root / "managed.log"
            live_log.write_text("", encoding="utf-8")
            with patch.object(
                TOOL, "_load_project_agent_module", return_value=fake_module
            ):
                with self.assertRaisesRegex(
                    SpikeError, "rejected restricted preset.*invalid type ptr"
                ):
                    asyncio.run(
                        TOOL._live_stage(
                            "task63_clear",
                            snapshot,
                            live_log,
                            reuse_attached_target=True,
                            expected_native_save_slot=2,
                        )
                    )

    def test_live_capture_rejects_error_appended_after_complete_fields(self) -> None:
        class DelayedFailureRepl:
            scheduled = False

            def __init__(self) -> None:
                self.connected = False

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                return None

            async def send_form(self, form: str) -> str:
                del form
                if not self.__class__.scheduled:
                    self.__class__.scheduled = True
                    values = " ".join(
                        f"{field}=0" for field in sorted(TOOL.NATIVE_QUERY_FIELDS)
                    )
                    with live_log.open("a", encoding="utf-8") as stream:
                        stream.write(f"M11_STATE {values}\n")

                    async def append_error() -> None:
                        await asyncio.sleep(0.05)
                        with live_log.open("a", encoding="utf-8") as stream:
                            stream.write("has invalid type ptr\n")

                    asyncio.create_task(append_error())
                return "nREPL"

            async def close(self) -> None:
                self.connected = False

        fake_module = ModuleType("delayed_capture_repl_client")
        fake_module.OpenGoalRepl = DelayedFailureRepl
        with TemporaryDirectory() as directory:
            root = Path(directory)
            live_log = root / "managed.log"
            live_log.write_text("", encoding="utf-8")
            snapshot = root / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "native_save_slot 2\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            with (
                patch.object(
                    TOOL, "_load_project_agent_module", return_value=fake_module
                ),
                patch.object(TOOL, "LIVE_STAGE_SETTLE_SECONDS", 0.2),
            ):
                with self.assertRaisesRegex(
                    SpikeError, "rejected restricted capture.*invalid type ptr"
                ):
                    asyncio.run(
                        TOOL._live_capture(
                            None,
                            live_log,
                            snapshot,
                            expected_native_save_slot=2,
                        )
                    )

    def test_live_probe_rejects_error_appended_after_complete_fields(self) -> None:
        class DelayedFailureRepl:
            def __init__(self) -> None:
                self.connected = False

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                raise AssertionError("reuse-attached-target must skip attach")

            async def send_form(self, form: str) -> str:
                del form
                values = " ".join(
                    f"{field}=0"
                    for field in (
                        "side_marker_available",
                        "side_event_resolved",
                        "side_displayed_cost",
                        "side_activation_flag",
                        "side_parent_shadow_closed",
                        "side_parent_command_suppressed",
                        "side_intro_node_closed",
                        "side_intro_node_open",
                        "side_resolution_node_closed",
                    )
                )
                with live_log.open("a", encoding="utf-8") as stream:
                    stream.write(f"M11_STATE {values}\n")

                async def append_error() -> None:
                    await asyncio.sleep(0.05)
                    with live_log.open("a", encoding="utf-8") as stream:
                        stream.write("call_method_of_type failed!\n")

                asyncio.create_task(append_error())
                return "nREPL"

            async def close(self) -> None:
                self.connected = False

        fake_module = ModuleType("delayed_probe_repl_client")
        fake_module.OpenGoalRepl = DelayedFailureRepl
        with TemporaryDirectory() as directory:
            root = Path(directory)
            live_log = root / "managed.log"
            snapshot = root / "bridge.tmp"
            live_log.write_text("", encoding="utf-8")
            snapshot.write_text("snapshot_begin 1\nsnapshot_end 1\n", encoding="utf-8")
            with (
                patch.object(
                    TOOL, "_load_project_agent_module", return_value=fake_module
                ),
                patch.object(TOOL, "_validate_live_bridge_snapshot"),
                patch.object(TOOL, "LIVE_STAGE_SETTLE_SECONDS", 0.2),
            ):
                with self.assertRaisesRegex(
                    SpikeError, "rejected restricted probe.*call_method_of_type"
                ):
                    asyncio.run(
                        TOOL._live_probe(
                            "side_marker_desb4",
                            snapshot,
                            live_log,
                            reuse_attached_target=True,
                            expected_native_save_slot=2,
                        )
                    )

    def test_task63_capture_requires_active_cutscene_boundary(self) -> None:
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "current_level foresta\n"
                "current_task -1\n"
                "current_task_node -1\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 1\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "permanent_item_native_target_mask 0\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=2,
                require_task63_scene_capture=True,
            )
            with self.assertRaisesRegex(SpikeError, "run-owned native save slot"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    require_task63_scene_capture=True,
                )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "native_save_slot 2", "native_save_slot 3"
                ),
                encoding="utf-8",
            )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=3,
                require_task63_scene_capture=True,
            )
            with self.assertRaisesRegex(SpikeError, "run requires 2"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=2,
                    require_task63_scene_capture=True,
                )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8")
                .replace("native_save_slot 3", "native_save_slot 2")
                .replace("in_cutscene 1", "in_cutscene 0"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "in_cutscene=1, got 0"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=2,
                    require_task63_scene_capture=True,
                )

    def test_permanent_item_boundary_allows_an_unambiguous_active_mission(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 3\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "current_task 10\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "safe_to_apply_permanent_item 1\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=3,
                require_permanent_item_safe=True,
            )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8")
                .replace(
                    "safe_to_apply_permanent_item 1",
                    "safe_to_apply_permanent_item 0",
                )
                .replace(
                    "safe_to_mutate_mission_state 0",
                    "permanent_item_native_target_mask -1\n"
                    "safe_to_mutate_mission_state 0",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "safe_to_apply_permanent_item=1"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=3,
                    require_permanent_item_safe=True,
                )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=3,
                require_permanent_item_safe=True,
                allow_suspended_permanent_item=True,
            )
            with self.assertRaisesRegex(SpikeError, "only for a permanent-item"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=3,
                    allow_suspended_permanent_item=True,
                )

    def test_restore_reconciliation_routes_through_the_suspended_boundary(
        self,
    ) -> None:
        instances = []

        class FakeRepl:
            def __init__(self) -> None:
                self.connected = False
                self.forms = []
                instances.append(self)

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                raise AssertionError("reuse-attached-target must skip attach")

            async def send_form(self, form: str) -> str:
                self.forms.append(form)
                return "nREPL"

            async def close(self) -> None:
                self.connected = False

        fake_module = ModuleType("fake_repl_client")
        fake_module.OpenGoalRepl = FakeRepl
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text("unused", encoding="utf-8")
            with patch.object(
                TOOL, "_load_project_agent_module", return_value=fake_module
            ):
                with patch.object(
                    TOOL,
                    "_validate_live_bridge_snapshot",
                    return_value=snapshot_provenance(7, 3),
                ) as validate:
                    asyncio.run(
                        TOOL._live_stage(
                            "jetboard_restore_reconciliation",
                            snapshot,
                            reuse_attached_target=True,
                            expected_native_save_slot=3,
                        )
                    )
        validate.assert_called_once_with(
            snapshot,
            expected_native_save_slot=3,
            require_mutation_safe=False,
            require_permanent_item_safe=True,
            allow_suspended_permanent_item=True,
            require_clean_start_stage=False,
            require_side_marker_capture=False,
        )
        self.assertEqual(
            instances[0].forms,
            [TOOL.PRESET_FORMS["jetboard_restore_reconciliation"][2]],
        )

    def test_side_marker_probe_requires_exact_paused_desert_boundary(self) -> None:
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "current_level desert\n"
                "current_task -1\n"
                "current_task_node -1\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "permanent_item_native_target_mask 0\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=2,
                require_side_marker_capture=True,
            )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "current_level desert", "current_level desrace1"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "current_level=desert"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=2,
                    require_side_marker_capture=True,
                )

    def test_active_side_challenge_requires_exact_task_137_boundary(self) -> None:
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "current_level desert\n"
                "current_task 137\n"
                "current_task_node 409\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "permanent_item_native_target_mask 0\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=2,
                require_side_challenge_active_capture=True,
            )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "current_task_node 409", "current_task_node 410"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "current_task_node=409, got 410"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=2,
                    require_side_challenge_active_capture=True,
                )

    def test_reloaded_side_challenge_allows_native_continue_vehicle_state(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "current_level desert\n"
                "current_task 7\n"
                "current_task_node 4\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 1\n"
                "permanent_item_native_target_mask 7\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=2,
                require_side_challenge_reload_capture=True,
            )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "current_level desert", "current_level wasall"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "current_level=desert"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=2,
                    require_side_challenge_reload_capture=True,
                )

    def test_course_capture_allows_loaded_vehicle_but_rejects_loading(self) -> None:
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 1\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            TOOL._validate_live_bridge_snapshot(
                snapshot,
                expected_native_save_slot=2,
                require_course_capture=True,
            )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace("loading 0", "loading 1"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "loading=1"):
                TOOL._validate_live_bridge_snapshot(
                    snapshot,
                    expected_native_save_slot=2,
                    require_course_capture=True,
                )

    def test_side_course_controls_require_unchanged_ap_and_purchase_state(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "side_challenges",
                2,
                acknowledged=True,
            )
            for checkpoint, assertions in SPIKES["side_challenges"].items():
                expected = dict(
                    TOOL.EXPECTED_OBSERVATIONS.get(("side_challenges", checkpoint), {})
                )
                expected.update(
                    {
                        "ap_checked_mask": 255,
                        "ap_relic_count": 0,
                        "native_purchase_secrets": 0,
                    }
                )
                capture_checkpoint(
                    run,
                    checkpoint,
                    {name: "pass" for name in assertions},
                    expected,
                    save_generation=1 if "reload" in checkpoint else 0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            status, reasons = evaluate_run(load_state(run)[1])
            self.assertEqual((status, reasons), ("pass", []))

            path, state = load_state(run)
            state["checkpoints"]["courses_shadow_reload"]["observations"][
                "native_purchase_secrets"
            ] = 1
            TOOL.save_state(path, state)
            status, reasons = evaluate_run(load_state(run)[1])
            self.assertEqual(status, "blocked")
            self.assertTrue(
                any("native_purchase_secrets changed" in reason for reason in reasons)
            )

    def test_task63_intro_stage_requires_exact_clean_start(self) -> None:
        class IntroStageRepl:
            async def connect(self) -> None:
                pass

            async def attach(self) -> None:
                raise AssertionError("reuse-attached-target must skip attach")

            async def send_form(self, form: str) -> str:
                self.form = form
                return "nREPL"

            async def close(self) -> None:
                pass

        fake_module = ModuleType("intro_stage_repl_client")
        fake_module.OpenGoalRepl = IntroStageRepl
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "current_level wasstada\n"
                "current_act 1\n"
                "current_task 10\n"
                "current_task_node 8\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "permanent_item_native_target_mask 0\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            with patch.object(
                TOOL, "_load_project_agent_module", return_value=fake_module
            ):
                asyncio.run(
                    TOOL._live_stage(
                        "task63_clear_intro_stage",
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=2,
                    )
                )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "current_task 10", "current_task 11"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "current_task=10, got 11"):
                asyncio.run(
                    TOOL._live_stage(
                        "task63_clear_intro_stage",
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=2,
                    )
                )

            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "current_task 11", "current_task 10"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "run requires 3"):
                asyncio.run(
                    TOOL._live_stage(
                        "task63_clear_intro_stage",
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=3,
                    )
                )

    def test_staging_is_restricted_to_the_run_spike_and_recorded(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "jetboard_launch",
                0,
                acknowledged=True,
            )
            with self.assertRaisesRegex(SpikeError, "acknowledgement"):
                stage_run(
                    run,
                    "jetboard_base_only",
                    mutation_acknowledged=False,
                )
            with self.assertRaisesRegex(SpikeError, "does not match"):
                stage_run(
                    run,
                    "task30_none",
                    mutation_acknowledged=True,
                )
            with patch.object(
                TOOL,
                "_live_stage",
                new=AsyncMock(return_value=snapshot_provenance(7, 0)),
            ) as live_stage:
                snapshot = Path(directory) / "bridge.tmp"
                stage_run(
                    run,
                    "jetboard_base_only",
                    mutation_acknowledged=True,
                    bridge_snapshot=snapshot,
                )
            live_stage.assert_awaited_once_with(
                "jetboard_base_only",
                snapshot,
                None,
                reuse_attached_target=False,
                expected_native_save_slot=0,
                used_snapshot_keys=frozenset(),
            )
            _, state = load_state(run)
            self.assertEqual(state["preparations"][0]["preset"], "jetboard_base_only")
            with self.assertRaisesRegex(SpikeError, "does not match"):
                capture_checkpoint(
                    run,
                    "00",
                    {},
                    {},
                    save_generation=0,
                    live=True,
                    preset="jetboard_base_only",
                    mutation_acknowledged=True,
                    bridge_snapshot=snapshot,
                )

            async def live_capture_result(*args, **kwargs):
                del args
                kwargs["snapshot_provenance"].update(snapshot_provenance(8, 0))
                return {"native_jetboard_mask": 1}

            with patch.object(
                TOOL,
                "_live_capture",
                new=AsyncMock(side_effect=live_capture_result),
            ) as live_capture:
                capture_checkpoint(
                    run,
                    "base_only",
                    {
                        "base_present": "pass",
                        "launch_absent": "pass",
                        "charged_launch_absent": "pass",
                    },
                    {},
                    save_generation=0,
                    live=True,
                    preset="jetboard_base_only",
                    mutation_acknowledged=True,
                    bridge_snapshot=snapshot,
                )
            self.assertTrue(
                live_capture.await_args.kwargs["allow_pre_staged_permanent_item"]
            )
            _, state = load_state(run)
            self.assertEqual(len(state["bridge_snapshot_uses"]), 2)
            self.assertEqual(
                state["preparations"][0]["bridge_snapshot"],
                snapshot_provenance(7, 0),
            )
            self.assertEqual(
                state["checkpoints"]["base_only"]["bridge_snapshot"],
                snapshot_provenance(8, 0),
            )
            with self.assertRaisesRegex(SpikeError, "stage-only"):
                capture_checkpoint(
                    run,
                    "after_save_load",
                    {},
                    {},
                    save_generation=1,
                    live=True,
                    preset="jetboard_restore_reconciliation",
                    mutation_acknowledged=True,
                    bridge_snapshot=snapshot,
                )

    def test_side_challenge_initialization_requires_exact_stage_order(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "side_challenges",
                2,
                acknowledged=True,
            )
            snapshot = Path(directory) / "bridge.tmp"
            with patch.object(
                TOOL,
                "_live_stage",
                new=AsyncMock(
                    side_effect=[
                        snapshot_provenance(revision, 2) for revision in range(10, 15)
                    ]
                ),
            ) as live_stage:
                with self.assertRaisesRegex(
                    SpikeError,
                    "requires side_zero_cost_desb4_intro_stage next",
                ):
                    stage_run(
                        run,
                        "side_zero_cost_desb4_refresh_stage",
                        mutation_acknowledged=True,
                        bridge_snapshot=snapshot,
                    )
                for preset in TOOL.SIDE_CHALLENGE_INITIALIZATION_ORDER:
                    stage_run(
                        run,
                        preset,
                        mutation_acknowledged=True,
                        bridge_snapshot=snapshot,
                    )
                with self.assertRaisesRegex(SpikeError, "exact unfinished prefix"):
                    stage_run(
                        run,
                        "side_zero_cost_desb4_refresh_stage",
                        mutation_acknowledged=True,
                        bridge_snapshot=snapshot,
                    )
            self.assertEqual(live_stage.await_count, 5)
            _, state = load_state(run)
            self.assertEqual(
                [entry["preset"] for entry in state["preparations"]],
                list(TOOL.SIDE_CHALLENGE_INITIALIZATION_ORDER),
            )

    def test_every_live_target_requires_snapshot_and_reuse_only_skips_attach(
        self,
    ) -> None:
        with self.assertRaisesRegex(SpikeError, "fresh, run-owned"):
            asyncio.run(
                TOOL._live_stage(
                    "jetboard_base_only",
                    reuse_attached_target=True,
                    expected_native_save_slot=2,
                )
            )
        with self.assertRaisesRegex(SpikeError, "fresh, run-owned"):
            asyncio.run(
                TOOL._live_stage(
                    "jetboard_base_only",
                    reuse_attached_target=False,
                    expected_native_save_slot=2,
                )
            )
        with self.assertRaisesRegex(SpikeError, "fresh, run-owned"):
            asyncio.run(
                TOOL._live_capture(
                    "jetboard_base_only",
                    None,
                    reuse_attached_target=False,
                    expected_native_save_slot=2,
                )
            )

        instances = []

        class FakeRepl:
            def __init__(self) -> None:
                self.connected = False
                self.attach_calls = 0
                self.forms = []
                instances.append(self)

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                self.attach_calls += 1

            async def send_form(self, form: str) -> None:
                self.forms.append(form)

            async def close(self) -> None:
                self.connected = False

        fake_module = ModuleType("fake_repl_client")
        fake_module.OpenGoalRepl = FakeRepl
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(
                "snapshot_begin 7\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "safe_to_apply_permanent_item 1\n"
                "safe_to_mutate_mission_state 0\n"
                "snapshot_end 7\n",
                encoding="utf-8",
            )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "dying_or_dead 0", "dying_or_dead 1"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SpikeError, "unsafe for .*staging"):
                asyncio.run(
                    TOOL._live_stage(
                        "jetboard_base_only",
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=2,
                    )
                )
            live_log = Path(directory) / "managed.log"
            live_log.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(SpikeError, "unsafe for .*staging"):
                asyncio.run(
                    TOOL._live_capture(
                        "jetboard_base_only",
                        live_log,
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=2,
                    )
                )
            with self.assertRaisesRegex(SpikeError, "unsafe for .*staging"):
                asyncio.run(
                    TOOL._live_capture(
                        "jetboard_base_only",
                        live_log,
                        snapshot,
                        reuse_attached_target=False,
                        expected_native_save_slot=2,
                    )
                )
            snapshot.write_text(
                snapshot.read_text(encoding="utf-8").replace(
                    "dying_or_dead 1", "dying_or_dead 0"
                ),
                encoding="utf-8",
            )
            with patch.object(
                TOOL, "_load_project_agent_module", return_value=fake_module
            ):
                asyncio.run(
                    TOOL._live_stage(
                        "jetboard_base_only",
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=2,
                    )
                )
                asyncio.run(
                    TOOL._live_stage(
                        "jetboard_base_only",
                        snapshot,
                        reuse_attached_target=False,
                        expected_native_save_slot=2,
                    )
                )
        self.assertEqual(instances[0].attach_calls, 0)
        self.assertEqual(
            instances[0].forms, [TOOL.PRESET_FORMS["jetboard_base_only"][2]]
        )
        self.assertEqual(instances[1].attach_calls, 1)

    def test_jetboard_live_capture_suspends_then_restores_reconciliation(
        self,
    ) -> None:
        instances = []

        class FakeRepl:
            def __init__(self) -> None:
                self.connected = False
                self.forms = []
                self.test_target = 0
                self.revision = 7
                instances.append(self)

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                raise AssertionError("reuse-attached-target must skip attach")

            async def send_form(self, form: str, timeout: float = 10.0) -> str:
                del timeout
                self.forms.append(form)
                if "test-target) (+" in form:
                    self.test_target = 1
                elif form == "(set! (-> *ap-runtime* test-target) 0)":
                    self.test_target = 0
                elif form == "(ap-export-state!)":
                    self.revision += 1
                    snapshot.write_text(
                        bridge_snapshot(self.revision, self.test_target),
                        encoding="utf-8",
                    )
                return "nREPL"

            async def close(self) -> None:
                self.connected = False

        def bridge_snapshot(revision: int, test_target: int) -> str:
            return (
                f"snapshot_begin {revision}\n"
                "connection_ready 1\n"
                "game_running 1\n"
                "source_loaded 1\n"
                "save_loaded 1\n"
                "native_save_slot 2\n"
                "ap_state_loaded 1\n"
                "ap_state_bound 1\n"
                "at_title_menu 0\n"
                "loading 0\n"
                "in_cutscene 0\n"
                "dying_or_dead 0\n"
                "mission_restarting 0\n"
                "level_transition 0\n"
                "in_vehicle 0\n"
                "safe_to_apply_permanent_item 1\n"
                "safe_to_mutate_mission_state 0\n"
                f"test_target {test_target}\n"
                f"snapshot_end {revision}\n"
            )

        fake_module = ModuleType("fake_repl_client")
        fake_module.OpenGoalRepl = FakeRepl
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "bridge.tmp"
            snapshot.write_text(bridge_snapshot(7, 0), encoding="utf-8")
            with patch.object(
                TOOL, "_load_project_agent_module", return_value=fake_module
            ):
                observations = asyncio.run(
                    TOOL._live_capture(
                        "jetboard_base_only",
                        None,
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=2,
                    )
                )

        self.assertEqual(observations, {"native_jetboard_mask": 1})
        self.assertIn(
            "ap3-permanent-items-noop-reconciliation-suspended?",
            TOOL.PRESET_FORMS["jetboard_base_only"][2],
        )
        restore = (
            "(set! *ap3-permanent-items-reconciliation-suspended-hook* "
            "ap-rewards-permanent-item-reconciliation-suspended?)"
        )
        self.assertIn(restore, instances[0].forms)
        self.assertLess(
            instances[0].forms.index(restore),
            len(instances[0].forms) - 1,
        )

    def test_clean_start_capture_uses_slot_bound_relocation_validation(self) -> None:
        class FakeRepl:
            def __init__(self) -> None:
                self.connected = False

            async def connect(self) -> None:
                self.connected = True

            async def attach(self) -> None:
                raise AssertionError("reuse-attached-target must skip attach")

            async def send_form(self, form: str) -> str:
                del form
                values = " ".join(
                    f"{field}=0" for field in sorted(TOOL.NATIVE_QUERY_FIELDS)
                )
                with live_log.open("a", encoding="utf-8") as stream:
                    stream.write(f"M11_STATE {values}\n")
                return "nREPL"

            async def close(self) -> None:
                self.connected = False

        fake_module = ModuleType("clean_start_capture_repl_client")
        fake_module.OpenGoalRepl = FakeRepl
        with TemporaryDirectory() as directory:
            root = Path(directory)
            live_log = root / "managed.log"
            snapshot = root / "bridge.tmp"
            live_log.write_text("", encoding="utf-8")
            snapshot.write_text("snapshot_begin 1\nsnapshot_end 1\n", encoding="utf-8")
            with (
                patch.object(
                    TOOL, "_load_project_agent_module", return_value=fake_module
                ),
                patch.object(
                    TOOL,
                    "_validate_live_bridge_snapshot",
                    return_value=snapshot_provenance(1, 3),
                ) as validate,
            ):
                asyncio.run(
                    TOOL._live_capture(
                        "haven_task35_hub_candidate",
                        live_log,
                        snapshot,
                        reuse_attached_target=True,
                        expected_native_save_slot=3,
                    )
                )

        validate.assert_called_once()
        self.assertEqual(validate.call_args.kwargs["expected_native_save_slot"], 3)
        self.assertFalse(validate.call_args.kwargs["require_mutation_safe"])
        self.assertTrue(validate.call_args.kwargs["require_clean_start_stage"])

    def test_assertion_and_native_response_parsing_are_bounded(self) -> None:
        self.assertEqual(
            parse_assertions(["base_present=pass", "launch_absent=fail"]),
            {"base_present": "pass", "launch_absent": "fail"},
        )
        response = (
            "compiler output\nM11_STATE native_features=262144 "
            "native_skill_total=600.0 native_gems=0.0 "
            "side_previous_cost=8 side_displayed_cost=0\nnREPL"
        )
        self.assertEqual(
            parse_native_response(response),
            {
                "native_features": 262144,
                "native_skill_total": 600.0,
                "native_gems": 0.0,
                "side_previous_cost": 8,
                "side_displayed_cost": 0,
            },
        )
        with self.assertRaisesRegex(SpikeError, "allowlisted"):
            parse_native_response("M11_STATE password=secret\nnREPL")
        self.assertEqual(
            TOOL._bridge_snapshot_value(
                "snapshot_begin 8\ntest_target 2\nsnapshot_end 8\n",
                "test_target",
            ),
            2,
        )
        with self.assertRaisesRegex(SpikeError, "omitted test_target"):
            TOOL._bridge_snapshot_value("snapshot_begin 8\n", "test_target")

    def test_every_observation_field_is_diagnostic_allowlisted(self) -> None:
        diagnostics = TOOL._load_project_agent_module("diagnostics")
        context_fields = diagnostics.EVENT_REGISTRY[
            "feasibility.spike.checkpoint"
        ].context_fields
        self.assertLessEqual(TOOL.OBSERVATION_FIELDS, context_fields)
        self.assertLessEqual(
            {
                "bridge_snapshot_sha256",
                "bridge_snapshot_revision",
                "bridge_snapshot_native_slot",
                "bridge_snapshot_age_ms",
            },
            context_fields,
        )

    def test_no_arbitrary_goal_form_option_exists(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(
                [
                    "capture",
                    "--run",
                    "run",
                    "--checkpoint",
                    "00",
                    "--form",
                    "(shutdown)",
                ]
            )

    def test_stage_cli_requires_bridge_snapshot(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(
                [
                    "stage",
                    "--run",
                    "run",
                    "--preset",
                    "jetboard_base_only",
                    "--acknowledge-live-mutation",
                ]
            )

    def test_source_audit_rejects_anchor_drift(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            jak_project = root / "jak-project"
            archipelago = root / "Archipelago"
            decompile = root / "openGOAL-decompile"
            for relative, anchors in SOURCE_FILES.items():
                payload = "\n".join(anchors) + "\n"
                primary = jak_project / "goal_src" / "jak3" / relative
                snapshot = decompile / "jak3" / "data" / "goal_src" / "jak3" / relative
                primary.parent.mkdir(parents=True, exist_ok=True)
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                primary.write_text(payload, encoding="utf-8")
                snapshot.write_text(payload, encoding="utf-8")
            broken = jak_project / "goal_src" / "jak3" / next(iter(SOURCE_FILES))
            broken.write_text("missing anchors\n", encoding="utf-8")
            with patch.object(
                TOOL,
                "_git_revision",
                side_effect=[
                    EXPECTED_REVISIONS["jak-project"],
                    EXPECTED_REVISIONS["Archipelago"],
                ],
            ):
                with self.assertRaisesRegex(SpikeError, "anchors missing"):
                    audit_sources(jak_project, archipelago, decompile)

    def test_fallback_arithmetic_conserves_the_pool(self) -> None:
        self.assertIn("after_restart", SPIKES["jetboard_launch"])
        self.assertEqual(
            TOOL.EXPECTED_OBSERVATIONS[("jetboard_launch", "after_restart")],
            {"native_jetboard_mask": 3},
        )
        self.assertEqual(
            fallback_counts(600, launch_retired=False),
            {
                "orb_thresholds": 24,
                "locations": 147,
                "progression": 26,
                "useful": 28,
                "filler": 93,
            },
        )
        self.assertEqual(fallback_counts(324, launch_retired=True)["filler"], 82)
        with self.assertRaisesRegex(SpikeError, "between 0 and 600"):
            fallback_counts(601, launch_retired=False)

        orb_fallback = fallback_versioning(324, launch_retired=False)
        self.assertEqual(orb_fallback["location_table_version_bump"], 1)
        self.assertEqual(orb_fallback["item_table_version_bump"], 0)
        self.assertTrue(orb_fallback["location_table_hash_required"])
        self.assertTrue(orb_fallback["reject_older_development_state"])

        launch_fallback = fallback_versioning(600, launch_retired=True)
        self.assertEqual(launch_fallback["item_table_version_bump"], 1)
        self.assertEqual(launch_fallback["location_table_version_bump"], 0)
        self.assertTrue(launch_fallback["resolved_options_hash_required"])
        self.assertEqual(launch_fallback["slot_data_version_bump"], 1)

    def test_blocked_run_bundle_has_a_reproducible_hash(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory),
                "native_reconstruction",
                3,
                acknowledged=True,
            )
            finish_run(run)
            bundle, digest, status = bundle_run(run)
            self.assertTrue(bundle.is_file())
            self.assertEqual(len(digest), 64)
            self.assertIn(status, {"complete", "partial"})
            state_path, state = load_state(run)
            self.assertEqual(state["bundle"]["sha256"], digest)
            self.assertEqual(
                json.loads(state_path.read_text("utf-8"))["bundle"]["name"],
                bundle.name,
            )
            with self.assertRaisesRegex(SpikeError, "Finalize the run exactly once"):
                bundle_run(run)

    def test_superseded_review_preserves_source_and_records_hash(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = start_run(
                root / "source",
                "task_30_shadow",
                2,
                acknowledged=True,
            )
            source_state_path, _ = load_state(source)
            finish_run(source)
            bundle_run(source)
            source_before = source_state_path.read_bytes()
            run, bundle, digest, status = review_run(
                source,
                root / "reviews",
                "invalid_task30_numeric_control",
            )
            self.assertEqual(source_state_path.read_bytes(), source_before)
            self.assertTrue(bundle.is_file())
            self.assertEqual(len(digest), 64)
            self.assertIn(status, {"complete", "partial"})
            _, state = load_state(run)
            self.assertEqual(state["decision"], "BLOCKED")
            self.assertEqual(
                state["reviewed_source"]["run_sha256"],
                TOOL.sha256_file(source_state_path),
            )

    def test_haven_review_rejects_an_incomplete_source_matrix(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = start_run(
                root / "source",
                "haven_task_35",
                3,
                acknowledged=True,
            )
            finish_run(source)
            bundle_run(source)

            with self.assertRaisesRegex(
                SpikeError, "before_entry and mission_start checkpoints"
            ):
                review_run(
                    source,
                    root / "reviews",
                    "predefined_haven_fallback",
                )

    def test_jetboard_review_requires_and_accepts_the_complete_matrix(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = start_run(
                root / "source",
                "jetboard_launch",
                2,
                acknowledged=True,
            )
            for generation, checkpoint in enumerate(SPIKES["jetboard_launch"]):
                expected = TOOL.EXPECTED_OBSERVATIONS[("jetboard_launch", checkpoint)][
                    "native_jetboard_mask"
                ]
                capture_checkpoint(
                    source,
                    checkpoint,
                    {name: "pass" for name in SPIKES["jetboard_launch"][checkpoint]},
                    {"native_jetboard_mask": expected},
                    save_generation=generation,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            attach_acceptance_provenance(source)
            self.assertEqual(finish_run(source)[0], "pass")
            bundle_run(source)
            source_state_path, _ = load_state(source)
            source_before = source_state_path.read_bytes()

            run, bundle, digest, status = review_run(
                source,
                root / "reviews",
                "jetboard_semantics_proven",
            )

            self.assertEqual(source_state_path.read_bytes(), source_before)
            self.assertTrue(bundle.is_file())
            self.assertEqual(len(digest), 64)
            self.assertEqual(status, "complete")
            _, state = load_state(run)
            self.assertEqual(state["decision"], "PASS")
            self.assertEqual(state["decision_scope"], "jetboard_launch")
            self.assertEqual(state["blockers"], [])
            self.assertEqual(
                state["bridge_snapshot_uses"],
                load_state(source)[1]["bridge_snapshot_uses"],
            )

    def test_positive_review_rejects_legacy_source_without_provenance(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = start_run(root / "source", "jetboard_launch", 2, acknowledged=True)
            for generation, checkpoint in enumerate(SPIKES["jetboard_launch"]):
                expected = TOOL.EXPECTED_OBSERVATIONS[("jetboard_launch", checkpoint)][
                    "native_jetboard_mask"
                ]
                capture_checkpoint(
                    source,
                    checkpoint,
                    {name: "pass" for name in SPIKES["jetboard_launch"][checkpoint]},
                    {"native_jetboard_mask": expected},
                    save_generation=generation,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            state_path, state = load_state(source)
            state.update(
                {
                    "status": "pass",
                    "evidence_status": "pass",
                    "decision": "PASS",
                    "bundle": {"status": "complete"},
                }
            )
            TOOL.save_state(state_path, state)

            with self.assertRaisesRegex(
                SpikeError, "complete live acceptance provenance"
            ):
                review_run(
                    source,
                    root / "reviews",
                    "jetboard_semantics_proven",
                )

    def test_jetboard_review_rejects_failed_persistence_assertions_and_masks(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = start_run(
                root / "source",
                "jetboard_launch",
                2,
                acknowledged=True,
            )
            for checkpoint in SPIKES["jetboard_launch"]:
                persistence = checkpoint in TOOL.JETBOARD_PERSISTENCE_CHECKPOINTS
                expected = TOOL.EXPECTED_OBSERVATIONS[("jetboard_launch", checkpoint)][
                    "native_jetboard_mask"
                ]
                capture_checkpoint(
                    source,
                    checkpoint,
                    {
                        name: "fail" if persistence else "pass"
                        for name in SPIKES["jetboard_launch"][checkpoint]
                    },
                    {"native_jetboard_mask": 0 if persistence else expected},
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            self.assertEqual(finish_run(source)[0], "blocked")
            bundle_run(source)

            with self.assertRaisesRegex(
                SpikeError, "after_save_load/launch_reconstructed=fail"
            ):
                review_run(
                    source,
                    root / "reviews",
                    "jetboard_semantics_proven",
                )

    def test_jetboard_semantics_review_rejects_an_inexact_control(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = start_run(
                root / "source",
                "jetboard_launch",
                2,
                acknowledged=True,
            )
            for checkpoint in SPIKES["jetboard_launch"]:
                expected = TOOL.EXPECTED_OBSERVATIONS[("jetboard_launch", checkpoint)][
                    "native_jetboard_mask"
                ]
                capture_checkpoint(
                    source,
                    checkpoint,
                    {name: "pass" for name in SPIKES["jetboard_launch"][checkpoint]},
                    {"native_jetboard_mask": expected},
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            state_path, state = load_state(source)
            state["checkpoints"]["launch_only"]["observations"][
                "native_jetboard_mask"
            ] = 3
            TOOL.save_state(state_path, state)
            finish_run(source)
            bundle_run(source)

            with self.assertRaisesRegex(
                SpikeError, "launch_only/native_jetboard_mask=3"
            ):
                review_run(
                    source,
                    root / "reviews",
                    "jetboard_semantics_proven",
                )

    def test_native_task_mission_and_reward_queries_are_independent(self) -> None:
        task_query = next(
            form
            for form in TOOL.NATIVE_QUERY_FORMS
            if "native_task_mask=~D native_mission_mask=~D" in form
        )
        self.assertIn("(dotimes (i 59)", task_query)
        self.assertTrue(
            any(
                "task-perm-list" in anchor
                for anchor in SOURCE_FILES["engine/game/game-info-h.gc"]
            )
        )
        self.assertIn("task-mask", task_query)
        self.assertIn("mission-mask", task_query)
        self.assertIn("sub-task-list", task_query)
        self.assertIn("game-task-node-flag close-task", task_query)
        self.assertNotIn("mask mask", task_query)

        reward_query = next(
            form
            for form in TOOL.NATIVE_QUERY_FORMS
            if "M11_STATE native_reward_mask=~D" in form
        )
        self.assertEqual(reward_query.count("task-node-closed?"), 10)
        self.assertNotIn("(-> *game-info* items)", reward_query)
        actor_query = next(
            form for form in TOOL.NATIVE_QUERY_FORMS if "native_actor_mask=~D" in form
        )
        self.assertNotIn("native_reward_mask", actor_query)

    def test_legacy_item_aliased_reward_masks_cannot_pass_shadow_spikes(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(Path(directory), "task_30_shadow", 3, acknowledged=True)
            for checkpoint, assertions in SPIKES["task_30_shadow"].items():
                observations = dict(
                    TOOL.EXPECTED_OBSERVATIONS[("task_30_shadow", checkpoint)]
                )
                observations.update({"ap_relic_count": 0, "ap_checked_mask": 0})
                observations["native_reward_mask"] = observations[
                    "native_task30_item_mask"
                ]
                capture_checkpoint(
                    run,
                    checkpoint,
                    {name: "pass" for name in assertions},
                    observations,
                    save_generation=0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            status, reasons = finish_run(run)
            self.assertEqual(status, "blocked")
            self.assertTrue(
                any("seal_only/native_reward_mask=16" in reason for reason in reasons)
            )

    def test_consumed_snapshot_is_rejected_before_live_stage_or_capture(
        self,
    ) -> None:
        class NeverConnectedRepl:
            def __init__(self) -> None:
                raise AssertionError("duplicate snapshot must fail before REPL use")

        fake_module = ModuleType("duplicate_snapshot_repl_client")
        fake_module.OpenGoalRepl = NeverConnectedRepl
        provenance = snapshot_provenance(11, 3)
        used = frozenset({TOOL._snapshot_provenance_key(provenance)})
        with TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "bridge.tmp"
            live_log = root / "managed.log"
            snapshot.write_text("unused", encoding="utf-8")
            live_log.write_text("", encoding="utf-8")
            with (
                patch.object(
                    TOOL, "_load_project_agent_module", return_value=fake_module
                ),
                patch.object(
                    TOOL,
                    "_validate_live_bridge_snapshot",
                    return_value=provenance,
                ),
            ):
                with self.assertRaisesRegex(SpikeError, "already consumed"):
                    asyncio.run(
                        TOOL._live_stage(
                            "jetboard_base_only",
                            snapshot,
                            reuse_attached_target=True,
                            expected_native_save_slot=3,
                            used_snapshot_keys=used,
                        )
                    )
                with self.assertRaisesRegex(SpikeError, "already consumed"):
                    asyncio.run(
                        TOOL._live_capture(
                            None,
                            live_log,
                            snapshot,
                            reuse_attached_target=True,
                            expected_native_save_slot=3,
                            used_snapshot_keys=used,
                        )
                    )

    def test_finish_is_pending_until_a_complete_bundle_exists(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(
                Path(directory), "native_reconstruction", 3, acknowledged=True
            )
            self.assertEqual(finish_run(run)[0], "blocked")
            _, pending = load_state(run)
            self.assertEqual(pending["status"], TOOL.FINALIZED_PENDING_BUNDLE)
            bundle_run(run)
            _, terminal = load_state(run)
            self.assertEqual(terminal["status"], "blocked")
            self.assertEqual(terminal["bundle"]["status"], "complete")

    def test_partial_bundle_never_becomes_terminal_evidence(self) -> None:
        class PartialSession:
            def __init__(self, bundle: Path) -> None:
                self.bundle = bundle

            def register_context_provider(self, *args) -> None:
                del args

            def emit(self, *args, **kwargs) -> None:
                del args, kwargs

            def export_bundle(self):
                self.bundle.write_bytes(b"partial")
                return type(
                    "Result",
                    (),
                    {"path": self.bundle, "status": "partial", "error": None},
                )()

            def close(self, *, clean: bool) -> None:
                del clean

        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = start_run(root, "native_reconstruction", 3, acknowledged=True)
            finish_run(run)
            session = PartialSession(root / "partial.zip")
            with patch.object(TOOL, "_diagnostic_session", return_value=session):
                _, _, status = bundle_run(run)
            self.assertEqual(status, "partial")
            _, state = load_state(run)
            self.assertEqual(state["status"], TOOL.BUNDLE_INCOMPLETE)
            with self.assertRaisesRegex(SpikeError, "Finalize the run exactly once"):
                bundle_run(run)

    def test_orb_source_families_must_be_integral_nonnegative_and_total_600(
        self,
    ) -> None:
        cases = {
            "all_zero": ([0, 0, 0, 0], "source_family_total=0"),
            "negative": ([-1, 151, 300, 150], "expected 0..600"),
            "fractional": ([300.0, 150, 100, 50], "expected integer count"),
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, (values, expected_reason) in cases.items():
                with self.subTest(name=name):
                    run = start_run(root / name, "orb_600", 3, acknowledged=True)
                    for generation, checkpoint in enumerate(SPIKES["orb_600"]):
                        observations = dict(
                            TOOL.EXPECTED_OBSERVATIONS[("orb_600", checkpoint)]
                        )
                        if checkpoint == "at_600":
                            observations.update(
                                dict(zip(TOOL.ORB_SOURCE_FAMILY_FIELDS, values))
                            )
                        capture_checkpoint(
                            run,
                            checkpoint,
                            {
                                assertion: "pass"
                                for assertion in SPIKES["orb_600"][checkpoint]
                            },
                            observations,
                            save_generation=generation,
                            live=False,
                            preset=None,
                            mutation_acknowledged=False,
                        )
                    status, reasons = finish_run(run)
                    self.assertEqual(status, "blocked")
                    self.assertTrue(
                        any(expected_reason in reason for reason in reasons), reasons
                    )

    def test_side_reload_requires_zero_cost_resource_and_ap_controls(self) -> None:
        with TemporaryDirectory() as directory:
            run = start_run(Path(directory), "side_challenges", 2, acknowledged=True)
            for checkpoint, assertions in SPIKES["side_challenges"].items():
                observations = dict(
                    TOOL.EXPECTED_OBSERVATIONS.get(("side_challenges", checkpoint), {})
                )
                observations.update(
                    {
                        "ap_checked_mask": 255,
                        "ap_relic_count": 0,
                        "native_purchase_secrets": 0,
                    }
                )
                if checkpoint == "zero_cost_reload":
                    observations.pop("native_reward_mask")
                capture_checkpoint(
                    run,
                    checkpoint,
                    {name: "pass" for name in assertions},
                    observations,
                    save_generation=1 if "reload" in checkpoint else 0,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            status, reasons = finish_run(run)
            self.assertEqual(status, "blocked")
            self.assertIn(
                "zero_cost_reload/native_reward_mask=missing (expected 32)", reasons
            )

    def test_live_capture_persists_then_stops_on_automatic_observation_blocker(
        self,
    ) -> None:
        captures = [
            dict(TOOL.EXPECTED_OBSERVATIONS[("side_challenges", "zero_cost_before")]),
            {
                **TOOL.EXPECTED_OBSERVATIONS[("side_challenges", "zero_cost_after")],
                "native_items": 243803,
                "native_reward_mask": 7,
            },
        ]
        capture_index = 0

        async def fake_live_capture(*args, **kwargs):
            nonlocal capture_index
            snapshot_provenance = kwargs["snapshot_provenance"]
            capture_index += 1
            snapshot_provenance.update(
                {
                    "bridge_snapshot_sha256": f"{capture_index:064x}",
                    "bridge_snapshot_revision": capture_index,
                    "bridge_snapshot_native_slot": 2,
                    "bridge_snapshot_age_ms": 10,
                }
            )
            return {
                **captures[capture_index - 1],
                "native_purchase_secrets": 0,
            }

        ap_observations = [
            {"ap_checked_mask": 0, "ap_relic_count": 0},
            {"ap_checked_mask": 255, "ap_relic_count": 0},
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = start_run(root, "side_challenges", 2, acknowledged=True)
            bridge = root / "bridge.tmp"
            ap_state = root / "state.json"
            with (
                patch.object(TOOL, "_live_capture", side_effect=fake_live_capture),
                patch.object(
                    TOOL,
                    "_ap_state_observations",
                    side_effect=ap_observations,
                ),
            ):
                capture_checkpoint(
                    run,
                    "zero_cost_before",
                    {
                        name: "pass"
                        for name in SPIKES["side_challenges"]["zero_cost_before"]
                    },
                    {},
                    save_generation=0,
                    live=True,
                    preset=None,
                    mutation_acknowledged=False,
                    bridge_snapshot=bridge,
                    ap_state=ap_state,
                )
                with self.assertRaisesRegex(
                    SpikeError, "preserved as BLOCKED evidence"
                ):
                    capture_checkpoint(
                        run,
                        "zero_cost_after",
                        {
                            name: "pass"
                            for name in SPIKES["side_challenges"]["zero_cost_after"]
                        },
                        {},
                        save_generation=0,
                        live=True,
                        preset=None,
                        mutation_acknowledged=False,
                        bridge_snapshot=bridge,
                        ap_state=ap_state,
                    )

            _, state = load_state(run)
            record = state["checkpoints"]["zero_cost_after"]
            self.assertEqual(record["automatic_validation"]["status"], "blocked")
            reasons = record["automatic_validation"]["reasons"]
            self.assertIn("zero_cost_after/native_items=243803 (expected 0)", reasons)
            self.assertIn(
                "ap_checked_mask changed across checkpoints: [0, 255]", reasons
            )
            self.assertEqual(state["events"][-4]["context"]["status"], "blocked")

    def test_reconstruction_review_rejects_a_clean_typed_lifecycle(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = start_run(
                root / "source", "native_reconstruction", 3, acknowledged=True
            )
            observations = {
                "native_items": 7,
                "native_features": 5,
                "native_non_ap_feature_mask": 4,
                "native_permanent_target_mask": 1,
                "native_reward_mask": 7,
                "native_task_mask": 0,
                "native_mission_mask": 0,
                "ap_inventory_mask": 1,
                "ap_ledger_revision": 25,
                "ap_checked_mask": 0,
            }
            for generation, (checkpoint, assertions) in enumerate(
                SPIKES["native_reconstruction"].items()
            ):
                capture_checkpoint(
                    source,
                    checkpoint,
                    {name: "pass" for name in assertions},
                    observations,
                    save_generation=generation,
                    live=False,
                    preset=None,
                    mutation_acknowledged=False,
                )
            attach_acceptance_provenance(source)
            self.assertEqual(finish_run(source), ("pass", []))
            bundle_run(source)
            with self.assertRaisesRegex(
                SpikeError, "source decision is not terminal BLOCKED"
            ):
                review_run(
                    source,
                    root / "reviews",
                    "release_blocking_reconstruction_leak",
                )


if __name__ == "__main__":
    unittest.main()
