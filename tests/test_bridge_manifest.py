import json
import re
import unittest
from pathlib import Path

from worlds.jak3.agents.bridge_manifest import parse_bridge_manifest
from worlds.jak3.agents.diagnostics import GOAL_EVENT_REGISTRY


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "mod" / "opengoal" / "bridge-modules.json"
BRIDGE_ROOT = MANIFEST_PATH.parent
GOAL_EVENT_DECLARATION = re.compile(
    r"\(defconstant AP-DIAG-EVENT-[A-Z0-9-]+ ([0-9]+)\)"
)


def goal_event_codes(payload: bytes) -> tuple[int, ...]:
    return tuple(
        int(match.group(1))
        for line in payload.decode().splitlines()
        if (match := GOAL_EVENT_DECLARATION.fullmatch(line)) is not None
    )


class BridgeManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = MANIFEST_PATH.read_bytes()
        self.manifest = parse_bridge_manifest(self.raw)
        self.payloads = {
            str(module.resource): (BRIDGE_ROOT / Path(str(module.source))).read_bytes()
            for module in self.manifest.modules
        }

    def test_manifest_has_exact_deterministic_lifecycle_order(self) -> None:
        self.assertEqual(
            tuple(module.name for module in self.manifest.modules),
            ("startup", "control", "diagnostics", "items", "locations", "rewards"),
        )
        self.assertEqual(
            tuple(module.object_name for module in self.manifest.runtime_modules),
            (
                "archipelago.o",
                "archipelago-diagnostics.o",
                "archipelago-items.o",
                "archipelago-locations.o",
                "archipelago-rewards.o",
            ),
        )
        self.assertEqual(
            self.manifest.source_set_sha256(self.payloads),
            self.manifest.source_set_sha256(dict(reversed(self.payloads.items()))),
        )

    def test_every_manifest_or_source_mutation_changes_source_set_hash(self) -> None:
        baseline = self.manifest.source_set_sha256(self.payloads)
        for resource in self.payloads:
            changed = dict(self.payloads)
            changed[resource] += b"\n;; mutation"
            self.assertNotEqual(baseline, self.manifest.source_set_sha256(changed))
        document = json.loads(self.raw)
        document["modules"][0]["resource"] = "assets/opengoal/renamed.gc"
        changed_raw = json.dumps(document, separators=(",", ":")).encode()
        with self.assertRaises(ValueError):
            parse_bridge_manifest(changed_raw)
        whitespace_change = self.raw + b"\n"
        changed_manifest = parse_bridge_manifest(whitespace_change)
        self.assertNotEqual(baseline, changed_manifest.source_set_sha256(self.payloads))

    def test_rejects_duplicate_unsafe_and_wrong_order_entries(self) -> None:
        for mutation, message in (
            (("modules", 1, "name", "startup"), "Duplicate"),
            (("modules", 1, "source", "../archipelago.gc"), "Unsafe"),
            (
                (
                    "modules",
                    0,
                    "source",
                    "goal_src/jak3/pc/features/archipelago-renamed.gc",
                ),
                "canonical",
            ),
            (("modules", 1, "order", 31), "canonical"),
        ):
            document = json.loads(self.raw)
            _, index, field, value = mutation
            document["modules"][index][field] = value
            with self.assertRaisesRegex(ValueError, message):
                parse_bridge_manifest(json.dumps(document).encode())

    def test_rejects_wrong_manifest_scalar_types_without_json_coercion(self) -> None:
        mutations = (
            ("manifest_version", None, "manifest_version", True, "integer"),
            ("manifest_version", None, "manifest_version", "1", "integer"),
            ("source_set_format", None, "source_set_format", 1, "string"),
            ("object_anchor", None, "object_anchor", False, "string"),
            ("module order", 0, "order", "10", "integer"),
            ("module order boolean", 0, "order", True, "integer"),
            ("module phase", 0, "phase", ["pre_mi"], "phase"),
        )
        for label, index, field, value, message in mutations:
            with self.subTest(label=label):
                document = json.loads(self.raw)
                target = document if index is None else document["modules"][index]
                target[field] = value
                with self.assertRaisesRegex(ValueError, message):
                    parse_bridge_manifest(json.dumps(document).encode())

    def test_goal_source_boundaries_keep_python_as_support_file_writer(self) -> None:
        control = self.payloads["assets/opengoal/archipelago.gc"].decode()
        diagnostics = self.payloads[
            "assets/opengoal/archipelago-diagnostics.gc"
        ].decode()
        items = self.payloads["assets/opengoal/archipelago-items.gc"].decode()
        locations = self.payloads["assets/opengoal/archipelago-locations.gc"].decode()
        rewards = self.payloads["assets/opengoal/archipelago-rewards.gc"].decode()
        self.assertNotIn("ap-set-log-path!", control)
        self.assertNotIn("'append", control)
        self.assertNotIn("ap-diagnostic-ring-state", control)
        self.assertNotIn("(new 'stack 'file-stream", diagnostics)
        self.assertIn("AP-DIAGNOSTIC-RING-CAPACITY 64", diagnostics)
        self.assertIn("*ap3-diagnostic-export-hook*", diagnostics)
        self.assertIn("source-loaded-pending", diagnostics)
        self.assertIn("channel-ready-pending", diagnostics)
        self.assertIn("(defun ap-diagnostic-ack! ((activation-generation int)", control)
        self.assertIn(
            "(= activation-generation *ap-diagnostic-activation-generation*)",
            diagnostics,
        )
        self.assertNotIn(
            "(ap-diagnostic-emit! AP-DIAG-EVENT-SOURCE-LOADED", diagnostics
        )
        self.assertNotIn("received-item", diagnostics.casefold())
        self.assertNotIn("location-check", diagnostics.casefold())
        self.assertNotIn("mission-reward", diagnostics.casefold())
        self.assertNotIn("game-feature", control)
        self.assertIn("game-feature board", items)
        self.assertIn("game-feature gun-yellow-1", items)
        self.assertIn("game-feature armor0", items)
        self.assertIn(
            "(set! *ap3-permanent-items-native-target-hook* "
            "ap-items-native-target-mask)",
            items,
        )
        self.assertIn(
            "permanent_item_native_target_mask ~D~%",
            control,
        )
        self.assertIn("(define *ap3-items-module-active* 0)", control)
        self.assertIn("(define *ap3-locations-module-active* 0)", control)
        self.assertIn("(define *ap3-reward-module-active* 0)", control)
        self.assertIn("items_module_active ~D~%", control)
        self.assertIn("locations_module_active ~D~%", control)
        self.assertIn("reward_module_active ~D~%", control)
        self.assertIn(
            "(*ap3-permanent-items-native-target-hook*)",
            control,
        )
        self.assertIn(
            "*ap3-permanent-items-reconciliation-suspended-hook*",
            control,
        )
        diagnostic_transitions = diagnostics[
            diagnostics.index(
                "(defun ap-diagnostic-observe-transitions!"
            ) : diagnostics.index("(defun ap-diagnostic-ring-export!")
        ]
        self.assertIn(
            "(*ap3-permanent-items-reconciliation-suspended-hook*)",
            diagnostic_transitions,
        )
        self.assertIn(
            "(if (*ap3-permanent-items-reconciliation-suspended-hook*)\n"
            "                       0\n"
            "                       (-> *ap-runtime* safe-permanent))",
            diagnostic_transitions,
        )
        for forbidden in ("precursor", "skull", "ammo", "health", "mission"):
            self.assertNotIn(forbidden, items.casefold())
        self.assertIn("(game-task arena-training-1)", locations)
        self.assertIn("(game-task arena-fight-1)", locations)
        self.assertIn("(game-task desert-artifact-race-1)", locations)
        self.assertIn("(task-complete? *game-info*", locations)
        self.assertIn("(task-node-closed?", locations)
        recovery_poll = locations[
            locations.index("(task-node-closed?") : locations.index(
                "(ap-locations-publish! 0"
            )
        ]
        self.assertIn("*ap3-reward-location-recovery-eligible-hook*", recovery_poll)
        self.assertLess(
            recovery_poll.index("*ap3-reward-location-recovery-eligible-hook*"),
            recovery_poll.index(
                "(ap-locations-queue-once! AP-LOCATION-MASK-REWARD-ARMOR-1)"
            ),
        )
        immediate = locations[
            locations.index("(defun ap-locations-observe-reward!") : locations.index(
                "(defun ap-locations-observe!"
            )
        ]
        self.assertIn("(ap-locations-publish! 7", immediate)
        self.assertNotIn("debug", locations.casefold())
        self.assertIn("AP-DIAG-EVENT-LOCATION-OBSERVED", locations)
        publish = locations[
            locations.index("(defun ap-locations-publish!") : locations.index(
                "(defun ap-locations-observe!"
            )
        ]
        self.assertIn("(when (>= sequence 0)", publish)
        self.assertNotIn("logclear!", publish)
        self.assertIn(
            "logclear!", locations[locations.index("(defun ap-locations-ack-one!") :]
        )
        self.assertNotIn("close-task", locations)
        self.assertNotIn("(-> *game-info* task-perm-list)", locations)
        self.assertNotIn("actor", locations.casefold())
        self.assertNotIn("address", locations.casefold())
        self.assertNotIn("mission-reward", locations.casefold())
        self.assertNotIn("arena-training-1", control)
        self.assertEqual(items.count("(set! *ap3-items-module-active* 1)"), 1)
        self.assertLess(
            items.index("(set! *ap3-permanent-items-native-target-hook*"),
            items.index("(set! *ap3-items-module-active* 1)"),
        )
        self.assertEqual(locations.count("(set! *ap3-locations-module-active* 1)"), 1)
        self.assertLess(
            locations.index("(set! *ap3-reward-location-observe-hook*"),
            locations.index("(set! *ap3-locations-module-active* 1)"),
        )
        self.assertLess(
            locations.index("(set! *ap3-locations-module-active* 1)"),
            locations.index("(ap-export-state!)"),
        )
        self.assertIn("desert-artifact-race-1-resolution", rewards)
        self.assertIn("AP-REWARD-ARMOR-1-COMMAND-INDEX 12", rewards)
        self.assertIn("AP-REWARD-ARMOR-1-COMMAND-COUNT 2", rewards)
        self.assertIn("(game-task-node-command add-jakc)", rewards)
        self.assertIn("(game-task-node-command add-armor-0)", rewards)
        bound_mode = rewards[
            rewards.index("(defun ap-rewards-bound-mode?") : rewards.index(
                "(defun ap-rewards-armor-1-node-info"
            )
        ]
        for dependency in (
            "*ap3-items-module-active*",
            "*ap3-locations-module-active*",
            "*ap3-reward-module-active*",
        ):
            self.assertIn(dependency, bound_mode)
        self.assertIn("(*ap3-native-eval-game-task-cmd!* this)", rewards)
        self.assertIn(
            "(logior! (-> *game-info* features) (game-feature jakc))", rewards
        )
        self.assertNotIn("(game-feature armor0)", rewards)
        self.assertEqual(rewards.count("desert-artifact-race-1-resolution"), 1)
        self.assertNotIn("desert-turtle-training", rewards)

    def test_reward_wrapper_has_one_reload_safe_fail_open_interception(self) -> None:
        control = self.payloads["assets/opengoal/archipelago.gc"].decode()
        rewards = self.payloads["assets/opengoal/archipelago-rewards.gc"].decode()
        wrapper = rewards[
            rewards.index("(defun ap3-eval-game-task-cmd-wrapper") : rewards.index(
                "(defun ap3-install-reward-hook!"
            )
        ]
        installer = rewards[rewards.index("(defun ap3-install-reward-hook!") :]

        self.assertEqual(wrapper.count("(*ap3-native-eval-game-task-cmd!* this)"), 4)
        self.assertEqual(wrapper.count("(*ap3-reward-location-observe-hook*"), 1)
        self.assertLess(
            wrapper.index("((nonzero? *ap-applying-item*)"),
            wrapper.index("((not (ap-rewards-bound-mode?))"),
        )
        mismatch = wrapper.index("((not (ap-rewards-armor-1-shape-valid? this))")
        self.assertLess(
            wrapper.index("(*ap3-native-eval-game-task-cmd!* this)", mismatch),
            wrapper.index("(ap-rewards-report-armor-1-shape-mismatch! this)", mismatch),
        )
        self.assertIn(
            "(method-of-type game-task-node-info eval-game-task-cmd!)", installer
        )
        self.assertIn("(method-set! game-task-node-info 13", installer)
        self.assertIn(
            "(!= current *ap3-installed-eval-game-task-cmd-wrapper*)", installer
        )
        self.assertEqual(rewards.count("(set! *ap3-reward-module-active* 1)"), 1)
        self.assertEqual(rewards.count("(ap-export-state!)"), 1)
        self.assertLess(
            installer.index("(method-set! game-task-node-info 13"),
            installer.index("(set! *ap3-reward-module-active* 1)"),
        )
        self.assertLess(
            installer.index("(set! *ap3-reward-module-active* 1)"),
            installer.index("(ap-export-state!)"),
        )
        self.assertIn("*ap3-item-application-begin-hook*", rewards)
        self.assertIn("*ap3-item-application-end-hook*", rewards)
        self.assertIn(
            "*ap3-reward-location-recovery-eligible-hook*",
            self.payloads["assets/opengoal/archipelago.gc"].decode(),
        )
        reporter = rewards[
            rewards.index(
                "(defun ap-rewards-report-armor-1-shape-mismatch!"
            ) : rewards.index("(defun ap-rewards-location-recovery-eligible?")
        ]
        self.assertIn("AP-DIAG-EVENT-REWARD-SHAPE-MISMATCH", reporter)
        self.assertIn("*ap-reward-armor-1-shape-mismatch-reported*", reporter)
        recovery = rewards[
            rewards.index(
                "(defun ap-rewards-location-recovery-eligible?"
            ) : rewards.index("(defun ap-rewards-item-application-begin!")
        ]
        self.assertIn("(ap-rewards-bound-mode?)", recovery)
        self.assertIn("(ap-rewards-armor-1-shape-valid?", recovery)
        self.assertIn("(ap-rewards-report-armor-1-shape-mismatch!", recovery)
        self.assertIn("(set! *ap3-reward-location-recovery-eligible-hook*", rewards)
        self.assertIn(
            "(set! *ap3-permanent-items-reconciliation-suspended-hook*",
            rewards,
        )
        suspension = rewards[
            rewards.index(
                "(defun ap-rewards-permanent-item-reconciliation-suspended?"
            ) : rewards.index("(defun ap-rewards-location-recovery-eligible?")
        ]
        self.assertIn("(ap-rewards-bound-mode?)", suspension)
        self.assertIn("(ap-rewards-armor-1-shape-valid?", suspension)
        self.assertIn("(ap-rewards-report-armor-1-shape-mismatch!", suspension)

        snapshot_export = control[
            control.index("(defun ap-export-state!") : control.index(
                "(defun ap-set-state-path!"
            )
        ]
        self.assertIn("permanent-reconciliation-suspended", snapshot_export)
        self.assertIn(
            "(if permanent-reconciliation-suspended\n                -1",
            snapshot_export,
        )
        dispatch = control[
            control.index("(defun ap3-command-core!") : control.index(
                "(defun ap3-init!"
            )
        ]
        suspended = dispatch.index(
            "(*ap3-permanent-items-reconciliation-suspended-hook*)"
        )
        reconcile = dispatch.index(
            "(*ap3-permanent-items-reconcile-hook* command-id payload)"
        )
        self.assertLess(suspended, reconcile)
        self.assertIn('"reward-shape-incompatible"', dispatch)

    def test_blaster_target_requires_its_generic_gun_dependency(self) -> None:
        items = self.payloads["assets/opengoal/archipelago-items.gc"].decode()
        start = items.index("(defun ap-items-blaster-stage-one-correct? ()")
        end = items.index("(defun ap-items-native-target-mask ()", start)
        correctness_check = items[start:end]

        self.assertIn("(game-feature gun)", correctness_check)
        self.assertIn("(game-feature gun-yellow-1)", correctness_check)
        self.assertIn(
            "(when (ap-items-blaster-stage-one-correct?)",
            items,
        )

    def test_goal_event_codes_match_the_python_registry(self) -> None:
        codes: list[int] = []
        for payload in self.payloads.values():
            codes.extend(goal_event_codes(payload))
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(set(codes), set(GOAL_EVENT_REGISTRY))

    def test_goal_event_code_parser_accepts_lf_and_crlf(self) -> None:
        declaration = b"(defconstant AP-DIAG-EVENT-SOURCE-LOADED 100)"

        for ending in (b"\n", b"\r\n"):
            with self.subTest(ending=ending):
                self.assertEqual(goal_event_codes(declaration + ending), (100,))


if __name__ == "__main__":
    unittest.main()
