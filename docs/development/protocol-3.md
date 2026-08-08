# Protocol 3 runtime and harmless command contract

Protocol 3/game integration 2 is the Milestone 7 control boundary. The GOAL
bridge rewrites one framed text snapshot; matching `snapshot_begin` and
`snapshot_end` revisions reject torn reads. Required fields include the full
runtime/save/safety model, schema and table versions/hashes, client session,
game-session nonce, bridge runtime implementation version, last result/error,
reload-persistent bridge activation generation, and up to eight receipts.
Readers ignore unknown additional fields.

The game-session nonce is created from Python-supplied UUID entropy on the first
hello after the bridge starts. It survives client reconnects because the client
probes an already loaded bridge and reuses it only when the complete
protocol/integration/schema/table version-and-hash contract matches. A game or
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
successful source evaluation. A forced reload records the pre-load generation,
then requires a current compatible snapshot with a different generation before
protocol hello and before clearing the marker. If no comparable generation
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
persists harmless receipts as `<game nonce>:<command ID>`. Protocol-2
sidecars fail compatibility read-only and are not migrated. Transport loss or
an incompatible reconnect closes any live writer session uncleanly and clears
the game's sidecar acknowledgement before the nREPL connection is released.
