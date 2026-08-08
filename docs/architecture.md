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
archipelago-items.gc / archipelago-locations.gc / archipelago.gc
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
test target, and metadata-only native save/load wrappers for tag 900. It has no
item delivery, location submission, reward interception, goal reporting,
mission mutation, or gameplay HUD hooks.

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

The current single-source pipeline must become manifest-driven when Milestone
7.1 introduces the first additional bridge module. Use one explicit versioned
manifest, recommended at `mod/opengoal/bridge-modules.json`, containing each
source, object name, role, and deterministic load order. The build script,
standalone installer, installed-client repair path, object registration, and
compatibility hashing must consume that same manifest. Wildcard discovery is
not permitted. The bridge compatibility hash covers the canonical ordered
source set rather than only `archipelago.gc`. Installation and repair are
atomic for the complete declared module set.

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
- A game-session nonce survives client reconnects and changes on bridge/game
  restart. Mutating command IDs are nonnegative and monotonic per nonce.
- AP-state acknowledgement is authority for one exact native save UUID and
  slot. Stale loaded/bound bits never transfer across a save switch, and every
  mutating command refreshes that acknowledgement before its safety check.
- The last eight receipts provide reconnect discovery. Exact duplicates return
  the stored result; conflicts and older evicted IDs are rejected.
- Live client readiness requires a fresh pong. A stale file is never enough.
- Communication failure closes the client transport and does not invoke a game
  mutation.
- Protocol 3 has no AP inventory, native mission state, or network-location
  behavior.

## Default implementation boundary

The design-default world contains 147 addressed locations: 61 story task
completions, 38 major reward moments, 24 selected side tasks, and 24 global
25-orb thresholds. Task 72 is a locked Victory event and does not hold a random
item. The active generator consumes the versioned first-release registry and
creates the exact 26 progression, 28 useful, and 93 weighted filler instances.
Its single always-open region and immediately reachable event locations are
explicitly non-playable Milestone 5 scaffolding; Standard reachability remains
Milestone 12 work. The runtime observes safety and save identity but does not
submit these locations or apply these items.
