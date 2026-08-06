from BaseClasses import Entrance, Region

from .data import ACTIVITIES, MISSIONS
from .locations import Jak3Location


def create_regions(world: "Jak3World", resolved_options: "ResolvedJak3Options") -> None:
    player = world.player
    multiworld = world.multiworld

    menu = Region("Menu", player, multiworld)
    mission_select = Region("Mission Select", player, multiworld)
    menu.connect(mission_select, "Start Jak 3")
    multiworld.regions.extend((menu, mission_select))

    for mission in MISSIONS:
        region = Region(f"Mission - {mission.name}", player, multiworld)
        location = Jak3Location(
            player,
            mission.location_name,
            world.location_name_to_id[mission.location_name],
            region,
        )
        region.locations.append(location)
        entrance = Entrance(player, f"Unlock Mission - {mission.name}", mission_select)
        mission_select.exits.append(entrance)
        entrance.connect(region)
        world.mission_entrances[mission.task_id] = entrance
        multiworld.regions.append(region)

    for activity in ACTIVITIES:
        region = Region(f"Challenge - {activity.name}", player, multiworld)
        location = Jak3Location(
            player,
            activity.location_name,
            world.location_name_to_id[activity.location_name],
            region,
        )
        region.locations.append(location)
        entrance = Entrance(player, f"Unlock Challenge - {activity.name}", mission_select)
        mission_select.exits.append(entrance)
        entrance.connect(region)
        world.activity_entrances[activity.task_id] = entrance
        multiworld.regions.append(region)

    goal = Region("Goal", player, multiworld)
    victory = Jak3Location(player, "Victory", None, goal)
    victory.place_locked_item(world.create_event("Victory"))
    goal.locations.append(victory)
    goal_entrance = Entrance(player, "Meet Completion Condition", mission_select)
    mission_select.exits.append(goal_entrance)
    goal_entrance.connect(goal)
    world.goal_entrance = goal_entrance
    multiworld.regions.append(goal)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Jak3World
    from .option_resolution import ResolvedJak3Options
