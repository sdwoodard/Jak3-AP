"""Compatibility versions shared by the APWorld, client, and GOAL bridge.

Version changes are deliberate compatibility decisions.  Table versions cover
the first-release registries in :mod:`worlds.jak3.registry`; the legacy
protocol-1 scaffold remains frozen separately at table version 1.
"""

DESIGN_VERSION = "0.3"

# Protocol 3 adds the Milestone 7 runtime snapshot and duplicate-safe harmless
# command transport.  Gameplay delivery and location reporting remain absent.
PROTOCOL_VERSION = 3
GAME_INTEGRATION_VERSION = 2
# This implementation revision is compatibility metadata for the ordered
# runtime modules. It adds Milestone 10's connected gameplay slice without
# changing Protocol 3 or any table, slot-data, integration, or state schema.
BRIDGE_RUNTIME_VERSION = 5

SLOT_DATA_VERSION = 2
STATE_SCHEMA_VERSION = 1
ITEM_TABLE_VERSION = 2
LOCATION_TABLE_VERSION = 2
MISSION_TABLE_VERSION = 1
MISSION_PROFILE_VERSION = 1
