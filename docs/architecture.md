# Architecture

The project is split at boundaries that can evolve independently while sharing
stable network identifiers.

## APWorld (`worlds/jak3`)

The APWorld owns item/location tables, player-option validation, region and
access rules, item-pool construction, slot data, the Archipelago launcher
component, and the Python client. `options_schema.py` is the stable public
option contract; compatibility shims belong in `options.py` rather than in the
schema.

Client process discovery and protocol mechanics live under `agents/`. They are
kept separate from Archipelago room behavior so path discovery, nREPL framing,
and launch commands can be tested without a server.

`agents/diagnostics.py` assigns one session ID to a client/OpenGOAL log pair.
The client file records AP connection metadata, bridge state, nREPL barriers,
heartbeats, and Python exceptions. The OpenGOAL file combines the two
child-process streams and GOAL-side protocol events. Existing OpenGOAL
processes are never restarted merely to capture them; a prominent warning asks
the user to reproduce from a clean process state instead.

### Diagnostic ownership and placement

`worlds/jak3/agents/diagnostics.py` is the authoritative support-facing logger.
Milestone 7.1 extends that existing module rather than creating a competing
logger. It owns the human-readable client log, the Python-owned structured
JSONL event stream, ordering, rotation/retention, redaction, and support-bundle
export. Persistence and protocol code receive a small injectable event sink so
they remain independently testable.

GOAL-side code does not write those support files. A sibling
`archipelago-diagnostics.gc` module may own a bounded, sequence-numbered event
ring and an `ap-diagnostic-emit!`-style API. Python drains that ring and writes
the authoritative event stream. A normal event path is therefore:

```text
archipelago-items.gc / archipelago-locations.gc / archipelago-rewards.gc / archipelago.gc
    -> archipelago-diagnostics.gc bounded event ring
    -> Python protocol drain
    -> worlds/jak3/agents/diagnostics.py
    -> human logs, structured JSONL, and sanitized support bundle
```

`archipelago.gc` may expose a narrow optional diagnostic-sink registration or
dispatch hook, but event storage, retention, redaction, and bundle creation do
not belong in the control plane.

## OpenGOAL overlay (`mod/opengoal`)

This directory mirrors the destination path beneath an OpenGOAL Jak 3 data
tree. In protocol 3 the GOAL bridge owns a temporary runtime snapshot,
version/session validation, an eight-entry command receipt ring, one harmless
test target, descriptor-qualified permanent-item dispatch, and metadata-only
native save/load wrappers for tag 900. `archipelago-items.gc` reconstructs only
the Milestone 8 Jetboard, Blaster stage-1, and Armor stage-1 native targets and
exposes their actual three-bit native state through the control snapshot.
Python compares that readback with the bound ledger on every heartbeat, so an
event-free native task-mask rebuild is repaired at the next safe opportunity.
`archipelago-locations.gc` observes persistent completion for tasks 10–16 and
task-16 reward node 36, then publishes them to the Python-owned persistent
outbox. `archipelago-rewards.gc` wraps only method 13 for that exact two-command
reward, preserving Jak C while suppressing Armor 1 in bound AP mode. The
control snapshot requires separate items-, locations-, and reward-module
activation bits. Each remains false until its ordered source has installed all
of its hooks (and, for rewards, the method wrapper); Python will not bind or
clear a reload obligation without the complete three-module proof. The
overlay has no consumable delivery, other location/reward observation,
ordinary task-72 goal reporting, mission mutation, or gameplay HUD hooks.

### OpenGOAL gameplay-module boundaries

`archipelago.gc` remains the stable control plane created by Milestone 7. It
owns runtime observation, native-save identity and binding acknowledgement,
protocol compatibility, session management, command validation and
deduplication, shared safety state, and command dispatch.

Gameplay-domain code is implemented in sibling modules rather than growing the
control plane into one monolithic source file. The expected first-release
boundaries are:

```text
mod/opengoal/goal_src/jak3/pc/features/
├── archipelago.gc
├── archipelago-diagnostics.gc
├── archipelago-items.gc
├── archipelago-consumables.gc
├── archipelago-locations.gc
├── archipelago-rewards.gc
├── archipelago-overlays.gc
├── archipelago-missions.gc
├── archipelago-story-state.gc
└── archipelago-startup.gc
```

| Module | Responsibility |
| --- | --- |
| `archipelago.gc` | Protocol control plane, runtime observation, save identity/binding, session state, compatibility checks, command dispatch |
| `archipelago-diagnostics.gc` | Bounded GOAL-side event production and sequence/gap reporting; no authoritative file output |
| `archipelago-items.gc` | Permanent native item target-state application and AP-ledger reconciliation |
| `archipelago-consumables.gc` | Additive filler/consumable application and durable-application receipt integration |
| `archipelago-locations.gc` | Native accomplishment observation and publication to Python-owned persistent location state |
| `archipelago-rewards.gc` | Native reward interception, permanent-grant suppression, and AP-item recursion guards |
| `archipelago-overlays.gc` | Temporary lesson and mission-equipment overlays with idempotent cleanup |
| `archipelago-missions.gc` | Route authorizations, mission-board access, mission initialization, and bootstrap orchestration |
| `archipelago-story-state.gc` | Non-counting shadow native story state used by simplified authorization mode |
| `archipelago-startup.gc` | Existing startup/pre-build presentation behavior |

Python remains the authoritative persistent writer. Splitting the OpenGOAL
source does not transfer AP-ledger, checked-location, or sidecar authority into
the game process. Domain modules may use shared types, safety state, dispatch,
and diagnostics interfaces from the control plane, but circular gameplay-module
dependencies are not permitted.

The module list is an ownership plan, not a requirement to create empty files.
A module is introduced by the first milestone that needs it. Completed
Milestone 7 code is not proactively refactored solely to satisfy this layout.

## Persistent AP state

[ADR-001](development/ADR-001-python-owned-ap-state.md) makes the Python Jak 3
client the sole persistent writer. State is selected by a SHA-256 digest of an
opaque native-save identity and stored under the platform user-data path
`Archipelago/Jak3/state-v1` (or the explicit `JAK3_AP_STATE_DIR` override).
The root is protected by one nonblocking operating-system writer lock.

The temporary GOAL snapshot and persistent sidecar are separate channels.
GOAL never writes the sidecar. This lets a later bridge retain game-side
progress while the AP server is offline, provided the Python client remains
running to commit acknowledgements. Playing AP content with the client closed
is unsupported for the first release.

Schema-1 writes use a checksummed canonical JSON envelope, same-directory
temporary file, file flush/`fsync`, atomic backup refresh from the last valid
primary, and atomic primary replacement. Corrupt primaries are quarantined
only after a compatible backup has been validated; compatibility and binding
mismatches never trigger rollback or mutation. Milestone 6 tests this engine
against opaque save descriptors. Milestone 7 supplies live identity, slot, and
monotonic freshness observation and opens/switches this repository only after
authenticated slot data is available.

## Tools and packaging

`tools/build_apworld.ps1` stages `worlds/jak3` and injects the versioned GOAL
source from `mod/opengoal` as package data. The installed client reads those
resources from either the source tree or APWorld zip and installs them into the
active OpenGOAL project.

The bridge lifecycle is manifest-driven through the explicit versioned
`mod/opengoal/bridge-modules.json` module list introduced by Milestone 7.1. The
build script, standalone installer, installed-client repair path, object
registration, compile/load order, activation verification, and compatibility
hashing consume that same manifest. Wildcard discovery is not permitted. The
bridge compatibility hash covers the canonical ordered source set rather than
only `archipelago.gc`, and installation/repair is atomic for the complete
declared module set.

The standalone install tool remains useful while developing the GOAL source.
`installer/` is reserved for any future experience beyond Archipelago's native
APWorld installer, such as repair/uninstall UI or prerequisite validation.

`tools/verify_source_tables.ps1` is an independent source audit. Keeping the
audit outside generator code avoids turning decompiler paths into runtime
dependencies.

## Active protocol invariants

- Protocol version and game-integration version are independent compatibility
  fields.
- A complete snapshot has matching begin/end revisions.
- nREPL acknowledgement is only a command barrier; readiness requires the
  expected snapshot result.
- A game-session nonce is defined to survive unchanged-source client reconnects
  and change on bridge/game restart. Official OpenGOAL v0.3.5 did not pass the
  replacement-compiler lifecycle in Milestone 7.2, so the safe operational
  fallback currently restarts client, game, and compiler together. Mutating
  command IDs remain nonnegative and monotonic per nonce.
- AP-state acknowledgement is authority for one exact native save UUID and
  slot. Stale loaded/bound bits never transfer across a save switch, and every
  mutating command refreshes that acknowledgement before its safety check.
- The last eight receipts provide reconnect discovery. Exact duplicates return
  the stored result; conflicts and older evicted IDs are rejected.
- Live client readiness requires a fresh pong. A stale file is never enough.
- Communication failure closes the client transport and does not invoke a game
  mutation.
- Protocol 3 meanings remain frozen; implementation-only runtime revisions add
  narrow sibling-module hooks. AP inventory remains distinct from native state,
  and location confirmation comes only from server checked-location state.

## Default implementation boundary

The design-default world contains 147 addressed locations: 61 story task
completions, 38 major reward moments, 24 selected side tasks, and 24 global
25-orb thresholds. Task 72 is a locked Victory event and does not hold a random
item. The active generator consumes the versioned first-release registry and
creates the exact 26 progression, 28 useful, and 93 weighted filler instances.
Its single always-open region and immediately reachable event locations are
explicitly non-playable Milestone 5 scaffolding; Standard reachability remains
later work. The runtime applies only the Milestone 8 three-item slice and
submits the eight Milestone 10 location IDs; the rest of the generated pool has
no runtime hooks. A development environment gate can report a temporary
task-16 goal without changing generated slot data or the canonical task-72
event.


## Collectible-sanity ownership and data flow

The default-only beta uses **global locally earned Precursor Orb thresholds**.
It does not expose regional or individual orb locations, and Skull Gem sanity
remains off. A source catalog is nevertheless required before Milestone 13 so
the generator can prove how much local orb value is reachable in each logical
state rather than treating every threshold as automatically reachable.

### Authoritative boundaries

- The APWorld owns the versioned collectible-source catalog, stable network
  location records, logical region assignment, access rules, option validation,
  placement classification, and dynamic filler count.
- `archipelago-locations.gc` observes finite native source completion and
  local-native currency changes. It does not apply AP-delivered currency and it
  does not own the Python sidecar.
- `archipelago-consumables.gc` applies AP-delivered Orb/Gem Packs through the
  exactly-once receipt boundary. Those effects are always tagged
  `ap_delivered` and cannot advance local-earned or source-completion state.
- Python remains the sole persistent writer for monotonic local-earned totals,
  completed collectible-source/location bits, pending outbox entries, and
  server-confirmed locations.
- The diagnostics subsystem may carry bounded, allowlisted collectible events,
  but diagnostic output is never the durability boundary.

### Audit pipeline before public locations

Milestone 12 creates a deterministic **candidate source catalog** and a
runtime verification report. Candidate entries are development evidence, not
public network locations. Each entry records at least:

```text
source_id_candidate
source_family
native_level
logical_region
native_actor_or_reward_kind
resource_or_persistent_key
value
respawn_class
save_persistence
availability_parent
access_requirements
source_evidence
runtime_verification
```

Stable identity must be source-derived. Coordinates are useful diagnostic
metadata but cannot be the identity. Actor addresses and spawn order are never
stable identity.

A container that awards multiple orbs is one finite source with `value = 2` or
`value = 3` unless the engine exposes a separate persistent bit for each unit.
Therefore `individual_static` means one location per audited finite source; it
is not promised to create exactly 600 network locations.

### Logic and generation

For global thresholds, Milestone 13 derives a conservative function equivalent
to:

```text
reachable_local_orb_value(state)
```

It sums only audited, one-time local-native source values and one-time native
mission/challenge rewards whose locations are reachable in that state. AP Orb
Packs are never included.

Future regional/individual modes use the same catalog. Enabling one of those
modes changes the generated location table and therefore requires an explicit
location-table version/hash, deterministic slot-data representation, stable ID
reservation, and persistence compatibility or migration decision.

The mandatory progression/useful item pool does not grow merely because more
collectible checks are enabled. The generator adds enough filler/traps to equal
the enabled unfilled location count. To avoid turning hundreds of optional
pickup checks into a progression hunt, the first supported individual mode
places those locations as `EXCLUDED` under the safe policy until a separate
placement audit deliberately permits progression.

### Skull Gem boundary

Repeatable Metal Head drops are not individual locations. Future cumulative
Skull Gem milestones require both a finite milestone cap and a progression cap;
`skull_gem_bundle_size` alone does not define a finite location set because the
resource is farmable. Secret purchases are the preferred first Skull Gem
expansion because their first-time persistent states are finite. Individual
static Skull Gem locations remain conditional on Milestone 12 proving a
source-audited set of non-respawning, independently persistent entities.
