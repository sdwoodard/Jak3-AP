# Jak 3 Archipelago development instructions

## Normative sources

Read these before making changes:

1. `docs/design/progression-and-logic.md`
2. `config/templates/Jak3.yaml`
3. Audited OpenGOAL Jak 3 sources
4. The existing Jak and Daxter Archipelago world

The revised roadmap is
`docs/development/Project-Milestones-Revised.md`. Milestone status is tracked
in `docs/development/milestone_status.md`, and conflicts, unknowns, and source
discrepancies belong in `docs/JAK3_AP_RISKS.md`.

The design specification is normative for the first-release defaults.

Do not silently change or reinterpret the specification. Record conflicts,
unknowns, and source discrepancies in `docs/JAK3_AP_RISKS.md`.

## Read-only reference trees

The following workspace directories are immutable reference inputs:

- `../jak-project/` — upstream OpenGOAL source reference.
- `../Archipelago/` — upstream Archipelago source and Jak and Daxter reference.
- `../openGOAL-decompile/` — decompiled Jak 1 and Jak 3 source snapshots.

Do not edit, patch, format, generate files into, install mod files into, or use
these directories as build destinations. Read-only searches, source audits,
hashing, and tests that do not write into the trees are allowed.

All project-owned changes belong in this repository. OpenGOAL integration
smoke tests must install into a separate active OpenGOAL project, such as
`D:\OpenGOAL\active\jak3\data`, never into `../jak-project/`. If a tool cannot
run without writing to a reference tree, use a disposable copy outside these
directories and document it.

Before and after work that reads a Git-backed reference tree, verify its Git
status remains clean. `../openGOAL-decompile/` has no Git metadata in this
workspace, so treat it as strictly immutable and do not claim it was restored
from Git.

## First-release scope

Implement only the recommended default configuration.

Unsupported and experimental option values must fail early with a clear error
until a later milestone explicitly implements them.

## Architectural invariants

- AP inventory is separate from native mission state.
- Permanent AP inventory is reconstructed from the AP ledger.
- Temporary mission grants never become AP receipts.
- Temporary mission grants never send location checks.
- Shadow native story state never satisfies AP rules.
- Shadow story state never increments the finale relic count.
- Every location is finite, persistent, monotonic, and idempotent.
- Item and location IDs are explicit and never derived from list position.
- Native behavior must not be guessed when source or runtime verification is
  still required.
- AP-delivered currency must not advance locally earned collectible checks.

### Collectible-sanity invariants

- The first-release collectible mode remains the existing global Precursor Orb
  threshold model. Regional and individual Precursor Orb modes, and every
  non-`off` Skull Gem mode, remain rejected until their explicit later
  milestones are complete.
- Milestone 12 may add source catalogs, audit tools, tests, and opt-in runtime
  observations. Audit data is not a player-facing location table and MUST NOT
  make an experimental option selectable.
- A future individual collectible location represents one finite native source
  with one durable identity. A source that awards two or three orbs remains one
  source with a `value` unless each orb unit has its own independently
  persistent native identity.
- Stable collectible identity must come from audited source data, such as a
  level/resource/permanent-entity key. Actor addresses, spawn order,
  coordinates, display order, and generated list position are never public
  location identity.
- Repeatable enemy drops, respawning containers, replay rewards, and random
  spawns are never individual locations. Skull Gem enemy drops remain invalid
  even when cumulative locally earned totals are observed.
- AP-delivered Orb Packs and Skull Gem Packs are spendable resource effects
  only. They never increment local-earned totals, regional totals, source
  completion bits, or sanity locations.
- Any later promotion of a collectible mode changes the generated location
  contract. It requires an explicit location-table/version/hash decision,
  deterministic slot data, stable ID reservations, persistence compatibility
  or migration behavior, and full logic/accessibility tests. Milestone 7.2's
  frozen Protocol 3 semantics are not changed implicitly.
- Native collectible observation belongs in `archipelago-locations.gc`;
  AP-delivered resource effects belong in `archipelago-consumables.gc`. Neither
  responsibility moves into the Protocol 3 control plane.

## OpenGOAL module boundaries

`mod/opengoal/goal_src/jak3/pc/features/archipelago.gc` is the stable Protocol 3
control-plane module. It owns only shared concerns such as:

- Protocol constants, compatibility fields, and shared control-plane types.
- Runtime-state and native-save/binding observation.
- Client/game session state and heartbeat handling.
- Command validation, deduplication, result/error codes, and dispatch wiring.
- Shared safety predicates and narrow interfaces used by gameplay modules.

Do not add later gameplay-domain implementations wholesale to
`archipelago.gc`. New behavior belongs in dedicated sibling modules introduced
by the milestone that first needs it. Expected boundaries include:

- `archipelago-diagnostics.gc` — bounded GOAL-side diagnostic event production.
- `archipelago-items.gc` — permanent item application and reconciliation.
- `archipelago-consumables.gc` — additive filler/consumable application.
- `archipelago-locations.gc` — native accomplishment observation/publication.
- `archipelago-rewards.gc` — native reward interception.
- `archipelago-overlays.gc` — reversible lesson and mission-equipment overlays.
- `archipelago-missions.gc` — route authorizations, mission-board behavior, and
  mission bootstrap orchestration.
- `archipelago-story-state.gc` — non-counting shadow native story state.

The expected names describe ownership boundaries; do not create empty
placeholder modules before a milestone needs them.

A later milestone may modify `archipelago.gc` only for a shared protocol field,
command/result/error code, dispatch entry, compatibility field, safety field,
or another narrow control-plane interface required by its dedicated module. Do
not refactor completed Milestone 7 behavior merely to reorganize files.

### Diagnostic ownership

- `worlds/jak3/agents/diagnostics.py` is the authoritative Python logging,
  structured-event, rotation/retention, redaction, and support-bundle boundary.
- A GOAL-side `archipelago-diagnostics.gc` may keep a bounded event ring and
  expose a small event-emission API to the control and gameplay modules.
- GOAL must not write the authoritative JSONL stream or support bundle. Python
  remains the sole support-file writer.
- Domain modules must emit through the shared diagnostic API rather than
  creating separate free-form log files or unrelated event formats.

Every new OpenGOAL module must be:

- Declared in one explicit, versioned, deterministic module manifest.
- Packaged in the APWorld and installed atomically with the other bridge files.
- Compiled/loaded in manifest order without wildcard discovery.
- Included in the canonical ordered bridge source-set hash.
- Covered by package, installation, compilation, load-order, and
  source-boundary tests.

## Task behavior

- Implement only the requested milestone.
- Do not start later milestones.
- Avoid unrelated refactoring.
- Add tests for every behavioral change.
- Keep the diff small enough for a human to review.
- Record deferred work rather than implementing it opportunistically.

## Completion requirements

Before reporting completion:

1. Run the targeted tests.
2. Run relevant lint, formatting, and type checks.
3. Review the complete diff.
4. Report files changed.
5. Report commands run and their results.
6. Report assumptions and unresolved runtime risks.

## CI and push discipline

Before pushing any change, run the same repository-owned gate that GitHub CI
uses. The Archipelago path must be a disposable checkout, never either
read-only reference tree:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_ci_checks.ps1 `
  -ArchipelagoPath D:\path\to\disposable\archipelago
```

Targeted tests remain useful during development but do not replace this final
pre-push gate. Preserve `AGENTS.md` and the canonical LF policy in
`.gitattributes`; the preflight treats both as repository contract files. If
the exact GitHub runner environment cannot be reproduced locally, push a
feature branch and require the `python-apworld` check to pass before merging
or updating `main`.
