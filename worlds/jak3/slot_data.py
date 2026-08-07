"""Versioned first-release slot-data compatibility contract.

The payload intentionally contains runtime decisions and compatibility
metadata, not redundant item/location name maps already supplied by the
Archipelago data package.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from .canonical import canonical_json_bytes, canonical_sha256, json_safe
from .option_resolution import ResolvedJak3Options, SUPPORTED_FIRST_RELEASE_OPTIONS
from .registry import (
    ITEM_TABLE_HASH,
    LOCATION_TABLE_HASH,
    MISSION_TABLE_HASH,
    ORB_THRESHOLD_LOCATIONS,
    SELECTED_SIDE_LOCATIONS,
)
from .versions import (
    DESIGN_VERSION,
    GAME_INTEGRATION_VERSION,
    ITEM_TABLE_VERSION,
    LOCATION_TABLE_VERSION,
    MISSION_PROFILE_VERSION,
    MISSION_TABLE_VERSION,
    PROTOCOL_VERSION,
    SLOT_DATA_VERSION,
    STATE_SCHEMA_VERSION,
)


RUNTIME_OPTION_FIELDS = (
    "goal",
    "mission_order",
    "logic_difficulty",
    "mission_equipment",
    "story_item_mode",
    "finale_relic_requirement",
    "mission_completion_checks",
    "vanilla_reward_checks",
    "mission_milestone_checks",
    "side_mission_sanity",
    "sanity_costs",
    "challenge_progression",
    "medal_sanity",
    "precursor_orb_sanity",
    "precursor_orb_bundle_size",
    "precursor_orb_progression_cap",
    "skull_gem_sanity",
    "secret_purchase_sanity",
    "allow_experimental_checks",
    "gun_shuffle",
    "gun_logic",
    "ammo_upgrade_shuffle",
    "armor_shuffle",
    "jetboard_shuffle",
    "jetboard_upgrade_shuffle",
    "invisibility_statues_shuffle",
    "light_power_shuffle",
    "dark_power_shuffle",
    "vehicle_shuffle",
    "eco_crystal_shuffle",
    "secret_upgrade_shuffle",
    "trap_percentage",
    "trap_duration",
    "death_link",
)

SLOT_DATA_KEYS = frozenset(
    {
        "seed_identifier",
        "protocol_version",
        "game_integration_version",
        "slot_data_version",
        "state_schema_version",
        "item_table_version",
        "location_table_version",
        "mission_table_version",
        "mission_profile_version",
        "item_table_hash",
        "location_table_hash",
        "mission_table_hash",
        "resolved_options_hash",
        "design_version",
        "resolved_options",
        "features",
        "goal",
        "enabled_location_families",
        "orb_thresholds",
        "challenge_policy",
        "trap_duration",
    }
)


def resolved_options_payload(resolved: ResolvedJak3Options) -> dict[str, Any]:
    """Return every resolved design option in a canonical semantic shape."""

    payload: dict[str, Any] = {}
    for field in sorted(fields(ResolvedJak3Options), key=lambda item: item.name):
        value = getattr(resolved, field.name)
        if field.name in {"filler_item_weights", "trap_weights"}:
            payload[field.name] = dict(value)
        else:
            payload[field.name] = value
    return json_safe(payload)


def resolved_options_hash(resolved: ResolvedJak3Options) -> str:
    return canonical_sha256(resolved_options_payload(resolved))


SUPPORTED_RESOLVED_OPTIONS_HASH = resolved_options_hash(SUPPORTED_FIRST_RELEASE_OPTIONS)


def _runtime_options(resolved: ResolvedJak3Options) -> dict[str, Any]:
    return {name: getattr(resolved, name) for name in RUNTIME_OPTION_FIELDS}


def _validate_seed_identifier(seed_identifier: object) -> str:
    if not isinstance(seed_identifier, str):
        raise ValueError("Jak 3 slot data `seed_identifier` must be a string.")
    if not seed_identifier or len(seed_identifier) > 128:
        raise ValueError(
            "Jak 3 slot data `seed_identifier` must contain 1-128 characters."
        )
    if any(
        ord(character) < 32 or ord(character) == 127 for character in seed_identifier
    ):
        raise ValueError(
            "Jak 3 slot data `seed_identifier` must not contain control characters."
        )
    return seed_identifier


def _exact_json_match(found: Any, expected: Any) -> bool:
    """Return whether two JSON values have identical values and concrete types."""

    if type(found) is not type(expected):
        return False
    if isinstance(expected, dict):
        return found.keys() == expected.keys() and all(
            _exact_json_match(found[key], expected_value)
            for key, expected_value in expected.items()
        )
    if isinstance(expected, list):
        return len(found) == len(expected) and all(
            _exact_json_match(found_value, expected_value)
            for found_value, expected_value in zip(found, expected)
        )
    return found == expected


def build_slot_data(
    resolved: ResolvedJak3Options, *, seed_identifier: str
) -> dict[str, Any]:
    """Build the deterministic JSON-safe first-release slot-data payload."""

    side_task_ids = sorted(
        location.native_task_id
        for location in SELECTED_SIDE_LOCATIONS
        if location.native_task_id is not None
    )
    excluded_side_task_ids = sorted(
        location.native_task_id
        for location in SELECTED_SIDE_LOCATIONS
        if location.native_task_id is not None and location.default_excluded
    )
    thresholds = sorted(
        location.orb_threshold
        for location in ORB_THRESHOLD_LOCATIONS
        if location.orb_threshold is not None
    )

    payload = {
        "seed_identifier": _validate_seed_identifier(seed_identifier),
        "protocol_version": PROTOCOL_VERSION,
        "game_integration_version": GAME_INTEGRATION_VERSION,
        "slot_data_version": SLOT_DATA_VERSION,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "item_table_version": ITEM_TABLE_VERSION,
        "location_table_version": LOCATION_TABLE_VERSION,
        "mission_table_version": MISSION_TABLE_VERSION,
        "mission_profile_version": MISSION_PROFILE_VERSION,
        "item_table_hash": ITEM_TABLE_HASH,
        "location_table_hash": LOCATION_TABLE_HASH,
        "mission_table_hash": MISSION_TABLE_HASH,
        "resolved_options_hash": resolved_options_hash(resolved),
        "design_version": DESIGN_VERSION,
        "resolved_options": _runtime_options(resolved),
        "features": {
            "mission_completion_checks": resolved.mission_completion_checks == "story",
            "major_reward_checks": resolved.vanilla_reward_checks == "major",
            "selected_side_challenges": resolved.side_mission_sanity == "selected",
            "precursor_orb_thresholds": resolved.precursor_orb_sanity
            == "global_bundles",
            "mission_milestones": resolved.mission_milestone_checks != "off",
            "medals": resolved.medal_sanity != "off",
            "skull_gem_checks": resolved.skull_gem_sanity != "off",
            "secret_purchase_checks": resolved.secret_purchase_sanity != "off",
            "traps": resolved.trap_percentage > 0,
            "death_link": resolved.death_link,
            "experimental_checks": resolved.allow_experimental_checks,
        },
        "goal": {
            "mode": resolved.goal,
            "native_task_id": 72,
            "finale_relic_requirement": resolved.finale_relic_requirement,
        },
        "enabled_location_families": [
            "major_reward",
            "precursor_orb_threshold",
            "selected_side_challenge",
            "story_completion",
        ],
        "orb_thresholds": {
            "mode": resolved.precursor_orb_sanity,
            "bundle_size": resolved.precursor_orb_bundle_size,
            "maximum": max(thresholds),
            "progression_cap": resolved.precursor_orb_progression_cap,
            "enabled_thresholds": thresholds,
        },
        "challenge_policy": {
            "mode": resolved.challenge_progression,
            "selected_task_ids": side_task_ids,
            "excluded_task_ids": excluded_side_task_ids,
        },
        "trap_duration": resolved.trap_duration,
    }
    safe_payload = json_safe(payload)
    validate_slot_data(safe_payload)
    return safe_payload


def validate_slot_data(payload: dict[str, Any]) -> None:
    """Validate the supported default-only compatibility envelope."""

    json_safe(payload)
    if set(payload) != SLOT_DATA_KEYS:
        missing = sorted(SLOT_DATA_KEYS - set(payload))
        unknown = sorted(set(payload) - SLOT_DATA_KEYS)
        raise ValueError(
            f"Invalid Jak 3 slot-data keys: missing={missing}, unknown={unknown}"
        )

    _validate_seed_identifier(payload["seed_identifier"])

    expected = {
        "protocol_version": PROTOCOL_VERSION,
        "game_integration_version": GAME_INTEGRATION_VERSION,
        "slot_data_version": SLOT_DATA_VERSION,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "item_table_version": ITEM_TABLE_VERSION,
        "location_table_version": LOCATION_TABLE_VERSION,
        "mission_table_version": MISSION_TABLE_VERSION,
        "mission_profile_version": MISSION_PROFILE_VERSION,
        "item_table_hash": ITEM_TABLE_HASH,
        "location_table_hash": LOCATION_TABLE_HASH,
        "mission_table_hash": MISSION_TABLE_HASH,
        "resolved_options_hash": SUPPORTED_RESOLVED_OPTIONS_HASH,
        "design_version": DESIGN_VERSION,
    }
    for key, expected_value in expected.items():
        if not _exact_json_match(payload[key], expected_value):
            raise ValueError(
                f"Incompatible Jak 3 slot data `{key}`: "
                f"expected {expected_value!r}, found {payload[key]!r}."
            )

    if set(payload["resolved_options"]) != set(RUNTIME_OPTION_FIELDS):
        raise ValueError("Jak 3 slot data has an incompatible resolved-options shape.")
    if not _exact_json_match(
        payload["resolved_options"],
        _runtime_options(SUPPORTED_FIRST_RELEASE_OPTIONS),
    ):
        raise ValueError("Jak 3 slot data has unsupported resolved option values.")
    if not _exact_json_match(
        payload["goal"],
        {
            "mode": "complete_city_win",
            "native_task_id": 72,
            "finale_relic_requirement": 5,
        },
    ):
        raise ValueError("Jak 3 slot data has an unsupported goal contract.")
    if not _exact_json_match(
        payload["trap_duration"], payload["resolved_options"]["trap_duration"]
    ):
        raise ValueError(
            "Jak 3 slot data trap duration disagrees with resolved options."
        )

    expected_features = {
        "mission_completion_checks": True,
        "major_reward_checks": True,
        "selected_side_challenges": True,
        "precursor_orb_thresholds": True,
        "mission_milestones": False,
        "medals": False,
        "skull_gem_checks": False,
        "secret_purchase_checks": False,
        "traps": False,
        "death_link": False,
        "experimental_checks": False,
    }
    if not _exact_json_match(payload["features"], expected_features):
        raise ValueError("Jak 3 slot data has incompatible feature flags.")
    if not _exact_json_match(
        payload["enabled_location_families"],
        [
            "major_reward",
            "precursor_orb_threshold",
            "selected_side_challenge",
            "story_completion",
        ],
    ):
        raise ValueError("Jak 3 slot data has incompatible location families.")
    if not _exact_json_match(
        payload["orb_thresholds"],
        {
            "mode": "global_bundles",
            "bundle_size": 25,
            "maximum": 600,
            "progression_cap": 300,
            "enabled_thresholds": list(range(25, 601, 25)),
        },
    ):
        raise ValueError("Jak 3 slot data has an incompatible orb-threshold contract.")
    if not _exact_json_match(
        payload["challenge_policy"],
        {
            "mode": "safe",
            "selected_task_ids": list(range(114, 138)),
            "excluded_task_ids": [127, 129, 130, 131, 132, 136],
        },
    ):
        raise ValueError("Jak 3 slot data has an incompatible challenge policy.")


def serialize_slot_data(
    resolved: ResolvedJak3Options, *, seed_identifier: str
) -> bytes:
    return canonical_json_bytes(
        build_slot_data(resolved, seed_identifier=seed_identifier)
    )
