# Milestone 9 acceptance report

Date: **2026-08-12**

Status: **Implementation and automated gates pass; controlled live completion gate pending**

## Accepted implementation scope

- Native location `743001010` observes task 10 (`arena-training-1`) only through
  its save-persistent `task-complete?` result while the exact AP save descriptor
  is loaded and bound.
- Debug location `743001011` is reachable only through the explicit nREPL
  function `(ap-locations-debug-complete!)`.
- Python atomically commits the durable checked ID and pending outbox entry
  before acknowledging the GOAL diagnostic record or sending
  `LocationChecks`.
- A send result never acknowledges or compacts an outbox entry. Canonical
  `Connected.checked_locations` and partial `RoomUpdate.checked_locations` are
  the only confirmation sources.
- The durable local checked set is monotonic. Server rollback moves a durable
  checked ID back to pending and never clears it.
- Protocol 3, game integration 2, native tag 900, state schema 1, slot-data
  version 2, location-table version 2, and the frozen 147-location pool remain
  unchanged. Bridge runtime implementation metadata alone advances to 4.

Reward suppression, native task mutation, additional story/challenge/orb
checks, mission dispatch, and player-facing debug commands are absent.

## Automated acceptance

| Scenario | Evidence | Result |
| --- | --- | --- |
| First native/debug observation and replay | Pure transitions plus GOAL record ingestion | Pass |
| Commit before GOAL acknowledgement/send | Repository-backed ingestion and injected commit failure | Pass |
| Offline completion and both supported process restart models | Sidecar close/reopen/rebind simulations with repeated native observation | Pass |
| Sorted upload, closed/failed transport, duplicate resend, and five-second retry bound | Async client send tests for the normal outbox and item-gap `Sync` paths | Pass |
| Reauthentication isolation and shared send reservation | Stale-generation, compatibility-latch recovery, CommonClient gap-`Sync`, and concurrent outbox/`Sync` transport regressions | Pass |
| Pre-bind server-state accumulation | A newly bound sidecar consumes one canonical accumulated `Connected`/`RoomUpdate` snapshot without replaying stale packet history | Pass |
| Prechecked canonical `Connected` and server rollback | Full-set reconciliation transitions | Pass |
| Same-slot/co-op `RoomUpdate` | Partial delta reconciliation transitions | Pass |
| Confirmation-only compaction and permanent local bit | Exact checked/confirmed/pending partition assertions | Pass |
| Malformed, unknown, retired, disabled, and table-mismatched server state | Packet parser and CommonClient pre-dispatch tests | Pass |
| Diagnostic writer or GOAL-ring publication failure | Failed serialization replay test and source-boundary assertions | Pass |
| Durable native identity rather than transient state | Source assertions for `task-complete?`, descriptor qualification, and absence of actor/address identity | Pass |
| Native rewards remain untouched | Source boundary rejects task closing and mission-reward behavior | Pass |
| Batch and rollback diagnostics remain attributable | Bounded location/task ID allowlist and correlated send/reconciliation event tests | Pass |

Post-implementation reviews found and repaired seven diagnostic, transport,
and state-transition defects. A closed CommonClient socket can no longer be
mistaken for a successful send, and batch or rollback diagnostics name every
affected Milestone 9 location and task using bounded allowlisted arrays.
Location sends are qualified by the currently authenticated connection
generation; CommonClient's own item-gap `Sync` substitutes the durable outbox
for its volatile checked-location mirror; and normal retries plus item-gap
uploads share one five-second reservation. A newly bound state now reconciles
one canonical accumulated server snapshot instead of replaying stale pre-bind
packet history, and a valid reauthentication clears an earlier location
compatibility latch so protocol startup can resume.

The repository now owns its canonical `AGENTS.md`; standalone checkouts no
longer depend on a workspace-parent copy. This fixes the GitHub failure in
`OptionSchemaTest.test_canonical_sources_are_present_in_a_standalone_checkout`.

The exact deterministic 239,546-byte APWorld artifact has SHA-256
`372CF63B1B8A320D41B9E7F867518BBE0F4FD181EE1E2C8BAC2278DB1EE3FA2E`.
It passed all **340 tests** from the repository checkout against a disposable
Archipelago copy. Ruff lint, the 27-file format check, and mypy over 13 source
modules passed.

## OpenGOAL evidence

The installer registered the new order-50 module in the separate active
OpenGOAL project and produced ordered bridge source-set SHA-256
`cc6282d4990b1631befe5749d1883a283b989360c8e19f6039cdbe9596b7c4a4`.
Official OpenGOAL v0.3.5 compiled all **1,168 targets** in 42.385 seconds. An
nREPL smoke then loaded `archipelago.o`, `archipelago-diagnostics.o`,
`archipelago-items.o`, and `archipelago-locations.o` in manifest order with no
compiler errors. Calling the debug function without a bound AP save returned
safely and did not create a completion.

## Controlled live matrix

| Live scenario | Status |
| --- | --- |
| Bound nREPL debug check through Python and server confirmation | Pending |
| Real task-10 native completion | Pending |
| Offline upload and reconnect resend | Pending |
| Duplicate send and mission replay | Pending |
| Native save/load and game restart | Pending |
| Supported full client/`gk`/`goalc` restart | Pending |
| Prechecked `Connected` and same-slot `RoomUpdate` | Pending |
| Live proof that compaction retains the local bit | Pending |

These rows require a disposable authenticated AP room plus a tagged native save
that can exercise task 10 without altering the user's ordinary save or server
state. No such fixture was available in this implementation session, so the
rows are not inferred from unit tests or the unbound load smoke. Milestone 9's
roadmap completion gate therefore remains open even though the implementation
and automated gates pass.

## Remaining risks

- The live game-to-Python diagnostic handoff and real server reconciliation
  still need the matrix above.
- The task-10 poll is source-audited and compiled, but its exact real save/load
  timing has not yet been observed in the controlled matrix.
- Broader location families and goal reporting remain deferred. `R-007` stays
  open and this report does not close broader persistent-gameplay work.
