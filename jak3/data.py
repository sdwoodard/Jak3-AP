"""Static Jak 3 data derived from OpenGOAL's ``game-task`` enum.

Native task IDs are intentionally kept alongside every mission.  They are the
stable boundary shared by the APWorld, client, and OpenGOAL mod.
"""

from dataclasses import dataclass


GAME_NAME = "Jak 3"
BASE_ID = 743_000_000


@dataclass(frozen=True)
class MissionData:
    task_id: int
    key: str
    name: str
    area: str

    @property
    def item_name(self) -> str:
        return f"Mission Unlock: {self.name}"

    @property
    def location_name(self) -> str:
        return f"Complete Mission: {self.name}"


@dataclass(frozen=True)
class ActivityData:
    task_id: int
    key: str
    name: str
    unlock_count: int

    @property
    def location_name(self) -> str:
        return f"Complete Challenge: {self.name}"


@dataclass(frozen=True)
class EquipmentData:
    name: str
    copies: int
    kind: int
    group: str


# game-task values 6 through 71 are the main-game task range.  Four internal
# transition/training tasks have no progress-menu text, so descriptive names
# are supplied for them instead of silently omitting valid task IDs.
MISSIONS: tuple[MissionData, ...] = (
    MissionData(6, "city-start", "Watch Intro Movie", "Spargus"),
    MissionData(7, "desert-interceptors", "Survive the Desert Ambush", "Spargus"),
    MissionData(8, "desert-vehicle-training-1", "Complete Vehicle Training I", "Spargus"),
    MissionData(9, "desert-vehicle-training-2", "Complete Vehicle Training II", "Spargus"),
    MissionData(10, "arena-training-1", "Complete Arena Training", "Spargus"),
    MissionData(11, "arena-fight-1", "Earn the First War Amulet", "Spargus"),
    MissionData(12, "wascity-chase", "Catch the Kanga Rats", "Spargus"),
    MissionData(13, "wascity-pre-game", "Unlock the Satellite", "Spargus"),
    MissionData(14, "desert-turtle-training", "Learn to Ride the Tough Puppy", "Wasteland"),
    MissionData(15, "desert-course-race", "Beat Kleiver in the Desert Race", "Wasteland"),
    MissionData(16, "desert-artifact-race-1", "Collect Artifacts", "Wasteland"),
    MissionData(17, "wascity-leaper-race", "Beat the Monks in the Leaper Race", "Spargus"),
    MissionData(18, "desert-hover", "Destroy the Metal Head Beasts", "Wasteland"),
    MissionData(19, "arena-fight-2", "Earn the Second War Amulet", "Spargus"),
    MissionData(20, "desert-catch-lizards", "Corral the Wild Leapers", "Wasteland"),
    MissionData(21, "desert-rescue", "Rescue the Wastelanders", "Wasteland"),
    MissionData(22, "wascity-gungame", "Beat the Turret Challenge", "Spargus"),
    MissionData(23, "arena-fight-3", "Defeat the Marauders in the Arena", "Spargus"),
    MissionData(24, "nest-eggs", "Destroy the Eggs in the Nest", "Wasteland"),
    MissionData(25, "temple-climb", "Climb the Monk Temple Tower", "Temple"),
    MissionData(26, "desert-glide", "Glide to the Volcano", "Wasteland"),
    MissionData(27, "volcano-darkeco", "Find the Satellite at the Volcano", "Volcano"),
    MissionData(28, "temple-oracle", "Meet the Monk Temple Oracle", "Temple"),
    MissionData(29, "desert-oasis-defense", "Protect Ashelin at the Oasis", "Wasteland"),
    MissionData(30, "temple-tests", "Complete the Monk Temple Tests", "Temple"),
    MissionData(31, "comb-travel", "Travel Through the Catacomb Subrails", "Catacombs"),
    MissionData(32, "mine-explore", "Explore the Eco Mine", "Catacombs"),
    MissionData(33, "mine-blow", "Escort the Bomb Train", "Catacombs"),
    MissionData(34, "mine-boss", "Defeat Veger's Precursor Robot", "Catacombs"),
    MissionData(35, "sewer-met-hum", "Reach the Metal Head Area via Sewer", "Haven City"),
    MissionData(36, "city-vehicle-training", "Complete Haven Vehicle Training", "Haven City"),
    MissionData(37, "city-port-fight", "Defend the Port from Attack", "Haven City"),
    MissionData(38, "city-port-attack", "Defeat the Incoming Blast Bots", "Haven City"),
    MissionData(39, "city-gun-course-1", "Beat Gun Course I", "Haven City"),
    MissionData(40, "city-sniper-fight", "Destroy the Sniper Cannons", "Haven City"),
    MissionData(41, "sewer-kg-met", "Reach Freedom HQ", "Haven City"),
    MissionData(42, "city-destroy-darkeco", "Destroy the Dark Eco Tanks", "Haven City"),
    MissionData(43, "forest-kill-plants", "Kill the Dark Plants in the Forest", "Forest"),
    MissionData(44, "city-destroy-grid", "Destroy the Eco Grid with Jinx", "Haven City"),
    MissionData(45, "city-hijack-vehicle", "Hijack the Eco Vehicle", "Haven City"),
    MissionData(46, "city-port-assault", "Defend the Port with the Jetboard", "Haven City"),
    MissionData(47, "city-gun-course-2", "Beat Gun Course II", "Haven City"),
    MissionData(48, "city-blow-barricade", "Destroy the Barricade with the Bomb Bot", "Haven City"),
    MissionData(49, "city-protect-hq", "Defend Freedom HQ", "Haven City"),
    MissionData(50, "sewer-hum-kg", "Find the Switch in the Sewers", "Haven City"),
    MissionData(51, "city-power-game", "Find the Cipher in the Eco Grid", "Haven City"),
    MissionData(52, "desert-artifact-race-2", "Race for More Artifacts", "Wasteland"),
    MissionData(53, "nest-hunt", "Destroy the Metal-pedes in the Nest", "Wasteland"),
    MissionData(54, "desert-beast-battle", "Destroy the Marauder Beasts", "Wasteland"),
    MissionData(55, "desert-jump-mission", "Test Drive the Dune Hopper", "Wasteland"),
    MissionData(56, "desert-chase-marauders", "Chase the Marauders", "Wasteland"),
    MissionData(57, "forest-ring-chase", "Chase the Precursor Rings", "Forest"),
    MissionData(58, "factory-sky-battle", "Destroy the War Factory Defenses", "War Factory"),
    MissionData(59, "factory-assault", "Assault the War Factory", "War Factory"),
    MissionData(60, "factory-boss", "Defeat the War Factory Boss", "War Factory"),
    MissionData(61, "temple-defend", "Defend the Monk Temple", "Temple"),
    MissionData(62, "wascity-defend", "Defend Spargus", "Spargus"),
    MissionData(63, "forest-turn-on-machine", "Activate the Astro-Viewer in the Forest", "Forest"),
    MissionData(64, "precursor-tour", "Explore the Precursor Core", "Precursor Core"),
    MissionData(65, "city-blow-tower", "Break Through the City Tower", "Haven City"),
    MissionData(66, "tower-destroy", "Destroy the Dark Maker Tower", "Dark Maker Tower"),
    MissionData(67, "palace-ruins-patrol", "Reach the Palace Ruins", "Palace Ruins"),
    MissionData(68, "palace-ruins-attack", "Defend the Palace Ruins", "Palace Ruins"),
    MissionData(69, "comb-wild-ride", "Complete the Catacomb Rail Ride", "Catacombs"),
    MissionData(70, "precursor-destroy-ship", "Destroy the Dark Ship", "Precursor Core"),
    MissionData(71, "desert-final-boss", "Defeat Cyber Errol", "Wasteland"),
)

MISSION_BY_ID = {mission.task_id: mission for mission in MISSIONS}
MISSION_BY_KEY = {mission.key: mission for mission in MISSIONS}
STARTING_MISSION_ID = 6

# Native game-task values 73 through 137 are optional discoveries and side
# challenges. Including the complete range avoids silently discarding valid
# checks and leaves room for useful consumable filler after progression is
# placed.
ACTIVITIES: tuple[ActivityData, ...] = (
    ActivityData(73, "desert-bbush-get-to-1", "Wasteland Discovery 1", 1),
    ActivityData(74, "desert-bbush-get-to-2", "Wasteland Discovery 2", 2),
    ActivityData(75, "desert-bbush-get-to-3", "Wasteland Discovery 3", 3),
    ActivityData(76, "desert-bbush-get-to-4", "Wasteland Discovery 4", 4),
    ActivityData(77, "desert-bbush-get-to-5", "Wasteland Discovery 5", 5),
    ActivityData(78, "desert-bbush-get-to-6", "Wasteland Discovery 6", 6),
    ActivityData(79, "desert-bbush-get-to-7", "Wasteland Discovery 7", 7),
    ActivityData(80, "desert-bbush-get-to-8", "Wasteland Discovery 8", 8),
    ActivityData(81, "desert-bbush-get-to-9", "Wasteland Discovery 9", 9),
    ActivityData(82, "desert-bbush-get-to-11", "Wasteland Discovery 11", 10),
    ActivityData(83, "desert-bbush-get-to-12", "Wasteland Discovery 12", 11),
    ActivityData(84, "desert-bbush-get-to-14", "Wasteland Discovery 14", 12),
    ActivityData(85, "desert-bbush-get-to-16", "Wasteland Discovery 16", 13),
    ActivityData(86, "desert-bbush-get-to-17", "Wasteland Discovery 17", 14),
    ActivityData(87, "wascity-bbush-get-to-18", "Spargus Discovery 18", 15),
    ActivityData(88, "desert-bbush-get-to-19", "Wasteland Discovery 19", 16),
    ActivityData(89, "wascity-bbush-get-to-20", "Spargus Discovery 20", 17),
    ActivityData(90, "wascity-bbush-get-to-21", "Spargus Discovery 21", 18),
    ActivityData(91, "wascity-bbush-get-to-22", "Spargus Discovery 22", 19),
    ActivityData(92, "wascity-bbush-get-to-23", "Spargus Discovery 23", 20),
    ActivityData(93, "wascity-bbush-get-to-24", "Spargus Discovery 24", 21),
    ActivityData(94, "wascity-bbush-get-to-25", "Spargus Discovery 25", 22),
    ActivityData(95, "city-bbush-get-to-26", "Haven Discovery 26", 23),
    ActivityData(96, "city-bbush-get-to-27", "Haven Discovery 27", 24),
    ActivityData(97, "city-bbush-get-to-28", "Haven Discovery 28", 25),
    ActivityData(98, "city-bbush-get-to-29", "Haven Discovery 29", 26),
    ActivityData(99, "city-bbush-get-to-30", "Haven Discovery 30", 27),
    ActivityData(100, "city-bbush-get-to-31", "Haven Discovery 31", 28),
    ActivityData(101, "city-bbush-get-to-32", "Haven Discovery 32", 29),
    ActivityData(102, "city-bbush-get-to-33", "Haven Discovery 33", 30),
    ActivityData(103, "city-bbush-get-to-34", "Haven Discovery 34", 31),
    ActivityData(104, "city-bbush-get-to-35", "Haven Discovery 35", 32),
    ActivityData(105, "city-bbush-get-to-36", "Haven Discovery 36", 33),
    ActivityData(106, "city-bbush-get-to-37", "Haven Discovery 37", 34),
    ActivityData(107, "city-bbush-get-to-38", "Haven Discovery 38", 35),
    ActivityData(108, "city-bbush-get-to-39", "Haven Discovery 39", 36),
    ActivityData(109, "city-bbush-get-to-40", "Haven Discovery 40", 37),
    ActivityData(110, "city-bbush-get-to-41", "Haven Discovery 41", 38),
    ActivityData(111, "city-bbush-get-to-42", "Haven Discovery 42", 39),
    ActivityData(112, "city-bbush-get-to-43", "Haven Discovery 43", 40),
    ActivityData(113, "city-bbush-get-to-44", "Haven Discovery 44", 41),
    ActivityData(114, "desert-bbush-ring-1", "Wasteland Ring Challenge 1", 16),
    ActivityData(115, "desert-bbush-ring-2", "Wasteland Ring Challenge 2", 18),
    ActivityData(116, "wascity-bbush-ring-3", "Spargus Ring Challenge 1", 20),
    ActivityData(117, "wascity-bbush-ring-4", "Spargus Ring Challenge 2", 22),
    ActivityData(118, "city-bbush-ring-5", "Haven Ring Challenge 1", 24),
    ActivityData(119, "city-bbush-ring-6", "Haven Ring Challenge 2", 26),
    ActivityData(120, "desert-bbush-egg-spider-1", "Destroy the Metal Spider", 28),
    ActivityData(121, "desert-bbush-spirit-chase-1", "Wasteland Spirit Chase", 30),
    ActivityData(122, "wascity-bbush-spirit-chase-2", "Spargus Spirit Chase", 32),
    ActivityData(123, "city-bbush-spirit-chase-3", "Haven Spirit Chase", 34),
    ActivityData(124, "desert-bbush-timer-chase-1", "Wasteland Time Freeze", 36),
    ActivityData(125, "wascity-bbush-timer-chase-2", "Spargus Time Freeze", 38),
    ActivityData(126, "desert-bbush-air-time", "Single Jump Air Time", 40),
    ActivityData(127, "desert-bbush-total-air-time", "Total Jump Air Time", 42),
    ActivityData(128, "desert-bbush-jump-distance", "Single Jump Distance", 44),
    ActivityData(129, "desert-bbush-total-jump-distance", "Total Jump Distance", 46),
    ActivityData(130, "desert-bbush-roll-count", "Wasteland Roll Challenge", 48),
    ActivityData(131, "desert-bbush-time-trial-1", "Wasteland Time Trial", 50),
    ActivityData(132, "desert-bbush-rally", "Wasteland Rally", 52),
    ActivityData(133, "city-bbush-port-attack", "Defend the Port Side Mission", 54),
    ActivityData(134, "desert-rescue-bbush", "Wastelander Rescue Side Mission", 56),
    ActivityData(135, "city-gun-course-play-for-fun", "Gun Course Free Play", 58),
    ActivityData(136, "city-jetboard-bbush", "Haven Jetboard Challenge", 60),
    ActivityData(137, "desert-bbush-destroy-interceptors", "Destroy the Interceptors", 62),
)

ACTIVITY_BY_ID = {activity.task_id: activity for activity in ACTIVITIES}
CHECK_BY_TASK = {**MISSION_BY_ID, **ACTIVITY_BY_ID}

# Repeated progressive items apply the next native OpenGOAL feature bit. Logic
# classification is derived from the requirement tables below; upgrades which
# only improve survivability or capacity stay useful rather than progression.
EQUIPMENT: tuple[EquipmentData, ...] = (
    EquipmentData("Progressive Scatter Gun", 3, 0, "Weapons"),
    EquipmentData("Progressive Blaster", 3, 1, "Weapons"),
    EquipmentData("Progressive Vulcan Fury", 3, 2, "Weapons"),
    EquipmentData("Progressive Peace Maker", 3, 3, "Weapons"),
    EquipmentData("Progressive Red Ammo Capacity", 2, 4, "Gun Upgrades"),
    EquipmentData("Progressive Yellow Ammo Capacity", 2, 5, "Gun Upgrades"),
    EquipmentData("Progressive Blue Ammo Capacity", 2, 6, "Gun Upgrades"),
    EquipmentData("Progressive Dark Ammo Capacity", 2, 7, "Gun Upgrades"),
    EquipmentData("Jetboard", 1, 8, "Vehicles"),
    EquipmentData("Tough Puppy", 1, 9, "Vehicles"),
    EquipmentData("Sand Shark", 1, 10, "Vehicles"),
    EquipmentData("Gila Stomper", 1, 11, "Vehicles"),
    EquipmentData("Dune Hopper", 1, 12, "Vehicles"),
    EquipmentData("Slam Dozer", 1, 13, "Vehicles"),
    EquipmentData("Progressive Dark Jak Power", 4, 14, "Powers"),
    EquipmentData("Progressive Light Jak Power", 4, 15, "Powers"),
    EquipmentData("Progressive Armor", 4, 16, "Armor"),
)

EQUIPMENT_BY_NAME = {equipment.name: equipment for equipment in EQUIPMENT}

# A requirement is an item name and the number of progressive copies needed.
# These requirements describe inventory actually needed to execute a mission,
# not vanilla story order. They are deliberately conservative: Archipelago may
# place an item earlier than vanilla, but never labels a gear-dependent mission
# reachable before that gear exists.
Requirement = tuple[str, int]

MISSION_REQUIREMENTS: dict[int, tuple[Requirement, ...]] = {
    7: (("Progressive Scatter Gun", 1),),
    8: (("Tough Puppy", 1),),
    9: (("Tough Puppy", 1),),
    10: (("Progressive Scatter Gun", 1),),
    11: (("Progressive Scatter Gun", 1),),
    14: (("Tough Puppy", 1),),
    15: (("Tough Puppy", 1),),
    16: (("Tough Puppy", 1),),
    18: (("Sand Shark", 1), ("Progressive Scatter Gun", 1)),
    19: (("Progressive Scatter Gun", 1),),
    21: (("Sand Shark", 1),),
    23: (("Progressive Scatter Gun", 1), ("Progressive Blaster", 1)),
    24: (("Progressive Scatter Gun", 1),),
    29: (("Progressive Blaster", 1),),
    30: (("Jetboard", 1),),
    32: (("Progressive Scatter Gun", 1),),
    33: (("Progressive Blaster", 1),),
    34: (("Progressive Blaster", 1), ("Progressive Vulcan Fury", 1)),
    35: (("Progressive Scatter Gun", 1),),
    37: (("Progressive Blaster", 1),),
    38: (("Progressive Blaster", 1),),
    39: (("Progressive Scatter Gun", 2), ("Progressive Blaster", 2),
         ("Progressive Vulcan Fury", 1)),
    40: (("Progressive Blaster", 1),),
    42: (("Progressive Blaster", 1),),
    43: (("Progressive Blaster", 1),),
    44: (("Progressive Blaster", 1),),
    46: (("Jetboard", 1), ("Progressive Blaster", 1)),
    47: (("Progressive Scatter Gun", 3), ("Progressive Blaster", 3),
         ("Progressive Vulcan Fury", 2), ("Progressive Peace Maker", 1)),
    49: (("Progressive Blaster", 2),),
    50: (("Progressive Scatter Gun", 2),),
    52: (("Sand Shark", 1),),
    53: (("Progressive Vulcan Fury", 1),),
    54: (("Gila Stomper", 1),),
    55: (("Dune Hopper", 1),),
    56: (("Dune Hopper", 1),),
    57: (("Jetboard", 1),),
    59: (("Progressive Scatter Gun", 2), ("Progressive Blaster", 2),
         ("Progressive Vulcan Fury", 2)),
    60: (("Progressive Blaster", 2), ("Progressive Vulcan Fury", 2),
         ("Progressive Peace Maker", 1)),
    61: (("Progressive Blaster", 2),),
    62: (("Progressive Blaster", 2), ("Progressive Vulcan Fury", 1)),
    64: (("Progressive Light Jak Power", 3), ("Progressive Blaster", 2)),
    65: (("Progressive Light Jak Power", 4), ("Progressive Blaster", 2)),
    66: (("Progressive Light Jak Power", 4), ("Progressive Peace Maker", 1)),
    67: (("Jetboard", 1),),
    68: (("Progressive Blaster", 2), ("Progressive Vulcan Fury", 2)),
    69: (("Progressive Blaster", 2),),
    70: (("Progressive Light Jak Power", 4), ("Progressive Peace Maker", 2)),
    71: (("Dune Hopper", 1), ("Progressive Blaster", 3),
         ("Progressive Vulcan Fury", 3), ("Progressive Peace Maker", 2)),
}

ACTIVITY_REQUIREMENTS: dict[int, tuple[Requirement, ...]] = {
    **{task_id: (("Tough Puppy", 1),) for task_id in range(73, 95)},
    **{task_id: (("Jetboard", 1),) for task_id in range(95, 114)},
    114: (("Sand Shark", 1),),
    115: (("Dune Hopper", 1),),
    116: (("Tough Puppy", 1),),
    117: (("Tough Puppy", 1),),
    118: (("Jetboard", 1),),
    119: (("Jetboard", 1),),
    120: (("Progressive Vulcan Fury", 1),),
    121: (("Sand Shark", 1),),
    122: (("Tough Puppy", 1),),
    123: (("Jetboard", 1),),
    124: (("Progressive Light Jak Power", 2),),
    125: (("Progressive Light Jak Power", 2),),
    **{task_id: (("Dune Hopper", 1),) for task_id in range(126, 133)},
    133: (("Jetboard", 1), ("Progressive Blaster", 2)),
    134: (("Sand Shark", 1),),
    135: (("Progressive Scatter Gun", 3), ("Progressive Blaster", 3),
          ("Progressive Vulcan Fury", 2), ("Progressive Peace Maker", 1)),
    136: (("Jetboard", 1),),
    137: (("Dune Hopper", 1), ("Progressive Blaster", 2)),
}

LOGIC_ITEM_NAMES = {
    name
    for requirements in (*MISSION_REQUIREMENTS.values(), *ACTIVITY_REQUIREMENTS.values())
    for name, _count in requirements
}

TRAPS: tuple[str, ...] = (
    "Ammo Trap", "Camera Trap", "Dark Trap", "Darkness Trap", "Earthquake Trap",
    "Gravity Trap", "Health Trap", "Hero Trap", "High Alert Trap", "Ledge Trap",
    "Mirror Trap", "Pacifism Trap", "Slip Trap", "Slow Trap", "Speed Trap",
    "Teleport Trap", "Trip Trap",
)

FILLERS: tuple[str, ...] = (
    "Health Pack",
    "Red Ammo Crate",
    "Yellow Ammo Crate",
    "Blue Ammo Crate",
    "Dark Ammo Crate",
    "Light Eco",
    "Dark Eco",
)
FILLER_KIND_BY_NAME = {name: kind for kind, name in enumerate(FILLERS)}


def item_id_for_task(task_id: int) -> int:
    return BASE_ID + task_id


def location_id_for_task(task_id: int) -> int:
    return BASE_ID + 1_000 + task_id


ITEM_NAME_TO_ID = {
    **{
        mission.item_name: item_id_for_task(mission.task_id)
        for mission in MISSIONS
        if mission.task_id != STARTING_MISSION_ID
    },
    **{equipment.name: BASE_ID + 100 + equipment.kind for equipment in EQUIPMENT},
    **{name: BASE_ID + 2_000 + index for index, name in enumerate(FILLERS)},
    **{name: BASE_ID + 3_000 + index for index, name in enumerate(TRAPS)},
}

LOCATION_NAME_TO_ID = {
    **{mission.location_name: location_id_for_task(mission.task_id) for mission in MISSIONS},
    **{activity.location_name: location_id_for_task(activity.task_id) for activity in ACTIVITIES},
}
