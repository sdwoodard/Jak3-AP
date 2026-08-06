import unittest

from worlds.jak3.data import (
    ACTIVITIES,
    ACTIVITY_BY_ID,
    ACTIVITY_REQUIREMENTS,
    EQUIPMENT,
    FILLER_DATA,
    ITEM_ID_DATA,
    ITEM_NAME_TO_ID,
    ITEM_TABLE_FINGERPRINT,
    LEGACY_ID_TABLE_VERSION,
    LOCATION_ID_DATA,
    LOCATION_NAME_TO_ID,
    LOCATION_TABLE_FINGERPRINT,
    MISSION_BY_ID,
    MISSION_REQUIREMENTS,
    MISSIONS,
    StableIdData,
    TRAP_DATA,
    build_name_to_id,
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

    def test_duplicate_item_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate item name"):
            build_name_to_id(
                (StableIdData("Duplicate", 1), StableIdData("Duplicate", 2)),
                "item",
            )

    def test_duplicate_item_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate item ID 1"):
            build_name_to_id(
                (StableIdData("First", 1), StableIdData("Second", 1)),
                "item",
            )

    def test_duplicate_location_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate location name"):
            build_name_to_id(
                (StableIdData("Duplicate", 1), StableIdData("Duplicate", 2)),
                "location",
            )

    def test_duplicate_location_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate location ID 1"):
            build_name_to_id(
                (StableIdData("First", 1), StableIdData("Second", 1)),
                "location",
            )

    def test_table_creation_is_deterministic(self) -> None:
        rows = (StableIdData("Zulu", 2), StableIdData("Alpha", 1))
        expected = [("Alpha", 1), ("Zulu", 2)]
        self.assertEqual(expected, list(build_name_to_id(rows, "item").items()))
        self.assertEqual(expected, list(build_name_to_id(reversed(rows), "item").items()))

    def test_legacy_table_fingerprints_are_frozen(self) -> None:
        self.assertEqual(1, LEGACY_ID_TABLE_VERSION)
        self.assertEqual(
            "565f44e4b4e56f562163eb29e3fb06f720eb8f295c627fde3ce923be0e770738",
            ITEM_TABLE_FINGERPRINT,
        )
        self.assertEqual(
            "25dba961f30fae8987a3f426f39ad00d584faaa3323ffb877e562152c80e64b8",
            LOCATION_TABLE_FINGERPRINT,
        )

    def test_every_current_network_id_is_an_explicit_record_field(self) -> None:
        self.assertEqual(106, len(ITEM_ID_DATA))
        self.assertEqual(131, len(LOCATION_ID_DATA))
        self.assertEqual(ITEM_NAME_TO_ID, {row.name: row.code for row in ITEM_ID_DATA})
        self.assertEqual(LOCATION_NAME_TO_ID, {row.name: row.code for row in LOCATION_ID_DATA})
        self.assertTrue(all(mission.location_id for mission in MISSIONS))
        self.assertTrue(all(activity.location_id for activity in ACTIVITIES))
        self.assertTrue(all(equipment.item_id for equipment in EQUIPMENT))
        self.assertTrue(all(item.item_id for item in FILLER_DATA + TRAP_DATA))

    def test_goal_tasks_exist(self) -> None:
        for task_id in (34, 60, 62, 66, 70, 71):
            self.assertIn(task_id, MISSION_BY_ID)

    def test_optional_native_task_range_is_complete(self) -> None:
        self.assertEqual(list(range(73, 138)), [activity.task_id for activity in ACTIVITIES])

    def test_task_88_uses_its_source_node_alias(self) -> None:
        activity = ACTIVITY_BY_ID[88]
        self.assertEqual(activity.key, "wascity-bbush-get-to-19")
        self.assertEqual(activity.name, "Spargus Discovery 19")

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
