from dataclasses import dataclass
from functools import cached_property

from Options import Choice, OptionCounter, PerGameCommonOptions, Range, StartInventoryPool

from .data import TRAPS


class CompletionCondition(Choice):
    """Choose whether victory requires one named mission or a number of completed missions."""

    display_name = "Jak 3 Completion Condition"
    option_complete_specific_mission = 0
    option_complete_number_of_missions = 1
    default = 1


class SpecificMissionForCompletion(Choice):
    """The goal mission when the completion condition is Complete Specific Mission."""

    display_name = "Specific Mission for Completion"
    option_defeat_precursor_robot = 34
    option_defeat_war_factory_boss = 60
    option_defend_spargus = 62
    option_destroy_dark_maker_tower = 66
    option_destroy_dark_ship = 70
    option_defeat_cyber_errol = 71
    default = 71


class NumberOfMissionsForCompletion(Range):
    """Number of the 66 main-game tasks that must be completed for victory."""

    display_name = "Number of Missions for Completion"
    range_start = 5
    range_end = 66
    default = 66


class PercentFillerReplacedWithTraps(Range):
    """Percentage of filler slots replaced with weighted traps."""

    display_name = "Percent Filler Replaced with Traps"
    range_start = 0
    range_end = 100
    default = 0


class TrapEffectDuration(Range):
    """Duration of timed trap effects, in seconds."""

    display_name = "Trap Effect Duration"
    range_start = 5
    range_end = 60
    default = 30


class TrapWeights(OptionCounter):
    """Relative weights for traps. All zero disables trap replacement."""

    display_name = "Trap Weights"
    min = 0
    default = {trap: 1 for trap in TRAPS}
    valid_keys = sorted(TRAPS)

    @cached_property
    def weights_pair(self) -> tuple[list[str], list[int]]:
        return list(self.value), list(self.value.values())


@dataclass
class Jak3Options(PerGameCommonOptions):
    jak_3_completion_condition: CompletionCondition
    specific_mission_for_completion: SpecificMissionForCompletion
    number_of_missions_for_completion: NumberOfMissionsForCompletion
    percent_filler_replaced_with_traps: PercentFillerReplacedWithTraps
    trap_effect_duration: TrapEffectDuration
    trap_weights: TrapWeights
    start_inventory_from_pool: StartInventoryPool
