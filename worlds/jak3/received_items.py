"""Milestone 8 indexed receipt ledger and permanent-item target derivation.

This module is deliberately independent from the OpenGOAL transport.  Packet
validation and every journal transition are pure, so the client can validate a
complete packet before committing any part of it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, cast

from .persistence import (
    NETWORK_ID_ABSOLUTE_LIMIT,
    GameCommandReceipt,
    PersistentState,
    ReceivedItemJournalEntry,
    ReceivedItemState,
)
from .registry import FIRST_RELEASE_ITEMS


JETBOARD_ITEM_ID = 743_000_108
BLASTER_ITEM_ID = 743_010_014
PROGRESSIVE_ARMOR_ITEM_ID = 743_000_116

JETBOARD_TARGET_BIT = 1 << 0
BLASTER_TARGET_BIT = 1 << 1
ARMOR_STAGE_ONE_TARGET_BIT = 1 << 2
PERMANENT_ITEM_TARGET_MASK = (
    JETBOARD_TARGET_BIT | BLASTER_TARGET_BIT | ARMOR_STAGE_ONE_TARGET_BIT
)

MILESTONE_8_ITEM_IDS = frozenset(
    (JETBOARD_ITEM_ID, BLASTER_ITEM_ID, PROGRESSIVE_ARMOR_ITEM_ID)
)
_KNOWN_ITEM_NAMES = {record.code: record.name for record in FIRST_RELEASE_ITEMS}


def known_jak3_item_name(item_id: int) -> str | None:
    """Return a stable public name for a known first-release item ID."""

    return _KNOWN_ITEM_NAMES.get(item_id)


class ReceivedItemsPacketError(ValueError):
    """A ReceivedItems packet is not valid for the Milestone 8 slice."""

    def __init__(
        self,
        reason: str,
        *,
        item_id: int | None = None,
        item_index: int | None = None,
        location_id: int | None = None,
        source_player: int | None = None,
        flags: int | None = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.item_id = item_id
        self.item_index = item_index
        self.location_id = location_id
        self.source_player = source_player
        self.flags = flags


@dataclass(frozen=True, slots=True)
class ReceivedItemsPacket:
    index: int
    entries: tuple[ReceivedItemJournalEntry, ...]

    @property
    def end_index(self) -> int:
        return self.index + len(self.entries)


class PacketOutcome(str, Enum):
    ACCEPTED = "accepted"
    REPLACED = "replaced"
    DUPLICATE = "duplicate"
    GAP = "gap"
    CONFLICT = "conflict"
    PARTIAL_OVERLAP = "partial_overlap"


@dataclass(frozen=True, slots=True)
class PacketTransition:
    outcome: PacketOutcome
    state: PersistentState
    changed: bool
    history_discrepancies: tuple[int, ...] = ()


def parse_received_items_packet(args: Mapping[str, Any]) -> ReceivedItemsPacket:
    """Validate an entire ReceivedItems packet without mutating state."""

    if not isinstance(args, Mapping):
        raise ReceivedItemsPacketError("packet_not_mapping")
    index = args.get("index")
    raw_items = args.get("items")
    if type(index) is not int or index < 0 or index > NETWORK_ID_ABSOLUTE_LIMIT:
        raise ReceivedItemsPacketError("invalid_index")
    if not isinstance(raw_items, (list, tuple)):
        raise ReceivedItemsPacketError("items_not_sequence")

    entries: list[ReceivedItemJournalEntry] = []
    if index + len(raw_items) > NETWORK_ID_ABSOLUTE_LIMIT:
        raise ReceivedItemsPacketError("index_range_overflow")
    for offset, raw in enumerate(raw_items):
        item_index = index + offset
        values = _network_item_values(raw)
        if values is None:
            raise ReceivedItemsPacketError("malformed_entry", item_index=item_index)
        item_id, location_id, source_player, flags = values
        for value in values:
            if type(value) is not int or abs(value) > NETWORK_ID_ABSOLUTE_LIMIT:
                raise ReceivedItemsPacketError(
                    "malformed_entry",
                    item_id=item_id if type(item_id) is int else None,
                    item_index=item_index,
                    location_id=location_id if type(location_id) is int else None,
                    source_player=(
                        source_player if type(source_player) is int else None
                    ),
                    flags=flags if type(flags) is int else None,
                )
        item_id = cast(int, item_id)
        location_id = cast(int, location_id)
        source_player = cast(int, source_player)
        flags = cast(int, flags)
        if source_player < 0 or flags < 0:
            raise ReceivedItemsPacketError(
                "malformed_entry",
                item_id=item_id,
                item_index=item_index,
                location_id=location_id,
                source_player=source_player,
                flags=flags,
            )
        if item_id not in _KNOWN_ITEM_NAMES:
            raise ReceivedItemsPacketError(
                "unknown_item_id",
                item_id=item_id,
                item_index=item_index,
                location_id=location_id,
                source_player=source_player,
                flags=flags,
            )
        if item_id not in MILESTONE_8_ITEM_IDS:
            raise ReceivedItemsPacketError(
                "item_outside_milestone_8",
                item_id=item_id,
                item_index=item_index,
                location_id=location_id,
                source_player=source_player,
                flags=flags,
            )
        entries.append(
            ReceivedItemJournalEntry(
                index=item_index,
                item_id=item_id,
                location_id=location_id,
                source_player=source_player,
                flags=flags,
                state=ReceivedItemState.PENDING,
            )
        )
    return ReceivedItemsPacket(index=index, entries=tuple(entries))


def apply_received_items_packet(
    state: PersistentState, packet: ReceivedItemsPacket
) -> PacketTransition:
    """Apply AP index semantics to an already validated packet."""

    if packet.index == 0:
        if len(packet.entries) == len(state.received_item_journal) and all(
            _same_packet_identity(old, new)
            for old, new in zip(
                state.received_item_journal, packet.entries, strict=True
            )
        ):
            return PacketTransition(PacketOutcome.DUPLICATE, state, changed=False)
        return _replace_canonical_history(state, packet)

    expected = state.next_received_item_index
    if packet.index == expected:
        journal = state.received_item_journal + packet.entries
        updated = _with_received_item_journal(state, journal)
        return PacketTransition(
            PacketOutcome.ACCEPTED, updated, changed=updated != state
        )

    if packet.index > expected:
        return PacketTransition(PacketOutcome.GAP, state, changed=False)

    if packet.end_index > expected:
        return PacketTransition(PacketOutcome.PARTIAL_OVERLAP, state, changed=False)

    historical = state.received_item_journal[packet.index : packet.end_index]
    if len(historical) == len(packet.entries) and all(
        _same_packet_identity(old, new)
        for old, new in zip(historical, packet.entries, strict=True)
    ):
        return PacketTransition(PacketOutcome.DUPLICATE, state, changed=False)
    return PacketTransition(PacketOutcome.CONFLICT, state, changed=False)


def permanent_item_target_mask(state: PersistentState) -> int:
    """Derive the capped native target from the authoritative receipt counts."""

    counts = dict(state.received_item_counts)
    mask = 0
    if counts.get(JETBOARD_ITEM_ID, 0) > 0:
        mask |= JETBOARD_TARGET_BIT
    if counts.get(BLASTER_ITEM_ID, 0) > 0:
        mask |= BLASTER_TARGET_BIT
    if counts.get(PROGRESSIVE_ARMOR_ITEM_ID, 0) > 0:
        mask |= ARMOR_STAGE_ONE_TARGET_BIT
    return mask


def mark_pending_items_applied(
    state: PersistentState, receipt: GameCommandReceipt
) -> PersistentState:
    """Durably observe a successful aggregate native reconciliation."""

    journal = tuple(
        replace(entry, state=ReceivedItemState.APPLIED)
        if entry.state is ReceivedItemState.PENDING
        else entry
        for entry in state.received_item_journal
    )
    return replace(
        state,
        received_item_journal=journal,
        pending_item_application_indices=(),
        last_observed_game_command_receipt=receipt,
    )


def _replace_canonical_history(
    state: PersistentState, packet: ReceivedItemsPacket
) -> PacketTransition:
    old = state.received_item_journal
    discrepancies: list[int] = []
    rebuilt: list[ReceivedItemJournalEntry] = []
    for entry in packet.entries:
        previous = old[entry.index] if entry.index < len(old) else None
        if previous is not None and previous.item_id == entry.item_id:
            rebuilt.append(replace(entry, state=previous.state))
        else:
            rebuilt.append(entry)
            if previous is not None:
                discrepancies.append(entry.index)
    if len(old) != len(packet.entries):
        discrepancies.extend(
            range(
                min(len(old), len(packet.entries)), max(len(old), len(packet.entries))
            )
        )
    updated = _with_received_item_journal(state, tuple(rebuilt))
    return PacketTransition(
        PacketOutcome.REPLACED,
        updated,
        changed=updated != state,
        history_discrepancies=tuple(dict.fromkeys(discrepancies)),
    )


def _with_received_item_journal(
    state: PersistentState, journal: tuple[ReceivedItemJournalEntry, ...]
) -> PersistentState:
    counts = Counter(entry.item_id for entry in journal)
    pending = tuple(
        entry.index for entry in journal if entry.state is ReceivedItemState.PENDING
    )
    return replace(
        state,
        next_received_item_index=len(journal),
        received_item_journal=journal,
        received_item_counts=tuple(sorted(counts.items())),
        pending_item_application_indices=pending,
    )


def _same_packet_identity(
    historical: ReceivedItemJournalEntry, incoming: ReceivedItemJournalEntry
) -> bool:
    return (
        historical.index,
        historical.item_id,
        historical.location_id,
        historical.source_player,
        historical.flags,
    ) == (
        incoming.index,
        incoming.item_id,
        incoming.location_id,
        incoming.source_player,
        incoming.flags,
    )


def _network_item_values(raw: object) -> tuple[object, object, object, object] | None:
    if all(hasattr(raw, field) for field in ("item", "location", "player", "flags")):
        return (
            getattr(raw, "item"),
            getattr(raw, "location"),
            getattr(raw, "player"),
            getattr(raw, "flags"),
        )
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        if len(raw) == 3:
            return raw[0], raw[1], raw[2], 0
        if len(raw) == 4:
            return raw[0], raw[1], raw[2], raw[3]
    return None
