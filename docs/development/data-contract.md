# First-release data and slot-data contract

Milestone 4 froze the design version 0.3 identities, and Milestone 5 activates
those records as the complete 147-location static generator. The authoritative
executable records are in `worlds/jak3/registry.py`; `worlds/jak3/data.py`
remains only as an isolated protocol-1 compatibility input. The published
protocol-1 identities are copied literally into `worlds/jak3/legacy_ids.py`,
so compatibility does not depend on the legacy table continuing to contain
those rows.

## Versions

The shared constants live in `worlds/jak3/versions.py` and are mirrored as
static compatibility constants in the OpenGOAL bridge.

| Field | Version |
| --- | ---: |
| Protocol | 3 |
| Game integration | 2 |
| Slot data | 2 |
| State schema | 1 |
| Item table | 2 |
| Location table | 2 |
| Mission table | 1 |
| Mission profiles | 1 |

Protocol 3 adds the forward-safe runtime snapshot, game-session nonce, and
eight-entry idempotent command receipt ring. Slot-data version 2 adds the
generated `multiworld.seed_name` as the mandatory opaque `seed_identifier`.
State schema version 1 and every table version/hash remain unchanged. Protocol
2 sidecars are incompatible read-only evidence and are not migrated.

## Registry scope

The item registry contains 26 default progression instances, 28 default useful
instances, every documented filler name, and the five future trap names. Trap
pool counts remain zero because the supported default disables traps.

The location registry contains exactly:

- 61 story-completion locations, retaining their matching legacy task IDs;
- 38 major reward locations keyed to audited native node IDs;
- 24 selected side challenges, retaining their matching legacy task IDs; and
- 24 global Precursor Orb thresholds.

Task 36's legacy location ID is retired. Task 72 is the code-less Victory
event. Hidden mission-completion events and Victory use `None`, never network
IDs. Task 88 retains native ID 88 and records both the native enum alias and its
normalized runtime node alias.

Every protocol-1 item and location ID not retained for the exact same concept
appears in a serialized reserved-ID ledger. Reserved IDs are unavailable for
future reuse, including the old per-mission unlock items, prologue/task-36
locations, experimental tasks 73-113, renamed filler, and retired trap
concepts. The frozen compatibility snapshot gives every retained code an
explicit semantic label; registry validation rejects a changed or missing
retained item family/name identity and a changed or missing location
family/task identity.

## Canonical hashing

Tables and resolved options are serialized as JSON with these exact rules:

1. UTF-8 encoding without a byte-order mark.
2. Object keys sorted by Unicode code-point order.
3. Records sorted by their semantic record values before serialization.
4. Separators are `,` and `:` with no insignificant whitespace.
5. JSON literals are lowercase and non-ASCII text is emitted directly.
6. Floating-point values and non-string mapping keys are rejected.
7. One LF byte terminates the payload.
8. The published digest is lowercase SHA-256 of those bytes.

Frozen table hashes:

| Table | SHA-256 |
| --- | --- |
| Item | `eb557676187512253327e2fdcbad2f8f49f62236d019fdd8129f14cb9987f99c` |
| Location | `f1c74c5a9da78e8e2b87a57ae283b514038be521699367342c0a555826333793` |
| Mission/profile | `2e6e631ed650ceb860921e3feb066a85f6d858038a0f46f510a616d17633f09a` |
| Supported resolved options | `facdfa555f7c5804a5c5c0ebaf3db8e6260ba5f409f66e7bc22a1ab128a4c914` |

## Slot-data shape

`worlds/jak3/slot_data.py` is the schema authority. It includes the opaque seed
identifier; protocol, integration, slot/state/table/profile versions; the
three table hashes; the resolved-options hash and runtime-required resolved
values; feature flags; task-72 goal and relic threshold; enabled location
families; orb thresholds; selected/excluded challenge IDs; and trap duration.

Item/location name-to-ID mappings, legacy mission requirement tables, filler
kinds, and equipment command maps are deliberately absent. Archipelago's data
package supplies public names and IDs, while future runtime implementation will
consume the versioned registry directly.

On `Connected`, the Python client validates the complete contract and obtains
team, slot, and canonical slot name from the authenticated packet. The
`RoomInfo.seed_name` value is logged for diagnosis only and never binds state.

## Persistent state shape

`worlds/jak3/persistence.py` is the schema-1 authority. The payload includes
all roadmap compatibility/binding fields, an instance UUID, and a monotonic
revision. Unbound state has null seed/team/slot/name fields; every journal,
explicit location-ID set, outbox, overlay, trap queue, counter, and goal flag
starts empty, zero, or false.

Received items are represented by explicit per-index records whose state is
`received`, `pending`, or `applied`. The fields named `checked_location_bits`
and `server_confirmed_location_bits` contain sorted, unique public location
IDs; they are not declaration-order bit positions.

The canonical payload is wrapped with its SHA-256. Unknown fields, invalid
field relationships, unsupported public IDs, and incompatible contracts are
rejected. Contract scalars and journal containers, records, indices, and count
pairs require their exact declared types before serialization. Schema, format,
version, and binding mismatches are preserved as read-only failures; malformed
or checksum-invalid bytes enter the documented backup/quarantine flow.

`StateSession.status` retains backup recovery when recovery and first binding
occur in the same open operation. `StateSession.binding_performed` reports the
binding as a separate fact, so diagnostics do not have to discard either
event.
