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
| Milestone 6 Python/APWorld suite | 147 tests passed on 2026-08-07 from the packaged APWorld installed in a disposable Archipelago copy, with bytecode and pytest cache writes disabled. | Covers schema/binding, exact version and journal types, strict deferred-container shapes, atomic writes, backups, corruption/quarantine, combined recovery/binding reporting, compatibility, OS writer locking, slot-data seed identity, authenticated client validation, package contents, and all prior static generation behavior; no live native descriptor or gameplay I/O. |
| Milestone 6 APWorld artifact | Built successfully with 30 entries; SHA-256 `A4C415999CE1B749D252840B1EBCA7DA53397A2FA97D83D942A083292BB3E827`. | Builder and packaged test require `jak3/persistence.py`; release reproducibility and live binding remain later evidence. |
| Milestone 6 static checks | Ruff lint/targeted format, mypy including persistence, and all six source-table audit groups passed; both Git-backed reference trees remained clean. | Automated storage/source evidence only; no real-game save observation. |
| Milestone 5 Python/APWorld suite | 108 tests passed on 2026-08-07 from the packaged APWorld installed in a disposable Archipelago copy, with bytecode and pytest cache writes disabled. | Covers the exact static pool, registry multiplicities/classifications, all location families/events, exclusions, fixed-seed filler output, hashes, options, slot data, package imports, and archive contents; no Standard logic or gameplay runtime behavior. |
| Milestone 5 APWorld artifact | Built successfully with 28 entries; SHA-256 `5E828817BFCF097BF4D72D4616E33E95A6E23CEEE9047F12DE350329B889D5AD`. | Local artifact evidence; release reproducibility and runtime installation remain later milestones. |
| Milestone 5 static checks | Ruff lint/targeted format, mypy compatibility-module checks, and all six source-table audit groups passed. | Static/source evidence only. |
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
checks, goals, native saves, rewards, or missions. Python schema-1 persistence
is active as a tested library but awaits the Milestone 7 live save descriptor.
The following table characterizes
the active static generator and retired protocol-1 history; it is not active
runtime acceptance.

## Static generator and retired protocol matrix

| Behavior | Source | Automated | Runtime acceptance | Current conclusion |
| --- | :---: | :---: | :---: | --- |
| Explicit legacy table counts/IDs | Yes | Duplicate, explicit-record, determinism, and fingerprint tests passed | N/A | Automated for current registry |
| First-release registry and reservations | Yes | 26/28 item instances, 147 locations, duplicate/reorder/hash, independent frozen legacy snapshot, exact retained-concept mutation rejection, full retention/reservation, task 36/72/88, profile identifiers, and exclusions pass | N/A | Automated compatibility contract and active generator |
| Versioned first-release slot data | Yes | Deterministic JSON, mandatory generated seed identity, fixed schema/versions/hashes/options, authenticated `Connected` validation, no redundant mappings, and Python/GOAL parity pass | No gameplay runtime | Automated Python room contract; GOAL gameplay use deferred |
| Default option resolution/pinning | Yes | Exact normative/shipped YAML resolution, all 41 governed defaults, every non-default field, deterministic normalization, and raw-access boundary tested | N/A | Automated |
| Standard placement-control interactions | Partial | Core ownership is preserved; one start-inventory-from-pool boundary case is tested | N/A | Active-pool overcount, locality conflict, and early-guarantee cases remain deferred under `R-018` |
| 147-location pool balance/composition | Yes | Exact 147/26/28/93/0 generation, registry multiplicities/classifications, and pool-to-unfilled-location balance pass | N/A | Automated for Milestone 5 |
| Fixed-seed determinism | Yes | Seeds 0, 1, and 743000000 reproduce identical complete generation snapshots; seed 0 freezes the exact 93-item weighted filler output | N/A | Automated narrow sample |
| Permissive scaffold reachability | Yes | Empty-state reachability of every network location and all code-less events passes | No | Automated temporary scaffold only; not Standard logic evidence |
| Scaffold receipt mapping | Historical source only | Retired from client/bridge | Historical only | Disabled by protocol 2 |
| Scaffold task completion mapping | Historical source only | Retired from client/bridge | Historical only | Disabled by protocol 2 |
| Snapshot parsing/binding | Historical | Protocol-1 tests replaced | Protocol-1 startup smoke only | Retired |
| HUD notification queue/encoding | Historical | Retired from client/bridge | No | Disabled by protocol 2 |
| Duplicate/reconnect replay | Historical | Superseded by harmless ping tests | No gameplay runtime | Retired |
| Offline location outbox | Schema only | Empty/outbox relationship and atomic round-trip tests pass | No | Storage contract present; game population/drain missing |
| Save/reload reconstruction | Python sidecar only | Clean/unclean reload, binding, revision, backup, and switching tests pass | No | Automated opaque-descriptor engine; live GOAL identity/reconciliation missing |
| Goal status | Task 72 code-less event and event-item completion condition exist | Event identity, no network code/pool slot, and task-71 network location are tested | No | Generator correct; Standard finale logic and runtime reporting deferred |

## Normative first-release generation acceptance

Milestone 5 passes the static-data gates below. Standard reachability,
beatability, self-lock analysis, and early guarantees remain Milestone 12 work;
the permissive scaffold must not be used as evidence for those gates.

| Gate | Required evidence | Status |
| --- | --- | --- |
| Exact pool balance | 147 unfilled locations = 26 progression + 28 useful + 93 filler before traps. | Automated; passed for Milestone 5. |
| Progression classification | Every item referenced by any default access-rule branch is progression. | Static registry classifications are automated; access-rule coverage awaits Milestone 12. |
| All-state reachability | Every one of 147 enabled locations is reachable in `get_all_state()`. | Trivially automated for the permissive scaffold; Standard evidence awaits Milestone 12. |
| Beatability | Task-72 Victory is reachable under the default. | Event plumbing is automated but immediate; Standard finale evidence awaits Milestone 12. |
| No self-lock | Every reward/lesson/mission item is placeable without requiring itself. | Not meaningful until Standard rules exist; deferred to Milestone 12. |
| Stable IDs | Explicit registry with retired-ID protection and deterministic hashes. | Automated for the first-release contract; runtime mismatch enforcement pending. |
| Exclusion safety | Orb thresholds >300 and side tasks 127/129/130/131/132/136 reject progression/useful placements. | Automated; all exact 18 exclusions pass. |
| Early route guarantee | Local Spargus Field Orders is immediately actionable. | Not implemented |
| Early ranged guarantee | Local Blaster or Vulcan Fury is in sphere zero. | Not implemented |
| Deterministic slot data | Versioned schema and table hashes are stable across identical generation. | Automated contract; active generation leaves the frozen schema and hashes unchanged. |
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

Current status: **static table generation complete; runtime acceptance not
started**. The active protocol has no gameplay receipt handlers, durable ledger,
caps, or safe-state behavior.

## Normative location acceptance

For each of 147 network locations, verify:

- first completion sends exactly once;
- replay does not create a new send;
- offline completion enters a durable outbox;
- reconnect drains pending checks;
- save/load retains completion; and
- permanent reward suppression does not block task closure.

Current status: **all identities generated; runtime acceptance not started**.
Protocol 2 has no task/reward/orb check submission or durable persistence.

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

Milestone 6 establishes the storage boundary below. “Automated” here does not
mean real-game runtime acceptance.

| Storage scenario | Automated evidence | Runtime conclusion |
| --- | --- | --- |
| Fresh creation and one-time binding | Eligible/ineligible creation, bind/reload, duplicate load, and rebinding rejection pass. | Live identity/freshness source deferred to Milestone 7. |
| Atomic commit and restart | Monotonic revision, clean/unclean restart, stale state, and interrupted-write injection pass. | No live game process has populated state. |
| Backup and quarantine | Missing/corrupt primary recovery, retained backup, corrupt backup, checksum failure, and collision-safe quarantine preservation pass. | Filesystem behavior automated; operational recovery not runtime accepted. |
| Read-only rejection | Old/new schema, all compatibility fields, unsupported IDs, seed/team/slot/name/native-slot mismatches, and incompatible backup cases preserve bytes. | Python boundary automated; GOAL gameplay boundary absent. |
| Save switching/copies | Opaque identity sidecar selection, original-slot restore, wrong-slot copy rejection, and switching pass. | Cross-machine divergent copies explicitly unsupported. |
| Concurrent writers | Same-process guard and a second real Python process are rejected nonblocking by the root OS lock. | Same-machine policy automated. |
| Offline AP server | ADR permits continued game-side commits with Python running. | No game progress transport exists yet, so this remains design support, not gameplay evidence. |

| Scenario | Status |
| --- | --- |
| Duplicate `ReceivedItems` packet | Not runtime tested |
| Nonzero packet index and packet gap | Explicit gap handling missing |
| AP client disconnect/reconnect | Not runtime tested |
| Game offline location completion | Outbox schema exists; game population and drain are missing. |
| OpenGOAL restart with same seed/slot/save | Sidecar reload is automated against an opaque descriptor; live bridge identity remains untested. |
| AP client restart with same game process | Clean/unclean sidecar reload is automated; live game observation remains untested. |
| New game and full receipt replay | Journal schema exists; the item stream and replay transport are missing. |
| Load another save then reconcile | Sidecar switching is automated; live save observation/reconciliation is missing. |
| Switch room/slot | Durable Python binding rejects the mismatch read-only; live save switching remains untested. |
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
