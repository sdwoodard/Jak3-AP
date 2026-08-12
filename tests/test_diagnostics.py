import asyncio
import hashlib
import io
import json
import logging
import os
import platform
import re
import sys
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import patch

from worlds.jak3.agents.diagnostics import (
    BUNDLE_MANIFEST_VERSION,
    DIAGNOSTIC_SCHEMA_VERSION,
    EVENT_REGISTRY,
    GOAL_EVENT_REGISTRY,
    DiagnosticPolicy,
    DiagnosticSession,
    GoalDiagnosticRecord,
    _ClientDiagnosticHandler,
    _RedactingFilter,
    _process_start_identity,
    _recover_stale_interprocess_lock,
    hash_identifier,
    interprocess_directory_lock,
)
from worlds.jak3.agents.launcher import (
    OpenGoalInstall,
    _mirror_process_output,
    launch_missing_processes,
)
from worlds.jak3.agents.protocol import (
    BridgeProtocol,
    BridgeSnapshot,
    CommandReceipt,
    ProtocolCommand,
    ProtocolError,
    ProtocolResult,
)
from worlds.jak3.client import Jak3Context
from worlds.jak3.option_resolution import SUPPORTED_FIRST_RELEASE_OPTIONS
from worlds.jak3.persistence import (
    AuthenticatedSlot,
    NativeSaveDescriptor,
    NativeSaveEligibility,
    StateBindingError,
    StateRepository,
)
from worlds.jak3.slot_data import build_slot_data


def read_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


class StructuredDiagnosticsTest(unittest.TestCase):
    def test_balanced_policy_defaults_and_overrides_are_bounded(self) -> None:
        self.assertEqual(
            DiagnosticPolicy(),
            DiagnosticPolicy(
                segment_bytes=8 * 1024 * 1024,
                backups_per_artifact=3,
                retained_sessions=10,
                retention_days=14,
                managed_bytes=256 * 1024 * 1024,
            ),
        )
        with patch.dict(
            os.environ,
            {"JAK3_DIAGNOSTICS_BACKUPS": "17"},
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, "backup"):
                DiagnosticPolicy.from_environment()
        with self.assertRaisesRegex(ValueError, "active rotation capacity"):
            DiagnosticPolicy(
                segment_bytes=1024,
                backups_per_artifact=3,
                retained_sessions=1,
                retention_days=1,
                managed_bytes=4096,
            ).validate()

    def test_registry_documentation_has_exact_name_parity(self) -> None:
        documentation = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "development"
            / "diagnostic-events.md"
        ).read_text("utf-8")
        documented = set(
            re.findall(r"^- `([a-z][a-z0-9_.]+)`", documentation, re.MULTILINE)
        )
        self.assertEqual(documented, set(EVENT_REGISTRY))

    def test_registry_schema_utf8_allowlist_and_concurrent_order(self) -> None:
        self.assertEqual(len(EVENT_REGISTRY), len(set(EVENT_REGISTRY)))
        goal_codes = [
            event.goal_code
            for event in EVENT_REGISTRY.values()
            if event.goal_code is not None
        ]
        self.assertEqual(len(goal_codes), len(set(goal_codes)))
        self.assertNotEqual(
            EVENT_REGISTRY["client.started"].context_fields,
            EVENT_REGISTRY["protocol.command.submitted"].context_fields,
        )
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "schema")
            self.assertTrue(
                session.emit("bridge.install.verified", details={"count": 0})
            )

            def emit(index: int) -> None:
                session.emit(
                    "runtime.state.changed",
                    message=f"café\r\nline {index}\x1b[31m",
                    source_component="test-worker",
                    context={"runtime_state": {"native_save_slot": index}},
                )

            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(emit, range(200)))
            self.assertFalse(
                session.emit(
                    "runtime.state.changed",
                    context={"password": "must-not-be-accepted"},
                )
            )
            self.assertFalse(
                session.emit(
                    "runtime.state.changed",
                    context={"runtime_state": {"password": "hunter2"}},
                )
            )
            self.assertFalse(
                session.emit(
                    "client.started",
                    context={"native_save_hash": "misplaced-field"},
                )
            )
            events = read_events(session.events_log)
            sequences = [event["event_sequence"] for event in events]
            self.assertEqual(sequences, sorted(sequences))
            self.assertEqual(len(sequences), len(set(sequences)))
            self.assertTrue(
                all(
                    event["diagnostic_schema_version"] == DIAGNOSTIC_SCHEMA_VERSION
                    for event in events
                )
            )
            self.assertTrue(
                all(str(event["observed_utc"]).endswith("Z") for event in events)
            )
            rendered = session.events_log.read_text("utf-8")
            self.assertIn("café", rendered)
            self.assertNotIn("\x1b", rendered)
            self.assertNotIn("hunter2", rendered)
            self.assertIn("diagnostics.event.rejected", rendered)

    def test_location_batch_context_is_allowlisted_and_bounded(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "location-batch")
            location_ids = list(range(100))
            self.assertTrue(
                session.emit(
                    "location.outbox.batch_sent",
                    context={
                        "location_ids": location_ids,
                        "task_ids": [10, 11],
                        "source": "client_outbox",
                        "outcome": "sent",
                    },
                )
            )

            event = read_events(session.events_log)[0]
            self.assertEqual(event["context"]["location_ids"], location_ids[:64])
            self.assertEqual(event["context"]["task_ids"], [10, 11])

    def test_bundle_reader_rejects_undeclared_nested_event_fields(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "nested-schema")
            self.assertTrue(
                session.emit(
                    "runtime.state.changed",
                    context={"runtime_state": {"game_status": "IN_GAME"}},
                )
            )
            forged = read_events(session.events_log)[0]
            forged["event_sequence"] = 999
            forged["context"] = {"runtime_state": {"password": "bundle-secret"}}
            with session.events_log.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(forged) + "\n")

            merged = session._merged_events([])

            self.assertNotIn(b"bundle-secret", merged)
            self.assertNotIn(b'"event_sequence":999', merged)

    def test_bundle_reader_ignores_unknown_optional_envelope_fields(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "forward-fields")
            self.assertTrue(session.emit("client.started"))
            event = read_events(session.events_log)[0]
            event["future_optional_field"] = {
                "uncontrolled_future_value": "ignored safely"
            }
            session.events_log.write_text(json.dumps(event) + "\n", encoding="utf-8")

            merged = session._merged_events([])

            exported = json.loads(merged)
            self.assertEqual(exported["event_name"], "client.started")
            self.assertNotIn("future_optional_field", exported)

    def test_human_log_redacts_exception_traceback_text(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "traceback-redaction")
            handler = _ClientDiagnosticHandler(session)
            handler.setFormatter(logging.Formatter("%(message)s"))
            handler.addFilter(_RedactingFilter())
            logger = logging.Logger("traceback-redaction")
            logger.addHandler(handler)
            try:
                raise RuntimeError("password=hunter2 token=abc")
            except RuntimeError:
                logger.exception("Synthetic diagnostic exception")
            finally:
                handler.close()

            rendered = session.client_log.read_text("utf-8")
            self.assertNotIn("hunter2", rendered)
            self.assertNotIn("token=abc", rendered)
            self.assertGreaterEqual(rendered.count("<redacted>"), 2)

    def test_human_logs_redact_quoted_structured_and_digest_credentials(self) -> None:
        secrets = (
            "very secret phrase",
            "unquoted secret phrase",
            "json secret value",
            "dict secret phrase",
            "digest-response-value",
            "camel access token",
            "camel client secret",
            "camel database password",
            "camel service api key",
        )
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "quoted-redaction")
            session.note_opengoal(
                "TEST",
                'password="very secret phrase" '
                '{"access_token": "json secret value"} '
                "{'client_secret': 'dict secret phrase'}",
            )
            session.note_opengoal("TEST", "password = unquoted secret phrase")
            session.note_opengoal(
                "TEST",
                'Authorization: Digest username="alice", '
                'response="digest-response-value"',
            )
            session.note_opengoal(
                "TEST",
                '{"accessToken":"camel access token",'
                '"clientSecret":"camel client secret",'
                '"dbPassword":"camel database password",'
                '"serviceApiKey":"camel service api key"}',
            )

            result = session.export_bundle()

            self.assertIn(result.status, {"complete", "partial"})
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                rendered = b"\n".join(
                    archive.read(name)
                    for name in ("client.txt", "opengoal.txt", "events.jsonl")
                ).decode("utf-8")
            for secret in secrets:
                self.assertNotIn(secret, rendered)
            self.assertGreaterEqual(rendered.count("<redacted>"), 9)

    def test_goal_drain_is_idempotent_and_reports_gap_and_overflow(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "goal")
            loaded_code = next(
                code
                for code, definition in GOAL_EVENT_REGISTRY.items()
                if definition.name == "bridge.source.loaded"
            )
            records = (
                GoalDiagnosticRecord(0, 10, 1, loaded_code, 0, 0, 1, 0, 0, 0, 0),
                GoalDiagnosticRecord(2, 12, 1, loaded_code, 0, 0, 1, 0, 0, 0, 0),
            )
            self.assertEqual(session.ingest_goal_events(records, dropped_count=4), 2)
            self.assertEqual(session.ingest_goal_events(records), 2)
            session.reset_goal_event_source()
            self.assertEqual(session.ingest_goal_events(records), 2)
            names = [event["event_name"] for event in read_events(session.events_log)]
            self.assertIn("diagnostics.goal.overflow", names)
            self.assertIn("diagnostics.goal.gap", names)
            self.assertIn("diagnostics.goal.duplicate", names)
            self.assertEqual(names.count("bridge.source.loaded"), 4)
            source_events = [
                event
                for event in read_events(session.events_log)
                if event["event_name"] == "bridge.source.loaded"
            ]
            self.assertEqual(
                [
                    (event["source_sequence"], event["context"]["source_generation"])
                    for event in source_events
                ],
                [(0, 0), (2, 0), (0, 1), (2, 1)],
            )

    def test_repeated_goal_duplicates_are_summarized_instead_of_flooding(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "goal-duplicates")
            loaded_code = next(
                code
                for code, definition in GOAL_EVENT_REGISTRY.items()
                if definition.name == "bridge.source.loaded"
            )
            record = GoalDiagnosticRecord(0, 10, 1, loaded_code, 0, 0, 1, 0, 0, 0, 0)
            session.ingest_goal_events((record,))
            for _ in range(10_000):
                session.ingest_goal_events((record,))
            session.close()

            names = [event["event_name"] for event in read_events(session.events_log)]
            self.assertEqual(names.count("diagnostics.goal.duplicate"), 1)
            self.assertEqual(names.count("diagnostics.events_dropped_or_suppressed"), 1)
            self.assertEqual(names.count("diagnostics.goal.drain.completed"), 1)

    def test_goal_command_uses_the_python_command_correlation(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "goal-correlation")
            command_code = next(
                code
                for code, definition in GOAL_EVENT_REGISTRY.items()
                if definition.name == "protocol.command.applied"
            )
            record = GoalDiagnosticRecord(0, 10, 1, command_code, 2, 42, 1, 0, 1, 0, 0)

            self.assertEqual(session.ingest_goal_events((record,)), 0)

            applied = next(
                event
                for event in read_events(session.events_log)
                if event["event_name"] == "protocol.command.applied"
            )
            self.assertEqual(applied["correlation_id"], "command:42")
            self.assertEqual(applied["context"]["command_id"], 42)

    def test_goal_record_is_not_acknowledged_until_serialized(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "goal-write")
            loaded_code = next(
                code
                for code, definition in GOAL_EVENT_REGISTRY.items()
                if definition.name == "bridge.source.loaded"
            )
            record = GoalDiagnosticRecord(0, 10, 1, loaded_code, 0, 0, 1, 0, 0, 0, 0)
            with patch.object(session, "_append_bytes", return_value=False):
                self.assertIsNone(session.ingest_goal_events((record,)))
            self.assertEqual(session.ingest_goal_events((record,)), 0)

    def test_rotation_is_bounded_and_writer_failure_is_nonfatal(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=3,
            retained_sessions=10,
            retention_days=14,
            managed_bytes=64 * 1024,
        )
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(
                Path(directory), "rotation", policy=policy
            )
            for index in range(100):
                session.emit(
                    "runtime.state.changed",
                    message="x" * 300,
                    context={"runtime_state": {"native_save_slot": index}},
                )
            self.assertLessEqual(
                len(list(Path(directory).glob("Jak3Events_rotation.jsonl.*"))), 3
            )
            with patch.object(
                session, "_append_bytes", side_effect=OSError("disk full")
            ):
                self.assertFalse(
                    session.emit(
                        "protocol.command.failed",
                        message="synthetic write failure",
                    )
                )

    def test_exception_capture_is_deduplicated(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "exceptions")
            for source in ("main", "asyncio", "thread", "collector"):
                error = RuntimeError(f"synthetic {source} failure")
                session.capture_exception(source, error)
                session.capture_exception(source, error)
            names = [event["event_name"] for event in read_events(session.events_log)]
            self.assertEqual(names.count("diagnostics.exception.main"), 1)
            self.assertEqual(names.count("diagnostics.exception.asyncio"), 1)
            self.assertEqual(names.count("diagnostics.exception.thread"), 2)

    def test_long_exception_is_compacted_under_small_valid_segment_policy(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=2,
            retention_days=1,
            managed_bytes=16 * 1024,
        )
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(
                Path(directory), "compact-exception", policy=policy
            )
            session.capture_exception("main", RuntimeError("é" * 10_000))

            events = read_events(session.events_log)
            captured = next(
                event
                for event in events
                if event["event_name"] == "diagnostics.exception.main"
            )
            self.assertEqual(captured["context"]["exception_type"], "RuntimeError")
            self.assertIn("truncated", captured["message"])
            self.assertLessEqual(session.events_log.stat().st_size, 1024)

    def test_text_writes_never_exceed_the_segment_size(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=2,
            retention_days=1,
            managed_bytes=16 * 1024,
        )
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(
                Path(directory), "text-segments", policy=policy
            )
            self.assertTrue(session._append_text(session.client_log, "\u00e9" * 5000))
            self.assertTrue(
                all(
                    path.stat().st_size <= policy.segment_bytes
                    for path in session._segments(session.client_log)
                )
            )

    def test_rotation_failure_falls_back_to_temporary_storage(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=3,
            retained_sessions=2,
            retention_days=1,
            managed_bytes=16 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            fallback = root / "fallback"
            session = DiagnosticSession.create(
                primary, "fallback-continuity", policy=policy
            )
            session._write_marker(clean=False)
            primary_marker = session.marker_path
            session.emit("client.started", message="x" * 200)
            session.note_opengoal("TEST", "pre-fallback evidence")
            original_rotate = session._rotate
            failed = False

            def fail_once(path: Path) -> None:
                nonlocal failed
                if not failed:
                    failed = True
                    raise PermissionError("locked segment")
                original_rotate(path)

            with (
                patch(
                    "worlds.jak3.agents.diagnostics.tempfile.gettempdir",
                    return_value=fallback,
                ),
                patch.object(session, "_rotate", side_effect=fail_once),
            ):
                self.assertTrue(session.emit("client.stopping", message="y" * 200))
            self.assertEqual(session.storage_mode, "temporary")
            self.assertTrue(session.events_log.is_file())
            self.assertFalse(primary_marker.exists())
            self.assertTrue(session.marker_path.is_file())
            session.note_opengoal("TEST", "post-fallback evidence")
            result = session.export_bundle()
            self.assertIn(result.status, {"complete", "partial"})
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                names = [
                    json.loads(line)["event_name"]
                    for line in archive.read("events.jsonl").decode().splitlines()
                ]
                opengoal = archive.read("opengoal.txt").decode()
            self.assertIn("client.started", names)
            self.assertIn("client.stopping", names)
            self.assertIn("pre-fallback evidence", opengoal)
            self.assertIn("post-fallback evidence", opengoal)

    def test_initial_marker_failure_falls_back_to_temporary_storage(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            fallback = root / "fallback"
            session = DiagnosticSession.create(primary, "initial-marker-fallback")
            primary_marker = session.marker_path
            original_write_marker = session._write_marker

            def fail_primary_marker(*, clean: bool, active: bool = True) -> bool:
                if session.directory == primary:
                    return False
                return original_write_marker(clean=clean, active=active)

            try:
                with (
                    patch(
                        "worlds.jak3.agents.diagnostics.tempfile.gettempdir",
                        return_value=fallback,
                    ),
                    patch.object(
                        session, "_write_marker", side_effect=fail_primary_marker
                    ),
                ):
                    session.initialize()
                    self.assertTrue(
                        session.emit("client.started", message="fallback evidence")
                    )
                    result = session.export_bundle()

                self.assertEqual(session.storage_mode, "temporary")
                self.assertEqual(session.directory, fallback / "Jak3Diagnostics")
                self.assertFalse(primary_marker.exists())
                self.assertTrue(session.marker_path.is_file())
                self.assertIn(result.status, {"complete", "partial"})
                assert result.path is not None
                self.assertEqual(result.path.parent, fallback / "Jak3Diagnostics")
                with zipfile.ZipFile(result.path) as archive:
                    event_names = {
                        json.loads(line)["event_name"]
                        for line in archive.read("events.jsonl").decode().splitlines()
                    }
                self.assertIn("diagnostics.session.started", event_names)
                self.assertIn("client.started", event_names)
            finally:
                session.close()

    def test_export_write_failure_retries_in_temporary_storage(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fallback = root / "fallback"
            session = DiagnosticSession.create(root / "primary", "export-fallback")
            session.emit("client.started")
            original_zip = zipfile.ZipFile
            calls = 0

            def fail_once(*args: object, **kwargs: object) -> zipfile.ZipFile:
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise PermissionError("primary archive unavailable")
                return original_zip(*args, **kwargs)

            with (
                patch(
                    "worlds.jak3.agents.diagnostics.tempfile.gettempdir",
                    return_value=fallback,
                ),
                patch(
                    "worlds.jak3.agents.diagnostics.zipfile.ZipFile",
                    side_effect=fail_once,
                ),
            ):
                result = session.export_bundle()

            self.assertEqual(session.storage_mode, "temporary")
            self.assertIn(result.status, {"complete", "partial"})
            assert result.path is not None
            self.assertEqual(result.path.parent, fallback / "Jak3Diagnostics")
            self.assertTrue(result.path.is_file())
            completed = [
                event
                for event in read_events(session.events_log)
                if event["event_name"]
                in {
                    "diagnostics.bundle.export.completed",
                    "diagnostics.bundle.export.partial",
                }
            ]
            self.assertEqual(len(completed), 1)
            self.assertEqual(completed[0]["context"]["bundle_path"], result.path.name)

    def test_failed_archive_write_never_records_export_completion(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "export-failed")
            session.emit("client.started")
            with patch(
                "worlds.jak3.agents.diagnostics.zipfile.ZipFile",
                side_effect=RuntimeError("synthetic archive failure"),
            ):
                result = session.export_bundle()

            self.assertEqual(result.status, "failed")
            names = [event["event_name"] for event in read_events(session.events_log)]
            self.assertIn("diagnostics.bundle.export.failed", names)
            self.assertNotIn("diagnostics.bundle.export.completed", names)
            self.assertNotIn("diagnostics.bundle.export.partial", names)

    def test_repeated_exports_respect_managed_capacity(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=2,
            retention_days=1,
            managed_bytes=24 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            session = DiagnosticSession.create(root, "export-cap", policy=policy)
            session.emit("client.started", message="bounded export session")
            successful = 0
            failed = None
            for _index in range(100):
                result = session.export_bundle()
                if result.status == "failed":
                    failed = result
                    break
                successful += 1

            self.assertGreater(successful, 0)
            self.assertIsNotNone(failed)
            managed = [
                path
                for path in root.iterdir()
                if path.is_file()
                and path.name.startswith(
                    (
                        "Jak3Client_",
                        "Jak3OpenGOAL_",
                        "Jak3Events_",
                        "Jak3Support_",
                    )
                )
            ]
            self.assertLessEqual(
                sum(path.stat().st_size for path in managed), policy.managed_bytes
            )

    def test_concurrent_sessions_serialize_bundle_capacity_publication(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=3,
            retention_days=1,
            managed_bytes=64 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = (
                DiagnosticSession.create(root, "export-first", policy=policy),
                DiagnosticSession.create(root, "export-second", policy=policy),
            )
            for session in sessions:
                session.emit("client.started")
            counter_lock = threading.Lock()
            active = 0
            maximum_active = 0
            original_usage = DiagnosticSession._managed_usage_bytes

            def observed_usage(session: DiagnosticSession) -> int:
                nonlocal active, maximum_active
                with counter_lock:
                    active += 1
                    maximum_active = max(maximum_active, active)
                try:
                    sleep(0.05)
                    return original_usage(session)
                finally:
                    with counter_lock:
                        active -= 1

            with (
                patch.object(
                    DiagnosticSession,
                    "_managed_usage_bytes",
                    observed_usage,
                ),
                ThreadPoolExecutor(max_workers=2) as executor,
            ):
                results = tuple(
                    executor.map(lambda session: session.export_bundle(), sessions)
                )

            self.assertEqual(maximum_active, 1)
            self.assertTrue(
                all(result.status in {"complete", "partial"} for result in results)
            )

    def test_startup_capacity_reservation_serializes_with_bundle_export(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=3,
            retention_days=1,
            managed_bytes=64 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            exporter = DiagnosticSession.create(root, "exporter", policy=policy)
            starter = DiagnosticSession.create(root, "starter", policy=policy)
            exporter.emit("client.started")
            export_capacity_entered = threading.Event()
            release_export = threading.Event()
            startup_capacity_entered = threading.Event()
            original_usage = DiagnosticSession._managed_usage_bytes

            def observed_usage(session: DiagnosticSession) -> int:
                if session is exporter:
                    export_capacity_entered.set()
                    self.assertTrue(release_export.wait(2.0))
                elif session is starter:
                    startup_capacity_entered.set()
                return original_usage(session)

            try:
                with (
                    patch.object(
                        DiagnosticSession,
                        "_managed_usage_bytes",
                        observed_usage,
                    ),
                    ThreadPoolExecutor(max_workers=2) as executor,
                ):
                    export_future = executor.submit(exporter.export_bundle)
                    self.assertTrue(export_capacity_entered.wait(2.0))
                    startup_future = executor.submit(starter.initialize)
                    self.assertFalse(startup_capacity_entered.wait(0.05))
                    release_export.set()
                    self.assertIn(
                        export_future.result(timeout=2.0).status,
                        {"complete", "partial"},
                    )
                    startup_future.result(timeout=2.0)
                self.assertTrue(startup_capacity_entered.is_set())
            finally:
                release_export.set()
                starter.close()
                exporter.close()

    def test_interprocess_capacity_lock_is_same_thread_reentrant(self) -> None:
        with TemporaryDirectory() as directory:
            lock_directory = Path(directory) / ".capacity.lock"
            with interprocess_directory_lock(lock_directory):
                self.assertTrue((lock_directory / "owner.json").is_file())
                owner = json.loads((lock_directory / "owner.json").read_text("utf-8"))
                self.assertEqual(
                    owner["process_start_identity"],
                    _process_start_identity(os.getpid()),
                )
                with interprocess_directory_lock(lock_directory):
                    self.assertTrue((lock_directory / "owner.json").is_file())
            self.assertFalse(lock_directory.exists())

    def test_interprocess_lock_age_never_evicts_a_live_local_owner(self) -> None:
        with TemporaryDirectory() as directory:
            lock_directory = Path(directory) / ".capacity.lock"
            lock_directory.mkdir()
            owner = {
                "token": "live-owner",
                "process_id": os.getpid(),
                "process_start_identity": "current-owner",
                "host": platform.node() or "local-host",
                "created_unix": 0,
            }
            (lock_directory / "owner.json").write_text(
                json.dumps(owner), encoding="utf-8"
            )

            with (
                patch(
                    "worlds.jak3.agents.diagnostics._process_is_running",
                    return_value=True,
                ),
                patch(
                    "worlds.jak3.agents.diagnostics._process_start_identity",
                    return_value="current-owner",
                ),
            ):
                recovered = _recover_stale_interprocess_lock(
                    lock_directory, stale_seconds=1.0
                )

            self.assertFalse(recovered)
            self.assertTrue(lock_directory.is_dir())
            with patch(
                "worlds.jak3.agents.diagnostics._process_is_running",
                return_value=False,
            ):
                recovered = _recover_stale_interprocess_lock(
                    lock_directory, stale_seconds=1.0
                )
            self.assertTrue(recovered)
            self.assertFalse(lock_directory.exists())

    def test_interprocess_lock_recovers_a_reused_live_pid_owner(self) -> None:
        with TemporaryDirectory() as directory:
            lock_directory = Path(directory) / ".capacity.lock"
            lock_directory.mkdir()
            (lock_directory / "owner.json").write_text(
                json.dumps(
                    {
                        "token": "stale-owner",
                        "process_id": os.getpid(),
                        "process_start_identity": "different-process-start",
                        "host": platform.node() or "local-host",
                        "created_unix": 0,
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch(
                    "worlds.jak3.agents.diagnostics._process_is_running",
                    return_value=True,
                ),
                patch(
                    "worlds.jak3.agents.diagnostics._process_start_identity",
                    return_value="current-process-start",
                ),
            ):
                recovered = _recover_stale_interprocess_lock(
                    lock_directory, stale_seconds=1.0
                )

            self.assertTrue(recovered)
            self.assertFalse(lock_directory.exists())

    def test_process_start_identity_is_stable_for_current_process(self) -> None:
        first = _process_start_identity(os.getpid())
        second = _process_start_identity(os.getpid())

        if first is not None:
            self.assertEqual(first, second)
            self.assertRegex(first, r"^(?:windows-filetime|procfs-startticks):[0-9]+$")

    def test_prior_unclean_marker_is_reported_once(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = DiagnosticSession.create(root, "prior")
            first.initialize()
            first.close(clean=False)

            current = DiagnosticSession.create(root, "current")
            current.initialize()
            try:
                names = [
                    event["event_name"] for event in read_events(current.events_log)
                ]
                self.assertEqual(names.count("diagnostics.prior_session.unclean"), 1)
            finally:
                current.close()

    def test_live_concurrent_session_is_not_misclassified_or_pruned(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=1,
            retention_days=1,
            managed_bytes=16 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = DiagnosticSession.create(root, "live-first", policy=policy)
            first.initialize()
            first.emit("client.started", message="live evidence")
            first_segment = Path(f"{first.events_log}.1")
            first_segment.write_text("live rotated evidence", encoding="utf-8")
            os.utime(first.events_log, (0, 0))
            os.utime(first_segment, (0, 0))
            marker = json.loads(first.marker_path.read_text("utf-8"))
            other_process_id = os.getpid() + 100_000
            marker["process_id"] = other_process_id
            first.marker_path.write_text(json.dumps(marker), encoding="utf-8")

            second = DiagnosticSession.create(root, "live-second", policy=policy)
            with patch(
                "worlds.jak3.agents.diagnostics._process_is_running",
                return_value=True,
            ) as process_is_running:
                second.initialize()
                try:
                    names = [
                        event["event_name"] for event in read_events(second.events_log)
                    ]
                    self.assertNotIn("diagnostics.prior_session.unclean", names)
                    self.assertTrue(first.marker_path.is_file())
                    second._prune_retention()
                    self.assertTrue(first.events_log.is_file())
                    self.assertTrue(first_segment.is_file())
                    process_is_running.assert_any_call(other_process_id)
                finally:
                    second.close()
                    first.close()

    def test_remote_live_marker_requires_a_recent_lease(self) -> None:
        recent = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        expired = (
            (datetime.now(UTC) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        )
        payload = {
            "active": True,
            "clean": False,
            "process_id": 1,
            "host_hash": "synthetic-remote-host",
            "last_seen_utc": recent,
        }

        self.assertTrue(DiagnosticSession._marker_is_live(payload))
        payload["last_seen_utc"] = expired
        self.assertFalse(DiagnosticSession._marker_is_live(payload))

    def test_local_live_marker_requires_pid_and_a_recent_lease(self) -> None:
        recent = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        expired = (
            (datetime.now(UTC) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        )
        payload = {
            "active": True,
            "clean": False,
            "process_id": 4242,
            "host_hash": hash_identifier(platform.node() or "local-host"),
            "last_seen_utc": recent,
        }
        with patch(
            "worlds.jak3.agents.diagnostics._process_is_running", return_value=True
        ):
            self.assertTrue(DiagnosticSession._marker_is_live(payload))
            payload["last_seen_utc"] = expired
            self.assertFalse(DiagnosticSession._marker_is_live(payload))

    def test_concurrent_live_reservations_prevent_capacity_overcommit(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=3,
            retention_days=1,
            managed_bytes=16 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = DiagnosticSession.create(root, "reservation-first", policy=policy)
            second = DiagnosticSession.create(root, "reservation-second", policy=policy)
            first._write_marker(clean=False)
            second._write_marker(clean=False)

            third = DiagnosticSession.create(root, "reservation-third", policy=policy)
            third.initialize()
            try:
                self.assertEqual(third.storage_mode, "console")
                self.assertTrue(first.marker_path.is_file())
                self.assertTrue(second.marker_path.is_file())
                marker = json.loads(third.marker_path.read_text("utf-8"))
                self.assertFalse(marker["active"])
                self.assertTrue(marker["clean"])
            finally:
                third.close()
                first.close()
                second.close()

    def test_prior_temporary_fallback_marker_is_reported_from_primary(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fallback_root = root / "temporary"
            fallback = fallback_root / "Jak3Diagnostics"
            fallback.mkdir(parents=True)
            marker = fallback / ".Jak3Session_prior-fallback.json"
            marker.write_text(
                json.dumps(
                    {
                        "session_id_hash": "prior-fallback-hash",
                        "started_utc": "2026-08-09T00:00:00Z",
                        "clean": False,
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "worlds.jak3.agents.diagnostics.tempfile.gettempdir",
                return_value=fallback_root,
            ):
                session = DiagnosticSession.create(root / "primary", "current-primary")
                session.initialize()
                try:
                    names = [
                        event["event_name"] for event in read_events(session.events_log)
                    ]
                    self.assertIn("diagnostics.prior_session.unclean", names)
                    self.assertFalse(marker.exists())
                finally:
                    session.close()

    def test_partial_startup_bundle_declares_missing_context(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "partial")
            session.emit("client.started", message="startup only")
            session.opengoal_log.unlink()
            result = session.export_bundle()
            self.assertEqual(result.status, "partial")
            self.assertIn("runtime.json", result.missing)
            self.assertIn("persistence.json", result.missing)
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                readme = archive.read("README.txt").decode("utf-8")
                self.assertIn("runtime.json", readme)
                self.assertIn("persistence.json", readme)
                self.assertIn("opengoal.txt", readme)

    def test_bundle_capture_gap_summary_comes_from_emitted_events(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "capture-summary")
            session.emit(
                "process.capture_gap",
                source_component="launcher",
                context={
                    "process": "gk",
                    "capture": "pipe_read_failed",
                    "reason": "OSError",
                },
            )
            session.emit(
                "diagnostics.capture_gap",
                source_component="protocol",
                context={"reason": "goal_ack_failed"},
            )

            result = session.export_bundle()

            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                gaps = json.loads(archive.read("capture_gaps.json"))
            self.assertEqual(
                gaps,
                [
                    {"component": "gk", "reason": "pipe_read_failed"},
                    {"component": "protocol", "reason": "goal_ack_failed"},
                ],
            )

    def test_bundle_provider_schemas_reject_uncontrolled_fields(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "provider-schema")
            session.emit("client.started")
            session.register_context_provider(
                "runtime", lambda: {"client_status": "ready", "token": "secret"}
            )
            session.register_context_provider(
                "persistence",
                lambda: {"binding_status": {"token": "nested-secret"}},
            )
            result = session.export_bundle()
            self.assertEqual(result.status, "partial")
            self.assertIn("runtime.json", result.missing)
            self.assertIn("persistence.json", result.missing)
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                self.assertNotIn("runtime.json", archive.namelist())
                self.assertNotIn("persistence.json", archive.namelist())
                self.assertNotIn(b"secret", archive.read("manifest.json"))

    def test_bundle_revalidates_known_timeline_fields_before_export(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "event-schema")
            session.emit("client.started")
            injected = read_events(session.events_log)[0]
            injected["event_sequence"] = 999
            injected["severity"] = "INVALID"
            injected["password"] = "bundle-secret"
            with session.events_log.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(injected) + "\n")

            result = session.export_bundle()

            self.assertIn(result.status, {"complete", "partial"})
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                payload = b"".join(archive.read(name) for name in archive.namelist())
                events = [
                    json.loads(line)
                    for line in archive.read("events.jsonl").decode().splitlines()
                ]
            self.assertNotIn(b"bundle-secret", payload)
            self.assertNotIn(999, {event["event_sequence"] for event in events})

    def test_initial_event_merge_failure_returns_failed_export(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "merge-failure")
            with patch.object(
                session, "_merged_events", side_effect=ValueError("malformed event")
            ):
                result = session.export_bundle()

            self.assertEqual(result.status, "failed")
            self.assertIsNone(result.path)
            self.assertIn("malformed event", result.error or "")

    def test_startup_removes_orphaned_support_archive_temp(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            orphan = root / "Jak3Support_crashed_20260809T120000000000Z.zip.tmp"
            orphan.write_bytes(b"incomplete archive")
            session = DiagnosticSession.create(root, "orphan-cleanup")

            session.initialize()
            try:
                self.assertFalse(orphan.exists())
            finally:
                session.close()

    def test_close_restores_asyncio_exception_handler(self) -> None:
        async def exercise() -> None:
            with TemporaryDirectory() as directory:
                loop = asyncio.get_running_loop()

                def prior_handler(
                    _loop: asyncio.AbstractEventLoop, _context: dict[str, object]
                ) -> None:
                    return None

                loop.set_exception_handler(prior_handler)
                session = DiagnosticSession.create(Path(directory), "loop-handler")
                session.install_exception_capture(loop)
                self.assertIsNot(loop.get_exception_handler(), prior_handler)
                session.close()
                self.assertIs(loop.get_exception_handler(), prior_handler)

        asyncio.run(exercise())

    def test_close_does_not_overwrite_newer_exception_hooks(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "hook-owner")
            previous_sys_hook = sys.excepthook
            previous_thread_hook = threading.excepthook

            def newer_sys_hook(
                _kind: type[BaseException], _exception: BaseException, _tb: object
            ) -> None:
                return None

            def newer_thread_hook(_args: threading.ExceptHookArgs) -> None:
                return None

            try:
                session.install_exception_capture()
                sys.excepthook = newer_sys_hook
                threading.excepthook = newer_thread_hook
                session.close()
                self.assertIs(sys.excepthook, newer_sys_hook)
                self.assertIs(threading.excepthook, newer_thread_hook)
            finally:
                sys.excepthook = previous_sys_hook
                threading.excepthook = previous_thread_hook

    def test_cross_component_forensic_bundle_uses_instrumented_failure_paths(
        self,
    ) -> None:
        secret_uuid = "123e4567-e89b-42d3-a456-426614174000"
        uuid_v7 = "018f778a-7abc-7def-8123-0123456789ab"
        nil_uuid = "00000000-0000-0000-0000-000000000000"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            session = DiagnosticSession.create(root / "logs", "forensic")
            session.note_opengoal(
                "TEST",
                f"password=hunter2 token=abc native={secret_uuid} "
                f"access_token=compound-token client_secret=compound-secret "
                f"future={uuid_v7} nil={nil_uuid} "
                "Authorization: Bearer bearer-secret "
                "ws://slot-user:url-secret@private.example:38281",
            )
            session.emit("client.started", message="Synthetic client startup.")

            install = OpenGoalInstall(root / "bin", root / "project")
            with patch(
                "worlds.jak3.agents.launcher._running_pid",
                side_effect=(101, 102),
            ):
                launch_missing_processes(install, session)

            class CrashedProcess:
                pid = 103
                returncode = 9
                stdout = io.BytesIO(b"synthetic startup failure\n")

                @staticmethod
                def poll() -> int:
                    return 9

            _mirror_process_output(CrashedProcess(), "gk", session)

            repository = StateRepository(root / "state", event_sink=session.event_sink)
            native_save = NativeSaveDescriptor(
                slot=0,
                identity=secret_uuid,
                eligibility=NativeSaveEligibility.FRESH_UNPROGRESSED,
            )
            opened = repository.open(native_save)
            opened.commit(replace(opened.state, last_clean_shutdown=True))
            opened.close(clean=False)
            paths = repository.paths_for(secret_uuid)
            paths.primary.write_text("{corrupt", encoding="utf-8")
            recovered = repository.open(native_save)
            slot_contract = build_slot_data(
                SUPPORTED_FIRST_RELEASE_OPTIONS, seed_identifier="forensic-seed"
            )
            first_slot = AuthenticatedSlot.from_connected_packet(
                slot_contract, team=0, slot=1, slot_name="Forensic Slot"
            )
            other_slot = AuthenticatedSlot.from_connected_packet(
                slot_contract, team=0, slot=2, slot_name="Other Slot"
            )
            recovered.bind(first_slot)
            with self.assertRaises(StateBindingError) as rejection:
                recovered.bind(other_slot)
            session.note_opengoal(
                "CLIENT", f"synthetic binding rejection: {rejection.exception}"
            )
            recovered.close(clean=False)

            class Repl:
                async def send_form(self, form: str, timeout: float = 10.0) -> str:
                    return "nREPL"

            replay = BridgeProtocol(
                Repl(),
                root / "replay.tmp",
                "forensic-replay",
                event_sink=session.event_sink,
            )
            replay.session_nonce = "game-session"

            async def replay_wait(*args: object, **kwargs: object) -> BridgeSnapshot:
                return BridgeSnapshot(
                    snapshot_revision=4,
                    last_command_id=7,
                    last_command_kind=ProtocolCommand.SET_TEST_TARGET,
                    last_command_result=ProtocolResult.ALREADY_APPLIED,
                    last_error_code=ProtocolError.NONE,
                )

            replay._wait_for = replay_wait  # type: ignore[method-assign]
            asyncio.run(
                replay.send_command(ProtocolCommand.SET_TEST_TARGET, 1, command_id=7)
            )

            timed_out_commands: dict[tuple[str, int], ProtocolCommand] = {}
            timed_out = BridgeProtocol(
                Repl(),
                root / "timeout.tmp",
                "forensic-timeout",
                command_timeout=0.002,
                poll_interval=0.0001,
                event_sink=session.event_sink,
                timed_out_commands=timed_out_commands,
            )
            timed_out.session_nonce = "game-session"
            with self.assertRaises(ConnectionError):
                asyncio.run(
                    timed_out.send_command(
                        ProtocolCommand.SET_TEST_TARGET, 0, command_id=8
                    )
                )
            recovered_command = BridgeProtocol(
                Repl(),
                root / "recovered.tmp",
                "forensic-recovered",
                event_sink=session.event_sink,
                timed_out_commands=timed_out_commands,
            )
            recovered_command._observe_snapshot(
                BridgeSnapshot(
                    snapshot_revision=5,
                    session_nonce="game-session",
                    recent_command_receipts=(
                        CommandReceipt(
                            8,
                            ProtocolCommand.SET_TEST_TARGET,
                            0,
                            ProtocolResult.APPLIED,
                            ProtocolError.NONE,
                        ),
                    ),
                )
            )

            class FailedRepl:
                async def send_form(self, form: str, timeout: float = 10.0) -> str:
                    raise ConnectionError("synthetic command transport failure")

            failed = BridgeProtocol(
                FailedRepl(),
                root / "failed.tmp",
                "forensic-failed",
                event_sink=session.event_sink,
            )
            failed.session_nonce = "game-session"
            with self.assertRaises(ConnectionError):
                asyncio.run(
                    failed.send_command(
                        ProtocolCommand.SET_TEST_TARGET, 0, command_id=9
                    )
                )

            class ClosedRepl:
                async def close(self) -> None:
                    return None

            context = object.__new__(Jak3Context)
            context.diagnostics = session
            context.repl = ClosedRepl()
            context.state_session = None
            context.protocol = None
            context.bridge_ready = True
            context.source_loaded = True
            context.game_attached = True
            context.last_bridge_error = ""
            context._communication_lost = False
            asyncio.run(
                context.mark_bridge_unavailable(
                    ConnectionError("synthetic communication loss")
                )
            )
            context.mark_bridge_reconnected()

            required_events = (
                "client.started",
                "process.capture_gap",
                "process.crashed",
                "persistence.backup.restored",
                "persistence.binding.rejected",
                "protocol.command.submitted",
                "protocol.command.replayed",
                "protocol.command.timed_out",
                "protocol.command.recovered",
                "protocol.command.failed",
                "runtime.communication.lost",
                "runtime.communication.reconnected",
            )
            session.register_context_provider(
                "runtime", lambda: {"client_status": "reconnected"}
            )
            session.register_context_provider(
                "persistence",
                lambda: {"revision": 8, "binding_status": "read_only"},
            )
            session.register_context_provider(
                "versions", lambda: {"source_set_sha256": "a" * 64}
            )
            session.register_context_provider(
                "commands",
                lambda: {
                    "recent": [
                        {
                            "command_id": 7,
                            "command_kind": 100,
                            "result": "replayed",
                            "error": 0,
                        }
                    ]
                },
            )
            session.register_context_provider(
                "capture_gaps", lambda: [{"component": "gk", "reason": "pre_existing"}]
            )
            result = session.export_bundle()
            self.assertEqual(result.status, "complete")
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                names = set(archive.namelist())
                self.assertEqual(
                    names,
                    {
                        "README.txt",
                        "capture_gaps.json",
                        "client.txt",
                        "commands.json",
                        "events.jsonl",
                        "manifest.json",
                        "opengoal.txt",
                        "persistence.json",
                        "runtime.json",
                        "versions.json",
                    },
                )
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(
                    manifest["bundle_manifest_version"], BUNDLE_MANIFEST_VERSION
                )
                for name, metadata in manifest["artifacts"].items():
                    self.assertEqual(
                        hashlib.sha256(archive.read(name)).hexdigest(),
                        metadata["sha256"],
                    )
                combined = b"".join(archive.read(name) for name in names)
                self.assertNotIn(b"hunter2", combined)
                self.assertNotIn(b"token=abc", combined)
                self.assertNotIn(b"compound-token", combined)
                self.assertNotIn(b"compound-secret", combined)
                self.assertNotIn(b"bearer-secret", combined)
                self.assertNotIn(b"url-secret", combined)
                self.assertNotIn(b"slot-user", combined)
                self.assertNotIn(b"private.example", combined)
                self.assertNotIn(secret_uuid.encode(), combined)
                self.assertNotIn(uuid_v7.encode(), combined)
                self.assertNotIn(nil_uuid.encode(), combined)
                self.assertNotIn(b"Forensic Slot", combined)
                self.assertNotIn(b"Other Slot", combined)
                self.assertNotIn(b"forensic-seed", combined)
                events = [
                    json.loads(line)
                    for line in archive.read("events.jsonl").decode().splitlines()
                ]
                bundled_names = [event["event_name"] for event in events]
                self.assertIn("diagnostics.bundle.export.started", bundled_names)
                self.assertNotIn("diagnostics.bundle.export.completed", bundled_names)
                self.assertNotIn("diagnostics.event.rejected", bundled_names)
                for event_name in required_events:
                    self.assertIn(event_name, bundled_names)
                self.assertEqual(
                    [event["event_sequence"] for event in events],
                    sorted(event["event_sequence"] for event in events),
                )
                command_events = [
                    event
                    for event in events
                    if event["event_name"]
                    in {"protocol.command.submitted", "protocol.command.replayed"}
                    and event["context"].get("command_id") == 7
                ]
                self.assertEqual(
                    {event["correlation_id"] for event in command_events},
                    {"command:7"},
                )
                replayed = next(
                    event
                    for event in command_events
                    if event["event_name"] == "protocol.command.replayed"
                )
                self.assertEqual(
                    replayed["context"]["result"],
                    int(ProtocolResult.ALREADY_APPLIED),
                )
                recovered_load = next(
                    event
                    for event in events
                    if event["event_name"] == "persistence.state.loaded"
                    and event["context"].get("status") == "recovered_backup"
                )
                self.assertIsInstance(recovered_load["persistent_state_revision"], int)
                capture_gap = next(
                    event
                    for event in events
                    if event["event_name"] == "process.capture_gap"
                )
                self.assertEqual(
                    capture_gap["context"]["capture"], "pre_existing_process"
                )
                self.assertFalse(
                    any(
                        name.endswith((".sav", ".dmp")) or name == "state.json"
                        for name in names
                    )
                )

    def test_export_holds_the_writer_lock_while_snapshotting_segments(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "export-lock")
            session.emit("client.started")
            entered = threading.Event()
            release = threading.Event()
            writer_finished = threading.Event()
            original_merge = session._merged_events
            calls = 0

            def blocked_merge(missing: list[str]) -> bytes:
                nonlocal calls
                calls += 1
                if calls == 1:
                    entered.set()
                    self.assertTrue(release.wait(2.0))
                return original_merge(missing)

            with patch.object(session, "_merged_events", side_effect=blocked_merge):
                exporter = threading.Thread(target=session.export_bundle)
                exporter.start()
                self.assertTrue(entered.wait(2.0))

                def write_during_export() -> None:
                    session.emit("client.stopping")
                    writer_finished.set()

                writer = threading.Thread(target=write_during_export)
                writer.start()
                self.assertFalse(writer_finished.wait(0.05))
                release.set()
                exporter.join(2.0)
                writer.join(2.0)

            self.assertFalse(exporter.is_alive())
            self.assertTrue(writer_finished.is_set())

    def test_logging_setup_does_not_start_archipelagos_log_cleaner(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "owned-retention")
            with patch("worlds.jak3.agents.diagnostics.Utils.init_logging") as upstream:
                session.initialize()
            try:
                upstream.assert_not_called()
            finally:
                session.close()

    def test_console_only_logging_redacts_secrets(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "console-redaction")
            session.storage_mode = "console"
            output = io.StringIO()
            root = logging.getLogger()
            previous_handlers = tuple(root.handlers)
            try:
                with patch("worlds.jak3.agents.diagnostics.sys.stdout", output):
                    session._install_logging()
                    logging.getLogger("privacy-test").warning(
                        "password=hunter2 token=abc"
                    )
                    for handler in root.handlers:
                        handler.flush()
            finally:
                for handler in tuple(root.handlers):
                    root.removeHandler(handler)
                    handler.close()
                for handler in previous_handlers:
                    root.addHandler(handler)
            rendered = output.getvalue()
            self.assertNotIn("hunter2", rendered)
            self.assertNotIn("token=abc", rendered)
            self.assertIn("<redacted>", rendered)

    def test_logging_preserves_nofile_nostream_and_progress_routing(self) -> None:
        with TemporaryDirectory() as directory:
            session = DiagnosticSession.create(Path(directory), "log-routing")
            output = io.StringIO()
            root = logging.getLogger()
            previous_handlers = tuple(root.handlers)
            try:
                with patch("worlds.jak3.agents.diagnostics.sys.stdout", output):
                    session._install_logging()
                    logger = logging.getLogger("routing-test")
                    logger.warning("file-only", extra={"NoStream": True})
                    logger.warning("stream-only", extra={"NoFile": True})
                    logger.warning("progress\rupdate")
                    for handler in root.handlers:
                        handler.flush()
            finally:
                for handler in tuple(root.handlers):
                    root.removeHandler(handler)
                    handler.close()
                for handler in previous_handlers:
                    root.addHandler(handler)
            client_log = session.client_log.read_text("utf-8")
            console = output.getvalue()
            self.assertIn("file-only", client_log)
            self.assertNotIn("file-only", console)
            self.assertIn("stream-only", console)
            self.assertNotIn("stream-only", client_log)
            self.assertIn("progress", console)
            self.assertNotIn("progress", client_log)

    def test_bundle_truncation_retains_newest_fallback_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            session = DiagnosticSession.create(root, "newest-evidence")
            historical = root / "Jak3Client_newest-evidence-primary.txt"
            historical.write_text("OLD-EVIDENCE-" + "a" * 200, encoding="utf-8")
            session._artifact_history["client"].append(historical)
            session.client_log.write_text(
                "b" * 200 + "NEWEST-EVIDENCE\n", encoding="utf-8"
            )

            with patch("worlds.jak3.agents.diagnostics.MAX_BUNDLE_TEXT_CHARS", 128):
                merged = session._merged_text("client", session.client_log)
                result = session.export_bundle()

            assert merged is not None
            payload, truncated = merged
            self.assertTrue(truncated)
            self.assertIn(b"earlier sanitized log content omitted", payload)
            self.assertIn(b"NEWEST-EVIDENCE", payload)
            self.assertNotIn(b"OLD-EVIDENCE", payload)
            self.assertEqual(result.status, "partial")
            self.assertEqual(result.truncated, ("client.txt",))
            assert result.path is not None
            with zipfile.ZipFile(result.path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["truncated"], ["client.txt"])

    def test_initialize_reserves_full_current_session_rotation_capacity(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=2,
            retention_days=14,
            managed_bytes=16 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "Jak3Events_old.jsonl"
            old.write_bytes(b"x" * 12_000)
            session = DiagnosticSession.create(root, "reserved", policy=policy)
            session.initialize()
            try:
                self.assertFalse(old.exists())
                self.assertLessEqual(
                    session._managed_usage_bytes()
                    + session._future_active_log_growth(),
                    policy.managed_bytes,
                )
            finally:
                session.close()

    def test_retention_keeps_current_session(self) -> None:
        policy = DiagnosticPolicy(
            segment_bytes=1024,
            backups_per_artifact=1,
            retained_sessions=2,
            retention_days=1,
            managed_bytes=16 * 1024,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "Jak3Events_old.jsonl"
            old.write_text("old", encoding="utf-8")
            old_support = root / "Jak3Support_old_20200101T000000000000Z.zip"
            old_support.write_bytes(b"old-support")
            os.utime(old, (0, 0))
            os.utime(old_support, (0, 0))
            session = DiagnosticSession.create(root, "current", policy=policy)
            session.initialize()
            try:
                current_segment = Path(f"{session.events_log}.1")
                current_segment.write_bytes(b"x" * 15_000)
                os.utime(current_segment, (0, 0))
                session._prune_retention()
                self.assertTrue(session.events_log.is_file())
                self.assertTrue(current_segment.is_file())
                self.assertFalse(old.exists())
                self.assertFalse(old_support.exists())
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
