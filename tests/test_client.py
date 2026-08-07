import unittest

from pathlib import Path
from types import SimpleNamespace

from worlds.jak3.client import Jak3Context, _goal_path_literal, _goal_string_literal
from worlds.jak3.option_resolution import SUPPORTED_FIRST_RELEASE_OPTIONS
from worlds.jak3.slot_data import build_slot_data


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SOURCE = (
    REPOSITORY_ROOT / "mod" / "opengoal" / "goal_src" / "jak3" / "pc" / "features"
    / "archipelago.gc"
)


class ClientProtocolTest(unittest.TestCase):
    def connected_context(self) -> Jak3Context:
        context = object.__new__(Jak3Context)
        context.auth = "Mutable Alias"
        context.slot_info = {3: SimpleNamespace(name="Canonical Jak Slot")}
        context.authenticated_slot = None
        context.slot_contract_error = ""
        context.persistence_contract_status = "not authenticated"
        context.persistence_binding_status = "not attempted"
        context.persistence_recovery_status = "not attempted"
        context.persistence_quarantine_status = "not attempted"
        context.persistence_read_only_failure = ""
        context.room_seed = ""
        return context

    def test_goal_protocol_string_is_escaped(self) -> None:
        self.assertEqual(_goal_string_literal("session\\value"), '"session\\\\value"')
        self.assertEqual(_goal_string_literal('session"value'), '"session\\"value"')

    def test_goal_protocol_string_is_ascii_and_bounded(self) -> None:
        self.assertEqual(_goal_string_literal("session-\u00e9"), '"session-?"')
        with self.assertRaises(ValueError):
            _goal_string_literal("x" * 97)

    def test_goal_state_path_is_escaped_without_short_string_limit(self) -> None:
        encoded = _goal_path_literal("D:\\AP State\\jak3-\u00e9.tmp")
        self.assertEqual(encoded, '"D:\\\\AP State\\\\jak3-\u00e9.tmp"')

    def test_goal_state_path_rejects_control_characters(self) -> None:
        with self.assertRaises(ValueError):
            _goal_path_literal("D:\\bad\npath")

    def test_client_requests_no_received_items(self) -> None:
        self.assertEqual(Jak3Context.items_handling, 0)

    def test_connected_uses_authenticated_seed_team_slot_and_canonical_name(self) -> None:
        context = self.connected_context()
        context.on_package("RoomInfo", {"seed_name": "diagnostic-room-name"})
        context.on_package(
            "Connected",
            {
                "team": 2,
                "slot": 3,
                "slot_data": build_slot_data(
                    SUPPORTED_FIRST_RELEASE_OPTIONS,
                    seed_identifier="authenticated-seed-identifier",
                ),
            },
        )

        self.assertEqual("diagnostic-room-name", context.room_seed)
        self.assertIsNotNone(context.authenticated_slot)
        assert context.authenticated_slot is not None
        self.assertEqual(
            "authenticated-seed-identifier",
            context.authenticated_slot.seed_identifier,
        )
        self.assertEqual(2, context.authenticated_slot.team)
        self.assertEqual(3, context.authenticated_slot.slot)
        self.assertEqual("Canonical Jak Slot", context.authenticated_slot.slot_name)
        self.assertEqual("validated", context.persistence_contract_status)
        self.assertIn("Milestone 7", context.persistence_binding_status)

    def test_incompatible_connected_contract_refuses_binding_read_only(self) -> None:
        context = self.connected_context()
        invalid = build_slot_data(
            SUPPORTED_FIRST_RELEASE_OPTIONS,
            seed_identifier="authenticated-seed-identifier",
        )
        invalid["item_table_hash"] = "0" * 64
        context.on_package(
            "Connected",
            {"team": 2, "slot": 3, "slot_data": invalid},
        )

        self.assertIsNone(context.authenticated_slot)
        self.assertEqual("rejected", context.persistence_contract_status)
        self.assertEqual("refused read-only", context.persistence_binding_status)
        self.assertIn("item_table_hash", context.persistence_read_only_failure)

    def test_connected_rejects_boolean_integer_version_alias(self) -> None:
        context = self.connected_context()
        invalid = build_slot_data(
            SUPPORTED_FIRST_RELEASE_OPTIONS,
            seed_identifier="authenticated-seed-identifier",
        )
        invalid["game_integration_version"] = True
        context.on_package(
            "Connected",
            {"team": 2, "slot": 3, "slot_data": invalid},
        )

        self.assertIsNone(context.authenticated_slot)
        self.assertEqual("rejected", context.persistence_contract_status)
        self.assertEqual("refused read-only", context.persistence_binding_status)
        self.assertIn("game_integration_version", context.persistence_read_only_failure)

    def test_goal_bridge_has_no_gameplay_hooks(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "ap-receive-",
            "ap-play-task!",
            "ap-start-game!",
            "ap-resync-items!",
            "task-resolution-close!",
            "send-event",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_goal_bridge_exports_unquoted_protocol_strings(self) -> None:
        source = BRIDGE_SOURCE.read_text(encoding="utf-8")
        self.assertIn('(format file "session_id ~S~%"', source)
        self.assertIn('(format file "message ~S~%"', source)


if __name__ == "__main__":
    unittest.main()
