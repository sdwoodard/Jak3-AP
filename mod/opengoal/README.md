# OpenGOAL bridge overlay

This directory mirrors the source path installed beneath an active OpenGOAL
Jak 3 `data` project. `archipelago.gc` is the in-game half of the protocol. It
currently provides the phase-1 task bridge, indexed item replay, slot/seed
binding, normal title/new-game transitions, and queued bottom-of-screen item
messages.

`tools/build_apworld.ps1` embeds this source in `jak3.apworld`. The installed
Jak 3 Client copies that exact payload to
`goal_src\jak3\pc\features\archipelago.gc`, registers `archipelago.o`
immediately after `task-control.o`, and repairs either file on later launches.

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
bridge, and opens the normal title sequence. The display process also expires
after 15 minutes if the compiler connection is lost before normal cleanup.
Both OpenGOAL processes write to the session's `Jak3OpenGOAL_*.txt` diagnostic
file. Stable `[JAK3-AP]` messages identify bridge bindings, item receipts,
mission dispatch/completion, resyncs, notifications, and title/new-game
transitions without polling spam.
