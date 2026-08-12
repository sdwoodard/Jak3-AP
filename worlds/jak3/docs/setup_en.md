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

## Updates and restarts

Official OpenGOAL v0.3.5 does not support attaching a replacement client and
compiler to a game process whose original compiler connection was lost. For
the first release, recovery after either a clean or unclean client/compiler
loss therefore requires finishing native save/load activity and restarting the
client, `gk`, and `goalc` together. Leaving `gk` open for a warm replacement
attachment is unsupported.

Always use the full clean-restart path when installing a changed APWorld or
bridge: finish native memory-card I/O, close the client, `gk`, and `goalc`,
install through Archipelago Launcher, and start a clean game session. Never
manually delete the pending-reload marker; compatible bridge activation clears
it. Manual `(ml)` is developer/recovery-only and unsupported during memory-card
I/O.

External programs must not lock, replace, or edit OpenGOAL's native save-bank
files while the game is running. That is unsupported upstream interference;
wait for ordinary native save/load to finish and use the full-process recovery
path if a bank operation fails.

Milestone 7.2 acceptance verified this full-process path after both clean and
unclean client loss, including a new game nonce, an empty receipt ring, and
descriptor-qualified rebinding before permanent-item safety reopened.

## Connect and launch

Start **Jak 3 Client** from Archipelago Launcher. It automatically discovers
OpenGOAL Launcher, installs or repairs the bridge bundled in the APWorld,
starts `gk` in Debug mode and the matching `goalc`, attaches to the game,
recompiles, loads the bridge, and verifies protocol 3/game integration 2. The
compile can take several minutes. A flashing message appears in the game while
this is happening; wait until it disappears and `/repl status` reports ready.

An Archipelago room connection is optional for title-menu queries. On a
successful connection the client validates slot-data version 2, including the
authenticated seed identifier, team, slot, canonical slot name, versions,
hashes, options, and design contract. A fresh native save receives metadata tag
900 with a UUID. After a successful save/restore in slot 0-3, the client opens
and binds its sidecar; progressed vanilla saves and copied slots are rejected.
Identity proposals are single-use and require a recent authenticated client
heartbeat. Disconnecting or losing the client for five seconds disarms an
unused proposal, while an already published identity remains stable across a
bridge reload.
The client durably records the authenticated seed/team/slot behind each UUID
before offering it. If the client crashes after the native tag is saved, that
UUID can still first-bind only after reconnecting to the same AP slot; changing
rooms or slots is refused read-only.

Useful recovery commands in Jak 3 Client are:

- `/diagnostics` — record current handshake state and show all diagnostic paths.
- `/diagnostics export` — create a local sanitized support ZIP without blocking
  the game heartbeat; the client reports whether it is complete or partial.
- `/repl status` — show transport, source, versions, session, and heartbeat.
- `/repl connect` — retry compilation and bridge attachment.

Protocol 3 does not start missions, report victory, suppress rewards, or show
item messages. The current runtime applies only the Milestone 8 Jetboard,
Blaster stage-1, and Armor stage-1 targets, and submits only task 10 plus the
nREPL-only task-11 debug check through the Milestone 9 durable outbox. Other
inventory, locations, and additive effects remain disabled.

## AP state backups and save copies

Schema-1 sidecars live under the platform user-data directory at
`Archipelago/Jak3/state-v1`; `JAK3_AP_STATE_DIR` is an explicit portable/test
override. Back up the native OpenGOAL save and this directory together while
the Jak 3 client is closed. See [persistence_en.md](persistence_en.md) for the
fresh-save, restore, copy, quarantine, and concurrent-writer policy.

## Troubleshooting

Every launch creates two matching human-readable logs and one versioned event
timeline in Archipelago's `logs` directory: `Jak3Client_<session-id>.txt`,
`Jak3OpenGOAL_<session-id>.txt`, and `Jak3Events_<session-id>.jsonl`. Close old
Jak 3/client/compiler processes before reproducing an issue, run
`/diagnostics export` afterward, and provide the resulting `Jak3Support_*.zip`.
The archive validates and sanitizes the timeline, both logs, runtime and
persistence summaries, recent harmless-command results, capture gaps, and
checksums. It never includes a native save or AP sidecar and is never uploaded
automatically. A `partial` export is still useful; its README lists what was
unavailable.

- If automatic discovery fails, set `JAK3_OPENGOAL_BIN` to the versioned
  OpenGOAL binary directory and `JAK3_OPENGOAL_PROJECT` to the active Jak 3
  `data` directory.
- If nREPL is unavailable, verify that `goalc` is running for Jak 3 and that no
  other process is using port 8181, then run `/repl connect`.
- If bridge installation fails, confirm that the active OpenGOAL project is
  writable and contains `goal_src\jak3\dgos\game.gd`, then run `/repl connect`.
- If the bridge is not ready, compare expected/reported versions and the last
  command/result in `/repl status`, then run `/repl connect`.
