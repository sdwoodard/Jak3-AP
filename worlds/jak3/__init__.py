from __future__ import annotations

from BaseClasses import ItemClassification, Tutorial
from Options import OptionGroup
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import (
    Component,
    Type,
    components,
    icon_paths,
    launch_subprocess,
)

from . import options
from .game_id import GAME_NAME
from .registry import (
    FILLER_ITEMS,
    FIRST_RELEASE_ITEM_NAME_TO_ID,
    FIRST_RELEASE_ITEMS,
    FIRST_RELEASE_LOCATION_NAME_TO_ID,
    FIRST_RELEASE_LOCATIONS,
    MAJOR_REWARD_LOCATIONS,
    ORB_THRESHOLD_LOCATIONS,
    PROGRESSION_ITEMS,
    SELECTED_SIDE_LOCATIONS,
    STORY_COMPLETION_LOCATIONS,
    TRAP_ITEMS,
    USEFUL_ITEMS,
)
from .items import Jak3Item
from .option_resolution import ResolvedJak3Options
from .regions import create_regions
from .rules import set_rules
from .slot_data import build_slot_data


_ITEM_RECORD_BY_NAME = {record.name: record for record in FIRST_RELEASE_ITEMS}
_CLASSIFICATION_BY_REGISTRY_VALUE = {
    "progression": ItemClassification.progression,
    "progression_skip_balancing": ItemClassification.progression_skip_balancing,
    "useful": ItemClassification.useful,
    "filler": ItemClassification.filler,
    "trap": ItemClassification.trap,
}


def launch_client() -> None:
    from . import client

    launch_subprocess(client.launch, name="Jak3Client")


components.append(
    Component(
        "Jak 3 Client",
        func=launch_client,
        component_type=Type.CLIENT,
        icon="jak3-logo",
        game_name=GAME_NAME,
        supports_uri=True,
        description="Connect Jak 3 for OpenGOAL to an Archipelago multiworld.",
    )
)
icon_paths["jak3-logo"] = f"ap:{__name__}/icons/jak3-logo.png"


class Jak3WebWorld(WebWorld):
    theme = "ocean"
    setup_en = Tutorial(
        "Multiworld Setup Guide",
        "Install the Jak 3 APWorld and connect it to the OpenGOAL mod.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Jak3-AP Contributors"],
    )
    tutorials = [setup_en]
    option_groups = [
        OptionGroup(
            "Progression",
            [
                options.Goal,
                options.MissionOrder,
                options.LogicDifficulty,
                options.MissionEquipment,
                options.StoryItemMode,
                options.FinaleRelicRequirement,
                options.EarlyRouteItem,
                options.EarlyRangedGun,
            ],
        ),
        OptionGroup(
            "Checks",
            [
                options.MissionCompletionChecks,
                options.VanillaRewardChecks,
                options.MissionMilestoneChecks,
                options.SideMissionSanity,
                options.SanityCosts,
                options.ChallengeProgression,
                options.MedalSanity,
                options.PrecursorOrbSanity,
                options.PrecursorOrbBundleSize,
                options.PrecursorOrbProgressionCap,
                options.SkullGemSanity,
                options.SkullGemBundleSize,
                options.SecretPurchaseSanity,
                options.AllowExperimentalChecks,
            ],
        ),
        OptionGroup(
            "Items",
            [
                options.GunShuffle,
                options.GunLogic,
                options.AmmoUpgradeShuffle,
                options.ArmorShuffle,
                options.JetboardShuffle,
                options.JetboardUpgradeShuffle,
                options.InvisibilityStatuesShuffle,
                options.LightPowerShuffle,
                options.DarkPowerShuffle,
                options.VehicleShuffle,
                options.EcoCrystalShuffle,
                options.SecretUpgradeShuffle,
                options.FillerItemWeights,
            ],
        ),
        OptionGroup(
            "Traps",
            [
                options.TrapPercentage,
                options.TrapDuration,
                options.TrapWeights,
                options.DeathLink,
            ],
        ),
    ]


class Jak3World(World):
    """Default-only Jak 3 static pool with permissive pre-logic scaffolding."""

    game = GAME_NAME
    required_client_version = (0, 6, 7)
    options_dataclass = options.Jak3Options
    options: options.Jak3Options
    web = Jak3WebWorld()

    item_name_to_id = FIRST_RELEASE_ITEM_NAME_TO_ID
    location_name_to_id = FIRST_RELEASE_LOCATION_NAME_TO_ID
    item_name_groups = {
        "Progression": {record.name for record in PROGRESSION_ITEMS},
        "Useful": {record.name for record in USEFUL_ITEMS},
        "Filler": {record.name for record in FILLER_ITEMS},
        "Traps": {record.name for record in TRAP_ITEMS},
        "Route Authorizations": {
            record.name
            for record in PROGRESSION_ITEMS
            if record.family == "route_authorization"
        },
        "Finale Relics": {
            record.name
            for record in PROGRESSION_ITEMS
            if record.family == "finale_relic"
        },
    }
    location_name_groups = {
        "Story Completions": {record.name for record in STORY_COMPLETION_LOCATIONS},
        "Major Rewards": {record.name for record in MAJOR_REWARD_LOCATIONS},
        "Selected Side Challenges": {record.name for record in SELECTED_SIDE_LOCATIONS},
        "Precursor Orb Thresholds": {record.name for record in ORB_THRESHOLD_LOCATIONS},
    }

    resolved_options: ResolvedJak3Options

    def generate_early(self) -> None:
        self.resolved_options = options.resolve_options(self.options)

    def create_regions(self) -> None:
        create_regions(self, self.resolved_options)

    def create_item(self, name: str) -> Jak3Item:
        record = _ITEM_RECORD_BY_NAME[name]
        classification = _CLASSIFICATION_BY_REGISTRY_VALUE[record.classification]
        return Jak3Item(name, classification, record.code, self.player)

    def create_event(self, name: str) -> Jak3Item:
        return Jak3Item(name, ItemClassification.progression, None, self.player)

    def create_items(self) -> None:
        pool = [
            self.create_item(record.name)
            for record in PROGRESSION_ITEMS + USEFUL_ITEMS
            for _ in range(record.pool_count)
        ]
        filler_count = len(FIRST_RELEASE_LOCATIONS) - len(pool)
        if filler_count != 93:
            raise RuntimeError(
                "The frozen Jak 3 default must have exactly 93 filler slots; "
                f"computed {filler_count}."
            )
        pool.extend(
            self.create_item(name) for name in self._weighted_filler_names(filler_count)
        )
        if len(pool) != len(FIRST_RELEASE_LOCATIONS):
            raise RuntimeError(
                "Jak 3 item pool does not balance its network locations."
            )
        self.multiworld.itempool += pool

    def set_rules(self) -> None:
        set_rules(self, self.resolved_options)

    def fill_slot_data(self) -> dict:
        return build_slot_data(
            self.resolved_options,
            seed_identifier=str(self.multiworld.seed_name),
        )

    def get_filler_item_name(self) -> str:
        return self._weighted_filler_names(1)[0]

    def _weighted_filler_names(self, count: int) -> list[str]:
        configured_weights = dict(self.resolved_options.filler_item_weights)
        names = [record.name for record in FILLER_ITEMS]
        weights = [configured_weights[name] for name in names]
        return self.random.choices(names, weights=weights, k=count)
