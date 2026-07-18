# Running Jak 3 Archipelago with OpenGOAL

These instructions assume Jak 3 has already been extracted and successfully
rebuilt by OpenGOAL.

## 1. Install the current APWorld

From this repository:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_apworld.ps1
```

Use **Install APWorld** in the Archipelago Launcher to install
`dist\jak3.apworld`, then completely close and reopen Archipelago. Updating the
APWorld does not invalidate an already-generated room when item and location
IDs are unchanged.

## 2. Install and load the OpenGOAL bridge

Point the installer at the OpenGOAL repository used to build Jak 3:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-opengoal-bridge.ps1 -OpenGoalRepository ..\jak-project
```

The path must match the `data` directory shown in `goalc` file errors. For an
OpenGOAL Launcher installation whose compiler resolves files beneath
`D:\OpenGOAL\active\jak3\data`, use:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-opengoal-bridge.ps1 -OpenGoalRepository D:\OpenGOAL\active\jak3\data
```

Whenever a new Jak 3 `goalc` process is opened, run `(mi)` to load the complete
project symbol/type environment and rebuild `GAME.CGO`. This is required per
compiler process even if the source did not change. The installer has placed
`archipelago.o` after `task-control.o`, which is the required load order.

Using the supplied `jak-project` development tree, the corresponding shell
commands are:

```powershell
cd D:\Codex\jak-project
task set-game-jak3
task repl
```

Run `(mi)` at the `goalc` prompt. Launch the Jak 3 debug runtime by the same
method you currently use (`task run-game` is the development-tree command).
Do not manually run `(lt)` or `(ml ...)`: `/repl connect` sends both through
nREPL so that target acknowledgements return to the client. Keep both
processes open.

For an already-running debug game, the same `goalc` session must have run
`(mi)` at least once. Keep it open without manually attaching; `/repl connect`
attaches and loads the bridge. The compiler should print `Jak 3 Archipelago
protocol 1 ready.` Keep the
OpenGOAL compiler open: the Jak 3 client connects to its nREPL on TCP port
8181. A retail/non-debug boot without this compiler connection cannot run the
current bridge.

The bridge must be installed into the same OpenGOAL source/output tree that
produces the game runtime you launch. A normal launcher-only/retail boot is not
enough for this first integration because the AP client needs the debug
compiler's nREPL.

## 3. Host the generated room

Start **Archipelago Server** from the Archipelago Launcher and open the
generated `.archipelago` file. For the supplied generated room, that is:

```text
D:\Codex\AP_16266186996945461488\AP_16266186996945461488.archipelago
```

Keep the server window open and note its listening address. A local server is
normally reached as `localhost:38281`; use the port printed by the server if it
differs.

## 4. Connect Jak 3

1. Start the debug OpenGOAL Jak 3 game and leave the `goalc` session that ran
   `(mi)` open. Do not manually run `(lt)`; the client must issue it through
   nREPL.
2. Start **Jak 3 Client** from the Archipelago Launcher.
3. Connect it to the room address and use the exact slot name `SigmarJak3` for
   the supplied room. Enter the room password only if the server has one.
4. In the Jak 3 Client console, run `/repl connect`.

Run `/repl status` next. Do not continue until it reports the Archipelago
server and OpenGOAL nREPL as connected and the Jak 3 bridge as ready. Slash
commands must be entered in **Jak 3 Client**, not at the `goalc` prompt.

A successful connection reports that the client connected to the Jak 3
OpenGOAL nREPL. It then binds the game to the room and replays already-received
items safely. No manual state-file path is needed.

For a fresh playthrough, run `/game start` once. A Debug launch initially shows
an idle test character; this command performs Jak 3's normal New Game
initialization and enables the real player, controls, HUD, saving, and mission
systems. It resets in-game story state, so do not run it just to reconnect to
an already-running playthrough.

For a later session, use `/game title`, load the dedicated save for this AP
slot in Jak 3's normal menu, and then run `/game sync` after Jak is playable.
That reapplies the server's received inventory in case the vanilla save load
replaced equipment fields.

Use `/missions` to list missions currently allowed by both received unlocks
and equipment logic. The New Game intro is the always-available **Watch Intro
Movie** check. After normal gameplay exists, `/play <task id>` dispatches
another listed mission; `/play 6` can retry the intro if it remains listed. A
unique part of a listed name also works, for example `/play intro`.

## Troubleshooting

- **Connection refused on `/repl connect`:** `goalc` is not running, is not the
  Jak 3 compiler instance, or its nREPL is not listening on port 8181.
- **Bridge is not loaded:** close the client and `goalc`, open a fresh compiler,
  run `(mi)`, and let `/repl connect` attach and load the bridge. Do not issue
  `(lt)` manually first.
- **A mission is rejected:** use `/missions`; possession of a mission-unlock
  item alone is insufficient when that mission also requires a weapon, power,
  vehicle, or Jetboard.
- **No HUD item notice:** notifications wait while Jak or the gameplay HUD is
  unavailable, then display after gameplay resumes. Replayed connection
  history is intentionally silent.
- **Idle character with no controls:** this is the Debug attachment scene. Run
  `/game start` after `/repl status` reports that the bridge is ready.
- **Wrong checks/items after reconnecting:** verify the AP server room and the
  exact slot name. The bridge resets its transient state when the seed/slot
  binding changes.
