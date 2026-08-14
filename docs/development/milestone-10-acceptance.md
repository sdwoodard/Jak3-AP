# Milestone 10 acceptance report

Date: **2026-08-14**

Status: **Implementation and non-interactive gates pass; connected live gameplay gate pending**

## Implemented boundary

- The durable location allowlist is exactly story tasks 10–16
  (`743001010`–`743001016`) plus task-16 reward node 36 (`743020036`).
  Task 11 is now a real `task-complete?` observation; the old debug trigger is
  absent.
- Reward node 36 is observed immediately at interception and recovered from
  its persistent closed-node state after a restart. Python commits the checked
  bit and outbox before acknowledging GOAL or sending `LocationChecks`.
- `archipelago-rewards.gc` installs one reload-safe wrapper around
  `game-task-node-info.eval-game-task-cmd!` method 13. It matches only
  `desert-artifact-race-1-resolution`, command index 12/count 2, and the exact
  `add-jakc`, `add-armor-0` command pair. Bound AP mode preserves Jak C and
  omits Armor 1. Unbound/AP-off, recursion-guard, and shape-mismatch paths call
  the complete native method; no other reward node is intercepted.
- Control resets required items-, locations-, and reward-module activation
  attestations before each ordered source load. Each module publishes only its
  own proof after installing its hooks; rewards publishes last after method 13
  and immediately re-exports the snapshot. Python refuses compatibility and
  retains any reload obligation when any proof is absent, even if nREPL
  returned its transport completion barrier. The wrapper's own bound-mode
  predicate requires the same three proofs and therefore preserves the native
  reward during any partial-load interval before Python observes the snapshot.
- The existing ledger remains authoritative for Jetboard, Blaster, and
  Progressive Armor capped at stage 1. Item reconciliation is bracketed by
  reward-owned application hooks and never publishes the reward check. Every
  durable task/reward observation invalidates the item-reconciliation fast
  path. In addition, every bridge heartbeat exports the actual three-bit native
  target and Python compares it with the bound ledger, so a death/retry
  task-mask rebuild cannot strand a ledger-owned feature after its one-shot
  observation was acknowledged.
- Persistent reward recovery reports an audited-shape mismatch once per bound
  mismatch episode, including when the native reward first replayed before AP
  binding. Recovery remains fail-open and never guesses at a changed command.
  The same live shape predicate suspends permanent-item reconciliation in the
  exported snapshot and again at command dispatch, so Python cannot erase the
  preserved native Armor fallback after a diagnostic acknowledgement or client
  restart. The GOAL runtime-safety event masks the permanent-item bit through
  that same predicate, keeping support diagnostics consistent with snapshots
  and dispatch. Reconciliation resumes only after the audited shape is restored.
- `JAK3_AP_M10_TEST_GOAL=task16` enables the disposable acceptance goal. Unset
  disables it and every other value fails at startup. Completion is one atomic
  sidecar transition after both task-16 IDs are durable. `CLIENT_GOAL` sends
  once per authenticated connection and resends after reconnect or client
  restart; `goal_status_sent` means at least one socket send succeeded.
- Protocol 3, integration 2, native tag 900, state schema 1, slot-data version
  2, all public table versions/hashes, the 147-location generator, and normal
  task-72 goal semantics are unchanged. Bridge runtime metadata advances to 5.

## Automated and build evidence

| Gate | Result |
| --- | --- |
| Complete packaged suite | **PASS — 362 tests**, expected optional C++ speedup warning only |
| Ruff | **PASS** — lint plus 29-file format check |
| mypy | **PASS** — 13 compatibility modules |
| Source audit | **PASS** — all six task/reward/milestone groups |
| Deterministic APWorld | **PASS** — two byte-identical 246,668-byte artifacts |
| APWorld SHA-256 | `9AC9ABD63C870918E8FC1360C0CC45887E55302CB80CD51EC7CB0BF53844EB91` |
| Active-project source set | `dfc172d0516923dd3d00d5f2e0bf71b2839d8989f537c641868679b00c94eb45` |
| Official OpenGOAL v0.3.5 compile | **PASS** — exact final source set built all 1,169 targets in 26.643 seconds with no compile/type errors |
| Manifest-order live reload | **PASS** — the attached runtime loaded control, diagnostics, items, locations, and rewards in 1.215 seconds and exported `items_module_active 1`, `locations_module_active 1`, and `reward_module_active 1` |

Automated tests cover all eight IDs, malformed/unknown IDs, table mismatch,
commit failure, diagnostic writer failure, duplicate observation, sorted
retry, connection-generation isolation, server rollback, confirmation-only
compaction, reward node validation, audited-shape-gated persistent recovery,
deduplicated item-rebuild invalidation while GOAL observations await
diagnostic acknowledgement, retriggering after a new reward invocation or
GOAL source activation, native-target readback recovery when the corresponding
diagnostic record was evicted, and no command retrigger when only the diagnostic
dropped-count continues to rise,
strict goal configuration, a real WebSocket `ConnectionClosed` goal-send
failure, reconnect/client-restart resend, and a send that completes on a stale
connection. They also cover a successful goal wire send followed by a sent-flag
commit failure without duplicating that connection.
Source-boundary tests cover AP-on/off and
unbound branching, exact command shape, mismatch fail-open behavior and
reconciliation suspension across a fresh client context,
recursion/item guard, already-target-state reconciliation, reload-safe native
capture, post-bind mismatch reporting, task/reward rebuild reconciliation
including an in-flight command race, event-free native-target loss detected by
an ordinary heartbeat, suspension-aware runtime-safety diagnostics, independent
items/location/reward activation failure behind a successful nREPL barrier,
and absence of a second reward interception. Existing Milestone 8
tests retain index-zero replay, packet gaps, crash windows, receipt attribution,
target-state idempotence, and restart reconstruction.

## Generated two-slot fixture and transport evidence

`tools/generate_milestone_10_fixture.py` derives both player files from the
canonical YAML and changes only identity, description, and standard plando
blocks. The current fixture passes Archipelago's real two-world plando and fill
pipeline with seed `10101636`: both slots retain 147 locations, every planned
item is taken from the canonical pool, every location is filled, and no pool
item is left unplaced. The resulting assignments are:

| Runner location | Delivered item/owner |
| --- | --- |
| Task 10 | Jetboard / runner |
| Task 11 | Blaster / runner |
| Tasks 12–16 | Scatter Gun, Wave Concussor, Plasmite RPG, Beam Reflexor, and Gyro Burster / helper |
| Reward `743020036` | Progressive Armor / runner |

The runner therefore receives no unsupported Jak 3 item during this slice.
These five helper items are guaranteed single-copy members of the canonical
pool; the fixture no longer assumes that five copies of a weighted filler were
rolled. The earlier real local-server smoke proved the same runner placements
and helper ownership boundary, but used the superseded Orb Pack helper payload.
It remains transport evidence only; the current five-item helper payload has
not been rerun through the server.
The fixture instructions require the task-16 environment gate and prohibit
reuse of its native save or sidecar with a normal task-72 seed.

## Remaining connected live gate

The following rows require operator play with disposable AP-tagged native
saves and were not inferred from unit tests, generation, server transport, or
an unbound module-load smoke:

| Scenario | Status |
| --- | --- |
| Complete real tasks 10–16 through the connected client | Pending |
| Bound node-36 suppression: Jak C/task/cutscene survive and Armor 1 is absent | Pending |
| AP disabled and unbound node-36 replay preserve the complete native reward | Pending |
| Save immediately before/after reward; game/compiler/client restart recovery | Pending |
| Death before/after reward and mission replay, including duplicate observation | Pending |
| Title/load/connect in both orders and offline completion/reconnect | Pending |
| Live index-zero receipt replay and native target reconciliation | Pending |
| Live temporary-goal send, reconnect resend, and client-restart resend | Pending |
| Support bundle reconstructs the connected check/receipt/command chain | Pending |

Milestone 10 is therefore not marked complete under the roadmap gate. The code,
package, current fixture's real core plando/fill, earlier local-server transport
smoke, official compile, and ordered-load portions are complete; the exact
remaining gate is the disposable connected native gameplay matrix above.
