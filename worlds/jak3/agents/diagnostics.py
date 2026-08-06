"""Paired diagnostic logs for one Jak 3 Archipelago client session."""

from __future__ import annotations

import json
import logging
import os
import pkgutil
import platform
import re
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import Utils


CLIENT_LOG_FORMAT = "[%(levelname)s] [%(name)s at %(asctime)s]: %(message)s"
ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def _world_metadata() -> dict[str, object]:
    package = __package__.rsplit(".", 1)[0]
    try:
        payload = pkgutil.get_data(package, "archipelago.json")
        return json.loads(payload.decode("utf-8")) if payload else {}
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
        return {}


@dataclass(frozen=True)
class DiagnosticSession:
    """The two support-facing files produced during one client run."""

    session_id: str
    client_log: Path
    opengoal_log: Path
    _write_lock: threading.Lock = field(default_factory=threading.Lock, compare=False, repr=False)

    @classmethod
    def create(
        cls,
        log_directory: Path | None = None,
        session_id: str | None = None,
    ) -> "DiagnosticSession":
        directory = log_directory or Path(Utils.user_path("logs"))
        directory.mkdir(parents=True, exist_ok=True)
        identifier = session_id or (
            datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f") + f"_{os.getpid()}"
        )
        return cls(
            identifier,
            directory / f"Jak3Client_{identifier}.txt",
            directory / f"Jak3OpenGOAL_{identifier}.txt",
        )

    def initialize(self) -> None:
        """Configure Archipelago logging and create the matching OpenGOAL log."""

        Utils.init_logging(
            f"Jak3Client_{self.session_id}",
            loglevel=logging.INFO,
            write_mode="a",
            log_format=CLIENT_LOG_FORMAT,
            exception_logger="Client",
        )
        # Keep third-party libraries at their normal levels while retaining
        # detailed Jak 3 protocol and logic events in the file handler.
        logging.getLogger("Client").setLevel(logging.DEBUG)
        logging.captureWarnings(True)

        metadata = _world_metadata()
        common = [
            "Jak 3 Archipelago diagnostic session",
            f"session_id={self.session_id}",
            f"created_local={datetime.now().astimezone().isoformat()}",
            f"apworld_version={metadata.get('world_version', 'unknown')}",
            f"archipelago_version={getattr(Utils, '__version__', 'unknown')}",
            f"python={platform.python_version()} frozen={bool(getattr(sys, 'frozen', False))}",
            f"platform={platform.platform()}",
            f"executable={sys.executable}",
            f"working_directory={Path.cwd()}",
            f"client_log={self.client_log}",
            f"opengoal_log={self.opengoal_log}",
        ]
        self.opengoal_log.write_text(
            "=== " + common[0] + " ===\n"
            + "\n".join(common[1:])
            + "\noutput_encoding=UTF-8; ANSI control sequences stripped by collector\n"
            + "This file combines [GK], [GOALC], [JAK3-AP], and [CLIENT] events.\n\n",
            encoding="utf-8",
        )
        logger = logging.getLogger("Client")
        logger.info("=== %s ===", common[0])
        for line in common[1:]:
            logger.info("DIAGNOSTIC %s", line)
        logger.info("Keep both paired diagnostic files when reporting a problem.")

    def note_opengoal(self, source: str, message: str) -> None:
        """Append a client-side lifecycle marker to the OpenGOAL output."""

        timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
        clean_message = message.replace("\r", "\\r").replace("\n", "\\n")
        with self._write_lock:
            with self.opengoal_log.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(f"[{timestamp}] [{source}] {clean_message}\n")
                stream.flush()

    def append_process_output(self, source: str, output: str) -> None:
        """Append sanitized child output with an unambiguous process prefix."""

        clean_output = ANSI_ESCAPE.sub("", output).replace("\r\n", "\n").replace("\r", "\n")
        if not clean_output:
            return
        lines = clean_output.splitlines(keepends=True)
        with self._write_lock:
            with self.opengoal_log.open("a", encoding="utf-8", newline="\n") as stream:
                for line in lines:
                    stream.write(f"[{source}] {line.rstrip(chr(10))}\n")
                stream.flush()

    def raw_output_path(self, source: str) -> Path:
        """Return an internal spool path, not a third support-facing log."""

        safe_source = "".join(character for character in source if character.isalnum()).lower()
        return Path(tempfile.gettempdir()) / f"jak3-ap-{self.session_id}-{safe_source}.raw"

    def flush(self) -> None:
        """Make the current diagnostic snapshot immediately shareable."""

        for handler in logging.getLogger().handlers:
            handler.flush()
