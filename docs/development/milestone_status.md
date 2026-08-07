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
| 5 — Activate the exact default static APWorld pool | **Complete** | The active APWorld consumes the Milestone 4 registry and generates exactly 147 network locations, 26 progression instances, 28 useful instances, 93 weighted filler instances, zero traps, 65 hidden completion events, and one code-less Victory event. |
| 6 — Add atomic persistent AP state and seed/save binding | **Complete** | Accepted Python-writer ADR, schema-1 atomic sidecar/binding engine, slot-data version 2 authenticated seed identity, recovery/quarantine/lock tests, and explicit Milestone 7 live-save deferral. |
| 7–26 | Not started | Deliberately outside this change. |

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

## Milestone 5 completion evidence

- Active public item and location maps are the frozen first-release registry;
  the legacy per-mission unlock and 131-location tables remain compatibility
  inputs only.
- The pool contains the exact registry multiplicities and classifications,
  with all 93 filler instances selected by one deterministic weighted draw
  from the canonical YAML weights. No legacy mission unlock or trap is
  generated.
- All four location families are active. Task 36 is absent, task 72 exists only
  as locked code-less Victory, and 65 separate mission-completion events use no
  network addresses.
- The six documented side challenges and 12 orb thresholds above 300 are
  enabled but `EXCLUDED`; automated fill rules reject progression/useful items
  at all 18.
- The fixed Milestone 4 table versions, hashes, slot-data schema, retained IDs,
  and reserved IDs are unchanged.
- `tools/verify_source_tables.ps1` passed all six source-audit groups.
- The packaged APWorld test suite passed **108 tests** from a disposable
  Archipelago checkout with bytecode and pytest cache writes disabled.
- Ruff lint/targeted formatting and the existing mypy compatibility-module
  checks passed.
- `tools/build_apworld.ps1` produced a validated 28-entry artifact with SHA-256
  `5e828817bfcf097bf4d72d4616e33e95a6e23ceee9047f12de350329b889d5ad`.

## Milestone 6 completion evidence

- [ADR-001](ADR-001-python-owned-ap-state.md) accepts Python as the sole
  persistent writer and separates its atomic sidecar from GOAL's temporary
  observation snapshot.
- Schema 1 includes every roadmap field plus a state UUID and monotonic
  revision. Fresh creation, one-time seed/team/slot/name/save binding,
  explicit received-item states, sorted location IDs, save switching, clean
  and unclean shutdown, and stale revision rejection are automated.
- State uses the platform `Archipelago/Jak3/state-v1` data directory (or
  `JAK3_AP_STATE_DIR`), SHA-256 native-identity filenames, canonical checksums,
  same-directory temporary writes, retained atomic backup rotation, recovery,
  collision-safe quarantine, and a root-wide nonblocking OS lock.
- Compatibility and binding mismatches are read-only; tests cover every stored
  protocol/integration/slot/schema/table/options/design field plus wrong seed,
  team, slot, name, native slot, unsupported IDs, and corrupt backups.
- Slot-data version 2 requires the generated seed identifier. `Connected`
  validates the complete authenticated contract and canonical slot name;
  `RoomInfo.seed_name` remains diagnostic-only. GOAL mirrors version 2 without
  adding save or gameplay behavior.
- The packaged APWorld suite passed **147 tests** from a disposable
  Archipelago checkout with bytecode and pytest cache writes disabled.
- Ruff lint and targeted formatting passed; mypy passed for all compatibility
  modules including `persistence.py`.
- `tools/verify_source_tables.ps1` passed all six source-audit groups, and both
  Git-backed reference trees remained clean before and after verification.
- `tools/build_apworld.ps1` produced a validated 30-entry artifact containing
  `jak3/persistence.py`, with SHA-256
  `a4c415999ce1b749d252840b1ebca7da53397a2fa97d83d942a083292bb3e827`.

## Explicitly deferred

The active generator deliberately exposes one always-open, non-playable region
until Milestone 12 supplies Standard reachability. Milestone 6 adds storage and
authenticated Python contract validation, but no early placement guarantees,
received-item handling, location submission, mission hooks/dispatch, reward
interception, native state mutation, or goal reporting. Live observation of a
stable native identity and fresh/unprogressed status is deferred to Milestone
7; production binding stays disabled until then.

Open runtime risks remain recorded in [`../JAK3_AP_RISKS.md`](../JAK3_AP_RISKS.md),
especially permissive generator logic (`R-003`), runtime goal reporting
(`R-005`), gameplay persistence (`R-007`), mission/shadow behavior (`R-008`),
runtime compatibility enforcement (`R-012`), early guarantees (`R-013`),
placement-control interactions (`R-018`), and live native-save provenance
(`R-019`).
