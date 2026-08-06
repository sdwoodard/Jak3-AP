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
