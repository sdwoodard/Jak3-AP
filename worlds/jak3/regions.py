from BaseClasses import LocationProgressType, Region

from .locations import Jak3Location
from .registry import (
    FIRST_RELEASE_LOCATIONS,
    MISSION_COMPLETION_EVENTS,
    VICTORY_EVENT,
)


PERMISSIVE_SCAFFOLD_REGION_NAME = "Milestone 5 Permissive Static Pool"


def create_regions(world: "Jak3World", resolved_options: "ResolvedJak3Options") -> None:
    player = world.player
    multiworld = world.multiworld

    menu = Region("Menu", player, multiworld)
    scaffold = Region(PERMISSIVE_SCAFFOLD_REGION_NAME, player, multiworld)
    menu.connect(scaffold, "Enter Milestone 5 Static Pool")
    multiworld.regions.extend((menu, scaffold))

    # Milestone 5 activates the exact network pool but intentionally has no
    # Standard reachability rules. Milestone 12 replaces this always-open,
    # non-playable scaffold with the audited mission graph.
    for record in FIRST_RELEASE_LOCATIONS:
        location = Jak3Location(
            player,
            record.name,
            record.code,
            scaffold,
        )
        if record.default_excluded:
            location.progress_type = LocationProgressType.EXCLUDED
        scaffold.locations.append(location)

    for event in MISSION_COMPLETION_EVENTS:
        location = Jak3Location(player, event.location_name, None, scaffold)
        location.show_in_spoiler = False
        location.place_locked_item(world.create_event(event.item_name))
        scaffold.locations.append(location)

    victory = Jak3Location(player, VICTORY_EVENT.location_name, None, scaffold)
    victory.place_locked_item(world.create_event(VICTORY_EVENT.item_name))
    scaffold.locations.append(victory)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Jak3World
    from .option_resolution import ResolvedJak3Options
