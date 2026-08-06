from BaseClasses import CollectionState
from worlds.generic.Rules import set_rule

from .data import (
    ACTIVITIES,
    ACTIVITY_REQUIREMENTS,
    MISSION_BY_ID,
    MISSION_REQUIREMENTS,
    MISSIONS,
    STARTING_MISSION_ID,
)


def set_rules(world: "Jak3World", resolved_options: "ResolvedJak3Options") -> None:
    player = world.player

    for mission in MISSIONS:
        if mission.task_id == STARTING_MISSION_ID:
            continue
        set_rule(
            world.mission_entrances[mission.task_id],
            lambda state, mission=mission: _mission_beatable(state, player, mission.task_id),
        )

    for activity in ACTIVITIES:
        set_rule(
            world.activity_entrances[activity.task_id],
            lambda state, activity=activity: (
                state.has_group_unique("Mission Unlocks", player, activity.unlock_count)
                and _has_requirements(state, player, ACTIVITY_REQUIREMENTS.get(activity.task_id, ()))
            ),
        )

    # The initial option validator currently permits only complete_city_win.
    # The protocol vertical slice has task 71 as its last addressable mission;
    # task 72 becomes the actual locked goal in the design-default world pass.
    set_rule(world.goal_entrance, lambda state: _mission_beatable(state, player, 71))

    world.multiworld.completion_condition[player] = lambda state: state.has("Victory", player)


def _has_requirements(
    state: CollectionState, player: int, requirements: tuple[tuple[str, int], ...]
) -> bool:
    return all(state.has(item, player, count) for item, count in requirements)


def _mission_beatable(state: CollectionState, player: int, task_id: int) -> bool:
    mission = MISSION_BY_ID[task_id]
    unlocked = task_id == STARTING_MISSION_ID or state.has(mission.item_name, player)
    return unlocked and _has_requirements(state, player, MISSION_REQUIREMENTS.get(task_id, ()))


def _reachable_mission_count(state: CollectionState, player: int) -> int:
    return sum(_mission_beatable(state, player, mission.task_id) for mission in MISSIONS)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Jak3World
    from .option_resolution import ResolvedJak3Options
