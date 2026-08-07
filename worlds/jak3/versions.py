"""Compatibility versions shared by the APWorld, client, and GOAL bridge.

Version changes are deliberate compatibility decisions.  Table versions cover
the first-release registries in :mod:`worlds.jak3.registry`; the legacy
protocol-1 scaffold remains frozen separately at table version 1.
"""

DESIGN_VERSION = "0.3"

# Protocol 2 remains the handshake-only boundary established before gameplay
# delivery.  Milestone 4 adds data compatibility metadata, not gameplay I/O.
PROTOCOL_VERSION = 2
GAME_INTEGRATION_VERSION = 1

SLOT_DATA_VERSION = 1
STATE_SCHEMA_VERSION = 1
ITEM_TABLE_VERSION = 2
LOCATION_TABLE_VERSION = 2
MISSION_TABLE_VERSION = 1
MISSION_PROFILE_VERSION = 1
