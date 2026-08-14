import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

import yaml
from Fill import (
    distribute_items_restrictive,
    distribute_planned_blocks,
    parse_planned_blocks,
    resolve_early_locations_for_planned,
)
from test.general import gen_steps, setup_multiworld

from worlds.AutoWorld import call_all
from worlds.jak3 import Jak3World


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPOSITORY_ROOT / "tools" / "generate_milestone_10_fixture.py"
TEMPLATE_PATH = REPOSITORY_ROOT / "config" / "templates" / "Jak3.yaml"


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m10_fixture", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Milestone10FixtureTest(unittest.TestCase):
    def test_two_slot_fixture_is_derived_only_by_identity_description_and_plando(
        self,
    ) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
        template = yaml.safe_load(template_text)
        tool = load_tool()
        documents = tool.build_fixture_documents(template_text)

        self.assertEqual(set(documents), {"M10-Runner.yaml", "M10-Helper.yaml"})
        generated = {name: yaml.safe_load(text) for name, text in documents.items()}
        for name, document in generated.items():
            with self.subTest(name=name):
                self.assertEqual(document["game"], "Jak 3")
                self.assertEqual(
                    {
                        key: value
                        for key, value in document["Jak 3"].items()
                        if key != "plando_items"
                    },
                    {
                        key: value
                        for key, value in template["Jak 3"].items()
                        if key != "plando_items"
                    },
                )

        runner = generated["M10-Runner.yaml"]
        helper = generated["M10-Helper.yaml"]
        self.assertEqual(runner["name"], "M10 Runner")
        self.assertEqual(helper["name"], "M10 Helper")
        self.assertEqual(
            [entry["location"] for entry in runner["Jak 3"]["plando_items"]],
            [
                "Complete Mission: Complete Arena Training",
                "Complete Mission: Earn 1st War Amulet",
                "Reward: First Armor Upgrade",
            ],
        )
        self.assertEqual(
            [entry["item"] for entry in runner["Jak 3"]["plando_items"]],
            ["Jetboard", "Blaster", "Progressive Armor"],
        )
        helper_block = helper["Jak 3"]["plando_items"][0]
        self.assertEqual(
            helper_block["items"],
            {item_name: 1 for item_name in tool.HELPER_ITEM_NAMES},
        )
        self.assertEqual(len(helper_block["locations"]), 5)
        self.assertEqual(helper_block["world"], "M10 Runner")

    def test_two_slot_fixture_uses_real_plando_fill_without_pool_creation(
        self,
    ) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
        tool = load_tool()
        documents = tool.build_fixture_documents(template_text)
        generated = {name: yaml.safe_load(text) for name, text in documents.items()}
        option_documents = [
            generated["M10-Runner.yaml"]["Jak 3"],
            generated["M10-Helper.yaml"]["Jak 3"],
        ]
        multiworld = setup_multiworld(
            [Jak3World, Jak3World],
            steps=gen_steps[:-1],
            seed=10_101_636,
            options=option_documents,
        )
        multiworld.player_name = {1: tool.RUNNER_NAME, 2: tool.HELPER_NAME}
        multiworld.plando_item_blocks = parse_planned_blocks(multiworld)
        resolve_early_locations_for_planned(multiworld)
        distribute_planned_blocks(
            multiworld,
            [
                block
                for player in multiworld.player_ids
                for block in multiworld.plando_item_blocks[player]
            ],
        )
        call_all(multiworld, "pre_fill")
        distribute_items_restrictive(multiworld)

        runner_expected = {
            "Complete Mission: Complete Arena Training": ("Jetboard", 1),
            "Complete Mission: Earn 1st War Amulet": ("Blaster", 1),
            "Reward: First Armor Upgrade": ("Progressive Armor", 1),
        }
        for location_name, expected in runner_expected.items():
            location = multiworld.get_location(location_name, 1)
            self.assertIsNotNone(location.item)
            self.assertEqual((location.item.name, location.item.player), expected)

        helper_locations = option_documents[1]["plando_items"][0]["locations"]
        helper_items = [
            multiworld.get_location(name, 1).item for name in helper_locations
        ]
        self.assertTrue(all(item is not None for item in helper_items))
        self.assertEqual(
            {item.name for item in helper_items}, set(tool.HELPER_ITEM_NAMES)
        )
        self.assertEqual({item.player for item in helper_items}, {2})
        self.assertEqual(multiworld.get_unfilled_locations(), [])
        self.assertFalse(
            [item for item in multiworld.itempool if item.location is None],
            "The fixture must take every planned item from the canonical pool.",
        )

    def test_marker_drift_fails_instead_of_silently_changing_defaults(self) -> None:
        tool = load_tool()
        with self.assertRaisesRegex(ValueError, "marker changed"):
            tool.build_fixture_documents("name: changed\n")


if __name__ == "__main__":
    unittest.main()
