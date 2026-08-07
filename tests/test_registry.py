import hashlib
import unittest
from dataclasses import replace

from worlds.jak3.data import ITEM_ID_DATA as LEGACY_ITEM_ID_DATA
from worlds.jak3.data import LOCATION_ID_DATA as LEGACY_LOCATION_ID_DATA
from worlds.jak3.legacy_ids import (
    FROZEN_LEGACY_ITEM_IDS,
    FROZEN_LEGACY_LOCATION_IDS,
)
from worlds.jak3.registry import (
    EVENT_LOCATIONS,
    FIRST_RELEASE_ITEMS,
    FIRST_RELEASE_LOCATIONS,
    ITEM_TABLE_HASH,
    LOCATION_TABLE_HASH,
    MAJOR_REWARD_LOCATIONS,
    MISSIONS,
    MISSION_BY_TASK_ID,
    MISSION_TABLE_HASH,
    ORB_THRESHOLD_LOCATIONS,
    PROGRESSION_ITEMS,
    RESERVED_LEGACY_ITEM_IDS,
    RESERVED_LEGACY_LOCATION_IDS,
    SELECTED_SIDE_LOCATIONS,
    STORY_COMPLETION_LOCATIONS,
    USEFUL_ITEMS,
    VICTORY_EVENT,
    serialize_item_registry,
    serialize_location_registry,
    serialize_mission_registry,
    validate_registry,
    validate_mission_registry,
)


class FirstReleaseRegistryTest(unittest.TestCase):
    def test_default_item_instance_counts_match_the_design(self) -> None:
        self.assertEqual(26, sum(record.pool_count for record in PROGRESSION_ITEMS))
        self.assertEqual(28, sum(record.pool_count for record in USEFUL_ITEMS))

    def test_default_location_family_counts_match_the_design(self) -> None:
        self.assertEqual(61, len(STORY_COMPLETION_LOCATIONS))
        self.assertEqual(38, len(MAJOR_REWARD_LOCATIONS))
        self.assertEqual(24, len(SELECTED_SIDE_LOCATIONS))
        self.assertEqual(24, len(ORB_THRESHOLD_LOCATIONS))
        self.assertEqual(147, len(FIRST_RELEASE_LOCATIONS))

    def test_default_location_native_identity_sets_match_the_design(self) -> None:
        self.assertEqual(
            set(range(10, 36)) | set(range(37, 72)),
            {record.native_task_id for record in STORY_COMPLETION_LOCATIONS},
        )
        self.assertEqual(
            {
                10,
                11,
                12,
                23,
                36,
                39,
                41,
                44,
                48,
                63,
                67,
                84,
                93,
                98,
                102,
                109,
                113,
                119,
                129,
                132,
                145,
                146,
                149,
                152,
                162,
                167,
                175,
                182,
                191,
                195,
                200,
                232,
                238,
                240,
                243,
                252,
                256,
                259,
            },
            {record.native_node_id for record in MAJOR_REWARD_LOCATIONS},
        )
        self.assertEqual(
            set(range(114, 138)),
            {record.native_task_id for record in SELECTED_SIDE_LOCATIONS},
        )
        self.assertEqual(
            set(range(25, 601, 25)),
            {record.orb_threshold for record in ORB_THRESHOLD_LOCATIONS},
        )

    def test_duplicate_item_names_and_ids_fail(self) -> None:
        first, second = FIRST_RELEASE_ITEMS[:2]
        with self.assertRaisesRegex(ValueError, "Duplicate item name"):
            validate_registry(items=(first, replace(second, name=first.name)))
        with self.assertRaisesRegex(ValueError, "Duplicate item ID"):
            validate_registry(items=(first, replace(second, code=first.code)))

    def test_duplicate_location_names_and_ids_fail(self) -> None:
        first, second = FIRST_RELEASE_LOCATIONS[:2]
        with self.assertRaisesRegex(ValueError, "Duplicate location name"):
            validate_registry(locations=(first, replace(second, name=first.name)))
        with self.assertRaisesRegex(ValueError, "Duplicate location ID"):
            validate_registry(locations=(first, replace(second, code=first.code)))

    def test_retired_ids_cannot_be_reused(self) -> None:
        retired = RESERVED_LEGACY_ITEM_IDS[0]
        with self.assertRaisesRegex(ValueError, "reserved legacy item ID"):
            validate_registry(
                items=(replace(FIRST_RELEASE_ITEMS[0], code=retired.code),)
            )

        retired_location = RESERVED_LEGACY_LOCATION_IDS[0]
        with self.assertRaisesRegex(ValueError, "reserved legacy network ID"):
            validate_registry(
                items=(replace(FIRST_RELEASE_ITEMS[0], code=retired_location.code),)
            )

        jetboard = next(
            record for record in FIRST_RELEASE_ITEMS if record.code == 743_000_108
        )
        renamed_items = tuple(
            replace(record, name="Renamed Jetboard") if record is jetboard else record
            for record in FIRST_RELEASE_ITEMS
        )
        with self.assertRaisesRegex(ValueError, "retained legacy item concept"):
            validate_registry(items=renamed_items)

        refamilied_items = tuple(
            replace(record, family="vehicle") if record is jetboard else record
            for record in FIRST_RELEASE_ITEMS
        )
        with self.assertRaisesRegex(ValueError, "retained legacy item concept"):
            validate_registry(items=refamilied_items)

        story_location = next(
            record for record in FIRST_RELEASE_LOCATIONS if record.code == 743_001_010
        )
        changed_locations = tuple(
            replace(record, native_task_id=999) if record is story_location else record
            for record in FIRST_RELEASE_LOCATIONS
        )
        with self.assertRaisesRegex(ValueError, "retained legacy location concept"):
            validate_registry(locations=changed_locations)

        changed_reservations = (
            replace(
                RESERVED_LEGACY_ITEM_IDS[0],
                legacy_name="Changed retired item concept",
            ),
            *RESERVED_LEGACY_ITEM_IDS[1:],
        )
        with self.assertRaisesRegex(ValueError, "reservations were changed"):
            validate_registry(item_reservations=changed_reservations)

    def test_duplicate_mission_and_profile_ids_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate native mission task ID"):
            validate_mission_registry(
                missions=(MISSIONS[0], replace(MISSIONS[1], task_id=6))
            )

    def test_registry_serialization_ignores_source_declaration_order(self) -> None:
        self.assertEqual(
            serialize_item_registry(),
            serialize_item_registry(
                reversed(FIRST_RELEASE_ITEMS), reversed(RESERVED_LEGACY_ITEM_IDS)
            ),
        )
        self.assertEqual(
            serialize_location_registry(),
            serialize_location_registry(
                reversed(FIRST_RELEASE_LOCATIONS),
                reversed(RESERVED_LEGACY_LOCATION_IDS),
            ),
        )
        self.assertEqual(
            serialize_mission_registry(),
            serialize_mission_registry(reversed(MISSION_BY_TASK_ID.values())),
        )

    def test_table_hashes_are_frozen_and_match_serialized_bytes(self) -> None:
        self.assertEqual(
            "eb557676187512253327e2fdcbad2f8f49f62236d019fdd8129f14cb9987f99c",
            ITEM_TABLE_HASH,
        )
        self.assertEqual(
            "f1c74c5a9da78e8e2b87a57ae283b514038be521699367342c0a555826333793",
            LOCATION_TABLE_HASH,
        )
        self.assertEqual(
            "2e6e631ed650ceb860921e3feb066a85f6d858038a0f46f510a616d17633f09a",
            MISSION_TABLE_HASH,
        )
        self.assertEqual(
            ITEM_TABLE_HASH, hashlib.sha256(serialize_item_registry()).hexdigest()
        )
        self.assertEqual(
            LOCATION_TABLE_HASH,
            hashlib.sha256(serialize_location_registry()).hexdigest(),
        )
        self.assertEqual(
            MISSION_TABLE_HASH, hashlib.sha256(serialize_mission_registry()).hexdigest()
        )

    def test_every_legacy_id_is_retained_or_reserved(self) -> None:
        frozen_items = {record.code for record in FROZEN_LEGACY_ITEM_IDS}
        frozen_locations = {record.code for record in FROZEN_LEGACY_LOCATION_IDS}
        active_items = {record.code for record in FIRST_RELEASE_ITEMS}
        reserved_items = {record.code for record in RESERVED_LEGACY_ITEM_IDS}
        active_locations = {record.code for record in FIRST_RELEASE_LOCATIONS}
        reserved_locations = {record.code for record in RESERVED_LEGACY_LOCATION_IDS}
        self.assertEqual(
            frozen_items,
            active_items & frozen_items | reserved_items,
        )
        self.assertEqual(
            frozen_locations,
            active_locations & frozen_locations | reserved_locations,
        )
        self.assertFalse(active_items & reserved_items)
        self.assertFalse(active_locations & reserved_locations)

        self.assertEqual(
            {(record.legacy_name, record.code) for record in FROZEN_LEGACY_ITEM_IDS},
            {(record.name, record.code) for record in LEGACY_ITEM_ID_DATA},
        )
        self.assertEqual(
            {
                (record.legacy_name, record.code)
                for record in FROZEN_LEGACY_LOCATION_IDS
            },
            {(record.name, record.code) for record in LEGACY_LOCATION_ID_DATA},
        )
        self.assertEqual(
            {
                (record.code, record.legacy_name)
                for record in FROZEN_LEGACY_ITEM_IDS
                if record.retained_concept is None
            },
            {(record.code, record.legacy_name) for record in RESERVED_LEGACY_ITEM_IDS},
        )
        self.assertEqual(
            {
                (record.code, record.legacy_name)
                for record in FROZEN_LEGACY_LOCATION_IDS
                if record.retained_concept is None
            },
            {
                (record.code, record.legacy_name)
                for record in RESERVED_LEGACY_LOCATION_IDS
            },
        )

    def test_task_36_is_retired_and_task_72_is_an_event(self) -> None:
        self.assertNotIn(
            36, {location.native_task_id for location in FIRST_RELEASE_LOCATIONS}
        )
        task_36 = next(
            record
            for record in RESERVED_LEGACY_LOCATION_IDS
            if record.code == 743_001_036
        )
        self.assertIn("Complete Haven Vehicle Training", task_36.legacy_name)
        self.assertEqual(72, VICTORY_EVENT.native_task_id)
        self.assertIsNone(VICTORY_EVENT.code)
        self.assertNotIn(
            72, {location.native_task_id for location in FIRST_RELEASE_LOCATIONS}
        )

    def test_event_records_never_have_network_ids(self) -> None:
        self.assertTrue(EVENT_LOCATIONS)
        self.assertTrue(all(event.code is None for event in EVENT_LOCATIONS))

    def test_task_88_preserves_native_id_and_normalized_alias(self) -> None:
        mission = MISSION_BY_TASK_ID[88]
        self.assertEqual("desert-bbush-get-to-19", mission.native_alias)
        self.assertEqual("wascity-bbush-get-to-19", mission.runtime_alias)

    def test_default_exclusions_are_frozen(self) -> None:
        self.assertEqual(
            {127, 129, 130, 131, 132, 136},
            {
                location.native_task_id
                for location in SELECTED_SIDE_LOCATIONS
                if location.default_excluded
            },
        )
        self.assertEqual(
            set(range(325, 601, 25)),
            {
                location.orb_threshold
                for location in ORB_THRESHOLD_LOCATIONS
                if location.default_excluded
            },
        )


if __name__ == "__main__":
    unittest.main()
