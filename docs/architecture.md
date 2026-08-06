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
The client file is authoritative for AP packets, options, reachability inputs,
bridge state, nREPL barriers, and Python exceptions. The OpenGOAL file combines
the two child-process streams and GOAL-side protocol events. Existing OpenGOAL
processes are never restarted merely to capture them; a prominent warning asks
the user to reproduce from a clean process state instead.

## OpenGOAL overlay (`mod/opengoal`)

This directory mirrors the destination path beneath an OpenGOAL Jak 3 data
tree. The GOAL bridge owns native task observation, authoritative item grants,
slot/seed binding, save reconstruction hooks, and safe HUD presentation. It
must never determine reachability; the APWorld remains authoritative for logic.

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

## Protocol invariants

- Native task IDs are transport data, not display names.
- Location and item IDs are append-only after a public release.
- Every received item carries an Archipelago receive index and is safe to
  replay.
- Transient bridge state is bound to the room seed and slot.
- The game reports facts (completed native task/reward/orb threshold); it does
  not decide whether an item placement was legal.
- Save/load reconstruction reapplies AP-owned state after vanilla state has
  loaded; temporary mission bootstrap grants never become permanent inventory.
- HUD messages are queued until gameplay owns the draw pipeline, and replayed
  connection history does not produce old alerts.

## Default implementation boundary

The design-default world contains 147 addressed locations: 61 story task
completions, 38 major reward moments, 24 selected side tasks, and 24 global
25-orb thresholds. Task 72 is a locked Victory event and does not hold a random
item. The current generator/runtime is still the phase-1 protocol slice, so the
phase-2 migration must replace its tables as a unit across APWorld, client,
GOAL bridge, and tests.
