import ast
import unittest
from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace

from Generate import roll_settings
from Options import OptionError
from Utils import parse_yamls
from worlds.jak3 import options


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_TEMPLATE = REPOSITORY_ROOT / "config" / "templates" / "Jak3.yaml"
CANONICAL_DESIGN = REPOSITORY_ROOT / "docs" / "design" / "progression-and-logic.md"
REPOSITORY_INSTRUCTIONS = REPOSITORY_ROOT / "AGENTS.md"

PROFILE_FIELDS = tuple(field.name for field in fields(options.ResolvedJak3Options))

UNSUPPORTED_VALUES = {
    "progression_balancing": 64,
    "accessibility": "items",
    "goal": "defeat_final_boss",
    "mission_order": "vanilla",
    "logic_difficulty": "casual",
    "mission_equipment": "require_unlocks",
    "story_item_mode": "vanilla",
    "finale_relic_requirement": 4,
    "early_route_item": "sphere_zero",
    "early_ranged_gun": "sphere_zero",
    "mission_completion_checks": "off",
    "vanilla_reward_checks": "off",
    "mission_milestone_checks": "major",
    "side_mission_sanity": "off",
    "sanity_costs": "vouchers",
    "challenge_progression": "all",
    "medal_sanity": "gold_only",
    "precursor_orb_sanity": "off",
    "precursor_orb_bundle_size": 30,
    "precursor_orb_progression_cap": 299,
    "skull_gem_sanity": "cumulative_milestones",
    "skull_gem_bundle_size": 30,
    "secret_purchase_sanity": "milestones_free",
    "allow_experimental_checks": True,
    "gun_shuffle": "base_and_upgrades",
    "gun_logic": "none",
    "ammo_upgrade_shuffle": False,
    "armor_shuffle": "vanilla",
    "jetboard_shuffle": False,
    "jetboard_upgrade_shuffle": False,
    "invisibility_statues_shuffle": False,
    "light_power_shuffle": "key_powers",
    "dark_power_shuffle": "key_powers",
    "vehicle_shuffle": "vanilla",
    "eco_crystal_shuffle": "useful_tokens",
    "secret_upgrade_shuffle": "useful",
    "filler_item_weights": {
        **dict(options.SUPPORTED_FIRST_RELEASE_OPTIONS.filler_item_weights),
        "Health Refill": 9,
    },
    "trap_percentage": 1,
    "trap_duration": 21,
    "trap_weights": {
        **dict(options.SUPPORTED_FIRST_RELEASE_OPTIONS.trap_weights),
        "Sandstorm Trap": 2,
    },
    "death_link": True,
}


def make_options(**overrides):
    values = {
        name: option_type.default
        for name, option_type in options.Jak3Options.type_hints.items()
    }
    values.update(overrides)
    return SimpleNamespace(
        **{
            name: option_type.from_any(values[name])
            for name, option_type in options.Jak3Options.type_hints.items()
        }
    )


def load_yaml(path: Path) -> dict:
    documents = list(parse_yamls(path.read_text(encoding="utf-8")))
    if len(documents) != 1:
        raise AssertionError(f"Expected one YAML document in {path}, found {len(documents)}")
    return documents[0]


class OptionSchemaTest(unittest.TestCase):
    def test_shipped_template_covers_the_complete_option_schema(self) -> None:
        yaml_options = load_yaml(SHIPPED_TEMPLATE)["Jak 3"]
        self.assertEqual(set(options.Jak3Options.type_hints), set(yaml_options))
        self.assertEqual(51, len(yaml_options))

    def test_canonical_sources_are_present_in_a_standalone_checkout(self) -> None:
        self.assertTrue(REPOSITORY_INSTRUCTIONS.is_file())
        self.assertTrue(CANONICAL_DESIGN.is_file())
        self.assertTrue(SHIPPED_TEMPLATE.is_file())

    def test_schema_defaults_resolve_to_the_design_profile(self) -> None:
        self.assertEqual(
            options.SUPPORTED_FIRST_RELEASE_OPTIONS,
            options.resolve_options(make_options()),
        )

    def test_jak3_common_defaults_override_archipelago_defaults(self) -> None:
        self.assertEqual(65, options.Jak3ProgressionBalancing.default)
        self.assertEqual("full", options.Jak3Accessibility.from_any("full").current_key)
        self.assertEqual("items", options.Jak3Accessibility.from_any("items").current_key)
        self.assertNotEqual(
            options.Jak3Accessibility.from_any("full").value,
            options.Jak3Accessibility.from_any("items").value,
        )


class OptionResolutionTest(unittest.TestCase):
    def test_shipped_default_yaml_resolves_successfully(self) -> None:
        rolled = roll_settings(load_yaml(SHIPPED_TEMPLATE))
        self.assertEqual(
            options.SUPPORTED_FIRST_RELEASE_OPTIONS,
            options.resolve_options(rolled),
        )

    def test_supported_first_release_profile_is_explicit(self) -> None:
        resolved = options.SUPPORTED_FIRST_RELEASE_OPTIONS
        self.assertEqual("tiered_open_board", resolved.mission_order)
        self.assertEqual("standard", resolved.logic_difficulty)
        self.assertEqual("bootstrap", resolved.mission_equipment)
        self.assertEqual("simplified_authorizations", resolved.story_item_mode)
        self.assertEqual(5, resolved.finale_relic_requirement)
        self.assertEqual("story", resolved.mission_completion_checks)
        self.assertEqual("major", resolved.vanilla_reward_checks)
        self.assertEqual("selected", resolved.side_mission_sanity)
        self.assertEqual("global_bundles", resolved.precursor_orb_sanity)
        self.assertEqual(0, resolved.trap_percentage)
        self.assertFalse(resolved.death_link)
        self.assertFalse(resolved.allow_experimental_checks)

    def test_yaml_comments_preserve_overlay_and_shadow_state_separation(self) -> None:
        text = SHIPPED_TEMPLATE.read_text(encoding="utf-8")
        mission_block = text.split("mission_equipment:", 1)[1].split("story_item_mode:", 1)[0]
        story_block = text.split("story_item_mode:", 1)[1].split("finale_relic_requirement:", 1)[0]
        experimental_block = text.split("allow_experimental_checks:", 1)[1].split(
            "gun_shuffle:", 1
        )[0]
        self.assertNotIn("shadow", mission_block.casefold())
        self.assertIn("lesson abilities", mission_block)
        self.assertIn("shadow-story subsystem", story_block)
        self.assertIn("true remains rejected", experimental_block)

    def test_every_other_governed_value_fails_early(self) -> None:
        self.assertEqual(set(PROFILE_FIELDS), set(UNSUPPORTED_VALUES))
        for name, value in UNSUPPORTED_VALUES.items():
            with self.subTest(option=name):
                with self.assertRaisesRegex(OptionError, name):
                    options.resolve_options(make_options(**{name: value}))

    def test_experimental_modes_fail_early(self) -> None:
        cases = {
            "mission_order": "full_shuffle_experimental",
            "gun_logic": "color_specific_experimental",
            "armor_shuffle": "progression_experimental",
            "vehicle_shuffle": "individual_experimental",
        }
        for name, value in cases.items():
            with self.subTest(option=name):
                with self.assertRaisesRegex(OptionError, name):
                    options.resolve_options(make_options(**{name: value}))

    def test_experimental_collectibles_require_the_experimental_gate(self) -> None:
        cases = {
            "side_mission_sanity": ("orb_hunts", "all"),
            "precursor_orb_sanity": ("regional_bundles", "individual_static"),
            "skull_gem_sanity": ("individual_static",),
        }
        for name, values in cases.items():
            for value in values:
                with self.subTest(option=name, value=value):
                    with self.assertRaisesRegex(
                        OptionError, "allow_experimental_checks.*" + name
                    ):
                        options.resolve_options(make_options(**{name: value}))

    def test_experimental_gate_cannot_enable_unimplemented_tables(self) -> None:
        with self.assertRaisesRegex(OptionError, "allow_experimental_checks.*not implemented"):
            options.resolve_options(make_options(allow_experimental_checks=True))

    def test_canonical_story_mode_has_a_specific_error(self) -> None:
        with self.assertRaisesRegex(OptionError, "canonical.*gate table.*not implemented"):
            options.resolve_options(make_options(story_item_mode="canonical"))

    def test_invalid_relic_requirements_fail_clearly(self) -> None:
        for value in (-1, 8):
            with self.subTest(value=value):
                with self.assertRaisesRegex(OptionError, "finale_relic_requirement.*0.*7"):
                    options.validate_options(
                        replace(options.SUPPORTED_FIRST_RELEASE_OPTIONS, finale_relic_requirement=value)
                    )

    def test_invalid_progression_caps_fail_clearly(self) -> None:
        for value in (-1, 601):
            with self.subTest(value=value):
                with self.assertRaisesRegex(OptionError, "precursor_orb_progression_cap.*0.*600"):
                    options.validate_options(
                        replace(
                            options.SUPPORTED_FIRST_RELEASE_OPTIONS,
                            precursor_orb_progression_cap=value,
                        )
                    )

    def test_resolution_is_deterministic(self) -> None:
        filler = dict(reversed(options.SUPPORTED_FIRST_RELEASE_OPTIONS.filler_item_weights))
        traps = dict(reversed(options.SUPPORTED_FIRST_RELEASE_OPTIONS.trap_weights))
        first = options.resolve_options(make_options(filler_item_weights=filler, trap_weights=traps))
        second = options.resolve_options(make_options())
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        self.assertEqual(tuple(options.FILLER_DEFAULTS.items()), first.filler_item_weights)
        self.assertEqual(tuple(options.TRAP_DEFAULTS.items()), first.trap_weights)

    def test_standard_placement_controls_remain_archipelago_owned(self) -> None:
        raw = make_options(start_inventory_from_pool={"Progressive Armor": 1})
        self.assertEqual(
            options.SUPPORTED_FIRST_RELEASE_OPTIONS,
            options.resolve_options(raw),
        )


class RawOptionBoundaryTest(unittest.TestCase):
    def test_world_code_reads_raw_options_only_during_resolution(self) -> None:
        package = REPOSITORY_ROOT / "worlds" / "jak3"
        uses = []

        class Visitor(ast.NodeVisitor):
            function = None

            def visit_FunctionDef(self, node):
                previous = self.function
                self.function = node.name
                self.generic_visit(node)
                self.function = previous

            def visit_Attribute(self, node):
                if (
                    node.attr == "options"
                    and isinstance(node.value, ast.Name)
                    and node.value.id in {"self", "world"}
                ):
                    uses.append((source.name, self.function))
                self.generic_visit(node)

        for source in sorted(package.glob("*.py")):
            Visitor().visit(ast.parse(source.read_text(encoding="utf-8"), filename=str(source)))

        self.assertEqual([("__init__.py", "generate_early")], uses)


if __name__ == "__main__":
    unittest.main()
