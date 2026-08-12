# Milestone 8 acceptance report

## Current decision

**Milestone 8 is complete.** The final APWorld passes the complete packaged
suite, official OpenGOAL v0.3.5 compile, and the corrected native Blaster
dependency probe. The retained disposable AP-tagged-save live matrix below
continues to cover the accepted gameplay and recovery workflow. The accepted
recovery uses the frozen full client/`gk`/`goalc` restart policy; no warm
replacement compiler was started or attached.

## Frozen foundation

- Milestones 7 and 7.2 remain complete for the documented 14/14 supported
  first-release workflow.
- Protocol 3, game integration 2, native tag 900/version 1, descriptor-qualified
  acknowledgement, the existing result/error meanings, and the eight-entry
  game-session receipt ring are unchanged.
- The original OpenGOAL v0.3.5 warm replacement-compiler and external bank-lock
  limitations remain documented in the Milestone 7.2 report and Protocol 3
  update/restart policy.
- The Milestone 7.2 closure is isolated at commit `b0fd45c`; this Milestone 8
  work began from a clean `Jak3-AP` tree and clean Git-backed reference trees.

## Implemented Milestone 8 contract

- The client requests remote, local, and starting-inventory items with
  `items_handling = 0b111`.
- A serialized coordinator validates a complete packet before any persistent
  or native mutation and accepts only Jetboard (`743000108`), Blaster
  (`743010014`), and Progressive Armor (`743000116`). All armor receipts remain
  in the journal while native behavior is capped at stage 1.
- Schema-1 journal commits precede native reconciliation. Exact duplicates do
  not commit, gaps and conflicts retain the durable expected index and request
  canonical `Sync`, and index zero atomically replaces the complete history.
- Runtime version 3 adds Protocol 3 command 102 with target bits Jetboard,
  yellow-gun stage 1, and armor stage 1. Existing codes and meanings are not
  changed.
- `archipelago-items.gc` owns all native feature mutation; `archipelago.gc`
  contains only the constant, payload validation, existing safety gate, narrow
  hook, and dispatch branch.
- Pending journal entries become applied only in the same durable transition
  that records an `APPLIED` or `ALREADY_APPLIED` command receipt. Both uncertain
  crash windows retain pending state for a fresh command.
- The diagnostic-schema-1 registry now covers packet, receipt, replay, queue,
  application, reconciliation, rejection, and recovery events. GOAL codes
  500–502 describe native target applied/already-correct/failed.

No Orb Pack, Skull Gem Pack, ammunition, health, refill, trap, location,
reward, overlay, mission, route-state, or additive-effect implementation is
present. Item transitions leave both locally earned collectible totals
unchanged.

## Automated evidence

| Gate | Result |
| --- | --- |
| Focused post-review ReceivedItems and native-source regression suites | **PASS** — 30 tests; two environment warnings (`_speedups` and `pkg_resources` deprecation) |
| Complete packaged suite | **PASS** — 318 tests; two environment warnings (`_speedups` and `pkg_resources` deprecation) |
| Ruff lint and selected formatting | **PASS** |
| mypy compatibility modules, including `received_items.py` | **PASS** — 12 source files |
| OpenGOAL source-table audit | **PASS** — all six audit groups; both Git-backed reference trees remained clean |
| Deterministic twin APWorld build | **PASS** — two byte-identical 231,202-byte artifacts; SHA-256 `942EFB508BB8716DBBEC454F62253C58A3C1FA58F1B46CB13D82EE3E065963BC` |
| Standalone active-project installation | **PASS** — source set `93d964bde805cd714367dbf4db7d0b5bc790a67f2869360ab1c7a7d1846e435a` |
| Official OpenGOAL v0.3.5 full compile | **PASS** — all 1,167 targets in 41.717 seconds |
| Runtime module load order | **PASS** — control, diagnostics, items |
| Direct native target probe | **PASS (supplemental)** — retained masks 0, 1, 2, 4, and 7 were observed exactly; on the corrected final source, yellow stage 1 with the generic gun bit absent returned `APPLIED`, rebuilt target 2 with generic gun 1/yellow stage 1, and restored the original target 0 afterward |

The complete packaged suite ran from the final APWorld in a disposable
Archipelago checkout. The final diff passed `git diff --check` and the source
boundary review.

The first post-review closure moved validation ahead of CommonClient's generic
mutation and replaced the synthetic crash-window assertion with executable
coordinator recovery. The second closure made Blaster's native correctness
predicate require both yellow stage 1 and its generic gun dependency, and made
whole-packet rejection diagnostics retain the offending entry's absolute index,
location, source player, and flags. The third closure treats each distinct GOAL
native-load success generation/sequence as a reconciliation boundary, so a
same-descriptor load that starts and finishes between heartbeat snapshots still
reconstructs the ledger target; a replayed diagnostic record is idempotent. The
fourth closure makes every changed index-zero canonical history a reconciliation
boundary even when metadata changes preserve all applied states and the capped
target mask. The fifth closure treats an increased bounded-ring dropped-record
counter as a conservative reconstruction boundary within its GOAL diagnostic
activation generation, so eviction of the native-load record cannot suppress
reconciliation; replaying the same overflow projection is idempotent. The final
Python paths are covered by direct CommonClient dispatch and coordinator tests
plus the exact-package suite; the unchanged final native source retains the full
compile and disposable dependency-repair evidence. Protocol 3, command 102, and
the frozen live acceptance policy were not changed, and the live hashes below
remain the retained Milestone 8 gameplay/recovery run.

## Crash-window automation

1. Receipt persisted pending before any native command: an unclean repository
   reopen drives the real coordinator, receives `APPLIED`, and durably clears
   the pending entry.
2. Native target changed before durable result observation: the coordinator
   receives `APPLIED`, an injected application-receipt commit failure leaves the
   ledger pending, and repository recovery sends a fresh command that receives
   `ALREADY_APPLIED` and performs exactly one durable pending-to-applied
   transition. The fake native target records one mutation across both commands.

Packet tests also cover the real CommonClient pre-dispatch boundary, malformed
multi-entry rejection without an in-memory prefix, one rejection/one `Sync`
across the index-zero canonical response, exact offending-entry rejection
attribution, valid normalized forwarding, multi-item atomicity,
unknown/deferred IDs, gaps, overlaps, exact replay,
metadata-only canonical changes, history mismatch, stale removal, foreign
attribution, starting inventory, special server locations, counts beyond native
caps, and unchanged Orb/Gem totals. Unsafe dispatch tests cover cutscene,
death/restart, vehicle, load, and transition.

## Required disposable live matrix

| Row | Required observation | Status |
| --- | --- | --- |
| 1 | Jetboard receipt → durable ledger → native target | **PASS** — receipt/application events include Jetboard; native readback mask is 7. |
| 2 | Blaster receipt → generic gun dependency plus yellow stage 1 | **PASS** — receipt/application events include Blaster; live GOAL readback reports target 7 and generic gun 1. |
| 3 | Progressive Armor receipts retained; native cap remains stage 1 | **PASS** — four receipts remain in the ten-entry ledger while the native target remains bit 2 only. |
| 4 | Unsafe receipt queues and dispatches only after current safety opens | **PASS** — vehicle safety retained index 9 pending at revision 34 with command 0 unchanged; command 1 returned `UNSAFE_NOW`, then command 2 returned `ALREADY_APPLIED` after safety reopened and revision 35 durably cleared pending. |
| 5 | Exact duplicate delivery produces no commit or native application | **PASS** — the final canonical duplicate retained ledger revision 39 and command 0. |
| 6 | Index-zero canonical replay/replacement reconciles exact target | **PASS** — the initial index-zero history rebuilt target 7; later index-zero packets were exact duplicates. |
| 7 | Client restart reconstructs from the durable ledger | **PASS** — client-state recovery was exercised through the required full-process restart, not unsupported warm attachment. |
| 8 | Game restart/new nonce reconstructs after exact rebinding | **PASS** — the new nonce remained unsafe until binding, then command 0 reapplied native target 7. |
| 9 | Supported full client/`gk`/`goalc` recovery reconstructs pending/applied targets | **PASS** — an unclean revision-35 ledger reopened, emitted recovery events, advanced once to revision 39, and reconstructed target 7. |

Warm replacement-compiler recovery is not a row and was not attempted.

The accepted run used copies of the retained Milestone 7.2 room, sidecar, and
AP-tagged Save A. A newer ineligible member of the copied redundant native-bank
pair was excluded during fixture preparation before the accepted run; the
original Milestone 7.2 artifacts were not changed. No accepted recovery row
locked, replaced, or edited a native bank after the run began.

## Live and native evidence hashes

- Post-review final compiler stdout:
  `0630d4ea45e01750aacdd3dfd787f5b27d9a580c42191a26c822d8e9154adc32`
- Post-review final compile recorder:
  `dc90a3cef9d0f0d451789e2ded930f1c14cd632b629298a45c9bada8cef787b0`
- Post-review Blaster dependency probe game stdout:
  `a385148c64d7c9745ae74524165db54b8e871e726295e1cda438a4e88ac15c16`
- Post-review Blaster dependency probe compiler stdout:
  `e72433df806f63d2292530e2b7b114c042ab2c601f0fee7ea9f004ea9e3346c1`

- Initial receipt/unsafe run stdout:
  `68be48a7c59da1f5cb5b3b3e91ce0a68252821f278bcf8abbffd7a124b361601`
- Supported full-process recovery stdout:
  `d0c35387ee7c0a0977b9ca26f6086fc3ba7c469a1ba8b71965332923706edd61`
- Initial diagnostic events, including item events 53–140:
  `4274521b541805351a2c28394d4a32cb29e882701b871223c5b95d35677a5b96`
- Recovery diagnostic events, including item events 52–73:
  `ff70d030ef629209814ccd57a04c972db462c1b0e274f580bce7f4a51ed1133c`
- Recovery OpenGOAL log with target 7/generic-gun 1 readback:
  `731a647fa4a2681bc3ed2da56a9cbaa8d93519c745cfaa62cb95a2299d4fb78b`
- Final revision-39 sidecar:
  `bb3ed53a23c069a2ca03ad5b2fa29d5bb243e9a291602fa36a2c4b9b0823f796`

- Compiler/probe stdout:
  `5f4dbf3bba549cae6fde4635566df15d55cb218414e8c52662dd5b6fe9e1880b`
- Game stdout:
  `d8a9cab3242b22bf98aa0d3b5318255de1bd49df7e50b8bbe08cf936f3f0ada6`
- Restricted compile/attach recorder:
  `9a180030cf892694160965cade2987b876f8a8ac205956922bacbe5c01c0f4d7`

Raw disposable artifacts remain ignored under `dist/milestone-8/live/` and
`D:\Codex\Jak3\tmp`; this report retains only sanitized observations and
evidence hashes.
