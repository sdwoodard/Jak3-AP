# Verification matrix

This document separates implementation claims from evidence. A green compile
or unit test is not evidence that a shuffled Jak 3 save is completable.

Snapshot date: **2026-08-07**

## Evidence levels

| Level | Meaning |
| --- | --- |
| Source verified | Static tables/behavior were checked against audited source or package contents. |
| Automated | A repeatable test directly exercises the stated behavior. |
| Smoke verified | A real process reached a narrow expected result once; broader behavior remains unproven. |
| Runtime accepted | The behavior passed its full real-game scenarios, including failure/replay cases where applicable. |
| Unverified | No sufficient current evidence is recorded. |

A behavior is release-ready only at the evidence level appropriate to its
risk. Persistence, reward suppression, bootstrap cleanup, and mission
reachability require runtime acceptance even when their tables have unit tests.

## Recorded baseline evidence

| Evidence | Result | Scope and limit |
| --- | --- | --- |
| Milestone 4 Python/APWorld suite | 110 tests passed on 2026-08-07 from the packaged APWorld installed in a disposable Archipelago copy, with bytecode writes disabled. | Covers legacy compatibility, canonical YAML, first-release registries, hashes, slot data, package imports, CI triggers, and retained scaffold generation; no gameplay runtime behavior. |
| Milestone 4 APWorld artifact | Built successfully with 27 entries; SHA-256 `3B7A33A876F4F054FBADEEF42C24AAD146D3E7AA9F10794F96444E2148F28534`. | Local artifact evidence; release reproducibility and runtime installation remain later milestones. |
| Milestone 4 static checks | Ruff lint/targeted format and mypy compatibility-module checks passed. | Static evidence only. |
| OpenGOAL source-table audit | Passed all six checks on 2026-08-06 against `D:\Codex\Jak3\jak-project`. | Verifies task/reward/parent/milestone records only. |
| APWorld artifact | Rebuilt `dist\jak3.apworld`, 22 entries, SHA-256 `B701D3BEAF6F7F90B99E2B2307547A724B3FA40E1EF349C31F17646DEABD46ED`. | Builder validated manifest, protocol module, GOAL payloads, icon, and absence of Python cache files. |
| Protocol-2 OpenGOAL compile | Built all 1,165 targets in 47.618 seconds, then live-loaded the bridge with no observed `goalc` compiler error. | One official v0.3.5 environment; unrelated game diagnostics remain under `R-016`. |
| Protocol-2 live exchange | The actual Python transport accepted version `2/1`, received pongs `0 -> 1` and `1 -> 2`, and kept a duplicate at `0 -> 1`. | Satisfies the narrow handshake completion gate; it does not exercise room gameplay. |
| Protocol-2 targeted tests | 23 tests passed: lifecycle/snapshot (10), launcher (4), client boundary (7), and developer installer (2). | Python 3.9 used package/dependency stubs where the local Archipelago source requires a newer interpreter. |
| Earlier installed APWorld | The protocol-1 installed archive hash matched its then-current built artifact. | Historical installation evidence, not current runtime playability. |
| Earlier startup/title smoke | The wait overlay was removed, protocol 1 loaded, and the normal title level appeared. | Historical; protocol 2 does not perform a title handoff. |
| Earlier Python suite | All 73 tests passed with Python 3.12.10 against the then-packaged APWorld. | Historical scaffold/option evidence; the full suite was not rerun for protocol 2. |

The earlier protocol-1 referenced log pair is:

```text
D:\Program Files\Archipelago\logs\Jak3Client_2026_08_05_23_14_26_037551_29676.txt
D:\Program Files\Archipelago\logs\Jak3OpenGOAL_2026_08_05_23_14_26_037551_29676.txt
```

That earlier OpenGOAL log records `Successfully built all 1165 targets in 28.568s`,
removal of the flashing message, bridge verification, title dispatch, and
title-level load. Logs are local evidence and are not committed release
artifacts.

That protocol-1 combined log contains 79 `gk` error-level lines: 78 duplicate
texture/registration diagnostics and one reference-patching diagnostic. It has
zero `goalc` error-level lines and no matched nREPL/compiler-failure marker, and
the title still loaded. The `gk` lines have not been classified as harmless
across supported OpenGOAL versions; they remain visible under `R-016` rather
than being omitted from the successful compile claim.

The protocol-2 smoke used local files beneath `Jak3-AP\dist` named
`protocol2-gk.*.log`, `protocol2-goalc.*.log`, and
`protocol2-live-state.tmp`. The test-owned `gk` and `goalc` processes were
stopped after the successful exchange. These are local evidence and are not
committed artifacts.

## Integration and packaging matrix

| Behavior | Source | Automated | Smoke | Runtime acceptance | Current conclusion |
| --- | :---: | :---: | :---: | :---: | --- |
| Package required files/manifest | Yes | Builder and packaged-archive tests passed | N/A | N/A | Automated |
| Transparent 256×256 launcher icon | Yes | Builder self-validates alpha/dimensions | Launcher displayed previously | N/A | Smoke verified |
| Earlier native APWorld install | Historical artifact hashes matched | No automated launcher installer test | Protocol-1 package loaded | N/A | Historical smoke only |
| Launcher component registration | Yes | Package registration/component/icon tests passed | Jak 3 Client launched | N/A | Automated and smoke verified |
| OpenGOAL path discovery | Yes | Environment-override validation passed | Local v0.3.5 path resolved | Other layouts not exercised | Smoke verified on one layout |
| Atomic bridge/startup install | Yes | Idempotence test passed | Active files installed and compiled | Failure/locked-file scenarios absent | Smoke verified |
| `game.gd` registration ordering | Yes | Ordering/idempotence test passed | `archipelago.o` compiled after task control | N/A | Automated and smoke verified |
| Debug `gk` and `goalc` launch | Yes | Command-construction test passed | Both launched | Existing-process and cleanup cases incomplete | Smoke verified |
| Compile-wait overlay | Yes | Packaged payload checks passed | Observed through removal marker | Visual timing/failure behavior incomplete | Smoke verified |
| Full compile | Yes | N/A | 1,165 targets built | Version matrix absent | Smoke verified on v0.3.5 |
| Compiler error recognition | Incomplete | No | No error in successful smoke | Failure injection absent | Unverified/incomplete |
| Title-menu handoff | Retired | N/A | Protocol-1 title loaded previously | N/A | Deliberately absent from protocol 2 |
| Process cleanup | No | No | Prior windows remained open | No | Not implemented |

## Protocol-2 handshake matrix

| Behavior | Source | Automated | Runtime acceptance | Current conclusion |
| --- | :---: | :---: | :---: | --- |
| Client starts before game | Yes | Fake lifecycle case added | Not rerun live | Automated; runtime pending |
| Game starts before client | Yes | Fake lifecycle case added | Live runtime was running before Python attached | Narrow runtime accepted |
| Game restarts with client open | Yes | Lost pong plus re-hello case added | Not rerun live | Automated; runtime pending |
| Client restarts with game open | Yes | New-session replacement case added | Not rerun live | Automated; runtime pending |
| Protocol/integration mismatch | Yes | Expected/found exception cases added | Failure injection pending | Automated |
| Duplicate ping | Yes | Same pong and one logical increment asserted | Live duplicate remained `0 -> 1` | Runtime accepted for handshake state |
| Communication loss | Yes | No game-state mutation asserted | Runtime socket-loss pending | Automated |
| Torn snapshot | Yes | Missing/mismatched frame cases added | N/A | Automated |
| Real OpenGOAL source/hello/ping | Yes | N/A | Compile, version `2/1`, hello, and two pongs passed | Completion gate met |
| No gameplay paths | Yes | Source/client structural cases added | Live handshake caused no requested gameplay action | Automated plus narrow smoke |

Protocol 2 is the active runtime. It deliberately does not process items,
checks, goals, saves, rewards, or missions. The following table characterizes
the retained generator and retired protocol-1 history; it is not active runtime
acceptance.

## Retained scaffold generator and retired protocol matrix

| Behavior | Source | Automated | Runtime acceptance | Current conclusion |
| --- | :---: | :---: | :---: | --- |
| Explicit legacy table counts/IDs | Yes | Duplicate, explicit-record, determinism, and fingerprint tests passed | N/A | Automated for current registry |
| First-release registry and reservations | Yes | 26/28 item instances, 147 locations, duplicate/reorder/hash, independent frozen legacy snapshot, exact retained-concept mutation rejection, full retention/reservation, task 36/72/88, profile identifiers, and exclusions pass | N/A | Automated compatibility contract; generator activation deferred |
| Versioned first-release slot data | Yes | Deterministic JSON, fixed schema/versions/hashes/options, no redundant mappings, and Python/GOAL parity pass | N/A | Automated compatibility contract; runtime room validation deferred |
| Default option resolution/pinning | Yes | Exact normative/shipped YAML resolution, all 41 governed defaults, every non-default field, deterministic normalization, and raw-access boundary tested | N/A | Automated |
| Standard placement-control interactions | Partial | Core ownership is preserved; one start-inventory-from-pool boundary case is tested | N/A | Target-pool overcount, locality conflict, and early-guarantee cases remain deferred under `R-018` |
| 131-location pool balance/composition | Yes | Generation and exact-composition tests passed | N/A | Automated for current scaffold |
| Fixed-seed determinism | Yes | Seeds 0, 1, and 743000000 reproduced identical pools, locations, slot data, and early item | N/A | Automated narrow sample |
| Simple scaffold reachability | Yes | Empty-state, all-state, and restrictive-fill tests passed | No | Automated only |
| Scaffold receipt mapping | Historical source only | Retired from client/bridge | Historical only | Disabled by protocol 2 |
| Scaffold task completion mapping | Historical source only | Retired from client/bridge | Historical only | Disabled by protocol 2 |
| Snapshot parsing/binding | Historical | Protocol-1 tests replaced | Protocol-1 startup smoke only | Retired |
| HUD notification queue/encoding | Historical | Retired from client/bridge | No | Disabled by protocol 2 |
| Duplicate/reconnect replay | Historical | Superseded by harmless ping tests | No gameplay runtime | Retired |
| Offline location outbox | No | No | No | Missing |
| Save/reload reconstruction | Partial | No | No | Unverified/incomplete |
| Goal status | Task 71 logic exists | Legacy task-71 reachability and slot-data tests passed | No | Automated characterization; conflicts with spec |

## Normative first-release generation acceptance

None of the following release gates currently pass because the 147-location
default has not been implemented.

| Gate | Required evidence | Status |
| --- | --- | --- |
| Exact pool balance | 147 unfilled locations = 26 progression + 28 useful + 93 filler before traps. | Not implemented |
| Progression classification | Every item referenced by any default access-rule branch is progression. | Not implemented |
| All-state reachability | Every one of 147 enabled locations is reachable in `get_all_state()`. | Not implemented |
| Beatability | Task-72 Victory is reachable under the default. | Not implemented |
| No self-lock | Every reward/lesson/mission item is placeable without requiring itself. | Not implemented |
| Stable IDs | Explicit registry with retired-ID protection and deterministic hashes. | Automated for the first-release contract; runtime mismatch enforcement pending. |
| Exclusion safety | Orb thresholds >300 and side tasks 127/129/130/131/132/136 reject progression/useful placements. | Not implemented |
| Early route guarantee | Local Spargus Field Orders is immediately actionable. | Not implemented |
| Early ranged guarantee | Local Blaster or Vulcan Fury is in sphere zero. | Not implemented |
| Deterministic slot data | Versioned schema and table hashes are stable across identical generation. | Automated contract; complete generator activation awaits Milestone 5. |
| Fuzzing | 10,000 default seeds with sphere/branch/drought/relic/challenge metrics. | Not run |

The minimum all-state assertion remains:

```python
state = multiworld.get_all_state()
assert multiworld.has_beaten_game(state, player)
for location in multiworld.get_locations(player):
    assert location.can_reach(state), location.name
assert multiworld.fulfills_accessibility(state)
```

## Normative runtime item acceptance

For every default item, record first receipt, duplicate receipt, receipt beyond
native cap, and receipt during cutscene, vehicle use, death, loading, and
mission restart. Also record immediate save/reload, full replay from index zero,
and native reward reconstruction followed by AP reconciliation.

Current status: **not started for the normative item table**. The retained scaffold
bridge has additive receipt handlers, but that is not sufficient evidence for
the specified named items, ledger, caps, or safe-state behavior.

## Normative location acceptance

For each of 147 network locations, verify:

- first completion sends exactly once;
- replay does not create a new send;
- offline completion enters a durable outbox;
- reconnect drains pending checks;
- save/load retains completion; and
- permanent reward suppression does not block task closure.

Current status: **not started**. Task closure has a scaffold observation hook;
reward and orb checks and durable persistence do not exist.

## Normative bootstrap acceptance

For every mission profile, test start, completion, failure, retry, abort, death,
load, and permanent receipt while the overlay is active. The final native
inventory must match the AP ledger and a temporary grant must never fire a
location.

Mandatory scenarios:

| Scenario | Status |
| --- | --- |
| Task 11 finishes with temporary Dark Bomb; task 28 stays locked without permanent Dark Bomb. | Not implemented |
| Task 27 can return using temporary Invisibility Statues; task 28 stays locked without the permanent item. | Not implemented |
| Task 30 requires shuffled Launch and receives only non-counting Seal/amulet shadow state. | Not implemented |
| Task 63 receives all viewer props without increasing AP relic count. | Not implemented |

## Network and persistence acceptance

| Scenario | Status |
| --- | --- |
| Duplicate `ReceivedItems` packet | Not runtime tested |
| Nonzero packet index and packet gap | Explicit gap handling missing |
| AP client disconnect/reconnect | Not runtime tested |
| Game offline location completion | Durable outbox missing |
| OpenGOAL restart with same seed/slot/save | Not runtime tested; transient bridge state resets |
| AP client restart with same game process | Not runtime tested |
| New game and full receipt replay | Entry point exists; not runtime tested |
| Load another save then reconcile | Manual sync exists; full contract missing |
| Switch room/slot | Transient CRC binding resets live bridge; durable save policy missing |
| Goal-status resend after reconnect | Not runtime tested |

## Source audit coverage and limits

The maintained audit checks:

- task IDs and aliases 6–137, including task-88 normalization;
- story `close-task` coverage, with task 36 as the only omission;
- all 65 side-task close records;
- all 51 reward nodes classified 38/8/5;
- all 24 selected side-task source parents; and
- candidate milestone existence and owning task.

It does not prove:

- intended-route movement/combat predicates;
- bootstrap profiles or cleanup;
- native reward suppression correctness;
- save reconstruction or offline delivery;
- local-earned orb accounting or the ability to collect all 600 on an AP save;
- OpenGOAL version compatibility beyond the recorded environment; or
- real multiworld UI/network behavior.

## Evidence-recording template

For each future smoke or acceptance run, record:

```text
Date/time and tester:
Jak3-AP commit and worktree status:
APWorld version and SHA-256:
Archipelago version:
OpenGOAL version/commit and source-table hash:
Jak 3 decompile/project identity:
Seed, team, slot, and save identity (redact secrets):
Options file hash:
Scenario and expected result:
Actual result:
Client log path:
OpenGOAL log path:
Screenshots/video if useful:
Pass/fail and linked risk/issue:
Processes opened and cleanup confirmation:
```

Do not commit room passwords, connection tokens, private server addresses, or
unredacted user paths in public evidence.

Current build, package, install, and development commands are maintained in
[`../development.md`](../development.md).
