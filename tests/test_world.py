from test.bases import WorldTestBase

from worlds.jak3.data import (
    ACTIVITIES,
    EQUIPMENT,
    GAME_NAME,
    LOGIC_ITEM_NAMES,
    MISSIONS,
    STARTING_MISSION_ID,
)


class Jak3WorldTest(WorldTestBase):
    game = GAME_NAME

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


class Jak3SpecificGoalTest(WorldTestBase):
    game = GAME_NAME
    options = {
        "jak_3_completion_condition": "complete_specific_mission",
        "specific_mission_for_completion": "defeat_cyber_errol",
    }

    def test_goal_requires_all_final_mission_gear(self) -> None:
        self.collect_all_but("Dune Hopper")
        self.assertFalse(self.can_reach_location("Victory"))
        self.collect_by_name("Dune Hopper")
        self.assertTrue(self.can_reach_location("Victory"))
