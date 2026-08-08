# Jak 3 AP state, backup, and restore policy

The Python Jak 3 client is the only persistent AP-state writer. OpenGOAL writes
only its temporary bridge snapshot. Keep the Python client running during AP
play, including while the AP server is disconnected; playing with the client
closed is unsupported for the first release.

State is stored below the platform user-data directory at
`Archipelago/Jak3/state-v1`. `JAK3_AP_STATE_DIR` may override that root for a
portable installation or tests. Each opaque native-save identity selects a
SHA-256-named `.json` sidecar, with a retained `.json.bak`. The native slot and
AP seed/team/slot/name binding also remain inside the checksummed payload.
The same root contains `save-identity-authorizations-v1`, whose small
checksummed records durably associate each proposed UUID with the authenticated
seed/team/slot/name before that UUID is offered to the game. Back up the whole
`state-v1` directory, including this subdirectory.

For the first binding, the native save must be explicitly verified fresh and
unprogressed, and its proposal authorization must match the currently
authenticated AP slot. This check also applies if a crash left an unbound
sidecar. A binding is permanent:

- restoring the same save identity to its original native slot is supported;
- copying that identity into another native slot is rejected;
- deleting a native save leaves its AP sidecar available for recovery;
- a new fresh save has a new identity and therefore a new sidecar; and
- divergent live copies across machines are unsupported.

Only one writer session may own the state root on a machine. A second client
fails without waiting or changing state.

To back up or move a save, close the Jak 3 client cleanly and copy the native
OpenGOAL save together with the entire `state-v1` directory. Restore both to
the original native slot. Do not merge JSON files, change bindings, or replace
only the primary while leaving a backup from another point in time.

Every commit preserves the last validated primary as `.bak` before atomically
replacing the primary. If a primary is malformed or checksum-invalid, the
client validates the backup first, moves the corrupt bytes to a unique
`.corrupt.<timestamp>.<suffix>` name, and restores the compatible backup while
retaining it. If no valid backup exists, loading stops and no replacement state
is created. Interrupted temporary files are similarly preserved as diagnostic
evidence. Version, hash, option, seed, team, slot, name, and native-save
mismatches are read-only failures: they are not quarantined, rolled back, or
rebound.

Protocol 3 embeds a version-1 metadata tag with numeric ID 900 and a canonical
128-bit UUID in native saves. Missing or malformed tags never block native
loading, but they disable AP binding. Identity becomes visible only after a
successful native save/restore with slot 0-3. Fresh eligibility requires a
native new-game save with zero completion, collectible totals, and completed
tasks 6-137; once progress is observed, eligibility becomes ineligible for that
loaded identity. No inventory or mission data is stored in the native tag.
If an upgrade finds a tagged fresh save with neither a bound sidecar nor its
durable proposal authorization, it refuses first binding instead of guessing
which AP slot authorized that UUID.
