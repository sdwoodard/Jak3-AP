# Jak 3 Archipelago risk register

This is the required home for conflicts, unknowns, and evidence gaps discovered
while implementing the normative design. Do not silently resolve a risk by
changing logic to match the retained pre-design-default scaffold.

Snapshot date: **2026-08-16**

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
  2 handshake-only until Milestone 13 replaces the region and rules with the
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
  reachable; runtime goal reporting remains absent until Milestone 24.
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
- Current evidence: Milestone 8 makes the schema-1 Python journal authoritative
  for Jetboard, Blaster stage 1, and Armor stage 1, and reconstructs those exact
  native targets after receipt/replay/restart boundaries. Both persistence-
  before-application crash windows and native target idempotence are automated.
  Milestone 10 adds one source-audited interception: task-16 node 36 must still
  contain exactly `add-jakc` then `add-armor-0`. Bound AP mode preserves Jak C,
  publishes reward location `743020036`, and omits only Armor 1. Unbound/AP-off,
  item-application guard, and command-shape mismatch paths preserve the complete
  native evaluator. Compatible durable task or reward observations reschedule
  ledger reconciliation after the associated native task-mask rebuild, even
  when the same target projection was previously confirmed. Independently,
  every bridge heartbeat exports the actual three-bit native target; Python
  compares it to the bound ledger and repairs any mismatch at the next safe
  opportunity. This closes event-free death/retry rebuilds after a location
  observation has already been acknowledged. While the audited reward shape is
  incompatible, a reward-owned control-plane safety hook exports native target
  `-1`, marks permanent reconciliation unsafe, and rejects stale or in-flight
  reconciliation commands before mutation. The native Armor fallback therefore
  remains intact across client/game restarts until the audited shape is restored.
  Persistent recovery emits one compatibility diagnostic per bound
  shape-mismatch episode, including after a pre-bind native replay. The same
  suspension predicate masks the permanent-item bit in GOAL runtime-safety
  diagnostics. Exact-source official-v0.3.5 compile and attached ordered load
  pass, but the
  live bound reward/save/death/replay matrix has not been completed. The
  remaining permanent reward table is still absent, so this risk remains open.
  Milestone 11 additionally confirms that native save/load directly restores
  features/items and that closed-task reconstruction replays reward commands.
  Seal/amulets, Launch, and the five viewer artifacts are outside the current
  three-item reconciliation slice. The ordinary-save spike proved an
  uncontained leak: `native_items` expanded from `2015` to `262143` and stayed
  there after reconciliation even though the bounded AP ledger contained only
  Jetboard (`ap_inventory_mask=1`). It also published
  `ap_checked_mask=255`. The original recorder incorrectly labeled successful
  procedure completion as PASS, and its immutable review lacked the complete
  lifecycle. Finalized successor `m11-native-reconstruction-e920e187` now
  captures all five typed checkpoints. Full game/client/compiler restart,
  two completed target-`1` reconciliations, and an index-zero replay all retain
  independently observed items `262143`, task-perm mask `4194303`, non-AP
  feature mask `571903997079846336`, and checked mask `255`. Its historical
  generic reward/item and mission/task duplicate fields are excluded from the
  proof; the independent expansion is already release-blocking. The server packet contained
  nine entries, but the bounded client ledger correctly retained only the
  original Jetboard and rejected the first leaked filler before mutation as
  outside the supported slice. Final `run.json` SHA-256 is
  `BB1349F151FFC5346C6264DE3781944BC02776BACF59A901FA185481567DF3F5`;
  complete bundle SHA-256 is
  `BEEB9DACC4EE27AB7E57D7376D87A287B67CB1EC84A6745C4899F58294040E39`.
  This is a complete release blocker, not a deferred source hypothesis. A
  later Jetboard-only successor proved exact native masks `0/1/3/2` and the
  direct Launch behavior gate, including at the task-30 tutorial. Raw bank
  inspection proved the ordinary save contained the complete pre-save feature
  value and mask `3`; native task/reward reconstruction subsequently reset the
  live mask to `0` because the synthetic state did not own task 29's closed
  reward node. The reconciliation-suspension sentinel remained active across
  ordinary load, so this was not an empty AP ledger clearing the feature.
  `Jetboard Launch` is also correctly outside the current Milestone 8 receipt
  slice; implementing it during the feasibility spike would have violated
  milestone scope. A later completeness review found that scoped successor
  `m11-jetboard-launch-review-ef8737dc` had incorrectly recorded `PASS`: its
  source run contained mask `0` and failed both required assertions after
  ordinary load and restart, while the review helper checked only that a numeric
  mask existed. The immutable review is superseded; source run
  `m11-jetboard-launch-3a1163b5` remains the accepted `BLOCKED` evidence until a
  complete successor proves mask `3` at both persistence boundaries.
- Mitigation: Intercept only audited permanent grants; leave task, dialogue,
  cutscene, and presentation behavior intact; reconcile native state from the
  AP ledger after every compatible reconstruction boundary and every
  heartbeat-observed native-target mismatch; suspend AP mutation while a native
  reward shape is incompatible. Milestone 14 is the primary remediation gate
  and must close the accepted Milestone 11 `BLOCKED` decision before it expands
  the permanent-item table. Milestone 17 completes reward interception and
  Milestone 25 repeats the full integration matrix; neither may waive the
  Milestone 14 reconstruction proof. Milestone 14 must also close the Jetboard
  persistence blocker before Launch can ship. The corrected feasibility gate uses five
  separately named checkpoints (`before_save`, `after_native_reload`,
  `after_game_restart`, `after_ap_reconcile`, and `after_item_replay`) and
  compares the repaired native permanent target to the bounded AP-ledger target,
  while independently requiring non-AP native features, rewards, native
  task/mission masks, and AP checks to remain equal to their pre-save controls.
- Exit criteria: Every default item/reward passes first receipt, duplicate,
  cap, save/load, native reconstruction, replay, and closure tests. A finalized
  Milestone 14 successor to `m11-native-reconstruction-e920e187` proves that a
  bounded AP ledger survives ordinary save/load and full restart without native
  inventory expansion or unexpected AP check publication.

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
  Milestone 8 now requests all `ReceivedItems`, validates each complete packet,
  durably commits the approved permanent slice before native application,
  handles exact duplicates/gaps/index-zero replacement, and retries pending
  target reconciliation after client/game/process recovery. Automated tests
  cover both crash windows. Milestone 10 observes real persistent completion for
  tasks 10–16 plus reward node 36 and uses a Python-owned exact-partitioned
  checked/confirmed/pending location state. Local bits and outbox entries commit
  before GOAL drain acknowledgement or `LocationChecks`; successful sends do
  not compact state, while validated `Connected` and `RoomUpdate` checked sets
  do. Offline/restart/replay/reconnect/rollback behavior and failure isolation
  are automated. The gated task-16 goal commits only with both task/reward bits,
  sends once per authenticated connection, and resends after reconnect/client
  restart. The current generated two-slot fixture passes Archipelago's real
  plando/fill pipeline with all items conserved; an earlier helper payload
  passed a real local-server transport smoke with the intended three runner
  receipts and five helper-owned placements. The bound-save
  native/server/live-goal matrix is not yet recorded. Other location families,
  canonical task-72 goal reporting, and remaining item domains are still absent,
  so the full exit criteria remain open.
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
  overlays, and separate shadow state do not exist. Milestone 11 source audit
  finds two specification-sensitive discrepancies: task 30's medallion scene
  opens `tpl-mardoor-4` without a Seal/amulet predicate, and task 63's viewer
  scene owns the telescope/time-map actors without reading the five artifact
  bits. These are strong candidates for scene-owned presentation instead of
  native item shadow grants. Task 30's source run proved exact masks
  `0/16/7/23` in one stable scene: the portal remained present/open, the
  presentation node remained closed, and AP relic/check state did not change.
  Its historical generic mission and reward fields were aliases of task-perm
  and inventory. Accepted successor `m11-task-30-shadow-87b40f81` repeated exact
  masks `0/16/7/23` with independent task/mission/reward masks `0/0/0`, portal
  `1/1`, node closed `1`, checksummed AP relic/check controls `0/0`, and
  unchanged save banks. Task-30 feasibility now passes; public native task
  closure and reward replay remain forbidden. Task 63's
  original controls were contaminated; a replay black-screened, a backed-up 1%
  slot loaded above lava, and ordinary Restart Mission returned to the same
  death loop. Later retries exposed unsafe scene cleanup/autosave behavior and
  a pre-activation artifact-write timing failure. The final successor used
  separate clean processes and an exact active-scene capture boundary. It
  observed artifact masks `0/1984`, scene `1/1`, telescope/time-map actor mask
  `12`, zero AP relics, unchanged AP checks, and unchanged save-bank hashes.
  Its historical generic mission and reward fields had the same aliases, so
  corrective review `m11-task-63-viewer-review-a98ab064` invalidated that old
  positive classification. Accepted successor
  `m11-task-63-viewer-7aa9d3b9` repeated the clear/set variants from separate
  clean processes and proved independent task/mission/reward masks `0/0/0`,
  checksummed AP relic/check controls `0/0`, and unchanged save banks. Its
  complete sanitized bundle SHA-256 is
  `513AF462C008D1C969853931F8DD6021791C6C6115C0590EE1E27125B57EF82E`.
  Task-63 feasibility now passes. Milestone 20 may consume both accepted
  feasibility inputs, but must still implement and verify their complete
  production lifecycles.
  The same audit proves both hidden R&C
  courses share `secrets.gungame-ratchet`, while purchase history is a separate
  bitfield. The accepted side-challenge successor proved hidden/open/reload/
  cleanup access states `0/1/1/0` while purchase history and AP checks remained
  unchanged. Production course-access and cost hooks remain deferred.
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
  output. Milestone 11 reproduced the issue when a typed door target was sent
  as a string: nREPL acknowledged the form while the managed compiler log
  contained a typecheck failure. The restricted spike runner now rejects a
  stage or capture if its bounded response or newly appended managed-log bytes
  contain a compilation, REPL, or typecheck marker. That test-only safeguard
  prevented the bad stage from becoming accepted evidence. A task-63 retry
  then showed that runtime pointer/method errors can arrive after the initial
  nREPL response and first log read. The runner now also checks those bounded
  markers during an asynchronous settle window. A later task-63 attempt
  dereferenced its scene actor array after spawn but before the scene's first
  game tick; the 1,063-byte query never acknowledged, the client lost its
  heartbeat, and the original `gk` process exited. The actor query now
  short-circuits unless Protocol 3 reports an active cutscene, and accepted
  task-63 captures require an exact mid-scene bridge boundary. These are test-only
  safeguards; they do not add compiler or runtime-error classification to the
  production client.
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
  stop them on exit; old windows remained after a prior smoke test. Milestone 7.1 now records a structured capture gap whenever a process predates the
  client, and the support bundle includes the gap list. Processes started by
  the client stream through bounded pipes, so a client-side raw spool cannot
  grow after exit; a pipe read failure is now retained as a capture gap instead
  of being indistinguishable from EOF. Milestone 7.2 then reproduced the
  user-visible boundary: after either a clean or unclean client-only exit, the
  existing game retained its nonce, native descriptor, receipts, and safe
  sidecar state, but a replacement official-v0.3.5 compiler/client could not
  attach. Restarting the game recovered safely with a new nonce. Child-process
  ownership and replacement-attachment policy therefore remain unresolved.
  Milestone 11 reproduced the adjacent attachment boundary: when the AP client
  already owns the target, a second nREPL connection can evaluate forms only if
  it skips `(lt)`; issuing another `(lt)` stalls for about 18 seconds. A stale
  compiler from an earlier session also prevented target advancement until the
  operator performed a coordinated client/`gk`/`goalc` restart. The restricted
  runner now permits attached-target reuse only with a fresh paired bridge
  snapshot and never treats the active project's stale startup snapshot as
  live evidence. The Jetboard successor additionally exposed two simultaneous
  local-server listeners. The operator believed the newly generated room on
  port 38282 was active, but the Jak 3 client log proved it had connected to an
  older canonical-default room on 38281; the 38282 server received no client.
  Save binding made an unnoticed port switch unsafe. Runtime records therefore
  need the authenticated endpoint and seed/archive identity, not only the
  displayed player name.
- Mitigation: Start tests with no stale process, record PIDs, and close only
  processes opened for that test using the maintained runbook. For the first
  release, the sole supported recovery after clean or unclean client/compiler
  loss is to finish native I/O and restart the client, `gk`, and `goalc`
  together. Warm replacement attachment on official v0.3.5 is unsupported. In
  the final Milestone 11 cleanup, a bulk `Stop-Process` hit a PowerShell
  null-reference race after stopping the owned launcher but before stopping the
  owned server. Exact-PID verification and a separate server stop completed
  cleanup; final process/port checks were empty. Cleanup tooling must therefore
  verify each owned PID after every attempted group stop rather than treating a
  partial command as an atomic shutdown.
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
  Milestone 11 used live `gk`/`goalc` targets, controller checkpoints, managed
  AP logs, backed-up disposable slots, checksummed bound AP state, and immutable
  support bundles. Its investigation is complete: Haven is terminal
  `SAFE FALLBACK`; task 30/task 63 are terminal `PASS`; Jetboard Launch,
  native reconstruction, 600 orbs, and the side matrix are terminal `BLOCKED`.
  Haven correlation `m11-haven-task-35-fc238cee` and side correlation
  `m11-side-challenges-15ecab70` supply the final missing provenance. The side
  run also reproduced reconstruction leakage on ordinary load, so its course
  rows correctly remained unrun. These are isolated feasibility decisions, not
  a complete connected default-seed mission room. Jetboard/reconstruction must
  pass Milestone 14, task-30/task-63 production profiles must pass Milestone 20,
  the complete side production matrix must pass Milestone 22 after
  reconstruction, and the preserved normal-mode 600-orb candidates must pass
  the Milestone 23 OpenGOAL lifecycle. The earlier non-fresh 38281 Jetboard
  room, contaminated/unsafe native saves, legacy unprovenance runs, and static
  PS2 save decoding remain explicitly excluded from full connected acceptance.
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
  positive activation generations after successful initialization. Control
  also resets separate items-, locations-, and reward-module activation bits;
  each ordered gameplay source sets only its own bit after installing its
  hooks and the reward source additionally installs its wrapper. Python
  requires both generations to differ and all three gameplay proofs to be
  active in a current compatible snapshot before hello or marker removal. A
  mere nREPL completion response is insufficient. Python and
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
  task-12 guarantee and leaves `local_early_items` empty by design. Milestone
  11 locks task 35's `mine-boss-resolution` parent and its `ctygenb-samos` /
  `sewl-elevator` continuations, and confirms that native debug/open helpers
  recursively close parent state. The independent snapshot could not preserve
  required actor/task state, so Milestone 11 activated the predefined
  convergence fallback: task 35 requires `Haven City Access + DONE(34) +
  Jetboard + RANGED`. Tiered mission order remains the default and tasks 14-34
  must never be synthesized.
- Mitigation: Retain the conservative Spargus-first guarantee and implement the
  documented Haven convergence only in its later mission-routing milestone.
- Exit criteria: Default generation and 10,000-seed metrics prove the local,
  actionable Spargus route, one local RANGED alternative, the Act-I Haven
  convergence, and both documented midgame branches.

### R-014 — Currency balance and local-earned checks may contaminate each other

- Severity/status: **High / Open**
- Owner: Items/sanity maintainer
- Risk: AP-delivered Orb/Gem Packs must be spendable but must never advance
  local-world orb/gem check counters. Native kiosk/purchase costs can otherwise
  create grind locks or false checks.
- Current evidence: Milestone 5 generates the canonical currency-pack filler
  definitions and all 24 orb-threshold locations, with thresholds 325–600
  placement-excluded. Runtime balances, locally earned counters, and free
  side/purchase cost hooks remain absent. Milestone 11 confirms the save fields
  for `skill`, `skill-total`, and `skill-high-watermark`, the native 600
  comparison, the burning-bush event-cost subtraction, and the separate shared
  R&C access/purchase bitfields. The accepted side-challenge successor proves
  typed zero-cost activation with no gem/reward/AP-check delta, durable kiosk
  activation, and course access `1` with purchase history `0` across ordinary
  save/load. It does **not** prove that a legitimate normal non-Hero save can
  earn and retain 600 orbs or that AP Orb Packs are excluded from local
  counters. Those orb runtime rows remain BLOCKED; no lower maximum or table
  fallback was invented.
  The only available 86% slot was non-Hero but reported postgame false and zero
  local orbs; UI completion percentage was therefore not a valid qualification
  control. Two PS2 archives supplied after that decision now provide qualifying
  static candidates. Read-only decoding verifies that MAX Drive UI slot 1 and
  CodeBreaker UI slot 1 both use NTSC-U `BASCUS-97330AYBABTU!`, pass native
  bank header/footer/checksum validation, record completion `100.0`,
  `skill-total=600.0`, `new-game=0`, and have the Hero Mode bit clear. Container
  SHA-256 values are respectively
  `969EDBE385D6454A71DE1C2B8D441444C0F9FE0C134325F57D8A1F10C46AA625`
  and `FEC7E7E6F18BFF2B79AB6E00368954B3AD708CD8AB04BE99CAC5CC67D139FFC7`.
  Their raw bank layout is directly readable by OpenGOAL, but neither has yet
  passed live postgame/source-family observation, save/load, full restart, or
  AP Orb Pack exclusion. The 600-orb decision therefore remains `BLOCKED`, but
  lack of a candidate save is no longer the blocker. Earlier side-challenge
  retries exposed and preserved two harness
  discrepancies: an untyped integer cost failed compilation, and synthetic
  prerequisite closure replayed an unrelated reflector reward. Exact typed
  and reward-isolated successor controls supersede those failures for the side-
  challenge decision without hiding them.
- Mitigation: Maintain separate monotonic local-earned totals and AP balance;
  default costs are free and thresholds above 300 are placement-excluded.
  Milestone 12 must reconcile its audited finite-source value against the
  Milestone 11 maximum question without changing the public table. Milestone 23
  must then produce the finalized normal non-Hero postgame successor and apply
  the predefined highest-proven-multiple-of-25 fallback if 600 is disproved;
  Milestone 25 repeats the persistence and AP-pack isolation matrix.
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
- Mitigation: Log paths and bridge hashes, retain the source-table audit, and
  classify the native crash rather than attempting an AP-layer speculative
  workaround. External locking, replacement, or editing of native save banks
  is unsupported upstream interference and is excluded from the supported
  acceptance matrix; exercise ordinary unlocked save/load recovery instead.
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
  In Milestone 13, derive a checked placement snapshot after mandatory pool
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
  that its reload-persistent activation generations changed and the ordered
  items, locations, and reward modules installed their activation proofs. The
  complete proof happens before protocol hello, so an `(ml)` request that
  merely completes at the transport layer cannot admit a runtime missing any
  vertical-slice dependency. Same-contract bug fixes therefore cannot remain
  hidden across client restarts. The active
  OpenGOAL project compiles, and a double-reload runtime smoke passed all
  eight original-versus-installed hook assertions, and a later attached smoke
  preserved the descriptor across repeated reloads while rejecting an expired
  proposal and clearing one on disconnect. Milestone 7.2 exercised all 15
  historical rows with isolated state and disposable native slots. Twelve rows
  passed: fresh/repeated identity, game and ordered dual restarts, A to B to A
  switching, copied-slot and progressed-vanilla rejection, no-save clearing,
  distinct and overwritten New Game identity, harmless-command duplicate and
  no-op receipts, and title-menu safety. Descriptor-qualified acknowledgement
  prevented a false-safe save-switch interval. The three historical failures
  are clean and unclean client-only replacement attachment (R-010) and the
  native locked-bank crash (R-015); neither published an incorrect identity or
  uncommitted AP revision. The approved first-release policy excludes warm
  replacement attachment and external bank interference. Replacement clean and
  unclean full-process recovery both passed with new nonces, empty receipt
  rings, exact descriptor/sidecar rebinding, and no premature safe state. An
  ordinary unlocked save/load also passed. The revised supported result is
  14/14, so Milestones 7 and 7.2 are complete while R-010 and R-015 remain open
  for broader upstream lifecycle and compatibility work.
- Mitigation: Never infer freshness from a missing sidecar or tag, preserve
  slot-copy rejection, and require a complete client/`gk`/`goalc` restart after
  client or compiler loss. Treat external native-bank locking, replacement, or
  editing as unsupported without weakening Protocol 3 semantics.
- Exit criteria: The real bridge supplies stable identity/slot/freshness across
  clean and crashed restarts; new, progressed, copied, deleted, restored, and
  switched native saves pass the documented policy without inventory changes.

### R-020 — Regional/individual Precursor Orb identity and logic are unproven

- Severity/status: **High / Open**
- Owner: APWorld collectible-data and OpenGOAL location maintainers
- Risk: A total of 600 does not provide stable per-source identity, value,
  region, persistence, or access logic. Enabling regional/individual orbsanity
  from coordinates, actor addresses, or a generated order could change IDs
  across builds, duplicate multi-orb containers, create replayable checks, or
  place progression behind an unreachable source.
- Current evidence: The first-release registry contains only 24 global
  25-orb thresholds. Source contains a 600 comparison, but Milestone 11 could
  not runtime-prove that maximum on a legitimate normal non-Hero save. The
  audit also does not prove a complete source table. Upstream OpenGOAL tracking
  code distinguishes standalone `skill` actors and orb-bearing containers
  through persistent entity state, and documents one two-orb container plus one
  golden triple-orb container. That makes a finite source catalog feasible but
  also proves that one source is not necessarily one orb unit.
- Mitigation: Complete Milestone 12 before Milestone 13. Build a deterministic
  candidate catalog with source-derived identity, value, region, persistence,
  and access evidence; use it for global-threshold reachability but do not assign
  public IDs. Promote only accepted sources through Milestones 28, 30, and 31 with an
  explicit location-table/hash/migration decision. Initial individual-source
  placement is `EXCLUDED` under the safe policy.
- Exit criteria: The accepted catalog reconciles to the proven normal-save orb
  maximum, every source has unique stable identity/value/region/access evidence,
  default threshold logic is source-aware, and any enabled regional/individual
  mode passes exact-count, persistence, all-state, fuzzing, and runtime tests.

### R-021 — Skull Gem sanity lacks a finite source and cap contract

- Severity/status: **High / Open**
- Owner: APWorld option/logic and OpenGOAL collectible maintainers
- Risk: Ordinary Skull Gem enemy drops are repeatable, while the current
  `skull_gem_bundle_size` does not define a finite maximum. Enabling cumulative
  milestones without a cap could create an undefined or grind-dependent
  location family; treating enemy drops as individual checks would violate the
  finite/idempotent location invariant.
- Current evidence: The canonical design keeps `skull_gem_sanity: off`, rejects
  repeatable drops as locations, and documents only future cumulative,
  purchase, union, and conditional static modes. No complete non-respawning
  static-gem table or finite cumulative cap is frozen.
- Mitigation: Milestone 12 classifies every source family and audits purchase
  persistence. Milestone 28 adds explicit finite milestone and progression
  caps with versioned table/slot/state behavior. Milestone 32 implements
  cumulative milestones and secret purchases; the recommended initial
  progression cap is zero. Milestone 33 implements individual static gems only
  if a complete independently persistent table is proven, otherwise the mode
  remains rejected and IDs are reserved.
- Exit criteria: Every enabled Skull Gem mode has a finite exact location count,
  stable IDs where applicable, clear progression placement, AP-pack isolation,
  save/replay persistence, all-state logic, and runtime acceptance. Repeatable
  enemy drops never become individual locations.

### R-022 — Feasibility controls and save labels can misclassify runtime state

- Severity/status: **High / Open**
- Owner: Runtime feasibility and integration test maintainer
- Risk: A plausible UI label, successful GOAL form, or manually asserted
  behavior can be mistaken for an independent control. This can produce a
  false PASS while native inventory/task state is already saturated or the
  scene is unstable.
- Current evidence: Milestone 11 found multiple distinct control failures. The
  original task-30 `none/seal/amulets/all` variants all captured mask `19`
  because no live preparations were recorded. Successor retries then exposed
  three independent harness/staging problems without being misclassified as
  PASS: an internal node method did not produce the required scene state; a
  string-typed door target produced a compiler error despite nREPL
  acknowledgement; and public task-node closure replayed broad native state,
  producing mission mask `65535`, native items `235547`, task-30 mask `19`, and
  a Launch-only bit. Ordinary reload discarded that unsaved contaminated state.
  The final successor used only the scene continue, a direct closed flag on the
  named presentation node, and a typed event to the named door process. It
  passed exact masks `0/16/7/23` with portal `1/1`, node closed `1`, zero
  mission/task masks and AP relics, and an unchanged bounded AP check mask; the
  door opened on game ticks without player movement. Task 63's first successor
  later rejected a delayed `call_method_of_type`/invalid-pointer error caused
  by returning a spawned process as the nREPL value. It also found that the old
  preset enabled a debug-scene flag capable of opening native task state. No
  checkpoint was accepted; the preset now returns `none`, leaves debug mode
  off, requires registered scene identity, and polls the managed log for
  delayed runtime errors. The spawned scene nevertheless survived the
  requested ordinary UI-slot load, immediately ran the telescope cutscene,
  entered the Dark Maker robot, and completed through the source-owned autosave
  path. Readback showed native items/reward mask `262143`, mission/task masks
  `4194303`, artifact mask `1984`, task-30 mask/node `23/1`, and Jetboard mask
  `3`; active `bank4.bin` changed to SHA-256
  `E6CF384A92517BA4BDA152743DFB5D851B7159EA3476176A5BF22F04069A4263`.
  This was a harness cleanup failure, not an operator load/save mistake.
  Ordinary load is therefore forbidden as cleanup while a spawned
  `scene-player` remains. Audited `scene.gc` also proves the native `abort`
  event enters `release`, whose `scf4` path still autosaves. A direct viewer
  scene deactivation/setting-reset attempt later failed to acknowledge and
  terminated `gk`, so that cleanup path is also prohibited and its presets
  were removed. Task-63 variants now use a full paused process close with no
  load/save, followed by process-exit and unchanged-bank verification. A
  subsequent successor also proved that
  probing declarative scene-actor handles before `scene-player` receives its
  first game tick can terminate `gk`; no checkpoint or save write occurred,
  and the failure is preserved as a separate immutable bundle. The query and
  checkpoint gate now require the exact active-cutscene boundary. A later exact
  artifact-set attempt applied mask `1984` before scene activation, but the
  active-scene capture read mask `0`; the operator, endpoint, slot, and bridge
  boundary were all correct. That correlation was finalized `BLOCKED` rather
  than overwritten. A capture-only successor then applied the five allowlisted
  bits after the scene was active and paused and atomically captured exact mask
  `1984`, actor mask `12`, AP relic count `0`, and unchanged AP check mask. This
  proves a harness staging-order discrepancy; future shadow-profile work must
  set and verify the profile at its actual lifecycle boundary rather than
  assuming a pre-scene synthetic write survives activation. The older clear run
  captured all native item bits and artifact mask `1984`; an 86% slot was
  neither postgame nor orb-progressed; and a 1% slot was actually
  task 63 at an unrecoverable lava checkpoint. Task-63 replay also produced a
  black screen. Restart Mission did not recover the lava loop. The old
  side-cost form failed typed compilation while the UI continued to show
  eight gems. Raw compiler logs and the active project's startup snapshot were
  stale evidence paths; the managed AP log and session-matched temporary
  snapshot were authoritative. Finally, the original reconstruction run
  equated command completion with PASS despite `2015 -> 262143` native-item
  expansion and eight leaked checks. During the Jetboard successor, the first
  base-only operator checkpoint was invalid because production reconciliation
  from an empty ledger cleared the staged native bit after exact capture; that
  correlation was finalized `BLOCKED` rather than edited. The retry suspended
  reconciliation and proved exact masks/behavior. Ordinary save/load and full
  restart both read runtime mask `0`; raw bank inspection proved the save had
  contained mask `3`, isolating native task/reward reconstruction rather than
  operator save selection or serialization as the cause. A scoped immutable
  review then incorrectly recorded semantic `PASS` by ignoring the failed
  persistence assertions; it is now superseded and the full spike remains
  `BLOCKED`. The
  intended fresh
  room on port 38282 was never connected: the client was bound to a different
  canonical-default room on 38281 whose existing nine-item history caused the
  attempted base receipt to arrive at index 9 while durable state expected
  index 0; Launch was rejected as outside the current receipt slice. Those
  receipt failures were recorded and were not reinterpreted as successful AP
  reconstruction. The first side-challenge successor later proved a real
  zero-cost prompt and activation with zero Skull Gem or AP-check delta, but
  its synthetic closed prerequisite caused the next native task update to run
  command index `0x3a` and grant `artifact-av-reflector` (`items 0 -> 128`).
  That run was finalized `BLOCKED` and bundled rather than accepted. The
  bounded retry now requires native item/reward masks to stay zero and
  temporarily suppresses only that exact prerequisite command after verifying
  index/count `0x3a/1` and an absent reflector bit. This is test-only isolation
  for a disposable clean save, not a production shadow-state implementation.
  The corrected retry subsequently passed zero-cost activation without that
  reward leak and ordinary save/load preserved the exact kiosk entity-permanent
  activation flag (`1`), zero displayed cost, and zero Skull Gems. The operator
  correctly observed that the in-progress challenge HUD did not resume and the
  save loaded its ordinary task `7`/node `4` in a vehicle. Source shows that the
  native save serializes task-node closed bits and a resetter node, not the live
  task-manager/HUD session, so the reload capture now uses a distinct read-only
  boundary rather than falsely requiring active task `137`/node `409`. That
  same reload independently reproduced the existing reconstruction leak with
  native items/reward `243803`, mission/task masks `4194303`, task-30 mask `19`,
  and Jetboard mask `3`; it remains release-blocking and is not reclassified as
  a side-cost failure. The same successor then proved shared course access and
  purchase history are independent: hidden `0/0`, shadow-open `1/0`, ordinary-
  reload `1/0`, and cleanup `0/0`, with native access bit `4194304`, full
  purchase history zero, zero gems, and stable AP check/relic controls `255/0`.
  It originally finalized `PASS` as `m11-side-challenges-bc09ed7c`; final `run.json`
  SHA-256 is
  `BFF6596C544F5E7F1A1D5F7C5F5B7D9FA7CCEDA7E97B9D00AC6B882C5DF7115C`
  and complete bundle SHA-256 is
  `C9B515B7D6CB32639C3EFD27119DC5111F8E3B5A728E7F329233BBC59E0C6970`.
  Its behavioral observations remain useful, but a later provenance audit
  found zero checkpoint snapshots and no snapshot-use ledger. The `PASS` is
  therefore superseded until a live successor repeats all seven checkpoints.
  Native reconstruction and the missing qualifying
  600-orb control remain separate open release risks.
  The clean Haven evidence refresh then found, before any mutation, that the
  runner's clean-start relocation gate was hard-coded to native slot 2 while a
  newly created disposable UI slot 4 correctly reported native slot 3. The
  gate now receives the run-owned slot for every evidence-bound stage/capture,
  rejects a mismatched loaded slot, and permits the Haven candidate only as a
  continue-only clean-start relocation. This was a harness defect, not a game
  or operator failure; the slot-4 banks were backed up before proceeding.
  Finalized successor `m11-haven-task-35-95ab560f` then captured identical
  `before_entry` and `mission_start` controls: task/mission/item/reward/
  Jetboard/AP masks `0`, loaded-level mask `7`, passage mask `1`, and actor mask
  `0`. The operator confirmed playable geometry with Samos and Keira absent.
  A final review found that this runner revision computed `native_act=2` from
  the active `ctygenb`/sewer level cohort, making that field tautological rather
  than task-derived Act-II proof. The immutable artifact is not rewritten and
  the conservative fallback remains supported by the missing-actor and zero-
  task controls; future capture now reads bridge `current-act` directly, and
  Milestone 18 must prove real `current_act=2` after natural Act-I completion.
  Final `run.json` SHA-256 is
  `2E8649B2E052528A5D4C8472308B26819564A88D0E5658F20DDD8A3C34E2C2BD`;
  complete sanitized bundle SHA-256 is
  `336C9E9CA03BE0B4C9771076536CFFF5E58BFB0B6A6584FC944DE269D3279562`.
  Its actor-failure observations support retaining the predefined convergence
  fallback provisionally, but a later provenance audit found zero checkpoint
  snapshots and no snapshot-use ledger. The `SAFE FALLBACK` disposition is
  superseded until a live two-checkpoint successor satisfies the final contract;
  the fallback remains neither a runtime feature nor release acceptance.
  The following clean Jetboard successor preflight then found a second
  runner-only classification defect before any GOAL form was sent. UI slot 4
  was correctly loaded as native slot 3 at `wasstada`, task 10/node 8, with
  `safe_to_apply_permanent_item=1` but `safe_to_mutate_mission_state=0`; the
  runner had incorrectly required the latter for the four feature-only
  Jetboard controls. The controls now use the permanent-item boundary, while
  task-30 variants retain the mission-state boundary after a separate
  continue-only clean-start relocation. Both paths retain run-owned-slot and
  common unsafe-state validation. Focused runner coverage passes `47`, with
  Ruff lint/format and mypy also green. This was a harness defect rather than
  an operator or native-game failure, and no save or runtime mutation occurred
  before its correction.
  At the first mask-`0` controller check, the operator then observed the exact
  expected absence of both board deployment and charged Launch. Its first
  capture attempt nevertheless stopped before mutation because a runner-staged
  reconciliation suspension intentionally exports permanent-item safety `0`
  and native target `-1`; the preflight initially recognized only the ordinary
  unsuspended boundary. Capture now accepts that exact state only when the same
  run's latest recorded preparation owns the same Jetboard preset/checkpoint.
  Unowned suspension and every existing slot/transition/death/vehicle mismatch
  remain rejected. Focused coverage remains `47` with Ruff and mypy green. This
  was another evidence-handoff defect, not a failed native control or incorrect
  operator action, and the rejected capture wrote no checkpoint.
  During the following base-only control, the operator successfully deployed,
  moved, and jumped the board and confirmed charged Launch remained absent.
  An accidental death after that completed check returned to the clean-start
  checkpoint and removed the directly staged board. The stable respawn had no
  active death/restart/transition flag; the runner atomically reapplied the same
  preset and captured exact mask `1`. This post-check retry behavior is retained
  as diagnostic evidence that a direct synthetic grant is not a durable AP
  receipt. It neither invalidates the already observed in-memory semantic
  control nor satisfies the later ledger-backed persistence rows.
  After the accepted task-30 base-only capture, its named return continue still
  published `level_transition=1` because the operator had remained paused. The
  following positive-control stage was rejected before mutation. The run must
  allow that transition to settle before retry; this is a correctly detected
  staging-sequence boundary, not a failed Launch control.
  The first ledger-backed persistence retry then proved its written bank
  contained the full mask-`3` feature value at all four redundant offsets, and
  the authenticated room supplied AP base target `1`; nevertheless the load
  restored runtime mask `0`. This correlation is invalid as a native
  persistence verdict because the test-only reconciliation suspension had not
  been restored before load, deliberately preventing the AP base reconciler.
  It is preserved as finalized correlation `m11-jetboard-launch-5b7a791b`,
  `run.json` SHA-256
  `946635A3A4C865FE9E0F68FF67604C9112AFDC38E049E7C2FE26B34C387DC210`,
  bundle SHA-256
  `165034EA9951C49C4394F5AAB14BB23212F826735289AE1EC194F09354B3ADD6`.
  A stage-only preset now restores the production reconciliation hook at the
  exact run-owned suspended boundary and is forbidden from capturing a
  checkpoint. The successor must use it before load. The same finalization also
  exposed that standalone bundling depended on an ambient Archipelago
  `PYTHONPATH`; the runner now adds its pinned dependency root without loading
  the world registry. Focused coverage passes `48`, with Ruff and mypy green.
  Corrected persistence successor `m11-jetboard-launch-2e22a7b0` then restored
  production reconciliation before repeating the same ordinary load. The
  operator could deploy the Jetboard but not charge Launch; exact readback was
  native mask `1` and permanent target `1`, with base ownership passing and
  Launch reconstruction failing. Its `run.json` SHA-256 is
  `DFFEB15129266802C87BCC3B6F271943D2421D00AE3657B492B563BFA19F33FA`
  and bundle SHA-256 is
  `35AD2E9DE7CE00691EF44D540A7740AEA26FC7A1883BAC2CA755FDF42F711110`.
  This replaces mask `0` as the best isolated persistence evidence: the AP
  ledger reconstructs base Jetboard correctly, while Launch remains outside
  the supported receipt/application slice. No production source change caused
  the difference; the test boundary changed from suspended synthetic state to
  active production reconciliation.
  The first five-checkpoint native-reconstruction successor then exposed a
  recorder-only omission before any ordinary save: live capture queried all
  native fields but did not require the AP inventory mask, ledger revision, or
  checked mask until final review. Correlation
  `m11-native-reconstruction-9e7c7111` was finalized `BLOCKED` and bundled as
  incomplete evidence (bundle SHA-256
  `17FBA917F6C5D52E22C32D467EEFAEB6C7A6FBDD1BA48DA5668416BC944C2C91`).
  The runner now derives those three values from the checksummed persistent AP
  state, verifies its native slot and save identity against the live bridge,
  rejects unknown bounded-slice checks and manual substitution, and refuses an
  incomplete reconstruction checkpoint before writing it. Focused coverage
  passes `50`. Its first live checksum attempt also correctly refused to write
  a checkpoint but revealed that the new reader had omitted the canonical JSON
  trailing newline; the production state was valid, the reader was corrected,
  and an exact-byte regression test now covers that contract. Neither issue was
  an operator or native-game failure. Successor
  `m11-native-reconstruction-e920e187` subsequently accepted its exact
  pre-save control (AP target `1`, checked mask `128`, native items/reward
  `2015`, mission/task masks `0`) and independently verified the ordinary save
  by a changed native-bank hash. Ordinary reload of the same bound native slot
  reproduced the release-blocking expansion: items/reward `262143`,
  mission/task masks `4194303`, checked mask `255`, and non-AP feature mask
  `571903997079846336`, while the AP inventory target remained `1`. The live
  bridge showed the exact save identity, on-foot paused-safe state, and no
  cutscene/death/restart/transition; a single enemy hit before pause was
  incidental and cannot explain the deterministic saved-state expansion. The
  server then accepted all eight leaked checks and queued eight rewards beyond
  the original Jetboard receipt. The client was closed before ingesting them,
  leaving a deliberately preserved boundary where the server owns a nine-item
  canonical history but the checksummed client state still owns one receipt and
  all eight check bits. Reconnect/replay must treat that difference as evidence
  of the leak, not as a clean-room or operator-delivery failure. The paired
  server save and client-state snapshot were copied before restart with
  SHA-256 values
  `61B49687E140191C117F755C9ED7B40E978AE5DDC80528E5FE32E40B7FCB0ED1`
  and
  `A6EDAC1A873ED96A50178A822C035D0B81D7D67A3580BEAC98F7CC78B14AFC6A`.
  A clean managed relaunch and ordinary load of that same slot then captured
  `after_game_restart`: items/rewards remained `262143`, mission/task masks
  remained `4194303`, checked mask remained `255`, and non-AP features remained
  `571903997079846336`, despite bounded AP permanent target `1`. The exact
  bridge slot/identity and safe runtime flags exclude the repeated enemy hit,
  absent item popups, or operator slot choice as explanations. Full process
  restart therefore reproduces rather than repairs the leak.
  The final Milestone 11 completeness review found seven additional
  false-acceptance paths in the recorder and evidence contract. First,
  `native_reward_mask` was not a reward observation: it repeated the full
  native inventory value. Task-30 item/reward pairs were consequently
  `0/0`, `16/16`, `7/7`, and `23/23`, and the task-63 set pair was
  `1984/1984`. Second, `native_mission_mask` repeated the task-perm mask rather
  than inspecting mission nodes. The corrected live query now independently
  measures task-perm completion for tasks 14-72, closed `close-task` nodes in
  `sub-task-list`, and a bounded ten-node audited reward set. Immutable
  corrective reviews `m11-task-30-shadow-review-fb327917` and
  `m11-task-63-viewer-review-a98ab064` therefore supersede the old positive
  classifications as `BLOCKED`; their complete bundle SHA-256 values are
  `8FC9E7125E6325E7269D3053E9D69CAC4924278DD5D7E1107EACB1BF62686009`
  and
  `D9D1D9F9899B13C2D2B9283908EC6B03AC81F5585BB1987542BF9843D0D5C507`.
  The Haven fallback remains supported by its independent task-perm and actor
  failure, but its historical mission/reward duplicates are excluded and must
  be recaptured by Milestones 18/19. The native reconstruction blocker also
  remains conclusive from independent item, task-perm, non-AP-feature, and
  AP-check expansion; its duplicate generic fields are excluded. The side-
  challenge PASS rests on side-specific node, suppression, cost, gem, item,
  purchase, and AP controls, while Milestone 22 must repeat the corrected
  generic reward observation.
  Third, one fresh bridge file could be reused for multiple stage/capture
  boundaries because age and slot checks did not prove a new observation. The
  runner now hashes every snapshot, records its revision/slot/age, and rejects
  reuse of a hash/revision pair within the run before sending a staging form or
  writing a checkpoint. Fourth, `finish` made the proposed feasibility decision
  terminal before support-bundle export. It now records
  `finalized_pending_bundle`; only a complete hashed bundle promotes the run to
  `pass`, `safe_fallback`, or `blocked`, while a partial bundle becomes
  non-accepting `bundle_incomplete`. Fifth, the side-challenge reload gate did
  not require the whole zero-cost/resource/AP control set. It now repeats cost,
  gems, items, purchase history, AP checks/relics, marker/event/suppression, and
  activation fields. Sixth, the orb source-family gate checked only presence.
  Each value must now be an integer, non-negative, at most 600, and the four
  values must sum to the locally earned total. Seventh, a reconstruction review
  could accept a typed five-checkpoint lifecycle that contained no leak. It now
  requires the source decision to be terminal `BLOCKED` and requires at least
  one automatically derived decision blocker. Regression tests construct each
  former false-acceptance shape and prove rejection.
  When the corrected task-30 successor was opened on a fresh native-slot-3
  save, its first continue-only `task30_scene_stage` attempt was rejected before
  sending GOAL because that preset was missing from the clean-start relocation
  allowlist and therefore incorrectly required mission-state safety at the
  initial-save boundary. The preset now uses the same restricted clean-start
  classification as its source-identical Jetboard task-30 relocation; common
  unsafe-state and run-owned-slot checks remain mandatory. A focused regression
  assertion covers the classification, all 64 runner tests pass, and the two
  active save-bank hashes were unchanged after rejection. This was a recorder
  setup defect, not an operator or native-game failure.
  At the next task-30 boundary, the exact mask-`0` native query passed but the
  checkpoint lacked required AP relic/check fields because live shadow capture
  did not require the checksummed AP state. Testing stopped before a positive
  variant. The incomplete correlation was finalized and bundled as
  `m11-task-30-shadow-8a041a4e` (bundle SHA-256
  `7AC4E4F13E3126276F206F468F07D96EB9802561FC759302C04A1F5A16B96CA8`)
  rather than being edited. Live task-30/task-63 captures now require a
  same-slot/same-identity checksummed state before mutation and automatically
  derive the bounded checked mask plus the count of the seven explicit AP
  finale-relic receipt IDs; manual substitution is rejected. All 64 focused
  runner tests pass. This was another recorder-input defect, not an operator or
  native-game failure, and the protected save hashes remained unchanged.
  The following successor produced exact mask-`0` native and checksummed AP
  controls, but the invocation omitted the required procedure assertions. The
  runner had allowed a non-terminal live evidence write, so testing stopped
  again before a positive mask. Correlation `m11-task-30-shadow-81aba654` was
  finalized and bundled (bundle SHA-256
  `452FE4E17EF2A743F1D635FD06E584B27A2C27491B2392BF76E775C5A342FABB`)
  rather than edited. Live shadow capture now rejects missing procedure
  assertions before mutation. Final successor `m11-task-30-shadow-87b40f81`
  passed every exact numeric and procedure control with unique snapshots and
  unchanged save banks; its bundle SHA-256 is
  `3A5D265D2589AD7D524A6BC51A788744B724FED2D75A29FE0AB895A7462FF7E5`.
  This closes the task-30 independent-isolation discrepancy while leaving its
  production lifecycle in Milestone 20.
  Task-63 successor `m11-task-63-viewer-7aa9d3b9` then used separate clean
  processes for the clear and set variants and applied the set mask only at the
  exact active-scene capture boundary. It proved artifact masks `0/1984`, scene
  state `1/1`, telescope/time-map actor mask `12`, independent
  task/mission/reward masks `0/0/0`, checksummed AP relic/check controls `0/0`,
  and unchanged protected save-bank hashes. Its final `run.json` SHA-256 is
  `CBD252352B5537E024AF2EF9351FC68955A36B862023658BE6038968B03E83CD`;
  complete bundle SHA-256 is
  `513AF462C008D1C969853931F8DD6021791C6C6115C0590EE1E27125B57EF82E`.
  This closes the task-63 independent-isolation discrepancy while leaving its
  production lifecycle in Milestone 20.
  The final acceptance audit then found that the runner could finalize a
  manually populated `live=False` matrix as `PASS`, and that positive reviews
  did not require or preserve a complete provenance ledger. The runner now
  treats missing, duplicate, stale, wrong-slot, mismatched, or synthetic
  provenance as a positive-decision blocker and copies/revalidates the ledger
  in positive successor reviews. This automated fix cannot retrofit immutable
  artifacts; Haven and side challenges need new correlation IDs.
  The first 2026-08-21 Haven provenance successor exposed a second acceptance-
  input omission: live Haven and side-challenge captures required AP controls
  at decision time but were not routed through the checksummed AP-state reader.
  `m11-haven-task-35-b3c3d40f` therefore preserved valid native/missing-actor
  evidence but omitted `ap_inventory_mask` and `ap_checked_mask`; it was
  finalized `BLOCKED` and bundled at SHA-256
  `8B6CB3BB17DDE5FE0D119045379335532DE0C4A16CD216EBF9508F3039C3953A`
  rather than edited. The runner now requires same-slot/same-identity
  checksummed AP state for both pending spikes, rejects manual substitution,
  and derives their exact required fields before writing a live checkpoint.
  All 66 focused runner tests pass. Fresh successor correlations remain required
  because the incomplete artifact is immutable.
  The first side-challenge provenance successor then exposed an ordering hole:
  the runner allowed the native task-counter refresh immediately after clean
  relocation, before the guarded parent reward was suppressed, the child intro
  node was opened, and the marker continue was re-entered. The actor remained
  available but unresolved (`available/event/cost/activation = 1/0/0/0`) after
  an operator settle, so the zero was correctly rejected as a default rather
  than accepted as free-cost evidence. Correlation
  `m11-side-challenges-d429b84e` was finalized `BLOCKED`; final `run.json`
  SHA-256 is
  `EC7AA73CEA3C4F6CCE8C3452677F508F90809B094B6E20B8AC06FE0C7707E1BE`
  and complete bundle SHA-256 is
  `72540634FE3013F126872620C6E36F3FB51D3EB93D4B72BA9B15540B32177989`.
  The runner now enforces the exact five-stage initialization prefix before
  mutation and all 67 focused tests pass. This was a harness-order defect, not
  an operator or native-cost failure; a fresh successor is still required.
  Provenance-complete Haven successor `m11-haven-task-35-fc238cee` then
  reproduced the two-point actor failure with unique native-slot-3 snapshots,
  stable task/mission/reward/item/AP controls, and operator-confirmed playable
  geometry without Samos or Keira. It is terminal `SAFE FALLBACK`; final
  `run.json` SHA-256 is
  `493A0EB0B9E858CDC6D9A0BDDE68A2D80EDB663C7161840E3D90C73063B76E39`
  and complete bundle SHA-256 is
  `9F67499CC22803689EC75EF6E5DB64FEC6188EAA57EEE8C792DE29A182AE7BE3`.
  The predefined `Haven City Access + DONE(34) + Jetboard + RANGED` convergence
  is now accepted evidence, while production implementation remains assigned
  to Milestones 18/19.

  Ordered side successor `m11-side-challenges-15ecab70` proved the original
  price `8`, typed zero-cost prompt, zero Gems, activation `0 -> 1`, and
  activation persistence through ordinary load with AP controls initially
  `0/0`. Finalization found two harness expectation errors: the deliberately
  closed parent reward is bounded mask bit `32`, and the active event texture
  becomes play icon `4` rather than a four-Gem cost. Those expectations are
  corrected. The ordinary load nevertheless reproduced a genuine unrelated
  expansion: native items `0 -> 243803`, bounded rewards `32 -> 63`, AP checked
  mask `0 -> 255`, Jetboard `0 -> 3`, task-30 items `0 -> 19`, and broad
  task/mission/feature state. Testing stopped before course controls. The run is
  terminal `BLOCKED`; final `run.json` SHA-256 is
  `DFF7F3D61DAAA0F68C007E3F0A5276B34D6CD01E6E42A4A70CD3A9D586B955B6`
  and complete bundle SHA-256 is
  `DFD55540DA5D08C46D2047305D8A6638050F5B95E4E732FD03D666A98BE9199A`.

  The runner now writes an `automatic_validation` result into every checkpoint
  and, for a contradictory live capture, preserves the evidence but raises
  immediately so no later operator step can silently continue. All 68 focused
  runner tests pass. This closes the Milestone 11 evidence-refresh process but
  leaves release feasibility blocked by the accepted Milestone 14
  reconstruction/Launch gates, the Milestone 22 side successor, and the
  Milestone 23 orb lifecycle.
- Mitigation: Require exact machine-checked masks and counters, unique
  correlation IDs, fresh internally consistent run-owned-slot snapshots,
  immutable finalization, and one complete hashed bundle. Never let a manual
  assertion override numeric controls. The runner rejects duplicate checkpoint
  names and snapshot use, waits for delayed compiler/runtime errors, validates
  each fallback independently, derives AP observations from same-identity
  checksummed state, and now stops immediately after preserving a contradictory
  live checkpoint. Haven production work must use only the accepted converged
  gate. Milestone 14 must reconstruct the full bounded AP-owned permanent target
  without native reward/task/check expansion and must include Launch. Milestone
  22 may resume the side matrix only after that gate passes; Milestone 23 owns
  the legitimate normal-mode 600-orb lifecycle.
- Exit criteria: Milestone 11 itself is complete as an investigation. Release
  requires a passing Milestone 14 reconstruction/Launch successor, production
  shadow-state verification in Milestone 20, a complete seven-checkpoint side
  production successor in Milestone 22, and the bounded normal-mode orb proof
  in Milestone 23. The Haven fallback remains accepted evidence for Milestones
  18/19. No UI percentage, stale path, unparsed nREPL acknowledgement, or
  offline matrix is accepted as positive runtime proof.
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
