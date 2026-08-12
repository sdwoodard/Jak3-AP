# OpenGOAL bridge overlay

This directory mirrors the source path installed beneath an active OpenGOAL
Jak 3 `data` project. `bridge-modules.json` version 1 declares the startup,
Protocol 3 control, diagnostics, permanent-item, and finite-location modules in
their only supported order. `archipelago.gc` retains shared version/session,
native-save observation, runtime safety, heartbeat, validation, and dispatch
decisions. The sibling modules own their gameplay domains.

`tools/build_apworld.ps1` embeds the manifest and every declared source in
`jak3.apworld`. The installed client stages and validates the complete set,
registers `archipelago.o`, `archipelago-diagnostics.o`, `archipelago-items.o`,
then `archipelago-locations.o` immediately after `task-control.o`, and uses the
ordered source-set hash for repair and reload activation. Both installation
paths serialize the entire staged replacement with the same atomic directory
lock.

For development without rebuilding/reinstalling the APWorld, apply the working
tree version manually with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install_opengoal_bridge.ps1 `
  -OpenGoalRepository D:\OpenGOAL\active\jak3\data
```

Jak 3 Client owns normal process startup and compilation. It starts the game
with `-debug`, starts `goalc`, attaches through nREPL, compiles OpenGOAL's
version-matched kernel/font type prefix, and live-loads the small
`archipelago-startup.gc` display process. It then runs `(mi)`, removes the
flashing in-game compilation warning at the completion barrier, loads the main
bridge modules in manifest order, and verifies a snapshot-backed hello and
ping. The display process
also expires after 15 minutes if the compiler connection is lost before normal
cleanup.
Python captures both OpenGOAL processes through bounded sanitized pipes into
`Jak3OpenGOAL_*.txt`; it creates no raw spool, and GOAL never opens a support
log or archive. The diagnostic ring has 64 records, reserves its source/channel
readiness records until acknowledgement, drops the oldest ordinary record on
overflow, publishes a dropped count, and supports idempotent Python
acknowledgement qualified by the producer activation generation. A delayed
acknowledgement from an old loaded object cannot drain the new ring after a
reload. `archipelago-locations.gc` re-publishes its two descriptor-qualified
observations through that ring until Python durably commits them; the ring ack
is only the GOAL-to-Python handoff and is not an Archipelago packet ack.
Python tracks the producer activation and next sequence across reconnects,
resets its drain high-water mark after a diagnostic reload/restart, and latches
persistent optional-channel/drain/acknowledgement gaps until recovery. Ring
acknowledgements are queued on a short, failure-isolated background path and
cannot extend a Protocol 3 command or handshake deadline.
