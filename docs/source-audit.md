# OpenGOAL source audit

Audit date: 2026-08-04.

The design tables were checked against the local OpenGOAL source in
`jak-project` at commit
`425f143fccada9e38b35633bd298b5b64c6ca6e8` and the decompiled Jak 3 task
sources beneath `goal_src/jak3/engine/game/task`. The Jak 1 Archipelago client
in the local Archipelago checkout at commit
`feab54daec712ffb333b8c73f38eb69e1ed9c508` was used only as an
integration-pattern reference.

Run the repeatable structural audit with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_source_tables.ps1 `
  -OpenGoalRoot ..\jak-project
```

Verified results:

- `game-task` IDs and aliases cover 6 through 137.
- The node enum and node table both contain 410 entries.
- Story tasks 6 through 72 have close-task records except task 36, whose source
  contains only vehicle-training hover-zone nodes.
- All 65 side tasks 73 through 137 have close-task records.
- The source has 75 reward commands across 51 reward-bearing nodes; the design
  accounts for all of them as 38 major, 8 crystal-only, and 5 never-valid
  reward checks.
- Every one of the 24 default selected side tasks (114-137) has the documented
  source parent.
- Every candidate milestone node listed by the design exists on its documented
  task.
- Jak 3's OpenGOAL source defines the global Precursor Orb maximum as 600.

Two certain design corrections were made:

1. Task 88 is named `desert-bbush-get-to-19` in the task enum, but both of its
   node records are `wascity-bbush-get-to-19` and are parented by task 52
   (`desert-artifact-race-2-resolution`). The design now records that normalized
   alias and parent instead of leaving it unresolved.
2. Reward node 256 dispatches `add-pass-slumb-genb`; its effect is now named
   **Slums B-Gen B Pass** with the native command recorded verbatim.

Structural source evidence cannot by itself prove controller execution,
advanced movement assumptions, temporary bootstrap cleanup, save/load
reconciliation, or that a HUD hook is safe in every loading state. Evidence
marked walkthrough, inference, bootstrap, or experimental in the design keeps
that label and still requires the runtime acceptance tests in section 21.
