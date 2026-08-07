import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"


class ContinuousIntegrationWorkflowTest(unittest.TestCase):
    def test_push_and_pull_request_ci_runs_available_checks(self) -> None:
        source = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^  push:$")
        self.assertRegex(source, r"(?m)^  pull_request:$")
        for command in (
            "ruff check",
            "ruff format --check",
            "mypy",
            "build_apworld.ps1",
            "python -m pytest",
        ):
            with self.subTest(command=command):
                self.assertIn(command, source)
        self.assertTrue(re.search(r"AP_TEST_WORLDS\s*=\s*\"jak3\"", source))
        self.assertGreaterEqual(source.count("worlds/jak3/persistence.py"), 2)
        self.assertIn("tests/test_persistence.py", source)


if __name__ == "__main__":
    unittest.main()
