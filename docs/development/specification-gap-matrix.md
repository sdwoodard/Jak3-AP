# Specification gap matrix

This matrix compares the implementation observed in `Jak3-AP` with the
normative first-release default in
[`../design/progression-and-logic.md`](../design/progression-and-logic.md)
and
[`../../config/templates/Jak3.yaml`](../../config/templates/Jak3.yaml).

Snapshot date: **2026-08-09**

## Status vocabulary

| Status | Meaning |
| --- | --- |
| Implemented | Code exists for the stated default behavior. Runtime claims still require evidence in the verification matrix. |
| Partial | A related scaffold mechanism exists, but the default contract is incomplete or materially different. |
| Missing | No implementation of the default contract was found. |
| Unverified | Code appears present, but required end-to-end evidence has not been recorded. |
| Conflict | Current behavior contradicts the normative default and cannot be accepted as an alternate interpretation. |

## Exact default arithmetic

| Contract | Specification default | Current implementation | Status |
| --- | --- | --- | --- |
| Network locations | 147 | All 147 frozen registry records are active. | Implemented generator |
| Story completions | 61: tasks 10–35 and 37–71 | Exactly 61 active network locations; runtime hooks remain absent. | Implemented generator / runtime missing |
| Major reward moments | 38 | Exactly 38 active registry locations; runtime reward hooks remain absent. | Implemented generator / runtime missing |
| Selected side challenges | 24: tasks 114–137 | Exactly 24 active registry locations. | Implemented generator |
| Orb bundles | 24: thresholds 25–600 by 25 | Exactly 24 active thresholds; local-earned tracking remains absent. | Implemented generator / runtime missing |
| Victory event | Task 72 City Win, non-networked | One locked code-less task-72 event consumes no pool slot; it is immediately reachable in the temporary scaffold. | Implemented generator / Standard logic and runtime missing |
| Progression instances | 26 | Exactly 26 active registry instances with frozen classifications. | Implemented generator |
| Useful instances | 28 | Exactly 28 active registry instances. | Implemented generator |
| Filler before traps | 93 | Exactly 93 instances from one deterministic weighted draw. | Implemented generator |
| Traps at default | 0 | 0 | Implemented |

The static pool now has the exact required arithmetic, names, classifications,
and exclusions. It is not yet playable: all locations and events are exposed
through an immediate-access scaffold, and runtime receipt/check behavior is
still absent.

## Packaging, installation, and startup

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Self-contained `.apworld` | Builder validates and packages the world, client, icon, explicit bridge manifest, and every declared source. | Implemented | — |
| Deterministic bridge lifecycle | Manifest version 1 drives package/install/repair/object order/runtime load/source-set hashing without wildcard discovery. | Implemented and automated | `R-009` |
| Native launcher registration | Manifest registers Jak 3 Client and transparent 256×256 logo. | Implemented | — |
| Automatic OpenGOAL discovery | Launcher v2/v3 settings and paired environment overrides supported. | Implemented | — |
| Automatic debug game/compiler startup | Missing `gk`/`goalc` processes are launched with diagnostic commands. | Implemented | `R-010` |
| Compile-wait message | Flashing overlay is installed before `(mi)` and removed after compile path. | Implemented | `R-009` |
| Versioned runtime handshake | Protocol 3/game integration 2 exports a forward-safe live snapshot, full compatibility metadata, game nonce, and eight harmless receipts. The semantic contract is frozen; the revised supported matrix passed 14/14 rows. | Implemented; live accepted with limitations | `R-009`, `R-019` |
| Restart tolerance | Game restart changed the nonce, cleared receipts, rejected stale state, and rebound the save. Client-first and game-first both passed. Clean and unclean client loss recovered through the supported full client/`gk`/`goalc` restart; warm replacement attachment remains unsupported on v0.3.5. | Implemented for documented path; upstream limitation retained | `R-010`, `R-019` |
| Normal title handoff | Retired with protocol 1; protocol 3 permits read/query at title but does not change title or mission state. | Deliberately absent | — |
| Compile failure is authoritative | Protocol commands require snapshot acknowledgement, but `(mi)` completion does not prove compiler output contains no error. | Partial | `R-009` |
| Client-owned process cleanup | Client does not stop processes it started. | Missing | `R-010` |
| Tagged artifact automation | `v*` GitHub workflow validates version, builds, hashes, and releases. | Implemented | — |

## Options contract

| Requirement | Current state | Status |
| --- | --- | --- |
| Design vocabulary/default values | The complete 51-key YAML schema is declared. Jak 3 overrides progression balancing to 65 and exposes `accessibility: items` distinctly while retaining `full` as the only supported first-release value. | Implemented |
| Resolved generation boundary | `generate_early()` creates one immutable 41-field semantic snapshot before regions or items. A source test prevents downstream world code from reading raw option objects. | Implemented |
| Exact default-template resolution | The canonical shipped YAML passes through Archipelago's parser/roller and resolves to the explicit supported profile in a standalone checkout. | Implemented |
| Non-default experimental safety | Every non-default design-governed value fails early; canonical story, experimental collectible gates, relic bounds, and Orb progression-cap bounds have specific diagnostics. | Implemented |
| Default values drive behavior | Static-pool identities, counts, weights, trap percentage, and exclusions drive generation; Standard logic and runtime-governed fields remain deferred. | Partial |
| Standard AP placement controls | Standard inventory, locality, hints, exclusion, priority, item-link, and plando fields remain Archipelago-owned and configurable rather than being duplicated in the Jak 3 resolved profile. Their future pool/guarantee interactions remain deferred. | Partial |
| Unsupported combinations | All non-default governed configurations are rejected. Required first-release semantic failures have targeted messages, but placement-control overcounts/locality interactions with the active pool await Milestone 12. | Partial |

The supported default now drives the static pool, but it does not imply that
Standard logic or runtime behavior is implemented. Documentation and release
notes must keep that distinction explicit.

## Mission graph and early guarantees

| Requirement | Specification default | Current state | Status | Risk |
| --- | --- | --- | --- | --- |
| Mission structure | Tiered open board with eight broad route authorizations. | One always-open Milestone 5 scaffold region; no mission graph yet. | Partial / non-playable | `R-003` |
| Chain logic | Source order inside audited chains plus documented convergence. | No mission, item, finale, or route rules are applied. | Missing | `R-003` |
| Sphere-zero route | Local Spargus Field Orders; Haven only under safe Jetboard condition. | No early route guarantee; the obsolete task-12 guarantee was removed. | Missing | `R-013` |
| Sphere-zero ranged | Local Blaster or Vulcan Fury. | No reliable-ranged guarantee. | Missing | `R-013` |
| Mission dispatch | AP-authorized task starts without marking its completion. | Protocol 2 has no mission dispatch. | Missing | `R-011` |
| Task 36 | No default location because no durable native close node. | Absent from active generation; legacy ID `743001036` remains reserved. | Implemented generator | `R-004` closed |
| Goal | Task 72 after task 71. | Task 71 is a network location and task 72 a code-less Victory event; Standard finale logic and runtime reporting are absent. | Partial | `R-005` |

## Inventory and item application

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| AP inventory independent of native inventory | Schema 1 defines a Python-owned received-item journal/count ledger, but no item stream populates it and no native inventory is changed. | Storage contract / gameplay missing | `R-006`, `R-007` |
| Exact 26 progression pool | Exact registry multiplicities and classifications are generated. | Implemented generator | `R-003` |
| Exact 28 useful pool | Exact registry multiplicities and classifications are generated. | Implemented generator | `R-003` |
| Route authorizations | All eight are present in the generated progression pool; receipt behavior and rules are absent. | Partial | `R-003`, `R-006` |
| Seven finale relics / 5-of-7 | Seven relic items are generated; no AP relic ledger or `RELICS(5)` predicate exists. | Partial | `R-003`, `R-005` |
| Individual gun mods | All canonical individual gun-mod items are generated. Runtime application is absent. | Partial | `R-006` |
| Jetboard Launch and Zap separation | Both distinct items are generated. Runtime application is absent. | Partial | `R-006` |
| Dark/Light power dependency closure | Canonical named items and classifications are generated; runtime dependency behavior is absent. | Partial | `R-006` |
| Progressive vehicle licenses | Canonical progressive license instances are generated. Runtime application is absent. | Partial | `R-006` |
| AP currency versus local-earned counters | Currency packs participate in weighted filler generation and schema 1 reserves separate local-earned Orb/Gem counters; no runtime balance or earning hook exists. | Storage contract / runtime missing | `R-014` |
| Filler weighting | All 93 filler items use one deterministic weighted draw in canonical order. | Implemented generator | `R-003` |
| Trap default | Percentage zero prevents trap generation. | Implemented | — |
| Trap effects when enabled | Future trap definitions remain public but unsupported options fail and generate zero traps. Runtime effects are deferred. | Missing/WIP | — |

## Bootstrap, native rewards, and shadow state

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Mission-specific equipment profiles | Stable profile identifiers are frozen; profile behavior remains unimplemented. | Contract only | `R-008` |
| Lesson ability overlays | No scoped lesson grants/cleanup. | Missing | `R-008` |
| Vehicle/actor bootstrap | No per-mission temporary actor/loadout profiles. | Missing | `R-008` |
| Bootstrap grants never become AP receipts | No bootstrap subsystem exists. | Missing | `R-008` |
| Simplified native story shadow state | Separate task-30/task-63 profile identifiers are frozen; native state behavior remains unimplemented. | Contract only | `R-008` |
| Shadow state excluded from `RELICS(n)` | No relic ledger/shadow separation exists. | Missing | `R-006`, `R-008` |
| Major native reward interception | Reward-node table is audited but not hooked. | Missing | `R-006` |
| Suppress only permanent native grant | No reward suppression/recursion guard exists. | Missing | `R-006` |
| Reconcile after reward/load/exit | Receive cursor can request replay; it does not reconstruct all required AP/shadow state. | Partial | `R-006`, `R-007` |

## Location identity and sanity checks

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Finite, monotonic, persistent checks | Schema 1 validates sorted explicit location-ID sets and an outbox, but no game hook records a check. | Storage contract / gameplay missing | `R-007` |
| Explicit stable public IDs | Literal first-release records, permanent reservations, table versions/hashes, authenticated slot-data validation, and persistent-state ID rejection are automated. GOAL gameplay enforcement remains deferred. | Implemented Python contract / GOAL runtime pending | `R-012` |
| Story task checks | Exactly 61 registry identities are generated; native task-close hooks remain absent. | Implemented generator / runtime missing | `R-007` |
| Major reward checks | Exactly 38 audited registry identities are generated; reward hooks remain absent. | Implemented generator / runtime missing | `R-006` |
| Selected side checks | Exactly the 24 tasks 114–137 are generated. | Implemented generator | `R-003` |
| Safe challenge exclusions | IDs 127, 129, 130, 131, 132, and 136 are `EXCLUDED` and reject progression/useful placement. | Implemented generator | `R-003` |
| Free side/purchase costs | No cost bypass or pre-opened Ratchet & Clank course state. | Missing | `R-014` |
| 25-orb thresholds | All 24 identities through 600 are generated; local-earned tracking and durable bits remain absent. | Implemented generator / runtime missing | `R-014` |
| Orb thresholds above 300 excluded | Thresholds 325–600 are `EXCLUDED` and reject progression/useful placement. | Implemented generator | `R-014` |
| AP Orb Packs do not advance checks | Neither balance nor local-earned counter exists. | Missing | `R-014` |
| Milestones/medals/gems/purchases off | No such locations are generated, matching their default disabled state. | Implemented by absence | — |

## Persistence, reconnect, and saves

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Persistent identity includes seed/team/slot/save/table version | Schema 1 atomically persists and one-time binds the full identity/contract. Real fresh/repeated load, A → B → A, wrong-slot copy rejection, untagged vanilla rejection, Continue Without Save, New Game identity, normal recovery, and supported clean/unclean full-process recovery passed. Warm replacement attachment and external bank interference remain unsupported. | Automated plus runtime accepted with limitations | `R-007`, `R-012`, `R-019` |
| Durable received-item ledger/index | Per-index `received`/`pending`/`applied` records, counts, and pending indices are schema-defined and round-trip tested; the client still requests no `ReceivedItems`. | Automated empty/storage model / gameplay missing | `R-007` |
| Durable location bitset | Sorted explicit registry IDs are schema-defined and validated; no location hook populates them. | Automated storage model / gameplay missing | `R-007` |
| Durable pending-check outbox | Schema-defined and relationship-validated; no location hook or network drain exists. | Automated storage model / gameplay missing | `R-007` |
| Offline completion later sends exactly once | Not guaranteed. | Missing | `R-007` |
| New-game reconstruction | Absent from the handshake milestone. | Missing | `R-011` |
| Load-save reconstruction | Absent; protocol 2 has no `/game` command or inventory sync. | Missing | `R-006`, `R-011` |
| Reconnect/replay idempotence | Protocol 3 harmless commands passed one effect, exact duplicate receipt replay, `ALREADY_APPLIED`, stale-game-session reset, and title-menu unsafe rejection. Gameplay item replay is absent. Supported full-process recovery passed after clean and unclean client loss; warm replacement attachment remains unsupported. | Control transport and supported process recovery accepted | `R-007`, `R-010`, `R-019` |
| Packet-gap/out-of-order handling | Not implemented because Protocol 3 still requests no item stream. | Missing | `R-007` |

## Diagnostics and user feedback

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Client support log | The existing text log is preserved with bounded rotation and redaction. | Implemented | — |
| Game/compiler support log | Captured `gk`, `goalc`, emergency GOAL stdout, and client markers remain combined through bounded sanitized pipes; there is no raw spool and GOAL no longer opens a support file. | Implemented | `R-009` |
| Structured event timeline | Python owns one schema-1 JSONL stream with stable registered names, global ordering, GOAL source sequences/reload generations, sticky ring readiness, top-level and nested event allowlists, exception capture, and event-derived capture-gap summaries. Duplicate GOAL observations do not repeat drain-completion events. | Implemented and automated | — |
| State snapshot on demand | `/diagnostics` and `/diagnostics summary` retain the current snapshot UX without dumping raw identities or forms. | Implemented | — |
| Sanitized support export | `/diagnostics export` runs off the heartbeat loop and writes a checksummed local ZIP with merged timeline, paired logs, schema-validated summaries, cross-generation storage failover, missing/truncated-artifact declarations, newest-evidence retention, and no native save or sidecar. Startup and export reserve every leased live session's remaining rotation budget under the hard managed cap; remote leases expire after 30 minutes. | Implemented and automated | — |
| Diagnostic failure isolation | Injected event-sink and writer failures leave persistence revisions, command results, safety decisions, and state mutation unchanged. | Implemented and automated | — |
| Received/sent HUD messages | Deliberately absent from Protocol 3. | Missing | `R-011` |
| Compile-wait text | Flashing overlay during compile path. | Implemented/Smoke verified | — |
| Sufficient failure classification | Typed persistence compatibility/binding/corruption/eligibility/lock/stale errors and client contract diagnostics exist; compiler-error detection and live save provenance remain incomplete. | Partial | `R-009`, `R-012`, `R-019` |

## Verification conflicts versus design corrections

The OpenGOAL source-table audit currently supports the specification rather
than requiring a specification correction:

- native task aliases 6–137 match, with the documented task-88 normalization;
- task 36 is the only story-row omission from native `close-task` coverage;
- all 65 side tasks have native close records;
- all 51 reward-bearing nodes are accounted for as 38 major, eight
  crystal-only, and five never-valid moments;
- all 24 selected side-task parents match native source; and
- every documented candidate milestone node exists on its stated task.

No design change was made during this documentation milestone. Runtime route
requirements and persistence behavior remain evidence gaps, not reasons to
weaken the specification.
