"""Normalization and validation boundary for Jak 3 generation options."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from Options import OptionError

from .options_schema import FILLER_DEFAULTS, TRAP_DEFAULTS


__all__ = [
    "ResolvedJak3Options",
    "SUPPORTED_FIRST_RELEASE_OPTIONS",
    "resolve_options",
    "validate_options",
]


FINALE_RELIC_COUNT = 7
MAX_PRECURSOR_ORBS = 600

GOAL_PROTOCOL_VALUES = {
    "complete_city_win": 0,
    "defeat_final_boss": 1,
    "all_story_tasks": 2,
    "relic_hunt": 3,
}


@dataclass(frozen=True, slots=True)
class ResolvedJak3Options:
    """Immutable, semantic option values consumed by Jak 3 world code."""

    progression_balancing: int
    accessibility: str
    goal: str
    mission_order: str
    logic_difficulty: str
    mission_equipment: str
    story_item_mode: str
    finale_relic_requirement: int
    early_route_item: str
    early_ranged_gun: str
    mission_completion_checks: str
    vanilla_reward_checks: str
    mission_milestone_checks: str
    side_mission_sanity: str
    sanity_costs: str
    challenge_progression: str
    medal_sanity: str
    precursor_orb_sanity: str
    precursor_orb_bundle_size: int
    precursor_orb_progression_cap: int
    skull_gem_sanity: str
    skull_gem_bundle_size: int
    secret_purchase_sanity: str
    allow_experimental_checks: bool
    gun_shuffle: str
    gun_logic: str
    ammo_upgrade_shuffle: bool
    armor_shuffle: str
    jetboard_shuffle: bool
    jetboard_upgrade_shuffle: bool
    invisibility_statues_shuffle: bool
    light_power_shuffle: str
    dark_power_shuffle: str
    vehicle_shuffle: str
    eco_crystal_shuffle: str
    secret_upgrade_shuffle: str
    filler_item_weights: tuple[tuple[str, int], ...]
    trap_percentage: int
    trap_duration: int
    trap_weights: tuple[tuple[str, int], ...]
    death_link: bool

    @property
    def goal_protocol_value(self) -> int:
        """Return the existing numeric goal representation used in slot data."""

        return GOAL_PROTOCOL_VALUES[self.goal]


SUPPORTED_FIRST_RELEASE_OPTIONS = ResolvedJak3Options(
    progression_balancing=65,
    accessibility="full",
    goal="complete_city_win",
    mission_order="tiered_open_board",
    logic_difficulty="standard",
    mission_equipment="bootstrap",
    story_item_mode="simplified_authorizations",
    finale_relic_requirement=5,
    early_route_item="guaranteed_local",
    early_ranged_gun="guaranteed_local",
    mission_completion_checks="story",
    vanilla_reward_checks="major",
    mission_milestone_checks="off",
    side_mission_sanity="selected",
    sanity_costs="free",
    challenge_progression="safe",
    medal_sanity="off",
    precursor_orb_sanity="global_bundles",
    precursor_orb_bundle_size=25,
    precursor_orb_progression_cap=300,
    skull_gem_sanity="off",
    skull_gem_bundle_size=25,
    secret_purchase_sanity="off",
    allow_experimental_checks=False,
    gun_shuffle="individual_mods",
    gun_logic="reliable_ranged",
    ammo_upgrade_shuffle=True,
    armor_shuffle="useful",
    jetboard_shuffle=True,
    jetboard_upgrade_shuffle=True,
    invisibility_statues_shuffle=True,
    light_power_shuffle="all",
    dark_power_shuffle="all",
    vehicle_shuffle="progressive_licenses",
    eco_crystal_shuffle="off",
    secret_upgrade_shuffle="off",
    filler_item_weights=tuple(FILLER_DEFAULTS.items()),
    trap_percentage=0,
    trap_duration=20,
    trap_weights=tuple(TRAP_DEFAULTS.items()),
    death_link=False,
)


_CHOICE_FIELDS = (
    "accessibility",
    "goal",
    "mission_order",
    "logic_difficulty",
    "mission_equipment",
    "story_item_mode",
    "early_route_item",
    "early_ranged_gun",
    "mission_completion_checks",
    "vanilla_reward_checks",
    "mission_milestone_checks",
    "side_mission_sanity",
    "sanity_costs",
    "challenge_progression",
    "medal_sanity",
    "precursor_orb_sanity",
    "skull_gem_sanity",
    "secret_purchase_sanity",
    "gun_shuffle",
    "gun_logic",
    "armor_shuffle",
    "light_power_shuffle",
    "dark_power_shuffle",
    "vehicle_shuffle",
    "eco_crystal_shuffle",
    "secret_upgrade_shuffle",
)

_INTEGER_FIELDS = (
    "progression_balancing",
    "finale_relic_requirement",
    "precursor_orb_bundle_size",
    "precursor_orb_progression_cap",
    "skull_gem_bundle_size",
    "trap_percentage",
    "trap_duration",
)

_TOGGLE_FIELDS = (
    "allow_experimental_checks",
    "ammo_upgrade_shuffle",
    "jetboard_shuffle",
    "jetboard_upgrade_shuffle",
    "invisibility_statues_shuffle",
    "death_link",
)


def _raw_option(options: object, name: str) -> Any:
    try:
        return getattr(options, name)
    except AttributeError as error:
        raise OptionError(f"Jak 3 option source is missing `{name}`.") from error


def _choice_key(options: object, name: str) -> str:
    option = _raw_option(options, name)
    try:
        key = option.current_key
    except (AttributeError, KeyError, TypeError) as error:
        raise OptionError(f"Jak 3 option `{name}` has no valid named value.") from error
    if not isinstance(key, str):
        raise OptionError(f"Jak 3 option `{name}` did not resolve to a named value.")
    return key


def _integer_value(options: object, name: str) -> int:
    value = _raw_option(options, name).value
    if isinstance(value, bool) or not isinstance(value, int):
        raise OptionError(f"Jak 3 option `{name}` must resolve to an integer.")
    return value


def _toggle_value(options: object, name: str) -> bool:
    value = _raw_option(options, name).value
    if value not in (0, 1, False, True):
        raise OptionError(f"Jak 3 option `{name}` must resolve to true or false.")
    return bool(value)


def _ordered_weights(options: object, name: str, keys: tuple[str, ...]) -> tuple[tuple[str, int], ...]:
    value = _raw_option(options, name).value
    if not isinstance(value, dict):
        raise OptionError(f"Jak 3 option `{name}` must resolve to a weight mapping.")
    if set(value) != set(keys):
        missing = sorted(set(keys) - set(value))
        unknown = sorted(set(value) - set(keys))
        details = []
        if missing:
            details.append(f"missing {missing}")
        if unknown:
            details.append(f"unknown {unknown}")
        raise OptionError(f"Jak 3 option `{name}` has invalid weight keys: {', '.join(details)}.")
    if any(isinstance(value[key], bool) or not isinstance(value[key], int) for key in keys):
        raise OptionError(f"Jak 3 option `{name}` weights must be integers.")
    return tuple((key, value[key]) for key in keys)


def resolve_options(options: object) -> ResolvedJak3Options:
    """Normalize Archipelago option objects, validate them, and return one safe snapshot."""

    values: dict[str, Any] = {}
    for name in _CHOICE_FIELDS:
        values[name] = _choice_key(options, name)
    for name in _INTEGER_FIELDS:
        values[name] = _integer_value(options, name)
    for name in _TOGGLE_FIELDS:
        values[name] = _toggle_value(options, name)
    values["filler_item_weights"] = _ordered_weights(
        options, "filler_item_weights", tuple(FILLER_DEFAULTS)
    )
    values["trap_weights"] = _ordered_weights(options, "trap_weights", tuple(TRAP_DEFAULTS))

    resolved = ResolvedJak3Options(**values)
    validate_options(resolved)
    return resolved


def validate_options(resolved: ResolvedJak3Options) -> None:
    """Reject invalid interactions and every profile not implemented for first release."""

    relics = resolved.finale_relic_requirement
    if not 0 <= relics <= FINALE_RELIC_COUNT:
        raise OptionError(
            "Jak 3 option `finale_relic_requirement` must be between 0 and "
            f"{FINALE_RELIC_COUNT}; received {relics}."
        )

    orb_cap = resolved.precursor_orb_progression_cap
    if not 0 <= orb_cap <= MAX_PRECURSOR_ORBS:
        raise OptionError(
            "Jak 3 option `precursor_orb_progression_cap` must be between 0 and "
            f"{MAX_PRECURSOR_ORBS}; received {orb_cap}."
        )

    if resolved.story_item_mode == "canonical":
        raise OptionError(
            "Jak 3 option `story_item_mode`: `canonical` is unsupported because the canonical "
            "story gate table is not implemented. Use `simplified_authorizations`."
        )

    experimental_collectibles = []
    if resolved.side_mission_sanity in {"orb_hunts", "all"}:
        experimental_collectibles.append("side_mission_sanity")
    if resolved.precursor_orb_sanity in {"regional_bundles", "individual_static"}:
        experimental_collectibles.append("precursor_orb_sanity")
    if resolved.skull_gem_sanity == "individual_static":
        experimental_collectibles.append("skull_gem_sanity")
    if experimental_collectibles and not resolved.allow_experimental_checks:
        names = ", ".join(f"`{name}`" for name in experimental_collectibles)
        raise OptionError(
            "Jak 3 experimental collectible modes require `allow_experimental_checks: true`; "
            f"unsupported fields: {names}."
        )

    if resolved.allow_experimental_checks:
        raise OptionError(
            "Jak 3 option `allow_experimental_checks`: true is unsupported in the first release; "
            "matching experimental location and client tables are not implemented."
        )

    changed = [
        field.name
        for field in fields(ResolvedJak3Options)
        if getattr(resolved, field.name) != getattr(SUPPORTED_FIRST_RELEASE_OPTIONS, field.name)
    ]
    if changed:
        names = ", ".join(f"`{name}`" for name in changed)
        raise OptionError(
            "Jak 3 currently supports the documented first-release profile only. "
            f"These options use unsupported values: {names}."
        )
