from collections import Counter
from unittest.mock import patch

from BaseClasses import ItemClassification, LocationProgressType
from test.bases import WorldTestBase

from worlds.jak3.game_id import GAME_NAME
from worlds.jak3.options import SUPPORTED_FIRST_RELEASE_OPTIONS
from worlds.jak3.regions import PERMISSIVE_SCAFFOLD_REGION_NAME
from worlds.jak3.registry import (
    FILLER_ITEMS,
    FIRST_RELEASE_ITEM_NAME_TO_ID,
    FIRST_RELEASE_LOCATIONS,
    FIRST_RELEASE_LOCATION_NAME_TO_ID,
    ITEM_TABLE_HASH,
    LOCATION_TABLE_HASH,
    MAJOR_REWARD_LOCATIONS,
    MISSION_COMPLETION_EVENTS,
    MISSION_TABLE_HASH,
    ORB_THRESHOLD_LOCATIONS,
    PROGRESSION_ITEMS,
    RESERVED_LEGACY_ITEM_IDS,
    RESERVED_LEGACY_LOCATION_IDS,
    SELECTED_SIDE_LOCATIONS,
    STORY_COMPLETION_LOCATIONS,
    TRAP_ITEMS,
    USEFUL_ITEMS,
    VICTORY_EVENT,
)
from worlds.jak3.slot_data import SLOT_DATA_KEYS, SUPPORTED_RESOLVED_OPTIONS_HASH


CLASSIFICATION_BY_REGISTRY_VALUE = {
    "progression": ItemClassification.progression,
    "progression_skip_balancing": ItemClassification.progression_skip_balancing,
    "useful": ItemClassification.useful,
    "filler": ItemClassification.filler,
    "trap": ItemClassification.trap,
}


class Jak3WorldTest(WorldTestBase):
    game = GAME_NAME

    def test_world_uses_the_resolved_first_release_profile(self) -> None:
        self.assertEqual(SUPPORTED_FIRST_RELEASE_OPTIONS, self.world.resolved_options)

    def test_active_public_tables_are_the_first_release_registry(self) -> None:
        self.assertEqual(FIRST_RELEASE_ITEM_NAME_TO_ID, self.world.item_name_to_id)
        self.assertEqual(
            FIRST_RELEASE_LOCATION_NAME_TO_ID, self.world.location_name_to_id
        )
        self.assertEqual(65, len(self.world.item_name_to_id))
        self.assertEqual(147, len(self.world.location_name_to_id))
        self.assertFalse(
            any(
                name.startswith("Mission Unlock:")
                for name in self.world.item_name_to_id
            )
        )

        active_codes = set(self.world.item_name_to_id.values()) | set(
            self.world.location_name_to_id.values()
        )
        reserved_codes = {
            record.code
            for record in RESERVED_LEGACY_ITEM_IDS + RESERVED_LEGACY_LOCATION_IDS
        }
        self.assertFalse(active_codes & reserved_codes)

    def test_network_location_families_and_pool_balance_are_exact(self) -> None:
        network_locations = [
            location
            for location in self.multiworld.get_locations(self.player)
            if location.address is not None
        ]
        own_pool = [
            item for item in self.multiworld.itempool if item.player == self.player
        ]

        self.assertEqual(61, len(STORY_COMPLETION_LOCATIONS))
        self.assertEqual(38, len(MAJOR_REWARD_LOCATIONS))
        self.assertEqual(24, len(SELECTED_SIDE_LOCATIONS))
        self.assertEqual(24, len(ORB_THRESHOLD_LOCATIONS))
        self.assertEqual(147, len(network_locations))
        self.assertEqual(147, len(own_pool))
        self.assertEqual(147, len(self.multiworld.get_unfilled_locations(self.player)))
        self.assertEqual(
            {(record.name, record.code) for record in FIRST_RELEASE_LOCATIONS},
            {(location.name, location.address) for location in network_locations},
        )

    def test_default_item_counts_multiplicities_and_classifications_are_exact(
        self,
    ) -> None:
        own_pool = [
            item for item in self.multiworld.itempool if item.player == self.player
        ]
        counts = Counter(item.name for item in own_pool)
        classifications = Counter(item.classification for item in own_pool)

        for record in PROGRESSION_ITEMS + USEFUL_ITEMS:
            with self.subTest(item=record.name):
                self.assertEqual(record.pool_count, counts[record.name])
                self.assertEqual(
                    CLASSIFICATION_BY_REGISTRY_VALUE[record.classification],
                    self.get_item_by_name(record.name).classification,
                )

        filler_names = {record.name for record in FILLER_ITEMS}
        trap_names = {record.name for record in TRAP_ITEMS}
        self.assertEqual(26, sum(counts[record.name] for record in PROGRESSION_ITEMS))
        self.assertEqual(28, sum(counts[record.name] for record in USEFUL_ITEMS))
        self.assertEqual(93, sum(counts[name] for name in filler_names))
        self.assertEqual(0, sum(counts[name] for name in trap_names))
        self.assertEqual(17, classifications[ItemClassification.progression])
        self.assertEqual(
            9, classifications[ItemClassification.progression_skip_balancing]
        )
        self.assertEqual(28, classifications[ItemClassification.useful])
        self.assertEqual(93, classifications[ItemClassification.filler])
        self.assertEqual(0, classifications[ItemClassification.trap])
        self.assertEqual(
            set(counts),
            {record.name for record in PROGRESSION_ITEMS + USEFUL_ITEMS}
            | {name for name in filler_names if counts[name]},
        )

    def test_task_36_is_absent_and_task_72_is_only_victory(self) -> None:
        self.assertNotIn(743_001_036, self.world.location_name_to_id.values())
        self.assertFalse(
            any(record.native_task_id == 36 for record in FIRST_RELEASE_LOCATIONS)
        )
        self.assertFalse(
            any(record.native_task_id == 72 for record in FIRST_RELEASE_LOCATIONS)
        )

        victory = self.multiworld.get_location(VICTORY_EVENT.location_name, self.player)
        self.assertIsNone(victory.address)
        self.assertTrue(victory.locked)
        self.assertIsNotNone(victory.item)
        self.assertEqual(VICTORY_EVENT.item_name, victory.item.name)
        self.assertIsNone(victory.item.code)
        self.assertEqual(
            0,
            sum(
                item.name == VICTORY_EVENT.item_name
                for item in self.multiworld.itempool
            ),
        )

    def test_hidden_mission_events_and_victory_are_code_less(self) -> None:
        event_locations = [
            location
            for location in self.multiworld.get_locations(self.player)
            if location.address is None
        ]
        self.assertEqual(65, len(MISSION_COMPLETION_EVENTS))
        self.assertEqual(66, len(event_locations))
        self.assertEqual(
            set(range(6, 36)) | set(range(37, 72)),
            {event.native_task_id for event in MISSION_COMPLETION_EVENTS},
        )

        for event in MISSION_COMPLETION_EVENTS:
            with self.subTest(task=event.native_task_id):
                location = self.multiworld.get_location(
                    event.location_name, self.player
                )
                self.assertTrue(location.locked)
                self.assertFalse(location.show_in_spoiler)
                self.assertIsNotNone(location.item)
                self.assertEqual(event.item_name, location.item.name)
                self.assertIsNone(location.item.code)

        self.assertEqual(
            1,
            sum(
                location.name == VICTORY_EVENT.location_name
                for location in event_locations
            ),
        )

    def test_orb_thresholds_and_default_exclusions_are_exact(self) -> None:
        self.assertEqual(
            list(range(25, 601, 25)),
            [record.orb_threshold for record in ORB_THRESHOLD_LOCATIONS],
        )
        expected_exclusions = {
            record.name for record in FIRST_RELEASE_LOCATIONS if record.default_excluded
        }
        actual_exclusions = {
            location.name
            for location in self.multiworld.get_locations(self.player)
            if location.address is not None
            and location.progress_type == LocationProgressType.EXCLUDED
        }
        self.assertEqual(18, len(expected_exclusions))
        self.assertEqual(expected_exclusions, actual_exclusions)

        progression = self.world.create_item("Spargus Field Orders")
        useful = self.world.create_item("Progressive Armor")
        filler = self.world.create_item("Health Refill")
        trap = self.world.create_item("Sandstorm Trap")
        for name in expected_exclusions:
            with self.subTest(location=name):
                location = self.multiworld.get_location(name, self.player)
                self.assertFalse(
                    location.can_fill(
                        self.multiworld.state, progression, check_access=False
                    )
                )
                self.assertFalse(
                    location.can_fill(self.multiworld.state, useful, check_access=False)
                )
                self.assertTrue(
                    location.can_fill(self.multiworld.state, filler, check_access=False)
                )
                self.assertTrue(
                    location.can_fill(self.multiworld.state, trap, check_access=False)
                )

    def test_milestone_5_regions_are_explicitly_permissive_scaffolding(self) -> None:
        self.assertEqual(2, len(self.multiworld.regions))
        self.assertTrue(self.can_reach_region(PERMISSIVE_SCAFFOLD_REGION_NAME))
        self.assertTrue(
            all(
                location.can_reach(self.multiworld.state)
                for location in self.multiworld.get_locations(self.player)
            )
        )
        self.assertEqual({}, self.multiworld.local_early_items[self.player])

    def test_filler_pool_uses_one_weighted_draw_for_all_93_slots(self) -> None:
        expected_names = [record.name for record in FILLER_ITEMS]
        expected_weights = dict(self.world.resolved_options.filler_item_weights)
        self.multiworld.itempool.clear()

        with patch.object(
            self.world.random, "choices", wraps=self.world.random.choices
        ) as choices:
            self.world.create_items()

        choices.assert_called_once_with(
            expected_names,
            weights=[expected_weights[name] for name in expected_names],
            k=93,
        )

    def test_first_release_slot_data_contract_is_stable(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual(SLOT_DATA_KEYS, set(slot_data))
        self.assertEqual(ITEM_TABLE_HASH, slot_data["item_table_hash"])
        self.assertEqual(LOCATION_TABLE_HASH, slot_data["location_table_hash"])
        self.assertEqual(MISSION_TABLE_HASH, slot_data["mission_table_hash"])
        self.assertEqual(
            SUPPORTED_RESOLVED_OPTIONS_HASH, slot_data["resolved_options_hash"]
        )
        self.assertEqual(str(self.multiworld.seed_name), slot_data["seed_identifier"])
        self.assertEqual(72, slot_data["goal"]["native_task_id"])


class Jak3FixedSeedGenerationTest(WorldTestBase):
    game = GAME_NAME
    auto_construct = False

    def _snapshot(self, seed: int) -> tuple:
        self.world_setup(seed)
        return (
            tuple(
                (item.name, item.code, item.classification)
                for item in self.multiworld.itempool
            ),
            tuple(
                sorted(
                    (
                        location.name,
                        location.address,
                        location.progress_type,
                        location.locked,
                        location.show_in_spoiler,
                        location.item.name if location.item else None,
                        location.item.code if location.item else None,
                    )
                    for location in self.multiworld.get_locations(self.player)
                )
            ),
            self.world.fill_slot_data(),
            dict(self.multiworld.local_early_items[self.player]),
        )

    def test_static_pool_generation_is_reproducible_for_fixed_seeds(self) -> None:
        for seed in (0, 1, 743_000_000):
            with self.subTest(seed=seed):
                self.assertEqual(self._snapshot(seed), self._snapshot(seed))

    def test_seed_zero_weighted_filler_distribution_is_frozen(self) -> None:
        self.world_setup(0)
        filler_names = {record.name for record in FILLER_ITEMS}
        counts = Counter(
            item.name for item in self.multiworld.itempool if item.name in filler_names
        )
        self.assertEqual(93, counts.total())
        self.assertEqual({}, dict(self.multiworld.local_early_items[self.player]))
        self.assertEqual(
            {
                "Precursor Orb Pack (5)": 18,
                "Precursor Orb Pack (10)": 8,
                "Precursor Orb Pack (25)": 3,
                "Skull Gem Pack (1)": 10,
                "Skull Gem Pack (3)": 5,
                "Skull Gem Pack (5)": 1,
                "Red Ammo Refill": 10,
                "Yellow Ammo Refill": 4,
                "Blue Ammo Refill": 7,
                "Dark Ammo Refill": 5,
                "Health Refill": 3,
                "Light Eco Refill": 3,
                "Dark Eco Refill": 10,
                "Vehicle Repair": 5,
                "Vehicle Turbo Refill": 1,
            },
            dict(counts),
        )
