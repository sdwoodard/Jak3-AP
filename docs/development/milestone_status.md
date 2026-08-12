# Milestone status

Snapshot date: **2026-08-12**

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
| 7 — Add a runtime state model and idempotent command transport | **Complete** | The original 12/15 matrix and the supported-policy closure are recorded in [`milestone-7.2-acceptance.md`](milestone-7.2-acceptance.md). The revised supported matrix is 14/14: clean and unclean client loss both recover through a full client/`gk`/`goalc` restart. Warm replacement attachment and external native-bank interference are approved unsupported limitations. |
| 7.1 — Structured diagnostics and support bundles | **Complete** | The paired logs remain; diagnostic schema 1 JSONL, the stable event registry, 64-record GOAL ring/drain, manifest-driven bridge lifecycle/hash, persistence/protocol instrumentation, exception capture, bounded retention, allowlist redaction, and local support-bundle export are implemented and automated. The cross-component forensic test drives the real launcher, persistence, protocol, and reconnect instrumentation to reconstruct startup/capture, recovery/rejection, harmless command replay/timeout/failure, and reconnect without native-save or sidecar contents. |
| 7.2 — Live acceptance and Protocol 3 freeze | **Complete — 14/14 supported rows pass** | Protocol 3/game integration 2 and tag 900 semantics are frozen. Both approved full-process recovery observations and ordinary unlocked save/load passed. Original warm-attachment failures and the locked-bank crash remain historical evidence for accepted unsupported workflows. |
| 8 — Indexed ReceivedItems and permanent-item ledger | **Complete** | The three-item slice, atomic schema-1 ledger, command 102, order-40 native items module, pre-dispatch whole-packet validation, both crash windows, same-descriptor native-load reconstruction including diagnostic-ring overflow, changed index-zero reconciliation, 318-test packaged suite, deterministic twin build, official-v0.3.5 1,167-target compile, corrected Blaster-dependency probe, and the disposable AP-tagged-save receipt/unsafe/replay/full-process recovery matrix pass; see [`milestone-8-acceptance.md`](milestone-8-acceptance.md). |
| 9 — Persistent location outbox | **Implemented — live completion gate pending** | Task 10 native observation and the nREPL-only task-11 debug check feed an atomic Python-owned local bit/outbox, retry until `Connected`/`RoomUpdate` confirmation, and never clear the durable bit. The 340-test standalone packaged suite, deterministic build, source audit, official-v0.3.5 1,168-target compile, and ordered module-load smoke pass. Post-review tests also prove closed transports report failure, batch/rollback diagnostics retain bounded location/task correlation, stale authenticated generations cannot cross connections, CommonClient gap `Sync` uses only the durable outbox, concurrent send paths share the five-second retry reservation, pre-bind updates collapse into the authoritative accumulated server snapshot, and valid reauthentication releases an earlier compatibility latch. The repository-owned `AGENTS.md` also restores the standalone canonical-source gate in GitHub. The controlled bound-save/native/server matrix has not been rerun; see [`milestone-9-acceptance.md`](milestone-9-acceptance.md). |
| 10–26 | Not started | Deliberately outside this change. |

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

## Milestone 7 implementation evidence

- Protocol 3 exports every roadmap runtime field plus schema/table metadata,
  native-save eligibility, client identity, a game-session nonce, and the eight
  most recent command receipts. Unknown snapshot fields are forward-safe.
- Native save/load method slots 22/23 are wrapped only to append/read version-1
  metadata tag 900. Missing or malformed tags preserve native loading and
  disable AP binding. Reload-safe hook capture retains the real native targets,
  and the matching auto-save `done`/`error` path commits or invalidates each
  staged identity. Freshness reads the candidate save's serialized totals/tasks
  rather than state from the save being switched away from.
- Review remediation makes the published identity/slot/eligibility descriptor
  reload-persistent while resetting sidecar acknowledgement, consumes each save
  proposal once, exports that consumption independently of the live descriptor,
  rotates client UUID entropy even after immediate invalidation/save switching,
  and expires or clears unused proposals after lost/clean client contact.
  Title-menu new-game
  saves cannot inherit the previous identity, eligibility monotonicity is scoped
  to one UUID, and tag-append failures invalidate the live binding. Mutation
  safety now positively requires a live target and current level, with level
  identity cleared before each observation; explicit command IDs also advance
  the client's automatic allocator.
- Follow-up review remediation publishes a successful native descriptor into
  reload-persistent state inside the matching `done` wrapper, validates the
  complete schema/table contract before reusing an already loaded bridge, and
  wakes the serialized heartbeat immediately when AP authentication changes.
- The final reload-lifecycle remediation also preserves the entire in-flight
  native save/load candidate and its exact auto-save handle across bridge-only
  reloads. An implementation-only bridge runtime version detects an older live
  object even after corrected source is already on disk, while packaged source
  changes create a durable marker before replacement and retain it across
  client restarts until a reload-persistent activation generation advances in
  a current compatible snapshot. The check occurs before protocol hello; an
  nREPL completion response without source activation retains the marker and
  fails the connection. A running same-contract bridge therefore cannot hide
  installed bug fixes; unchanged compatible reconnects still retain nonce and
  receipts.
- Command IDs, kinds, and payloads are now bounded to the signed 32-bit width of
  the GOAL snapshot and receipt fields on both sides. Python rejects overflow
  before allocation/transmission, while GOAL rejects it before sidecar refresh,
  receipt recording, high-watermark advancement, or test-target mutation. An
  incompatible reconnect also closes any already-open sidecar writer lease and
  clears its live acknowledgement.
- Table-contract hashes are validated at their exact 64-character wire length
  before GOAL copies them, so a canonical prefix with trailing data cannot pass
  compatibility. Native tag error code/message state is reload-persistent and
  is cleared only when a valid identity is published, preserving actionable
  missing, malformed, and I/O diagnostics through bridge-only reloads.
- Save-binding acknowledgement is now descriptor-qualified on every control
  message and harmless mutation: loaded/bound bits are accepted only with the
  exact live native UUID and slot, and commands refresh them before runtime
  safety is evaluated. This prevents a stale sidecar heartbeat from re-binding
  a newly loaded or copied save before Python completes repository switching.
- The Python client opens, switches, and closes schema-1 state as live save
  identity changes; binding failures stay read-only and harmless receipts are
  persisted with their game-session nonce.
- Each Python UUID proposal is now preceded by an atomic, checksummed version-1
  authorization record containing its seed/team/slot/name provenance. Live
  first binding requires that exact record for both a missing sidecar and a
  crash-left unbound sidecar, closing the room-switch window between native tag
  publication and the sidecar binding commit without changing schema 1 or tag
  900.
- `SET_TEST_TARGET` is target-state/idempotent. Additive effects, invalid or
  conflicting IDs, stale sessions, contract mismatches, and unsafe state are
  rejected with stable result/error codes. `QUEUED` is reserved and not used.
- The dependency-ordered OpenGOAL v0.3.5 build compiled all 1,165 rebuilt
  targets against the separate active project, including the reload-safe and
  operation-specific save hooks. The later no-save safety fix adds a
  reload-safe `game-info.initialize!` wrapper: full native sessions without a
  supplied save now clear the old descriptor, while a successful New Game save
  arms a one-shot exception for the normal save-first transition. The focused
  protocol/client/persistence suite now passes all 104 tests, and the full
  1,165-target OpenGOAL rebuild passes with the new hook, signed-width command
  guard, exact-length contract hashes, and reload-persistent diagnostics. An
  attached-runtime
  smoke then loaded the
  bridge twice more and passed all eight native-versus-installed pointer
  assertions. Automated protocol/client tests pass. A live disposable-config
  smoke verified the complete snapshot,
  hello/query/ping, client-reconnect receipt discovery, game-restart nonce
  replacement, stale-nonce rejection, duplicate/conflict behavior, missing-save
  safety, and additive-effect rejection. Live title/save/copy acceptance remains
  the completion gate, including the `Continue Without Save` transition.
- A second attached-runtime review smoke preserved identity, slot, and
  eligibility across repeated bridge reloads while resetting AP
  acknowledgement, accepted a fresh proposal, rejected it after six seconds,
  and cleared it on clean disconnect. It used only bridge metadata and the
  harmless test target.
- The 30-entry packaged APWorld passed all 195 tests from the disposable
  Archipelago environment with bytecode/cache writes disabled; the final
  artifact hash is recorded in the verification matrix.

## Milestone 7.1 completion evidence

- `diagnostics.py` is the sole support-file writer and preserves the paired
  client/OpenGOAL text logs while adding one schema-1 JSONL timeline.
- The immutable registry documents stable names, severities, GOAL codes, and
  allowlists. Concurrent-source ordering, UTF-8/UTC serialization, ANSI and
  multiline normalization, malformed-event isolation, exception deduplication,
  rotation/retention, and write failure are covered by focused tests.
- `archipelago-diagnostics.gc` owns only a 64-record integer ring, transition
  observation, temporary-snapshot export, and idempotent acknowledgement.
  Source/channel readiness remains reserved until acknowledged, and Python
  preserves GOAL source sequences with explicit reload generations.
  Control retains all Protocol 3, save, binding, and safety decisions and no
  longer opens a support log.
- Manifest version 1 drives APWorld contents, transactional installed-client
  repair, the standalone installer, exact object order, runtime source load,
  and canonical source-set hashing without wildcard discovery.
- Persistence and protocol sinks are optional and failure-isolated. Synthetic
  sink exceptions do not alter commit revisions, stored state, harmless command
  results, or game test-target mutation.
- `/diagnostics export` writes a local allowlisted ZIP with validated event
  segments, sanitized human logs, checksums, runtime/version/persistence/command
  summaries, capture gaps, and an explicit missing-artifact status. A forensic
  test reconstructs the required startup-to-reconnect failure sequence from the
  bundle alone and proves UUID/password/token/native-state data is absent.
- Diagnostic-only compatibility repair leaves the live Protocol 3 control
  nonce, receipt ring, and test target intact. Process capture uses bounded
  sanitized pipes without raw spools; console-only logging, provider schemas,
  archive failover, support retention, actual server/nREPL/binding lifecycle,
  and categorized revision/backup events have focused regression coverage.
- Export requires every registered schema-1 field and validates known values
  while ignoring unknown future optional fields. Abandoned archive temporary
  files are removed on startup, exception handlers are restored only while
  still owned, and a failed requested clean persistence close is reported as
  unclean. Archive publication is atomic, and capacity is reserved before an
  export can report completion. Live source replacement requires independent
  control and diagnostic activation generations before clearing its durable
  marker.
- Native load instrumentation begins at `auto-save.restore` before `mc-load`,
  so failures that never call `game-info.load-game` still receive one terminal
  diagnostic event without changing Milestone 7 binding semantics.
- Diagnostic hardening treats quoted, spaced, structured, separator-free
  mixed-case, and Digest credentials as complete redaction units and omits
  oversized unbroken process lines before storage. GOAL drain state now follows
  activation/sequence resets across reconnects, persistent optional-channel
  failures are transition-latched, and repeated duplicate records produce no
  repeated drain-completion noise. The bundle's bounded capture-gap summary is
  derived from emitted launcher, pipe, protocol, and collector events.
- Atomic process-aware markers prevent concurrent clients from misclassifying
  or pruning one another's live sessions. Writer-renewed local and remote
  leases expire after 30 minutes, local markers also require a live PID, and
  each live marker advertises its remaining rotation reservation. Support ZIP
  capacity publication is process-wide, so concurrent sessions cannot
  overcommit the managed cap.
- Event validation now enforces explicit nested runtime/safety schemas at emit
  and export-read time. Startup/fallback/export pruning reserves every live
  active rotation footprint, invalid over-cap policies fail early, Archipelago `NoFile` /
  `NoStream` and progress routing are preserved, pipe read failures become
  capture gaps, and oversized bundle logs retain and declare their newest
  sanitized evidence. Both PowerShell manifest consumers behaviorally reject
  extra root/module fields, noncanonical phases, and coercible wrong scalar
  types. Python and standalone bridge installation now share a cross-process
  transaction lock. GOAL ring acknowledgements run off the Protocol 3 result
  path, and persistence binding failures no longer render identity values.
- The capacity lease is now published before startup pruning under the same
  process-wide transaction used by fallback and export, and an initial primary
  marker-publication failure rehomes all support artifacts to temporary storage.
  Same-host live lock owners cannot be evicted by age, while process-start
  identities safely recover PID-reused owners across Python and PowerShell.
  Packaged undeclared bridge sources are rejected anywhere in the staged world,
  and GOAL acknowledgements carry their producer activation generation so a
  delayed old acknowledgement cannot drain a newly loaded ring.
- All **287** packaged tests pass from the deterministic 33-entry APWorld;
  SHA-256 is
  `bbd3a08916a74988ee5043cec4d929e8e51ec022eddf271aeabf8fb0bf658c69`.
- The separate active OpenGOAL v0.3.5 project installed the manifest, built all
  required `(mi)` targets from source set
  `2f806f6817d28bb20522eb8dab60f66bc22b7dbda3404f991a38bccae5a9bc90`,
  loaded control then diagnostics, and exported diagnostic activation
  generation `2` with retained source sequences `0` through `3`. A synthetic
  generation-`1` acknowledgement left all four records intact; the matching
  generation-`2` acknowledgement and its duplicate drained idempotently to
  zero. No native-save acceptance scenario was run.

## Milestone 7.2 acceptance evidence

- Two independent authoritative APWorld builds were byte-identical at 220,211
  bytes with SHA-256
  `f74c13f2b0c24e44cc70be224ca4feefd167590e6ff3b29ed248f0fdb412adc5`.
  Normal launcher installation activated source set
  `fb3c2d69071c803fd0132b27bce1412a51f81028a74c2e780a30aed4441ace22`;
  the pending-reload marker was not manually cleared.
- After documenting the packaged first-release restart policy and applying the
  required mechanical formatting, two final 220,510-byte APWorld builds were
  byte-identical at SHA-256
  `6ca4ce729e6beed8bd5009ac3341e5e164637cf7ece5c59d85a71ec808d797ed`.
  Live-tested production semantics are unchanged; only packaged documentation
  and whitespace formatting account for the final artifact hash change. That
  exact final package passed all 293 tests in the disposable Archipelago
  environment.
- All 15 real native-save/restart/command rows were exercised with disposable
  saves and isolated AP state. Fresh/repeated load, game restart, both startup
  orders, A → B → A, copied-slot rejection, vanilla-tag rejection, Continue
  Without Save, both New Game identity cases, harmless deduplication, title
  query/unsafe mutation, and unlocked recovery passed.
- Rows 3 and 4 failed because OpenGOAL v0.3.5 does not accept a replacement
  compiler connection after its first connection is lost. Row 13 failed
  because an exclusively locked native bank throws through the upstream card
  scan and terminates `gk`; the native banks and AP revision remained unchanged
  and normal save/load recovered after unlock.
- The first-release support policy accepts those upstream limitations. The
  supported recovery after clean or unclean client/compiler loss is a complete
  restart of the client, `gk`, and `goalc`; warm replacement attachment is
  unsupported. External locking, replacement, or editing of native save banks
  is unsupported and original row 13 remains an accepted limitation.
- Replacement observation A recovered Save A after a clean full-process
  restart with the same descriptor/sidecar and slot, a new nonce, an empty
  receipt ring, and no safe state before exact rebinding. Replacement
  observation B detected the prior unclean client as diagnostic event 1, then
  recovered Save B through the same full-process path with the same guarantees.
  An ordinary unlocked Save B save/load also retained its descriptor, sidecar,
  authorization, binding, and safety. The revised supported matrix is 14/14.
- The recorder retains the row-4 and row-13 bundle names, sizes, and SHA-256
  values, but the exported ZIP bytes were absent from the ignored evidence root
  at final audit. This retention gap is recorded in the acceptance report.
- The matched five-minute samples passed: frame p95 changed by −0.102 ms,
  normalized CPU p95 by +0.2759 percentage points, and connected warm private
  memory grew 675,840 bytes. Heartbeats were 0.904 Hz and healthy heartbeats
  produced no INFO noise. A 30-minute connected gameplay sample retained
  0.9018 Hz heartbeats; its large `gk` allocation was content-loading growth,
  while the client shrank and `goalc` grew only 1.8 MiB.
- Protocol 3/game integration 2, native tag 900/version 1, authorization
  version 1, descriptor-qualified acknowledgement, result/error meanings, and
  the eight-entry receipt ring are semantically frozen. Any later change needs
  a protocol bump and compatibility/migration decision. The freeze does not
  waive the accepted upstream limitations or broaden the supported workflow.

## Explicitly deferred

The active generator deliberately exposes one always-open, non-playable region
until Milestone 12 supplies Standard reachability. Milestone 8 implements
ReceivedItems only for Jetboard, Blaster stage 1, and Armor stage 1. Milestone 9
implements only task 10 and the task-11 debug check; its live completion gate is
still pending. There are still no early placement guarantees, consumable
handling, other location hooks, mission dispatch, reward interception, or goal
reporting. Milestones 7/7.2 remain complete for their documented first-release
scope; these gameplay domains remain assigned to later milestones.

Open runtime risks remain recorded in [`../JAK3_AP_RISKS.md`](../JAK3_AP_RISKS.md),
especially permissive generator logic (`R-003`), runtime goal reporting
(`R-005`), gameplay persistence (`R-007`), mission/shadow behavior (`R-008`),
runtime compatibility enforcement (`R-012`), early guarantees (`R-013`),
placement-control interactions (`R-018`), and live native-save provenance
(`R-019`).
