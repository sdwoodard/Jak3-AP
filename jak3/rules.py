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
from .options import CompletionCondition


def set_rules(world: "Jak3World") -> None:
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

    if world.options.jak_3_completion_condition == CompletionCondition.option_complete_specific_mission:
        target = MISSION_BY_ID[world.options.specific_mission_for_completion.value]
        set_rule(
            world.goal_entrance,
            lambda state, task_id=target.task_id: _mission_beatable(state, player, task_id),
        )
    else:
        required = world.options.number_of_missions_for_completion.value
        # This is the generation-time approximation of the runtime goal.  The client
        # only reports victory after the configured number of checks are completed.
        set_rule(
            world.goal_entrance,
            lambda state: _reachable_mission_count(state, player) >= required,
        )

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
