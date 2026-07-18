# Jak 3 Archipelago for OpenGOAL

This repository contains a native-task mission randomizer for Jak 3:

- `jak3/` is the installable Archipelago world and client.
- `opengoal/archipelago/` is the Jak 3 GOAL bridge.
- `Jak3.yaml` is a ready-to-edit player template.
- `scripts/build_apworld.ps1` builds `dist/jak3.apworld`.

## World model

The world uses the authoritative Jak 3 `game-task` ranges from the OpenGOAL decompile. Main-game task IDs 6-71 become 66 mission checks and mission-unlock items. Task 6 is always available. All 65 native optional tasks (73-137) provide challenge checks, leaving room for the 38 equipment items plus health, ammo, and eco filler.

Central requirement tables make required weapon tiers, vehicles, the Jetboard, and Light Jak powers part of Archipelago reachability. Equipment referenced by a mission or challenge rule is classified as progression; optional ammo capacities, armor, Dark Jak powers, and the Slam Dozer remain useful items.

Upgrade grants are cumulative, idempotent versions of Jak 3's native `game-info` feature and vehicle rewards, making progressive upgrades safe even if a higher level is requested first. New item receipts are queued through loading and displayed one at a time on the in-game HUD. See `jak3/docs/upgrade_safety.md` for the audited grant matrix and failure behavior.

Goals may be a selected milestone mission or 5-66 distinct completed missions. Generation counts only missions whose unlock and equipment requirements are satisfied; the runtime client verifies actual completed checks before reporting `CLIENT_GOAL`.

## Build and test

```powershell
.\scripts\build_apworld.ps1
```

The build script adds APWorld container metadata to the packaged copy of `archipelago.json` and validates the resulting archive. The source manifest intentionally omits container-only `version` and `compatible_version` fields.

Install `dist/jak3.apworld` through Archipelago. Completely close and restart Archipelago after replacing an older copy because loaded world modules and manifests remain cached for the life of the process.

To run integration tests against an Archipelago checkout, place the artifact in the checkout's `custom_worlds` directory and run:

```powershell
$env:AP_TEST_WORLDS = "jak3"
python -m pytest path\to\Jak3-AP\tests -q
```

## Current integration boundary

The GOAL bridge implements mission completion, mission unlocks, replay dispatch, slot/seed isolation, reconnection, item upgrades, consumable filler, and item notifications. Trap IDs and durations cross the protocol, but the provided bridge currently logs traps instead of applying disruptive gameplay effects while Jak 3-specific trap actors are validated.

The bridge writes `jak3-ap-state.tmp`; this is also the client's default. Set `JAK3_AP_STATE` if the mod publishes the snapshot elsewhere.

## Source references

- `Archipelago/worlds/jakanddaxter/` for APWorld and client conventions.
- `jak-project/goal_src/jak3/engine/game/task/` for supported OpenGOAL APIs.
- `openGOAL-decompile/jak3/.../all-types.gc` for native task enum values.
- `Jak2_Example.yaml` for goal and trap option shape.

This fan project is not affiliated with Naughty Dog, Sony, OpenGOAL, or Archipelago.
