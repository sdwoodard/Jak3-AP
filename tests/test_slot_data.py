import json
import re
import unittest
from dataclasses import replace
from pathlib import Path

from worlds.jak3.option_resolution import SUPPORTED_FIRST_RELEASE_OPTIONS
from worlds.jak3.registry import (
    ITEM_TABLE_HASH,
    LOCATION_TABLE_HASH,
    MISSION_TABLE_HASH,
)
from worlds.jak3.slot_data import (
    SLOT_DATA_KEYS,
    SUPPORTED_RESOLVED_OPTIONS_HASH,
    build_slot_data,
    serialize_slot_data,
    validate_slot_data,
)
from worlds.jak3.versions import (
    GAME_INTEGRATION_VERSION,
    ITEM_TABLE_VERSION,
    LOCATION_TABLE_VERSION,
    MISSION_PROFILE_VERSION,
    MISSION_TABLE_VERSION,
    PROTOCOL_VERSION,
    SLOT_DATA_VERSION,
    STATE_SCHEMA_VERSION,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GOAL_BRIDGE = (
    REPOSITORY_ROOT
    / "mod"
    / "opengoal"
    / "goal_src"
    / "jak3"
    / "pc"
    / "features"
    / "archipelago.gc"
)


class SlotDataContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = build_slot_data(SUPPORTED_FIRST_RELEASE_OPTIONS)

    def test_slot_data_has_only_the_versioned_first_release_shape(self) -> None:
        self.assertEqual(SLOT_DATA_KEYS, set(self.payload))
        self.assertNotIn("task_ids", self.payload)
        self.assertNotIn("mission_requirements", self.payload)
        self.assertNotIn("equipment", self.payload)
        self.assertNotIn("filler", self.payload)

    def test_slot_data_is_deterministic_and_json_safe(self) -> None:
        first = serialize_slot_data(SUPPORTED_FIRST_RELEASE_OPTIONS)
        second = serialize_slot_data(SUPPORTED_FIRST_RELEASE_OPTIONS)
        self.assertEqual(first, second)
        self.assertEqual(self.payload, json.loads(first.decode("utf-8")))
        self.assertTrue(first.endswith(b"\n"))

    def test_versions_hashes_and_goal_are_frozen(self) -> None:
        self.assertEqual(PROTOCOL_VERSION, self.payload["protocol_version"])
        self.assertEqual(
            GAME_INTEGRATION_VERSION, self.payload["game_integration_version"]
        )
        self.assertEqual(SLOT_DATA_VERSION, self.payload["slot_data_version"])
        self.assertEqual(STATE_SCHEMA_VERSION, self.payload["state_schema_version"])
        self.assertEqual(ITEM_TABLE_VERSION, self.payload["item_table_version"])
        self.assertEqual(LOCATION_TABLE_VERSION, self.payload["location_table_version"])
        self.assertEqual(MISSION_TABLE_VERSION, self.payload["mission_table_version"])
        self.assertEqual(
            MISSION_PROFILE_VERSION, self.payload["mission_profile_version"]
        )
        self.assertEqual(ITEM_TABLE_HASH, self.payload["item_table_hash"])
        self.assertEqual(LOCATION_TABLE_HASH, self.payload["location_table_hash"])
        self.assertEqual(MISSION_TABLE_HASH, self.payload["mission_table_hash"])
        self.assertEqual(
            "facdfa555f7c5804a5c5c0ebaf3db8e6260ba5f409f66e7bc22a1ab128a4c914",
            SUPPORTED_RESOLVED_OPTIONS_HASH,
        )
        self.assertEqual(
            {
                "mode": "complete_city_win",
                "native_task_id": 72,
                "finale_relic_requirement": 5,
            },
            self.payload["goal"],
        )

    def test_challenge_and_orb_contract_is_explicit(self) -> None:
        self.assertEqual(
            [127, 129, 130, 131, 132, 136],
            self.payload["challenge_policy"]["excluded_task_ids"],
        )
        self.assertEqual(
            list(range(114, 138)), self.payload["challenge_policy"]["selected_task_ids"]
        )
        self.assertEqual(
            list(range(25, 601, 25)),
            self.payload["orb_thresholds"]["enabled_thresholds"],
        )
        self.assertEqual(300, self.payload["orb_thresholds"]["progression_cap"])

    def test_incompatible_contract_is_rejected(self) -> None:
        changed = dict(self.payload)
        changed["item_table_hash"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "item_table_hash"):
            validate_slot_data(changed)

        changed = json.loads(json.dumps(self.payload))
        changed["features"]["traps"] = True
        with self.assertRaisesRegex(ValueError, "feature flags"):
            validate_slot_data(changed)

        unsupported = replace(SUPPORTED_FIRST_RELEASE_OPTIONS, trap_duration=21)
        with self.assertRaisesRegex(ValueError, "resolved_options_hash"):
            build_slot_data(unsupported)

    def test_goal_bridge_constants_match_python_contract(self) -> None:
        source = GOAL_BRIDGE.read_text(encoding="utf-8")
        integer_constants = {
            "AP-PROTOCOL-VERSION": PROTOCOL_VERSION,
            "AP-GAME-INTEGRATION-VERSION": GAME_INTEGRATION_VERSION,
            "AP-SLOT-DATA-VERSION": SLOT_DATA_VERSION,
            "AP-STATE-SCHEMA-VERSION": STATE_SCHEMA_VERSION,
            "AP-ITEM-TABLE-VERSION": ITEM_TABLE_VERSION,
            "AP-LOCATION-TABLE-VERSION": LOCATION_TABLE_VERSION,
            "AP-MISSION-TABLE-VERSION": MISSION_TABLE_VERSION,
            "AP-MISSION-PROFILE-VERSION": MISSION_PROFILE_VERSION,
        }
        for name, value in integer_constants.items():
            self.assertRegex(source, rf"\(defconstant {name} {value}\)")
        for digest in (ITEM_TABLE_HASH, LOCATION_TABLE_HASH, MISSION_TABLE_HASH):
            self.assertEqual(1, len(re.findall(re.escape(digest), source)))


if __name__ == "__main__":
    unittest.main()
