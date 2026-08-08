import hashlib
import subprocess
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPOSITORY_ROOT / "tools" / "install_opengoal_bridge.ps1"
BRIDGE_SOURCE = (
    REPOSITORY_ROOT
    / "mod"
    / "opengoal"
    / "goal_src"
    / "jak3"
    / "pc"
    / "features"
    / "archipelago.gc"
)


class DeveloperInstallerTest(unittest.TestCase):
    def make_project(self, root: Path, project_data: bytes) -> tuple[Path, Path]:
        project = root / "goal_src" / "jak3" / "dgos" / "game.gd"
        destination = root / "goal_src" / "jak3" / "pc" / "features" / "archipelago.gc"
        project.parent.mkdir(parents=True)
        destination.parent.mkdir(parents=True)
        project.write_bytes(project_data)
        return project, destination

    def run_installer(self, root: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(INSTALL_SCRIPT),
                "-OpenGoalRepository",
                str(root),
            ),
            capture_output=True,
            check=False,
            text=True,
        )

    def test_crlf_project_install_is_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project, destination = self.make_project(
                root,
                b'(dgo "GAME.CGO"\r\n  "task-control.o"\r\n  "scene.o"\r\n)\r\n',
            )

            first = self.run_installer(root)
            second = self.run_installer(root)
            reload_marker = destination.with_name(".archipelago-reload-required")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(destination.read_bytes(), BRIDGE_SOURCE.read_bytes())
            self.assertTrue(reload_marker.is_file())
            self.assertEqual(
                reload_marker.read_text(encoding="utf-8").strip(),
                hashlib.sha256(BRIDGE_SOURCE.read_bytes()).hexdigest(),
            )
            project_text = project.read_text(encoding="utf-8")
            self.assertEqual(project_text.count('"archipelago.o"'), 1)
            self.assertLess(
                project_text.index('"task-control.o"'),
                project_text.index('"archipelago.o"'),
            )

    def test_invalid_project_is_rejected_before_source_copy(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _project, destination = self.make_project(
                root,
                b'(dgo "GAME.CGO"\r\n  "scene.o"\r\n)\r\n',
            )
            destination.write_bytes(b"sentinel")

            result = self.run_installer(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(destination.read_bytes(), b"sentinel")

    def test_source_copy_failure_does_not_register_project(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project, destination = self.make_project(
                root,
                b'(dgo "GAME.CGO"\r\n  "task-control.o"\r\n  "scene.o"\r\n)\r\n',
            )
            original = project.read_bytes()
            destination.mkdir()
            (destination / destination.name).mkdir()

            result = self.run_installer(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(project.read_bytes(), original)
            self.assertNotIn(b'"archipelago.o"', project.read_bytes())


if __name__ == "__main__":
    unittest.main()
