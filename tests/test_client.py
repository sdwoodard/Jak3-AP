import unittest

from worlds.jak3.client import _goal_string_literal


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


if __name__ == "__main__":
    unittest.main()
