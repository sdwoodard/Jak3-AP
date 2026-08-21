# Milestone 11 operator-assisted testing

This document is the resumable procedure for the focused Milestone 11 runtime
spikes. It records how the developer agent, the human controller operator, the
Archipelago client, and the live OpenGOAL target are coordinated. Terminal
results and immutable evidence hashes belong in
[`feasibility_decisions.md`](feasibility_decisions.md). During live testing,
chronological notes were written after every measurable checkpoint; the final
decisions, discrepancies, and recovery evidence have now been folded into the
authoritative decision, verification, and risk documents.

## Scope and stop rule

Run one spike at a time. Do not start the next spike until the current spike
has an evidence-backed `PASS` or its predefined `SAFE FALLBACK` has passed its
own acceptance checks. If a checkpoint fails, stop operator testing, determine
whether the failure is staging, connection, save selection, observation, or
native behavior, and correct that cause before retrying with a new correlation
ID. Milestone 11 must not implement later gameplay systems merely to turn a
feasibility result green; an out-of-scope production gap is recorded as a
release blocker and escalated rather than silently broadening the milestone.

Every set of operator instructions includes two estimates: time remaining for
the current spike and time remaining for all Milestone 11 operator testing.
Estimates are updated after each accepted checkpoint or stopped failure.

## Final Haven evidence-refresh session

The post-review Haven successor uses a newly started local room at
`127.0.0.1:38283`. The room was started with no `.apsave`; its immutable seed
archive has SHA-256
`7B6722EB50A69DE8B4112CC047E4F03CCA99A24107468B87A40FFA85C5FB842F`.
The installed APWorld is the deterministic 247,243-byte build with SHA-256
`C23B752D04C1E96D23FA9F17361AEAF28F50D76FF2B2B8F196069DD18E1E7D35`.
The active OpenGOAL bridge matches the project source and has no pending reload
marker. The client authenticated to the exact room, UI slot 4 mapped to native
slot 3, and a normal New Game save completed. The paired live snapshot at the
accepted baseline reported `connection_ready=1`, `source_loaded=1`,
`save_loaded=1`, `ap_state_loaded=1`, `ap_state_bound=1`, level `wasstada`, task
10/node 8, no transition/cutscene/death/vehicle state, and permanent target
mask `0`. Both physical banks were copied before staging: `bank6.bin` SHA-256
`789ED0AF2B168E3D2B9D490AA9221F36FE4E412FB923688AAEC2DDFCCEFD9467`
and `bank7.bin` SHA-256
`5A9AE748590652635E20B19C9C8FAAB377172328DC443C6C941CFE90441C6266`.

This baseline exposed a runner-only discrepancy before mutation: clean-start
relocation was hard-coded to native slot 2, even though the run owns native
slot 3. The validator now receives the run's recorded slot for every evidence-
bound live stage/capture, rejects a different loaded slot, and treats only the
continue-only `haven_task35_hub_candidate` as an allowed clean-start
relocation. No native task state was changed while correcting the harness.

Successor correlation `m11-haven-task-35-95ab560f` is finalized and bundled.
The corrected slot-bound validator accepted native slot 3 and the runner sent
only the allowlisted `ctygenb-samos` continue. Both `before_entry` and
`mission_start` then captured task/mission/item/reward/Jetboard/AP masks `0`,
loaded-level mask `7`, passage mask `1`, and actor mask `0`. The historical
runner's `native_act=2` value was a loaded-level inference, not the bridge's
task-derived `current_act`, and is not accepted as independent Act-II proof.
The operator confirmed playable city geometry with Samos and Keira absent.
This independently proved the required-actor failure while tasks 14-34 remained incomplete and
selected the predefined Haven convergence fallback. Final `run.json` SHA-256
is `2E8649B2E052528A5D4C8472308B26819564A88D0E5658F20DDD8A3C34E2C2BD`;
the complete sanitized support-bundle SHA-256 is
`336C9E9CA03BE0B4C9771076536CFFF5E58BFB0B6A6584FC944DE269D3279562`.
The Haven refresh is complete. The Jetboard successor has now isolated its
release blocker to Launch reconstruction after AP base mask `1` returns. At
this historical checkpoint, one operator-assisted successor remained: the
five-checkpoint native-reconstruction lifecycle subsequently completed below.
Older artifacts remain unchanged and are referenced only as superseded or
blocking evidence.

## Post-review harness correction and successor plan (historical)

The post-review correction was verified on 2026-08-16. Jetboard review now
requires all eight checkpoints, every named assertion to be `pass`, and exact
native masks `0`, `1`, `3`, `2`, `1`, `3`, `3`, and `3` in matrix order. A
successful recorder procedure cannot override a failed persistence assertion.
Native-reconstruction review now requires all five lifecycle checkpoints and
numeric values for the native item, feature, non-AP feature, permanent-target,
reward, task, mission, AP-inventory, AP-ledger-revision, and AP-check fields at
each one. Every live stage/capture—not only attached-target reuse or a
specialized boundary—requires a fresh snapshot matching the run-owned native
slot. The snapshot must be previously unconsumed and its hash, bridge revision,
native slot, and age are stored on the stage/capture boundary. Task-30/task-63
controls require exact-zero task, mission, and reward masks from independent
source structures. A future 600-orb capture requires all four source-family
observations to be integral, non-negative, and sum to the local-earned total,
and derives AP Orb Pack receipts from the checksummed bound AP state. A decision
remains `finalized_pending_bundle` until one complete sanitized bundle is hashed.

The deterministic APWorld was built twice at 247,243 bytes with SHA-256
`C23B752D04C1E96D23FA9F17361AEAF28F50D76FF2B2B8F196069DD18E1E7D35`.
The installed APWorld and all six active OpenGOAL bridge modules already matched
that build, so the planned operator session did not require installation. Final
review verification retained byte-identical 247,243-byte packages with the same
hash; Ruff, Ruff format, mypy, all three source-audit invocation modes, and the
complete 421-test packaged suite pass. Focused Milestone 11/diagnostic coverage
passes 106 tests. Both Git-backed reference trees remain clean.

The planned session started with the Jetboard matrix on disposable UI slot 4
(native slot 3). The agent verifies the exact server endpoint and session log,
creates a fresh successor correlation, backs up both slot banks, and performs
all staging/capture commands. The operator performs only the named controller
checks and ordinary save/load actions. The estimate at that point was 30-45
minutes for Jetboard and 50-75 minutes for both successors together. If a
checkpoint fails, testing stops at that spike while the staging, connection,
slot, save generation, and captured numeric state are diagnosed.

The clean successor room is running at `127.0.0.1:38284` from a new directory
with no prior `.apsave`; its seed archive SHA-256 is
`7B6722EB50A69DE8B4112CC047E4F03CCA99A24107468B87A40FFA85C5FB842F`.
Before launch, UI-slot-4 banks were copied to the recoverable folder
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-16T0322-ui-slot4-pre-jetboard-successor`.
The copied `bank6.bin` SHA-256 begins `789ED0AF2B168E3D2` and the copied
`bank7.bin` SHA-256 begins `5A9AE748590652635E`; these match the full baseline
hashes recorded in the Haven session above.

At the first Jetboard checkpoint, the managed session ID was
`2026_08_16_07_09_07_656020_26448`. The server log recorded Player1 joining the
fresh room, and the paired client log independently recorded authentication to
`ws://localhost:38284`, team 0, slot 1. The bridge snapshot was internally
consistent at revision 83, Protocol 3/runtime 5 were ready, all three gameplay
modules were active, the game was at the paused debug-start scene, and no
native save was loaded. Active slot-4 bank hashes still matched the pre-session
backup before the operator was asked to load the slot.

After UI slot 4 loaded, the paired snapshot identified native slot 3 and save
identity `56896cc5-e600-44d7-a859-82f4d45b68ba` at `wasstada`, task 10/node 8.
The game was paused and playable with `safe_to_apply_permanent_item=1`, while
the active start mission correctly made `safe_to_mutate_mission_state=0`. This
exposed a second runner-only preflight defect before mutation: all Jetboard
presets had been classified as mission-state writes even though the first four
controls alter only the bounded Jetboard/Launch feature mask. The runner now
uses the permanent-item safety boundary for those four controls, retains the
mission-state boundary for task-30 controls, and provides a separate clean-start
continue-only relocation to the task-30 tutorial. The two safety modes are
mutually exclusive, specialized-run-only, and still enforce the run-owned
native slot and all common transition/death/vehicle guards. Focused runner tests
now pass `47`; Ruff lint/format and mypy also pass. No GOAL form was sent and no
save or native state changed while the defect was corrected.

Successor correlation `m11-jetboard-launch-5b7a791b` was then created for
native slot 3. Its first allowlisted stage, `jetboard_00`, passed the corrected
slot-bound permanent-item safety gate and completed without a delayed compiler
or runtime error. Reconciliation is deliberately suspended only for this
bounded controller observation; the operator must now verify that neither the
base board nor the charged Launch behavior is available before the runner
captures the exact mask-`0` checkpoint.

The operator then confirmed that the board did not deploy and `L1+X` produced
only Jak's normal crouch jump. The first capture attempt stopped before sending
a form because the bridge intentionally publishes permanent-item safety as
false and native target `-1` while the runner's staged reconciliation
suspension is active. The capture handoff now accepts that exact suspended
boundary only when the run's most recent recorded preparation matches the same
Jetboard preset and checkpoint; it continues to reject an unowned suspension,
slot mismatch, or any transition/death/vehicle flag. The focused suite remains
green at `47`, and Ruff lint/format plus mypy pass. The checkpoint itself was
not written by the rejected attempt and will be captured without repeating the
already valid operator action.

Checkpoint `00` is now accepted in correlation
`m11-jetboard-launch-5b7a791b`: exact native Jetboard/Launch mask `0`, base
absent, Launch absent, and charged Launch absent at save generation `0`. The
capture completed at `2026-08-16T11:30:28Z` and restored production
reconciliation afterward.

The next allowlisted preparation, `jetboard_base_only`, passed the ordinary
permanent-item safety gate and staged base bit `1` with Launch bit `0`; the
bounded reconciliation suspension remains active for the controller check.

The operator confirmed that the base board deployed, moved, and jumped while
the held-`L1` charged jump remained unavailable. After that completed action,
an accidental death returned Jak to the original start and the directly staged
board was no longer deployable. The paused respawn snapshot was stable and
showed no death/restart/transition flag; because the behavioral check had
already completed, the runner atomically reapplied the same allowlisted preset
and captured exact mask `1` without requiring another controller attempt.
Checkpoint `base_only` is accepted at `2026-08-16T11:33:35Z` with all three
assertions passing. The post-check death/retry loss is retained as diagnostic
evidence about synthetic staging and is not treated as AP-ledger persistence.

The `jetboard_base_launch` preparation then passed the restored ordinary
permanent-item boundary and staged exact feature mask `3` for the positive
controller control.

The operator deployed the board and performed the held-`L1` charged jump,
then dismounted and paused without a death or transition. Checkpoint
`base_launch` is accepted at `2026-08-16T11:36:04Z` with exact mask `3` and all
base/Launch/charged-behavior assertions passing.

The `jetboard_launch_only` preparation then passed the restored permanent-item
boundary and staged Launch bit `2` with the base-board bit clear.

The operator confirmed that the board could not deploy and `L1+X` remained
Jak's ordinary crouch jump. Checkpoint `launch_only` is accepted at
`2026-08-16T11:38:04Z` with exact native mask `2`; the numeric Launch bit and
negative base behavior together prove in-memory bit independence.

The continue-only `jetboard_task30_scene_stage` then passed its exact clean-
start boundary and started the named `templec-start` play continue without
closing task nodes or synthesizing mission completion. The operator must allow
the transition to settle and pause in the task-30 Jetboard tutorial before any
task-node or feature control is applied.

The operator confirmed a stable temple scene. Paired readback reported level
`templec`, no active task/node, no unsafe runtime flags, native permanent target
`0`, and `safe_to_mutate_mission_state=1`. The bounded
`jetboard_task30_base_only` preset then staged base mask `1`, kept Launch clear,
closed only the two named tutorial presentation nodes, and returned to the
named `templec-start` continue for the traversal check.

The operator deployed the base board in the tutorial and confirmed the charged
jump remained unavailable, then dismounted before capture. Checkpoint
`task30_base_only` is accepted at `2026-08-16T11:42:18Z` with exact Jetboard
mask `1`, native task/mission/item/reward masks all `0`, locally earned skill
`0`, Hero Mode/postgame `0/0`, and no portal/viewer/course side effects.

The first attempt to stage `task30_base_launch` was rejected before mutation
because the preceding capture's deliberate return to `templec-start` still
published `level_transition=1` while the game remained paused. This is an
expected safety-gate stop, not a native behavior failure. The operator must
unpause until the same temple scene settles, then pause before the preset is
retried.

After the operator let the return complete, paired readback again showed
`templec`, no active task/node, no unsafe flags, native target `0`, and
`safe_to_mutate_mission_state=1`. The retried
`jetboard_task30_base_launch` stage then completed without error and staged
exact mask `3` at the same tutorial boundary.

The operator confirmed the charged jump worked in task 30 and dismounted
before capture. Checkpoint `task30_base_launch` is accepted at
`2026-08-16T11:46:07Z` with exact Jetboard/Launch mask `3`; native
task/mission/item/reward masks remain `0`, locally earned skill remains `0`,
and no portal/viewer/course field changed. All six semantic/traversal rows now
pass. The persistence setup will next add only the supported AP `Jetboard`
receipt to the fresh room's bounded ledger, then save native Launch alongside
that AP-owned base bit; Launch itself is not being injected as an unsupported
AP receipt.

The operator entered `!getitem Jetboard` only in the authenticated text client
for `localhost:38284`; the server replied `Cheat console: sending "Jetboard"
to Player1`. The paired client log recorded one immediate `ap-command!`, and
bridge readback remained bound to native slot 3/save identity
`56896cc5-e600-44d7-a859-82f4d45b68ba` with native permanent target mask `1`,
no bridge error, and all unsafe flags clear. This establishes the supported AP
ownership of the base bit before the native persistence save; no Launch receipt
was requested.

The allowlisted `jetboard_base_launch` stage then completed at the same stable
temple boundary, setting native mask `3` while leaving reconciliation suspended
so the upcoming ordinary save contains the AP-owned base bit plus native Launch.

The operator completed an ordinary Save Game overwrite to UI slot 4 with no
reported error. Only active `bank7.bin` changed; `bank6.bin` retained SHA-256
`789ED0AF2B168E3D2B9D490AA9221F36FE4E412FB923688AAEC2DDFCCEFD9467`,
while the written `bank7.bin` is SHA-256
`296F32F6C313975AB952BFD5D7A7E4FDE7B99E3080EEC0F4E6CB27909CB045E1`.
Both were copied to the recoverable post-save directory
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-16T0749-ui-slot4-jetboard-ledger-mask3-post-save`.
Raw little-endian feature values at offsets `68`, `1096`, `1728`, and `123972`
are all `360289207141531648`, exactly matching the task-30 mask-`3` capture's
full native feature value. Thus the ordinary save is proven to contain both
base and Launch before reload.

The first ordinary load then restored runtime mask `0`: neither board nor
charged jump was available. Exact capture at `2026-08-16T11:56:32Z` confirmed
mask `0` and both persistence assertions failed. Because the stage-only
reconciliation suspension had not been restored before the operator loaded,
this correlation cannot distinguish native reconstruction from a deliberately
disabled AP base reconciler. It was finalized `BLOCKED`, not overwritten:
correlation `m11-jetboard-launch-5b7a791b`, `run.json` SHA-256
`946635A3A4C865FE9E0F68FF67604C9112AFDC38E049E7C2FE26B34C387DC210`,
sanitized bundle SHA-256
`165034EA9951C49C4394F5AAB14BB23212F826735289AE1EC194F09354B3ADD6`.

The runner now has a restricted stage-only
`jetboard_restore_reconciliation` handoff. It accepts the permanent-item
boundary only on the run-owned slot, including the exact suspension sentinel
`safe_to_apply_permanent_item=0` plus native target `-1`, and restores the
production hook without synthesizing a checkpoint. Capture rejects this preset.
The runner also adds its pinned Archipelago dependency root when loading the
diagnostic bundler, so documented standalone bundle commands no longer depend
on an ambient `PYTHONPATH`. Focused coverage now passes `48`; Ruff lint/format
and mypy pass. A new successor must restore reconciliation before repeating the
load from the immutable mask-`3` saved bank.

Successor correlation `m11-jetboard-launch-2e22a7b0` now owns native slot 3.
Its first stage used only `jetboard_restore_reconciliation`; after the bounded
settle, bridge readback returned to `safe_to_apply_permanent_item=1`, AP native
target `1`, no bridge error, level `templec`, no active task, and no unsafe
runtime flag. This proves production base reconciliation is active before the
operator repeats the ordinary load from the already hashed mask-`3` bank.

With production reconciliation active, the repeated ordinary load produced a
different and decisive result: the operator could deploy the board but could
not perform the charged jump. Exact capture at `2026-08-16T12:05:20Z` reported
native Jetboard mask `1`, native permanent target `1`, and zero native
task/mission/item/reward masks. `base_ownership_unchanged` therefore passes,
while `launch_reconstructed` fails. Correlation
`m11-jetboard-launch-2e22a7b0` is finalized `BLOCKED`; `run.json` SHA-256 is
`DFFEB15129266802C87BCC3B6F271943D2421D00AE3657B492B563BFA19F33FA`
and sanitized bundle SHA-256 is
`35AD2E9DE7CE00691EF44D540A7740AEA26FC7A1883BAC2CA755FDF42F711110`.
This successor proves that AP-owned base reconstruction works and isolates the
remaining blocker to Launch, which is outside the current three-item receipt
slice. No additional Jetboard testing will run in this session; the operator
requested a full process close before the next spike.

The native-reconstruction successor is an evidence-completion run, not
authorization to implement Milestone 14 reconciliation. A fully captured leak
there remains terminal `BLOCKED` for Milestone 11 and an explicit Milestone 14
release gate; the run closes the investigation without claiming release
feasibility.

### Native-reconstruction resume preflight (2026-08-16)

After the requested full-process break, the operator reported readiness to
resume. The installed `jak3.apworld` remains the verified 247,243-byte build
with SHA-256
`C23B752D04C1E96D23FA9F17361AEAF28F50D76FF2B2B8F196069DD18E1E7D35`.
The preserved room contains the immutable seed archive and its server save with
exactly the one supported `Jetboard` receipt used by the corrected persistence
boundary; the preceding clean client shutdown recorded `received_item_count=1`,
`location_count=0`, native slot 3, and AP revision 22. This is the intended
bounded ledger for the reconstruction successor, not a fresh-ledger claim.

The computer restart invalidated the user's Windows Store `python.exe` alias.
The runner was therefore revalidated with the existing workspace-owned
`D:\Codex\Jak3\tmp\python312-m71-final\python.exe` (Python 3.12.10), whose
`--help` invocation completed successfully. No runtime or save mutation occurred
during this check. One stale, non-listening `ArchipelagoServer` process from the
Jetboard room remained to be replaced before the operator reopens the client;
the exact endpoint and new session-matched logs must be verified again.

The stale server was terminated by exact PID after it was confirmed to be the
non-listening Milestone 11 process. A replacement server, PID `25496`, loaded
the preserved room save with exactly one received item and is listening only on
`127.0.0.1:38284`; its logs are
`native-reconstruction-server.stdout.log` and
`native-reconstruction-server.stderr.log` in the preserved room directory.
Before launching the game, active UI-slot-4 banks were copied to
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-16T1156-ui-slot4-pre-native-reconstruction-successor`.
The copied `bank6.bin` SHA-256 is
`789ED0AF2B168E3D2B9D490AA9221F36FE4E412FB923688AAEC2DDFCCEFD9467`;
the copied `bank7.bin` SHA-256 is
`296F32F6C313975AB952BFD5D7A7E4FDE7B99E3080EEC0F4E6CB27909CB045E1`.
Successor correlation `m11-native-reconstruction-9e7c7111` owns native slot 3.
No checkpoint has yet been staged or captured.

The operator launched the verified Jak 3 client and connected before loading a
save. The paired session is `2026_08_16_11_56_23_732221_32272`, with client and
OpenGOAL logs of the same suffix and bridge snapshot
`C:\Users\steph\AppData\Local\Temp\jak3-ap-2026_08_16_11_56_23_732221_32272.tmp`.
The client log proves authentication to `ws://localhost:38284`, team 0/slot 1,
and the server log independently records the join. At the paused debug-start
boundary, bridge revision 65 was internally paired, Protocol 3/runtime 5 and all
three gameplay modules were active, the level was `wascitya`, no native save was
loaded, and every transition/cutscene/death/restart/vehicle flag was clear.
This is the accepted pre-load session baseline; no checkpoint or native state
was changed.

The operator then loaded disposable UI slot 4 and paused on foot in the stable
`templec` Jetboard-tutorial area. Bridge revision 153 identified native slot 3
and save identity `56896cc5-e600-44d7-a859-82f4d45b68ba`; AP state was loaded
and bound, the bounded ledger target was `1`, and every unsafe runtime flag was
clear. The allowlisted `native_reconstruction_targets` stage then passed the
run-owned-slot mutation boundary and completed without a delayed compiler or
runtime error. No ordinary save has yet been requested.

The second allowlisted preparation, `native_reconstruction_rewards`, passed at
the same paused, bound slot-3 boundary and completed without an OpenGOAL error.
It closed only the explicitly named audited reward nodes and invoked their two
required task commands. The runner is now ready to query and atomically record
the complete typed `before_save` baseline.

That first query exposed a recorder defect before any ordinary save: correlation
`m11-native-reconstruction-9e7c7111` accepted the native fields while omitting
the AP inventory mask, ledger revision, and checked mask. Testing stopped. The
runner now derives those controls from the checksummed persistent AP state,
requires its native slot and save identity to match the paired live bridge,
rejects unknown bounded-slice checks and manual AP-field substitution, and
rejects an incomplete native-reconstruction checkpoint before writing it. The
focused suite passes 50 tests; Ruff lint and format checks pass.

The incomplete correlation was finalized `BLOCKED` and bundled rather than
edited. Its final `run.json` SHA-256 is
`8EC2D2609E8C2EB2A601CAB02C1DDB262F9FC79262EAAD855605B57EBBDFDD2F`;
its complete sanitized bundle SHA-256 is
`17FBA917F6C5D52E22C32D467EEFAEB6C7A6FBDD1BA48DA5668416BC944C2C91`.
Successor correlation `m11-native-reconstruction-e920e187` owns the unchanged
paused slot-3 state. Because no ordinary save/load occurred, the two allowlisted
preparations may be reapplied idempotently and captured without repeating an
operator action.

The successor's idempotent `native_reconstruction_targets` preparation passed
the same slot-bound live safety gate. The game remained paused and no save was
written.

The successor's idempotent `native_reconstruction_rewards` preparation also
passed without an OpenGOAL error. Both preparations are now owned by correlation
`m11-native-reconstruction-e920e187`; the next capture uses the checksummed
slot-3 AP state instead of caller-supplied AP values.

The first successor capture correctly refused the live state rather than write
a checkpoint because the new checksum helper omitted the canonical trailing
newline. The production state envelope itself was valid. The helper now matches
the documented canonical byte contract exactly, with an explicit regression
test; all 50 focused tests and Ruff checks remain green. The retry accepted
`before_save` at `2026-08-16T16:11:54Z`: AP inventory mask `1`, ledger revision
`30`, checked mask `128`, native items/reward mask `2015`, native permanent
target `1`, native Jetboard mask `3`, and non-AP feature mask
`396318553924436992`. Immediately afterward, active bank hashes remained the
pretest values (`bank6` `789ED0AF...9467`, `bank7` `296F32F6...45E1`), proving
that staging and capture did not perform native save I/O. The ordinary slot-4
save then completed without any observed error or transition. Independent bank
verification proves that the ordinary save succeeded: active `bank6.bin`
changed to SHA-256
`90018D4309F1D04E47DC7F997C4B4E773233B84439748E50583271CDF7FC66F9`,
while `bank7.bin` remained
`296F32F6C313975AB952BFD5D7A7E4FDE7B99E3080EEC0F4E6CB27909CB045E1`.
Both post-save banks were copied to the recoverable folder
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-16T1217-ui-slot4-native-reconstruction-post-save`.
At that point, the next operator boundary was an ordinary reload of UI slot 4; the accepted
`after_native_reload` capture must follow that reload before any restart or AP
reconciliation action.

The operator then loaded UI slot 4 through the ordinary menu. Jak appeared on
foot in front of a closed door in a playable `templec` state; there was no
cutscene, death, or transition. A remote character was speaking, and an enemy
hit Jak once before the operator paused, causing only incidental movement. The
live bridge independently confirmed the run-owned native slot 3, exact save
identity, on-foot paused-safe state, and no cutscene/death/restart/transition.
The accepted `after_native_reload` checkpoint at `2026-08-16T16:25:15Z`
records AP inventory target `1`, ledger revision `40`, and a release-blocking
expansion: native items/reward `2015 -> 262143`, mission/task masks
`0 -> 4194303`, AP checked mask `128 -> 255`, and non-AP feature mask
`396318553924436992 -> 571903997079846336`. Native Jetboard mask remained `3`
and the bounded AP permanent target remained `1`. This exact-slot ordinary
reload therefore reproduces native reconstruction leakage independently of the
operator's incidental movement. The correlation remained active at that point only to capture
the required restart, AP-reconciliation, and item-replay lifecycle boundaries;
the terminal feasibility decision cannot be `PASS`.

The operator then closed `gk`, the Archipelago Text Client, and the OpenGOAL
compiler without saving. Process verification found all three absent while the
owned `ArchipelagoServer` process remained alive on port `38284`. This is the
required clean process boundary before `after_game_restart`; no relaunch had
occurred when it was recorded.

Before that shutdown, the server accepted all eight checks leaked by the
ordinary native reload and queued eight corresponding rewards after the
original Jetboard receipt: Light Eco Refill, Invisibility Statues, Time Map,
Skull Gem Pack (3), Blue Ammo Refill, Health Refill, Light Eco Refill, and Dark
Eco Refill. The client closed before ingesting those rewards, so its last
checksummed local state still records one receipt/target `1` but all eight AP
check bits. Reconnecting to the same room must therefore expose the canonical
nine-item server history; that expansion is part of the reconstruction leak,
not a fresh-ledger control or an operator delivery error. The clean process
boundary is preserved under
`D:\Codex\Jak3\tmp\milestone11-runtime-boundaries\2026-08-16T1236-native-reconstruction-after-native-reload`.
Its server save has SHA-256
`61B49687E140191C117F755C9ED7B40E978AE5DDC80528E5FE32E40B7FCB0ED1`,
and its checksummed client-state snapshot has SHA-256
`A6EDAC1A873ED96A50178A822C035D0B81D7D67A3580BEAC98F7CC78B14AFC6A`.

The operator relaunched the verified managed client, reauthenticated to the
same room on `localhost:38284`, loaded UI slot 4, and paused on foot at the same
closed-door `templec` continue. There was no cutscene, death, transition, load
error, or visible item notification; the same remote dialogue played and one
enemy hit caused incidental movement before pause. Session
`2026_08_16_12_51_02_821086_28748` independently reported the exact native
slot 3/save identity, bound AP state, safe on-foot flags, and permanent target
`1`. The accepted `after_game_restart` checkpoint at
`2026-08-16T16:56:46Z` records AP revision `44`, checked mask `255`, native
items/rewards `262143`, mission/task masks `4194303`, non-AP feature mask
`571903997079846336`, and Jetboard mask `3`. Every leaked native/AP field is
therefore unchanged from `after_native_reload`; full game/client/compiler
restart did not repair the reconstruction leak.

The same session's structured log proves the replay/reconciliation sequence
that was not visible in the UI. At authentication the server sent a
`ReceivedItems` packet from index `0` containing nine entries. The existing
Jetboard receipt remained valid, but index `1` (`Light Eco Refill`) was rejected
before persistent mutation with reason `item_outside_milestone_8`; therefore
the bounded client ledger correctly remained one supported receipt. After the
native descriptor bound, permanent-item recovery and the follow-up mismatch
repair each completed command 102 at target `1`, advancing the AP state to
revision `44`. Neither reconciliation cleared native inventory/reward leakage
or the eight AP checks. Accepted checkpoints `after_ap_reconcile` at
`2026-08-16T17:00:25Z` and `after_item_replay` at
`2026-08-16T17:00:28Z` consequently retain the exact restart values.

Correlation `m11-native-reconstruction-e920e187` now contains all five required
checkpoints and is finalized `BLOCKED`. Final `run.json` SHA-256 is
`BB1349F151FFC5346C6264DE3781944BC02776BACF59A901FA185481567DF3F5`;
the single complete sanitized support bundle has SHA-256
`BEEB9DACC4EE27AB7E57D7376D87A287B67CB1EC84A6745C4899F58294040E39`.
The final server/client/event boundary is preserved at
`D:\Codex\Jak3\tmp\milestone11-runtime-boundaries\2026-08-16T1301-native-reconstruction-final`.
Its server save, checksummed client state, and structured session event stream
have SHA-256 values
`8406D8D295E1B38FC96E4F3ED2E95B4C87850363F4B2DF205B17E8B662A8AF15`,
`76A6CECB816FCB35EEF8D032B7645A704889824084C5616FD9F47A8106625873`,
and `92149B4690EEA0084D6DD180365EDFCEAA039654D11D7F42714798EA10D22948`.
No further controller action was required for that completed reconstruction
session. The completeness correction below identifies the two short successor
runs needed before task-30/task-63 can become positive evidence.

### Newly supplied 600-orb candidate archives

During that clean boundary the operator supplied two immutable PS2 save
archives in `D:\Codex\Jak3\tmp-jak3-saves`. They were inspected read-only with
the public `mymc+` container parser and the audited OpenGOAL `kmemcard.cpp`
layout; neither archive nor the active OpenGOAL save directory was modified.

- `jak-3.34706.max` is a MAX Drive container, SHA-256
  `969EDBE385D6454A71DE1C2B8D441444C0F9FE0C134325F57D8A1F10C46AA625`.
- `jak-3.14894.cbs` is a CodeBreaker container, SHA-256
  `FEC7E7E6F18BFF2B79AB6E00368954B3AD708CD8AB04BE99CAC5CC67D139FFC7`.

Both decode to the exact NTSC-U directory `BASCUS-97330AYBABTU!`, its three
metadata files, and eight `129024`-byte bank files. The OpenGOAL reader uses the
same directory and filenames and reads the meaningful first `124928` bytes;
the PS2 archives' remaining `4096` bytes per bank are zero padding. Every
populated bank used below has matching header/footer save counts, magic
`0x12345678`, and a valid native checksum.

MAX Drive UI slot 1 selects bank 1 at save count 64 and statically records game
save version 4, completion `100.0`, `skill-total=600.0`, Hero Mode bit clear,
`new-game=0`, and current spendable orbs `35.0`. Its two redundant banks are
both valid. UI slot 2 records Hero Mode and is excluded from the normal-mode
control. CodeBreaker UI slot 1 selects checksum-valid bank 0 at save count 1
and independently records completion `100.0`, `skill-total=600.0`, Hero Mode
bit clear, `new-game=0`, and current spendable orbs `35.0`; its auxiliary bank
is empty. These are qualifying static candidates, with the MAX Drive normal
slot preferred for runtime work and the CodeBreaker normal slot retained as an
independent cross-check. They supersede only the claim that no qualifying save
was available. They do not change the terminal 600-orb decision without a
disposable OpenGOAL import, live postgame/source-family observations, ordinary
save/load, full restart, and AP Orb Pack exclusion.

Read-only copies and a restart manifest are preserved outside the repository at
`D:\Codex\Jak3\tmp\milestone11-orb600-save-candidates`; both copied archive
hashes match their supplied originals. No candidate was imported into the
active OpenGOAL save.

### Final native-reconstruction cleanup (2026-08-16)

After the operator closed the game, text client, and compiler, the two active
UI-slot-4 banks were copied without alteration to the recoverable folder
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-16T-final-cleanup-ui-slot4-post-native-reconstruction`.
The retained post-test hashes are `bank6.bin`
`90018D4309F1D04E47DC7F997C4B4E773233B84439748E50583271CDF7FC66F9`
and `bank7.bin`
`296F32F6C313975AB952BFD5D7A7E4FDE7B99E3080EEC0F4E6CB27909CB045E1`.

Only UI slot 4/native slot 3 was then restored from its verified pre-successor
backup at
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-16T1156-ui-slot4-pre-native-reconstruction-successor`.
The active post-restore hashes exactly match that boundary: `bank6.bin`
`789ED0AF2B168E3D2B9D490AA9221F36FE4E412FB923688AAEC2DDFCCEFD9467`
and `bank7.bin`
`296F32F6C313975AB952BFD5D7A7E4FDE7B99E3080EEC0F4E6CB27909CB045E1`.
No other bank was written.

The exact Milestone 11 launcher PID `32996` and server PID `25496` were stopped
after their files were preserved. A bulk `Stop-Process` invocation stopped the
launcher but returned a PowerShell null-reference race before stopping the
server; the already verified server PID was then stopped separately. Final
process and listener checks found no `gk`, `goalc`, `ArchipelagoLauncher`, or
`ArchipelagoServer` process and no listener on ports `38281` through `38284`.
The runtime was not reopened after restoration.

## Responsibilities

The developer agent:

- verifies installed artifacts, process ownership, server endpoint, evidence
  paths, and bridge freshness before staging;
- backs up both physical banks for the selected disposable UI slot before an
  ordinary save can overwrite them;
- applies only named, allowlisted runner presets and captures numeric state;
- gives the operator one short controller procedure at a time;
- records the operator report, exact observation, correlation ID, and next
  action in Markdown after every measurable step;
- stops immediately on a mismatch and checks for an operator-independent cause
  before calling native behavior failed.

The controller operator:

- performs only the requested menu or controller actions;
- reports what appeared and what input did, including errors or unexpected
  loading, death, vehicle, or cutscene states;
- leaves the game paused or unchanged when asked so the agent can capture a
  paired observation;
- does not switch saves, servers, clients, or game processes unless instructed.

## Starting and connecting

1. Close stale Jak 3 client, `gk`, and `goalc` processes when a clean process
   restart is part of the checkpoint. Do not terminate unrelated processes.
2. Launch the verified installed **Jak 3 Client** from Archipelago Launcher.
   The installed APWorld must match the deterministic project build recorded
   for the session.
3. Connect the client to the exact server endpoint supplied for the run. The
   agent verifies the authenticated endpoint in the session-matched client log
   and records the seed/archive identity. A visible client connection alone is
   insufficient when more than one local server is listening.
4. Allow the client to start or attach to OpenGOAL. If compilation ends at the
   debug-start scene rather than the title menu, use the in-game Start menu and
   **Quit Game** to reach the title menu only when instructed.
5. Load only the named disposable UI slot. The agent records both the UI slot
   and the native zero-based slot reported by the bridge.

The active evidence paths are the session-matched `Jak3Client`, `Jak3OpenGOAL`,
and `Jak3Events` logs plus the temporary bridge snapshot whose filename shares
the client timestamp and PID. The runner uses `--reuse-attached-target` after
checking snapshot age, equal begin/end revisions, ready/running/source-loaded
fields, and all mutation-safety flags. It must not issue another `(lt)` to an
already attached target.

## Checkpoint cycle

1. Confirm the game is on solid ground, outside menus, loading, cutscenes,
   death/restart loops, and vehicles. Pause when requested.
2. The agent validates the live bridge and stages one restricted preset. No
   free-form GOAL expression is accepted by the runner.
3. The agent supplies the controller action, expected scene, and both remaining
   time estimates.
4. The operator performs the action once and reports the result without trying
   unrelated recovery steps.
5. The agent captures the exact typed observation and operator assertions from
   the same staged state. Numeric mismatches override a manual `pass`.
6. The agent appends a resumable Markdown note with timestamp, correlation,
   preset, observation, operator result, interpretation, and next action.
7. On success, continue within the same spike. On failure, stop, preserve the
   evidence, diagnose and correct the cause, then use a successor correlation;
   never edit a finalized run.
8. After the full matrix or a predefined decisive fallback boundary, finalize
   the terminal decision and export one sanitized support bundle. Checkpoints
   cannot be recaptured, and a finalized bundle cannot be replaced; any retry
   uses a successor correlation ID. Only a complete bundle is accepted for
   `PASS` or `SAFE FALLBACK`.

### Haven fallback containment

The Haven `SAFE FALLBACK` decision means only that a clean independent
no-`DONE(34)` candidate was disproved. It is not a PASS for the later production
fallback. The decisive evidence requires two unique checkpoints: a staged
`before_entry` control with tasks 14-34 clear, followed by `mission_start` in
the active `ctygenb` Haven level cohort. Both checkpoints retain stable AP
inventory, checked mask, native items, and reward mask. The second checkpoint must show the
required Samos/Keira low actor bits are not both present, the scene geometry is
playable, and the operator assertion must agree that required actors are absent.

Never close `mine-boss-resolution`, set task 34 complete, or invoke a broad task-
mask update for this spike. The runner contains no preset that can synthesize
`DONE(34)`. Milestones 18 and 19 must later begin from a naturally completed Act
I save and prove the converged production route and actor/bootstrap lifecycle,
including real bridge `current_act=2`; loaded-level inference is not accepted.

### Native-reconstruction successor matrix

A successor reconstruction run has five distinct, non-overwritable checkpoints:
`before_save`, `after_native_reload`, `after_game_restart`,
`after_ap_reconcile`, and `after_item_replay`. Every checkpoint records the raw
native feature/item/reward fields, the non-AP feature subset, the three-item
native target mask, native task/mission masks, the bounded AP-ledger target,
and AP checked bits. Restart, reconciliation, and replay must restore the native target to the AP-ledger
projection while preserving the pre-save non-AP/native-story baseline. A
transient native reconstruction is diagnostic evidence; an unrepaired target,
non-AP mutation, or newly published check bit remains `BLOCKED`.

### Side-challenge marker containment

Arrival at `desert-bbush-desb-4` is not sufficient evidence that the associated
`burning-bush-desb-4` task actor exists. Before applying the free-cost override,
run the restricted read-only `side_marker_desb4` probe against the same live
snapshot/log pair. The probe scans the active process tree for a typed
`des-burning-bush` whose embedded task actor is exactly
`burning-bush-desb-4`; this actor is not registered under a global process name.
It reports actor availability, event-resolution status, displayed cost, and
durable activation flag. An unavailable marker reports `0/0/-1/-1`: do not
dereference it, do not accept a checkpoint, and correct the staging path first.
An available actor whose event is unresolved may report default cost `0`; this
is not free-cost evidence. In that state, the restricted refresh increments
only the native task counter, then the read-only probe must report resolved
event `1` and original typed cost `8` before the override is applied. Never use
the broad task-mask updater for this spike because it can evaluate unrelated
closed-node commands.

The typed zero-cost write is capture-only and may run only at the exact paused
desert marker boundary (the run-owned native slot, bound AP state, task/node `-1/-1`,
no title/loading/cutscene/death/restart/transition/vehicle state, target mask
zero). Its actor lookup is independently guarded. The accepted pre-interaction
checkpoint must report marker available `1`, displayed cost `0`, activation
event resolved `1`, activation flag `0`, and unchanged zero Skull Gems before
the operator moves or interacts.

The post-save/load kiosk checkpoint has a separate read-only boundary. Native
load may resume the save's ordinary continue task and may place Jak in a
vehicle, so it does not require task 137 to remain the current task or require
`in_vehicle=0`. It still requires the exact loaded/bound native slot, desert
level, no title/loading/cutscene/death/restart/transition state, and a
session-matched live snapshot. The guarded actor readback must prove marker and
event availability, durable `bb-perm.user-object[0] == 1`, zero Skull Gems, and
unchanged AP controls. Absence of the in-progress challenge HUD after load is
recorded separately: the native save serializes closed task-node bits and a
resetter node, not the active task-manager/HUD session.

Every specialized validation mode now requires an explicit native save slot.
Evidence-bound stage/capture commands obtain it from the run record; standalone
read-only `probe` commands require `--save-slot`. The validator first compares
that value with the live bridge and no longer embeds UI-slot-3/native-slot-2 in
task-63 or side-challenge rules. A valid disposable slot 0, 1, 2, or 3 can
therefore be used without weakening the boundary.

### Task-63 cutscene containment

Task 63 is the only current exception to the ordinary mutation-safety gate.
The scene is spawned only from a safe paused forest baseline. The operator
unpauses only until the telescope/time-map presentation is visible and pauses
again before the scene completes. The agent captures the exact active scene,
actor handles, artifact mask, AP counters, and task/reward masks from that
paused mid-scene state. Never inspect the scene actor array between spawning
the paused `scene-player` and its first game tick. The actor query is guarded by
the bridge's `in_cutscene=1` field, and the runner rejects task-63 checkpoint
capture until the exact active-cutscene boundary is present.

For the `1984` control, apply the five-bit capture-only preset only after that
active scene is paused, then capture in the same bounded operation. A synthetic
write before scene activation was observed as mask `0` at capture and is
immutable superseded evidence; it must not be treated as an operator failure or
an accepted set control. The ordinary stage command cannot invoke the
capture-only preset.

There is no safe in-runtime cleanup command for this spike. The native `abort`
event enters `release`, whose `scf4` path can autosave; a direct-deactivation
attempt also terminated `gk` before acknowledgement. After each accepted
mid-scene checkpoint, keep the game paused and close the game, client, and
compiler without loading or saving. Verify those processes are gone and both
bank hashes are unchanged before starting the next variant in a fresh runtime.
This full process boundary destroys the in-memory `scene-player` without
executing scene `release`, autosave, or another GOAL cleanup form.

## Save protection and ordinary persistence checks

Before an ordinary save, resolve the selected UI slot to its two physical bank
files, copy both to a timestamped directory outside the active save folder, and
record their sizes and SHA-256 hashes. Save and load through the normal game
menus unless a spike explicitly tests another boundary. Afterward, hash and
copy both banks again. A result is not blamed on the operator until the slot,
successful save operation, changed bank, loaded continue location, and raw
saved fields have been checked.

Existing vanilla saves are read-only unless the operator has explicitly chosen
a disposable duplicate. Debug staging is never applied while the bridge reports
title/loading/cutscene/death/restart/transition/vehicle state or unsafe mission
mutation. Ordinary load is not a cleanup mechanism for an active
`scene-player`; task 63 uses the full process boundary above.

## Connection discrepancy from the Jetboard run

The Jetboard successor was actually connected to `127.0.0.1:38281`, the
canonical-default AP 0.6.8 room backed by `AP_85141192197545812499.zip`, not the
unused fresh room on port 38282. The room already contained server history, so
it cannot support a fresh-ledger reconstruction claim. Its directly staged
native mask and behavior controls remain valid because rejected item receipts
never mutated the AP ledger or native target and reconciliation was explicitly
isolated. Future connected-ledger tests must verify the endpoint from the
managed client log before the first mutation.

## Final disposable-save cleanup

Cleanup completed on 2026-08-15 after all operator checkpoints. The game,
client, and compiler were already closed. A remaining Milestone 11
`ArchipelagoServer` listener on port `38281` (PID `14980`) was identified before
termination; the termination completed after the first bounded wait, and a
successor process/port check found it absent.

Before restoration, both modified banks were copied to the recoverable folder
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-15T-cleanup-post-side-challenge-before-restore`:

- `bank4.bin` SHA-256
  `5b355631bdf15497c82fc3be0496265543bef5a036ad2f93a72fe27ebe04b810`.
- `bank5.bin` SHA-256
  `1c75673f30627c23be60f23a7de5dfa26efbb5b0b0bed77ba9808cdc55ee8f4a`.

Disposable UI slot 3/native slot 2 was then restored from the known-clean
baseline folder
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-14T1727-ui-slot3-clean-bound-baseline`.
Post-copy verification of the active save folder reported:

- `bank4.bin` SHA-256
  `ff475887fcb814af2423253a6e9ecbfb5660ee445bf38d6ce2c2c8a3d8e7d49b`.
- `bank5.bin` SHA-256
  `d609f869505ed51da28854374b791afb997bf08a576be235c9fdcaec4b4fcfa4`.

The runtime was not reopened after restoration. Finalized evidence bundles and
their immutable run artifacts were retained.

## 2026-08-17 completeness correction and resumable successors

A line-by-line review of the restricted GOAL query found two evidence aliases:
`native_mission_mask` had repeated the task-perm query, and
`native_reward_mask` had repeated the complete native inventory mask. The
historical task-30 and task-63 runs therefore remain useful for their portal,
node, exact item masks, scene actors, save-bank protection, and AP controls, but
cannot support independent-isolation `PASS` decisions. They were not modified.
Two immutable corrective reviews record the terminal blockers:

- task 30: `m11-task-30-shadow-review-fb327917`, `run.json` SHA-256
  `2C40A86FF8C12A5B75BF9A1677198118BDE1A9B889D1E471FA535E9338F56646`,
  complete bundle SHA-256
  `8FC9E7125E6325E7269D3053E9D69CAC4924278DD5D7E1107EACB1BF62686009`;
- task 63: `m11-task-63-viewer-review-a98ab064`, `run.json` SHA-256
  `23A404ECCFA50006021D4BEC3F1F389099DB30CF1DA0E44133C31279DF743745`,
  complete bundle SHA-256
  `D9D1D9F9899B13C2D2B9283908EC6B03AC81F5585BB1987542BF9843D0D5C507`.

The corrected query now measures task-perm completion for tasks 14-72,
independently walks closed `close-task` nodes in `sub-task-list` for the mission
mask, and observes a bounded ten-node native reward set from audited
`game-task.gc` names. The source audit covers the required `game-info-h.gc`,
`game-info.gc`, and reward-node anchors. One bridge snapshot hash/revision may
be consumed only once per run; capture requires a newly written snapshot even
when the AP client remains attached.

To reopen task 30, use a new correlation ID and repeat the already-established
stable-scene four-mask sequence (`0`, `16`, `7`, `23`) without public task
closure. Each checkpoint must capture portal `1/1`, intro node `1`, exact item
mask, independent task/mission/reward masks `0/0/0`, and unchanged AP
relic/check controls. To reopen task 63, use separate clean process starts for
the clear and set variants, pause during the telescope presentation, apply the
`1984` bits only after the scene is active, and capture scene `1/1`, actor mask
`12`, independent task/mission/reward masks `0/0/0`, unchanged AP controls, and
unchanged save-bank hashes. Do not run these successors merely to make the
Milestone 11 investigation complete: its evidence-backed `BLOCKED` decisions
are terminal. Milestone 20 must run them before implementing either production
shadow-state profile.

The connection workflow remains reusable by later milestones: start one named
local AP room, verify its endpoint from the managed client log, connect the AP
client (which owns target attachment), pair that log with the exact same-suffix
bridge snapshot, load only the operator-selected disposable slot, back up its
two physical banks, and let the runner perform restricted staging/capture. The
operator performs only the explicitly requested controller or ordinary
save/load action, then reports the visible result. Stop at the first failure,
diagnose it as setup versus runtime behavior, and retry only under a successor
correlation ID.

The final correction is automated by 115 focused runner/diagnostics tests and
the complete 430-test packaged suite. Ruff lint/format and mypy pass. The source
audit passes with no roots, only `-OpenGoalRoot`, and both roots explicit for 13
byte-identical feasibility groups. Two final 247,265-byte APWorld builds are
byte-identical at SHA-256
`22BF12DE2997AA23A160F4EDDE3B51D0EEE1D7FDEAE808CC72F20FA1056D0628`.

### Prepared shadow-state successor session

Operator-assisted closure of the two corrected isolation blockers was prepared
on 2026-08-17. All Archipelago/OpenGOAL applications were confirmed closed.
The previous installed APWorld was backed up to
`D:\Codex\Jak3\tmp\m11-installed-backups\20260817-final-review\jak3.apworld`.
The verified 247,265-byte build above was then installed at
`D:\Program Files\Archipelago\custom_worlds\jak3.apworld`, and its installed
SHA-256 matched exactly. A new room with no `.apsave` was created at
`D:\Codex\Jak3\tmp\m11-shadow-successor-server-20260817` from immutable seed
archive SHA-256
`7B6722EB50A69DE8B4112CC047E4F03CCA99A24107468B87A40FFA85C5FB842F`.
The hidden `ArchipelagoServer` PID at preparation was `5816`, listening only on
`localhost:38285`. The next resumable action is for the operator to launch the
installed Jak 3 Client, connect to that exact endpoint as `Player1`, create a
normal New Game in the already-disposable UI slot 4, save it once more to slot
4, and pause Jak on foot at the initial playable location. Before any runner
mutation, verify the endpoint from the managed client log, pair its same-suffix
bridge snapshot, back up both physical slot-4 banks, and create a new task-30
correlation ID.

After a machine restart on 2026-08-18, the prepared directory and archive were
revalidated before relaunch. It still contained zero `.apsave` files, port
38285 was free, and the installed APWorld remained exactly 247,265 bytes with
SHA-256
`22BF12DE2997AA23A160F4EDDE3B51D0EEE1D7FDEAE808CC72F20FA1056D0628`.
The server was restarted hidden as PID `28372`; both IPv4/IPv6 listener rows
resolve to that one process on port 38285. The operator launch/connect action
below is now unblocked.

### 2026-08-18 task-30 successor live boundary

The operator connected the installed client to the verified fresh room at
`localhost:38285` as `Player1`, started a normal non-Hero new game, selected
disposable UI slot 4, saved it again, and paused Jak on foot at the initial
playable location. The managed session suffix is
`2026_08_18_05_56_11_483030_13360`; its client log proves the exact endpoint,
and its same-suffix bridge snapshot reports native slot `3`, identity
`b52c1e68-e7b9-4c69-b435-3f2c3e713b6b`, `wasstada`, task/node `10/8`,
`current_act=1`, loaded/bound AP state, and no title/loading/cutscene/death/
restart/transition/vehicle flags.

Before mutation, active `bank6.bin` and `bank7.bin` were copied to
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-18T0602-ui-slot4-pre-shadow-successors`.
Source and backup hashes match at
`4193030B71B2A798242B68ACB30718A8E55F90FE35070E077F39936E5DBEBF84`
and
`CD3A744EADE577046B36C41423F37526AE507B9E04F500C93C5487F8D90BD6DF`.
The new task-30 correlation is `m11-task-30-shadow-8a041a4e`.

Its first `task30_scene_stage` attempt was rejected locally before any GOAL
form, checkpoint, or save mutation because the runner routed the continue-only
clean-start relocation through the ordinary mission-state preflight. The live
bridge correctly reported permanent-item safety `1` and mission-state safety
`0`; this is the same supported initial-save boundary used by the other
continue-only relocation presets. `task30_scene_stage` is now explicitly in
the allowlisted clean-start preset set, and a regression assertion requires
that classification while preserving all common slot and unsafe-state gates.
All 63 focused runner tests pass after the correction. At
`2026-08-18T06:10:09-04:00`, both active save hashes still matched the pre-test
values above, proving the rejection was a harness/setup discrepancy rather
than an operator or native-game failure. The next resumable action is to retry
that stage with the same still-empty correlation, then let the temple
transition settle and pause before activation/capture.

The corrected retry succeeded at `2026-08-18T06:10:51-04:00`. The runner
recorded bridge revision `730`, native slot `3`, snapshot SHA-256
`FABA8EDAAB490C64A64434BD36752DB0A5A06678C6AD96E3A477648BEDAE5E97`,
and a `task30_scene_stage` preparation in the correlation. Both active save
bank hashes remained unchanged at `2026-08-18T06:11:05-04:00`. The next
operator checkpoint is to unpause, allow the continue transition to settle at
the flooded-temple/task-30 door scene without entering another menu or saving,
then pause and report the visible location and whether the scene is stable.

The operator reported Jak paused and stable in front of the closed task-30
door. At `2026-08-18T06:13:29-04:00`, bridge revision `874` independently
confirmed `templea`, on foot, no task or task node active, no unsafe runtime
flags, and `safe_to_mutate_mission_state=1` on the same native slot/identity.
Both active save hashes still matched the protected baseline. This is the
accepted pre-activation scene boundary; the next runner action is the narrow
`task30_scene_activate` preset only.

`task30_scene_activate` succeeded at `2026-08-18T06:14:06-04:00` using fresh
bridge revision `907` and snapshot SHA-256
`45E7DA26BA8D72C8679DD5164E35BE387B63DDE6002598374A2B4FDB06C1A1D7`.
Both protected save-bank hashes remained unchanged immediately afterward. The
operator must now unpause without moving Jak, allow several game ticks for the
typed door event, then pause and report whether the circular door opened.

The operator confirmed that the door opened without movement and the game
remained paused and stable. The first mask-`0` capture then produced the exact
native controls: task-30 item mask `0`, portal present/open `1/1`, intro node
closed `1`, and independent task/mission/reward masks `0/0/0`. It also exposed
a recorder-input omission: the live shadow capture path had not required the
checksummed AP state and therefore wrote the checkpoint without the required
AP relic/check controls. Testing stopped immediately; no positive variant was
attempted. Correlation `m11-task-30-shadow-8a041a4e` was finalized `BLOCKED`
with `run.json` SHA-256
`133B1E503A4000620AC68215BBB15810B8CD591723413FC0CFFDCB60DE2B739A`
and complete support-bundle SHA-256
`7AC4E4F13E3126276F206F468F07D96EB9802561FC759302C04A1F5A16B96CA8`.

The runner now requires the same-slot/same-identity checksummed AP state before
any live task-30 or task-63 capture, rejects manual substitution for its AP
checked-mask/relic fields, and derives the relic count from the explicit seven
finale-relic IDs in `received_item_counts`. All 64 focused runner tests pass.
The bound state is
`C:\Users\steph\AppData\Local\Archipelago\Jak3\state-v1\d90b6728be7c20cda364e6eebc3650919da74720df8e22380a37061b1c098453.json`,
whose SHA-256 at this boundary is
`1BFD126E395128864F4ECB806D77A6480D53BEAC3F8EBB1E24160E3587B67B34`;
its checksummed payload has zero checked locations and zero received relics.
Both protected save-bank hashes remained unchanged at
`2026-08-18T06:23:33-04:00`. Successor
`m11-task-30-shadow-81aba654` will reuse the already stable active scene,
record an idempotent narrow activation under its own fresh provenance, and
repeat all four captures with automatic AP controls.

That successor's mask-`0` numbers were exact, but its capture command omitted
the three required procedure assertions. The runner had allowed an evidence
write that could never finish `PASS`. Testing again stopped before a positive
variant. Correlation `m11-task-30-shadow-81aba654` was finalized `BLOCKED` with
`run.json` SHA-256
`B17B82AD5443008745C381D0D6AF2CA0513D36770285122AE384C798699027F5`
and complete bundle SHA-256
`452FE4E17EF2A743F1D635FD06E584B27A2C27491B2392BF76E775C5A342FABB`.
Live task-30/task-63 capture now rejects any missing procedure assertion before
running the preset or writing a checkpoint; the 64-test focused suite covers
both this gate and automatic AP-state derivation.

Final successor `m11-task-30-shadow-87b40f81` then reused the still-stable scene
and recorded its own idempotent narrow activation. All four assertion-complete
captures passed exact item masks `0`, `16`, `7`, and `23`; each independently
captured portal present/open `1/1`, intro node closed `1`, task/mission/reward
masks `0/0/0`, and checksummed AP relic/check controls `0/0`. Snapshot revisions
`1591`, `1607`, `1622`, and `1639` were unique. The run finalized `PASS` with no
decision reasons; final `run.json` SHA-256 is
`6903C32B28A4A1B89187456C52313BBC69DFAD97D592D34D5EA7E0143A36A965`
and complete sanitized bundle SHA-256 is
`3A5D265D2589AD7D524A6BC51A788744B724FED2D75A29FE0AB895A7462FF7E5`.
At `2026-08-18T06:27:56-04:00`, both active save-bank hashes still matched the
protected baseline. Task 30 is complete. Before task 63, keep the game paused
and close the game, client, and compiler without loading or saving; the full
process boundary is mandatory because task-63 scene cleanup must never use an
ordinary load or an in-runtime abort.

The operator closed the game, client, and compiler without saving or loading.
At `2026-08-18T06:31:53-04:00`, no `gk`, `goalc`, or managed Jak 3 client
process remained. Fresh-room server PID `28372` continued to own both listener
rows on `localhost:38285`. Active `bank6.bin` and `bank7.bin` still matched the
protected baseline hashes. Task-63 successor
`m11-task-63-viewer-7aa9d3b9` is started for native slot 3. The next operator
action is a clean client/compiler/game launch, exact-room connection, ordinary
load of disposable UI slot 4, and pause on foot after the load settles; no
task-63 scene is staged until the new managed log/snapshot pair and bound AP
state are verified.

The operator relaunched, connected, loaded UI slot 4, and paused on foot. The
new managed suffix is `2026_08_18_06_33_36_105370_7804`. Its client log proves
authentication to `ws://localhost:38285` as team 0/slot 1. Bridge revision `89`
reports native slot `3`, the same identity
`b52c1e68-e7b9-4c69-b435-3f2c3e713b6b`, loaded/bound AP state, `wasstada`,
task/node `10/8`, and no unsafe runtime flags; both save banks remain unchanged.
The next runner action is only `task63_clear_intro_stage`, the allowlisted
clean-start relocation to `forest-pillar-start`.

The clear relocation succeeded at `2026-08-18T06:37:17-04:00` with fresh
bridge revision `179` and snapshot SHA-256
`C6C2105E898042E3129E9D5C2C3675927D07D9B68622D5AC758C532FBC607DBD`.
Both save-bank hashes remained unchanged. The operator must now unpause, allow
the forest relocation to settle, pause at the peninsula/pillar area before any
telescope cutscene, and report the visible stable location.

The operator reported the forest peninsula stable with no cutscene. At
`2026-08-18T06:38:51-04:00`, bridge revision `264` confirmed `foresta`, on
foot, no active task/node or unsafe runtime flag, and mission-state safety `1`
on the same native slot/identity. Both saves remained unchanged. This is the
accepted clear-variant pre-scene boundary; the next runner action is the
restricted `task63_clear` stage, which clears only the five viewer artifact
bits and spawns only the registered resolution scene if it is absent.

The clear scene stage succeeded at `2026-08-18T06:39:25-04:00` with fresh
bridge revision `293` and snapshot SHA-256
`F7866AB67C95720DD80B4426AC30901815191DE937065C7E8934F8AFA8B0A52E`.
Both save hashes remained unchanged. The operator must unpause, wait until the
telescope presentation is visibly playing, pause during that cutscene (not
after it completes), and report that exact state. The runner will capture only
after the bridge independently reports the active-cutscene boundary.

The operator paused after the viewer cutscene began. Bridge revision `361`
independently reported `in_cutscene=1` with every other unsafe flag clear. The
assertion-complete `artifacts_clear` capture then passed at revision `377`
(snapshot SHA-256
`BA1849028107BCFD860B29C6444E1266FE40B16B8A93FF7456E223FAC13C6ED1`):
viewer mask `0`, scene available/active `1/1`, telescope/time-map actor mask
`12`, task/mission/reward masks `0/0/0`, and checksummed AP relic/check controls
`0/0`. Both save banks remained unchanged at
`2026-08-18T06:41:13-04:00`. The clear checkpoint is accepted. The active scene
must now be destroyed only by closing the paused game, client, and compiler;
do not unpause, save, load, skip, or invoke in-runtime cleanup. The server stays
running for the separate set-variant process.

The operator closed all three applications at the active clear cutscene. At
`2026-08-18T06:42:55-04:00`, `gk`, `goalc`, and the managed client were absent;
server PID `28372` still owned port `38285`; and both protected bank hashes
remained unchanged. This is the accepted process-only destruction boundary.
The next action is a fresh client/compiler/game launch, exact-room connection,
ordinary load of UI slot 4, and pause on foot before any set-variant staging.

The operator relaunched and paused the set variant. Managed suffix
`2026_08_18_06_50_12_339047_4392` proves the same exact endpoint and
slot/identity; bridge revision `56` was stable at the loaded start and both
save banks were unchanged. `task63_set_intro_stage` succeeded at
`2026-08-18T06:51:55-04:00` with fresh revision `70` and snapshot SHA-256
`653AA7C869CB668CE5742AFF9EC994BD02FAA75CDE2A8048764F47EE53988E6D`.
The operator must now let the forest relocation settle, pause at the peninsula
before any cutscene, and report the stable location.

The operator reported the forest boundary complete. Bridge revision `129`
confirmed stable `foresta`, on foot, no active task/node or unsafe runtime
flags, mission-state safety `1`, and unchanged save banks. The set scene stage
succeeded at `2026-08-18T06:53:12-04:00` with fresh revision `142` and snapshot
SHA-256
`1372B300AD84D592D975F0151CC4067EF27819CE71F81BEEC33ACC4B5F71E613`.
Its pre-scene artifact write is staging-only and is not accepted evidence. The
operator must now pause during the playing telescope cutscene; only then will
the capture-only preset apply mask `1984` at the active lifecycle boundary and
atomically query all controls.

The operator paused during the set viewer cutscene. Bridge revision `215`
independently confirmed `in_cutscene=1` with every other unsafe flag clear. The
capture-only `artifacts_set` preset then applied the five bits at the active
scene boundary and captured fresh revision `229`, snapshot SHA-256
`0148DC8CAF112F3E2963E917635D2B7ED877328009964058A08C56A9E30C85BA`:
viewer mask `1984`, scene available/active `1/1`, telescope/time-map actor mask
`12`, task/mission/reward masks `0/0/0`, and checksummed AP relic/check controls
`0/0`. Both save banks remained unchanged.

Task-63 successor `m11-task-63-viewer-7aa9d3b9` finalized `PASS` with no
decision reasons. Final `run.json` SHA-256 is
`CBD252352B5537E024AF2EF9351FC68955A36B862023658BE6038968B03E83CD`;
complete sanitized bundle SHA-256 is
`513AF462C008D1C969853931F8DD6021791C6C6115C0590EE1E27125B57EF82E`.
The operator-assisted Milestone 11 successor testing is complete. The final
runtime cleanup is to keep the game paused and close the game, client, and
compiler without unpausing, saving, loading, or skipping; then verify process
exit and unchanged bank hashes before stopping the local server.

The operator confirmed all three applications closed. At
`2026-08-18T06:57:09-04:00`, `gk`, `goalc`, and the managed client were absent;
the protected save-bank hashes were still
`4193030B71B2A798242B68ACB30718A8E55F90FE35070E077F39936E5DBEBF84`
and `CD3A744EADE577046B36C41423F37526AE507B9E04F500C93C5487F8D90BD6DF`.
The remaining listener was verified by executable path and command line as the
runner-owned local server PID `28372`, then stopped. Port `38285` was free after
shutdown. This is the terminal operator and process-cleanup checkpoint; no
further Milestone 11 operator action is pending.

## Final provenance audit and required successor refresh

A 2026-08-20 review found that two historical positive artifacts predated the
final per-boundary provenance contract:

- Haven `m11-haven-task-35-95ab560f` has two checkpoints, zero checkpoint
  `bridge_snapshot` records, and no `bridge_snapshot_uses` ledger.
- Side challenges `m11-side-challenges-bc09ed7c` has seven checkpoints, zero
  checkpoint `bridge_snapshot` records, and no ledger.

Both runs and their bundle hashes remain immutable historical behavioral
evidence. They are not accepted `SAFE FALLBACK`/`PASS` evidence. Milestone 11 is
reopened until new successor correlation IDs reproduce those matrices with one
fresh, unique, run-slot-matched snapshot on every stage and capture boundary.

The runner now initializes an empty provenance ledger for every run. Terminal
`PASS` and `SAFE FALLBACK` decisions reject missing, duplicate, stale,
wrong-slot, mismatched, unexpected, or synthetic provenance. A complete offline
matrix may exercise validators but defaults to `BLOCKED` and cannot be promoted
by a positive review. Positive reviews copy and revalidate the source
preparations and snapshot-use ledger.

Resume from an all-applications-closed state. Start a fresh named local room,
verify the exact endpoint and installed APWorld, launch the game/compiler and AP
client, load only the operator-selected disposable slot, and back up both
physical banks. Run Haven first: record fresh `before_entry` and `mission_start`
boundaries and confirm playable geometry plus missing Samos/Keira without
synthesizing tasks 14-34. Stop and diagnose any mismatch before side challenges.
Then use a fresh side-challenge successor and repeat all seven zero-cost,
activation/reload, course hidden/open/reload, and cleanup checkpoints. The
operator receives one short controller action at a time; every accepted capture
must be made while the matching snapshot is under five seconds old. Finalize
and bundle each successor exactly once, then update the authoritative decision,
verification, status, and risk documents with the new IDs and hashes.
The automated correction passes 65 focused runner tests and 116 combined
runner/diagnostics tests in the packaged environment. Ruff lint/format and mypy
pass; the source audit passes with no roots, only `-OpenGoalRoot`, and both
`-OpenGoalRoot`/`-DecompileRoot` explicit. The complete packaged suite passes
431 tests. Two 246,525-byte APWorld builds are byte-identical at SHA-256
`DDD30507C144D7F94AE09E6C6B4B855E0C03C36266CF634BE29AF4D2660E9723`.
These automated results close the harness defect, not the two missing runtime
successors.
### Provenance-successor room prepared

The verified 246,525-byte APWorld (SHA-256
`DDD30507C144D7F94AE09E6C6B4B855E0C03C36266CF634BE29AF4D2660E9723`)
was installed after backing up the prior package to
`D:\Codex\Jak3\tmp\m11-installed-backups\20260820-provenance-refresh`.
The separate active OpenGOAL project was atomically refreshed to bridge source
set `dfc172d0516923dd3d00d5f2e0bf71b2839d8989f537c641868679b00c94eb45`.
No game, compiler, or AP client process was running during installation.

Fresh room PID `29728` is listening only on `127.0.0.1:38286` from
`D:\Codex\Jak3\tmp\m11-provenance-successor-server-20260820`. It started with
no `.apsave` from seed archive SHA-256
`7B6722EB50A69DE8B4112CC047E4F03CCA99A24107468B87A40FFA85C5FB842F`.
The next operator action is to launch Jak 3 Client through the Archipelago
Launcher, allow Debug gk/goalc compilation to finish, connect to
`localhost:38286` as `Player1`, start or load only the agreed disposable slot,
and pause at the debug start. Do not load another slot or save until the agent
has verified the managed log, snapshot, room identity, and native slot.

### Provenance-successor room restarted after host reboot

On 2026-08-21, after the operator reported that the host had restarted, the
same prepared room was restarted from
`D:\Codex\Jak3\tmp\m11-provenance-successor-server-20260820` without reusing or
overwriting the earlier server logs. The seed archive still hashes to
`7B6722EB50A69DE8B4112CC047E4F03CCA99A24107468B87A40FFA85C5FB842F`, and no
room `.apsave` was present; the server therefore reported `No save data found,
starting a new game`. Hidden process PID `24996` was verified listening only on
`127.0.0.1:38286`. Successor output is preserved in
`server.restart-20260821.stdout.log` and
`server.restart-20260821.stderr.log`. The next operator checkpoint remains:
launch the installed Jak 3 Client, connect as `Player1`, and pause without
loading, creating, or saving a native slot until the live binding is verified.

### 2026-08-21 live connection and pre-load backup

The operator launched the verified client and connected as `Player1` to the
restarted room at `localhost:38286`, then paused at the debug-start scene
without loading, creating, or saving a native slot. The managed session suffix
is `2026_08_21_04_09_07_909531_24180`. The server log records the matching
join, and the client log records the authenticated room plus bridge source set
`dfc172d0516923dd3d00d5f2e0bf71b2839d8989f537c641868679b00c94eb45`.
The same-suffix bridge snapshot was stable at revision `216`, reported
`wascitya`, `save_loaded=0`, `native_save_slot=-1`, no transition/cutscene/
death/vehicle flags, and SHA-256
`B49ACA0DD3B214D0B0F368E1CADC289D2943F59BA5C6AC8889E8AFC00CAAB214`.

Before any native slot was loaded, both active save banks were copied to
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-21T041417-ui-slot4-pre-provenance-successors`.
The source and backup hashes match: `bank6.bin` is
`4193030B71B2A798242B68ACB30718A8E55F90FE35070E077F39936E5DBEBF84`
and `bank7.bin` is
`CD3A744EADE577046B36C41423F37526AE507B9E04F500C93C5487F8D90BD6DF`.
The next operator action is to reach the native load menu and load only
UI slot 4, then pause without saving or moving so the agent can verify its
zero-based native slot and binding before starting the Haven successor.

### 2026-08-21 Haven provenance successor started

After UI slot 4 loaded, the same live snapshot reported native slot `3`, save
identity `b52c1e68-e7b9-4c69-b435-3f2c3e713b6b`, level `wasstada`, task/node
`10/8`, `current_act=1`, loaded/bound AP state, and no unsafe runtime flags.
Both active bank hashes still matched the pre-load backup exactly. Fresh
correlation `m11-haven-task-35-b3c3d40f` now owns native slot 3.

The restricted `haven_task35_hub_candidate` preparation succeeded without a
runtime/compiler error and recorded `stage:haven_task35_hub_candidate` with
bridge revision `410`, snapshot age `923` ms, native slot `3`, and snapshot
SHA-256 `EE9547359F35DF0708B9D02A503FA718E484A0F8B19F38E29D44D3D761607002`.
No native save bank changed. The next operator action is to unpause only long
enough for the allowlisted `ctygenb-samos` continue to settle, then pause
without moving and report the visible location plus whether Samos or Keira is
present.

### 2026-08-21 Haven AP-control capture correction

The operator confirmed a stable, playable Haven city candidate with both Samos
and Keira absent. Correlation `m11-haven-task-35-b3c3d40f` captured exact native
controls at unique bridge revision `612` (snapshot age `1098` ms, native slot
`3`, SHA-256
`1DF7FF345E0ED0E5C1F16AE4852AF799637604FDEDDACB5DA2FDBA8FACED47EE`):
task/mission/item/reward/actor masks were all `0`, loaded-level mask was `7`,
and passage mask was `1`. The capture then exposed a recorder omission: Haven
was not in the checksummed AP-state path, so the immutable checkpoint lacked
its required AP inventory and checked masks. Side challenges had the same
latent omission. No native save bank changed and operator testing stopped.

The incomplete correlation was finalized `BLOCKED` and bundled rather than
edited. Final `run.json` SHA-256 is
`3082D59FD61269BA5EA33F22E5A24147057A5577F496B67E5B50C0CD87729A7F`;
complete support-bundle SHA-256 is
`8B6CB3BB17DDE5FE0D119045379335532DE0C4A16CD216EBF9508F3039C3953A`.
The runner now requires a checksummed, same-slot/same-identity AP state for live
Haven and side-challenge captures, rejects caller-supplied substitution of the
relevant AP fields, derives Haven inventory/check masks and side relic/check
controls automatically, and preserves the existing native query. Ruff and all
66 focused runner tests pass. The current bound state is
`C:\Users\steph\AppData\Local\Archipelago\Jak3\state-v1\d90b6728be7c20cda364e6eebc3650919da74720df8e22380a37061b1c098453.json`;
it validates against native slot 3/save identity and reports AP inventory mask
`0`, checked mask `0`, ledger revision `17`, and relic count `0`.

Because the clean-start relocation can only be staged from the ordinary start
continue, the next operator action is one normal reload of UI slot 4, followed
by an immediate pause without moving or saving. A new successor correlation
will then repeat the idempotent Haven stage and both required captures with the
checksummed AP controls.

### 2026-08-21 Haven checksummed successor retry

The operator reloaded UI slot 4 without moving or saving. The live bridge again
proved native slot `3`, the same save identity, `wasstada`, task/node `10/8`,
Act I, loaded/bound AP state, and safe on-foot flags. The checksummed bound AP
state reported inventory mask `0`, checked mask `0`, ledger revision `20`, and
relic count `0`; both protected bank hashes remained unchanged.

Replacement correlation `m11-haven-task-35-fc238cee` was created and the
restricted `haven_task35_hub_candidate` stage succeeded. Its unique provenance
records bridge revision `1023`, snapshot age `693` ms, native slot `3`, and
snapshot SHA-256
`F0FBEAF7DE3E93A34CB330B6F16EF8CCA7DD1935FF620362A0D164DA670287B1`.
The next operator action is to unpause only until the relocation settles, pause
without movement, and reconfirm playable geometry with Samos and Keira absent.

### 2026-08-21 Haven successor accepted

The operator again confirmed stable playable Haven geometry with Samos and
Keira absent. The corrected `before_entry` capture recorded unique bridge
revision `1101`, age `222` ms, snapshot SHA-256
`F51565ABFED7133457DC595796BC4CF8E10716D005239627EF9D51889DEB61BC`,
task/mission/item/reward/actor masks `0`, loaded-level mask `7`, passage mask
`1`, and checksummed AP inventory/check masks `0/0`. The distinct
`mission_start` capture recorded revision `1116`, age `485` ms, snapshot
SHA-256 `384C06DFDAAB7F15DE70C7EE6B2744AEC65DD913D5FA035B871AF7D8E6CA75CA`,
the same numeric controls, operator geometry `pass`, and required actors
`fail`. Both the Haven fallback-specific validator and final provenance
validator returned no blockers.

Correlation `m11-haven-task-35-fc238cee` is finalized `SAFE FALLBACK` and has
one complete sanitized bundle. Final `run.json` SHA-256 is
`493A0EB0B9E858CDC6D9A0BDDE68A2D80EDB663C7161840E3D90C73063B76E39`;
bundle SHA-256 is
`9F67499CC22803689EC75EF6E5DB64FEC6188EAA57EEE8C792DE29A182AE7BE3`.
The active `bank6.bin` and `bank7.bin` hashes still exactly match the protected
baseline. This closes the Milestone 11 Haven evidence refresh while preserving
the predefined convergence gate for Milestones 18/19. The next operator spike
is the fresh side-challenge provenance successor.

### 2026-08-21 side-challenge provenance successor started

The operator reloaded the unchanged UI-slot-4 baseline. The bridge proved native
slot `3`, `wasstada`, task/node `10/8`, the same save identity, loaded/bound AP
state, and safe on-foot flags. The checksummed AP state reported checked mask
`0`, relic count `0`, inventory mask `0`, and ledger revision `24`; both save
banks still matched their protected hashes.

Fresh correlation `m11-side-challenges-d429b84e` was created. The restricted
`side_zero_cost_desb4_intro_stage` preparation succeeded with bridge revision
`1277`, snapshot age `907` ms, native slot `3`, and snapshot SHA-256
`78CEB2028DDD2BC44BACD1C9F8EC3EF49525D2AE284A4BA6037EAC412CBCBD3B`.
The next operator action is to unpause only until the desert marker scene is
stable, pause without interacting, and report Jak's location plus whether the
nearby challenge pedestal appears active.

The operator completed that settle checkpoint and reported a stable, paused,
on-foot scene. A read-only `side_marker_desb4` probe then found marker
availability `1`, activation `0`, displayed cost `0`, and event resolution
`0` (all other intro/parent/resolution controls `0`). Because the native event
has not resolved its original price, this zero is an uninitialized/default
value and is not accepted as free-cost evidence. No interaction occurred and
this is a staging condition rather than a side-challenge failure. The next
step is the restricted task-counter refresh, followed by a second read-only
probe that must report `side_event_resolved=1` and the original native cost
`8` before the free-cost override is applied.

The allowlisted `side_zero_cost_desb4_refresh_stage` preparation then
succeeded at unique bridge revision `1452`, snapshot age `837` ms, native slot
`3`, and snapshot SHA-256
`839A52009B31CD03AD0F0244EAB25E7A66698FE14EB84F6CD0B78E807D2859A0`.
Both protected native save-bank hashes remained unchanged. The operator must
now briefly unpause without moving or interacting so the native task event can
update, then pause for the confirming read-only marker probe.

After that exact three-second settle, the operator again reported a stable,
paused, on-foot scene with no prompt, vehicle, cutscene, or active-looking
pedestal. The confirming read-only probe remained `available=1`,
`event_resolved=0`, `displayed_cost=0`, and `activation=0`. Investigation of
the immutable earlier behavioral run showed that the runner had allowed the
refresh out of order: the proven initialization sequence first suppresses the
guarded parent reward, opens the child intro node, re-enters the marker
continue, and only then increments the task counter. The current correlation
was therefore finalized `BLOCKED` without checkpoints rather than being
rewritten. Final `run.json` SHA-256 is
`EC7AA73CEA3C4F6CCE8C3452677F508F90809B094B6E20B8AC06FE0C7707E1BE`;
complete bundle SHA-256 is
`72540634FE3013F126872620C6E36F3FB51D3EB93D4B72BA9B15540B32177989`.

The runner now enforces the exact five-stage side initialization prefix before
any live mutation and rejects a duplicate or out-of-order stage with a fresh-
correlation instruction. Ruff and all 67 focused runner tests pass. Because
the premature counter increment is transient and the protected banks remain
unchanged, one ordinary reload of UI slot 4 will restore the clean start for a
new same-spike correlation.

### 2026-08-21 side-challenge ordered successor

The operator reloaded UI slot 4 and paused on foot without saving or moving.
The bridge proved native slot `3`, save identity
`b52c1e68-e7b9-4c69-b435-3f2c3e713b6b`, `wasstada` task/node `10/8`, loaded
and bound AP state, and no unsafe flags. Checksummed AP state revision `25`
still contained zero inventory, checked locations, local orbs, and local gems;
both protected save-bank hashes remained unchanged.

Fresh correlation `m11-side-challenges-15ecab70` was created under the fixed
exact-order contract. Its clean `side_zero_cost_desb4_intro_stage` relocation
used bridge revision `1906`, age `567` ms, native slot `3`, and snapshot
SHA-256
`9F72BD9F3602197885FCD8497F52E6C703A525DE734BEDE2A0CF9CF0941E142F`.
The next operator action is to unpause only until the desert scene settles,
then pause without moving or interacting.

The operator reported the resulting desert scene stable and paused on foot,
with no active-looking pedestal, minimap icon, prompt, vehicle, or error. The
read-only probe found the typed marker actor (`available=1`) and all parent,
child, resolution, event, cost, and activation controls at zero. The enforced
guarded suppression stage then used bridge revision `2013`, age `252` ms, and
snapshot SHA-256
`172D65B56AF5C63F73C54AABC273830CA7DCE82531F9B64760FA93020CE1C580`.
Read-only verification showed only parent command suppression changed to `1`;
both save-bank hashes remained unchanged.

The child-intro activation stage used bridge revision `2041`, age `485` ms,
and snapshot SHA-256
`BDDAD012328100DE82E4691BE475D4B7D2221AAD09087E51B4246E3E4B5E0CE2`.
The probe then showed parent shadow closed `1`, suppression `1`, child intro
open `1`, resolution closed `0`, marker available `1`, and unresolved event,
cost, and activation `0/0/0`. The marker-continue re-entry used revision
`2063`, age `606` ms, and snapshot SHA-256
`4062551CBE568AE781E168E592EB75D87F5076AC8EDA94EE6F4544AF37B6BC7E`.
The operator must now briefly unpause without movement or interaction so that
continue transition can settle before the final task-counter refresh.

The operator completed that settle and reported the challenge minimap icon
visible. Read-only controls remained at the exact pre-refresh state: marker
available `1`, parent shadow/suppression `1/1`, intro open `1`, resolution
closed `0`, and event/cost/activation `0/0/0`. The final ordered
`side_zero_cost_desb4_refresh_stage` used bridge revision `2169`, age `84` ms,
native slot `3`, and snapshot SHA-256
`11D04AA65F6B2854DAE755D19CE91C4C4B74DF8BA9B8E609E179F272F310C26A`.
The operator must briefly unpause once more without movement or interaction so
the marker actor consumes the refreshed native task counter; the following
read-only probe must prove event `1` and original cost `8` before the free-cost
capture is allowed.

The operator then observed the pedestal active with a prompt showing the
original cost `8`. The read-only probe agreed exactly: marker/event/cost/
activation `1/1/8/0`, parent shadow/suppression `1/1`, and intro open `1`.
Only after that positive control, the capture-only typed override recorded
`zero_cost_before` at bridge revision `2281`, age `486` ms, and snapshot
SHA-256
`98200AF58FB939B50907EC428CC3BD8C45A4FD8BBE15578638C4B4D44A9C0BAA`.
It proved previous/displayed cost `8/0`, event/marker `1/1`, activation `0`,
zero native Gems, unchanged AP check/relic controls `0/0`, and both required
procedure assertions passed. The next operator action is one normal pedestal
interaction, followed by an immediate pause once the challenge begins.

The operator confirmed displayed cost `0`, successful challenge entry, no
vehicle, and no error. The `zero_cost_after` capture at bridge revision `2396`,
age `615` ms, and snapshot SHA-256
`6DAF63F180A6E4B910176F7275EC2D62290F5BE5D7C1ECFB0645E16A16635851`
proved activation `1`, event resolved `1`, active/play icon `4`, zero Gems,
parent suppression `1`, unchanged AP check/relic controls `0/0`, and all three
procedure assertions passed. The next boundary is an ordinary save to UI slot
4 followed by an ordinary load of that same slot; no other slot may be used.
The operator saved UI slot 4. `bank6.bin` remained at protected SHA-256
`4193030B71B2A798242B68ACB30718A8E55F90FE35070E077F39936E5DBEBF84`;
newly written `bank7.bin` became
`0618900C22F887A2AA376F9BA207509610713DE577F86973B109FBC263F82A9D`.
The bridge retained native slot `3`, the same save identity, and task/node
`137/409` before load. The operator then performed an ordinary UI-slot-4 load.
Jak loaded in a vehicle near the active pedestal; the challenge-specific HUD
was absent and the pedestal/minimap icon were available. This is the expected
native distinction between persisted kiosk activation and a live task-manager
session.

The `zero_cost_reload` capture used bridge revision `2607`, age `876` ms, and
snapshot SHA-256
`8A69E82C78A2146AE58F50169B1E99AB7F98C70DE69631E4B61FFB2E3F5112C5`.
Side-specific persistence remained correct: marker/event/activation
`1/1/1`, displayed cost `0`, parent suppression `1`, purchase history `0`, and
zero Gems. The same boundary reproduced the release-blocking native
reconstruction leak: native items changed `0 -> 243803`, bounded reward mask
`32 -> 63`, AP checked mask `0 -> 255`, Jetboard mask `0 -> 3`, task-30 item
mask `0 -> 19`, and broad task/mission/feature state became populated. AP relic
count stayed `0`. Testing stopped immediately; no course stage was attempted.

Two harness expectation defects were identified while finalizing this evidence.
The ordered setup deliberately closes `desert-beast-battle-resolution`, which
is bit `32` in the corrected bounded reward query, so clean pre/active evidence
expects `32`, not `0`. After entry, the native `event.tex` field changes from
the zero-cost icon to play icon `4`; that value is not a four-Gem displayed
price. The runner now encodes those meanings and, for future live captures,
preserves a contradictory checkpoint as failure evidence but raises
immediately so testing cannot silently continue. Ruff and all 68 focused
runner tests pass after the correction.

Correlation `m11-side-challenges-15ecab70` is terminal `BLOCKED`; final
`run.json` SHA-256 is
`DFF7F3D61DAAA0F68C007E3F0A5276B34D6CD01E6E42A4A70CD3A9D586B955B6`;
complete sanitized bundle SHA-256 is
`DFD55540DA5D08C46D2047305D8A6638050F5B95E4E732FD03D666A98BE9199A`.
The free-entry behavior passed through ordinary reload, but the full seven-row
side matrix remains blocked by the separately accepted native-reconstruction
failure and four unrun course rows. Milestone 14 owns reconstruction repair;
Milestone 22 must repeat the full side matrix afterward. This is the terminal
Milestone 11 operator boundary: no further controller action is required.


## 2026-08-21 final process and disposable-save cleanup

After the operator confirmed the game, Archipelago Text Client, and compiler
were closed, process inspection found none of those three runtimes. The managed
Milestone 11 room was still present as `ArchipelagoServer` PID `24996`, verified
as the sole listener on `127.0.0.1:38286`; that exact process was stopped and a
successor inspection proved both the PID and listener absent. The unrelated
Archipelago Launcher UI and its multiprocessing child were left untouched.

Before restoration, UI slot 4's two active banks under
`C:\Users\steph\AppData\Roaming\OpenGOAL\jak3\saves\BASCUS-97330AYBABTU!`
were copied to the recoverable folder
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-21T-final-cleanup-ui-slot4-post-side-before-restore`.
The verified archived hashes are:

- `bank6.bin`:
  `4193030B71B2A798242B68ACB30718A8E55F90FE35070E077F39936E5DBEBF84`.
- `bank7.bin`:
  `0618900C22F887A2AA376F9BA207509610713DE577F86973B109FBC263F82A9D`.

Only those two active files were then restored from the protected pre-test
baseline
`D:\Codex\Jak3\tmp\milestone11-save-backups\2026-08-21T041417-ui-slot4-pre-provenance-successors`.
Post-copy SHA-256 verification exactly matched the protected baseline:

- `bank6.bin`:
  `4193030B71B2A798242B68ACB30718A8E55F90FE35070E077F39936E5DBEBF84`.
- `bank7.bin`:
  `CD3A744EADE577046B36C41423F37526AE507B9E04F500C93C5487F8D90BD6DF`.

The runtime was not reopened after restoration. The final side-challenge state
remains recoverable in the post-test archive, while the operator's disposable
slot is back at the protected pre-provenance boundary.
