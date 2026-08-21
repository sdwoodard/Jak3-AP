# Milestone 11 feasibility decisions

Milestone 11 is complete as a seven-spike investigation. Every spike has a
terminal, evidence-backed disposition: task 30 and task 63 are `PASS`; Haven
uses the predefined `SAFE FALLBACK`; Jetboard Launch, native save
reconstruction, 600-orb availability, and the complete side-challenge matrix
are `BLOCKED`. A completed investigation is not release feasibility: each
blocked result remains a hard carry-forward gate in the named future milestone.

The provenance-complete Haven successor proved the independent task-35
candidate lacks required actors and accepted only the predefined convergence
gate. The provenance-complete side successor proved original price `8`, the
typed zero-cost override, zero Skull Gem spend, challenge activation, and
activation persistence. Its ordinary reload simultaneously reproduced the
native-reconstruction leak, changing unrelated native/AP state, so testing
stopped before course controls and the full side spike is `BLOCKED` rather than
partially promoted.

Earlier reviews invalidated a scoped Jetboard `PASS`, aliased task-30/task-63
observations, and legacy positive runs without per-boundary provenance. Those
immutable artifacts remain diagnostic history; only the current correlations
in the decision table are authoritative. No production gameplay module, public
location, option, collectible catalog, supported default, or ID table was
expanded. The sole canonical design change is the predefined Haven fallback.

The reusable live-connection, operator, save-protection, and stop procedure is
in [`milestone-11-operator-testing.md`](milestone-11-operator-testing.md).
Verification and release consequences are tracked in
[verification-matrix.md](verification-matrix.md),
[specification-gap-matrix.md](specification-gap-matrix.md), and
[JAK3_AP_RISKS.md](../JAK3_AP_RISKS.md).
## Evidence boundary

- `jak-project` revision:
  `425f143fccada9e38b35633bd298b5b64c6ca6e8`
- `Archipelago` revision:
  `feab54daec712ffb333b8c73f38eb69e1ed9c508`
- Runtime: OpenGOAL 0.3.5 with matching decompile snapshots.
- Acceptance evidence root:
  `D:\Codex\Jak3\tmp\milestone11-runtime-evidence`; immutable successor
  reviews are under `D:\Codex\Jak3\tmp\milestone11-final-decisions`.
- UI slots 1 and 2, plus every material UI-slot-3 and UI-slot-4 successor boundary, were
  backed up outside the repository before resumed testing. The backup banks
  are recovery artifacts and are not packaged.
- A procedure finishing successfully is distinct from feasibility. A
  reproducible leak, invalid numeric control, or missing required checkpoint is
  `BLOCKED` even when every executed command completed.
- Final acceptance hardening never rewrites immutable run artifacts, but it
  applies to every positive terminal decision. Historical runs without the
  required provenance remain diagnostic evidence only. Every live stage and
  capture requires a fresh, previously unconsumed bridge snapshot whose native
  slot matches the run, whether or not
  the AP client's existing target attachment is reused. The run records that
  snapshot's SHA-256, bridge revision, native slot, and age at each boundary.
  Task-30/task-63 acceptance requires exact-zero independent native task,
  mission, and reward masks. Native reconstruction requires and compares those
  masks at all five checkpoints. A run is not terminally accepted until its
  sanitized support bundle is complete and hashed. A 600-orb
  successor requires all four bounded source-family observations at `at_600`
  as non-negative integers whose sum is the locally earned total, and derives
  its AP Orb Pack receipt count from the checksummed, save-bound AP state
  instead of accepting a manual value.

## Live connection and recovery record

The AP client owned the OpenGOAL target attachment. For the first attached
session, the authoritative paired files were:

- managed target/compiler log:
  `D:\Program Files\Archipelago\logs\Jak3OpenGOAL_2026_08_14_16_13_25_059719_5688.txt`;
- bridge snapshot:
  `C:\Users\steph\AppData\Local\Temp\jak3-ap-2026_08_14_16_13_25_059719_5688.tmp`.

The session suffix must match. The active project's `jak3-ap-state.tmp` was only
the superseded startup path, and raw compiler logs were not the managed
acceptance stream. Before every live stage or capture, the runner requires a
snapshot no more than five seconds old, equal begin/end revisions,
`connection_ready=game_running=source_loaded=1`, and the run-owned native save
slot. Reusing an attachment changes only whether `(lt)` is sent; it no longer
changes snapshot validation.

Load `worlds/jak3/agents/repl_client.py` through the runner's synthetic
`_m11_project_worlds` package so the global Archipelago world registry and its
unrelated optional dependencies are not initialized. With
`--reuse-attached-target`, connect to nREPL but skip `OpenGoalRepl.attach()` and
therefore skip `(lt)`. A second `(lt)` stalls for roughly 18 seconds because the
AP client already owns the target. When both paired files are supplied, the
snapshot is validation-only and restricted `M11_STATE` output is read from only
the newly appended managed-log bytes. Snapshot-only mode is reserved for the
Jetboard `test-target` mask and resets that field in `finally`.

Attached-target staging additionally requires title/loading/cutscene/death/
restart/transition/vehicle flags all clear and
`safe_to_mutate_mission_state=1`. Before the Jetboard successor, UI slot 1 was
left at `wasstada`, task 63, node 244, above lava with `dying_or_dead=1` after
ordinary Restart Mission failed. No unsafe debug recovery or save followed on
that slot.

The Jetboard successor used newly created normal-mode UI slot 3 (native slot
2). The first AP-bound baseline was backed up before any inventory mutation.
The test-only runner suspended the production permanent-item reconciliation
hook while it staged exact native masks and restored the production hook at
the end of ordinary preset captures. Task-30 captures intentionally reused the
same suspension without replaying a scene transition. The full restart used a
new matched session:

- managed target/compiler log:
  `D:\Program Files\Archipelago\logs\Jak3OpenGOAL_2026_08_14_20_19_23_281222_29680.txt`;
- bridge snapshot:
  `C:\Users\steph\AppData\Local\Temp\jak3-ap-2026_08_14_20_19_23_281222_29680.tmp`.

Connection audit corrected an operator/setup discrepancy: the live client was
bound throughout to the one-player canonical-default room on port 38281,
archive `AP_85141192197545812499.zip`, SHA-256
`7B6722EB50A69DE8B4112CC047E4F03CCA99A24107468B87A40FFA85C5FB842F`.
The separately generated fresh canonical room on port 38282 never received a
connection. The 38281 room already had nine server items and eight reported
locations, so it is not fresh-ledger evidence. This did not alter the native
mask controls: reconciliation was suspended and both attempted item-cheat
receipts were rejected before persistent or native mutation. `Jetboard`
arrived at index 9 while the bounded ledger expected 0; `Jetboard Launch` was
correctly rejected as outside the implemented Milestone 8 three-item slice.

The clean Haven successor used a fresh room at `127.0.0.1:38283`, the same
immutable seed archive hash, and newly created normal-mode UI slot 4 (native
slot 3). Its installed deterministic APWorld was 247,243 bytes with SHA-256
`C23B752D04C1E96D23FA9F17361AEAF28F50D76FF2B2B8F196069DD18E1E7D35`.
Both physical banks were backed up before staging: `bank6.bin` SHA-256
`789ED0AF2B168E3D2B9D490AA9221F36FE4E412FB923688AAEC2DDFCCEFD9467`
and `bank7.bin` SHA-256
`5A9AE748590652635E20B19C9C8FAAB377172328DC443C6C941CFE90441C6266`.
The session-matched managed log and snapshot were
`Jak3OpenGOAL_2026_08_15_20_42_57_956851_1704.txt` and
`jak3-ap-2026_08_15_20_42_57_956851_1704.tmp` respectively.

At the operator's request, both UI slots were backed up outside the repository
before resumed use:

- UI slot 2:
  `D:\Codex\Jak3\tmp\milestone11-save-backups\20260814T1558Z-ui-slot2-pretest`;
  `bank2.bin` SHA-256
  `F535F77FFF5C02BDAD2F5F2120208A2FF362EE2673728A0B93B0757188B3B9B0`,
  `bank3.bin` SHA-256
  `13E49FEB944400D63923CB210ADE5F5BD7B8558C6DB2A3204BBF06A899DC9FEA`;
- UI slot 1:
  `D:\Codex\Jak3\tmp\milestone11-save-backups\20260814T2035Z-ui-slot1-pretest`;
  `bank0.bin` SHA-256
  `8B1657D9D5B5C394ABC99E75D9AFAD607172DCE03E7929707C40F2B9F6BE532D`,
  `bank1.bin` SHA-256
  `C4BD92F9A2DA960A8A473A7BFE3B087BA1217D185450D345CDB7AACECA66927C`.
- UI slot 3 pre-persistence boundary:
  `D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-14T1815-ui-slot3-pre-persistence`;
  `bank4.bin` SHA-256
  `FF475887FCB814AF2423253A6E9ECBFB5660EE445BF38D6CE2C2C8A3D8E7D49B`,
  `bank5.bin` SHA-256
  `D609F869505ED51DA28854374B791AFB997BF08A576BE235C9FDCAEC4B4FCFA4`;
- UI slot 3 post-failure boundary:
  `D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-14T1821-ui-slot3-post-persistence-failure`;
  `bank4.bin` retained the preceding hash and newly written `bank5.bin` had
  SHA-256
  `D53C5BF5D43A5322FEA12EF384296018711BBADDEF887548B3A1891052C58669`.

Source and backup hashes matched. These banks are recovery artifacts only and
must never be committed or placed in a support bundle.

The source audit matched all required anchors between `jak-project` and
`openGOAL-decompile`:

| Audited source | SHA-256 |
| --- | --- |
| `engine/game/game-info-h.gc` | `ba260a261b169f9a0583ef0830f05d6c4eb6ba9f50e5d860aa2ae06956ecf1ee` |
| `engine/game/game-info.gc` | `6af1744eea5013475fd33c3aa9a63d301acea47a9527bc3ead269d8d3d489f0e` |
| `engine/game/settings-h.gc` | `b2e8f421436ecbc2b88adf527f45e92d8829539ba0fae0f025d5383d3b0e3ef0` |
| `engine/game/task/game-task.gc` | `0a6a9f7385e0707e3a60c44ed89409df71126f6da162a9de0a2ccc3f1b004429` |
| `engine/game/task/task-control.gc` | `53f41380cba39ed093f643b60167d237e5735d4db422d7c31e1810f222501dca` |
| `engine/util/script.gc` | `dd6036391834497a0606edf2d8a412383421c11e62e21bf069ad5317df44375e` |
| `engine/target/board/target-board.gc` | `e16b49294263a05cf9bdc69b696659ba3cbbdf10a248a3cce227ffd77e7f7bf0` |
| `engine/target/target-handler.gc` | `23728f9d97fe6b44c16a1572fdecb6dc1659622515640a9ce453acdc769c860c` |
| `engine/game/game-save.gc` | `677658e6e9e7eb6b8f6ee97b6f6541367e0946bee852913a618146bb08ce4ab2` |
| `levels/temple/temple-scenes.gc` | `e6844fe5aae1ce9171522ff641897ba9e3160d084d0085fee10057c27c3aea37` |
| `levels/forest/forest-tasks.gc` | `e643cef487b71afcae61c14207e88c77d51bb5558b0d9c2331f6029b9957bf9f` |
| `levels/desert/des-burning-bush.gc` | `b107b56c25463198f338ce6037b1dfbab2b82cd61c7fbc9c518d0e628ae13d40` |
| `levels/gungame/gungame-manager.gc` | `51ebb791df6950e5c121feebc7ce3ae2d08a1ed2dd416603f882e38fc65a714d` |

## Decision summary

| Spike | Decision | Current evidence correlation | Bundle SHA-256 |
| --- | --- | --- | --- |
| Haven task 35 | `SAFE FALLBACK` | `m11-haven-task-35-fc238cee` | `9f67499cc22803689ec75ef6e5db64fec6188eaa57eee8c792de29a182ae7be3` |
| Jetboard Launch | `BLOCKED` | `m11-jetboard-launch-3a1163b5`; corrected persistence `m11-jetboard-launch-2e22a7b0` | `e4274f30e4c85a66a579414bbe4decc689d630b4cdd3fb32c804d554762b29f6`; `35ad2e9de7ce00691ef44d540a7740aea26fc7a1883bac2ca755fdf42f711110` |
| Task 30 native portal state | `PASS` | `m11-task-30-shadow-87b40f81` | `3a5d265d2589ad7d524a6bc51a788744b724fed2d75a29fe0ab895a7462ff7e5` |
| Task 63 viewer props | `PASS` | `m11-task-63-viewer-7aa9d3b9` | `513af462c008d1c969853931f8dd6021791c6c6115c0590ee1e27125b57ef82e` |
| Native save reconstruction | `BLOCKED` | `m11-native-reconstruction-e920e187` | `beeb9dacc4ee27ab7e57d7376d87a287b67cb1ec84a6745c4899f58294040e39` |
| 600-orb availability | `BLOCKED` | `m11-orb-600-e8d7eed7` | `bb1dca3265620d3edf52078cb5f39a6c37cfc4f1bc5f99f4ab4087e75d802e59` |
| Default side challenges/course access | `BLOCKED` | `m11-side-challenges-15ecab70` | `dfd55540da5d08c46d2047305d8a6638050f5b95e4e732fd03d666a98be9199a` |
## Haven task 35 - SAFE FALLBACK

- **Source evidence:** `game-task.gc:322-328` identifies task 35
  (`sewer-met-hum`) and its city/sewer continuations; `game-task.gc:7248-7331`
  defines the introduction, required actors, resolution, and parent chain.
- **Procedure:** from the clean disposable native slot 3, capture the independent
  candidate before entry and at mission start without closing tasks 14-34.
  Require stable task/mission/reward/item/AP controls, playable geometry, and an
  exact actor mask. The fallback validator accepts actor absence only when all
  isolation controls remain stable and the operator agrees with the mask.
- **Observed values:** `before_entry` and `mission_start` both recorded task,
  mission, reward, item, Jetboard, AP checked, and AP inventory masks `0`; loaded
  level mask `7`; passage mask `1`; and actor mask `0`. Geometry remained
  playable, while the operator independently confirmed Samos and Keira were not
  visible. The run did not synthesize task 34 or any task 14-34 completion.
- **Evidence:** terminal correlation `m11-haven-task-35-fc238cee`; final
  `run.json` SHA-256
  `493A0EB0B9E858CDC6D9A0BDDE68A2D80EDB663C7161840E3D90C73063B76E39`;
  complete sanitized bundle SHA-256
  `9F67499CC22803689EC75EF6E5DB64FEC6188EAA57EEE8C792DE29A182AE7BE3`.
  The two capture boundaries used unique native-slot-3 snapshots at revisions
  `1101/1116`, SHA-256
  `F51565ABFED7133457DC595796BC4CF8E10716D005239627EF9D51889DEB61BC` and
  `384C06DFDAAB7F15DE70C7EE6B2744AEC65DD913D5FA035B871AF7D8E6CA75CA`.
  Legacy and AP-input-incomplete attempts remain superseded diagnostics.
- **Decision/specification correction:** accept the first predefined fallback:
  task 35 requires `Haven City Access + DONE(34) + Jetboard + RANGED`. Retain
  the tiered mission order; this convergence does not switch the whole beta to
  vanilla order. Never synthesize tasks 14-34.
- **Risk/future milestone:** Milestone 18 implements the converged mission-board
  rule, and Milestone 19 proves the production task-35 bootstrap/actor profile
  without reward replay. `SAFE FALLBACK` is an accepted logic decision, not a
  production-runtime `PASS`.
## Jetboard Launch - BLOCKED

- **Source evidence:** `target-board.gc:2179-2184` tests the native
  `board-launch` feature separately from board ownership.
- **Procedure:** from a new normal-mode disposable slot, capture exact native
  masks `0`, `1`, `3`, and `2`; exercise board deploy/move/jump and a held-L1
  charged jump; repeat base-only and base-plus-Launch at the same task-30
  tutorial geometry; then ordinary-save/load and restart the client, `gk`, and
  `goalc`. Test-only reconciliation suspension isolated native feature
  semantics from the deliberately incomplete production receipt slice.
- **Observed values:** all six in-memory controls were exact and internally
  consistent. Mask 0 had neither board nor charged move. Mask 1 deployed,
  moved, and jumped the board but did not charge. Mask 3 added the charged
  move. Mask 2 retained the Launch bit but could not deploy a board. At the
  same flooded-Temple tutorial, mask 1 lacked the charged jump and mask 3 had
  it. Immediately before save the mask was 3 and the board worked. Ordinary
  save/load produced exact mask 0 and no deploy; a clean full-process restart
  and reload again produced mask 0 and no deploy. Both persistence assertions
  failed at both generations. Raw bank inspection then proved the newly written
  bank contained the complete pre-save feature value, including exact mask 3,
  at offsets 68, 1096, 1728, and 123972. Native task reconstruction resets
  features and replays rewards from closed task nodes; this synthetic state did
  not own task 29's reward, so the direct grant was not replayed. The client
  remained paused during the rejected item-cheat attempts, but those attempts
  cannot explain the loss because they never mutated the ledger and the
  suspension sentinel remained active across ordinary load.
  A 2026-08-16 successor then authenticated to a fresh room on port 38284,
  delivered supported Jetboard at the bounded ledger start, and verified AP
  native target `1`. Its ordinary save again contained the exact mask-`3` full
  feature value at offsets 68, 1096, 1728, and 123972. The first reload was
  excluded because the test suspension was still active. After the new
  stage-only handoff restored production reconciliation, the repeated load
  produced exact mask `1`: board deployment worked, charged Launch did not,
  base ownership passed, and Launch reconstruction failed. This isolates the
  shipping gap to Launch rather than base Jetboard, serialization, endpoint,
  slot choice, or operator input.
- **Evidence:** accepted blocking run `m11-jetboard-launch-3a1163b5`, immutable
  `run.json` SHA-256
  `531823f3ba467c6e4bf6e724aa6669eb6f9e4d8c3a3909165f86a7bd0a5ffd4f`;
  complete sanitized bundle SHA-256 is in the summary table. Scoped review
  `m11-jetboard-launch-review-ef8737dc` and its bundle SHA-256
  `14a756f6ba7e2bb79f405511cf27f479358e5557c0a4c14fe7d714eefd49d08f`
  remain immutable superseded evidence because that review ignored two failed
  persistence assertions and accepted masks `0` where the matrix required `3`.
  The older
  `m11-jetboard-launch-6c943eae` and
  `m11-jetboard-launch-review-75a32451` remain immutable superseded evidence.
  A first successor `m11-jetboard-launch-a3a07828` was also finalized
  `BLOCKED`, bundle SHA-256
  `1f090d7cd21a7bc6579a84063c75725f861d037b4c2893a9b603d0615e2de599`,
  after empty-ledger production reconciliation invalidated its base-only
  operator checkpoint.
  The invalid suspended-load correlation
  `m11-jetboard-launch-5b7a791b` is finalized with `run.json` SHA-256
  `946635a3a4c865fe9e0f68ff67604c9112afdc38e049e7c2fe26b34c387dc210`
  and bundle SHA-256
  `165034ea9951c49c4394f5aab14bb23212f826735289ae1ec194f09354b3add6`.
  Corrected persistence correlation `m11-jetboard-launch-2e22a7b0` is finalized
  with `run.json` SHA-256
  `dffeb15129266802c87bcc3b6f271943d2421d00ae3657b492b563bfa19f33fa`
  and bundle SHA-256
  `35ad2e9de7ce00691ef44d540a7740aea26fc7a1883bac2ca755fdf42f711110`.
- **Decision/specification correction:** `BLOCKED`. In-memory behavior strongly
  supports separate bits, but the complete required matrix did not pass. Do not
  activate the merge/retire fallback because inseparability was not demonstrated,
  and do not treat the reserved Launch item as shippable while its persistence/
  application path is unproved. Registry IDs, versions, hashes, counts, and
  default YAML remain unchanged pending the required successor.
- **Risk/future milestone:** Milestone 14 must add
  the separately audited Launch receipt/application path and reproduce exact
  mask 3 across ordinary native save/load and full client/game restart without
  diagnostic suspension before item application can ship. That successor must
  pass the full Jetboard matrix and may not use a semantic-only review.

## Task 30 native portal state - PASS

- **Source evidence:** `temple-scenes.gc:318-320` opens `tpl-mardoor-4` and
  closes the task introduction from scene/task state.
- **Procedure:** stage the scene first, then capture none, Seal-only,
  amulets-only, and all-four combinations. Required exact item masks were
  `0`, `16`, `7`, and `23`; each capture also required portal presence/open,
  task-node closure, and unchanged AP relic count.
- **Observed values:** after the scene loaded, direct closure of only the named
  introduction-node flag and a typed door-open event produced portal
  presence/open `1/1` and node closed `1`. The door opened after three
  unpaused seconds without Jak moving, excluding the suspected proximity
  trigger. In that stable scene the four exact item masks were `0`, `16`, `7`,
  and `23`. The corrected runner independently read task-perm, closed mission
  nodes, and ten bounded reward nodes as `0/0/0` at every variant. The
  same-slot checksummed AP ledger derived relic/check controls `0/0` throughout.
  Both protected save-bank hashes remained unchanged. The historical aliased
  query and its corrective review remain immutable superseded evidence rather
  than support for this decision.
- **Evidence:** accepted correlation `m11-task-30-shadow-87b40f81` has final
  `run.json` SHA-256
  `6903C32B28A4A1B89187456C52313BBC69DFAD97D592D34D5EA7E0143A36A965`;
  its complete sanitized bundle SHA-256 is in the summary table. Historical
  source correlation `m11-task-30-shadow-7d579864` and corrective review
  `m11-task-30-shadow-review-fb327917` remain immutable superseded evidence.
  Setup retries
  `m11-task-30-shadow-850109eb`, `m11-task-30-shadow-fd7d4cdd`, and
  `m11-task-30-shadow-682ce329` preserve the wrong-method, typed compiler, and
  public-task-close reward-replay failures; none accepted an inventory control.
  Later incomplete correlations `m11-task-30-shadow-8a041a4e` and
  `m11-task-30-shadow-81aba654` preserve missing checksummed-state and missing
  procedure-assertion recorder defects; both were bundled and superseded.
- **Decision/specification correction:** `PASS`. The source-owned portal and
  presentation node do not depend on the Seal/amulet item bits, and the exact
  bounded isolation controls prove the simplified presentation procedure is
  feasible. Production code still must not call public task closure,
  traverse parents, complete native tasks, replay rewards, increment AP relics,
  or publish checks.
- **Risk/future milestone:** Milestone 19 may consume the portal/bootstrap
  behavior evidence. Milestone 20 may consume this accepted task-30 feasibility
  input, but must still implement and prove the production story-state lifecycle
  through mission entry, cleanup, failure, and load boundaries. This `PASS` is
  not permission for Milestone 11 production code.

## Task 63 viewer props - PASS

- **Source evidence:** `forest-tasks.gc:903-910` defines the
  `forest-turn-on-machine-res` scene; `game-task.gc:13779-13852` owns its
  resolution sequence.
- **Procedure:** from separate clean process starts on disposable UI slot 4,
  reach `forest-pillar-start`, spawn only the registered resolution scene,
  pause when the telescope presentation is active, and capture artifact masks
  `0` and `1984`, both scene-owned actors, native task state, AP relic count,
  and AP check mask. End the clear variant by closing the paused process without
  loading or saving and prove both save banks unchanged.
- **Observed values:** clear and set checkpoints captured exact artifact masks
  `0` and `1984`; both had registered/active viewer scene `1/1`, telescope plus
  time-map actor mask `12`, AP relic count `0`, and unchanged AP checked mask
  `0`. A historical pre-activation synthetic set was lost
  and is preserved as a superseded `BLOCKED` timing diagnostic; applying the
  five allowlisted bits after the scene was active and paused produced exact
  `1984`. The corrected successor independently captured task/mission/reward
  masks `0/0/0` for both clear and set variants and proved both protected save
  banks unchanged across the mandatory process boundary. Source inspection
  independently shows the scene owns both actors and contains no five-bit
  predicate. Historical aliased fields remain superseded evidence.
- **Evidence:** accepted correlation `m11-task-63-viewer-7aa9d3b9` has final
  `run.json` SHA-256
  `CBD252352B5537E024AF2EF9351FC68955A36B862023658BE6038968B03E83CD`;
  its complete sanitized bundle SHA-256 is in the summary table. Historical
  source correlation `m11-task-63-viewer-711ef05e` remains
  immutable useful scene evidence, with post-bundle `run.json` SHA-256
  `0b9d45ba21af2175dbb7957ad1e9dfe0580c9fe1b9ae7a81d21fe5b5b16577f0`.
  Corrective review `m11-task-63-viewer-review-a98ab064` remains immutable
  superseded evidence, with `run.json` SHA-256
  `23A404ECCFA50006021D4BEC3F1F389099DB30CF1DA0E44133C31279DF743745`;
  its complete sanitized bundle SHA-256 is in the summary table. Superseded timing
  run `m11-task-63-viewer-6cc25eb3` remains immutable with `run.json` SHA-256
  `f3254bf2604782bc0c2af8b74a0115c0d9cb0fce956caabc43b832526d138de5`
  and bundle SHA-256
  `30af4acb39322fdf973376fc6a437695fb3ea4337270c479974a173b4efbfe0e`.
- **Decision/specification correction:** `PASS`. The exact five artifact bits
  are independently isolated from the source-owned telescope/time-map scene;
  neither item profile is required to make those actors available. Do not infer
  that the scene actors depend on the bits, and do not use public task closure
  or reward replay to supply them.
- **Risk/future milestone:** Milestone 20 may consume this accepted feasibility
  result, but must still implement and prove the full production shadow-profile
  lifecycle, including idempotent cleanup, death, abort, load, restart, and
  preservation of legitimate native changes.

## Native save reconstruction - BLOCKED

- **Source evidence:** `game-save.gc:603` and `game-save.gc:1672` define native
  save/load; `game-save.gc:947-949` writes `skill-total` and
  `game-save.gc:1860-1861` restores it. Task reward commands are separately
  replayed from native task state.
- **Procedure:** successor `m11-native-reconstruction-e920e187` staged the
  bounded native target/reward controls on the disposable bound slot, captured
  `before_save`, performed ordinary save and ordinary load, captured
  `after_native_reload`, closed the game/client/compiler without saving,
  relaunched and loaded the same slot, and captured `after_game_restart`,
  `after_ap_reconcile`, and `after_item_replay`. Every checkpoint derives AP
  inventory, ledger revision, and checked bits from the checksummed state and
  captures the exact live native slot/save identity and typed native fields,
  including native task and mission masks. Repaired checkpoints compare both
  masks with the pre-save baseline instead of treating their mere presence as
  sufficient.
- **Observed values:** before save, the bounded AP ledger contained only
  Jetboard (`ap_inventory_mask=1`), native permanent target `1`, native
  items `2015`, task-perm mask `0`, non-AP feature mask
  `396318553924436992`, and checked mask `128`. Ordinary reload expanded
  items to `262143`, task-perm mask to `4194303`, non-AP features
  to `571903997079846336`, and checked mask to `255`. Full process restart,
  both completed target-`1` reconciliations, and index-zero item replay retained
  every leaked value. The server replayed nine entries; the original Jetboard
  remained the only supported receipt, while index `1` was rejected before
  mutation as `item_outside_milestone_8`. Thus the client ledger stayed bounded
  even though native state and AP checks did not. The historical generic reward
  mask was aliased to items and the mission mask to task-perm, so their numeric
  duplicates are excluded. The blocker remains conclusive because the
  independently observed inventory, task-perm, non-AP feature, and AP-check
  fields all expanded and persisted across the complete lifecycle.
- **Evidence:** accepted terminal run `m11-native-reconstruction-e920e187`,
  final `run.json` SHA-256
  `bb1349f151ffc5346c6264de3781944bc02776bacf59a901fa185481567df3f5`;
  complete sanitized bundle SHA-256 is in the summary table. Incomplete
  successor `m11-native-reconstruction-9e7c7111` and the earlier original/review
  evidence remain immutable superseded diagnostics; they no longer supply the
  acceptance boundary.
- **Decision/specification correction:** release-blocking `BLOCKED`. The
  canonical AP-ledger reconstruction invariant is unchanged; runtime violates
  it. Do not implement the later reconciliation/interception subsystem in
  Milestone 11.
- **Risk/future milestone:** Milestone 14 is the primary remediation gate for
  deterministic AP-ledger reconstruction and must close this `BLOCKED`
  decision with a finalized successor run before expanding the permanent-item
  table. Milestone 17 must prove complete reward interception does not
  reintroduce the leak, and Milestone 25 must repeat the reconstruction matrix
  against the full integration. Permanent items, rewards, locations, and
  shadow story cannot release until native expansion and check leakage are
  contained; see R-006.

## 600-orb availability - BLOCKED

- **Source evidence:** `game-save.gc:32`, `:947-949`, and `:1860-1861` define
  the native `skill-total` save field. Runtime acceptance additionally requires
  bounded local-source-family observations and exclusion of AP Orb Packs.
- **Procedure:** inspect the available non-Hero candidate, then require locally
  earned 600, finale/postgame, Hero Mode off, AP pack count zero, source-family
  bounds for standalone pickups, containers, mission rewards, and challenge
  rewards, ordinary save/load, and full restart. Every source-family count must
  be a non-negative integer and their sum must equal the locally earned total.
  The AP pack count must be
  derived from the checksummed persistent receipt ledger bound to the same
  native slot/save identity; a manually supplied zero is not evidence.
- **Observed values:** UI slot 2 reported 86% but captured
  `native_hero_mode=0`, `native_postgame_complete=0`, `native_skill_total=0`,
  `native_skill_high_watermark=0`, and `ap_orb_pack_count=0`. A read-only
  archive search found no qualifying 600-orb save at the time of the terminal
  run. Two later operator-supplied PS2 archives now provide checksum-valid
  static candidates: MAX Drive UI slot 1 and CodeBreaker UI slot 1 both record
  completion `100.0`, `skill-total=600.0`, `new-game=0`, and Hero Mode off.
  Their container SHA-256 values are
  `969EDBE385D6454A71DE1C2B8D441444C0F9FE0C134325F57D8A1F10C46AA625`
  and `FEC7E7E6F18BFF2B79AB6E00368954B3AD708CD8AB04BE99CAC5CC67D139FFC7`.
  Read-only copies and their import-safety manifest are preserved at workspace
  path `D:\Codex\Jak3\tmp\milestone11-orb600-save-candidates`; the MAX Drive
  file is the preferred primary control and the CodeBreaker file is an
  independent cross-check. Future work must copy/decode them into a separately
  backed-up disposable save directory rather than importing over an active
  OpenGOAL save.
  Static validation does not replace the required OpenGOAL runtime lifecycle.
- **Evidence:** terminal run `m11-orb-600-e8d7eed7`, `run.json` SHA-256
  `2f0d124deb5f30d112d1de61e12bacef171397895ff8e886fde32d440704dc0a`;
  complete bundle and hash are in the summary table. The older placeholder
  review is superseded.
- **Decision/specification correction:** `BLOCKED`; the available save is not a
  runtime-proven postgame/600 control. Retain all 24 threshold IDs and the
  default table unchanged. Do not calculate fallback counts because no highest
  proven normal postgame multiple of 25 exists. The newly supplied static
  candidates remove the availability blocker but do not change this decision
  until one passes the complete live procedure.
- **Risk/future milestone:** Milestone 12 must reconcile finite source families
  with the normal-save maximum. Milestone 23 must not enable thresholds above
  the highest maximum jointly proven by Milestones 11/12, and Milestone 25 must
  repeat local-only persistence and AP-pack isolation across restart before
  release. No predefined orb fallback may be activated without that evidence.

## Default side challenges and R&C course access - BLOCKED

- **Source evidence:** `game-task.gc:23238-23240` gives the desert burning-bush
  event typed icon `gaticon-08`. `des-burning-bush.gc` reads the event texture
  as price/prompt state and persists kiosk activation in
  `bb-perm.user-object[0]`. `gungame-manager.gc:1435-1438` gates both R&C
  courses with `secrets.gungame-ratchet`; native save data keeps `secrets` and
  `purchase-secrets` distinct.
- **Procedure:** enforce the exact ordered parent-suppression, child-intro,
  continue, and refresh prefix; prove original price `8`; apply the typed free
  value immediately before one interaction; capture pre-entry, active, and
  ordinary-reload state with checksummed AP controls. Continue to hidden/open/
  reload/cleanup course controls only if reload preserves unrelated state.
- **Observed values:** the clean successor proved marker/event `1/1`, original
  price `8`, typed displayed price `0`, activation `0 -> 1`, zero Skull Gems,
  native items `0`, purchase history `0`, and AP checked/relic controls `0/0`.
  The bounded reward mask was correctly `32`, not `0`, because the test setup
  deliberately closes the audited `desert-beast-battle-resolution` node at bit
  32. While active, the same native `event.tex` field became play icon `4`; it
  was not a four-gem charge. The operator visibly confirmed the zero-cost
  prompt and successful challenge entry. UI-slot-4 save changed only `bank7`;
  ordinary load retained activation `1`, displayed cost `0`, event/marker
  `1/1`, suppression `1`, and zero Gems.
- **Blocking discrepancy:** that same load changed native items `0 -> 243803`,
  bounded reward mask `32 -> 63`, AP checked mask `0 -> 255`, Jetboard mask
  `0 -> 3`, task-30 item mask `0 -> 19`, and broad task/mission/feature state.
  The challenge HUD itself cleared while Jak loaded in a vehicle near an active
  pedestal, which is normal task-session reload behavior; the unrelated state
  expansion is not. Testing stopped before course controls under the required
  stop-on-failure rule. The legacy seven-checkpoint run remains useful course
  behavior evidence but has no per-boundary provenance and cannot fill the
  missing current checkpoints.
- **Evidence:** terminal correlation `m11-side-challenges-15ecab70`; final
  `run.json` SHA-256
  `DFF7F3D61DAAA0F68C007E3F0A5276B34D6CD01E6E42A4A70CD3A9D586B955B6`;
  complete sanitized bundle SHA-256
  `DFD55540DA5D08C46D2047305D8A6638050F5B95E4E732FD03D666A98BE9199A`.
  Pre-entry, active, and reload snapshot SHA-256 values are
  `98200AF58FB939B50907EC428CC3BD8C45A4FD8BBE15578638C4B4D44A9C0BAA`,
  `6DAF63F180A6E4B910176F7275EC2D62290F5BE5D7C1ECFB0645E16A16635851`,
  and
  `8A69E82C78A2146AE58F50169B1E99AB7F98C70DE69631E4B61FFB2E3F5112C5`.
  The out-of-order predecessor `m11-side-challenges-d429b84e` remains immutable
  superseded diagnostic evidence.
- **Decision/specification correction:** `BLOCKED`. Retain the documented
  free-cost and pre-opened-course defaults provisionally; do not add production
  hooks or change the default YAML. The pre-save free-entry behavior passed,
  but the complete persistence/course matrix did not.
- **Risk/future milestone:** Milestone 14 must first close native reconstruction
  so an ordinary load does not contaminate AP/native controls. Milestone 22 then
  reuses this runner to prove the full seven-checkpoint production hook,
  including course access/purchase isolation. This is a release gate, not a
  request to implement Milestone 14 or 22 inside Milestone 11.
## Contract consequence

The Milestone 11 investigation is complete because every spike has a terminal
decision and a complete hashed evidence bundle. Release feasibility remains
blocked. Jetboard Launch and native reconstruction are hard Milestone 14 gates;
Haven production integration remains Milestones 18/19; task-30/task-63
production shadow lifecycles remain Milestone 20; the side matrix resumes in
Milestone 22 after reconstruction is fixed; and the 600-orb lifecycle remains
Milestone 23.

The canonical design records the accepted Haven convergence fallback and keeps
Launch independent but unshippable until persistence/application passes. The
default YAML supported option set, item/location IDs, table versions/hashes, 24
orb thresholds, Launch reservation, and side defaults remain unchanged.

## Harness ownership and future reuse

- `tools/run_milestone_11_spikes.py` is a development-only evidence runner; it
  is not packaged into the APWorld and does not implement gameplay. Its typed
  observation schema, automatic decision checks, snapshot provenance, immutable
  review records, and support-bundle gate are intended to be extended for the
  successor proofs in Milestone 14 (Jetboard and reconstruction), Milestones
  18/19 (Haven convergence/bootstrap), Milestone 20 (task-30/task-63 shadow
  state), Milestone 22 (side challenges), Milestone 23 (600-orb lifecycle), and
  Milestone 25 (full restart/reconciliation integration).
- `worlds/jak3/agents/diagnostics.py` is production infrastructure, not a
  one-milestone test helper. It remains the authoritative Python event,
  redaction, retention, and support-bundle boundary for all later runtime
  modules. Milestone 11 only adds the bounded `feasibility.spike.*` event
  family and its strict allowlist.
- `tests/test_milestone_11_spikes.py` is the CI regression suite for the
  development runner. Later milestones should add their successor checkpoints
  without weakening these mask, contradiction, finalization, redaction, and
  hashing tests. `tests/test_diagnostics.py` protects the shared production
  diagnostics contract.
- `tools/verify_source_tables.ps1` remains the reusable, read-only source-audit
  entry point. Milestone 12 and later source-backed work may add scoped audits,
  but the documented default-root behavior and reference-tree cleanliness
  checks remain required.
