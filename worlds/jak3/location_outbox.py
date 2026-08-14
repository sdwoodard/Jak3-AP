"""Pure persistent transitions for the Milestone 10 Jak 3 location slice."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping

from .persistence import PersistentState, StateCompatibilityError
from .registry import FIRST_RELEASE_LOCATIONS
from .slot_data import validate_slot_data


ARENA_TRAINING_LOCATION_ID = 743_001_010
FIRST_WAR_AMULET_LOCATION_ID = 743_001_011
KANGA_RATS_LOCATION_ID = 743_001_012
SATELLITE_LOCATION_ID = 743_001_013
VEHICLE_TRAINING_LOCATION_ID = 743_001_014
KLEIVER_RACE_LOCATION_ID = 743_001_015
ARTIFACT_RACE_LOCATION_ID = 743_001_016
FIRST_ARMOR_REWARD_LOCATION_ID = 743_020_036
LOCATION_OBSERVED_GOAL_CODE = 600
LOCATION_RETRY_SECONDS = 5.0

LOCATION_TASK_IDS = {
    ARENA_TRAINING_LOCATION_ID: 10,
    FIRST_WAR_AMULET_LOCATION_ID: 11,
    KANGA_RATS_LOCATION_ID: 12,
    SATELLITE_LOCATION_ID: 13,
    VEHICLE_TRAINING_LOCATION_ID: 14,
    KLEIVER_RACE_LOCATION_ID: 15,
    ARTIFACT_RACE_LOCATION_ID: 16,
    FIRST_ARMOR_REWARD_LOCATION_ID: 16,
}
LOCATION_SOURCES = {
    ARENA_TRAINING_LOCATION_ID: "native_task_complete",
    FIRST_WAR_AMULET_LOCATION_ID: "native_task_complete",
    KANGA_RATS_LOCATION_ID: "native_task_complete",
    SATELLITE_LOCATION_ID: "native_task_complete",
    VEHICLE_TRAINING_LOCATION_ID: "native_task_complete",
    KLEIVER_RACE_LOCATION_ID: "native_task_complete",
    ARTIFACT_RACE_LOCATION_ID: "native_task_complete",
    FIRST_ARMOR_REWARD_LOCATION_ID: "native_reward_intercept",
}
LOCATION_SOURCE_CODES = {location_id: 0 for location_id in LOCATION_TASK_IDS}
LOCATION_SOURCE_CODES[FIRST_ARMOR_REWARD_LOCATION_ID] = 1
LOCATION_NATIVE_NODE_IDS = {location_id: 0 for location_id in LOCATION_TASK_IDS}
LOCATION_NATIVE_NODE_IDS[FIRST_ARMOR_REWARD_LOCATION_ID] = 36
_ACTIVE_LOCATIONS = {record.code: record for record in FIRST_RELEASE_LOCATIONS}


class LocationPacketError(StateCompatibilityError):
    """A server location update is malformed or incompatible with this slot."""


@dataclass(frozen=True, slots=True)
class LocationTransition:
    state: PersistentState
    changed: bool
    checked_added: tuple[int, ...] = ()
    confirmed_added: tuple[int, ...] = ()
    confirmed_removed: tuple[int, ...] = ()
    pending_added: tuple[int, ...] = ()
    pending_removed: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ServerLocationUpdate:
    checked_locations: tuple[int, ...]
    full: bool


def _sorted(values: Iterable[int]) -> tuple[int, ...]:
    return tuple(sorted(set(values)))


def _transition(
    state: PersistentState,
    *,
    checked: Iterable[int],
    confirmed: Iterable[int],
) -> LocationTransition:
    old_checked = set(state.checked_location_bits)
    old_confirmed = set(state.server_confirmed_location_bits)
    old_pending = set(state.pending_location_outbox)
    new_checked = set(checked)
    new_confirmed = set(confirmed)
    if not old_checked <= new_checked:
        raise ValueError("Durable local location checks are monotonic.")
    if not new_confirmed <= new_checked:
        raise ValueError("Server-confirmed checks must also be durable local checks.")
    new_pending = new_checked - new_confirmed
    replacement = replace(
        state,
        checked_location_bits=_sorted(new_checked),
        server_confirmed_location_bits=_sorted(new_confirmed),
        pending_location_outbox=_sorted(new_pending),
    )
    return LocationTransition(
        state=replacement,
        changed=replacement != state,
        checked_added=_sorted(new_checked - old_checked),
        confirmed_added=_sorted(new_confirmed - old_confirmed),
        confirmed_removed=_sorted(old_confirmed - new_confirmed),
        pending_added=_sorted(new_pending - old_pending),
        pending_removed=_sorted(old_pending - new_pending),
    )


def observe_local_location(
    state: PersistentState, location_id: int
) -> LocationTransition:
    """Durably enqueue one local observation without changing server state."""

    if location_id not in LOCATION_TASK_IDS:
        raise ValueError(f"Location {location_id} is not observable in Milestone 10.")
    return _transition(
        state,
        checked=set(state.checked_location_bits) | {location_id},
        confirmed=state.server_confirmed_location_bits,
    )


def reconcile_connected(
    state: PersistentState, checked_locations: Iterable[int]
) -> LocationTransition:
    """Apply a canonical Connected.checked_locations set."""

    server = set(checked_locations)
    return _transition(
        state,
        checked=set(state.checked_location_bits) | server,
        confirmed=server,
    )


def reconcile_room_update(
    state: PersistentState, checked_locations: Iterable[int]
) -> LocationTransition:
    """Apply a partial RoomUpdate.checked_locations delta."""

    server = set(state.server_confirmed_location_bits) | set(checked_locations)
    return _transition(
        state,
        checked=set(state.checked_location_bits) | server,
        confirmed=server,
    )


def diagnostic_batch_id(state: PersistentState) -> str:
    """Return a non-identifying batch ID tied to the committed state revision."""

    payload = f"{state.state_instance_id}:{state.state_revision}".encode("utf-8")
    return f"location-{hashlib.sha256(payload).hexdigest()[:16]}"


def enabled_location_ids(slot_data: Mapping[str, Any]) -> frozenset[int]:
    """Validate the frozen slot contract and return its enabled location IDs."""

    contract = dict(slot_data)
    try:
        validate_slot_data(contract)
    except (TypeError, ValueError) as exc:
        raise LocationPacketError(str(exc)) from exc
    families = contract["enabled_location_families"]
    return frozenset(
        record.code for record in FIRST_RELEASE_LOCATIONS if record.family in families
    )


def _packet_ids(
    packet: Mapping[str, Any], field: str, *, required: bool
) -> tuple[int, ...]:
    if field not in packet:
        if required:
            raise LocationPacketError(f"Server packet is missing `{field}`.")
        return ()
    values = packet[field]
    if not isinstance(values, list):
        raise LocationPacketError(f"Server packet `{field}` must be a list.")
    if any(type(value) is not int for value in values):
        raise LocationPacketError(f"Server packet `{field}` contains a non-integer ID.")
    if len(values) != len(set(values)):
        raise LocationPacketError(f"Server packet `{field}` contains duplicate IDs.")
    return tuple(sorted(values))


def parse_server_location_update(
    packet: Mapping[str, Any],
    *,
    connected: bool,
    slot_data: Mapping[str, Any] | None = None,
) -> ServerLocationUpdate:
    """Validate location IDs before CommonClient mutates its in-memory sets."""

    if not isinstance(packet, Mapping):
        raise LocationPacketError("Server location update must be a mapping.")
    if connected:
        if slot_data is None:
            raise LocationPacketError("Connected packet is missing slot data.")
        enabled = enabled_location_ids(slot_data)
    else:
        if slot_data is None:
            raise LocationPacketError(
                "RoomUpdate arrived before a compatible slot was authenticated."
            )
        enabled = enabled_location_ids(slot_data)

    checked = _packet_ids(packet, "checked_locations", required=connected)
    missing = _packet_ids(packet, "missing_locations", required=connected)
    supplied = set(checked) | set(missing)
    unknown = supplied - set(_ACTIVE_LOCATIONS)
    disabled = supplied - set(enabled)
    if unknown:
        raise LocationPacketError(
            f"Server packet contains unknown or retired Jak 3 locations: {sorted(unknown)}."
        )
    if disabled:
        raise LocationPacketError(
            f"Server packet contains slot-disabled Jak 3 locations: {sorted(disabled)}."
        )
    if connected:
        overlap = set(checked) & set(missing)
        if overlap:
            raise LocationPacketError(
                f"Connected checked/missing locations overlap: {sorted(overlap)}."
            )
        if supplied != set(enabled):
            raise LocationPacketError(
                "Connected location set does not match the authenticated location table."
            )
    return ServerLocationUpdate(checked_locations=checked, full=connected)
