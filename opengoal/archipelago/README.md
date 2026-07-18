# OpenGOAL bridge

`archipelago.gc` is the in-game half of the Jak 3 Archipelago client. It is
loaded after Jak 3's `task-control` object and:

- records checks for native story and activity task IDs;
- binds runtime state to the current Archipelago slot and seed;
- grants mission unlocks and progressive equipment idempotently;
- displays new-item notifications in the Jak 3 HUD; and
- starts only missions that the Python client reports as logically available.

## Install into OpenGOAL

From the `Jak3-AP` repository in PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-opengoal-bridge.ps1 -OpenGoalRepository ..\jak-project
```

The installer copies the source to
`goal_src/jak3/pc/features/archipelago.gc` and adds `archipelago.o` immediately
after `task-control.o` in `goal_src/jak3/dgos/game.gd`. It is safe to run again
after updating this repository.

Every newly opened Jak 3 `goalc` process must run `(mi)` successfully to load
the complete Jak 3 compiler environment and rebuild `GAME.CGO`. Keep that
compiler and the Debug game running, but do not manually issue `(lt)` or `(ml
...)`. The Python client's `/repl connect` sends both commands through nREPL;
that connection must own the target reply channel for synchronization.

The Python client assigns an absolute state-snapshot path during its bridge
handshake. `JAK3_AP_STATE` may override that location, but is normally not
needed.
