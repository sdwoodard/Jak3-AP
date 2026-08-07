from .registry import VICTORY_EVENT


def set_rules(world: "Jak3World", resolved_options: "ResolvedJak3Options") -> None:
    """Install only the event completion condition for the permissive scaffold.

    Final Standard mission, reward, challenge, orb, and finale reachability is
    deliberately deferred to Milestone 12.
    """

    player = world.player
    world.multiworld.completion_condition[player] = lambda state: state.has(
        VICTORY_EVENT.item_name, player
    )


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Jak3World
    from .option_resolution import ResolvedJak3Options
