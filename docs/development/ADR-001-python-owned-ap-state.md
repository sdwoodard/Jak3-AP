# ADR-001: Python-Owned Atomic AP State

- Status: Accepted
- Date: 2026-08-07
- Milestone: 6

## Context

The protocol-2 bridge currently exports only a temporary handshake snapshot.
That file is intentionally session-scoped and cannot own Archipelago progress.
Milestone 6 needs one persistent boundary that survives client and game
restarts, rejects the wrong seed or native save, and can retain progress while
the Archipelago server is unavailable. It must also avoid Python and GOAL
writing the same file.

The first release requires a fresh, unprogressed native save. Importing a
progressed vanilla save would require an audited merge between native rewards
and the AP ledger and is outside this milestone.

## Decision

The Python Jak 3 client is the only process allowed to write persistent AP
state. GOAL never opens or edits the persistent sidecar. GOAL continues to own
only its temporary observation snapshot; later milestones will hold game-side
events there until Python acknowledges that they have been committed. The AP
server may be disconnected during that exchange, but the Python client must
remain running. Playing AP content with the Python client closed is unsupported
for the first release.

State lives below the platform user-data directory at
`Archipelago/Jak3/state-v1`, with `JAK3_AP_STATE_DIR` as an explicit portable or
test override. A sidecar filename is the SHA-256 digest of the opaque native
save identity. The payload also stores the native slot and authenticated
seed/team/slot identity, so a copied save cannot silently rebind.

The native save identity and fresh-save eligibility are opaque inputs to this
layer. Milestone 7 must obtain them from live game state before production
binding is enabled. Milestone 6 implements and tests the complete binding
engine without adding a save hook or changing native inventory.

One nonblocking operating-system lock covers the state root for the lifetime
of a writer session. A second Jak 3 client may inspect state read-only but
cannot bind or commit. Lock release is tied to the process/file descriptor, so
a crash does not leave an authoritative stale-owner record.

Each state file is a canonical JSON envelope containing a schema-1 payload and
the SHA-256 of that payload. A commit:

1. validates the in-memory state and expected revision;
2. writes and flushes a unique same-directory temporary file;
3. refreshes `.bak` atomically from the last validated primary;
4. atomically replaces the primary; and
5. performs a best-effort directory sync where the platform supports it.

A corrupt, empty, truncated, malformed, or checksum-invalid primary is never
silently overwritten. The repository validates `.bak`; if it is compatible,
the corrupt primary is quarantined under a unique timestamped name and the
backup is restored atomically without consuming the backup. Without a valid
backup, corrupt bytes are quarantined and loading fails. Schema, version,
table, option, seed, team, slot, and save mismatches are compatibility or
binding failures rather than corruption: they remain read-only and are not
quarantined or replaced from backup.

## Native save lifecycle policy

- Missing state may be created only when the caller explicitly attests that
  the loaded native save is fresh and unprogressed.
- An unbound state binds once, after native and authenticated AP identities are
  both known. Rebinding is forbidden.
- Copying a bound save to another native slot preserves its identity and is
  rejected because the recorded slot differs.
- Deleting a native save does not delete its sidecar. Restoring that save to
  its original slot reuses the same sidecar and can recover its `.bak`.
- A new fresh save in a reused slot must have a new native identity and gets a
  different sidecar.
- Multiple live copies on different machines are unsupported. Same-machine
  concurrent writers are prevented by the root lock.

## Consequences

Python can provide robust atomic replacement, checksums, quarantine, backups,
and actionable errors without extending GOAL file handling. Server outages do
not block durable local AP state as long as the client stays attached. A player
must back up both the native OpenGOAL save and the Jak 3 AP sidecar, and must
not clone one bound save into multiple live installations.

This milestone does not request `ReceivedItems`, submit `LocationChecks`, hook
missions or rewards, report victory, or mutate native game state. Those systems
may populate the schema-defined journals only in their assigned milestones.
