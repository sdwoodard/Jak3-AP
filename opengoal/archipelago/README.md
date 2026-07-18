# OpenGOAL bridge

`archipelago.gc` is a narrow patch loaded after Jak 3's `game-task` and `task-control` objects. It:

- records completion for native story task IDs 6–71;
- binds state to hashes of the Archipelago slot and seed so another save cannot leak checks;
- accepts idempotent mission unlocks using the Archipelago receive index;
- grants progressive guns, ammo capacity, Dark/Light powers, armor, the Jetboard, and vehicles through native feature bits;
- starts only missions whose unlock has been received; and
- exports a small state snapshot for the Python client.

Add this source file to the mod's project after `game-task.gc` and `task-control.gc`. The client expects the state snapshot in its working directory, or at the path specified by `JAK3_AP_STATE`.

The supplied source writes `jak3-ap-state.tmp`. A production mod package should use OpenGOAL's platform file rename helper to publish that closed file as `jak3-ap-state.txt`; alternatively point `JAK3_AP_STATE` at the `.tmp` file. This prevents the client from parsing a partially-written snapshot.
