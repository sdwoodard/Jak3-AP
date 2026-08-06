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
restart all Archipelago processes after replacing an installed APWorld.

The package contains the launcher icon, Python client, and exact OpenGOAL
bridge source. Starting the client installs or repairs the bridge in the active
Jak 3 project before compilation, including the idempotent `game.gd`
registration.

## Manual bridge recovery

The normal installed-APWorld path does not need a separate bridge step. During
source development, this idempotent tool can apply the checkout's bridge
without rebuilding the package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install_opengoal_bridge.ps1 `
  -OpenGoalRepository D:\OpenGOAL\active\jak3\data
```

It copies `archipelago.gc` to
`goal_src\jak3\pc\features` and registers `archipelago.o` immediately after
`task-control.o` in `goal_src\jak3\dgos\game.gd`. The next normal client launch
will restore the bridge version carried by the installed APWorld.

## Launch path

Start **Jak 3 Client** from Archipelago Launcher. The client mirrors the proven
Jak 1 lifecycle: it launches missing OpenGOAL processes, starts `gk` in debug
mode, connects to `goalc` nREPL, attaches with `(lt)`, recompiles with `(mi)`,
loads the bridge, disables debug/cheat state, and opens `title-restart`.

There is no routine need to type `(mi)`, `(lt)`, or `(ml ...)` manually. The
client console keeps these recovery commands:

- `/diagnostics` writes and flushes a full current logic/protocol snapshot and
  prints the paired client/OpenGOAL log paths.
- `/repl status` reports server, compiler, and bridge state.
- `/repl connect` retries the full compile/connect operation.
- `/game title` reopens the normal title menu.
- `/game start` initializes a fresh game from `intro-start`.
- `/game sync` reapplies authoritative AP inventory after loading a save.

The exact normal retail-style command supplied for local smoke testing is:

```powershell
& "D:\OpenGOAL\versions\official\v0.3.5\gk.exe" -v `
  --proj-path "D:\OpenGOAL\active\jak3\data" --game jak3 -- -boot -fakeiso
```

The client uses the required debug equivalent by adding `-debug` after
`-fakeiso` and also starting the matching `goalc` process. Both commands request
disabled ANSI colors; internal collectors strip remaining control sequences
and append prefixed stdout/stderr to the same session-specific OpenGOAL
diagnostic log. Detailed usage and privacy guidance is in
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
5. Perform an end-to-end debug launch and verify title return, save loading,
   item reconstruction, check delivery, and both sent/received HUD messages.
6. Confirm the session creates exactly one matched Jak3 client/OpenGOAL support
   pair, compiler and bridge events are present, and `/diagnostics` flushes a
   parseable state snapshot.

The checked-in phase-1 world is useful for protocol smoke tests but is not the
design-default acceptance target. Do not publish an installer or call a seed
playable until the 147-location default and the acceptance matrix in the design
document pass.
