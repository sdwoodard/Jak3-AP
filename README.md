# Jak 3 Archipelago for OpenGOAL

This project lets Jak 3 participate in an Archipelago multiworld through
OpenGOAL. Missions are checks, mission access and equipment can be received as
items, and new items are shown on the Jak 3 HUD.

The current APWorld version is **0.1.0**.

## What you need

Before starting, make sure all of these are true:

- Archipelago 0.6.7 or newer is installed.
- OpenGOAL can already start your legally obtained Jak 3 installation.
- Jak 3 has already been decompiled and rebuilt successfully.
- You can start Jak 3 in **Debug** mode and open its `goalc` compiler window.
- This repository is located at `D:\Codex\Jak3-AP`.

These instructions use the OpenGOAL Launcher path validated during testing:

```text
D:\OpenGOAL\active\jak3\data
```

If your `goalc` errors show a different path ending in `jak3\data`, substitute
that path in the installer command below.

## First-time installation

### 1. Install the Jak 3 APWorld

Open **Archipelago Launcher**, choose **Install APWorld**, and select:

```text
D:\Codex\Jak3-AP\dist\jak3.apworld
```

After installing it, completely close every Archipelago window and reopen
Archipelago Launcher. This restart is required whenever the APWorld is
replaced.

To rebuild the APWorld from this repository before installing it, open
PowerShell and run:

```powershell
cd D:\Codex\Jak3-AP
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_apworld.ps1
```

### 2. Install the bridge into the active OpenGOAL copy

The bridge is the code that runs inside Jak 3. In PowerShell, run:

```powershell
cd D:\Codex\Jak3-AP
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-opengoal-bridge.ps1 -OpenGoalRepository D:\OpenGOAL\active\jak3\data
```

The command should report that it:

- copied `archipelago.gc`; and
- registered `archipelago.o` after `task-control.o`.

The installer is safe to run again after updating this repository. Do not aim
it at a separate decompile/reference folder—the path must be the same active
`data` directory used by the `goalc` instance that runs your game.

### 3. Compile the bridge

Every newly opened Jak 3 `goalc` process must load the project symbols and
types into memory. At its `g>` or `gc>` prompt, type only:

```clojure
(mi)
```

Do not type the displayed prompt itself. Wait until the build reaches 100% and
reports success. This is required again whenever `goalc` itself is closed and
reopened, even when no source files changed. The incremental rebuild is what
restores compiler knowledge of symbols such as `ap-init!`.

After `(mi)` succeeds, do **not** manually run `(lt)` or `(ml ...)`. Start or
keep Jak 3 running in Debug mode and leave this `goalc` window open. `/repl
connect` will issue `(lt)` through nREPL, live-load the bridge, and initialize
it. This matters because the connection that issues `(lt)` owns the target
reply channel; manually attaching first routes replies to the `goalc` console
instead of the Archipelago client.

## Prepare or host a multiworld

For a new seed, copy [Jak3.yaml](Jak3.yaml) into Archipelago's `Players`
folder, change its `name`, and generate normally. The generated
`.archipelago` file is the room file used by Archipelago Server.

For the supplied six-player test room, start **Archipelago Server** and open:

```text
D:\Codex\AP_16266186996945461488\AP_16266186996945461488.archipelago
```

You can also launch that server directly from PowerShell:

```powershell
& "D:\Program Files\Archipelago\ArchipelagoServer.exe" "D:\Codex\AP_16266186996945461488\AP_16266186996945461488.archipelago"
```

Leave the server open. Its local address is usually `localhost:38281`; use the
port printed in the server window if it is different.

## Connect Jak 3 to the room

1. Make sure Jak 3 is running in Debug mode and the `goalc` window that
   successfully ran `(mi)` is still open. Do not manually run `(lt)`.
2. Open **Archipelago Launcher** and start **Jak 3 Client**.
3. Connect it to `localhost:38281`, or the address printed by your server.
4. Enter the exact generated slot name. For the supplied room it is
   `SigmarJak3`.
5. Enter a room password only if the server uses one.
6. In the Jak 3 Client console, enter:

```text
/repl connect
```

The client should report that it connected to nREPL, attached to the game,
loaded the bridge, and bound the slot. It selects a shared state-file path
automatically and replays previously received items safely.

Confirm all three connections before playing:

```text
/repl status
```

It should show the Archipelago server and OpenGOAL nREPL as `connected`, and
the Jak 3 bridge as `ready`. If `goalc` prints `already connected!`, it was
manually attached first; close that client and compiler, open a fresh `goalc`,
run `(mi)`, and let `/repl connect` attach it.

## Start playing

The Debug launch is only a compiler/test scene and is not controllable as a
normal game. After `/repl status` reports `ready`, enter this once in **Jak 3
Client** to perform Jak 3's real New Game initialization:

```text
/game start
```

This loads the normal intro, player controls, HUD, saving, and mission systems.
It starts a fresh in-game playthrough, so do not use it merely to reconnect to
an AP game that is already running. Previously received AP inventory is
automatically replayed after initialization.

Use a dedicated Jak 3 save for each AP slot. On a later session, connect the
same room and slot, wait for bridge readiness, then use:

```text
/game title
```

Load that slot's save through Jak 3's normal menu. Once Jak is playable, run
`/game sync` so the server's received inventory is reapplied after the vanilla
save load. Do **not** use `/game start` when resuming; it is New Game.

Once the intro/gameplay has loaded, list everything currently playable:

```text
/missions
```

The normal New Game intro is the always-available first check, **Watch Intro
Movie**. Let it play normally. If task 6 remains listed after the playable game
has loaded, it can also be dispatched explicitly:

```text
/play 6
```

After receiving more mission and equipment items, run `/missions` again and
start another listed task with `/play <number>`. A unique name fragment also
works, such as:

```text
/play intro
```

A mission is listed only when you have both its mission-unlock item and any
weapon, vehicle, Jetboard, or Light Jak power required by its logic. New server
items wait through loading/title screens and then appear one at a time as
orange notifications on the gameplay HUD. Replayed connection history is
intentionally silent.

## Troubleshooting

### `can't load a file that doesn't exist`

The bridge was installed into a different OpenGOAL tree. Read the full path in
the error and rerun the installer with that active `jak3\data` directory.

### The client reports unknown types or missing helpers while loading the bridge

Run `(mi)` successfully in that same `goalc` session first. A newly opened
compiler has not yet loaded all Jak 3 types and macros.

### `Unrecognized symbol ap-init!` or bridge initialization times out

Close Jak 3 Client and `goalc`. Open a fresh `goalc`, run `(mi)` successfully,
and do not type `(lt)` or `(ml ...)` manually. Keep the Debug game running and
let `/repl connect` perform the attach and live load so nREPL owns the target
reply channel.

### `/repl connect` says connection refused

Keep the correct Jak 3 `goalc` process open, use a Debug launch, and make sure
its nREPL is listening on port 8181.

### `/missions` or `/play` does not respond

These slash commands belong in the **Jak 3 Client** input box, not the `goalc`
window or Archipelago Server window. Run `/repl status`. All commands now print
explicit feedback; if the bridge says `not bound`, connect the Jak 3 Client to
the Archipelago room first and then run `/repl connect` again.

### The Debug game shows an idle character and ignores controls

That scene is only OpenGOAL's Debug attachment target. After the bridge is
ready, run `/game start` in **Jak 3 Client**. Do not use `/play` as the initial
game boot command; mission dispatch assumes the normal game systems already
exist.

### The bridge is not loaded

Open a fresh `goalc`, run `(mi)`, leave the Debug game running, and use `/repl
connect`. It performs the required `(lt)` and `(ml ...)` commands.

### A mission is rejected

Use `/missions`. Having a mission-unlock item is not sufficient if its
equipment requirements have not arrived.

### No item notification is visible

Notifications wait until Jak and the gameplay HUD are active. Replayed items
during initial connection restore inventory without displaying old notices.

## Project layout and implementation notes

- `jak3/` contains the installable APWorld and Python client.
- `opengoal/archipelago/` contains the in-game GOAL bridge.
- `scripts/build_apworld.ps1` builds and validates `dist/jak3.apworld`.
- `scripts/install-opengoal-bridge.ps1` performs the idempotent OpenGOAL install.
- `RUNNING.md` contains a shorter operator-oriented launch reference.

The world provides 66 main mission checks using native task IDs 6-71 and 65
optional challenge checks using task IDs 73-137, for 131 Jak 3 checks total.
Progressive grants are cumulative and idempotent. The client verifies actual
completed checks before reporting the configured goal. Trap messages cross
the protocol, but disruptive in-game trap effects are currently logged while
their Jak 3 actors are validated.

This fan project is not affiliated with Naughty Dog, Sony, OpenGOAL, or
Archipelago.
