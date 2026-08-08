"""Locate and launch the official OpenGOAL Jak 3 install.

This follows the proven Jak 1 client lifecycle while keeping path discovery and
process creation independent of Archipelago networking for unit testing.
"""

from __future__ import annotations

import codecs
import hashlib
import json
import os
import pkgutil
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .diagnostics import DiagnosticSession
from .protocol import (
    BRIDGE_RUNTIME_VERSION,
    GAME_INTEGRATION_VERSION,
    PROTOCOL_VERSION,
)


BRIDGE_RESOURCE = "assets/opengoal/archipelago.gc"
BRIDGE_DESTINATION = Path("goal_src/jak3/pc/features/archipelago.gc")
BRIDGE_RELOAD_MARKER = Path("goal_src/jak3/pc/features/.archipelago-reload-required")
STARTUP_RESOURCE = "assets/opengoal/archipelago-startup.gc"
STARTUP_DESTINATION = Path("goal_src/jak3/pc/features/archipelago-startup.gc")
BOOTSTRAP_TYPES_SOURCE = Path("decompiler/config/jak3/all-types.gc")
BOOTSTRAP_TYPES_DESTINATION = Path(
    "goal_src/jak3/pc/features/archipelago-bootstrap-types.gc"
)
GAME_DGO = Path("goal_src/jak3/dgos/game.gd")


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
    source_path: Path
    reload_marker_path: Path
    startup_path: Path
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


def load_packaged_bridge() -> bytes:
    """Read the GOAL bridge carried inside the installed APWorld."""

    package = __package__.rsplit(".", 1)[0]
    payload = pkgutil.get_data(package, BRIDGE_RESOURCE)
    if not payload:
        raise FileNotFoundError(
            f"The installed Jak 3 APWorld is missing {BRIDGE_RESOURCE}; reinstall the APWorld."
        )
    _validate_bridge_payload(payload)
    return payload


def load_packaged_startup() -> bytes:
    """Read the pre-compile wait overlay carried inside the APWorld."""

    package = __package__.rsplit(".", 1)[0]
    payload = pkgutil.get_data(package, STARTUP_RESOURCE)
    if not payload:
        raise FileNotFoundError(
            f"The installed Jak 3 APWorld is missing {STARTUP_RESOURCE}; reinstall the APWorld."
        )
    if (
        b"(in-package goal)" not in payload
        or b"ap-bootstrap-show-startup-wait!" not in payload
    ):
        raise ValueError("The bundled OpenGOAL startup overlay payload is invalid.")
    return payload


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


def install_packaged_bridge(
    install: OpenGoalInstall,
    payload: bytes | None = None,
    startup_payload: bytes | None = None,
) -> BridgeInstallResult:
    """Install/repair the APWorld's bridge and pre-compile overlay."""

    bridge_payload = payload if payload is not None else load_packaged_bridge()
    compile_overlay_payload = (
        startup_payload if startup_payload is not None else load_packaged_startup()
    )
    bootstrap_types_payload = _build_bootstrap_type_database(install)
    _validate_bridge_payload(bridge_payload)
    if (
        b"(in-package goal)" not in compile_overlay_payload
        or b"ap-bootstrap-show-startup-wait!" not in compile_overlay_payload
    ):
        raise ValueError("The OpenGOAL startup overlay payload is invalid.")

    source_path = install.project_directory / BRIDGE_DESTINATION
    reload_marker_path = install.project_directory / BRIDGE_RELOAD_MARKER
    startup_path = install.project_directory / STARTUP_DESTINATION
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
    bridge_entries = list(
        re.finditer(r'(?m)^[ \t]*"archipelago\.o"[ \t]*(?=\r?$)', project_text)
    )
    if len(task_entries) != 1:
        raise ValueError(
            f"Expected one task-control.o entry in {project_path}; found {len(task_entries)}."
        )
    if len(bridge_entries) > 1:
        raise ValueError(
            f"Expected at most one archipelago.o entry in {project_path}; found {len(bridge_entries)}."
        )
    if bridge_entries and bridge_entries[0].start() < task_entries[0].end():
        raise ValueError(
            "archipelago.o must load after task-control.o in the Jak 3 project."
        )

    project_updated = not bridge_entries
    if project_updated:
        marker = task_entries[0].group(0)
        indent_match = re.match(r"[ \t]*", marker)
        assert indent_match is not None
        indent = indent_match.group(0)
        newline = "\r\n" if "\r\n" in project_text else "\n"
        project_text = (
            project_text[: task_entries[0].end()]
            + newline
            + indent
            + '"archipelago.o"'
            + project_text[task_entries[0].end() :]
        )

    source_updated = (
        not source_path.is_file() or source_path.read_bytes() != bridge_payload
    )
    startup_updated = (
        not startup_path.is_file()
        or startup_path.read_bytes() != compile_overlay_payload
    )
    bootstrap_types_updated = (
        not bootstrap_types_path.is_file()
        or bootstrap_types_path.read_bytes() != bootstrap_types_payload
    )
    if source_updated:
        # Record the live-reload obligation before replacing the installed
        # source. If this client exits before a snapshot proves a new
        # activation generation, a later client must still reload the
        # corrected same-contract object.
        marker_payload = hashlib.sha256(bridge_payload).hexdigest().encode("ascii")
        _atomic_write(reload_marker_path, marker_payload + b"\n")
        _atomic_write(source_path, bridge_payload)
    if startup_updated:
        _atomic_write(startup_path, compile_overlay_payload)
    if bootstrap_types_updated:
        _atomic_write(bootstrap_types_path, bootstrap_types_payload)
    if project_updated:
        _atomic_write(project_path, project_text.encode("utf-8"))

    return BridgeInstallResult(
        source_updated=source_updated,
        reload_required=reload_marker_path.is_file(),
        project_updated=project_updated,
        startup_updated=startup_updated,
        bootstrap_types_updated=bootstrap_types_updated,
        source_path=source_path,
        reload_marker_path=reload_marker_path,
        startup_path=startup_path,
        bootstrap_types_path=bootstrap_types_path,
        project_path=project_path,
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
    raw_path: Path,
    diagnostics: DiagnosticSession,
) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    offset = 0
    pending = ""
    while True:
        try:
            with raw_path.open("rb") as raw_stream:
                raw_stream.seek(offset)
                payload = raw_stream.read()
        except FileNotFoundError:
            payload = b""
        if payload:
            offset += len(payload)
            pending += decoder.decode(payload).replace("\r\n", "\n").replace("\r", "\n")
            last_newline = pending.rfind("\n")
            if last_newline >= 0:
                diagnostics.append_process_output(
                    label.upper(), pending[: last_newline + 1]
                )
                pending = pending[last_newline + 1 :]
        if process.poll() is not None and not payload:
            break
        time.sleep(0.05)

    pending += decoder.decode(b"", final=True)
    if pending:
        diagnostics.append_process_output(label.upper(), pending)
    diagnostics.note_opengoal(
        "CLIENT",
        f"{label} process exited: pid={process.pid} return_code={process.returncode}",
    )
    try:
        raw_path.unlink()
    except OSError as exc:
        diagnostics.note_opengoal(
            "CLIENT", f"could not remove {label} spool file: {exc}"
        )


def _launch_logged_process(
    command: tuple[str, ...],
    creationflags: int,
    label: str,
    diagnostics: DiagnosticSession,
) -> subprocess.Popen:
    # Each process gets an internal spool file. A single-writer collector then
    # prefixes/sanitizes both streams into the support-facing OpenGOAL log,
    # avoiding cross-process file offsets that could overwrite GOAL events.
    raw_path = diagnostics.raw_output_path(label)
    raw_path.unlink(missing_ok=True)
    with raw_path.open("wb", buffering=0) as log_stream:
        process = subprocess.Popen(
            command,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    threading.Thread(
        target=_mirror_process_output,
        args=(process, label, raw_path, diagnostics),
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
    else:
        diagnostics.note_opengoal(
            "CLIENT",
            f"gk already running: pid={game_pid}; pre-existing stdout is not captured",
        )

    compiler_started = compiler_pid is None
    if compiler_started:
        compiler_process = _launch_logged_process(
            compiler_command, creation_console, "goalc", diagnostics
        )
        compiler_pid = compiler_process.pid
        diagnostics.note_opengoal("CLIENT", f"goalc started: pid={compiler_pid}")
    else:
        diagnostics.note_opengoal(
            "CLIENT",
            f"goalc already running: pid={compiler_pid}; pre-existing stdout is not captured",
        )

    return ProcessLaunchResult(
        game_started,
        compiler_started,
        game_pid,
        compiler_pid,
        game_command,
        compiler_command,
    )
