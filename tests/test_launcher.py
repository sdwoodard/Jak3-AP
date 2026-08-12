import io
import json
import os
import subprocess
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import Mock, patch

from worlds.jak3.agents.diagnostics import DiagnosticSession
from worlds.jak3.agents.launcher import (
    PROCESS_OUTPUT_LINE_LIMIT,
    OpenGoalInstall,
    _atomic_write,
    _launch_logged_process,
    _mirror_process_output,
    build_launch_commands,
    install_packaged_bridge,
    load_packaged_bridge_set,
)


BRIDGE_PAYLOAD = b""";; test bridge
(in-package goal)
(defconstant AP-PROTOCOL-VERSION 3)
(defconstant AP-GAME-INTEGRATION-VERSION 2)
(defconstant AP-BRIDGE-RUNTIME-VERSION 3)
"""
STARTUP_PAYLOAD = (
    b";; test startup\n(in-package goal)\n"
    b"(defun ap-bootstrap-show-startup-wait! () #t)\n"
)


class OpenGoalBridgeInstallerTest(unittest.TestCase):
    def test_launched_process_uses_bounded_pipe_without_raw_spool(self) -> None:
        process = Mock(pid=101, stdout=io.BytesIO())
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "pipe")
            with (
                patch(
                    "worlds.jak3.agents.launcher.subprocess.Popen",
                    return_value=process,
                ) as popen,
                patch("worlds.jak3.agents.launcher.threading.Thread") as thread,
            ):
                self.assertIs(
                    _launch_logged_process(("gk",), 0, "gk", session), process
                )
            self.assertIs(popen.call_args.kwargs["stdout"], subprocess.PIPE)
            self.assertIs(popen.call_args.kwargs["stderr"], subprocess.STDOUT)
            thread.return_value.start.assert_called_once()
            self.assertEqual(list(Path(directory).glob("*.raw")), [])

    def test_process_collectors_preserve_partial_utf8_and_classify_exits(self) -> None:
        class FinishedProcess:
            def __init__(self, pid: int, returncode: int, payload: bytes) -> None:
                self.pid = pid
                self.returncode = returncode
                self.stdout = io.BytesIO(payload)

            def poll(self) -> int:
                return self.returncode

        with TemporaryDirectory() as directory:
            root = Path(directory)
            diagnostics = DiagnosticSession.create(root, "collectors")
            cases = (
                (FinishedProcess(101, 0, b"partial-\xe2\x98\x83"), "gk"),
                (FinishedProcess(102, 9, b"compiler line\ntrailing"), "goalc"),
            )
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        _mirror_process_output,
                        process,
                        label,
                        diagnostics,
                    )
                    for process, label in cases
                ]
                for future in futures:
                    future.result()
            combined = diagnostics.opengoal_log.read_text("utf-8")
            self.assertIn("partial-☃", combined)
            self.assertIn("trailing", combined)
            events = [
                json.loads(line)["event_name"]
                for line in diagnostics.events_log.read_text("utf-8").splitlines()
            ]
            self.assertIn("process.exited", events)
            self.assertIn("process.crashed", events)

    def test_process_collector_records_pipe_read_failure_as_capture_gap(self) -> None:
        class FailedStream:
            def read(self, _size: int) -> bytes:
                raise OSError("synthetic pipe failure")

        class FinishedProcess:
            pid = 103
            stdout = FailedStream()

            @staticmethod
            def poll() -> int:
                return 0

        with TemporaryDirectory() as directory:
            diagnostics = DiagnosticSession.create(Path(directory), "pipe-failure")

            _mirror_process_output(FinishedProcess(), "gk", diagnostics)

            events = [
                json.loads(line)
                for line in diagnostics.events_log.read_text("utf-8").splitlines()
            ]
            gap = next(
                event
                for event in events
                if event["event_name"] == "process.capture_gap"
            )
            self.assertEqual(gap["context"]["capture"], "pipe_read_failed")
            self.assertEqual(gap["context"]["reason"], "OSError")
            self.assertIn("process.exited", [event["event_name"] for event in events])

    def test_process_collector_omits_oversized_unbroken_lines_before_storage(
        self,
    ) -> None:
        class FinishedProcess:
            pid = 104
            returncode = 0
            stdout = io.BytesIO(
                b"x" * (PROCESS_OUTPUT_LINE_LIMIT - 8)
                + b'password="boundary secret phrase"'
                + b"y" * 32
                + b"\nretained line\n"
            )

            @classmethod
            def poll(cls) -> int:
                return cls.returncode

        with TemporaryDirectory() as directory:
            diagnostics = DiagnosticSession.create(Path(directory), "oversized-line")

            _mirror_process_output(FinishedProcess(), "gk", diagnostics)

            rendered = diagnostics.opengoal_log.read_text("utf-8")
            self.assertIn("oversized process output line omitted", rendered)
            self.assertIn("retained line", rendered)
            self.assertNotIn("boundary secret phrase", rendered)
            events = [
                json.loads(line)
                for line in diagnostics.events_log.read_text("utf-8").splitlines()
            ]
            gaps = [
                event
                for event in events
                if event["event_name"] == "process.capture_gap"
                and event["context"].get("capture") == "oversized_line"
            ]
            self.assertEqual(len(gaps), 1)
            result = diagnostics.export_bundle()
            self.assertIn(result.status, {"complete", "partial"})
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                bundled = archive.read("opengoal.txt").decode("utf-8")
            self.assertIn("oversized process output line omitted", bundled)
            self.assertNotIn("boundary secret phrase", bundled)

    def test_install_is_exact_and_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "data"
            dgo = project / "goal_src" / "jak3" / "dgos" / "game.gd"
            dgo.parent.mkdir(parents=True)
            all_types = project / "decompiler" / "config" / "jak3" / "all-types.gc"
            all_types.parent.mkdir(parents=True)
            all_types.write_bytes(
                b";; test types\n"
                b"(deftype process (basic))\n"
                b"(define-extern *font-default-matrix* matrix)\n"
                b"(def-event-handler must-not-be-imported process)\n"
            )
            original = b'(dgo "GAME.CGO"\r\n  "task-control.o"\r\n  "scene.o"\r\n)\r\n'
            dgo.write_bytes(original)
            install = OpenGoalInstall(root / "bin", project)

            first = install_packaged_bridge(install, BRIDGE_PAYLOAD, STARTUP_PAYLOAD)
            second = install_packaged_bridge(install, BRIDGE_PAYLOAD, STARTUP_PAYLOAD)

            self.assertTrue(first.source_updated)
            self.assertTrue(first.reload_required)
            self.assertTrue(first.project_updated)
            self.assertTrue(first.startup_updated)
            self.assertTrue(first.bootstrap_types_updated)
            self.assertFalse(second.source_updated)
            self.assertTrue(second.reload_required)
            self.assertFalse(second.project_updated)
            self.assertFalse(second.startup_updated)
            self.assertFalse(second.bootstrap_types_updated)
            self.assertEqual(first.source_path.read_bytes(), BRIDGE_PAYLOAD)
            self.assertEqual(
                first.reload_marker_path.read_text(encoding="ascii").strip(),
                first.source_set_hash,
            )
            self.assertEqual(first.startup_path.read_bytes(), STARTUP_PAYLOAD)
            bootstrap_types = first.bootstrap_types_path.read_bytes()
            self.assertIn(b"*font-default-matrix*", bootstrap_types)
            self.assertNotIn(b"must-not-be-imported", bootstrap_types)
            project_text = first.project_path.read_text(encoding="utf-8")
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
            self.assertTrue(first.manifest_path.is_file())
            self.assertEqual(
                {path.name for path in first.source_paths},
                {
                    "archipelago-startup.gc",
                    "archipelago.gc",
                    "archipelago-diagnostics.gc",
                    "archipelago-items.gc",
                },
            )
            project_bytes = first.project_path.read_bytes()
            self.assertNotIn(b"\n", project_bytes.replace(b"\r\n", b""))

            with self.assertRaisesRegex(ValueError, "does not match"):
                install_packaged_bridge(
                    install,
                    BRIDGE_PAYLOAD.replace(
                        b"AP-BRIDGE-RUNTIME-VERSION 3",
                        b"AP-BRIDGE-RUNTIME-VERSION 2",
                    ),
                    STARTUP_PAYLOAD,
                )

    def test_install_repairs_partial_or_reversed_bridge_registration(self) -> None:
        registrations = (
            '  "archipelago-diagnostics.o"\n',
            '  "archipelago-items.o"\n  "archipelago-diagnostics.o"\n  "archipelago.o"\n',
        )
        for registration in registrations:
            with (
                self.subTest(registration=registration),
                TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                project = root / "data"
                dgo = project / "goal_src" / "jak3" / "dgos" / "game.gd"
                dgo.parent.mkdir(parents=True)
                dgo.write_text(
                    '(dgo "GAME.CGO"\n  "task-control.o"\n'
                    + registration
                    + '  "scene.o"\n)\n',
                    encoding="utf-8",
                )
                all_types = project / "decompiler" / "config" / "jak3" / "all-types.gc"
                all_types.parent.mkdir(parents=True)
                all_types.write_bytes(
                    b"(deftype process (basic))\n"
                    b"(define-extern *font-default-matrix* matrix)\n"
                )

                result = install_packaged_bridge(
                    OpenGoalInstall(root / "bin", project),
                    BRIDGE_PAYLOAD,
                    STARTUP_PAYLOAD,
                )

                project_text = result.project_path.read_text("utf-8")
                self.assertTrue(result.project_updated)
                self.assertEqual(project_text.count('"archipelago.o"'), 1)
                self.assertEqual(project_text.count('"archipelago-diagnostics.o"'), 1)
                self.assertEqual(project_text.count('"archipelago-items.o"'), 1)
                anchor = project_text.index('"task-control.o"')
                control = project_text.index('"archipelago.o"')
                diagnostics = project_text.index('"archipelago-diagnostics.o"')
                items = project_text.index('"archipelago-items.o"')
                scene = project_text.index('"scene.o"')
                self.assertLess(anchor, control)
                self.assertLess(control, diagnostics)
                self.assertLess(diagnostics, items)
                self.assertLess(items, scene)

    def test_concurrent_installs_publish_one_coherent_source_set(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "data"
            dgo = project / "goal_src" / "jak3" / "dgos" / "game.gd"
            dgo.parent.mkdir(parents=True)
            dgo.write_text(
                '(dgo "GAME.CGO"\n  "task-control.o"\n  "scene.o"\n)\n',
                encoding="utf-8",
            )
            all_types = project / "decompiler" / "config" / "jak3" / "all-types.gc"
            all_types.parent.mkdir(parents=True)
            all_types.write_bytes(
                b"(deftype process (basic))\n"
                b"(define-extern *font-default-matrix* matrix)\n"
            )
            install = OpenGoalInstall(root / "bin", project)
            manifest, packaged = load_packaged_bridge_set()
            payload_sets = tuple(
                {
                    resource: payload + f"\n;; concurrent-{label}\n".encode()
                    for resource, payload in packaged.items()
                }
                for label in ("first", "second")
            )
            counter_lock = threading.Lock()
            active = 0
            maximum_active = 0

            def observed_atomic_write(path: Path, payload: bytes) -> None:
                nonlocal active, maximum_active
                with counter_lock:
                    active += 1
                    maximum_active = max(maximum_active, active)
                try:
                    sleep(0.02)
                    _atomic_write(path, payload)
                finally:
                    with counter_lock:
                        active -= 1

            with (
                patch(
                    "worlds.jak3.agents.launcher._atomic_write",
                    side_effect=observed_atomic_write,
                ),
                ThreadPoolExecutor(max_workers=2) as executor,
            ):
                futures = [
                    executor.submit(
                        install_packaged_bridge,
                        install,
                        manifest=manifest,
                        module_payloads=payloads,
                    )
                    for payloads in payload_sets
                ]
                results = tuple(future.result() for future in futures)

            installed = {
                str(module.resource): (
                    project / Path(str(module.destination))
                ).read_bytes()
                for module in manifest.modules
            }
            if installed == payload_sets[0]:
                expected_hash = manifest.source_set_sha256(payload_sets[0])
            elif installed == payload_sets[1]:
                expected_hash = manifest.source_set_sha256(payload_sets[1])
            else:
                self.fail("Concurrent bridge installation left a mixed source set.")
            marker = (
                project
                / "goal_src"
                / "jak3"
                / "pc"
                / "features"
                / ".archipelago-reload-required"
            )
            self.assertEqual(marker.read_text("ascii").strip(), expected_hash)
            self.assertEqual(maximum_active, 1)
            self.assertEqual(
                {result.source_set_hash for result in results},
                {
                    manifest.source_set_sha256(payload_sets[0]),
                    manifest.source_set_sha256(payload_sets[1]),
                },
            )
            self.assertFalse(
                (
                    project
                    / "goal_src"
                    / "jak3"
                    / "pc"
                    / "features"
                    / ".archipelago-install.lock"
                ).exists()
            )

    def test_partial_environment_override_is_rejected(self) -> None:
        from worlds.jak3.agents.launcher import find_install

        with patch.dict(os.environ, {"JAK3_OPENGOAL_BIN": "C:/OpenGOAL"}, clear=True):
            with self.assertRaisesRegex(ValueError, "must be set together"):
                find_install()

    def test_launch_commands_capture_readable_debug_and_compiler_output(self) -> None:
        install = OpenGoalInstall(Path("C:/OpenGOAL/bin"), Path("C:/OpenGOAL/data"))
        game, compiler = build_launch_commands(install)

        self.assertIn("-debug", game)
        self.assertIn("-fakeiso", game)
        self.assertIn("-v", game)
        self.assertIn("--disable-ansi", game)
        self.assertIn("--disable-ansi", compiler)
        self.assertEqual(compiler[compiler.index("--game") + 1], "jak3")
        self.assertEqual(
            compiler[compiler.index("--iso-path") + 1], str(install.iso_directory)
        )

    def test_diagnostic_artifacts_use_one_session_id(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "known_session")
            session.note_opengoal("TEST", "diagnostic marker")
            session.append_process_output(
                "GOALC", "\x1b[31mcompiler error\x1b[0m\rnext line\n"
            )

            self.assertEqual(session.client_log.name, "Jak3Client_known_session.txt")
            self.assertEqual(
                session.opengoal_log.name, "Jak3OpenGOAL_known_session.txt"
            )
            self.assertEqual(session.events_log.name, "Jak3Events_known_session.jsonl")
            contents = session.opengoal_log.read_text("utf-8")
            self.assertIn("[TEST] diagnostic marker", contents)
            self.assertIn("[GOALC] compiler error", contents)
            self.assertIn("[GOALC] next line", contents)
            self.assertNotIn("\x1b", contents)


if __name__ == "__main__":
    unittest.main()
