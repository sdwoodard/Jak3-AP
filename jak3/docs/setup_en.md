# Jak 3 Multiworld Setup Guide

## Requirements

- Archipelago 0.6.7 or newer.
- A legally obtained Jak 3 disc image extracted by OpenGOAL.
- An OpenGOAL build with Jak 3 support.

## Install

1. Build `jak3.apworld` with `scripts/build_apworld.ps1`, then install it through Archipelago's **Install APWorld** action. Completely restart Archipelago after replacing an older build so it reloads the packaged manifest.
2. Copy `opengoal/archipelago` into the matching Jak 3 OpenGOAL source/mod tree and add `archipelago.gc` to that mod's project file after `game-task` is loaded.
3. Compile the mod in debug mode and leave the OpenGOAL compiler's nREPL open on port 8181.
4. Start **Jak 3 Client**, connect to the Archipelago room, and use `/repl connect`.

The integration uses native `game-task` IDs. Received mission unlocks are saved by item index, completed task IDs are sent as Archipelago checks, and reconnecting is idempotent. Bridge state is bound to the room seed and slot to prevent checks leaking between games.

Gun families, ammo capacity, Dark/Light Jak powers, and armor are progressive in-game upgrades. The Jetboard and five story Wasteland vehicles are one-time power items. Equipment required by a mission or challenge is classified as Archipelago progression and enforced by its access rule; optional capacity, armor, and Dark Jak upgrades remain useful items. Optional challenges unlock gradually as mission-unlock items are received, with health, ammo, and eco filling the remaining checks.

Progressive grants are cumulative and idempotent: a higher requested level also installs every prerequisite feature bit. Newly received server items are retained through title/loading states and displayed one at a time as orange HUD notifications once Jak and the HUD are active. Replayed item history restores inventory silently when reconnecting.

## Goal behavior

The AP client reports goal completion only after the configured mission itself, or the configured number of distinct missions, has actually been checked. The generator uses reachable mission unlocks as its equivalent completion model so item placement remains verifiable by Archipelago.
