# Troubleshooting and diagnostic logs

Every Jak 3 Client run preserves the matched human-readable support pair and
adds a Python-owned structured timeline. All filenames contain the same session
ID:

```text
Jak3Client_<session-id>.txt
Jak3OpenGOAL_<session-id>.txt
Jak3Events_<session-id>.jsonl
```

`/diagnostics` or `/diagnostics summary` flushes the current snapshot and prints
all three paths. Prefer `/diagnostics export` when reporting a problem: it
creates a sanitized, checksummed ZIP beside the logs and reports whether the
export is complete, partial, or failed. Export runs in the background so the
five-second game-contact safety window remains live, and it never uploads
automatically.

## What the pair records

The client log covers the Archipelago and mod side of the session:

- APWorld, Archipelago, Python, operating-system, and executable versions;
- detected OpenGOAL paths, ordered source-set SHA-256, registration/repair results, process
  IDs, and the exact launch commands;
- nREPL connection attempts, bounded form summaries, completion barriers, and failures;
- AP connection state, hashed room seed/slot identity when correlation is needed, and the
  temporary handshake session;
- the persistent sidecar root and contract-validation, binding, recovery,
  quarantine, and read-only failure status;
- protocol and game-integration versions, connection-ready state, heartbeats,
  the last command/result, and the bridge status message; and
- an on-demand handshake snapshot plus uncaught background-task tracebacks.

The OpenGOAL log combines captured `gk` and `goalc` stdout/stderr through
bounded, sanitized complete lines in chronological file order; no unbounded raw
spool is created. Unbroken lines over 16 KiB are omitted before storage and
recorded as capture gaps so a credential cannot straddle sanitization chunks.
It includes the verbose game boot, graphics/runtime errors, compiler
output from `(mi)` and bridge live-loading, process exit codes, and `[JAK3-AP]`
emergency traces emitted by the in-game bridge. OpenGOAL does not append to this
file directly.
Both commands request disabled ANSI colors, and the collector strips any
terminal-control sequences still emitted by OpenGOAL's REPL UI.

The JSONL timeline contains versioned, registered lifecycle, compatibility,
save, binding, safety, command, persistence, exception, rotation, capture-gap,
and export events. The GOAL-side 64-record ring is drained through the temporary
snapshot channel into this Python-owned file.

## Capturing a useful reproduction

1. Close every old Jak 3 `gk`, `goalc`, and Jak 3 Client process. Output from a
   process started before the client cannot be attached retroactively; the
   client logs a warning if it detects this condition.
2. Start **Jak 3 Client** from Archipelago Launcher and reproduce the problem.
3. Enter `/diagnostics export` as soon as practical. Keep the reported ZIP; a
   partial archive explicitly lists any unavailable artifacts.
4. Close the client, game, and compiler normally. If one has crashed, leave the
   other files untouched; process exit information and flushed output are
   still useful.
5. Send the ZIP, or all three same-session files if export failed, together with
   a short description of what you expected and what happened.

The export command is exactly `/diagnostics export`. `action=bundle` and
`action=export` are not client-console commands.

## Restart and update recovery

For a changed APWorld or bridge, wait until native memory-card I/O finishes,
close the client, `gk`, and `goalc`, install through Archipelago Launcher, and
start a clean session. Never delete `.archipelago-reload-required` manually;
the activation handshake clears it only after the new source is running.

An unchanged-source client reconnect is designed to keep the game open, but
official OpenGOAL v0.3.5 failed the Milestone 7.2 clean and unclean reconnect
rows after its original compiler connection was lost. If the compiler/client
closes while the game remains open, preserve/export the session evidence and
restart all three processes together. Repeated `/repl connect` attempts cannot
repair the one-connection game process observed in that version.

Manual `(ml)` is developer/recovery-only. Never live-load the bridge while a
native save/load is active. Do not lock, replace, or externally edit native
bank files while the game is running: the v0.3.5 native card scan throws on an
exclusively locked bank and can terminate `gk` before it emits a graceful save
failure. After such a crash, release the lock, retain the banks and support
bundle, then perform a clean restart and normal save/load recovery.

Jak 3 diagnostics use 8 MiB segments with three backups, ten sessions,
fourteen-day retention, and a 256 MiB managed cap. The current session is never
pruned, and process-aware markers protect every artifact of another live
client. Local markers require both a live PID and a renewed 30-minute lease;
remote markers require the renewed lease. Startup,
fallback, and export retention reserve every live session's remaining rotation
budget under the same process-wide capacity lock, beginning with publication of
its marker lease. A new session uses console-only
diagnostics, or an export fails cleanly,
when those reservations cannot fit; move an earlier same-session ZIP elsewhere
before retrying. If the ZIP
reports a partial export because a human log was truncated, it contains the
newest sanitized evidence and declares the affected file in `manifest.json` and
the README. Copy the export elsewhere if the report will be delayed.

## Privacy

Structured events and bundle context providers enforce explicit field schemas,
hash UUID/seed/slot/save/nonces used for correlation, and redact credential URLs,
quoted or structured password/token/secret/API-key assignments (including
separator-free mixed-case keys such as `accessToken`), and complete
Authorization/Digest values, including console-only fallback output.
The export re-sanitizes all included artifacts and never considers native saves,
AP state sidecars, authorization records, packets/forms, or memory dumps. Human
logs may still contain paths or third-party text, so private attachments remain
preferable.

## Quick interpretation

- Installation/startup failures: begin at `DIAGNOSTIC` and `OpenGOAL startup`
  in the client file.
- Compiler failures: search the OpenGOAL file for `error`, `Compiler`, the
  bridge source name, and the last `[CLIENT]` completion marker.
- Version mismatch: compare the reported protocol and game-integration values
  with the client's expected values in `/diagnostics`.
- Lost heartbeat: compare the last `PING` sequence with the exported game
  heartbeat and `PONG` result. A duplicate sequence should not advance either
  heartbeat.
- Stale or partial state: look for a missing frame marker, revision mismatch,
  or reconnect message. The client rejects incomplete snapshot writes.
- Persistent state failure: distinguish the temporary bridge path from the
  persistent root. Do not edit a rejected sidecar. Preserve the primary,
  `.bak`, and every `.corrupt.*` or `.interrupted.*` file with the logs.
- Crashes or hangs: use the final OpenGOAL lines, recorded process exit code,
  and any traceback in the client log.
- `native-save-tag-missing`: the native save remains loadable but AP state is
  deliberately read-only; no sidecar should be created.
- Copied-slot rejection: return to the original native slot. Do not edit the
  tag or sidecar to force a copied UUID into a different slot.

This milestone intentionally adds no item delivery, location checks, mission
changes, rewards, or victory reporting. Their
absence in the logs is expected.

OpenGOAL also maintains its own rotating native logs beneath the active
project. The matched pair should be requested first; native logs are only a
fallback when the pair explicitly says an old process was already running.
