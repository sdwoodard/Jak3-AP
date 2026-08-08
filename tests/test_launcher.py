import hashlib
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from worlds.jak3.agents.diagnostics import DiagnosticSession
from worlds.jak3.agents.launcher import (
    OpenGoalInstall,
    build_launch_commands,
    install_packaged_bridge,
)


BRIDGE_PAYLOAD = b""";; test bridge
(in-package goal)
(defconstant AP-PROTOCOL-VERSION 3)
(defconstant AP-GAME-INTEGRATION-VERSION 2)
(defconstant AP-BRIDGE-RUNTIME-VERSION 2)
"""
STARTUP_PAYLOAD = (
    b";; test startup\n(in-package goal)\n"
    b"(defun ap-bootstrap-show-startup-wait! () #t)\n"
)


class OpenGoalBridgeInstallerTest(unittest.TestCase):
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
                hashlib.sha256(BRIDGE_PAYLOAD).hexdigest(),
            )
            self.assertEqual(first.startup_path.read_bytes(), STARTUP_PAYLOAD)
            bootstrap_types = first.bootstrap_types_path.read_bytes()
            self.assertIn(b"*font-default-matrix*", bootstrap_types)
            self.assertNotIn(b"must-not-be-imported", bootstrap_types)
            project_text = first.project_path.read_text(encoding="utf-8")
            self.assertEqual(project_text.count('"archipelago.o"'), 1)
            self.assertLess(
                project_text.index('"task-control.o"'),
                project_text.index('"archipelago.o"'),
            )
            project_bytes = first.project_path.read_bytes()
            self.assertNotIn(b"\n", project_bytes.replace(b"\r\n", b""))

            with self.assertRaisesRegex(ValueError, "does not match"):
                install_packaged_bridge(
                    install,
                    BRIDGE_PAYLOAD.replace(
                        b"AP-BRIDGE-RUNTIME-VERSION 2",
                        b"AP-BRIDGE-RUNTIME-VERSION 1",
                    ),
                    STARTUP_PAYLOAD,
                )

    def test_partial_environment_override_is_rejected(self) -> None:
        from unittest.mock import patch
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

    def test_diagnostic_pair_uses_one_session_id(self) -> None:
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
            contents = session.opengoal_log.read_text("utf-8")
            self.assertIn("[TEST] diagnostic marker", contents)
            self.assertIn("[GOALC] compiler error", contents)
            self.assertIn("[GOALC] next line", contents)
            self.assertNotIn("\x1b", contents)


if __name__ == "__main__":
    unittest.main()
