import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
RELEASE_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
CI_PREFLIGHT = REPOSITORY_ROOT / "tools" / "run_ci_checks.ps1"


class ContinuousIntegrationWorkflowTest(unittest.TestCase):
    def test_push_and_pull_request_ci_runs_shared_preflight(self) -> None:
        source = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^  push:$")
        self.assertRegex(source, r"(?m)^  pull_request:$")
        self.assertEqual(source.count("uses: actions/checkout@v7"), 2)
        self.assertIn("uses: actions/setup-python@v7", source)
        for invocation in (
            ".\\tools\\run_ci_checks.ps1 -Phase Static",
            ".\\tools\\run_ci_checks.ps1 -Phase Package",
            ".\\tools\\run_ci_checks.ps1 -Phase Tests -ArchipelagoPath .\\archipelago",
        ):
            with self.subTest(invocation=invocation):
                self.assertIn(invocation, source)

    def test_shared_preflight_owns_the_complete_ci_gate(self) -> None:
        source = CI_PREFLIGHT.read_text(encoding="utf-8")
        for command in (
            '"-m", "ruff", "check"',
            '"-m", "ruff", "format", "--check"',
            '"-m", "mypy"',
            '"build_apworld.ps1"',
            '"-m", "pytest"',
        ):
            with self.subTest(command=command):
                self.assertIn(command, source)
        self.assertIn('$env:AP_TEST_WORLDS = "jak3"', source)
        self.assertIn('$env:SKIP_REQUIREMENTS_UPDATE = "1"', source)
        self.assertGreaterEqual(source.count('"worlds/jak3/persistence.py"'), 2)
        self.assertIn('"tests/test_persistence.py"', source)
        self.assertIn('"AGENTS.md"', source)
        self.assertIn('"* text=auto eol=lf"', source)

    def test_release_and_ci_actions_use_the_current_node_runtime(self) -> None:
        ci_source = CI_WORKFLOW.read_text(encoding="utf-8")
        release_source = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        for obsolete in ("actions/checkout@v4", "actions/setup-python@v5"):
            self.assertNotIn(obsolete, ci_source)
        self.assertIn("uses: actions/checkout@v7", release_source)


if __name__ == "__main__":
    unittest.main()
