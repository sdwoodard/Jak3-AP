# Phase-1 upgrade and notification safety

This note documents the retained protocol vertical slice. Its progressive item
kinds will be replaced by the design-default named-item ledger in phase 2.

The Archipelago grant bridge follows the same persistent `game-info` fields as
Jak 3's native `eval-game-task-cmd!` reward evaluator in
`engine/game/task/task-control.gc`.

| AP kind | Upgrade | Native storage | Order-safety behavior |
| --- | --- | --- | --- |
| 0–3 | Four gun families | `game-info.features` | Every level ORs in that level and every earlier mod. |
| 4–7 | Four ammo capacities | `game-info.features` | Level 2 ORs in both capacity bits. |
| 8 | Jetboard | `game-info.features` | Independent, idempotent board bit. |
| 9–13 | Wasteland vehicles | `game-info.vehicles` | Each vehicle is an independent, idempotent bit. |
| 14 | Dark Jak powers | `game-info.features` | Every level includes Dark Eco, Dark Jak, and all earlier powers. |
| 15 | Light Jak powers | `game-info.features` | Every level includes Light Eco, Light Jak, and all earlier powers. |
| 16 | Armor | `game-info.features` | Every level ORs in all earlier armor bits. |

These operations do not dereference the player actor, construct a weapon or
vehicle actor, or modify an active mission. They are consequently safe during
menus and loading as long as `game-info` is loaded, which is a prerequisite of
loading this mod. Unknown kinds and out-of-range levels perform no feature
mutation. Receive indices make replay idempotent.

Consumable filler is handled separately and dereferences `*target*` only after
checking that a target exists. Losing a consumable during a menu is preferable
to touching a missing actor; consumables are never progression.

New server receipts are retained by the Python client until the title screen
is inactive, a target exists, and no earlier notification owns the HUD. The
GOAL side copies notification text out of the nREPL buffer before starting its
three-second display process. A five-second watchdog releases the notification
lock if a display-pool teardown interrupts that process.
