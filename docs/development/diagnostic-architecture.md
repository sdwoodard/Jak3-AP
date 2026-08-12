# Diagnostic architecture

Milestone 7.1 adds an observability boundary without changing Protocol 3,
schema-1 persistence, save binding, runtime safety, or harmless-command
semantics. `worlds/jak3/agents/diagnostics.py` is the only support-file writer.
OpenGOAL may print emergency traces to captured stdout, but it does not open a
human log, JSONL stream, or support archive.

## Artifacts and ownership

Each client run initializes these three UTF-8 artifacts with one session ID:

```text
Jak3Client_<session>.txt
Jak3OpenGOAL_<session>.txt
Jak3Events_<session>.jsonl
```

The first two remain human-readable. The third is a Python-ordered diagnostic
schema version 1 timeline. Python serializes all events under one lock and
assigns the monotonic `event_sequence`; each component also supplies or
receives a `source_sequence`. A rejected or unserializable event is reported
through the same registry when possible and otherwise only to stderr. Logging
failure is never allowed to change persistence, protocol, safety, or state.

Every JSONL envelope includes the schema version, global and source ordering,
UTC observation time, component, source monotonic value or game tick,
severity, stable event name, bounded message, session/correlation/process/task
fields, frozen protocol and integration versions, optional runtime and
persistence revisions, and allowlisted `context` and `details` objects.

## GOAL producer and drain

`archipelago-diagnostics.gc` owns a 64-record integer-only ring. Its fixed
emission interface carries event code, severity, correlation kind/value,
result/error, and three bounded integer arguments. It assigns source sequence
and game tick. On overflow it drops the oldest record and increments a
monotonic dropped counter.

OpenGOAL real functions have an eight-argument ABI limit. The public
nine-field `ap-diagnostic-emit!` contract is therefore a macro that packs only
severity and correlation kind for the internal hook; the producer immediately
unpacks them into separate ring fields. The snapshot and Python envelope
retain all nine values.

The control module retains every runtime, save, binding, and command decision.
It only invokes no-fail diagnostic hooks. The diagnostics module registers the
ring emission, snapshot export, and acknowledgement hooks after
`archipelago.gc` loads. Ring records are appended to the existing temporary
snapshot channel. Python drains them idempotently, identifies duplicates,
sequence gaps, and overflow, then calls the diagnostic-only acknowledgement
function with both the producer activation generation and source sequence. A
delayed acknowledgement from an earlier loaded object therefore cannot drain
records from the new generation after its sequence space resets. A malformed
optional record or failed acknowledgement cannot make a valid Protocol 3
snapshot, ping, or command fail.

The client retains the diagnostic activation generation, next source sequence,
and dropped-count projection across nREPL reconnects. A changed activation
generation, a backwards next-sequence value, or recovery from a missing or
malformed channel resets Python's drain high-water mark before new records are
accepted. Persistent missing/malformed, drain, and acknowledgement failures
are transition-latched until recovery. Repeated unacknowledged records likewise
produce one duplicate event and a bounded shutdown suppression summary instead
of heartbeat noise; a drain-completed event is written only when Python accepts
at least one new record.

The initial source-loaded and channel-ready records are reserved outside the
ordinary overflow queue until acknowledged. Later bursts therefore cannot
erase the initialization evidence. Python preserves GOAL's source sequence in
the envelope and increments a `source_generation` whenever that producer is
intentionally reloaded and its new diagnostic activation generation is visible,
so repeated sequence numbers remain unambiguous. A completed nREPL request by
itself does not advance Python's generation.

Native save and load diagnostics use operation metadata separate from the AP
binding candidate. Save instrumentation begins in the existing save wrapper.
Load instrumentation begins in the native auto-save `restore` behavior before
`mc-load`, so an I/O failure that never reaches `game-info.load-game` is still
recorded. The matching native `done` or `error` behavior emits exactly one
outcome and clears only that diagnostic metadata; it does not decide whether a
save identity is valid or published.

Correlation kind `1` is rendered as `native-slot:<slot>` and kind `2` as
`command:<command-id>`. The latter deliberately matches the Python protocol
producer so a submitted command and its GOAL-side result share one correlation
identifier. Unknown future nonzero kinds remain distinguishable without being
interpreted.

## Bridge manifest

`mod/opengoal/bridge-modules.json` is manifest version 1 and declares this
exact order:

1. `archipelago-startup.gc` in the pre-`(mi)` phase;
2. `archipelago.gc` / `archipelago.o`; and
3. `archipelago-diagnostics.gc` / `archipelago-diagnostics.o`; and
4. `archipelago-items.gc` / `archipelago-items.o`.

The three objects are registered contiguously after `task-control.o`. Packaging,
standalone and installed-client repair, full compilation, bridge-only load,
activation verification, and support summaries consume the manifest rather
than wildcard discovery. Packaging recursively rejects every staged
`archipelago-*.gc` source that is not declared, including sources nested below
the normal asset directory. The canonical source-set SHA-256 hashes the raw
manifest digest and each ordered payload digest. Any manifest byte or declared
source change therefore leaves a durable reload obligation until a compatible
new control-module and diagnostic-module activation generation is observed.
Both the installed-client repair path and the standalone installer hold the
same atomic directory lock for the complete staged replacement transaction, so
concurrent processes cannot publish a mixed source set or project registration.
An aged lock owned by a still-running process on the same host is never stolen;
age-based recovery remains limited to owners whose liveness cannot be checked.

## Capture and retention

The balanced default is 8 MiB per segment, three backups per artifact, ten
sessions, fourteen days, and 256 MiB for managed diagnostics including support
archives. The current session is created before pruning and is protected from
retention deletion. Startup pruning reserves the remaining configured rotation
growth of all live sessions, not only the process performing the prune, and
policy validation rejects an active rotation footprint that cannot fit inside
the managed cap. A new session falls back to console diagnostics when the sum
of live reservations cannot fit. The same reservation is repeated after a
primary-to-temporary fallback across both storage generations. Before
publishing a support archive, the exporter reserves the archive plus all live
remaining growth; if another archive would exceed the managed cap, export
fails cleanly instead of deleting live-session evidence or growing without
bound. Archive creation, pruning, capacity checking, and atomic publication use
one process-wide lock. Startup marker publication, startup pruning/checking,
primary-to-temporary marker transfer/pruning/checking, and bundle publication
all use that lock, so concurrent clients cannot omit another reservation or
both reserve the same remaining bytes. A marker publication failure disables
file diagnostics instead of admitting an unleased writer. Client-side overrides use
`JAK3_DIAGNOSTICS_SEGMENT_BYTES`, `JAK3_DIAGNOSTICS_BACKUPS`,
`JAK3_DIAGNOSTICS_SESSIONS`, `JAK3_DIAGNOSTICS_DAYS`, and
`JAK3_DIAGNOSTICS_MANAGED_BYTES`; positive values must also pass the documented
hard safety bounds enforced by `DiagnosticPolicy`.

Main-thread, asyncio, and background-thread failures are fingerprinted and
deduplicated. Child process output is normalized for UTF-8, line endings, and
ANSI escapes while it is read in bounded pipe chunks; no raw unbounded spool
file is created. Complete process lines are sanitized as units. An unbroken
line over 16 KiB is omitted before storage and represented by one capture-gap
event, preventing an arbitrary chunk boundary from separating a credential key
from its value. A missing pipe or pipe read failure is also an explicit
capture-gap event, and abnormal exit is classified separately. A pre-existing
game or compiler is a capture gap because its earlier stdout cannot be
recovered.

A small atomically replaced marker distinguishes clean and prior-unclean
sessions and carries a hashed host, process ID, last-seen time, and remaining
rotation reservation. Local liveness requires both a running process ID and a
writer-renewed 30-minute lease, preventing a later reuse of a crashed client's
PID from protecting evidence forever. Remote markers use the same lease because
their process cannot be inspected locally. Retention protects every
artifact belonging to a live local or leased remote session; concurrent clients
therefore neither report one another as crashed nor prune one another's logs.
An inactive, locally dead, or lease-expired marker remains eligible for the
normal one-time prior-session report.
Primary storage falls back to a temporary directory, then stderr-only capture.
When primary storage fails mid-session, readable primary artifact generations
remain part of the export snapshot and the clean/unclean marker transfers to
the temporary directory; the pre-failure evidence is not abandoned.
Later primary sessions scan both the primary and canonical temporary diagnostic
directories, so a crash after fallback is still classified and all managed
artifacts continue to participate in the same retention budget.
Initialization removes only incomplete `Jak3Support_*.zip.tmp` archives left by
an earlier abnormal exit; completed bundles and unrelated temporary files are
not candidates.

## Redaction and bundles

Normal structured events accept only registered event names and per-event
allowlisted fields. Object-valued fields are rejected unless that event also
declares the object's nested keys; recursive undeclared objects are rejected at
emit time and again while bundle segments are read. Text normalization removes
ANSI sequences, redacts quoted, unquoted, and structured
password/token/secret/API-key assignments including separator-free mixed-case
keys such as `accessToken` and `clientSecret`, complete Authorization and
Digest header values, and credential URLs, and replaces every canonical UUID
shape with a stable hash.
Seed identifiers, slot names, native-save identities, and nonces are correlated
only by hashes. Persistence binding errors identify only the mismatched field;
they never render either identity value into an exception or human log. If an
otherwise valid event exceeds a configured segment, the
writer retains its required envelope and compact context instead of dropping
the event; exception events preserve the newest traceback suffix that fits.

`/diagnostics export` writes a timestamped local ZIP beside the logs. It merges
validated event segments chronologically and includes sanitized copies of both
human logs, runtime and version/source-set summaries, persistence counts and
status, recent command results, capture gaps, a README, and a versioned bundle
manifest with SHA-256 checksums. Missing optional inputs make the export
`partial` and are declared. If a sanitized human log exceeds its bundle bound,
the archive retains the newest evidence, inserts an omission marker, records
the artifact in the manifest's `truncated` list, and reports a partial export.
Native saves, schema-1 sidecars, authorization records, packet/form dumps,
memory dumps, credentials, and uncontrolled files are never candidates. Each
provider also has an explicit top-level and nested field schema; an unexpected
field makes only that optional snapshot missing. The capture-gap summary is
derived from the same bounded, sanitized `process.capture_gap` and
`diagnostics.capture_gap` events as the timeline, so launcher, pipe, protocol,
and collector gaps cannot diverge from bundle evidence.
Export runs off the client heartbeat loop, retries in temporary storage if the
primary archive write fails, records completion only after atomic publication,
and never uploads automatically. Every timeline line must contain all schema-v1
fields and is revalidated against the stable registry and that event's
context/detail allowlists before it enters the archive. Unknown future optional
envelope fields are ignored; missing required or invalid known fields discard
the malformed record.
