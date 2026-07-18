from __future__ import annotations

from BaseClasses import Entrance, ItemClassification, Tutorial
from Options import OptionGroup
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, launch_subprocess

from . import options
from .data import (
    ACTIVITIES,
    ACTIVITY_REQUIREMENTS,
    EQUIPMENT,
    EQUIPMENT_BY_NAME,
    FILLER_KIND_BY_NAME,
    FILLERS,
    GAME_NAME,
    ITEM_NAME_TO_ID,
    LOCATION_NAME_TO_ID,
    LOGIC_ITEM_NAMES,
    MISSION_REQUIREMENTS,
    MISSIONS,
    STARTING_MISSION_ID,
    TRAPS,
)
from .items import Jak3Item
from .regions import create_regions
from .rules import set_rules


def launch_client() -> None:
    from . import client
    launch_subprocess(client.launch, name="Jak3Client")


components.append(Component("Jak 3 Client", func=launch_client, component_type=Type.CLIENT))


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
        OptionGroup("Goal", [
            options.CompletionCondition,
            options.SpecificMissionForCompletion,
            options.NumberOfMissionsForCompletion,
        ]),
        OptionGroup("Traps", [
            options.PercentFillerReplacedWithTraps,
            options.TrapEffectDuration,
            options.TrapWeights,
        ]),
    ]


class Jak3World(World):
    """Mission unlock randomizer for Jak 3 running through OpenGOAL."""

    game = GAME_NAME
    required_client_version = (0, 6, 7)
    options_dataclass = options.Jak3Options
    options: options.Jak3Options
    web = Jak3WebWorld()

    item_name_to_id = ITEM_NAME_TO_ID
    location_name_to_id = LOCATION_NAME_TO_ID
    item_name_groups = {
        "Mission Unlocks": {
            mission.item_name for mission in MISSIONS if mission.task_id != STARTING_MISSION_ID
        },
        "Filler": set(FILLERS),
        "Traps": set(TRAPS),
        "Equipment": set(EQUIPMENT_BY_NAME),
        **{
            group: {equipment.name for equipment in EQUIPMENT if equipment.group == group}
            for group in {equipment.group for equipment in EQUIPMENT}
        },
    }
    location_name_groups = {
        "Missions": {mission.location_name for mission in MISSIONS},
        "Challenges": {activity.location_name for activity in ACTIVITIES},
        **{
            area: {mission.location_name for mission in MISSIONS if mission.area == area}
            for area in {mission.area for mission in MISSIONS}
        },
    }

    mission_entrances: dict[int, Entrance]
    activity_entrances: dict[int, Entrance]
    goal_entrance: Entrance

    def generate_early(self) -> None:
        self.mission_entrances = {}
        self.activity_entrances = {}

    def create_regions(self) -> None:
        create_regions(self)

    def create_item(self, name: str) -> Jak3Item:
        if name in self.item_name_groups["Mission Unlocks"]:
            classification = ItemClassification.progression
        elif name in LOGIC_ITEM_NAMES:
            classification = ItemClassification.progression
        elif name in self.item_name_groups["Equipment"]:
            classification = ItemClassification.useful
        elif name in self.item_name_groups["Traps"]:
            classification = ItemClassification.trap
        else:
            classification = ItemClassification.filler
        return Jak3Item(name, classification, self.item_name_to_id[name], self.player)

    def create_event(self, name: str) -> Jak3Item:
        return Jak3Item(name, ItemClassification.progression, None, self.player)

    def create_items(self) -> None:
        # The intro task is always available. Complete native side-task coverage
        # leaves consumable filler slots after unlocks and equipment are placed.
        unlocks = [
            self.create_item(mission.item_name)
            for mission in MISSIONS
            if mission.task_id != STARTING_MISSION_ID
        ]
        unlocks.extend(
            self.create_item(equipment.name)
            for equipment in EQUIPMENT
            for _ in range(equipment.copies)
        )
        location_count = len(MISSIONS) + len(ACTIVITIES)
        filler_count = location_count - len(unlocks)
        trap_count = round(filler_count * self.options.percent_filler_replaced_with_traps.value / 100)
        trap_names, trap_weights = self.options.trap_weights.weights_pair
        if not any(trap_weights):
            trap_count = 0

        for _ in range(trap_count):
            unlocks.append(self.create_item(self.random.choices(trap_names, weights=trap_weights, k=1)[0]))
        for _ in range(filler_count - trap_count):
            unlocks.append(self.create_item(self.random.choice(FILLERS)))
        self.multiworld.itempool += unlocks

    def set_rules(self) -> None:
        set_rules(self)

    def fill_slot_data(self) -> dict:
        return {
            "completion_condition": self.options.jak_3_completion_condition.value,
            "specific_mission": self.options.specific_mission_for_completion.value,
            "mission_count": self.options.number_of_missions_for_completion.value,
            "trap_duration": self.options.trap_effect_duration.value,
            "starting_task": STARTING_MISSION_ID,
            "task_ids": {
                mission.item_name: mission.task_id
                for mission in MISSIONS
                if mission.task_id != STARTING_MISSION_ID
            },
            "activity_unlock_counts": {
                str(activity.task_id): activity.unlock_count for activity in ACTIVITIES
            },
            "mission_requirements": {
                str(task_id): {name: count for name, count in requirements}
                for task_id, requirements in MISSION_REQUIREMENTS.items()
            },
            "activity_requirements": {
                str(task_id): {name: count for name, count in requirements}
                for task_id, requirements in ACTIVITY_REQUIREMENTS.items()
            },
            "equipment": {
                equipment.name: {"kind": equipment.kind, "copies": equipment.copies}
                for equipment in EQUIPMENT
            },
            "filler": FILLER_KIND_BY_NAME,
        }

    def get_filler_item_name(self) -> str:
        return self.random.choice(FILLERS)


# Keep a direct lookup importable by the client without rebuilding it.
MISSION_ITEM_ID_TO_TASK = {
    ITEM_NAME_TO_ID[mission.item_name]: mission.task_id
    for mission in MISSIONS
    if mission.task_id != STARTING_MISSION_ID
}
