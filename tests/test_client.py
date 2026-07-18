import unittest

from pathlib import Path
from tempfile import TemporaryDirectory

from worlds.jak3.client import (
    _goal_path_literal,
    _goal_string_literal,
    parse_binding,
    parse_notification_index,
)


class ClientProtocolTest(unittest.TestCase):
    def test_goal_notification_string_is_escaped(self) -> None:
        encoded = _goal_string_literal('Received: \\ "item"')
        self.assertTrue(encoded.startswith('"Received: '))
        self.assertTrue(encoded.endswith('"'))
        self.assertIn('\\\\', encoded)
        self.assertIn('\\"item\\"', encoded)

    def test_goal_notification_string_is_ascii_and_bounded(self) -> None:
        encoded = _goal_string_literal("\u00e9" + "x" * 200)
        self.assertTrue(encoded.startswith('"?'))
        self.assertLessEqual(len(encoded), 98)

    def test_goal_state_path_is_escaped_without_notification_truncation(self) -> None:
        encoded = _goal_path_literal('D:\\AP State\\jak3-\u00e9.tmp')
        self.assertEqual(encoded, '"D:\\\\AP State\\\\jak3-\u00e9.tmp"')

    def test_goal_state_path_rejects_control_characters(self) -> None:
        with self.assertRaises(ValueError):
            _goal_path_literal("D:\\bad\npath")

    def test_bridge_snapshot_binding_and_notification(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.tmp"
            path.write_text("slot 123\nseed 456\nnotification 7\n", encoding="utf-8")
            self.assertEqual(parse_binding(path), (123, 456))
            self.assertEqual(parse_notification_index(path), 7)


if __name__ == "__main__":
    unittest.main()
