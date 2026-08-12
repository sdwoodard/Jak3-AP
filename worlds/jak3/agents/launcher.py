"""Locate and launch the official OpenGOAL Jak 3 install.

This follows the proven Jak 1 client lifecycle while keeping path discovery and
process creation independent of Archipelago networking for unit testing.
"""

from __future__ import annotations

import codecs
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .bridge_manifest import (
    MANIFEST_DESTINATION,
    BridgeManifest,
    load_packaged_manifest,
    load_packaged_modules,
)
from .diagnostics import DiagnosticSession, interprocess_directory_lock
from .protocol import (
    BRIDGE_RUNTIME_VERSION,
    GAME_INTEGRATION_VERSION,
    PROTOCOL_VERSION,
)


BRIDGE_RELOAD_MARKER = Path("goal_src/jak3/pc/features/.archipelago-reload-required")
BRIDGE_INSTALL_LOCK = Path("goal_src/jak3/pc/features/.archipelago-install.lock")
BOOTSTRAP_TYPES_SOURCE = Path("decompiler/config/jak3/all-types.gc")
BOOTSTRAP_TYPES_DESTINATION = Path(
    "goal_src/jak3/pc/features/archipelago-bootstrap-types.gc"
)
GAME_DGO = Path("goal_src/jak3/dgos/game.gd")
PROCESS_OUTPUT_LINE_LIMIT = 16 * 1024


@dataclass(frozen=True)
class OpenGoalInstall:
    binary_directory: Path
    project_directory: Path

    @property
    def gk(self) -> Path:
        return self.binary_directory / ("gk.exe" if os.name == "nt" else "gk")

    @property
    def goalc(self) -> Path:
        return self.binary_directory / ("goalc.exe" if os.name == "nt" else "goalc")

    @property
    def iso_directory(self) -> Path:
        return self.project_directory / "iso_data" / "jak3"

    def validate(self) -> None:
        missing = [
            path
            for path in (
                self.gk,
                self.goalc,
                self.project_directory,
                self.iso_directory,
            )
            if not path.exists()
        ]
        if missing:
            raise FileNotFoundError(
                "OpenGOAL Jak 3 is incomplete; missing " + ", ".join(map(str, missing))
            )


@dataclass(frozen=True)
class BridgeInstallResult:
    source_updated: bool
    reload_required: bool
    project_updated: bool
    startup_updated: bool
    bootstrap_types_updated: bool
    manifest_updated: bool
    modules_updated: tuple[str, ...]
    source_set_hash: str
    source_path: Path
    source_paths: tuple[Path, ...]
    reload_marker_path: Path
    startup_path: Path
    manifest_path: Path
    bootstrap_types_path: Path
    project_path: Path


@dataclass(frozen=True)
class ProcessLaunchResult:
    game_started: bool
    compiler_started: bool
    game_pid: int | None
    compiler_pid: int | None
    game_command: tuple[str, ...]
    compiler_command: tuple[str, ...]


def _validate_bridge_payload(payload: bytes) -> None:
    expected_protocol = f"(defconstant AP-PROTOCOL-VERSION {PROTOCOL_VERSION})".encode()
    expected_integration = (
        f"(defconstant AP-GAME-INTEGRATION-VERSION {GAME_INTEGRATION_VERSION})".encode()
    )
    expected_runtime = (
        f"(defconstant AP-BRIDGE-RUNTIME-VERSION {BRIDGE_RUNTIME_VERSION})".encode()
    )
    if (
        b"(in-package goal)" not in payload
        or expected_protocol not in payload
        or expected_integration not in payload
        or expected_runtime not in payload
    ):
        raise ValueError(
            "The bundled OpenGOAL bridge payload does not match the Python protocol versions."
        )


def load_packaged_bridge_set() -> tuple[BridgeManifest, Mapping[str, bytes]]:
    """Read and validate the complete deterministic bridge source set."""

    manifest = load_packaged_manifest()
    payloads = load_packaged_modules(manifest)
    _validate_module_payloads(manifest, payloads)
    manifest.source_set_sha256(payloads)
    return manifest, payloads


def load_packaged_bridge() -> bytes:
    """Read the GOAL bridge carried inside the installed APWorld."""

    manifest, payloads = load_packaged_bridge_set()
    module = next(module for module in manifest.modules if module.name == "control")
    return payloads[str(module.resource)]


def load_packaged_startup() -> bytes:
    """Read the pre-compile wait overlay carried inside the APWorld."""

    manifest, payloads = load_packaged_bridge_set()
    module = next(module for module in manifest.modules if module.name == "startup")
    return payloads[str(module.resource)]


def _validate_module_payloads(
    manifest: BridgeManifest, payloads: Mapping[str, bytes]
) -> None:
    for module in manifest.modules:
        payload = payloads.get(str(module.resource))
        if not payload:
            raise ValueError(f"Missing bridge payload for module {module.name}.")
        if module.name == "control":
            _validate_bridge_payload(payload)
        elif module.name == "startup":
            if (
                b"(in-package goal)" not in payload
                or b"ap-bootstrap-show-startup-wait!" not in payload
            ):
                raise ValueError("The OpenGOAL startup overlay payload is invalid.")
        elif module.name == "diagnostics":
            if (
                b"(in-package goal)" not in payload
                or b"ap-diagnostic-emit!" not in payload
                or b"AP-DIAGNOSTIC-RING-CAPACITY 64" not in payload
            ):
                raise ValueError("The OpenGOAL diagnostic module payload is invalid.")
        elif module.name == "items":
            if (
                b"(in-package goal)" not in payload
                or b"ap-items-reconcile-native-target!" not in payload
                or b"*ap3-permanent-items-reconcile-hook*" not in payload
            ):
                raise ValueError(
                    "The OpenGOAL permanent-item module payload is invalid."
                )


def _atomic_write(path: Path, payload: bytes) -> None:
    """Replace one generated/installed file without exposing a partial write."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _build_bootstrap_type_database(install: OpenGoalInstall) -> bytes:
    """Extract the metadata needed by the pre-build in-game overlay.

    OpenGOAL's generated all-types file later repeats some types and contains
    event-handler forms, so compiling the whole database as one source is not
    valid. The font matrix declaration is after every kernel/process/font type
    used by the overlay and before those later declarations.
    """

    source_path = install.project_directory / BOOTSTRAP_TYPES_SOURCE
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Jak 3 generated type database is missing: {source_path}. "
            "Decompile Jak 3 once in OpenGOAL Launcher, then retry."
        )
    source = source_path.read_bytes()
    marker = b"(define-extern *font-default-matrix* matrix)"
    if source.count(marker) != 1:
        raise ValueError(
            f"Expected one font matrix marker in {source_path}; found {source.count(marker)}."
        )
    marker_end = source.index(marker) + len(marker)
    line_end = source.find(b"\n", marker_end)
    if line_end < 0:
        line_end = len(source)
    else:
        line_end += 1
    header = (
        b";; Generated from OpenGOAL's Jak 3 all-types.gc by the Archipelago client.\n"
        b";; Contains only the kernel/process/font metadata needed before (mi).\n"
    )
    return header + source[:line_end]


def _install_packaged_bridge_locked(
    install: OpenGoalInstall,
    payload: bytes | None = None,
    startup_payload: bytes | None = None,
    *,
    manifest: BridgeManifest | None = None,
    module_payloads: Mapping[str, bytes] | None = None,
) -> BridgeInstallResult:
    """Transactionally install/repair the manifest-declared bridge source set."""

    if manifest is None or module_payloads is None:
        packaged_manifest, packaged_payloads = load_packaged_bridge_set()
        manifest = manifest or packaged_manifest
        resolved_payloads = dict(module_payloads or packaged_payloads)
    else:
        resolved_payloads = dict(module_payloads)
    control_module = next(
        module for module in manifest.modules if module.name == "control"
    )
    startup_module = next(
        module for module in manifest.modules if module.name == "startup"
    )
    if payload is not None:
        resolved_payloads[str(control_module.resource)] = payload
    if startup_payload is not None:
        resolved_payloads[str(startup_module.resource)] = startup_payload
    payloads: Mapping[str, bytes] = MappingProxyType(resolved_payloads)
    _validate_module_payloads(manifest, payloads)
    source_set_hash = manifest.source_set_sha256(payloads)
    bootstrap_types_payload = _build_bootstrap_type_database(install)

    module_paths = {
        module.name: install.project_directory / Path(str(module.destination))
        for module in manifest.modules
    }
    source_path = module_paths["control"]
    reload_marker_path = install.project_directory / BRIDGE_RELOAD_MARKER
    startup_path = module_paths["startup"]
    manifest_path = install.project_directory / MANIFEST_DESTINATION
    bootstrap_types_path = install.project_directory / BOOTSTRAP_TYPES_DESTINATION
    project_path = install.project_directory / GAME_DGO
    if not project_path.is_file():
        raise FileNotFoundError(f"Jak 3 project file is missing: {project_path}")

    # Decode the bytes directly so an install using CRLF is not rewritten to
    # LF merely because the bridge registration had to be added.
    project_text = project_path.read_bytes().decode("utf-8")
    task_entries = list(
        re.finditer(r'(?m)^[ \t]*"task-control\.o"[ \t]*(?=\r?$)', project_text)
    )
    if len(task_entries) != 1:
        raise ValueError(
            f"Expected one task-control.o entry in {project_path}; found {len(task_entries)}."
        )
    objects = tuple(
        module.object_name for module in manifest.runtime_modules if module.object_name
    )
    object_matches = {
        object_name: list(
            re.finditer(
                rf'(?m)^[ \t]*"{re.escape(object_name)}"[ \t]*(?=\r?$)',
                project_text,
            )
        )
        for object_name in objects
    }
    for object_name, entries in object_matches.items():
        if len(entries) > 1:
            raise ValueError(
                f"Expected at most one {object_name} entry in {project_path}; found {len(entries)}."
            )
        if entries and entries[0].start() < task_entries[0].end():
            raise ValueError(
                f"{object_name} must load after {manifest.object_anchor} in the Jak 3 project."
            )
    newline = "\r\n" if "\r\n" in project_text else "\n"
    indent_match = re.match(r"[ \t]*", task_entries[0].group(0))
    assert indent_match is not None
    indent = indent_match.group(0)
    lines = project_text.splitlines(keepends=True)
    anchor_line = next(
        index
        for index, line in enumerate(lines)
        if re.fullmatch(r'[ \t]*"task-control\.o"[ \t]*\r?\n?', line)
    )
    current_after_anchor_list: list[str] = []
    for line in lines[anchor_line + 1 : anchor_line + 1 + len(objects)]:
        line_match = re.fullmatch(r'[ \t]*"([^\"]+\.o)"[ \t]*\r?\n?', line)
        if line_match:
            current_after_anchor_list.append(line_match.group(1))
    current_after_anchor = tuple(current_after_anchor_list)
    project_updated = current_after_anchor != objects
    if project_updated:
        object_set = set(objects)
        lines = [
            line
            for line in lines
            if not (
                (match := re.fullmatch(r'[ \t]*"([^\"]+\.o)"[ \t]*\r?\n?', line))
                and match.group(1) in object_set
            )
        ]
        anchor_line = next(
            index
            for index, line in enumerate(lines)
            if re.fullmatch(r'[ \t]*"task-control\.o"[ \t]*\r?\n?', line)
        )
        object_lines = [f'{indent}"{object_name}"{newline}' for object_name in objects]
        lines[anchor_line + 1 : anchor_line + 1] = object_lines
        project_text = "".join(lines)

    module_updates = tuple(
        module.name
        for module in manifest.modules
        if not module_paths[module.name].is_file()
        or module_paths[module.name].read_bytes() != payloads[str(module.resource)]
    )
    source_updated = "control" in module_updates
    startup_updated = "startup" in module_updates
    manifest_updated = (
        not manifest_path.is_file() or manifest_path.read_bytes() != manifest.raw
    )
    bootstrap_types_updated = (
        not bootstrap_types_path.is_file()
        or bootstrap_types_path.read_bytes() != bootstrap_types_payload
    )
    changed_paths = [module_paths[name] for name in module_updates]
    if manifest_updated:
        changed_paths.append(manifest_path)
    if bootstrap_types_updated:
        changed_paths.append(bootstrap_types_path)
    if project_updated:
        changed_paths.append(project_path)
    originals = {
        path: path.read_bytes() if path.is_file() else None for path in changed_paths
    }
    reload_obligation = bool(module_updates or manifest_updated)
    if reload_obligation:
        # Persist before replacing any declared source. Ordinary failures roll
        # back files but intentionally keep this crash-safe obligation.
        _atomic_write(reload_marker_path, source_set_hash.encode("ascii") + b"\n")
    try:
        for module in manifest.modules:
            if module.name in module_updates:
                _atomic_write(module_paths[module.name], payloads[str(module.resource)])
        if manifest_updated:
            _atomic_write(manifest_path, manifest.raw)
        if bootstrap_types_updated:
            _atomic_write(bootstrap_types_path, bootstrap_types_payload)
        if project_updated:
            _atomic_write(project_path, project_text.encode("utf-8"))
    except Exception:
        for path, original in originals.items():
            try:
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, original)
            except OSError:
                pass
        raise

    return BridgeInstallResult(
        source_updated=source_updated,
        reload_required=reload_marker_path.is_file(),
        project_updated=project_updated,
        startup_updated=startup_updated,
        bootstrap_types_updated=bootstrap_types_updated,
        manifest_updated=manifest_updated,
        modules_updated=module_updates,
        source_set_hash=source_set_hash,
        source_path=source_path,
        source_paths=tuple(module_paths[module.name] for module in manifest.modules),
        reload_marker_path=reload_marker_path,
        startup_path=startup_path,
        manifest_path=manifest_path,
        bootstrap_types_path=bootstrap_types_path,
        project_path=project_path,
    )


def install_packaged_bridge(
    install: OpenGoalInstall,
    payload: bytes | None = None,
    startup_payload: bytes | None = None,
    *,
    manifest: BridgeManifest | None = None,
    module_payloads: Mapping[str, bytes] | None = None,
) -> BridgeInstallResult:
    """Install one coherent bridge source set under a cross-process lock."""

    lock_directory = install.project_directory / BRIDGE_INSTALL_LOCK
    with interprocess_directory_lock(lock_directory):
        return _install_packaged_bridge_locked(
            install,
            payload,
            startup_payload,
            manifest=manifest,
            module_payloads=module_payloads,
        )


def _settings_path() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise FileNotFoundError(
                "APPDATA is not defined; OpenGOAL Launcher settings cannot be located"
            )
        return Path(appdata) / "OpenGOAL-Launcher" / "settings.json"
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "OpenGOAL-Launcher"
            / "settings.json"
        )
    return Path.home() / ".config" / "OpenGOAL-Launcher" / "settings.json"


def find_install(settings_path: Path | None = None) -> OpenGoalInstall:
    """Resolve environment overrides or the OpenGOAL Launcher v2/v3 settings."""

    binary_override = os.environ.get("JAK3_OPENGOAL_BIN")
    project_override = os.environ.get("JAK3_OPENGOAL_PROJECT")
    if bool(binary_override) != bool(project_override):
        raise ValueError(
            "JAK3_OPENGOAL_BIN and JAK3_OPENGOAL_PROJECT must be set together"
        )
    if binary_override and project_override:
        install = OpenGoalInstall(
            Path(binary_override).expanduser().resolve(),
            Path(project_override).expanduser().resolve(),
        )
        install.validate()
        return install

    path = settings_path or _settings_path()
    with path.open("r", encoding="utf-8") as stream:
        settings = json.load(stream)
    base = Path(settings["installationDir"]).expanduser().resolve()
    version = settings.get("version")
    games = settings["games"]
    if version == "3.0":
        game = games["jak3"]
        installed_version = game["version"]
        installed = game["isInstalled"]
    elif version == "2.0":
        game = games["Jak 3"]
        installed_version = game.get("version") or game.get("installedVersion")
        installed = game["isInstalled"]
    else:
        raise ValueError(f"Unsupported OpenGOAL Launcher settings version: {version!r}")
    if not installed:
        raise FileNotFoundError("Jak 3 is not installed in OpenGOAL Launcher")
    install = OpenGoalInstall(
        base / "versions" / "official" / installed_version,
        base / "active" / "jak3" / "data",
    )
    install.validate()
    return install


def _running_pid(process_name: str) -> int | None:
    try:
        from PyMemoryEditor import OpenProcess, ProcessNotFoundError  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        process = OpenProcess(process_name=process_name)
        return int(process.pid)
    except ProcessNotFoundError:
        return None


def build_launch_commands(
    install: OpenGoalInstall,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Build the exact diagnostic-friendly Jak 3 runtime/compiler commands."""

    game_command = (
        str(install.gk),
        "-v",
        "--disable-ansi",
        "--proj-path",
        str(install.project_directory),
        "--game",
        "jak3",
        "--",
        "-boot",
        "-fakeiso",
        "-debug",
    )
    compiler_command = (
        str(install.goalc),
        "--disable-ansi",
        "--game",
        "jak3",
        "--proj-path",
        str(install.project_directory),
        "--iso-path",
        str(install.iso_directory),
    )
    return game_command, compiler_command


def _mirror_process_output(
    process: subprocess.Popen,
    label: str,
    diagnostics: DiagnosticSession,
) -> None:
    """Drain one bounded pipe without retaining unsanitized process output."""

    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    pending = ""
    discarding_oversized_line = False
    stream = process.stdout
    if stream is None:
        diagnostics.emit(
            "process.capture_gap",
            message="Launched process output pipe was unavailable.",
            source_component="launcher",
            context={"process": label, "capture": "pipe_unavailable"},
        )
        return
    while True:
        try:
            read_chunk = getattr(stream, "read1", stream.read)
            payload = read_chunk(16 * 1024)
        except OSError as exc:
            diagnostics.emit(
                "process.capture_gap",
                message="Launched process output pipe failed while being read.",
                source_component="launcher",
                context={
                    "process": label,
                    "capture": "pipe_read_failed",
                    "reason": type(exc).__name__,
                },
            )
            break
        if not payload:
            break
        decoded = decoder.decode(payload).replace("\r\n", "\n").replace("\r", "\n")
        if discarding_oversized_line:
            newline = decoded.find("\n")
            if newline < 0:
                continue
            decoded = decoded[newline + 1 :]
            discarding_oversized_line = False
        pending += decoded
        while True:
            newline = pending.find("\n")
            if newline >= 0:
                line = pending[: newline + 1]
                pending = pending[newline + 1 :]
                if len(line) <= PROCESS_OUTPUT_LINE_LIMIT:
                    diagnostics.append_process_output(label.upper(), line)
                else:
                    diagnostics.append_process_output(
                        label.upper(),
                        "[oversized process output line omitted before storage]\n",
                    )
                    diagnostics.emit(
                        "process.capture_gap",
                        message="Oversized process output line was omitted safely.",
                        source_component="launcher",
                        context={"process": label, "capture": "oversized_line"},
                    )
                continue
            if len(pending) > PROCESS_OUTPUT_LINE_LIMIT:
                diagnostics.append_process_output(
                    label.upper(),
                    "[oversized process output line omitted before storage]\n",
                )
                diagnostics.emit(
                    "process.capture_gap",
                    message="Oversized process output line was omitted safely.",
                    source_component="launcher",
                    context={"process": label, "capture": "oversized_line"},
                )
                pending = ""
                discarding_oversized_line = True
            break

    pending += decoder.decode(b"", final=True)
    if pending and not discarding_oversized_line:
        diagnostics.append_process_output(label.upper(), pending)
    return_code = process.poll()
    if return_code is None:
        return_code = process.wait()
    diagnostics.note_opengoal(
        "CLIENT",
        f"{label} process exited: pid={process.pid} return_code={return_code}",
    )
    diagnostics.emit(
        "process.crashed" if return_code else "process.exited",
        message=f"{label} process exited.",
        source_component="launcher",
        context={
            "process": label,
            "pid": process.pid,
            "return_code": return_code,
        },
    )


def _launch_logged_process(
    command: tuple[str, ...],
    creationflags: int,
    label: str,
    diagnostics: DiagnosticSession,
) -> subprocess.Popen:
    # A bounded pipe is sanitized and serialized directly into the managed log.
    # No unbounded unsanitized spool survives the client process.
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    threading.Thread(
        target=_mirror_process_output,
        args=(process, label, diagnostics),
        name=f"Jak3-{label}-log-collector",
        daemon=True,
    ).start()
    return process


def launch_missing_processes(
    install: OpenGoalInstall,
    diagnostics: DiagnosticSession,
) -> ProcessLaunchResult:
    """Start gk/goalc and combine both output streams in the OpenGOAL log."""

    creation_hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    creation_console = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    game_command, compiler_command = build_launch_commands(install)
    game_pid = _running_pid(install.gk.name)
    compiler_pid = _running_pid(install.goalc.name)

    diagnostics.note_opengoal("CLIENT", f"binary_directory={install.binary_directory}")
    diagnostics.note_opengoal(
        "CLIENT", f"project_directory={install.project_directory}"
    )
    diagnostics.note_opengoal("CLIENT", f"iso_directory={install.iso_directory}")
    diagnostics.note_opengoal(
        "CLIENT", "gk_command=" + subprocess.list2cmdline(game_command)
    )
    diagnostics.note_opengoal(
        "CLIENT", "goalc_command=" + subprocess.list2cmdline(compiler_command)
    )

    game_started = game_pid is None
    if game_started:
        game_process = _launch_logged_process(
            game_command, creation_hidden, "gk", diagnostics
        )
        game_pid = game_process.pid
        diagnostics.note_opengoal("CLIENT", f"gk started: pid={game_pid}")
        diagnostics.emit(
            "process.started",
            message="OpenGOAL game process started with captured output.",
            source_component="launcher",
            context={"process": "gk", "pid": game_pid, "capture": "complete"},
        )
    else:
        diagnostics.note_opengoal(
            "CLIENT",
            f"gk already running: pid={game_pid}; pre-existing stdout is not captured",
        )
        diagnostics.emit(
            "process.already_running",
            message="OpenGOAL game process was already running.",
            source_component="launcher",
            context={"process": "gk", "pid": game_pid},
        )
        diagnostics.emit(
            "process.capture_gap",
            message="Pre-existing game stdout cannot be captured retroactively.",
            source_component="launcher",
            context={"process": "gk", "capture": "pre_existing_process"},
        )

    compiler_started = compiler_pid is None
    if compiler_started:
        compiler_process = _launch_logged_process(
            compiler_command, creation_console, "goalc", diagnostics
        )
        compiler_pid = compiler_process.pid
        diagnostics.note_opengoal("CLIENT", f"goalc started: pid={compiler_pid}")
        diagnostics.emit(
            "process.started",
            message="OpenGOAL compiler process started with captured output.",
            source_component="launcher",
            context={
                "process": "goalc",
                "pid": compiler_pid,
                "capture": "complete",
            },
        )
    else:
        diagnostics.note_opengoal(
            "CLIENT",
            f"goalc already running: pid={compiler_pid}; pre-existing stdout is not captured",
        )
        diagnostics.emit(
            "process.already_running",
            message="OpenGOAL compiler process was already running.",
            source_component="launcher",
            context={"process": "goalc", "pid": compiler_pid},
        )
        diagnostics.emit(
            "process.capture_gap",
            message="Pre-existing compiler stdout cannot be captured retroactively.",
            source_component="launcher",
            context={"process": "goalc", "capture": "pre_existing_process"},
        )

    return ProcessLaunchResult(
        game_started,
        compiler_started,
        game_pid,
        compiler_pid,
        game_command,
        compiler_command,
    )
