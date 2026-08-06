"""Stable design-facing option schema for the initial Jak 3 profile."""

from dataclasses import dataclass
from functools import cached_property

from Options import (Choice, DeathLink, DefaultOnToggle, ItemsAccessibility,
                     OptionCounter, PerGameCommonOptions, ProgressionBalancing,
                     Range, StartInventoryPool, Toggle)


__all__ = [
    "Jak3ProgressionBalancing", "Jak3Accessibility",
    "Goal", "MissionOrder", "LogicDifficulty", "MissionEquipment", "StoryItemMode",
    "FinaleRelicRequirement", "EarlyRouteItem", "EarlyRangedGun",
    "MissionCompletionChecks", "VanillaRewardChecks", "MissionMilestoneChecks",
    "SideMissionSanity", "SanityCosts", "ChallengeProgression", "MedalSanity",
    "PrecursorOrbSanity", "PrecursorOrbBundleSize", "PrecursorOrbProgressionCap",
    "SkullGemSanity", "SkullGemBundleSize", "SecretPurchaseSanity",
    "AllowExperimentalChecks", "GunShuffle", "GunLogic", "AmmoUpgradeShuffle",
    "ArmorShuffle", "JetboardShuffle", "JetboardUpgradeShuffle",
    "InvisibilityStatuesShuffle", "LightPowerShuffle", "DarkPowerShuffle",
    "VehicleShuffle", "EcoCrystalShuffle", "SecretUpgradeShuffle",
    "FILLER_DEFAULTS", "FillerItemWeights", "TrapPercentage", "TrapDuration",
    "TRAP_DEFAULTS", "TrapWeights", "DeathLink", "Jak3Options",
    "INITIAL_PROFILE_FIELDS", "validate_initial_profile",
]


class Jak3ProgressionBalancing(ProgressionBalancing):
    """Jak 3's design default, distinct from Archipelago's global default."""

    default = 65


class Jak3Accessibility(ItemsAccessibility):
    """Expose full/items/minimal distinctly while defaulting to full."""

    default = ItemsAccessibility.option_full


class Goal(Choice):
    display_name = "Goal"
    option_complete_city_win = 0
    option_defeat_final_boss = 1
    option_all_story_tasks = 2
    option_relic_hunt = 3
    default = 0


class MissionOrder(Choice):
    display_name = "Mission Order"
    option_vanilla = 0
    option_tiered_open_board = 1
    option_chapter_shuffle = 2
    option_full_shuffle_experimental = 3
    default = 1


class LogicDifficulty(Choice):
    display_name = "Logic Difficulty"
    option_casual = 0
    option_standard = 1
    option_expert = 2
    default = 1


class MissionEquipment(Choice):
    display_name = "Mission Equipment"
    option_bootstrap = 0
    option_require_unlocks = 1
    option_vanilla = 2
    default = 0


class StoryItemMode(Choice):
    display_name = "Story Item Mode"
    option_simplified_authorizations = 0
    option_canonical = 1
    option_vanilla = 2
    default = 0


class FinaleRelicRequirement(Range):
    display_name = "Finale Relic Requirement"
    range_start = 0
    range_end = 7
    default = 5


class EarlyRouteItem(Choice):
    display_name = "Early Route Item"
    option_guaranteed_local = 0
    option_sphere_zero = 1
    option_none = 2
    default = 0


class EarlyRangedGun(EarlyRouteItem):
    display_name = "Early Ranged Gun"


class MissionCompletionChecks(Choice):
    display_name = "Mission Completion Checks"
    option_off = 0
    option_story = 1
    option_include_prologue = 2
    default = 1


class VanillaRewardChecks(Choice):
    display_name = "Vanilla Reward Checks"
    option_off = 0
    option_major = 1
    option_all_stable = 2
    default = 1


class MissionMilestoneChecks(Choice):
    display_name = "Mission Milestone Checks"
    option_off = 0
    option_major = 1
    option_all_audited = 2
    default = 0


class SideMissionSanity(Choice):
    display_name = "Side Mission Sanity"
    option_off = 0
    option_selected = 1
    option_orb_hunts = 2
    option_all = 3
    default = 1


class SanityCosts(Choice):
    display_name = "Sanity Costs"
    option_free = 0
    option_vouchers = 1
    option_vanilla = 2
    default = 0


class ChallengeProgression(Choice):
    display_name = "Challenge Progression"
    option_safe = 0
    option_all = 1
    option_none = 2
    default = 0


class MedalSanity(Choice):
    display_name = "Medal Sanity"
    option_off = 0
    option_gold_only = 1
    option_silver_and_gold = 2
    option_all_explicit = 3
    default = 0


class PrecursorOrbSanity(Choice):
    display_name = "Precursor Orb Sanity"
    option_off = 0
    option_global_bundles = 1
    option_global_milestones = 2
    option_regional_bundles = 3
    option_individual_static = 4
    default = 1


class PrecursorOrbBundleSize(Range):
    display_name = "Precursor Orb Bundle Size"
    range_start = 10
    range_end = 100
    default = 25


class PrecursorOrbProgressionCap(Range):
    display_name = "Precursor Orb Progression Cap"
    range_start = 0
    range_end = 600
    default = 300


class SkullGemSanity(Choice):
    display_name = "Skull Gem Sanity"
    option_off = 0
    option_cumulative_milestones = 1
    option_secret_purchases = 2
    option_both = 3
    option_individual_static = 4
    default = 0


class SkullGemBundleSize(Range):
    display_name = "Skull Gem Bundle Size"
    range_start = 5
    range_end = 100
    default = 25


class SecretPurchaseSanity(Choice):
    display_name = "Secret Purchase Sanity"
    option_off = 0
    option_milestones_free = 1
    option_individual_free = 2
    option_individual_vanilla_costs = 3
    default = 0


class AllowExperimentalChecks(Toggle):
    display_name = "Allow Experimental Checks"
    default = 0


class GunShuffle(Choice):
    display_name = "Gun Shuffle"
    option_vanilla = 0
    option_base_and_upgrades = 1
    option_individual_mods = 2
    default = 2


class GunLogic(Choice):
    display_name = "Gun Logic"
    option_none = 0
    option_reliable_ranged = 1
    option_color_specific_experimental = 2
    default = 1


class AmmoUpgradeShuffle(DefaultOnToggle):
    display_name = "Ammo Upgrade Shuffle"


class ArmorShuffle(Choice):
    display_name = "Armor Shuffle"
    option_vanilla = 0
    option_useful = 1
    option_progression_experimental = 2
    default = 1


class JetboardShuffle(DefaultOnToggle):
    display_name = "Jetboard Shuffle"


class JetboardUpgradeShuffle(DefaultOnToggle):
    display_name = "Jetboard Upgrade Shuffle"


class InvisibilityStatuesShuffle(DefaultOnToggle):
    display_name = "Invisibility Statues Shuffle"


class LightPowerShuffle(Choice):
    display_name = "Light Power Shuffle"
    option_vanilla = 0
    option_key_powers = 1
    option_all = 2
    default = 2


class DarkPowerShuffle(LightPowerShuffle):
    display_name = "Dark Power Shuffle"


class VehicleShuffle(Choice):
    display_name = "Vehicle Shuffle"
    option_vanilla = 0
    option_progressive_licenses = 1
    option_individual_experimental = 2
    default = 1


class EcoCrystalShuffle(Choice):
    display_name = "Eco Crystal Shuffle"
    option_off = 0
    option_useful_tokens = 1
    option_relic_tokens = 2
    default = 0


class SecretUpgradeShuffle(Choice):
    display_name = "Secret Upgrade Shuffle"
    option_off = 0
    option_useful = 1
    default = 0


FILLER_DEFAULTS = {
    "Precursor Orb Pack (5)": 20, "Precursor Orb Pack (10)": 10,
    "Precursor Orb Pack (25)": 4, "Skull Gem Pack (1)": 12,
    "Skull Gem Pack (3)": 6, "Skull Gem Pack (5)": 2,
    "Red Ammo Refill": 8, "Yellow Ammo Refill": 8, "Blue Ammo Refill": 8,
    "Dark Ammo Refill": 4, "Health Refill": 10, "Light Eco Refill": 6,
    "Dark Eco Refill": 6, "Vehicle Repair": 6, "Vehicle Turbo Refill": 4,
}


class WeightedCounter(OptionCounter):
    min = 0
    max = 100

    @cached_property
    def weights_pair(self) -> tuple[list[str], list[int]]:
        return list(self.value), list(self.value.values())


class FillerItemWeights(WeightedCounter):
    display_name = "Filler Item Weights"
    default = FILLER_DEFAULTS
    valid_keys = sorted(FILLER_DEFAULTS)


class TrapPercentage(Range):
    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 0


class TrapDuration(Range):
    display_name = "Trap Duration"
    range_start = 5
    range_end = 120
    default = 20


TRAP_DEFAULTS = {
    "Sandstorm Trap": 3, "Low Gravity Trap": 2, "Gun Jam Trap": 1,
    "Eco Leak Trap": 1, "Vehicle Wobble Trap": 1,
}


class TrapWeights(WeightedCounter):
    display_name = "Trap Weights"
    default = TRAP_DEFAULTS
    valid_keys = sorted(TRAP_DEFAULTS)


@dataclass
class Jak3Options(PerGameCommonOptions):
    progression_balancing: Jak3ProgressionBalancing
    accessibility: Jak3Accessibility
    goal: Goal
    mission_order: MissionOrder
    logic_difficulty: LogicDifficulty
    mission_equipment: MissionEquipment
    story_item_mode: StoryItemMode
    finale_relic_requirement: FinaleRelicRequirement
    early_route_item: EarlyRouteItem
    early_ranged_gun: EarlyRangedGun
    mission_completion_checks: MissionCompletionChecks
    vanilla_reward_checks: VanillaRewardChecks
    mission_milestone_checks: MissionMilestoneChecks
    side_mission_sanity: SideMissionSanity
    sanity_costs: SanityCosts
    challenge_progression: ChallengeProgression
    medal_sanity: MedalSanity
    precursor_orb_sanity: PrecursorOrbSanity
    precursor_orb_bundle_size: PrecursorOrbBundleSize
    precursor_orb_progression_cap: PrecursorOrbProgressionCap
    skull_gem_sanity: SkullGemSanity
    skull_gem_bundle_size: SkullGemBundleSize
    secret_purchase_sanity: SecretPurchaseSanity
    allow_experimental_checks: AllowExperimentalChecks
    gun_shuffle: GunShuffle
    gun_logic: GunLogic
    ammo_upgrade_shuffle: AmmoUpgradeShuffle
    armor_shuffle: ArmorShuffle
    jetboard_shuffle: JetboardShuffle
    jetboard_upgrade_shuffle: JetboardUpgradeShuffle
    invisibility_statues_shuffle: InvisibilityStatuesShuffle
    light_power_shuffle: LightPowerShuffle
    dark_power_shuffle: DarkPowerShuffle
    vehicle_shuffle: VehicleShuffle
    eco_crystal_shuffle: EcoCrystalShuffle
    secret_upgrade_shuffle: SecretUpgradeShuffle
    filler_item_weights: FillerItemWeights
    trap_percentage: TrapPercentage
    trap_duration: TrapDuration
    trap_weights: TrapWeights
    death_link: DeathLink
    start_inventory_from_pool: StartInventoryPool


# Compatibility names retained for callers of the earlier schema module. The
# actual profile definition and validation live exclusively in option_resolution.
INITIAL_PROFILE_FIELDS = tuple(
    name for name in Jak3Options.__annotations__
    if name != "start_inventory_from_pool"
)


def validate_initial_profile(options: Jak3Options) -> None:
    from .option_resolution import resolve_options

    resolve_options(options)
