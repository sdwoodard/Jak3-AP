# Jak 3 Multiworld Setup Guide

## Requirements

- Archipelago 0.6.7 or newer.
- A legally obtained Jak 3 disc image extracted and rebuilt by OpenGOAL.
- A debug OpenGOAL Jak 3 launch with the `goalc` nREPL available on port 8181.

## Install

1. Build `jak3.apworld` with `scripts/build_apworld.ps1`, install it through
   Archipelago's **Install APWorld** action, and completely restart
   Archipelago.
2. Run `scripts/install-opengoal-bridge.ps1 -OpenGoalRepository <path>` to copy
   the bridge into the OpenGOAL source tree and register it after
   `task-control.o`.
3. Every newly opened Jak 3 `goalc` process must run `(mi)` successfully to
   load the project symbols and types. Start the Debug game and keep `goalc`
   open, but do not manually run `(lt)` or `(ml ...)`. `/repl connect` sends
   both through nREPL so replies return to the client.
4. Host the generated `.archipelago` file and start **Jak 3 Client** from the
   Archipelago Launcher.
5. Connect the client to the room with the exact generated slot name, then run
   `/repl connect` in the Jak 3 Client console.
6. Run `/repl status` and confirm the server and nREPL are connected and the
   bridge is ready.
7. Run `/game start` once to leave the uncontrollable Debug test scene and
   initialize a normal fresh Jak 3 game.
8. Let the intro play, then use `/missions` to see logically playable task IDs
   and `/play <task id>` to launch a listed mission when needed.

For later sessions, use `/game title`, load the dedicated save for this AP
slot, then run `/game sync` once gameplay has loaded. `/game start` always
creates a new in-game playthrough.

The Python client and GOAL bridge negotiate an absolute shared-state path, so
their working directories do not need to match. Received item indices and
completed tasks are bound to hashes of the room seed and slot, making
reconnection and item replay idempotent.

Gun families, ammo capacity, Dark/Light Jak powers, and armor are progressive
in-game upgrades. The Jetboard and five story Wasteland vehicles are one-time
power items. A mission appears in `/missions` only when its mission unlock and
all equipment in its Archipelago access rule have been received. Optional
challenges unlock gradually with mission-item count.

New server receipts wait through titles and loading screens and display one at
a time on the gameplay HUD. Historical items replayed during connection
restore inventory silently.

## Goal behavior

The AP client reports goal completion only after the configured specific
mission, or the configured number of distinct missions, has actually been
checked. The generator uses the same reachable mission-unlock model for item
placement so Archipelago can validate completion.
