# Protocol 3 runtime and receipt-bearing command contract

## First-release semantic freeze

Protocol 3/game integration 2 is frozen for the first-release boundary as of
Milestone 7.2. The freeze covers native tag 900/version 1, authorization record
version 1, descriptor-qualified loaded/bound acknowledgement, the current
command/result/error meanings, signed-32-bit command fields, and the eight
newest receipts scoped to one game-session nonce. Later gameplay milestones
must consume this contract without reinterpreting it. Any semantic change
requires a protocol bump and an explicit compatibility and migration decision.

The optional diagnostic-schema-1 projection remains outside command semantics:
it may be repaired or extended compatibly without changing the control nonce,
receipt ring, persistence decisions, or Protocol 3 result.

Protocol 3/game integration 2 is the Milestone 7 control boundary. The GOAL
bridge rewrites one framed text snapshot; matching `snapshot_begin` and
`snapshot_end` revisions reject torn reads. Required fields include the full
runtime/save/safety model, schema and table versions/hashes, client session,
game-session nonce, bridge runtime implementation version, last result/error,
reload-persistent bridge activation generation, and up to eight receipts.
Readers ignore unknown additional fields.

Milestone 7.1 adds an optional diagnostic-schema-1 section to that same
temporary snapshot. It contains the bounded GOAL producer's dropped count,
next sequence, positive reload-persistent diagnostic activation generation,
and at most 64 integer-only records. A malformed or
unacknowledged diagnostic section is discarded and recorded as a capture gap;
it never invalidates the required Protocol 3 snapshot or changes a command
result. Python drains and acknowledges records idempotently and remains the
only writer of the versioned JSONL timeline and support archive.
Source/channel readiness is reserved until acknowledged, and Python records
the original GOAL sequence plus a generation that advances on intentional
diagnostic reload. Every acknowledgement carries that activation generation;
the GOAL ring ignores a delayed acknowledgement for any earlier generation.

Bridge installation, compilation, and load order are declared by
`mod/opengoal/bridge-modules.json` version 1. The startup overlay loads before
`mi`; `archipelago.o`, `archipelago-diagnostics.o`,
`archipelago-items.o`, `archipelago-locations.o`, and
`archipelago-rewards.o` are registered immediately after `task-control.o` in
that order. The canonical source-set SHA-256 covers the
raw manifest plus each declared payload digest in manifest order, so changing
either the manifest bytes or any declared source retains the reload marker
until the control and diagnostics modules publish new compatible activation
generations and the items, locations, and reward modules publish their
individual activation proofs after the complete manifest-ordered load.
Packaging rejects
undeclared matching bridge sources recursively,
not only at the expected asset-directory depth.

The game-session nonce is created from Python-supplied UUID entropy on the first
hello after the bridge starts. It survives client reconnects because the client
probes an already loaded bridge and reuses the control module only when the
protocol/integration/schema/table version-and-hash contract matches. Optional
diagnostic incompatibility repairs only `archipelago-diagnostics.gc`, leaving
the control nonce, receipts, and test target intact. A game or
bridge restart creates a new nonce. Control-plane hello, ping, query, and
disconnect do not enter the mutating-command receipt ring; query is valid at
the title menu. AP authentication changes wake the serialized heartbeat loop,
so authorized save-identity entropy is published immediately instead of
waiting for the next periodic ping.

The snapshot's implementation-only bridge runtime version rejects an older
same-contract live object even when corrected source was already installed on
disk. The installer also records an actual packaged-source byte change in a
durable marker beside the installed source. The bridge activation generation
is a positive reload-persistent counter incremented by `ap3-init!` after a
successful source evaluation, and the diagnostics module publishes an
independent positive counter after its hooks and initial records are installed.
A forced reload records both pre-load generations, then requires a current
compatible snapshot with both values changed before protocol hello and before
clearing the marker. If no comparable generation
exists on a first or legacy install, the client establishes a current-source
baseline and performs one additional load to prove activation. Transport-level
nREPL completion alone never clears the marker. Ordinary client reconnects
still reuse an unchanged compatible bridge, preserving its nonce and receipt
ring; installing corrected source deliberately establishes a new bridge
session.

Mutating commands carry client and game session identities, a nonnegative
monotonic signed-32-bit ID (`0` through `2147483647`), a signed-32-bit kind and
integer payload, and the expected protocol/schema/table contract. Python
rejects values outside that wire width before reserving an ID or sending a
form. GOAL independently returns `INVALID_PAYLOAD` without recording a receipt,
advancing the high watermark, or applying the test target when any of those
three values is outside its snapshot/receipt field width. Control messages and
mutating commands also carry the client's AP
sidecar acknowledgement as a two-bit loaded/bound field plus the exact native
save slot and UUID that acknowledgement describes. The game accepts those bits
only when both descriptor fields match its live native save; a stale heartbeat
from a save being switched away from therefore cannot bind the replacement.
Every table hash must also be exactly 64 characters before it enters GOAL's
comparison buffer; an overlength value with a valid digest prefix remains a
table mismatch rather than being normalized by truncation.
The game keeps a high watermark and the eight newest receipts:

- an exact duplicate returns its stored result without applying again;
- a reused ID with a different kind or payload fails as a conflict;
- an older ID absent from the ring fails as out of order; and
- an old game nonce or different client session fails before mutation.

The client advances its allocator beyond every command ID that receives a
response, including an explicitly selected or replayed ID. A later automatic
command therefore cannot accidentally reuse an accepted explicit ID.

`SET_TEST_TARGET` accepts payload `0` or `1` and changes only a bridge-owned
boolean. A new command already at its target returns `ALREADY_APPLIED`.
`TEST_ADDITIVE_EFFECT` always fails with `ADDITIVE_EFFECT_FORBIDDEN`.
`QUEUED` is reserved and is never emitted in Milestone 7.

Bridge runtime version 3 adds the Milestone 8 extension command kind `102`,
`RECONCILE_PERMANENT_ITEMS`, without changing Protocol 3, game integration 2,
native tag 900, or any existing command/result/error meaning. Payload bits are
`0` Jetboard, `1` native yellow-gun/Blaster stage 1, and `2` native Armor stage
1; every other bit is invalid. The control plane repeats the existing exact
descriptor and command-time permanent-safety gates, then dispatches the mask
through the narrow `archipelago-items.gc` hook. That module applies the three
target bits idempotently and returns only `APPLIED`, `ALREADY_APPLIED`, or
`FAILED`. Python sends a fresh command after an uncertain result and advances
durable item state only after `APPLIED` or `ALREADY_APPLIED` is committed.

Bridge runtime version 4 adds only the Milestone 9 location-observation and
diagnostic-drain hooks used by the ordered `archipelago-locations.gc` module.
It does not change Protocol 3, game integration 2, native tag 900, slot data,
state schema, public location tables, or existing command/result/error
meanings. Location confirmation comes only from authoritative
`Connected.checked_locations` and `RoomUpdate.checked_locations`; a successful
`LocationChecks` send is never treated as an acknowledgement.

Bridge runtime version 5 adds the Milestone 10 order-60 reward module, expands
the existing observer to tasks 10–16 plus persistent reward node 36, and adds
narrow reward-observation and item-application-guard hooks. Every required
snapshot includes `items_module_active`, `locations_module_active`, and
`reward_module_active`; control resets all three to zero and each ordered
gameplay module sets only its own proof after installing all of its hooks (and
method 13 for rewards). Python rejects any inactive value both when probing an
existing bridge and when verifying a live reload, so an nREPL completion
barrier cannot masquerade as a complete gameplay-module activation. The reward
wrapper also requires all three proofs in its bound-mode predicate, preserving
the complete native grant during any partial-load interval. The
snapshot also exports the actual
three-bit permanent-item native target, or `-1` until the ordered items module
installs its readback hook. Python compares
that value with the bound durable ledger on every heartbeat and schedules safe
target-state reconciliation on any mismatch; correctness therefore does not
depend on a task/reward observation remaining available after acknowledgement.
The same `-1` sentinel is retained while reward node 36 has an incompatible
native command shape. A reward-owned safety hook also reports permanent-item
application as unsafe and rejects command 102 at dispatch time, preventing a
stale or restarted client from clearing the fail-open native Armor grant.
The exact task-16
wrapper preserves native behavior unless the save is bound in AP mode and the
audited command shape is still `add-jakc`, `add-armor-0`; only then does it
preserve Jak C and omit Armor 1. The development-only task-16 `StatusUpdate`
gate is Python-owned and does not alter Protocol 3, integration 2, state schema
1, slot-data version 2, public tables/hashes, or the task-72 goal.

Permanent/test mutation is safe only with a compatible, loaded, bound native
save during stable on-foot gameplay. Title, load, movie, death, resetter,
transition/teleport, vehicle/transformation, and ambiguous task-manager state
all force it false. Mission mutation additionally requires no active mission.
Dark and Light Jak are transformation states for this guard. A live target and
a currently observed level are positive requirements; the observer clears the
previous level before every scan so a transition cannot retain stale level
identity. Every mutating command refreshes these observations immediately
before checking safety; a prior heartbeat is never treated as a mutation
lease. Consumable safety remains false throughout Milestone 7.

Native save/load method slots 22 and 23 are wrapped only for numeric tag 900.
The bridge also wraps the native auto-save `done`/`error` code pointers so a
staged identity is committed or discarded by the matching I/O operation. Hook
installation preserves the real native targets across bridge-only reloads and
recaptures rebuilt native targets after a full game compile.
Diagnostic load tracking starts independently in the native auto-save `restore`
behavior before `mc-load`; this records both successful reads and failures that
never invoke method slot 23. The matching `done`/`error` wrapper clears this
diagnostic-only operation without changing the binding candidate or native
result.
The last successfully published identity, native slot, and monotonic
eligibility use OpenGOAL's reload-persistent globals. A bridge-only reload
restores that descriptor for the next native save, but deliberately resets the
client/session and sidecar acknowledgement bits so Python must acknowledge the
descriptor again.
The version-1 tag holds one canonical lowercase UUID. The client creates and
offers UUID entropy only after authenticated slot data is known. Before the
UUID can enter a control message, Python atomically writes a checksummed
version-1 authorization record containing that UUID and the authenticated
seed/team/slot/name. This record is separate from both schema-1 AP state and
native tag 900. A missing sidecar or an existing unbound sidecar may bind only
when this durable provenance exactly matches the currently authenticated slot;
the check therefore survives a client crash between native tag publication and
the first sidecar commit, as well as a crash between sidecar creation and its
binding commit. Already-bound compatible sidecars remain self-authenticating
and do not depend on retaining a proposal record.
Disconnected heartbeats and clean disconnect clear any unused proposal. An unused proposal
also expires five seconds after the last authenticated client contact, so an
unclean client exit cannot leave save mutation armed. Publication records the
consumed proposal in a game-owned snapshot acknowledgement before disarming it.
That acknowledgement remains independent of the current native-save descriptor:
the game rejects the consumed UUID and Python rotates to fresh entropy even if
the save is cleared or switched before the next heartbeat. Two new saves cannot
share one proposal. A native `new-game` save
always selects that live proposal instead of a previously published identity;
without authenticated proposal entropy it remains unbound. Missing or malformed
tags never block the native load, but the bridge clears save identity and
refuses AP binding. A failed tag append likewise invalidates the live descriptor
and sidecar acknowledgement before the untagged native write can be considered
AP-safe.
Identity is exposed only after that operation executes native `done` in slot
0-3; the matching `done` wrapper commits the descriptor to both live and
reload-persistent state before returning, so an immediate bridge-only reload
cannot discard a successful save that has not yet reached the observer's next
snapshot. The staged UUID, validity/success flags, eligibility, New Game marker,
and exact auto-save process handle are also reload-persistent. A bridge reload
while memory-card I/O is still pending therefore lets the newly installed
`done`/`error` wrapper resolve that same operation instead of abandoning it.
The observer retains the same guarded publication as a fallback.
Native `error` invalidates the staged identity even when a global status still
contains an older success. Fresh eligibility is read from the candidate save's
`new-game` summary plus serialized money/gem/skill totals and task completion
payload for tasks 6-137, never from the previously active game.
Observed progress flips eligibility monotonically to `INELIGIBLE` for that
identity only; switching to a different UUID uses the candidate save's own
attestation. Publishing a different identity or slot clears the previous
sidecar acknowledgement until Python acknowledges that exact new descriptor.
Every mutating command refreshes this descriptor-qualified acknowledgement
before re-observing safety, so an authentication or repository failure between
heartbeats also fails closed at command time. Missing, malformed, invalid-UUID,
duplicate, append-failed, and I/O-failed tag diagnostics remain snapshot-visible,
including across a bridge-only reload, until a valid identity is published.

The Python client is still the sole sidecar writer. It opens/switches schema-1
state only after authenticated slot data and a live descriptor are both known,
requires matching durable proposal authorization before any first binding, and
persists receipt-bearing command observations as `<game nonce>:<command ID>`.
Milestone 8 requests the full ReceivedItems stream and uses the existing
schema-1 indexed journal as the durable authority only for Jetboard, Blaster,
and Progressive Armor receipts. Receipt persistence precedes native
reconciliation; exact duplicates do not commit, gaps retain the expected index
and request `Sync`, and index zero atomically replaces the canonical history.
Unknown IDs and valid Jak 3 IDs outside that slice reject the complete packet.
Progressive Armor counts are retained without applying beyond native stage 1.
Protocol-2
sidecars fail compatibility read-only and are not migrated. Transport loss or
an incompatible reconnect closes any live writer session uncleanly and clears
the game's sidecar acknowledgement before the nREPL connection is released.

## Update and restart policy

Installing a changed APWorld or bridge is never a live player update. Finish
native memory-card I/O, close the client, `gk`, and `goalc`, install through the
normal Archipelago Launcher path, then start a clean game session. The durable
pending-reload marker must be cleared only by the normal compatible activation
attestation; deleting it manually is unsupported.

Official OpenGOAL v0.3.5 cannot accept a replacement compiler connection after
the original connection is lost. The sole supported first-release recovery
path after clean or unclean client/compiler loss is therefore to finish native
memory-card I/O and restart the client, `gk`, and `goalc` together. Warm
replacement attachment to the existing game is unsupported. A full-process
restart creates a new game nonce, discards the old eight-entry receipt ring,
and requires exact native-save rebinding before any mutation gate can reopen.
This operational limitation does not redefine the frozen Protocol 3 semantics.

External locking, replacement, or editing of native save-bank files is
unsupported upstream interference. Acceptance covers ordinary unlocked native
save/load and verifies that the same descriptor and sidecar recover after a
supported full-process restart; it does not promise recovery from injected
filesystem contention.

The 2026-08-10/11 closure observations passed this policy for both clean and
unclean client loss: each full-process restart issued a new nonce, started with
an empty receipt ring, remained unsafe before loading, and recovered the exact
descriptor-qualified sidecar binding. Ordinary unlocked save/load also passed.

Manual `(ml)` remains a developer/recovery aid only. It is unsupported during
native save/load or any other memory-card I/O, and future gameplay milestones
must not rely on arbitrary hot reload across such an operation.
