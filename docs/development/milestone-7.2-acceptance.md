# Milestone 7.2 live acceptance report

## Decision

**Pending.** The real OpenGOAL v0.3.5 run exercised all 15 mandatory rows.
Rows 1, 2, and 5–12 plus 14–15 passed. Rows 3, 4, and 13 failed mandatory
requirements, so Milestones 7 and 7.2 remain incomplete and Milestone 8 remains
blocked. The performance gates passed after separating normal gameplay content
allocation from warm client/bridge growth.

This run added no gameplay behavior. Production changes are limited to three
reproduced native-save defects in the Protocol 3 GOAL boundary and one
reproduced diagnostic-acknowledgement scheduling defect. An attempted
client-reuse workaround for row 3 failed live and was removed before the
authoritative artifact was built.

## Environment and artifacts

| Field | Recorded value |
| --- | --- |
| Runtime date | 2026-08-09, America/New_York; UTC evidence timestamps cross into 2026-08-10 |
| Jak3-AP base commit | `9fa6617569e39cf47129e4d34c5150bf776fd81c` plus this reviewed worktree |
| Live-tested APWorld | version `0.1.0`, 220,211 bytes |
| Live deterministic build A/B SHA-256 | `f74c13f2b0c24e44cc70be224ca4feefd167590e6ff3b29ed248f0fdb412adc5` for both builds |
| Final documented APWorld build A/B | 220,510 bytes; SHA-256 `6ca4ce729e6beed8bd5009ac3341e5e164637cf7ece5c59d85a71ec808d797ed` for both builds; all 293 packaged tests passed |
| Installed source-set SHA-256 | `fb3c2d69071c803fd0132b27bce1412a51f81028a74c2e780a30aed4441ace22` |
| Protocol contract | protocol 3, game integration 2, bridge runtime 2 |
| Archipelago | 0.6.7, frozen Python 3.13.11 |
| OpenGOAL | official v0.3.5 |
| Audited OpenGOAL reference | `425f143fccada9e38b35633bd298b5b64c6ca6e8` |
| Audited Archipelago reference | `feab54daec712ffb333b8c73f38eb69e1ed9c508` |
| Platform | Windows 11 build 26200, 64-bit; AMD64 family 25 model 97; 6 logical processors |
| Renderer | NVIDIA GeForce RTX 4080, OpenGL 4.3, driver 610.88, 3840×2160 |

Both live APWorld builds were produced independently and compared byte-for-byte.
The live artifact was installed through the normal Archipelago Launcher handler.
The client installed and activated its manifest-declared bridge sources; the
pending-reload marker was never manually removed.

After the acceptance report and packaged setup/restart policy were finalized,
two more builds produced the byte-identical final documented artifact shown
above. Its production semantics are the live-tested semantics; the package hash
differs because the packaged setup guide now contains the frozen first-release
restart policy and the touched Python source received mechanical formatting.

All native saves, AP sidecars, authorizations, snapshots, metrics, and process
logs used disposable roots beneath ignored `dist/milestone-7.2/live/`.
Existing user saves and sidecars were not used. One invalid row-9 harness
attempt launched an AP Launcher outside the isolated environment and created a
single 344-byte authorization in an otherwise empty default state root. After
the session closed, that exact file was hashed and removed and only verified
empty directories were removed. No user save or sidecar was present or
touched.

Raw logs, saves, sidecars, metrics, profiler traces, and support ZIPs remain
local and ignored. The committed report contains only sanitized session labels,
short descriptor/nonces hashes, event ranges, and evidence hashes.

## Method

One authenticated default-only local room was used. A human operator drove the
native menus and gameplay while `tools/milestone_7_2_recorder.ps1` recorded
UTC timestamps, restricted nREPL probes, sanitized snapshots, one-second
process/file samples, annotations, and SHA-256 evidence. Native save identity
was never printed in this report; descriptor values below are the first 16
hexadecimal characters of SHA-256.

The disposable saves were:

| Save | Native slot | Descriptor hash | Purpose |
| --- | ---: | --- | --- |
| A | 0 | `0debe8fcf21f0729` | primary AP save |
| B | 1 | `48f91b6d5d34bf59` | independent save-switch target |
| C | 2 | `cd635a2ac384a24a` | post-copy New Game and lock/recovery target |
| Vanilla | 3 | none | disconnected, untagged native control |

## Acceptance matrix

“Session/event evidence” names the sanitized recorder label and GOAL event
range where one was available. A session-scoped entry means the row is proven
by the recorded snapshots, hashes, and whole-session timeline rather than one
contiguous GOAL range.

| # | Expected | Observed | Result | State/descriptor/nonce evidence | Session/event evidence and gaps |
| ---: | --- | --- | :---: | --- | --- |
| 1 | Fresh A receives one stable identity and binds before progress. | Three focused defects were reproduced and repaired. Final retry emitted save start/success/publication, created revision 0, bound at revision 1, then monotonically changed from fresh to ineligible after native progress and reached revision 3. | **PASS** | A `0debe8fcf21f0729`; one nonce; no identity before native success. | `row-01-fresh-a-pass`, events 46–80. Earlier failed attempts and their crashes are retained. |
| 2 | Repeated A loads retain descriptor and sidecar. | Native bank hash and A descriptor remained identical across repeated loads; sidecar revisions changed only for ordinary close/open bookkeeping. | **PASS** | A stable; same game nonce. | `row-02-load-a-repeat-1/2`; session-scoped hashes. |
| 3 | Clean client-only restart keeps game nonce, receipts, and binding. | Save, nonce, binding, and receipt remained in the game snapshot, but v0.3.5 `goalc`/Deci2 replacement could not reconnect to the existing `gk`. A second source-guided reuse attempt crashed `goalc` on its first form. The workaround was removed. | **FAIL** | A and receipt retained; same nonce; Python could not safely reopen the binding. | `row-03-warm-reconnect-failed` and `row-03-fixed-warm-reconnect-upstream-fail`; full failed-session timelines. |
| 4 | Unclean client termination is detected and safely recovered. | The next session immediately emitted prior-unclean evidence, but the owned compiler exit hit the same one-connection v0.3.5 lifecycle and recovery could not attach to the existing game. | **FAIL** | A/nonce remained only in the stale snapshot; no unsafe mutation was attempted. | `row-04-unclean-recovery-fail`; prior-unclean event 1; bundle name/size/hash retained, but the ZIP has a final-audit retention gap. |
| 5 | Game restart changes nonce, rejects stale receipts, and reopens A. | Heartbeat loss was detected in about 3 seconds; replacement game attached in 1.910 seconds, nonce changed, receipt ring reset, and A rebound before safety became true. | **PASS** | Nonce `7112…` → `6a8d…`; A stable; receipt count 1 → 0. | `row-05-gk-restart-pass`; session-scoped. |
| 6 | Both startup orders work; game-first gap is explicit. | Client-first started and captured both processes. Game-first attached to existing processes, reached ready with a new nonce, and emitted one capture gap for each process’s pre-client stdout. | **PASS** | Fresh nonce per game session; later A binding normal. | `row-06-client-first-pass`, `row-06-game-first-pass`; expected pre-client capture gap. |
| 7 | A → B → A never transfers acknowledgement. | A closed, fresh B was created/bound/closed, and A reopened. Safety was all false between descriptors and became available only after exact descriptor acknowledgement. | **PASS** | A/B/A; one nonce; A reopened at revision 18. | Events 88–167. |
| 8 | Copying A to slot 2 is rejected; slot 0 recovers. | The copied UUID in slot 2 was rejected read-only with no new sidecar and all safety false. Original slot 0 reopened normally. | **PASS** | Copied A at wrong slot; A revision 19; same nonce. | Events 168–206. |
| 9 | Progressed untagged slot 3 stays read-only with no sidecar. | A game-only launch created and progressed slot 3. Connected loading reported `native-save-tag-missing`, identity absent, no AP state/binding, and all safety false. | **PASS** | No descriptor or sidecar; error 16. | `row-09-vanilla-read-only-pass`; one excluded retail-mode harness attempt and the isolated-launch provenance gap are documented. |
| 10 | Continue Without Save clears descriptor, acknowledgement, and safety. | A closed at revision 23; slot/identity/AP state/binding cleared before no-save gameplay and all safety remained false. | **PASS** | Same nonce; no descriptor; error 16 `native-save-not-loaded`. | Events 68–87. |
| 11 | New Game after A creates a fresh identity and does not reopen A. | Slot 2 created C and opened only C’s sidecar. | **PASS** | A `0de…` → C `cd6…`; same game session. | `row-11-new-game-after-a-pass`; session-scoped. |
| 12 | New Game overwrite never inherits AP metadata. | Occupied slot 2 contained copied A; New Game wrote the alternate bank and created C rather than inheriting A. | **PASS** | Native bank changed; descriptor A → C. | `row-12-overwrite-occupied-slot-pass`; session-scoped hashes. |
| 13 | Locked banks yield native failure diagnostics without publishing state, then recover. | Exclusive locks crashed `gk` twice with Windows C++ exception `0xe06d7363`; no graceful native failure event was emitted. Both banks and sidecar revision 3 stayed byte-identical, so no uncommitted identity/revision was published. After unlock and clean restart, a normal save changed the bank, C binding reopened, and revision advanced only through clean close/open to 5. | **FAIL** | C revision 3 unchanged during failure; normal recovery reached revision 5 with C stable. | `row-13-native-lock-failure` and `row-13-normal-recovery-proven`; two excluded no-save precondition attempts; bundle name/size/hash retained, but the ZIP has a final-audit retention gap. |
| 14 | Unique effect applies once, exact duplicate replays receipt, new no-op returns `ALREADY_APPLIED`. | ID 7201401 changed target 0→1 and revision 5→6; exact duplicate returned stored `APPLIED` with no receipt/revision growth; ID 7201402 returned `ALREADY_APPLIED`, receipt count 2, revision 6→7. | **PASS** | C; same nonce; receipt results 3 and 4. | Events 106–116. The recorder’s old 100 ms check missed the last transient acknowledgement; the durable ring proved it and the recorder now polls/reads the ring. |
| 15 | Queries work at title; unique mutation is unsafe/unbound. | Query completed in 184.215 ms. ID 7201501 did not change the target and returned result 6 `UNSAFE_NOW` with error 16. | **PASS** | No save/state/binding; title flag true. | `row-15-pass`; session-scoped snapshot. |

Mandatory result: **12 PASS / 3 FAIL**. No row bound the wrong save,
transferred an acknowledgement, published an uncommitted identity, or reported
mutation-safe without a compatible bound save. The three failures nevertheless
prevent the required release claim.

## Failure ownership

Rows 3 and 4 reproduce an OpenGOAL v0.3.5 process-lifecycle limitation.
`game/system/Deci2Server.cpp::accept_thread_func` returns after the first
compiler connection and leaves `client_connected` true. A replacement compiler
therefore cannot attach to the still-running game. This is not safely fixable
inside the APWorld control protocol.

Row 13 reproduces upstream native I/O behavior. `pc_game_save_synch` calls
`pc_update_card` before the later write path; `pc_update_card` reads existing
banks through `file_util::read_binary_file`, which throws `std::runtime_error`
when an exclusively locked file cannot be opened. That exception escapes the
memory-card thread and terminates the game. The immutable upstream reference
owns the defect. No AP production patch or speculative optimization was made.

## Performance baseline

### Startup and developer operations

| Measurement | Result |
| --- | ---: |
| Cold client nREPL attach | 1.280 s |
| Cold full `(mi)` | 26.736 s |
| Other cold full `(mi)` observations | 27.474–28.829 s |
| Unchanged-source final `(mi)` | 382.986 ms |
| Final manifest-ordered three-module `(ml)` | 782.841 ms total |
| Module loads | startup 189.049 ms; control 274.895 ms; diagnostics 264.142 ms |
| Game-restart reattach | 1.910 s |
| Unchanged-source client-only warm reconnect | **failed; no valid timing** |
| Support-bundle export | approximately 273 ms |

### Matched five-minute idle samples

The same loaded scene and the same `gk`/`goalc` processes were sampled first
with the client and then after `/exit` left the game running.

| Gate | Control | Connected | Delta/result |
| --- | ---: | ---: | --- |
| Normalized CPU p95 | 23.1428% | 23.4187% | +0.2759 points, **PASS** |
| Frame time p95 | 16.815 ms | 16.713 ms | −0.102 ms, **PASS** |
| Warm private-memory growth | 64 KiB aggregate | 660 KiB aggregate | <32 MiB, **PASS** |
| Client/game heartbeat | 0 Hz after client exit | 0.904/0.904 Hz | near 1 Hz, **PASS** |
| Snapshot writes/hour | 0 | 3,254.233 | 0.904 writes/s, bounded rewrite |
| Snapshot bytes/hour | 0 | 6,359,059.752 | bounded temporary snapshot |

The control trace contains 26 graphics-frame intervals and the connected trace
27. The connected trace was dumped after the operator had opened the in-game
start menu; that scene mismatch is a capture gap even though the measured gate
passes.

Connected quiet log growth was 1,150,389 bytes/hour for the client text log,
216,364 bytes/hour for the combined OpenGOAL log, and zero for the structured
timeline. Healthy heartbeat details produced 6,436 DEBUG lines and **zero INFO
heartbeat lines**. Rotation/retention bounds storage; snapshot files are
rewritten rather than accumulated.

### Thirty-minute connected gameplay

The 1,799.738-second sample contained 1,755 one-second observations. Normalized
CPU p95 was 24.2844%. Client/game heartbeats were both 0.9018 Hz; snapshot rate
was 3,246.473 writes/hour and 5,012,332.771 rewritten bytes/hour. Log growth was
1,157,623 bytes/hour client, 1,273,252 bytes/hour combined OpenGOAL, and 216,706
bytes/hour structured events.

Aggregate private memory grew 704,520,192 bytes, but process separation shows
normal gameplay content allocation rather than client/bridge leakage:

| Process | Private-memory change |
| --- | ---: |
| AP client | −8,232,960 bytes |
| `goalc` | +1,900,544 bytes |
| `gk` while loading/playing new content | +710,852,608 bytes |

The warm same-scene comparison, not content-loaded `gk` growth, is the selected
32 MiB bridge/client gate. No speculative memory optimization is justified.

## Evidence hashes

| Evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| Sanitized recorder stream | local | `15109f9192bed946476d4f90fbe389b5c2fe6f5777280913baefd3ec3f320c3c` |
| Paired five-minute metrics | local | `7a7658ab520706098232e0e3c98b2d80982901aa3f429fb0da80696f7bc1993b` |
| Thirty-minute metrics | local | `2db8747748a79b78a94d1f44db3f37ef8a380f5206fc218a7226ea0bc910d5fc` |
| Control profiler trace | 3,516,733 | `38c77f30bc80aff084d33522d9d59b800f8a991d6186552fed46dcf20d7da7c8` |
| Connected profiler trace | 3,530,953 | `90953a2ede507711daa8945b93b869a156cb08732b78eccdfc97380705b0de23` |
| Row-4 crash-following bundle | 8,127 | `0d5303f7ccc275819d99869289d5e6fca3baa25857da66e5eca397c11766ddf8` |
| Row-13 crash-following bundle | 362,610 | `224cdc5f0fc6d428d3e4a4370690c71c31c728143f8592954580dd9382368aa5` |

The recorder retains both exported bundle names, byte lengths, and hashes, and
the associated local session/native-bank evidence remains under the ignored
evidence root. A final file audit did not find either ZIP under that root, so
the bundle bytes themselves are an explicit retention gap and cannot be
re-inspected. `/diagnostics export` is the supported command; `action=bundle`
is not valid.

## Final verification

| Check | Command surface | Result |
| --- | --- | --- |
| Focused regressions and recorder fixtures | Disposable Archipelago `pytest` selection for acknowledgement contention, analyzer gates, profiler parsing, and durable receipt polling | 4 passed |
| Complete packaged suite | `python -m pytest <Jak3-AP/tests> -q -p no:cacheprovider` from the disposable Archipelago copy with the exact final APWorld installed | 293 passed; one expected optional `_speedups` warning |
| Python lint | `ruff check --ignore E402 worlds/jak3 tests` | Passed |
| Python format | CI 23-file `ruff format --check` surface | Passed after mechanical formatting |
| Python typing | CI 11-module `mypy --ignore-missing-imports --follow-imports=skip` surface | Passed |
| Audited native tables | `tools/verify_source_tables.ps1 -OpenGoalRoot ..\jak-project` | All six groups passed |
| Deterministic package | Two independent `tools/build_apworld.ps1` runs after formatting | Both 220,510 bytes and SHA-256 `6ca4ce729e6beed8bd5009ac3341e5e164637cf7ece5c59d85a71ec808d797ed` |
| Native compile/load | Full `(mi)` and manifest-ordered `(ml)` against official v0.3.5 | Passed; source set `fb3c2d69071c803fd0132b27bce1412a51f81028a74c2e780a30aed4441ace22` |
| Immutable references | `git status --short` before/after source use in `jak-project` and `Archipelago` | Clean before and after; `openGOAL-decompile` has no Git metadata and remained read-only |

Raw local evidence remains under ignored `dist/milestone-7.2/live/`; the two
final verification packages remain under ignored
`dist/milestone-7.2/post-format-verification-{a,b}/`.

## Protocol 3 semantic freeze and release policy

The first-release semantic contract is frozen at protocol 3/game integration
2: native tag 900 version 1, authorization record version 1,
descriptor-qualified loaded/bound acknowledgement, existing command/result/
error meanings, signed-32-bit command fields, and the eight-entry per-game-
session receipt ring. A later semantic change requires a protocol bump plus an
explicit compatibility and migration decision. Optional diagnostic schema 1
remains failure-isolated and does not change that contract.

The intended unchanged-source policy is that a client/server reconnect may
leave the game open and retain its nonce, receipts, and descriptor. Rows 3 and
4 prove that official OpenGOAL v0.3.5 does not currently satisfy that policy
after the compiler connection is lost. Until the prerequisite is fixed or an
approved safe limitation is recorded, the operational workaround is a clean
restart of client, `gk`, and `goalc`; this is a release blocker, not a silent
policy change.

For a changed APWorld or bridge:

1. Finish all native memory-card I/O.
2. Close the client, `gk`, and `goalc` cleanly.
3. Install the APWorld/update through the normal launcher path.
4. Start a clean game/compiler/client session and let activation attestation
   clear the pending-reload marker. Never remove the marker manually.

Live `(ml)` remains developer/recovery-only and is unsupported during native
memory-card I/O. No first-release workflow promises arbitrary hot reload while
a save/load is active.

## Completion gate

Protocol 3 meanings are frozen, but the freeze does not waive runtime
acceptance. Rows 3, 4, and 13 require an upstream-compatible repair or an
explicitly reviewed safe limitation followed by reruns. Milestones 7 and 7.2
remain pending and Milestone 8 must not begin.
