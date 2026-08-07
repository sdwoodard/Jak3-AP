"""Canonical JSON serialization used by compatibility hashes.

The contract is UTF-8 encoded JSON with sorted object keys, no insignificant
whitespace, lowercase JSON literals, and a trailing newline.  Tuples are
serialized as arrays.  Only JSON-safe scalar values and mappings with string
keys are accepted.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any


def json_safe(value: Any) -> Any:
    """Return a normalized JSON-safe value or reject unsupported input."""

    if is_dataclass(value) and not isinstance(value, type):
        return json_safe(asdict(value))
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        raise TypeError(
            "Compatibility payloads must not contain floating-point values."
        )
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Compatibility payload mappings must use string keys.")
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_safe(item) for item in value]
    raise TypeError(f"Value is not JSON-safe: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize *value* using the documented deterministic byte encoding."""

    normalized = json_safe(value)
    rendered = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (rendered + "\n").encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return the lowercase SHA-256 digest of canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
