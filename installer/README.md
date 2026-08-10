# Installer boundary

The current end-user artifact is a self-contained `jak3.apworld`. Archipelago's
native APWorld installer registers the client and its transparent launcher
icon; the client then installs or repairs its bundled GOAL bridge on launch.
No separate installer is required for that supported path.

This directory reserves a boundary for a possible future installer that could:

- install/update `jak3.apworld` through the user's Archipelago installation;
- validate compatible Archipelago and OpenGOAL versions;
- retain a manifest for repair and clean uninstall; and
- avoid bundling copyrighted game data or OpenGOAL binaries.

The supported release operation is `tools/build_apworld.ps1`.
`tools/install_opengoal_bridge.ps1` remains a developer convenience.

## Update boundary

A changed APWorld or bridge must not be installed into a live player session.
Finish native memory-card I/O, close the Jak 3 client, `gk`, and `goalc`, then
install through Archipelago Launcher and start the game cleanly. The installer
must preserve the durable pending-reload marker until compatible control and
diagnostic activation attestations clear it; an installer or user must never
delete that marker merely because file copying completed.

Unchanged-source reconnect is a protocol-preserving operation in the intended
first-release policy. Official OpenGOAL v0.3.5 did not pass that live lifecycle
when its first compiler connection was lost, so the current operational
fallback is a clean restart of all three processes. A future installer must not
advertise in-game updating or arbitrary `(ml)` during native save/load.
