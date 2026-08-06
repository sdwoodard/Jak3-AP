import unittest
from types import SimpleNamespace

from Options import OptionError
from worlds.jak3 import options


SUPPORTED_DEFAULTS = {
    "progression_balancing": 65,
    "accessibility": 0,
    "goal": 0,
    "mission_order": 1,
    "logic_difficulty": 1,
    "mission_equipment": 0,
    "story_item_mode": 0,
    "finale_relic_requirement": 5,
    "early_route_item": 0,
    "early_ranged_gun": 0,
    "mission_completion_checks": 1,
    "vanilla_reward_checks": 1,
    "mission_milestone_checks": 0,
    "side_mission_sanity": 1,
    "sanity_costs": 0,
    "challenge_progression": 0,
    "medal_sanity": 0,
    "precursor_orb_sanity": 1,
    "precursor_orb_bundle_size": 25,
    "precursor_orb_progression_cap": 300,
    "skull_gem_sanity": 0,
    "skull_gem_bundle_size": 25,
    "secret_purchase_sanity": 0,
    "allow_experimental_checks": 0,
    "gun_shuffle": 2,
    "gun_logic": 1,
    "ammo_upgrade_shuffle": 1,
    "armor_shuffle": 1,
    "jetboard_shuffle": 1,
    "jetboard_upgrade_shuffle": 1,
    "invisibility_statues_shuffle": 1,
    "light_power_shuffle": 2,
    "dark_power_shuffle": 2,
    "vehicle_shuffle": 1,
    "eco_crystal_shuffle": 0,
    "secret_upgrade_shuffle": 0,
    "filler_item_weights": {
        "Precursor Orb Pack (5)": 20,
        "Precursor Orb Pack (10)": 10,
        "Precursor Orb Pack (25)": 4,
        "Skull Gem Pack (1)": 12,
        "Skull Gem Pack (3)": 6,
        "Skull Gem Pack (5)": 2,
        "Red Ammo Refill": 8,
        "Yellow Ammo Refill": 8,
        "Blue Ammo Refill": 8,
        "Dark Ammo Refill": 4,
        "Health Refill": 10,
        "Light Eco Refill": 6,
        "Dark Eco Refill": 6,
        "Vehicle Repair": 6,
        "Vehicle Turbo Refill": 4,
    },
    "trap_percentage": 0,
    "trap_duration": 20,
    "trap_weights": {
        "Sandstorm Trap": 3,
        "Low Gravity Trap": 2,
        "Gun Jam Trap": 1,
        "Eco Leak Trap": 1,
        "Vehicle Wobble Trap": 1,
    },
    "death_link": 0,
}

UNSUPPORTED_VALUES = {
    "progression_balancing": 64,
    "accessibility": 1,
    "goal": 1,
    "mission_order": 0,
    "logic_difficulty": 0,
    "mission_equipment": 1,
    "story_item_mode": 1,
    "finale_relic_requirement": 4,
    "early_route_item": 1,
    "early_ranged_gun": 1,
    "mission_completion_checks": 0,
    "vanilla_reward_checks": 0,
    "mission_milestone_checks": 1,
    "side_mission_sanity": 0,
    "sanity_costs": 1,
    "challenge_progression": 1,
    "medal_sanity": 1,
    "precursor_orb_sanity": 0,
    "precursor_orb_bundle_size": 30,
    "precursor_orb_progression_cap": 299,
    "skull_gem_sanity": 1,
    "skull_gem_bundle_size": 30,
    "secret_purchase_sanity": 1,
    "allow_experimental_checks": 1,
    "gun_shuffle": 1,
    "gun_logic": 0,
    "ammo_upgrade_shuffle": 0,
    "armor_shuffle": 0,
    "jetboard_shuffle": 0,
    "jetboard_upgrade_shuffle": 0,
    "invisibility_statues_shuffle": 0,
    "light_power_shuffle": 1,
    "dark_power_shuffle": 1,
    "vehicle_shuffle": 0,
    "eco_crystal_shuffle": 1,
    "secret_upgrade_shuffle": 1,
    "filler_item_weights": {**SUPPORTED_DEFAULTS["filler_item_weights"], "Health Refill": 9},
    "trap_percentage": 1,
    "trap_duration": 21,
    "trap_weights": {**SUPPORTED_DEFAULTS["trap_weights"], "Sandstorm Trap": 2},
    "death_link": 1,
}


def make_initial_profile(**overrides):
    values = {**SUPPORTED_DEFAULTS, **overrides}
    annotations = options.Jak3Options.__annotations__
    return SimpleNamespace(
        **{
            name: annotations[name].from_any(value)
            for name, value in values.items()
        }
    )


class InitialProfileOptionsTest(unittest.TestCase):
    def test_documented_defaults_are_schema_defaults(self) -> None:
        self.assertEqual(set(options.INITIAL_PROFILE_FIELDS), set(SUPPORTED_DEFAULTS))
        annotations = options.Jak3Options.__annotations__
        for name, value in SUPPORTED_DEFAULTS.items():
            self.assertEqual(value, annotations[name].default, name)

    def test_documented_default_profile_is_accepted(self) -> None:
        options.validate_initial_profile(make_initial_profile())

    def test_every_nondefault_world_value_fails_early(self) -> None:
        self.assertEqual(set(options.INITIAL_PROFILE_FIELDS), set(UNSUPPORTED_VALUES))
        for name, value in UNSUPPORTED_VALUES.items():
            with self.subTest(option=name):
                with self.assertRaisesRegex(OptionError, f"`{name}`"):
                    options.validate_initial_profile(make_initial_profile(**{name: value}))

    def test_only_start_inventory_pool_is_exempt_from_profile_pin(self) -> None:
        self.assertNotIn("start_inventory_from_pool", options.INITIAL_PROFILE_FIELDS)
        self.assertIn("goal", options.INITIAL_PROFILE_FIELDS)
        self.assertIn("death_link", options.INITIAL_PROFILE_FIELDS)


if __name__ == "__main__":
    unittest.main()
