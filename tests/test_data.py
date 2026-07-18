import unittest

from worlds.jak3.data import (
    ACTIVITIES,
    ACTIVITY_BY_ID,
    ACTIVITY_REQUIREMENTS,
    EQUIPMENT,
    ITEM_NAME_TO_ID,
    LOCATION_NAME_TO_ID,
    MISSION_BY_ID,
    MISSION_REQUIREMENTS,
    MISSIONS,
)


class MissionDataTest(unittest.TestCase):
    def test_native_story_task_range_is_complete(self) -> None:
        self.assertEqual(list(range(6, 72)), [mission.task_id for mission in MISSIONS])

    def test_mission_keys_and_names_are_unique(self) -> None:
        self.assertEqual(len(MISSIONS), len({mission.key for mission in MISSIONS}))
        self.assertEqual(len(MISSIONS), len({mission.name for mission in MISSIONS}))

    def test_network_ids_are_unique_and_separated(self) -> None:
        all_ids = list(ITEM_NAME_TO_ID.values()) + list(LOCATION_NAME_TO_ID.values())
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_goal_tasks_exist(self) -> None:
        for task_id in (34, 60, 62, 66, 70, 71):
            self.assertIn(task_id, MISSION_BY_ID)

    def test_optional_native_task_range_is_complete(self) -> None:
        self.assertEqual(list(range(73, 138)), [activity.task_id for activity in ACTIVITIES])

    def test_progression_and_filler_pool_balances_locations(self) -> None:
        progression_count = len(MISSIONS) - 1 + sum(item.copies for item in EQUIPMENT)
        self.assertGreater(len(MISSIONS) + len(ACTIVITIES), progression_count)

    def test_equipment_kinds_and_names_are_unique(self) -> None:
        self.assertEqual(len(EQUIPMENT), len({item.kind for item in EQUIPMENT}))
        self.assertEqual(len(EQUIPMENT), len({item.name for item in EQUIPMENT}))

    def test_every_requirement_references_an_available_copy(self) -> None:
        copies = {item.name: item.copies for item in EQUIPMENT}
        for table in (MISSION_REQUIREMENTS, ACTIVITY_REQUIREMENTS):
            for task_id, requirements in table.items():
                self.assertIn(
                    task_id,
                    MISSION_BY_ID if table is MISSION_REQUIREMENTS else ACTIVITY_BY_ID,
                )
                for name, count in requirements:
                    self.assertIn(name, copies)
                    self.assertGreaterEqual(copies[name], count)


if __name__ == "__main__":
    unittest.main()
