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
from worlds.jak3.agents.protocol import BridgeSnapshot, format_snapshot


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
MILESTONE_7_2_RECORDER = REPOSITORY_ROOT / "tools" / "milestone_7_2_recorder.ps1"
MILESTONE_7_2_METRICS = REPOSITORY_ROOT / "tests" / "milestone_7_2_metrics.jsonl"
MILESTONE_7_2_FRAMES = REPOSITORY_ROOT / "tests" / "milestone_7_2_frames.jsonl"


class DeveloperInstallerTest(unittest.TestCase):
    def run_milestone_7_2_recorder(
        self, output: Path, action: str, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(MILESTONE_7_2_RECORDER),
                "-Action",
                action,
                "-OutputDirectory",
                str(output),
                *arguments,
            ),
            capture_output=True,
            check=False,
            text=True,
        )

    def test_milestone_7_2_recorder_sanitizes_snapshot_identity(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_path = root / "bridge.snapshot"
            save_identity = "11111111-2222-3333-4444-555555555555"
            snapshot_path.write_text(
                format_snapshot(
                    BridgeSnapshot(
                        snapshot_revision=17,
                        client_session_id="test-client-session",
                        session_nonce="test-game-nonce",
                        native_save_identity=save_identity,
                        native_save_slot=2,
                        save_loaded=True,
                    )
                ),
                encoding="utf-8",
            )

            result = self.run_milestone_7_2_recorder(
                root, "Capture", "-SnapshotPath", str(snapshot_path)
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record_text = (root / "recorder.jsonl").read_text(encoding="utf-8")
            record = json.loads(record_text)
            self.assertNotIn(save_identity, record_text)
            self.assertEqual(record["kind"], "snapshot.capture")
            self.assertEqual(record["data"]["snapshot"]["snapshot_revision"], 17)
            self.assertEqual(record["data"]["snapshot"]["native_save_slot"], 2)
            self.assertEqual(
                len(record["data"]["snapshot"]["native_save_identity_hash"]), 16
            )

    def test_milestone_7_2_analyzer_applies_practical_gates(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)

            result = self.run_milestone_7_2_recorder(
                root,
                "Analyze",
                "-MetricsPath",
                str(MILESTONE_7_2_METRICS),
                "-FrameMetricsPath",
                str(MILESTONE_7_2_FRAMES),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((root / "analysis.json").read_text(encoding="utf-8"))
            self.assertTrue(report["gates"]["frame_p95_within_1_ms"])
            self.assertTrue(report["gates"]["normalized_cpu_within_2_points"])
            self.assertTrue(report["gates"]["connected_memory_within_32_mib"])
            self.assertTrue(report["gates"]["connected_client_heartbeat_near_1_hz"])
            connected = next(
                group for group in report["groups"] if group["label"] == "connected"
            )
            self.assertGreater(
                connected["files"][0]["positive_growth_bytes_per_hour"], 0
            )

    def test_milestone_7_2_recorder_extracts_opengoal_frame_times(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            trace_path = root / "prof.json"
            frame_path = root / "frames.jsonl"
            trace_path.write_text(
                json.dumps(
                    {
                        "displayTimeUnit": "ms",
                        "traceEvents": [
                            {"name": "ROOT", "ph": "i", "tid": 7, "ts": 1000.0},
                            {
                                "name": "drawing",
                                "ph": "B",
                                "tid": 7,
                                "ts": 1001.0,
                            },
                            {"ph": "E", "tid": 7, "ts": 1002.0},
                            {
                                "name": "ROOT",
                                "ph": "i",
                                "tid": 7,
                                "ts": 11000.0,
                            },
                            {
                                "name": "drawing",
                                "ph": "B",
                                "tid": 7,
                                "ts": 11001.0,
                            },
                            {"ph": "E", "tid": 7, "ts": 11002.0},
                            {
                                "name": "ROOT",
                                "ph": "i",
                                "tid": 7,
                                "ts": 22000.0,
                            },
                            {"name": "ROOT", "ph": "i", "tid": 2, "ts": 500.0},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_milestone_7_2_recorder(
                root,
                "ProfilerFrames",
                "-ProfilerTracePath",
                str(trace_path),
                "-MetricsPath",
                str(frame_path),
                "-Label",
                "control",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            frames = [
                json.loads(line)
                for line in frame_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([10.0, 11.0], [frame["duration_ms"] for frame in frames])
            self.assertTrue(all(frame["label"] == "control" for frame in frames))
            record = json.loads((root / "recorder.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(record["kind"], "profiler.frames")
            self.assertEqual(record["data"]["graphics_thread_id"], 7)
            self.assertEqual(record["data"]["p95_ms"], 11.0)

    def test_milestone_7_2_command_probe_accepts_durable_receipt_ack(self) -> None:
        script = MILESTONE_7_2_RECORDER.read_text(encoding="utf-8")
        command_probe = script.split('    "SetTestTarget" {', 1)[1].split(
            '    "Sample" {', 1
        )[0]

        self.assertIn("[DateTime]::UtcNow.AddSeconds(2)", command_probe)
        self.assertIn('"recent_command_${index}_id"', command_probe)
        self.assertIn("$afterFields.ContainsKey($receiptIdKey)", command_probe)
        self.assertIn("-not $acknowledged", command_probe)

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
            self.assertEqual(project_text.count('"archipelago-items.o"'), 1)
            self.assertLess(
                project_text.index('"task-control.o"'),
                project_text.index('"archipelago.o"'),
            )
            self.assertLess(
                project_text.index('"archipelago.o"'),
                project_text.index('"archipelago-diagnostics.o"'),
            )
            self.assertLess(
                project_text.index('"archipelago-diagnostics.o"'),
                project_text.index('"archipelago-items.o"'),
            )
            self.assertTrue(
                destination.with_name("archipelago-diagnostics.gc").is_file()
            )
            self.assertTrue(destination.with_name("archipelago-items.gc").is_file())
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
            self.assertIn("function Test-JsonIntegerScalar", script)
            self.assertIn("$Value -is [int] -or $Value -is [long]", script)
            self.assertIn(
                '@("manifest_version", "source_set_format", "object_anchor", "modules")',
                script,
            )
            self.assertIn(
                '@("name", "order", "phase", "source", "resource", "destination", "object")',
                script,
            )
        self.assertIn(
            '$expectedPhases = @("pre_mi", "bridge", "bridge", "bridge")',
            installer,
        )
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
                "fractional manifest version",
                lambda document: document.update({"manifest_version": 1.5}),
                "scalar types",
            ),
            (
                "int64 manifest version",
                lambda document: document.update({"manifest_version": 2147483648}),
                "Unsupported",
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
            (
                "fractional module order",
                lambda document: document["modules"][0].update({"order": 10.5}),
                "scalar types",
            ),
            (
                "int64 module order",
                lambda document: document["modules"][0].update({"order": 2147483648}),
                "canonical",
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
