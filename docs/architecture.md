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

## OpenGOAL overlay (`mod/opengoal`)

This directory mirrors the destination path beneath an OpenGOAL Jak 3 data
tree. In protocol 2 the GOAL bridge owns only a temporary handshake state,
version/session validation, ping/pong, status export, and protocol logging. It
has no task, item, location, reward, save, mission, or gameplay HUD hooks.

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
against opaque save descriptors. Live GOAL observation of identity and
freshness is deferred to Milestone 7.

## Tools and packaging

`tools/build_apworld.ps1` stages `worlds/jak3` and injects the versioned GOAL
source from `mod/opengoal` as package data. The installed client reads that
resource from either the source tree or APWorld zip, atomically installs it in
the active OpenGOAL project, and idempotently registers its object in `game.gd`.
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
- A new ping `N` returns `N + 1`; duplicate `N` returns the same pong without
  changing logical state.
- Live client readiness requires a fresh pong. A stale file is never enough.
- Communication failure closes the client transport and does not invoke a game
  mutation.
- Protocol 2 has no AP inventory, native mission state, or network-location
  behavior.

## Default implementation boundary

The design-default world contains 147 addressed locations: 61 story task
completions, 38 major reward moments, 24 selected side tasks, and 24 global
25-orb thresholds. Task 72 is a locked Victory event and does not hold a random
item. The active generator consumes the versioned first-release registry and
creates the exact 26 progression, 28 useful, and 93 weighted filler instances.
Its single always-open region and immediately reachable event locations are
explicitly non-playable Milestone 5 scaffolding; Standard reachability remains
Milestone 12 work. The runtime remains handshake-only and does not submit these
locations or apply these items.
