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
            ("startup", "control", "diagnostics", "items"),
        )
        self.assertEqual(
            tuple(module.object_name for module in self.manifest.runtime_modules),
            ("archipelago.o", "archipelago-diagnostics.o", "archipelago-items.o"),
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
        for forbidden in ("precursor", "skull", "ammo", "health", "mission"):
            self.assertNotIn(forbidden, items.casefold())

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
