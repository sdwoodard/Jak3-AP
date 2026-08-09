"""Validated, deterministic OpenGOAL bridge module manifest."""

from __future__ import annotations

import hashlib
import json
import pkgutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping


MANIFEST_VERSION = 1
MANIFEST_RESOURCE = "assets/opengoal/bridge-modules.json"
MANIFEST_DESTINATION = Path("goal_src/jak3/pc/features/archipelago-bridge-modules.json")
SOURCE_SET_FORMAT = "jak3-bridge-source-set-v1"
_EXPECTED_MODULES = (
    (
        "startup",
        10,
        "pre_mi",
        "goal_src/jak3/pc/features/archipelago-startup.gc",
        "assets/opengoal/archipelago-startup.gc",
        "goal_src/jak3/pc/features/archipelago-startup.gc",
        None,
    ),
    (
        "control",
        20,
        "bridge",
        "goal_src/jak3/pc/features/archipelago.gc",
        "assets/opengoal/archipelago.gc",
        "goal_src/jak3/pc/features/archipelago.gc",
        "archipelago.o",
    ),
    (
        "diagnostics",
        30,
        "bridge",
        "goal_src/jak3/pc/features/archipelago-diagnostics.gc",
        "assets/opengoal/archipelago-diagnostics.gc",
        "goal_src/jak3/pc/features/archipelago-diagnostics.gc",
        "archipelago-diagnostics.o",
    ),
)


@dataclass(frozen=True)
class BridgeModule:
    name: str
    order: int
    phase: str
    source: PurePosixPath
    resource: PurePosixPath
    destination: PurePosixPath
    object_name: str | None


@dataclass(frozen=True)
class BridgeManifest:
    raw: bytes
    manifest_version: int
    source_set_format: str
    object_anchor: str
    modules: tuple[BridgeModule, ...]

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()

    @property
    def runtime_modules(self) -> tuple[BridgeModule, ...]:
        return tuple(module for module in self.modules if module.phase == "bridge")

    def source_set_sha256(self, payloads: Mapping[str, bytes]) -> str:
        expected = {str(module.resource) for module in self.modules}
        if set(payloads) != expected:
            missing = sorted(expected - set(payloads))
            extra = sorted(set(payloads) - expected)
            raise ValueError(
                f"Bridge payload set does not match manifest; missing={missing}, extra={extra}."
            )
        lines = [
            self.source_set_format,
            f"manifest-sha256:{self.raw_sha256}",
        ]
        for module in self.modules:
            digest = hashlib.sha256(payloads[str(module.resource)]).hexdigest()
            lines.append(f"{module.order}:{module.name}:{digest}")
        return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def _safe_relative_path(value: Any, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Bridge module {field} must be a non-empty string.")
    if "\\" in value:
        raise ValueError(f"Bridge module {field} must use forward slashes: {value!r}.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"Unsafe bridge module {field}: {value!r}.")
    return path


def parse_bridge_manifest(raw: bytes) -> BridgeManifest:
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Bridge module manifest is not valid UTF-8 JSON.") from exc
    if not isinstance(document, dict):
        raise ValueError("Bridge module manifest root must be an object.")
    allowed_root = {
        "manifest_version",
        "source_set_format",
        "object_anchor",
        "modules",
    }
    if set(document) != allowed_root:
        raise ValueError("Bridge module manifest has unknown or missing root fields.")
    manifest_version = document["manifest_version"]
    if type(manifest_version) is not int:
        raise ValueError("Bridge manifest version must be an integer.")
    if manifest_version != MANIFEST_VERSION:
        raise ValueError(f"Unsupported bridge manifest version: {manifest_version!r}.")
    source_set_format = document["source_set_format"]
    if not isinstance(source_set_format, str):
        raise ValueError("Bridge source-set format must be a string.")
    if source_set_format != SOURCE_SET_FORMAT:
        raise ValueError("Unsupported bridge source-set format.")
    object_anchor = document["object_anchor"]
    if not isinstance(object_anchor, str):
        raise ValueError("Bridge object anchor must be a string.")
    if object_anchor != "task-control.o":
        raise ValueError("Bridge modules must be registered after task-control.o.")
    module_documents = document["modules"]
    if not isinstance(module_documents, list):
        raise ValueError("Bridge module manifest modules must be a list.")

    modules: list[BridgeModule] = []
    expected_fields = {
        "name",
        "order",
        "phase",
        "source",
        "resource",
        "destination",
        "object",
    }
    for entry in module_documents:
        if not isinstance(entry, dict) or set(entry) != expected_fields:
            raise ValueError(
                "Every bridge module must contain exactly the version 1 fields."
            )
        name = entry["name"]
        order = entry["order"]
        phase = entry["phase"]
        object_name = entry["object"]
        if not isinstance(name, str) or not name:
            raise ValueError("Bridge module name must be a non-empty string.")
        if not isinstance(order, int) or isinstance(order, bool):
            raise ValueError("Bridge module order must be an integer.")
        if not isinstance(phase, str) or phase not in {"pre_mi", "bridge"}:
            raise ValueError(f"Unsupported bridge module phase: {phase!r}.")
        if object_name is not None and (
            not isinstance(object_name, str) or not re_full_object_name(object_name)
        ):
            raise ValueError(f"Unsafe bridge object name: {object_name!r}.")
        modules.append(
            BridgeModule(
                name=name,
                order=order,
                phase=phase,
                source=_safe_relative_path(entry["source"], "source"),
                resource=_safe_relative_path(entry["resource"], "resource"),
                destination=_safe_relative_path(entry["destination"], "destination"),
                object_name=object_name,
            )
        )

    modules.sort(key=lambda module: module.order)
    for field in ("name", "order", "source", "resource", "destination"):
        values = [getattr(module, field) for module in modules]
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate bridge module {field}.")
    objects = [module.object_name for module in modules if module.object_name]
    if len(objects) != len(set(objects)):
        raise ValueError("Duplicate bridge module object.")
    actual_contract = tuple(
        (
            module.name,
            module.order,
            module.phase,
            str(module.source),
            str(module.resource),
            str(module.destination),
            module.object_name,
        )
        for module in modules
    )
    if actual_contract != _EXPECTED_MODULES:
        raise ValueError(
            "Bridge module manifest must declare startup, control, and diagnostics "
            "in the canonical version 1 order."
        )
    for module in modules:
        if module.source.name != module.resource.name:
            raise ValueError(f"Source/resource name mismatch for {module.name}.")
        if module.source != module.destination:
            raise ValueError(f"Source/destination mismatch for {module.name}.")
        if (
            not module.source.name.startswith("archipelago-")
            and module.name != "control"
        ):
            raise ValueError(f"Unexpected bridge source name for {module.name}.")
        if module.name == "control" and module.source.name != "archipelago.gc":
            raise ValueError("The control module source must remain archipelago.gc.")

    return BridgeManifest(
        raw=raw,
        manifest_version=MANIFEST_VERSION,
        source_set_format=SOURCE_SET_FORMAT,
        object_anchor="task-control.o",
        modules=tuple(modules),
    )


def re_full_object_name(value: str) -> bool:
    return value.endswith(".o") and all(
        character.isascii() and (character.isalnum() or character in "-_.")
        for character in value
    )


def load_packaged_manifest() -> BridgeManifest:
    package = __package__.rsplit(".", 1)[0]
    raw = pkgutil.get_data(package, MANIFEST_RESOURCE)
    if not raw:
        raise FileNotFoundError(
            f"The installed Jak 3 APWorld is missing {MANIFEST_RESOURCE}."
        )
    return parse_bridge_manifest(raw)


def load_packaged_modules(
    manifest: BridgeManifest | None = None,
) -> Mapping[str, bytes]:
    selected = manifest or load_packaged_manifest()
    package = __package__.rsplit(".", 1)[0]
    payloads: dict[str, bytes] = {}
    for module in selected.modules:
        resource = str(module.resource)
        payload = pkgutil.get_data(package, resource)
        if not payload:
            raise FileNotFoundError(
                f"The installed Jak 3 APWorld is missing {resource}."
            )
        payloads[resource] = payload
    return MappingProxyType(payloads)
