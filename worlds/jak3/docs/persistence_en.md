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

For the first binding, the native save must be explicitly verified fresh and
unprogressed. A binding is permanent:

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

Live observation of native identity and fresh-save eligibility is deferred to
Milestone 7. Milestone 6 provides and tests this policy through the Python
persistence API without modifying game inventory or native saves.
