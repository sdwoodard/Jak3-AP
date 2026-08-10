# Jak 3 Archipelago risk register

This is the required home for conflicts, unknowns, and evidence gaps discovered
while implementing the normative design. Do not silently resolve a risk by
changing logic to match the retained pre-design-default scaffold.

Snapshot date: **2026-08-09**

## Status and severity

- **Open**: unresolved and blocks some later acceptance claim.
- **Watching**: a mitigation exists, but compatibility or operational evidence
  must continue to be recorded.
- **Closed**: exit criteria passed with linked evidence. Closed entries remain
  for design history.
- **Critical** blocks a playable/release claim; **High** can corrupt progression
  or lose checks/items; **Medium** can cause integration or support failures.

Owners are deliberately role-based until maintainers assign people.

## Active risks

### R-001 — Normative source drift

- Severity/status: **High / Closed**
- Owner: Design and release maintainers
- Risk: Two editable workspace/repository specification copies could drift,
  causing code, tests, or public documentation to target different contracts.
- Historical evidence: On 2026-08-06 the workspace copy retained SHA-256
  `F6630779AD84C58394A643886B93CCFC5871C02A09D4E8CF70D7CDD9E891CA1C`, while
  the repository mirror had SHA-256
  `CCF1CE26204EE99BD1BE72EF41DDCE2AE4DED140D17576509ABFD21FE8E74EEC`.
  A line comparison found only the two intentional Markdown hard-break spaces
  on workspace lines 3 and 4 missing from the mirror; trimmed text is equal.
- Resolution evidence: `docs/design/progression-and-logic.md` and
  `config/templates/Jak3.yaml` are now the canonical version-controlled paths.
  The workspace-level specification files are redirect-only stubs,
  `AGENTS.md` names the canonical paths, and standalone tests load no optional
  sibling specification. YAML semantics and the overlay/shadow comments are
  tested directly from the shipped template.
- Exit criteria: **Passed.** There is one editable design and one editable
  default YAML, both inside the standalone repository.

### R-002 — Dirty working-tree baseline

- Severity/status: **Medium / Closed**
- Owner: Repository maintainer
- Risk: The repository contained pre-existing uncommitted work when this
  documentation snapshot was taken. Future changes can accidentally mix,
  overwrite, or misattribute those edits.
- Historical evidence: The first snapshot was made from commit `0c7497d` with
  a dirty worktree. Before Milestone 4 work, the reviewed repository was clean
  at `4974885`, matching `origin/main`.
- Mitigation: Review `git status`, full diff, and untracked files before every
  edit; preserve unrelated user changes; use focused commits only when asked.
- Exit criteria: **Passed for the Milestone 4 baseline.** The implementation
  began from the documented clean commit; this entry remains for history.

### R-003 — Permissive scaffold is not Standard logic

- Severity/status: **Critical / Open**
- Owner: APWorld and logic maintainers
- Risk: The exact first-release pool is exposed in one always-open region. It
  can be mistaken for playable Standard logic even though it has no mission,
  item, route, finale, or early-guarantee rules.
- Current evidence: See
  [`development/specification-gap-matrix.md`](development/specification-gap-matrix.md).
  Milestone 5 activates the frozen registry with exactly 147 network locations,
  26 progression instances, 28 useful instances, 93 weighted filler instances,
  and the required default exclusions. Generation tests pass, but every
  location and the Victory event are deliberately immediate-access scaffolding.
- Mitigation: Keep the scaffold clearly labeled non-playable and keep protocol
  2 handshake-only until Milestone 12 replaces the region and rules with the
  audited Standard mission graph and access predicates.
- Exit criteria: Tiered board, default predicates, early guarantees, all-state
  reachability, beatability, and full Standard generation tests pass.

### R-004 — Task 36 lacks a durable completion source

- Severity/status: **High / Closed**
- Owner: OpenGOAL integration maintainer
- Risk: The retired scaffold created a network location for task 36, but the
  audited source has no `close-task` node for it. The normal bridge hook
  therefore could not complete that location.
- Current evidence: Source-table audit identifies task 36 as the only story
  omission from `close-task` coverage. Milestone 5 excludes it from active
  generation, permanently reserves legacy location ID `743001036`, and tests
  assert that neither its name nor code appears in the default world.
- Mitigation: Do not add it to another preset without a new finite, durable AP
  completion flag and runtime proof.
- Exit criteria: **Passed for the default.** Any future enabled form must still
  pass exactly-once, replay, offline, and save/load tests.

### R-005 — Task-72 Standard finale and goal reporting are absent

- Severity/status: **Critical / Open**
- Owner: Logic and client maintainers
- Risk: Generator correctness can be mistaken for end-to-end victory support.
  The runtime still lacks task-72 completion detection, persistent goal state,
  and Archipelago goal reporting/reconnect resend.
- Current evidence: Milestone 5 generates task 71 as a network location and
  task 72 City Win only as a locked code-less Victory event. Its event item is
  the completion condition, and slot-data version 2 names task 72 plus the
  five-relic threshold. The permissive scaffold makes the event immediately
  reachable; runtime goal reporting remains absent until Milestone 23.
- Mitigation: Keep the immediate event labeled non-playable and avoid release
  seeds until Standard finale logic and runtime goal reporting are accepted.
- Exit criteria: Generator, client, bridge, tests, and reconnect goal resend all
  use task 72 under `complete_city_win`.

### R-006 — AP ledger and native rewards can diverge

- Severity/status: **Critical / Open**
- Owner: OpenGOAL persistence/reward maintainer
- Risk: Native reward commands and save reconstruction may grant shuffled
  permanent items independently of Archipelago, or overwrite AP-delivered
  state. Replaying a native reward can duplicate effects; suppressing too much
  can break task closure/cutscenes.
- Current evidence: All 51 native reward nodes are source-audited, but no
  permanent-grant interception, `ap-applying-item` guard, or authoritative
  durable ledger exists.
- Mitigation: Intercept only audited permanent grants; leave task, dialogue,
  cutscene, and presentation behavior intact; reconcile native state from the
  AP ledger after every reconstruction boundary.
- Exit criteria: Every default item/reward passes first receipt, duplicate,
  cap, save/load, native reconstruction, replay, and closure tests.

### R-007 — Transient state can lose offline checks or replay position

- Severity/status: **Critical / Open**
- Owner: Client and persistence maintainers
- Risk: The bridge snapshot and client sets are transient. A disconnect, game
  crash, client restart, packet gap, or save switch can lose unsent checks or
  create ambiguous receipt state.
- Current evidence: Protocol 1's positional receipt/check paths are retired.
  Milestone 6 adds a checksummed schema-1 sidecar with one-time binding,
  per-index item states, explicit location IDs, pending outbox, atomic backup,
  quarantine, revision checks, and writer locking. These paths are automated
  only against opaque test save descriptors. Protocol 3 now adds a game-session
  nonce, monotonic command IDs, an eight-entry receipt ring, duplicate/conflict
  detection, and session-qualified persistence for the harmless test target.
  The client allocator now advances beyond explicit as well as automatic IDs,
  preventing the next automatic command from reusing an accepted or replayed
  explicit ID. Command IDs and payloads are bounded to the signed 32-bit GOAL
  receipt representation before Python reserves/transmits them and again
  before GOAL records or applies them, preventing truncation from corrupting
  deduplication or the high watermark.
  A live disposable-config smoke verified receipt discovery after client
  reconnect and a new nonce with stale-session rejection after game restart.
  It still requests no `ReceivedItems` and has no game check transport, so item
  replay and offline location outbox exit criteria remain open.
- Mitigation: Keep the Milestone 6 sidecar authoritative and add idempotent
  game/client acknowledgement and packet-gap handling before gameplay
  acceptance.
- Exit criteria: Duplicate, gap, reconnect, offline completion, both process
  restarts, new game, load, and goal-resend scenarios pass without lost or
  duplicated state.

### R-008 — Mission bootstrap and shadow state are absent

- Severity/status: **Critical / Open**
- Owner: OpenGOAL mission adapter maintainer
- Risk: AP-authorized missions may start with missing actors/loadouts/story
  flags, while naive grants can leak permanent inventory, complete checks, or
  inflate the AP relic count. Tasks 11, 27, 30, and 63 are explicit high-risk
  cases.
- Current evidence: Protocol 2 has no mission dispatch. The retired scaffold
  had only generic task dispatch; per-mission bootstrap, cleanup, lesson
  overlays, and separate shadow state do not exist.
- Mitigation: Use explicit mission profiles and distinguish permanent AP
  inventory, temporary bootstrap, and non-counting native story shadow state.
- Exit criteria: Every profile passes complete/fail/retry/abort/death/load and
  mid-overlay receipt tests, including all mandatory specification scenarios.

### R-009 — nREPL acknowledgement is not a compiler-error gate

- Severity/status: **High / Open**
- Owner: Client/startup maintainer
- Risk: `goalc` may accept an nREPL form while compiler output contains an
  error. The client can continue toward title or time out with an indirect
  message rather than immediately identifying the failed file/form.
- Current evidence: Protocol 2 compiled all 1,165 targets in the recorded
  OpenGOAL v0.3.5 runtime and produced command-specific hello/pong snapshots.
  A first live attempt exposed and rejected quoted snapshot strings even though
  nREPL acknowledged the GOAL forms; the corrected exporter then passed hello,
  duplicate ping, and next-ping checks. Milestone 7.2 measured a 26.736-second
  cold full `(mi)`, a 382.986-millisecond unchanged-source full `(mi)`, and a
  782.841-millisecond manifest-ordered bridge load. Those successful cases do
  not close the risk: the client still does not parse/classify full compiler
  output.
- Mitigation: Preserve sanitized `gk`/`goalc` output, require snapshot
  acknowledgement for protocol commands, record the source-set/module context
  in schema-1 diagnostics, and use `/diagnostics export` for a same-session
  checksummed bundle. Output now reaches the managed log through bounded pipes
  without an unbounded raw spool; missing/read-failed pipes and nREPL
  timeout/close failures have distinct events. Compiler classification remains
  future work.
- Exit criteria: Inject representative syntax, type, missing-file, and target
  attach failures; client fails promptly with source/form context and never
  claims readiness.

### R-010 — Process ownership and cleanup are incomplete

- Severity/status: **High / Open**
- Owner: Client/startup maintainer
- Risk: `gk`, `goalc`, or client windows can remain open after a test/client
  exit. Reusing an old process also prevents the current diagnostic session
  from capturing its earlier output.
- Current evidence: The client records which processes it starts but does not
  stop them on exit; old windows remained after a prior smoke test. Milestone
  7.1 now records a structured capture gap whenever a process predates the
  client, and the support bundle includes the gap list. Processes started by
  the client stream through bounded pipes, so a client-side raw spool cannot
  grow after exit; a pipe read failure is now retained as a capture gap instead
  of being indistinguishable from EOF. Milestone 7.2 then reproduced the
  user-visible boundary: after either a clean or unclean client-only exit, the
  existing game retained its nonce, native descriptor, receipts, and safe
  sidecar state, but a replacement official-v0.3.5 compiler/client could not
  attach. Restarting the game recovered safely with a new nonce. Child-process
  ownership and replacement-attachment policy therefore remain unresolved.
- Mitigation: Start tests with no stale process, record PIDs, and close only
  processes opened for that test using the maintained runbook. For the first
  release, recover a failed client-only reconnect by finishing native I/O and
  cleanly restarting the client, `gk`, and `goalc`; do not promise that the game
  can remain open on official v0.3.5 until the lifecycle is fixed.
- Exit criteria: Define user-facing ownership policy and implement/test clean
  normal exit, crash recovery, “leave game running” behavior if desired, and
  no termination of unrelated processes.

### R-011 — No connected-room gameplay acceptance

- Severity/status: **Critical / Open**
- Owner: Integration test maintainer
- Risk: Compile/title success can conceal failures in authentication, bridge
  binding, mission start, item application, check submission, save loading,
  HUD notices, replay, and goal reporting.
- Current evidence: The protocol-2 hello/ping completion gate passed without a
  room connection or gameplay action. An earlier protocol-1 smoke reached the
  normal title menu. No complete live multiworld scenario is recorded.
- Mitigation: Do not equate startup smoke with playability; capture paired logs
  and scenario metadata for every acceptance run.
- Exit criteria: A connected default seed passes the generation, item,
  location, bootstrap, persistence, full-accessibility, and HUD scenarios in
  [`development/verification-matrix.md`](development/verification-matrix.md).

### R-012 — Public ID and table compatibility enforcement

- Severity/status: **High / Watching**
- Owner: Protocol/release maintainer
- Risk: A future client/game path could accept slot data whose versions or
  registry hashes do not match the installed APWorld/GOAL integration.
- Current evidence: Milestone 4 defines literal first-release item/location
  records, mission/bootstrap/shadow identifiers, and an independent literal
  protocol-1 snapshot that marks every published ID as an exact retained
  semantic identity or a permanent reservation. Canonical UTF-8 JSON hashing,
  versioned slot data, and frozen item/location/mission/resolved-option hashes
  are present. Duplicate IDs/names, declaration reordering, reservation reuse,
  retained-concept mutation, scaffold/snapshot parity, task 36, task 72, task
  88, deterministic JSON, standalone defaults, and Python/GOAL constant parity
  are covered by tests. Slot-data version 2 exports the generated seed
  identifier. On `Connected`, Python validates the complete authenticated
  contract and canonical slot identity; schema-1 state rejects every recorded
  version/hash/options/design or binding mismatch read-only. GOAL mirrors the
  protocol-3 contract in its snapshot, and every mutating command carries the
  schema/table contract. Client startup now also requires that complete
  contract before reusing an already loaded bridge, preventing a matching
  headline protocol version from hiding stale schema/table code. An
  implementation-only runtime version detects older same-contract live code,
  even if corrected source is already on disk. A changed packaged source
  separately writes a durable pending-reload marker before source replacement,
  forcing an activation-attested live reload across client restarts and
  covering same-version bug-fix builds without resetting ordinary reconnects.
  The control and diagnostics modules export independent reload-persistent
  positive activation generations after successful initialization; Python
  requires both to differ in a current compatible snapshot before hello or
  marker removal. A mere nREPL completion response is insufficient. Python and
  GOAL reject protocol, integration,
  schema, slot-data,
  item, location, and mission mismatches with distinct stable codes before the
  harmless target can change. Explicit command-ID responses also advance the
  client allocator without weakening the game-side high watermark. Both sides
  also enforce the signed 32-bit width of command/receipt fields before any
  harmless mutation or receipt publication. GOAL additionally rejects every
  contract hash that is not exactly 64 characters before copying it into a
  comparison buffer, so a valid digest prefix plus trailing data cannot be
  accepted by truncation. No room
  gameplay data is consumed yet.
- Mitigation: Keep `legacy_ids.py` as the immutable protocol-1 compatibility
  input; use only `registry.py`, `versions.py`, and `slot_data.py` for future
  state or compatibility work. Retain Python's read-only rejection and add the
  audited GOAL/live-save compatibility boundary before gameplay begins.
- Exit criteria: Approve the final design registry and retired-ID policy,
  export its schema version and deterministic hashes, reject mismatches in the
  client/game handshake, and pass compatibility tests.

### R-013 — Early routing can be directionless or blocked

- Severity/status: **High / Open**
- Owner: Generator/logic maintainer
- Risk: The active static-pool scaffold intentionally implements neither
  required early guarantee. A Haven-first alternative is unsafe without
  Jetboard, and lack of local ranged access can stall later Standard branches.
- Current evidence: The specification requires local Spargus Field Orders and
  a local Blaster/Vulcan Fury in sphere zero. Milestone 5 removed the obsolete
  task-12 guarantee and leaves `local_early_items` empty by design.
- Mitigation: Retain the conservative Spargus-first rule until a Haven snapshot
  and actionable Jetboard placement are proven.
- Exit criteria: Default generation and 10,000-seed metrics prove one local,
  actionable route plus one local RANGED alternative and at least two early
  branches.

### R-014 — Currency balance and local-earned checks may contaminate each other

- Severity/status: **High / Open**
- Owner: Items/sanity maintainer
- Risk: AP-delivered Orb/Gem Packs must be spendable but must never advance
  local-world orb/gem check counters. Native kiosk/purchase costs can otherwise
  create grind locks or false checks.
- Current evidence: Milestone 5 generates the canonical currency-pack filler
  definitions and all 24 orb-threshold locations, with thresholds 325–600
  placement-excluded. Runtime balances, locally earned counters, and free
  side/purchase cost hooks remain absent.
- Mitigation: Maintain separate monotonic local-earned totals and AP balance;
  default costs are free and thresholds above 300 are placement-excluded.
- Exit criteria: Receipt, spending, native earning, replay, save/load, all 600
  orb thresholds, and free-cost scenarios pass without counter leakage.

### R-015 — OpenGOAL compatibility is pinned only informally

- Severity/status: **High / Open**
- Owner: OpenGOAL/release maintainer
- Risk: Decompiled types, task tables, startup forms, or runtime hooks may
  change across OpenGOAL versions. Auto-installing a bridge against an unknown
  project can fail compilation or, worse, compile against changed semantics.
- Current evidence: Compile, ordered bridge load, the 15-row live matrix, and
  the performance baseline used official OpenGOAL v0.3.5. Rows 3 and 4 exposed
  replacement-client attachment failure against a still-running game. Row 13
  exposed a separate native failure boundary: exclusive locks on the two
  disposable save-bank files caused `gk` to terminate with Windows exception
  `0xe06d7363` before an operator-requested save or graceful native diagnostic.
  The audited v0.3.5 path calls `read_binary_file` from `pc_update_card`, whose
  locked-file open failure throws an uncaught `runtime_error`. Native banks and
  AP revision stayed unchanged, and unlocked save/load recovered. The source
  audit checks structural tables, but no compatible commit/table hash is stored
  in the APWorld handshake.
- Mitigation: Log paths and bridge hashes, retain the source-table audit, keep
  locked-bank injection confined to backed-up disposable saves, and classify
  the native crash rather than attempting an AP-layer speculative workaround.
- Exit criteria: Define supported OpenGOAL version/commit range, include a
  deterministic compatibility/table hash, reject known-incompatible projects,
  and test every supported release.

### R-016 — Successful smoke log still contains `gk` error-level noise

- Severity/status: **Medium / Open**
- Owner: OpenGOAL/integration maintainer
- Risk: The recorded successful startup log contains 79 `[GK] [error]` lines.
  Most report duplicate textures; the remainder report a duplicate MIPS2C
  registration and reference patching. These may be known debug-load
  diagnostics, but treating every error-level line as a compile failure creates
  false alarms, while ignoring them wholesale can hide a real runtime problem.
- Current evidence: The same session contains zero `goalc` error-level lines,
  no matched nREPL/compiler-failure marker, a successful 1,165-target build,
  bridge verification, and a loaded title level.
- Mitigation: Keep sanitized lines in the paired log and distinguish process,
  subsystem, message, exit classification, capture gaps, and final readiness
  state in the structured timeline.
- Exit criteria: Classify each message against a clean unmodified Jak 3 debug
  launch on every supported OpenGOAL version; document an exact allowlist only
  for proven-benign messages and fail on any new/unexpected error signature.

### R-017 — Reference-tree contamination can corrupt source evidence

- Severity/status: **High / Watching**
- Owner: All development and automation maintainers
- Risk: Installing a bridge, compiling, formatting, running writing tests, or
  generating caches inside `jak-project`, `Archipelago`, or
  `openGOAL-decompile` changes the evidence used to audit the mod. A later
  source conclusion could unknowingly be based on project-modified input.
- Current evidence: The 2026-08-05 audit found an `archipelago.o` registration
  and untracked bridge inside `jak-project`; both were removed and Git is now
  clean at `425f143fc`. `Archipelago` is clean at `feab54da`.
  `openGOAL-decompile` has no Git baseline, so it can only be preserved as the
  supplied immutable snapshot. During the first Milestone 4 local APWorld run,
  importing the Archipelago reference refreshed ignored `__pycache__` files;
  no tracked source changed, but pre-run cache bytes were not baselined. The
  final 110-test evidence was therefore rerun from a disposable copy with
  `PYTHONDONTWRITEBYTECODE=1` and the APWorld installed only in that copy's
  `custom_worlds` directory.
- Mitigation: Enforce
  [`development/reference-source-policy.md`](development/reference-source-policy.md),
  use the active OpenGOAL installation for smoke tests, and use disposable
  copies for writing Archipelago tests.
- Exit criteria: Add a repeatable pre/post reference-integrity guard to normal
  development/test automation and document provenance or hashes for the
  decompile snapshot.

### R-018 — Standard placement controls can conflict with future guarantees

- Severity/status: **High / Open**
- Owner: Generator/options maintainer
- Risk: Standard Archipelago controls remain customizable and core-owned. The
  current resolver intentionally does not duplicate them, but the final Jak 3
  pool must still reject `start_inventory_from_pool` overcounts, incompatible
  local/non-local declarations, and placements that invalidate the required
  local early route or reliable-ranged guarantees.
- Current evidence: The resolved profile covers all 41 design-governed values;
  a test confirms that standard placement controls do not alter that profile.
  Milestone 5 generates the exact target pool but intentionally omits the two
  design early guarantees, so placement-control cross-validation cannot yet be
  accepted.
- Mitigation: Keep Archipelago core authoritative for generic placement data.
  In Milestone 12, derive a checked placement snapshot after mandatory pool
  selection and before the early prefill.
- Exit criteria: Generation tests reject pool overcounts and local/non-local
  conflicts, account correctly for precollected items, and prove the local
  route and RANGED guarantees under every supported placement-control case.

### R-019 — Live native-save identity and freshness provenance

- Severity/status: **High / Open**
- Owner: Client and OpenGOAL persistence maintainers
- Risk: The atomic sidecar can bind safely only if native save identity, slot,
  and fresh/unprogressed eligibility come from an audited live source. Guessing
  or deriving an unstable identity could bind the wrong save, allow a copied
  slot, or strand valid AP state.
- Current evidence: Protocol 3 wraps the audited native save/load methods with
  version-1 metadata tag 900 containing a canonical 128-bit UUID. It publishes
  identity only when the matching native auto-save process reaches its `done`
  code, invalidates the candidate on native `error`, and preserves its original
  save/load and state-code targets across bridge-only reloads. Missing/malformed
  metadata preserves native loading. Native tag error code/message state also
  survives bridge-only reloads and is cleared only by valid identity
  publication. Freshness is attested from the candidate
  save's serialized completion, collectible totals, and `task-list` complete
  bits for tasks 6-137 rather than the previously active game, then flips
  monotonically on live progress.
  The published identity/slot/eligibility descriptor now uses OpenGOAL's
  reload-persistent global pattern, while sidecar acknowledgement resets on
  reload. A successful matching native `done` now commits that descriptor to
  the reload-persistent globals before the wrapper returns; the observer keeps
  a guarded fallback, closing the prior done-to-next-snapshot reload window.
  The staged UUID, operation flags, eligibility, New Game marker, and exact
  auto-save handle are also reload-persistent, closing the earlier
  wrapper-to-`done` window while asynchronous memory-card I/O is pending.
  Save proposals are one-shot: game publication records a consumption
  acknowledgement independent of the live descriptor, rejects that UUID for
  the rest of the bridge session, and lets Python rotate even if invalidation
  or a save switch occurs before observation. Clean disconnect clears unused
  proposals, and a five-second real-clock lease fails closed after an unclean
  client exit. Authentication changes wake an
  immediate serialized heartbeat, so a newly authenticated player does not
  wait for the periodic ping before New Game identity entropy is armed. A
  reload-safe `game-info`
  initialization wrapper now invalidates the live descriptor and AP
  acknowledgement on every full no-save session, including the native
  `Continue Without Save` path. A one-shot marker armed only by a successful
  native New Game save preserves the ordinary save-first transition.
  Client acknowledgement now includes its exact native UUID and slot on every
  hello, ping, query, and harmless mutation. GOAL accepts loaded/bound only
  when that descriptor matches the live save and refreshes it again before a
  command safety check, preventing stale sidecar bits from transferring across
  a save switch or repository failure. If a manual reconnect reaches an
  incompatible bridge, the client now closes the existing state session
  uncleanly, releases its writer lease, and clears the sidecar acknowledgement
  before closing nREPL.
  Python binding/switch/copy rejection and source contracts are automated.
  Milestone 7.1 adds failure-isolated persistence events for path selection,
  lock, create/load/bind/close, revisioned commits, backup recovery,
  quarantine, typed rejection, and clean/unclean shutdown. Correlations hash
  native identities, seeds, and slot names; bundles exclude sidecar and native
  save contents.
  Python now writes a separate checksummed version-1 authorization record with
  each proposed UUID's authenticated seed/team/slot/name before the protocol
  can publish it. Live first binding requires an exact match when state is
  missing or unbound, so a crash followed by a room/slot switch cannot claim a
  UUID authorized by the prior slot. Existing bound sidecars continue to rely
  on their schema-1 binding, and the native tag remains metadata-only.
  Loaded-source reuse also requires the complete schema/table contract rather
  than only the headline protocol versions. An implementation-only runtime
  version rejects older live code even after source was already installed, and
  a changed packaged source records a durable forced-reload marker before
  replacement and clears it only after a current compatible snapshot proves
  that its reload-persistent activation generation changed. The proof happens
  before protocol hello, so an `(ml)` request that merely completes at the
  transport layer cannot admit the older running object. Same-contract bug
  fixes therefore cannot remain hidden across client restarts. The active
  OpenGOAL project compiles, and a double-reload runtime smoke passed all
  eight original-versus-installed hook assertions, and a later attached smoke
  preserved the descriptor across repeated reloads while rejecting an expired
  proposal and clearing one on disconnect. Milestone 7.2 exercised all 15
  mandatory rows with isolated state and disposable native slots. Twelve rows
  passed: fresh/repeated identity, game and ordered dual restarts, A to B to A
  switching, copied-slot and progressed-vanilla rejection, no-save clearing,
  distinct and overwritten New Game identity, harmless-command duplicate and
  no-op receipts, and title-menu safety. Descriptor-qualified acknowledgement
  prevented a false-safe save-switch interval. The three remaining failures
  are clean and unclean client-only replacement attachment (R-010) and the
  native locked-bank crash (R-015); neither published an incorrect identity or
  uncommitted AP revision.
- Mitigation: Keep Milestones 7 and 7.2 formally incomplete until all three
  mandatory failures pass. Never infer freshness from a missing sidecar or tag,
  preserve slot-copy rejection, and use the clean full-process restart policy
  as the operational fallback without weakening Protocol 3 semantics.
- Exit criteria: The real bridge supplies stable identity/slot/freshness across
  clean and crashed restarts; new, progressed, copied, deleted, restored, and
  switched native saves pass the documented policy without inventory changes.

## Risk update rules

When a code or specification change touches an active risk:

1. Link the exact automated/runtime evidence; do not close on code inspection
   alone when the exit criteria require real-game behavior.
2. Update
   [`development/specification-gap-matrix.md`](development/specification-gap-matrix.md)
   and [`development/verification-matrix.md`](development/verification-matrix.md)
   in the same change.
3. Preserve the original decision and evidence when closing a risk.
4. Add new unknowns here before weakening a rule or inventing behavior.
