# Jak 3 Multiworld Setup Guide

The Jak 3 integration is under active development and is not yet a public
playable release. These steps are for protocol and integration testing.

## Requirements

- Archipelago 0.6.7 or newer.
- A legally obtained Jak 3 image decompiled successfully by OpenGOAL.
- Jak 3 installed through OpenGOAL Launcher.

## Install

1. Build `jak3.apworld` with `tools/build_apworld.ps1` and install it through
   Archipelago Launcher's **Install APWorld** action.
2. Restart Archipelago after replacing the APWorld.
3. Generate with the supplied `config/templates/Jak3.yaml`. Change the player
   name as needed, but leave every Jak 3-specific supported default unchanged.

## Connect and launch

Start **Jak 3 Client** from Archipelago Launcher. It automatically discovers
OpenGOAL Launcher, installs or repairs the bridge bundled in the APWorld,
starts `gk` in Debug mode and the matching `goalc`, attaches to the game,
recompiles, loads the bridge, and verifies protocol 2/game integration 1. The
compile can take several minutes. A flashing message appears in the game while
this is happening; wait until it disappears and `/repl status` reports ready.

An Archipelago room connection is optional for this handshake milestone. Room
state is reported to the game as client status but is not bound to a save and
does not enable items or checks.

Useful recovery commands in Jak 3 Client are:

- `/diagnostics` — record current handshake state and show both log paths.
- `/repl status` — show transport, source, versions, session, and heartbeat.
- `/repl connect` — retry compilation and bridge attachment.

Protocol 2 does not start gameplay, bind or load a save, apply inventory,
submit locations, report victory, modify missions, or show item messages.

## Troubleshooting

Every launch creates two matching files in Archipelago's `logs` directory:
`Jak3Client_<session-id>.txt` and `Jak3OpenGOAL_<session-id>.txt`. Close old
Jak 3/client/compiler processes before reproducing an issue, run `/diagnostics`
afterward, and provide both files with the same session ID. The client log
contains AP connection and handshake state; the OpenGOAL log combines
the verbose game and compiler output with in-game `[JAK3-AP]` events. The logs
do not intentionally include the room password, but may contain slot/player
names, room seed, server address, and local paths.

- If automatic discovery fails, set `JAK3_OPENGOAL_BIN` to the versioned
  OpenGOAL binary directory and `JAK3_OPENGOAL_PROJECT` to the active Jak 3
  `data` directory.
- If nREPL is unavailable, verify that `goalc` is running for Jak 3 and that no
  other process is using port 8181, then run `/repl connect`.
- If bridge installation fails, confirm that the active OpenGOAL project is
  writable and contains `goal_src\jak3\dgos\game.gd`, then run `/repl connect`.
- If the bridge is not ready, compare expected/reported versions and the last
  command/result in `/repl status`, then run `/repl connect`.
