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
- room/slot binding and the complete generated `slot_data` option payload;
- every received item with index, ID, sender, source location, dispatch type,
  and game acknowledgement cursor;
- native task completions, location submissions, goal evaluation, HUD queue
  state, and uncaught background-task tracebacks; and
- an on-demand snapshot of received inventory, reachable tasks, completed
  tasks, checked locations, and the bridge state file.

The OpenGOAL log combines `gk` and `goalc` stdout/stderr in chronological file
order. It includes the verbose game boot, graphics/runtime errors, compiler
output from `(mi)` and bridge live-loading, process exit codes, and `[JAK3-AP]`
events emitted by the in-game bridge for bindings, item application, mission
dispatch, task completion, resync, notifications, and title/new-game changes.
Both commands request disabled ANSI colors, and the collector strips any
terminal-control sequences still emitted by OpenGOAL's REPL UI.

## Capturing a useful reproduction

1. Close every old Jak 3 `gk`, `goalc`, and Jak 3 Client process. Output from a
   process started before the client cannot be attached retroactively; the
   client logs a warning if it detects this condition.
2. Start **Jak 3 Client** from Archipelago Launcher and reproduce the problem.
3. Enter `/diagnostics` as soon as practical. This flushes a detailed current
   logic/protocol snapshot and prints both paths.
4. Close the client, game, and compiler normally. If one has crashed, leave the
   other files untouched; process exit information and flushed output are
   still useful.
5. Send both files whose session IDs match, together with a short description
   of what you expected and what happened.

Archipelago normally removes text logs older than seven days. Copy the pair
elsewhere before then if the report will be delayed.

## Privacy

The Jak 3 diagnostics never deliberately write the Archipelago password. The
logs do contain the slot name, room seed name, player IDs/names encountered in
item messages, local installation paths, system/runtime versions, and possibly
the server address logged by Archipelago itself. Review those details before
posting a pair publicly; private issue attachments are preferable.

## Quick interpretation

- Installation/startup failures: begin at `DIAGNOSTIC` and `OpenGOAL startup`
  in the client file.
- Compiler failures: search the OpenGOAL file for `error`, `Compiler`, the
  bridge source name, and the last `[CLIENT]` completion marker.
- Missing items: compare `ReceivedItems`, `Applying received item`, the nREPL
  acknowledgement, `[JAK3-AP] ...-applied`, and the bridge `received` cursor.
- Missing checks: compare `[JAK3-AP] task-completed`, `Game completed task`, and
  `Submitting location checks`.
- Incorrect mission access: use the `/diagnostics` snapshot's `slot_data`,
  `received_items`, `completed_tasks`, and `unlocked_tasks` fields.
- Crashes or hangs: use the final OpenGOAL lines, recorded process exit code,
  and any traceback in the client log.

OpenGOAL also maintains its own rotating native logs beneath the active
project. The matched pair should be requested first; native logs are only a
fallback when the pair explicitly says an old process was already running.
