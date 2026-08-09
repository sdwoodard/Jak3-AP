import json
import os
import platform
import shutil
import subprocess
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from worlds.jak3.agents.bridge_manifest import parse_bridge_manifest
from worlds.jak3.agents.diagnostics import _process_start_identity


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPOSITORY_ROOT / "tools" / "install_opengoal_bridge.ps1"
BUILD_SCRIPT = REPOSITORY_ROOT / "tools" / "build_apworld.ps1"
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
BRIDGE_MANIFEST = REPOSITORY_ROOT / "mod" / "opengoal" / "bridge-modules.json"


class DeveloperInstallerTest(unittest.TestCase):
    def test_apworld_builder_is_byte_deterministic(self) -> None:
        with TemporaryDirectory() as directory:
            command = (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(BUILD_SCRIPT),
                "-OutputDirectory",
                directory,
            )
            first = subprocess.run(command, capture_output=True, check=False, text=True)
            artifact = Path(directory) / "jak3.apworld"
            first_payload = artifact.read_bytes() if artifact.is_file() else b""
            second = subprocess.run(
                command, capture_output=True, check=False, text=True
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_payload, artifact.read_bytes())
            with ZipFile(artifact) as archive:
                self.assertEqual(
                    {(2000, 1, 1, 0, 0, 0)},
                    {entry.date_time for entry in archive.infolist()},
                )

    def make_project(self, root: Path, project_data: bytes) -> tuple[Path, Path]:
        project = root / "goal_src" / "jak3" / "dgos" / "game.gd"
        destination = root / "goal_src" / "jak3" / "pc" / "features" / "archipelago.gc"
        project.parent.mkdir(parents=True)
        destination.parent.mkdir(parents=True)
        project.write_bytes(project_data)
        return project, destination

    def run_installer(
        self, root: Path, script: Path = INSTALL_SCRIPT
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-OpenGoalRepository",
                str(root),
            ),
            capture_output=True,
            check=False,
            text=True,
        )

    @staticmethod
    def make_manifest_consumer_fixture(root: Path, manifest: object) -> None:
        tools = root / "tools"
        tools.mkdir(parents=True)
        shutil.copy2(BUILD_SCRIPT, tools / BUILD_SCRIPT.name)
        shutil.copy2(INSTALL_SCRIPT, tools / INSTALL_SCRIPT.name)
        bridge = root / "mod" / "opengoal"
        bridge.mkdir(parents=True)
        (bridge / "bridge-modules.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        world = root / "worlds" / "jak3"
        icons = world / "icons"
        icons.mkdir(parents=True)
        shutil.copy2(REPOSITORY_ROOT / "worlds" / "jak3" / "archipelago.json", world)
        shutil.copy2(
            REPOSITORY_ROOT / "worlds" / "jak3" / "icons" / "jak3-logo.png",
            icons,
        )

    @staticmethod
    def copy_manifest_sources(root: Path, manifest: dict[str, object]) -> None:
        modules = manifest["modules"]
        assert isinstance(modules, list)
        for module in modules:
            assert isinstance(module, dict)
            relative = Path(str(module["source"]))
            destination = root / "mod" / "opengoal" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BRIDGE_MANIFEST.parent / relative, destination)

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
            manifest = parse_bridge_manifest(BRIDGE_MANIFEST.read_bytes())
            payloads = {
                str(module.resource): (
                    BRIDGE_MANIFEST.parent / Path(str(module.source))
                ).read_bytes()
                for module in manifest.modules
            }
            self.assertEqual(
                reload_marker.read_text(encoding="utf-8").strip(),
                manifest.source_set_sha256(payloads),
            )
            project_text = project.read_text(encoding="utf-8")
            self.assertEqual(project_text.count('"archipelago.o"'), 1)
            self.assertEqual(project_text.count('"archipelago-diagnostics.o"'), 1)
            self.assertLess(
                project_text.index('"task-control.o"'),
                project_text.index('"archipelago.o"'),
            )
            self.assertLess(
                project_text.index('"archipelago.o"'),
                project_text.index('"archipelago-diagnostics.o"'),
            )
            self.assertTrue(
                destination.with_name("archipelago-diagnostics.gc").is_file()
            )
            self.assertTrue(destination.with_name("archipelago-startup.gc").is_file())
            self.assertTrue(
                destination.with_name("archipelago-bridge-modules.json").is_file()
            )
            self.assertFalse(
                destination.with_name(".archipelago-install.lock").exists()
            )

    def test_installer_hashing_has_no_powershell_module_dependency(self) -> None:
        script = INSTALL_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("Get-FileHash -LiteralPath", script)
        self.assertIn("[System.Security.Cryptography.SHA256]::Create()", script)

    def test_powershell_consumers_enforce_the_exact_manifest_schema(self) -> None:
        builder = BUILD_SCRIPT.read_text(encoding="utf-8")
        installer = INSTALL_SCRIPT.read_text(encoding="utf-8")

        for script in (builder, installer):
            self.assertIn("function Assert-ExactJsonFields", script)
            self.assertIn(
                '@("manifest_version", "source_set_format", "object_anchor", "modules")',
                script,
            )
            self.assertIn(
                '@("name", "order", "phase", "source", "resource", "destination", "object")',
                script,
            )
        self.assertIn('$expectedPhases = @("pre_mi", "bridge", "bridge")', installer)
        self.assertIn("$module.phase -ne $expectedPhases[$index]", installer)

    def test_powershell_consumers_behaviorally_reject_malformed_manifests(
        self,
    ) -> None:
        mutations = (
            (
                "extra root field",
                lambda document: document.update({"unexpected": True}),
                "must contain exactly",
            ),
            (
                "extra module field",
                lambda document: document["modules"][0].update({"unexpected": True}),
                "must contain exactly",
            ),
            (
                "wrong phase",
                lambda document: document["modules"][0].update({"phase": "bridge"}),
                "canonical",
            ),
            (
                "string manifest version",
                lambda document: document.update({"manifest_version": "1"}),
                "scalar types",
            ),
            (
                "boolean manifest version",
                lambda document: document.update({"manifest_version": True}),
                "scalar types",
            ),
            (
                "string module order",
                lambda document: document["modules"][0].update({"order": "10"}),
                "scalar types",
            ),
            (
                "boolean module order",
                lambda document: document["modules"][0].update({"order": True}),
                "scalar types",
            ),
        )
        for label, mutate, expected_error in mutations:
            for consumer in ("builder", "installer"):
                with self.subTest(mutation=label, consumer=consumer):
                    with TemporaryDirectory() as directory:
                        fixture = Path(directory) / "repository"
                        document = json.loads(BRIDGE_MANIFEST.read_text("utf-8"))
                        mutate(document)
                        self.make_manifest_consumer_fixture(fixture, document)
                        if consumer == "builder":
                            result = subprocess.run(
                                (
                                    "powershell",
                                    "-NoProfile",
                                    "-ExecutionPolicy",
                                    "Bypass",
                                    "-File",
                                    str(fixture / "tools" / BUILD_SCRIPT.name),
                                    "-OutputDirectory",
                                    str(fixture / "dist"),
                                ),
                                capture_output=True,
                                check=False,
                                text=True,
                            )
                        else:
                            target = Path(directory) / "opengoal"
                            self.make_project(
                                target,
                                b'(dgo "GAME.CGO"\n  "task-control.o"\n)\n',
                            )
                            result = self.run_installer(
                                target,
                                fixture / "tools" / INSTALL_SCRIPT.name,
                            )
                        rendered = result.stdout + result.stderr
                        self.assertNotEqual(result.returncode, 0, rendered)
                        self.assertIn(expected_error, rendered)

    def test_apworld_builder_rejects_undeclared_bridge_sources_anywhere(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "repository"
            document = json.loads(BRIDGE_MANIFEST.read_text("utf-8"))
            self.make_manifest_consumer_fixture(fixture, document)
            self.copy_manifest_sources(fixture, document)
            undeclared = (
                fixture / "worlds" / "jak3" / "rogue" / "archipelago-undeclared.gc"
            )
            undeclared.parent.mkdir(parents=True)
            undeclared.write_text(";; undeclared test module\n", encoding="utf-8")

            result = subprocess.run(
                (
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(fixture / "tools" / BUILD_SCRIPT.name),
                    "-OutputDirectory",
                    str(fixture / "dist"),
                ),
                capture_output=True,
                check=False,
                text=True,
            )

            rendered = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, rendered)
            self.assertIn("undeclared", rendered.casefold())
            self.assertIn("rogue/archipelago-undeclared.gc", rendered)

    def test_installer_does_not_recover_an_aged_live_local_lock(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "repository"
            document = json.loads(BRIDGE_MANIFEST.read_text("utf-8"))
            self.make_manifest_consumer_fixture(fixture, document)
            script = fixture / "tools" / INSTALL_SCRIPT.name
            script_text = script.read_text("utf-8")
            shortened = script_text.replace(
                "[DateTime]::UtcNow.AddSeconds(30)",
                "[DateTime]::UtcNow.AddMilliseconds(250)",
                1,
            )
            self.assertNotEqual(shortened, script_text)
            script.write_text(shortened, encoding="utf-8")
            target = root / "opengoal"
            project, destination = self.make_project(
                target,
                b'(dgo "GAME.CGO"\n  "task-control.o"\n)\n',
            )
            original_project = project.read_bytes()
            lock_directory = destination.parent / ".archipelago-install.lock"
            lock_directory.mkdir()
            (lock_directory / "owner.json").write_text(
                json.dumps(
                    {
                        "token": "live-owner",
                        "process_id": os.getpid(),
                        "process_start_identity": _process_start_identity(os.getpid()),
                        "host": platform.node(),
                        "created_unix": 0,
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_installer(target, script)

            rendered = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, rendered)
            self.assertIn("Timed out waiting", rendered)
            self.assertTrue(lock_directory.is_dir())
            self.assertEqual(project.read_bytes(), original_project)
            self.assertFalse(destination.exists())

    def test_installer_recovers_a_lock_held_by_a_reused_pid(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "repository"
            document = json.loads(BRIDGE_MANIFEST.read_text("utf-8"))
            self.make_manifest_consumer_fixture(fixture, document)
            self.copy_manifest_sources(fixture, document)
            target = root / "opengoal"
            _project, destination = self.make_project(
                target,
                b'(dgo "GAME.CGO"\n  "task-control.o"\n)\n',
            )
            lock_directory = destination.parent / ".archipelago-install.lock"
            lock_directory.mkdir()
            (lock_directory / "owner.json").write_text(
                json.dumps(
                    {
                        "token": "reused-pid-owner",
                        "process_id": os.getpid(),
                        "process_start_identity": "different-process-start",
                        "host": platform.node(),
                        "created_unix": 0,
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_installer(target, fixture / "tools" / INSTALL_SCRIPT.name)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(lock_directory.exists())
            self.assertEqual(destination.read_bytes(), BRIDGE_SOURCE.read_bytes())

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
