# Milestone status

Snapshot date: **2026-08-07**

The revised roadmap in
[`Project-Milestones-Revised.md`](Project-Milestones-Revised.md) is the status
authority. A milestone is complete only when its stated gate is demonstrated;
later gameplay work is not credited early.

| Milestone | Status | Evidence |
| --- | --- | --- |
| 0–3 | Complete before revised roadmap | Historical implementation and protocol-2 evidence are retained in this directory. |
| 4 — Consolidate normative sources and freeze the versioned data contract | **Complete** | Canonical in-repository sources, literal first-release registries, complete legacy ID retention/reservation, deterministic table/options hashes, versioned JSON-safe slot data, shared Python/GOAL constants, standalone tests, and push/PR CI are present and passing. |
| 5–26 | Not started | Deliberately outside this change. |

## Milestone 4 completion evidence

- Canonical design: `docs/design/progression-and-logic.md`.
- Canonical default YAML: `config/templates/Jak3.yaml`.
- Repository instructions: `AGENTS.md`, with repository-relative canonical and
  evidence paths.
- Revised roadmap/status/risk/engineering evidence: version-controlled under
  `docs/development` and `docs/JAK3_AP_RISKS.md`.
- Workspace duplicate specification paths are redirect-only stubs.
- Registry totals: 26 progression instances, 28 useful instances, 147 network
  locations, code-less mission/Victory events, and stable mission/bootstrap/
  shadow profile identifiers.
- An independent literal snapshot preserves every one of the 106 legacy item
  IDs and 131 legacy location IDs. Each code is either tied to an explicit,
  validated retained concept or permanently reserved. Task 36 is reserved,
  task 72 is an event, and task 88 retains native ID 88 plus its normalized
  alias.
- Frozen table hashes and resolved-options hash use documented canonical UTF-8
  JSON serialization.
- Slot data excludes redundant name/ID and legacy requirement mappings.
- Python client diagnostics and the GOAL bridge carry matching versions/table
  hashes without adding gameplay protocol behavior.
- `tools/verify_source_tables.ps1` passed all six source-audit groups.
- The packaged APWorld test suite passed **110 tests**.
- Ruff lint, targeted Ruff formatting, and mypy compatibility-module checks
  passed.
- `tools/build_apworld.ps1` produced a validated 27-entry artifact with SHA-256
  `3b7a33a876f4f054fbadeef42c24aad146d3e7aa9f10794f96444e2148f28534`.

## Explicitly deferred

The active generator remains the isolated 131-location scaffold until
Milestone 5. This milestone adds no received-item handling, location
submission, persistence, mission hooks/dispatch, reward interception,
reachability rules, native state mutation, or goal reporting. Runtime
slot-data/table mismatch enforcement begins only when a later runtime milestone
consumes the room contract.

Open runtime risks remain recorded in [`../JAK3_AP_RISKS.md`](../JAK3_AP_RISKS.md),
especially the inactive target generator (`R-003`), task-36 scaffold conflict
(`R-004`), task-71 scaffold goal (`R-005`), gameplay persistence (`R-007`),
mission/shadow behavior (`R-008`), and runtime compatibility enforcement
(`R-012`).
