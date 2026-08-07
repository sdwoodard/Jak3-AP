import unittest

from pathlib import Path

from worlds.jak3.client import Jak3Context, _goal_path_literal, _goal_string_literal


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SOURCE = (
    REPOSITORY_ROOT / "mod" / "opengoal" / "goal_src" / "jak3" / "pc" / "features"
    / "archipelago.gc"
)


class ClientProtocolTest(unittest.TestCase):
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
