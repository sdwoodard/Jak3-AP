from collections import Counter

from test.bases import WorldTestBase

from worlds.jak3.data import (
    ACTIVITIES,
    EQUIPMENT,
    FILLERS,
    GAME_NAME,
    LOGIC_ITEM_NAMES,
    MISSION_BY_ID,
    MISSION_REQUIREMENTS,
    MISSIONS,
    STARTING_MISSION_ID,
    TRAPS,
)
from worlds.jak3.options import SUPPORTED_FIRST_RELEASE_OPTIONS


class Jak3WorldTest(WorldTestBase):
    game = GAME_NAME

    def test_world_uses_the_resolved_first_release_profile(self) -> None:
        self.assertEqual(SUPPORTED_FIRST_RELEASE_OPTIONS, self.world.resolved_options)

    def test_location_and_pool_counts_match(self) -> None:
        addressed = [location for location in self.multiworld.get_locations(self.player) if location.address]
        own_pool = [item for item in self.multiworld.itempool if item.player == self.player]
        self.assertEqual(len(MISSIONS) + len(ACTIVITIES), len(addressed))
        self.assertEqual(len(addressed), len(own_pool))

    def test_starting_mission_is_reachable(self) -> None:
        start = next(mission for mission in MISSIONS if mission.task_id == STARTING_MISSION_ID)
        self.assertTrue(self.can_reach_location(start.location_name))

    def test_locked_mission_requires_its_unlock(self) -> None:
        mission = next(mission for mission in MISSIONS if mission.task_id == 12)
        self.assertFalse(self.can_reach_location(mission.location_name))
        self.collect_by_name(mission.item_name)
        self.assertTrue(self.can_reach_location(mission.location_name))

    def test_mission_requires_unlock_and_each_progressive_tier(self) -> None:
        mission = next(mission for mission in MISSIONS if mission.task_id == 47)
        self.collect_by_name(mission.item_name)
        self.collect_by_name(("Progressive Blaster", "Progressive Vulcan Fury", "Progressive Peace Maker"))
        scatter = self.get_items_by_name("Progressive Scatter Gun")
        self.collect(scatter[:2])
        self.assertFalse(self.can_reach_location(mission.location_name))
        self.collect(scatter[2])
        self.assertTrue(self.can_reach_location(mission.location_name))

    def test_equipment_copy_counts(self) -> None:
        own_pool = [item for item in self.multiworld.itempool if item.player == self.player]
        for equipment in EQUIPMENT:
            self.assertEqual(equipment.copies, sum(item.name == equipment.name for item in own_pool))

    def test_current_minimal_pool_composition(self) -> None:
        own_pool = [item for item in self.multiworld.itempool if item.player == self.player]
        counts = Counter(item.name for item in own_pool)
        mission_unlock_count = sum(
            counts[mission.item_name]
            for mission in MISSIONS
            if mission.task_id != STARTING_MISSION_ID
        )
        equipment_count = sum(counts[equipment.name] for equipment in EQUIPMENT)
        filler_count = sum(counts[name] for name in FILLERS)
        trap_count = sum(counts[name] for name in TRAPS)

        self.assertEqual(65, mission_unlock_count)
        self.assertEqual(38, equipment_count)
        self.assertEqual(28, filler_count)
        self.assertEqual(0, trap_count)
        self.assertEqual(131, len(own_pool))

    def test_first_challenge_requires_one_mission_unlock(self) -> None:
        activity = ACTIVITIES[0]
        self.assertFalse(self.can_reach_location(activity.location_name))
        self.collect_by_name(MISSIONS[1].item_name)
        self.assertFalse(self.can_reach_location(activity.location_name))
        self.collect_by_name("Tough Puppy")
        self.assertTrue(self.can_reach_location(activity.location_name))

    def test_every_logic_item_is_classified_as_progression(self) -> None:
        for name in LOGIC_ITEM_NAMES:
            self.assertTrue(self.get_item_by_name(name).advancement, name)

    def test_optional_capacity_and_armor_are_not_required_progression(self) -> None:
        for name in ("Progressive Red Ammo Capacity", "Progressive Armor", "Progressive Dark Jak Power"):
            self.assertFalse(self.get_item_by_name(name).advancement, name)

    def test_current_region_construction_is_stable(self) -> None:
        self.assertEqual(len(MISSIONS), len(self.world.mission_entrances))
        self.assertEqual(len(ACTIVITIES), len(self.world.activity_entrances))
        self.assertEqual(2 + len(MISSIONS) + len(ACTIVITIES) + 1, len(self.multiworld.regions))
        self.assertEqual(
            1,
            sum(
                location.name == "Victory"
                for location in self.multiworld.get_locations(self.player)
            ),
        )

    def test_task_71_goal_is_retained_as_legacy_behavior(self) -> None:
        mission = MISSION_BY_ID[71]
        self.assertFalse(self.can_reach_location("Victory"))
        self.collect_by_name(mission.item_name)
        for name, count in MISSION_REQUIREMENTS[71]:
            self.collect(self.get_items_by_name(name)[:count])
        self.assertTrue(self.can_reach_location("Victory"))

    def test_current_slot_data_contract_is_stable(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertEqual(
            {
                "goal",
                "completion_condition",
                "specific_mission",
                "mission_count",
                "trap_duration",
                "starting_task",
                "task_ids",
                "activity_unlock_counts",
                "mission_requirements",
                "activity_requirements",
                "equipment",
                "filler",
            },
            set(slot_data),
        )
        self.assertEqual(0, slot_data["goal"])
        self.assertEqual(0, slot_data["completion_condition"])
        self.assertEqual(71, slot_data["specific_mission"])
        self.assertEqual(66, slot_data["mission_count"])
        self.assertEqual(6, slot_data["starting_task"])
        self.assertEqual(65, len(slot_data["task_ids"]))
        self.assertEqual(65, len(slot_data["activity_unlock_counts"]))


class Jak3FixedSeedGenerationTest(WorldTestBase):
    game = GAME_NAME
    auto_construct = False

    def _snapshot(self, seed: int) -> tuple:
        self.world_setup(seed)
        return (
            tuple((item.name, item.code, item.classification) for item in self.multiworld.itempool),
            tuple(
                sorted(
                    (location.name, location.address)
                    for location in self.multiworld.get_locations(self.player)
                )
            ),
            self.world.fill_slot_data(),
            dict(self.multiworld.local_early_items[self.player]),
        )

    def test_current_minimal_generation_is_reproducible_for_fixed_seeds(self) -> None:
        for seed in (0, 1, 743_000_000):
            with self.subTest(seed=seed):
                self.assertEqual(self._snapshot(seed), self._snapshot(seed))
