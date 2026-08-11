# Collectible Sanity Source Audit and Data Contract

**Applies to:** Milestone 12 and the post-beta Milestones 28–33
**Status:** Planning and evidence contract; does not enable player options
**Normative design:** `docs/design/progression-and-logic.md`

## Purpose

The current default already uses global locally earned Precursor Orb thresholds.
The project also documents future regional/individual orb modes and future Skull
Gem modes. Those future modes cannot be enabled safely from a total counter or a
coordinate list alone.

This document defines the source/runtime evidence that must be collected before
new collectible locations, stable IDs, access rules, or option values become
public. Audit tooling and candidate catalogs are development data only.

## Definitions

- **Finite source:** one native actor, container, reward, or persistent state
  transition that can be completed once per normal save.
- **Source value:** the amount of local currency contributed by that finite
  source. A single source may have value 2 or 3.
- **Local-native earned:** currency created by the player's native Jak 3 world.
- **AP-delivered:** currency applied from a `ReceivedItems` Orb/Gem Pack. It is
  spendable but never counts toward collectible checks.
- **Repeatable source:** an enemy drop, respawning container, replay reward, or
  other source that can generate currency repeatedly. It can never be an
  individual location.
- **Candidate source ID:** an audit identifier. It is not a public Archipelago
  location ID until a later milestone freezes the location table.

## Evidence hierarchy

1. Audited OpenGOAL source/resource data and persistent entity/reward fields.
2. Reproducible runtime observation on the pinned OpenGOAL build.
3. Walkthrough evidence only for intended-path access requirements.
4. Conservative inference, explicitly labeled and not sufficient by itself for
   public identity or persistence.

Relevant upstream evidence includes:

- OpenGOAL PR 4275 / commit `8c44183`: standalone `skill` actors and orb-bearing
  crates/urns can be distinguished, and container pickup type/value can be read.
- OpenGOAL PR 4312 / commit `07171c9`: orb-bearing containers use persistent
  `subtask-complete` state; at least one source awards two orbs and one awards a
  golden triple orb.

These facts show that a source-derived catalog is plausible. They do not prove
that every source already has a unique, stable cross-build network identity.

## Candidate catalog schema

Each candidate record must contain:

```text
catalog_schema_version
source_id_candidate
source_family
native_level
logical_region
native_actor_or_reward_kind
resource_name
persistent_key_or_entity_identity
value
respawn_class
save_persistent
availability_parent
access_requirements
one_time_reward
source_evidence
runtime_verified
notes
```

Recommended `source_family` values include:

```text
orb_standalone
orb_container
orb_mission_reward
orb_challenge_reward
gem_static
gem_mission_reward
gem_challenge_reward
gem_repeatable_enemy_drop
secret_purchase
```

## Stable identity rules

- Candidate/public IDs must be deterministic across repeated extraction and the
  pinned source/build.
- Prefer a composite native identity such as level/resource/permanent-entity
  key. Document every component and uniqueness assumption.
- Actor addresses, allocation order, spawn order, coordinates, display names,
  and list position are not identity.
- Coordinates may be retained only as diagnostic/audit metadata.
- A multi-orb container is one source with `value = 2` or `value = 3` unless
  runtime/source evidence proves independent persistent state for each unit.
- Duplicate candidate identities are an audit failure, not an opportunity to
  append an arbitrary ordinal.
- Public integer location IDs are assigned only in Milestone 28 after the
  catalog and compatibility/migration decision are accepted.

## Precursor Orb audit procedure

### Static/source extraction

1. Enumerate standalone `skill` actors.
2. Enumerate supported crates, sacks, baskets, urns, and other containers whose
   pickup type is `skill`.
3. Record container value and persistent completion field.
4. Enumerate one-time mission/challenge/native reward sources that contribute to
   the 600 local total.
5. Assign logical regions and candidate access requirements.
6. Produce a deterministic catalog and duplicate/total report.

### Runtime verification

For each representative source class, and every exceptional source value:

1. Observe the uncollected source and candidate identity.
2. Collect it once and confirm the local-native delta.
3. Save/load, die/revisit, and restart the game as applicable.
4. Confirm the persistent completion state prevents a second local-earned
   contribution.
5. Confirm AP-delivered Orb Packs do not alter its source bit or local-earned
   total.
6. Record source/runtime discrepancies in `docs/JAK3_AP_RISKS.md`.

### Precursor acceptance

- The sum of all accepted local-native source/reward values is 600, or a lower
  proven normal-save maximum is documented with every missing value explained.
- Every accepted source has one deterministic candidate identity and exactly one
  logical region.
- Every first-release global threshold can be assigned a conservative access
  rule through `reachable_local_orb_value(state)`.
- No repeatable/replay/Hero Mode source is counted.
- Regional mode remains blocked until all accepted values have unambiguous
  region attribution.
- Individual mode remains blocked until every enabled source has stable identity,
  persistence, value, and access evidence.

## Skull Gem audit procedure

1. Enumerate every known source family and classify it as finite or repeatable.
2. Prove that ordinary enemy drops are repeatable and exclude them from any
   individual table.
3. Search for static non-respawning entities with independent persistent state.
4. Enumerate finite mission/challenge rewards separately from repeatable drops.
5. Audit first-time secret purchase persistence and enabled purchase count.
6. Measure/localize the native local-earned increment path separately from the
   spendable balance and from AP-delivered Gem Packs.
7. Propose a finite `skull_gem_milestone_cap` and a safe
   `skull_gem_progression_cap`; do not infer a finite family from bundle size.

### Skull Gem decisions

- **Secret purchases:** GO when the first-time persistent table, costs/bypass
  behavior, logic, and replay tests are complete.
- **Cumulative milestones:** GO only after a finite cap and placement policy are
  versioned. The recommended first progression cap is zero.
- **Individual static:** GO only if a complete non-respawning, independently
  persistent source table exists. Otherwise retain/reject the documented mode
  and reserve any proposed IDs without shipping ghost locations.

## Logic deliverables

The audit must produce enough information for Milestone 13 to implement:

```text
reachable_local_orb_value(state)
```

For future source modes, each source also needs a normal Archipelago access rule
based on route authorizations, mission completion events, permanent capabilities,
and logical region. Pickup proximity alone is not a rule.

## Development-only telemetry

Opt-in audit telemetry may use the shared Milestone 7.1 diagnostic API, but it
must be bounded and disabled in normal player sessions. Suggested event names:

```text
audit.collectible.source_observed
audit.collectible.source_collected
audit.collectible.source_revisited
audit.collectible.total_reconciled
audit.collectible.catalog_mismatch
```

Telemetry failure never affects gameplay or persistence. Raw actor pointers,
full memory dumps, and uncontrolled resource payloads are prohibited.

## Required outputs

- Deterministic candidate catalog in a documented development-data path.
- Human-readable totals/duplicates/region report.
- Runtime verification procedure and results.
- Source discrepancies and unresolved decisions in the risk register.
- Tests proving audit data does not enter the current public location registry,
  location-table hash, slot data, or accepted option profile.

## Non-goals

- Do not add public location IDs.
- Do not enable regional/individual orb modes.
- Do not enable non-off Skull Gem modes.
- Do not modify the frozen Protocol 3 contract.
- Do not add normal per-frame/per-pickup INFO logging.
- Do not treat coordinates or an observed actor pointer as identity.

## Completion gate

The project has a deterministic, evidence-backed candidate catalog and a clear
GO/NO-GO result for global orb logic, regional orbs, individual orb sources,
cumulative Skull Gem milestones, secret purchases, and individual static Skull
Gems. The current generated world and supported option profile remain unchanged.

## Suggested Codex prompt

```text
/plan

Implement only Milestone 12 as a data/audit milestone.

Read AGENTS.md, the collectible-sanity design sections, this audit contract,
the current source audit, and the immutable OpenGOAL sources. Build a
deterministic candidate catalog for finite Precursor Orb and Skull Gem source
families, then verify representative persistence/value behavior in the real
runtime. Do not assign public AP IDs, enable options, change table hashes, or add
location traffic.

Prove the reachable local-orb data required by Milestone 13, classify every
Skull Gem family as finite or repeatable, and record explicit GO/NO-GO decisions.
```
