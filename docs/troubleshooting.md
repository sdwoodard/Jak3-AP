# Troubleshooting and diagnostic logs

Every Jak 3 Client run creates a matched support pair in Archipelago's `logs`
directory. Both filenames contain the same session ID:

```text
Jak3Client_<session-id>.txt
Jak3OpenGOAL_<session-id>.txt
```

Always provide both files from the same session. The client prints their exact
paths at startup and when `/diagnostics` is entered.

## What the pair records

The client log covers the Archipelago and mod side of the session:

- APWorld, Archipelago, Python, operating-system, and executable versions;
- detected OpenGOAL paths, bridge SHA-256, registration/repair results, process
  IDs, and the exact launch commands;
- nREPL connection attempts, commands, completion barriers, and failures;
- AP connection state, room seed/slot identity when available, and the
  temporary handshake session;
- protocol and game-integration versions, connection-ready state, heartbeats,
  the last command/result, and the bridge status message; and
- an on-demand handshake snapshot plus uncaught background-task tracebacks.

The OpenGOAL log combines `gk` and `goalc` stdout/stderr in chronological file
order. It includes the verbose game boot, graphics/runtime errors, compiler
output from `(mi)` and bridge live-loading, process exit codes, and `[JAK3-AP]`
events emitted by the in-game bridge for initialization, client hello, ping,
duplicate ping, disconnect, and protocol errors.
Both commands request disabled ANSI colors, and the collector strips any
terminal-control sequences still emitted by OpenGOAL's REPL UI.

## Capturing a useful reproduction

1. Close every old Jak 3 `gk`, `goalc`, and Jak 3 Client process. Output from a
   process started before the client cannot be attached retroactively; the
   client logs a warning if it detects this condition.
2. Start **Jak 3 Client** from Archipelago Launcher and reproduce the problem.
3. Enter `/diagnostics` as soon as practical. This flushes the current
   handshake snapshot and prints both paths.
4. Close the client, game, and compiler normally. If one has crashed, leave the
   other files untouched; process exit information and flushed output are
   still useful.
5. Send both files whose session IDs match, together with a short description
   of what you expected and what happened.

Archipelago normally removes text logs older than seven days. Copy the pair
elsewhere before then if the report will be delayed.

## Privacy

The Jak 3 diagnostics never deliberately write the Archipelago password. The
logs can contain the slot name, room seed name, local installation paths,
system/runtime versions, and possibly the server address logged by Archipelago
itself. Review those details before posting a pair publicly; private issue
attachments are preferable.

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
- Crashes or hangs: use the final OpenGOAL lines, recorded process exit code,
  and any traceback in the client log.

This milestone intentionally has no item delivery, location checks, mission
changes, rewards, save binding, or victory reporting. Their absence in the
logs is expected.

OpenGOAL also maintains its own rotating native logs beneath the active
project. The matched pair should be requested first; native logs are only a
fallback when the pair explicitly says an old process was already running.
