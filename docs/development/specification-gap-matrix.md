# Specification gap matrix

This matrix compares the implementation observed in `Jak3-AP` with the
normative first-release default in
[`../design/progression-and-logic.md`](../design/progression-and-logic.md)
and
[`../../config/templates/Jak3.yaml`](../../config/templates/Jak3.yaml).

Snapshot date: **2026-08-07**

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
| Network locations | 147 | Frozen registry: 147; active scaffold generator: 131 | Partial / inactive until Milestone 5 |
| Story completions | 61: tasks 10–35 and 37–71 | 66: tasks 6–35 and 37–71, plus task 36 | Conflict |
| Major reward moments | 38 | 38 literal registry records; not generated or hooked | Partial |
| Selected side challenges | 24: tasks 114–137 | 65: tasks 73–137 | Conflict |
| Orb bundles | 24: thresholds 25–600 by 25 | 24 literal registry records; not generated or tracked | Partial |
| Victory event | Task 72 City Win, non-networked | Frozen code-less task-72 event and slot contract; retained scaffold logic still task 71 | Partial / conflict |
| Progression instances | 26 | Frozen registry: 26; active scaffold: 86 | Partial / inactive until Milestone 5 |
| Useful instances | 28 | Frozen registry: 28; active scaffold: 17 | Partial / inactive until Milestone 5 |
| Filler before traps | 93 | 28 | Conflict |
| Traps at default | 0 | 0 | Implemented |

The current pool is internally balanced to its 131 locations, but it is not a
smaller valid instance of the specified pool. Names, classifications, logic,
and receipt effects differ.

## Packaging, installation, and startup

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Self-contained `.apworld` | Builder packages world, client, icon, bridge, and startup overlay. | Implemented | — |
| Native launcher registration | Manifest registers Jak 3 Client and transparent 256×256 logo. | Implemented | — |
| Automatic OpenGOAL discovery | Launcher v2/v3 settings and paired environment overrides supported. | Implemented | — |
| Automatic debug game/compiler startup | Missing `gk`/`goalc` processes are launched with diagnostic commands. | Implemented | `R-010` |
| Compile-wait message | Flashing overlay is installed before `(mi)` and removed after compile path. | Implemented | `R-009` |
| Versioned runtime handshake | Protocol 2/game integration 1 hello and harmless `N -> N+1` ping use a framed temporary snapshot. | Automated; live smoke pending | `R-009` |
| Restart tolerance | Supervisor re-enters discovery/attach/hello after client or game restart; lifecycle cases are automated. | Partial until live smoke | `R-010`, `R-011` |
| Normal title handoff | Retired with protocol 1; protocol 2 does not change game/title/mission state. | Deliberately absent | — |
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
| Default values drive behavior | Most accepted default fields do not affect world generation/runtime yet. | Conflict |
| Standard AP placement controls | Standard inventory, locality, hints, exclusion, priority, item-link, and plando fields remain Archipelago-owned and configurable rather than being duplicated in the Jak 3 resolved profile. Their future pool/guarantee interactions remain deferred. | Partial |
| Unsupported combinations | All non-default governed configurations are rejected. Required first-release semantic failures have targeted messages, but placement-control overcounts/locality interactions await the target item pool. | Partial |

The phrase “supported default” currently means “accepted by the resolved-option
boundary,” not “implemented to the design.” Documentation and release notes
must keep that distinction explicit.

## Mission graph and early guarantees

| Requirement | Specification default | Current state | Status | Risk |
| --- | --- | --- | --- | --- |
| Mission structure | Tiered open board with eight broad route authorizations. | One key for each story task 7–71. | Conflict | `R-003` |
| Chain logic | Source order inside audited chains plus documented convergence. | Independent mission keys plus equipment table. | Conflict | `R-003` |
| Sphere-zero route | Local Spargus Field Orders; Haven only under safe Jetboard condition. | Local task-12 mission key. | Conflict | `R-013` |
| Sphere-zero ranged | Local Blaster or Vulcan Fury. | No reliable-ranged guarantee. | Missing | `R-013` |
| Mission dispatch | AP-authorized task starts without marking its completion. | Client/bridge can dispatch an unlocked native task. | Partial | `R-011` |
| Task 36 | No default location because no durable native close node. | Excluded/reserved in the frozen registry; still generated only by the isolated scaffold. | Partial / conflict | `R-004` |
| Goal | Task 72 after task 71. | Frozen code-less event/slot contract uses task 72; active scaffold logic still uses task 71 and no goal reporting exists. | Partial / conflict | `R-005` |

## Inventory and item application

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| AP inventory independent of native inventory | Ordered receipts are replayed, but no durable AP ledger exists. | Partial | `R-006`, `R-007` |
| Exact 26 progression pool | Scaffold mission keys/equipment create 86 progression items. | Conflict | `R-003` |
| Exact 28 useful pool | Scaffold progressive families create 17 useful copies with different semantics. | Conflict | `R-003` |
| Route authorizations | No route-item receipt model. | Missing | `R-003` |
| Seven finale relics / 5-of-7 | No AP relic ledger or `RELICS(5)` predicate. | Missing | `R-003`, `R-005` |
| Individual gun mods | Four progressive color families are implemented instead. | Conflict | `R-003` |
| Jetboard Launch and Zap separation | Not represented as specified AP items. | Missing | `R-003` |
| Dark/Light power dependency closure | Progressive family feature bits exist; exact default named-item semantics differ. | Partial | `R-006` |
| Progressive vehicle licenses | Five individual vehicle unlocks plus Slam Dozer are used. | Conflict | `R-003` |
| AP currency versus local-earned counters | Scaffold filler is health/ammo/eco; no AP Orb/Gem pack balance or local-earned counter. | Missing | `R-014` |
| Filler weighting | Schema holds target weights, but generator chooses uniformly from seven scaffold refills. | Conflict | `R-003` |
| Trap default | Percentage zero prevents trap generation. | Implemented | — |
| Trap effects when enabled | Names/schema differ and GOAL trap entry point is a no-op. | Missing/WIP | — |

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
| Finite, monotonic, persistent checks | Task closure is observed in memory/transient file; server duplicate handling helps while online. | Partial | `R-007` |
| Explicit stable public IDs | Literal first-release records, an independent full protocol-1 snapshot with exact retained-concept labels and permanent reservations, table versions, canonical serialization, and frozen item/location/mission hashes are automated. Runtime room/GOAL mismatch enforcement remains deferred. | Implemented contract / runtime pending | `R-012` |
| Story task checks | Native close hook covers all specified story tasks except documented task 36; generated set is wrong. | Partial | `R-004` |
| Major reward checks | Source audit and registry account for all 38 native nodes; generation/hooks remain absent. | Partial | `R-006` |
| Selected side checks | Frozen registry contains only tasks 114–137; isolated scaffold still enables 41 extra experimental tasks. | Partial / conflict | `R-003` |
| Safe challenge exclusions | IDs 127, 129, 130, 131, 132, and 136 are frozen as default-excluded; placement behavior awaits Milestone 5. | Contract only | `R-003` |
| Free side/purchase costs | No cost bypass or pre-opened Ratchet & Clank course state. | Missing | `R-014` |
| 25-orb thresholds | All 24 identities are frozen; local-earned tracking, durable bits, and generation remain absent. | Contract only | `R-014` |
| Orb thresholds above 300 excluded | Thresholds 325–600 are frozen as default-excluded; placement behavior awaits Milestone 5. | Contract only | `R-014` |
| AP Orb Packs do not advance checks | Neither balance nor local-earned counter exists. | Missing | `R-014` |
| Milestones/medals/gems/purchases off | No such locations are generated, matching their default disabled state. | Implemented by absence | — |

## Persistence, reconnect, and saves

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Persistent identity includes seed/team/slot/save/table version | Slot/state/table versions and hashes are frozen; no seed/team/slot/save binding or persistence exists. | Contract only | `R-007`, `R-012` |
| Durable received-item ledger/index | Absent; the client requests no `ReceivedItems`. | Missing | `R-007` |
| Durable location bitset | Absent; the client submits no locations. | Missing | `R-007` |
| Durable pending-check outbox | None. | Missing | `R-007` |
| Offline completion later sends exactly once | Not guaranteed. | Missing | `R-007` |
| New-game reconstruction | Absent from the handshake milestone. | Missing | `R-011` |
| Load-save reconstruction | Absent; protocol 2 has no `/game` command or inventory sync. | Missing | `R-006`, `R-011` |
| Reconnect/replay idempotence | Hello and duplicate ping are idempotent; gameplay replay is absent. | Handshake only | `R-011` |
| Packet-gap/out-of-order handling | Not implemented because protocol 2 requests no item stream. | Missing | `R-007` |

## Diagnostics and user feedback

| Requirement | Current state | Status | Risk |
| --- | --- | --- | --- |
| Client support log | Structured lifecycle, handshake, heartbeat, and exception events recorded. | Implemented | — |
| Game/compiler support log | `gk`, `goalc`, client markers, and bridge events combined. | Implemented | `R-009` |
| State snapshot on demand | `/diagnostics` records current bridge/client state and paths. | Implemented | — |
| Received/sent HUD messages | Deliberately absent from protocol 2. | Missing | `R-011` |
| Compile-wait text | Flashing overlay during compile path. | Implemented/Smoke verified | — |
| Sufficient failure classification | Rich raw evidence exists; compiler-error detection and durable logic provenance remain incomplete. | Partial | `R-009`, `R-012` |

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
