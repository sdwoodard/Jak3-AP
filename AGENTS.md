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

The design specification is normative for the first-release defaults. Do not
silently change or reinterpret it.

## Read-only reference trees

The sibling workspace directories `../jak-project/`, `../Archipelago/`, and
`../openGOAL-decompile/` are immutable reference inputs. Do not edit, patch,
format, generate files into, install mod files into, or use them as build
destinations. Read-only searches, source audits, hashing, and tests that do not
write into them are allowed.

All project-owned changes belong in this repository. OpenGOAL integration
smoke tests must install into a separate active OpenGOAL project, such as
`D:\OpenGOAL\active\jak3\data`, never into `../jak-project/`. If a tool cannot
run without writing to a reference tree, use a disposable copy outside it and
document that use.

Before and after reading a Git-backed reference tree, verify its Git status is
clean. `../openGOAL-decompile/` has no Git metadata in this workspace, so treat
it as strictly immutable and do not claim it was restored from Git.

## First-release scope

Implement only the recommended default configuration. Unsupported and
experimental option values must fail early with a clear error until a later
milestone explicitly implements them.

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
  source with a `value` unless each orb unit has its own independently persistent
  native identity.
- Stable collectible identity must come from audited source data, such as a
  level/resource/permanent-entity key. Actor addresses, spawn order, coordinates,
  display order, and generated list position are never public location identity.
- Repeatable enemy drops, respawning containers, replay rewards, and random
  spawns are never individual locations. Skull Gem enemy drops remain invalid
  even when cumulative locally earned totals are observed.
- AP-delivered Orb Packs and Skull Gem Packs are spendable resource effects only.
  They never increment local-earned totals, regional totals, source completion
  bits, or sanity locations.
- Any later promotion of a collectible mode changes the generated location
  contract. It requires an explicit location-table/version/hash decision,
  deterministic slot data, stable ID reservations, persistence compatibility or
  migration behavior, and full logic/accessibility tests. Milestone 7.2's frozen
  Protocol 3 semantics are not changed implicitly.
- Native collectible observation belongs in `archipelago-locations.gc`;
  AP-delivered resource effects belong in `archipelago-consumables.gc`. Neither
  responsibility moves into the Protocol 3 control plane.

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
