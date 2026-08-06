# Jak 3 Archipelago for OpenGOAL

This repository owns the complete Jak 3 integration boundary: the Archipelago
world and client, the in-game OpenGOAL bridge, development tooling, design
records, and the future installer/release packaging.

The repository is currently an **integration scaffold**, not a playable
release. The original 131-check protocol vertical slice remains available for
incremental testing, while the option schema is now pinned to the documented
first-playable default profile. The next implementation pass replaces that
vertical slice with the design's 147-location default world.

## Repository layout

```text
config/templates/           Supported player YAML and documented WIP values
docs/design/                Versioned progression and logic specification
docs/                       Architecture, source audit, and development guides
installer/                  Release-installer boundary (planned deliverables)
mod/opengoal/               OpenGOAL source overlay owned by this project
tests/                      APWorld and protocol tests
tools/                      Build, install, and source-verification utilities
worlds/jak3/                Installable APWorld package and Jak 3 client
```

Generated archives belong in `dist/` and are ignored by Git.

## Current option policy

[config/templates/Jak3.yaml](config/templates/Jak3.yaml) is the only player
template. Every Jak 3-specific value marked `[SUPPORTED DEFAULT]` is accepted;
the alternatives remain visible but are explicitly labeled as work in
progress. The APWorld rejects a non-default Jak 3 option instead of silently
generating a partially implemented mode. Standard Archipelago placement
controls remain customizable.

The normative target is
[docs/design/progression-and-logic.md](docs/design/progression-and-logic.md).
See [docs/source-audit.md](docs/source-audit.md) for the source checks performed
against OpenGOAL and for the limits of that verification.

## Build and verify

From the repository root in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_source_tables.ps1 -OpenGoalRoot ..\jak-project
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_apworld.ps1
```

The build produces the self-contained `dist\jak3.apworld` and validates its
manifest, launcher icon, client, and bundled OpenGOAL bridge. Install it with
Archipelago Launcher's **Install APWorld** action, then restart the launcher.

Starting **Jak 3 Client** from Archipelago Launcher automatically:

1. discovers the OpenGOAL Launcher installation;
2. installs or repairs the exact bridge bundled in the APWorld and registers it
   in the active Jak 3 project;
3. starts Jak 3 `gk` with `-debug` and starts `goalc` when needed;
4. attaches to the target and runs the Jak 3 recompile;
5. loads and initializes the bridge; and
6. returns the game to the normal title menu so saves and game options remain
   available.

Newly received items and items sent to other players are queued as messages at
the bottom of the gameplay screen. Connection-history replay is intentionally
silent.

Every launch also creates a matched `Jak3Client_<session>.txt` and
`Jak3OpenGOAL_<session>.txt` support pair. The latter combines game and compiler
output, while `/diagnostics` records the current item/check/logic state and
prints both paths. See [docs/troubleshooting.md](docs/troubleshooting.md) before
reporting an issue.

Development details are in [docs/development.md](docs/development.md). The
setup guide packaged with the
APWorld is [worlds/jak3/docs/setup_en.md](worlds/jak3/docs/setup_en.md).

## Tagged releases

Pushing a tag such as `v0.1.0` runs
[the release workflow](.github/workflows/release.yml). The workflow requires
the tag to match `worlds/jak3/archipelago.json`'s `world_version`, builds the
self-contained APWorld on a Windows runner, writes a SHA-256 checksum, and
creates or updates the matching GitHub release. No OpenGOAL binaries or game
data are included.

This fan project is not affiliated with Naughty Dog, Sony, OpenGOAL, or
Archipelago.
