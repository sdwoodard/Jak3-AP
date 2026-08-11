# Development and integration workflow

## Prerequisites

- Archipelago 0.6.7 or newer.
- A legally obtained Jak 3 image successfully decompiled by OpenGOAL.
- An OpenGOAL Launcher Jak 3 installation with both `gk` and `goalc`.
- PowerShell 5.1 or newer for the repository tools.

The client reads OpenGOAL Launcher v2 or v3 settings. For an unusual or
portable installation, set both `JAK3_OPENGOAL_BIN` and
`JAK3_OPENGOAL_PROJECT`. The latter must be the active Jak 3 `data` directory
containing `goal_src` and `iso_data\jak3`.

## Build the APWorld

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_apworld.ps1
```

The result is `dist\jak3.apworld`. Install it through Archipelago Launcher and
follow the update/restart policy below after replacing an installed APWorld.

The package contains the launcher icon, Python client, and the explicit
`bridge-modules.json` source set. Starting the client validates and repairs the
complete set before compilation, including deterministic `game.gd` ordering.

## Manual bridge recovery

The normal installed-APWorld path does not need a separate bridge step. During
source development, this idempotent tool can apply the checkout's bridge
without rebuilding the package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install_opengoal_bridge.ps1 `
  -OpenGoalRepository D:\OpenGOAL\active\jak3\data
```

It copies the manifest-declared startup, control, and diagnostics sources plus
the manifest itself. It registers `archipelago.o` then
`archipelago-diagnostics.o` immediately after `task-control.o`. The next normal
client launch restores the exact source set carried by the installed APWorld.

## Supported update and restart policy

Before installing a changed APWorld or bridge, let native save/load finish,
then close the Jak 3 client, `gk`, and `goalc`. Install through Archipelago
Launcher and perform a clean game restart. Do not delete the durable
pending-reload marker: the compatible activation handshake clears it after the
installed source actually runs.

Manual `(ml)` is developer/recovery-only and unsupported during memory-card
I/O. It is not a player-facing hot-update workflow.

Official OpenGOAL v0.3.5 cannot reconnect a replacement compiler after the
original compiler connection is lost. The sole supported first-release
recovery path after clean or unclean client/compiler loss is to finish native
memory-card I/O and restart the client, `gk`, and `goalc` together. Warm
replacement attachment to an existing `gk` is unsupported. See
`docs/development/milestone-7.2-acceptance.md`.

Do not lock, replace, or edit OpenGOAL's native save-bank files from an external
program while the game is running. That is unsupported upstream interference,
not a bridge recovery workflow.

## Launch path

Start **Jak 3 Client** from Archipelago Launcher. The client mirrors the proven
Jak 1 lifecycle: it launches missing OpenGOAL processes, starts `gk` in debug
mode, connects to `goalc` nREPL, attaches with `(lt)`, recompiles with `(mi)`,
loads the bridge, disables debug/cheat state, verifies protocol 3/game
integration 2, and exchanges a harmless runtime heartbeat.

There is no routine need to type `(mi)`, `(lt)`, or `(ml ...)` manually. The
client console keeps these recovery commands:

- `/diagnostics` writes and flushes the current handshake snapshot and
  prints the paired client/OpenGOAL log and structured timeline paths.
- `/diagnostics export` builds a local sanitized, checksummed support ZIP off
  the heartbeat loop and falls back to temporary storage on archive I/O failure.
- `/repl status` reports server, compiler, game, source, versions, session,
  heartbeat, and last command/result state.
- `/repl connect` retries the full compile/connect operation.

The exact normal retail-style command supplied for local smoke testing is:

```powershell
& "D:\OpenGOAL\versions\official\v0.3.5\gk.exe" -v `
  --proj-path "D:\OpenGOAL\active\jak3\data" --game jak3 -- -boot -fakeiso
```

The client uses the required debug equivalent by adding `-debug` after
`-fakeiso` and also starting the matching `goalc` process. Both commands request
disabled ANSI colors; internal collectors drain bounded pipes, strip remaining
control sequences, and append prefixed stdout/stderr to the same
session-specific OpenGOAL diagnostic log without a raw spool. Detailed usage and privacy guidance is in
`docs/troubleshooting.md`.

## Release packages

Tags named `vMAJOR.MINOR.PATCH` run `.github/workflows/release.yml`. The version
without the leading `v` must equal the manifest's `world_version`. The workflow
builds `jak3.apworld`, emits its SHA-256 checksum, and publishes both files on
the GitHub release. Rerunning a tag replaces the two release assets.

## Source-derived table audit

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_source_tables.ps1 `
  -OpenGoalRoot ..\jak-project
```

The verifier checks task IDs and aliases, close-task coverage, reward-node
classification, selected side-task parents, and documented milestone node
names. It deliberately does not claim that every movement or combat predicate
is statically provable; those require runtime acceptance tests.

## Test layers

1. Run `verify_source_tables.ps1` whenever task/reward tables or the design
   document change.
2. Run the Python test suite from an Archipelago source checkout containing
   this package as `worlds\jak3`.
3. Build and inspect `dist\jak3.apworld`.
4. Compile the GOAL overlay against the active Jak 3 project.
5. Perform the client-first, game-first, both-restart, mismatch, duplicate-ping,
   and communication-loss protocol scenarios. Record a real `N -> N + 1` pong.
6. Confirm the session creates the matched human logs plus one JSONL timeline,
   compiler/bridge events are present, and `/diagnostics export` creates a
   validated sanitized bundle.
7. For Protocol 3 release evidence, run the native-save matrix and performance
   gates recorded in `docs/development/milestone-7.2-acceptance.md`. The
   accepted v0.3.5 matrix uses full-process recovery after client/compiler loss
   and excludes external native-bank interference.

The checked-in generator now creates the exact versioned 147-location static
pool. Its regions and events are deliberately always reachable until Milestone
12 supplies Standard logic, and protocol 3 still does not drive gameplay. Do
not publish an installer or call a seed playable until the remaining generator
and gameplay milestones pass.
