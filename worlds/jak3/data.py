"""Static data for the current, pre-design-default Jak 3 scaffold.

Native task IDs remain the boundary shared by the APWorld, client, and
OpenGOAL mod.  Archipelago network IDs are deliberately literal fields: the
design requires explicit, versioned IDs that cannot change when a source tuple
is reordered.  These protocol-1 values are retained for compatibility and are
not an endorsement of the scaffold as the final 147-location registry.
"""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass


GAME_NAME = "Jak 3"
BASE_ID = 743_000_000
LEGACY_ID_TABLE_VERSION = 1


@dataclass(frozen=True)
class StableIdData:
    name: str
    code: int


@dataclass(frozen=True)
class MissionData:
    task_id: int
    key: str
    name: str
    area: str
    item_id: int | None
    location_id: int

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
    location_id: int

    @property
    def location_name(self) -> str:
        return f"Complete Challenge: {self.name}"


@dataclass(frozen=True)
class EquipmentData:
    name: str
    copies: int
    kind: int
    group: str
    item_id: int


@dataclass(frozen=True)
class RuntimeItemData:
    name: str
    item_id: int
    kind: int


# game-task values 6 through 71 are the main-game task range.  Four internal
# transition/training tasks have no progress-menu text, so descriptive names
# are supplied for them instead of silently omitting valid task IDs.
MISSIONS: tuple[MissionData, ...] = (
    MissionData(6, "city-start", "Watch Intro Movie", "Spargus", None, 743_001_006),
    MissionData(7, "desert-interceptors", "Survive the Desert Ambush", "Spargus", 743_000_007, 743_001_007),
    MissionData(8, "desert-vehicle-training-1", "Complete Vehicle Training I", "Spargus", 743_000_008, 743_001_008),
    MissionData(9, "desert-vehicle-training-2", "Complete Vehicle Training II", "Spargus", 743_000_009, 743_001_009),
    MissionData(10, "arena-training-1", "Complete Arena Training", "Spargus", 743_000_010, 743_001_010),
    MissionData(11, "arena-fight-1", "Earn the First War Amulet", "Spargus", 743_000_011, 743_001_011),
    MissionData(12, "wascity-chase", "Catch the Kanga Rats", "Spargus", 743_000_012, 743_001_012),
    MissionData(13, "wascity-pre-game", "Unlock the Satellite", "Spargus", 743_000_013, 743_001_013),
    MissionData(14, "desert-turtle-training", "Learn to Ride the Tough Puppy", "Wasteland", 743_000_014, 743_001_014),
    MissionData(15, "desert-course-race", "Beat Kleiver in the Desert Race", "Wasteland", 743_000_015, 743_001_015),
    MissionData(16, "desert-artifact-race-1", "Collect Artifacts", "Wasteland", 743_000_016, 743_001_016),
    MissionData(17, "wascity-leaper-race", "Beat the Monks in the Leaper Race", "Spargus", 743_000_017, 743_001_017),
    MissionData(18, "desert-hover", "Destroy the Metal Head Beasts", "Wasteland", 743_000_018, 743_001_018),
    MissionData(19, "arena-fight-2", "Earn the Second War Amulet", "Spargus", 743_000_019, 743_001_019),
    MissionData(20, "desert-catch-lizards", "Corral the Wild Leapers", "Wasteland", 743_000_020, 743_001_020),
    MissionData(21, "desert-rescue", "Rescue the Wastelanders", "Wasteland", 743_000_021, 743_001_021),
    MissionData(22, "wascity-gungame", "Beat the Turret Challenge", "Spargus", 743_000_022, 743_001_022),
    MissionData(23, "arena-fight-3", "Defeat the Marauders in the Arena", "Spargus", 743_000_023, 743_001_023),
    MissionData(24, "nest-eggs", "Destroy the Eggs in the Nest", "Wasteland", 743_000_024, 743_001_024),
    MissionData(25, "temple-climb", "Climb the Monk Temple Tower", "Temple", 743_000_025, 743_001_025),
    MissionData(26, "desert-glide", "Glide to the Volcano", "Wasteland", 743_000_026, 743_001_026),
    MissionData(27, "volcano-darkeco", "Find the Satellite at the Volcano", "Volcano", 743_000_027, 743_001_027),
    MissionData(28, "temple-oracle", "Meet the Monk Temple Oracle", "Temple", 743_000_028, 743_001_028),
    MissionData(29, "desert-oasis-defense", "Protect Ashelin at the Oasis", "Wasteland", 743_000_029, 743_001_029),
    MissionData(30, "temple-tests", "Complete the Monk Temple Tests", "Temple", 743_000_030, 743_001_030),
    MissionData(31, "comb-travel", "Travel Through the Catacomb Subrails", "Catacombs", 743_000_031, 743_001_031),
    MissionData(32, "mine-explore", "Explore the Eco Mine", "Catacombs", 743_000_032, 743_001_032),
    MissionData(33, "mine-blow", "Escort the Bomb Train", "Catacombs", 743_000_033, 743_001_033),
    MissionData(34, "mine-boss", "Defeat Veger's Precursor Robot", "Catacombs", 743_000_034, 743_001_034),
    MissionData(35, "sewer-met-hum", "Reach the Metal Head Area via Sewer", "Haven City", 743_000_035, 743_001_035),
    MissionData(36, "city-vehicle-training", "Complete Haven Vehicle Training", "Haven City", 743_000_036, 743_001_036),
    MissionData(37, "city-port-fight", "Defend the Port from Attack", "Haven City", 743_000_037, 743_001_037),
    MissionData(38, "city-port-attack", "Defeat the Incoming Blast Bots", "Haven City", 743_000_038, 743_001_038),
    MissionData(39, "city-gun-course-1", "Beat Gun Course I", "Haven City", 743_000_039, 743_001_039),
    MissionData(40, "city-sniper-fight", "Destroy the Sniper Cannons", "Haven City", 743_000_040, 743_001_040),
    MissionData(41, "sewer-kg-met", "Reach Freedom HQ", "Haven City", 743_000_041, 743_001_041),
    MissionData(42, "city-destroy-darkeco", "Destroy the Dark Eco Tanks", "Haven City", 743_000_042, 743_001_042),
    MissionData(43, "forest-kill-plants", "Kill the Dark Plants in the Forest", "Forest", 743_000_043, 743_001_043),
    MissionData(44, "city-destroy-grid", "Destroy the Eco Grid with Jinx", "Haven City", 743_000_044, 743_001_044),
    MissionData(45, "city-hijack-vehicle", "Hijack the Eco Vehicle", "Haven City", 743_000_045, 743_001_045),
    MissionData(46, "city-port-assault", "Defend the Port with the Jetboard", "Haven City", 743_000_046, 743_001_046),
    MissionData(47, "city-gun-course-2", "Beat Gun Course II", "Haven City", 743_000_047, 743_001_047),
    MissionData(48, "city-blow-barricade", "Destroy the Barricade with the Bomb Bot", "Haven City", 743_000_048, 743_001_048),
    MissionData(49, "city-protect-hq", "Defend Freedom HQ", "Haven City", 743_000_049, 743_001_049),
    MissionData(50, "sewer-hum-kg", "Find the Switch in the Sewers", "Haven City", 743_000_050, 743_001_050),
    MissionData(51, "city-power-game", "Find the Cipher in the Eco Grid", "Haven City", 743_000_051, 743_001_051),
    MissionData(52, "desert-artifact-race-2", "Race for More Artifacts", "Wasteland", 743_000_052, 743_001_052),
    MissionData(53, "nest-hunt", "Destroy the Metal-pedes in the Nest", "Wasteland", 743_000_053, 743_001_053),
    MissionData(54, "desert-beast-battle", "Destroy the Marauder Beasts", "Wasteland", 743_000_054, 743_001_054),
    MissionData(55, "desert-jump-mission", "Test Drive the Dune Hopper", "Wasteland", 743_000_055, 743_001_055),
    MissionData(56, "desert-chase-marauders", "Chase the Marauders", "Wasteland", 743_000_056, 743_001_056),
    MissionData(57, "forest-ring-chase", "Chase the Precursor Rings", "Forest", 743_000_057, 743_001_057),
    MissionData(58, "factory-sky-battle", "Destroy the War Factory Defenses", "War Factory", 743_000_058, 743_001_058),
    MissionData(59, "factory-assault", "Assault the War Factory", "War Factory", 743_000_059, 743_001_059),
    MissionData(60, "factory-boss", "Defeat the War Factory Boss", "War Factory", 743_000_060, 743_001_060),
    MissionData(61, "temple-defend", "Defend the Monk Temple", "Temple", 743_000_061, 743_001_061),
    MissionData(62, "wascity-defend", "Defend Spargus", "Spargus", 743_000_062, 743_001_062),
    MissionData(63, "forest-turn-on-machine", "Activate the Astro-Viewer in the Forest", "Forest", 743_000_063, 743_001_063),
    MissionData(64, "precursor-tour", "Explore the Precursor Core", "Precursor Core", 743_000_064, 743_001_064),
    MissionData(65, "city-blow-tower", "Break Through the City Tower", "Haven City", 743_000_065, 743_001_065),
    MissionData(66, "tower-destroy", "Destroy the Dark Maker Tower", "Dark Maker Tower", 743_000_066, 743_001_066),
    MissionData(67, "palace-ruins-patrol", "Reach the Palace Ruins", "Palace Ruins", 743_000_067, 743_001_067),
    MissionData(68, "palace-ruins-attack", "Defend the Palace Ruins", "Palace Ruins", 743_000_068, 743_001_068),
    MissionData(69, "comb-wild-ride", "Complete the Catacomb Rail Ride", "Catacombs", 743_000_069, 743_001_069),
    MissionData(70, "precursor-destroy-ship", "Destroy the Dark Ship", "Precursor Core", 743_000_070, 743_001_070),
    MissionData(71, "desert-final-boss", "Defeat Cyber Errol", "Wasteland", 743_000_071, 743_001_071),
)

MISSION_BY_ID = {mission.task_id: mission for mission in MISSIONS}
MISSION_BY_KEY = {mission.key: mission for mission in MISSIONS}
STARTING_MISSION_ID = 6

# Native game-task values 73 through 137 are optional discoveries and side
# challenges. Including the complete range avoids silently discarding valid
# checks and leaves room for useful consumable filler after progression is
# placed.
ACTIVITIES: tuple[ActivityData, ...] = (
    ActivityData(73, "desert-bbush-get-to-1", "Wasteland Discovery 1", 1, 743_001_073),
    ActivityData(74, "desert-bbush-get-to-2", "Wasteland Discovery 2", 2, 743_001_074),
    ActivityData(75, "desert-bbush-get-to-3", "Wasteland Discovery 3", 3, 743_001_075),
    ActivityData(76, "desert-bbush-get-to-4", "Wasteland Discovery 4", 4, 743_001_076),
    ActivityData(77, "desert-bbush-get-to-5", "Wasteland Discovery 5", 5, 743_001_077),
    ActivityData(78, "desert-bbush-get-to-6", "Wasteland Discovery 6", 6, 743_001_078),
    ActivityData(79, "desert-bbush-get-to-7", "Wasteland Discovery 7", 7, 743_001_079),
    ActivityData(80, "desert-bbush-get-to-8", "Wasteland Discovery 8", 8, 743_001_080),
    ActivityData(81, "desert-bbush-get-to-9", "Wasteland Discovery 9", 9, 743_001_081),
    ActivityData(82, "desert-bbush-get-to-11", "Wasteland Discovery 11", 10, 743_001_082),
    ActivityData(83, "desert-bbush-get-to-12", "Wasteland Discovery 12", 11, 743_001_083),
    ActivityData(84, "desert-bbush-get-to-14", "Wasteland Discovery 14", 12, 743_001_084),
    ActivityData(85, "desert-bbush-get-to-16", "Wasteland Discovery 16", 13, 743_001_085),
    ActivityData(86, "desert-bbush-get-to-17", "Wasteland Discovery 17", 14, 743_001_086),
    ActivityData(87, "wascity-bbush-get-to-18", "Spargus Discovery 18", 15, 743_001_087),
    # The game-task enum says desert-bbush-get-to-19, but both node records use
    # wascity-bbush-get-to-19 and task 52 as their source parent.
    ActivityData(88, "wascity-bbush-get-to-19", "Spargus Discovery 19", 16, 743_001_088),
    ActivityData(89, "wascity-bbush-get-to-20", "Spargus Discovery 20", 17, 743_001_089),
    ActivityData(90, "wascity-bbush-get-to-21", "Spargus Discovery 21", 18, 743_001_090),
    ActivityData(91, "wascity-bbush-get-to-22", "Spargus Discovery 22", 19, 743_001_091),
    ActivityData(92, "wascity-bbush-get-to-23", "Spargus Discovery 23", 20, 743_001_092),
    ActivityData(93, "wascity-bbush-get-to-24", "Spargus Discovery 24", 21, 743_001_093),
    ActivityData(94, "wascity-bbush-get-to-25", "Spargus Discovery 25", 22, 743_001_094),
    ActivityData(95, "city-bbush-get-to-26", "Haven Discovery 26", 23, 743_001_095),
    ActivityData(96, "city-bbush-get-to-27", "Haven Discovery 27", 24, 743_001_096),
    ActivityData(97, "city-bbush-get-to-28", "Haven Discovery 28", 25, 743_001_097),
    ActivityData(98, "city-bbush-get-to-29", "Haven Discovery 29", 26, 743_001_098),
    ActivityData(99, "city-bbush-get-to-30", "Haven Discovery 30", 27, 743_001_099),
    ActivityData(100, "city-bbush-get-to-31", "Haven Discovery 31", 28, 743_001_100),
    ActivityData(101, "city-bbush-get-to-32", "Haven Discovery 32", 29, 743_001_101),
    ActivityData(102, "city-bbush-get-to-33", "Haven Discovery 33", 30, 743_001_102),
    ActivityData(103, "city-bbush-get-to-34", "Haven Discovery 34", 31, 743_001_103),
    ActivityData(104, "city-bbush-get-to-35", "Haven Discovery 35", 32, 743_001_104),
    ActivityData(105, "city-bbush-get-to-36", "Haven Discovery 36", 33, 743_001_105),
    ActivityData(106, "city-bbush-get-to-37", "Haven Discovery 37", 34, 743_001_106),
    ActivityData(107, "city-bbush-get-to-38", "Haven Discovery 38", 35, 743_001_107),
    ActivityData(108, "city-bbush-get-to-39", "Haven Discovery 39", 36, 743_001_108),
    ActivityData(109, "city-bbush-get-to-40", "Haven Discovery 40", 37, 743_001_109),
    ActivityData(110, "city-bbush-get-to-41", "Haven Discovery 41", 38, 743_001_110),
    ActivityData(111, "city-bbush-get-to-42", "Haven Discovery 42", 39, 743_001_111),
    ActivityData(112, "city-bbush-get-to-43", "Haven Discovery 43", 40, 743_001_112),
    ActivityData(113, "city-bbush-get-to-44", "Haven Discovery 44", 41, 743_001_113),
    ActivityData(114, "desert-bbush-ring-1", "Wasteland Ring Challenge 1", 16, 743_001_114),
    ActivityData(115, "desert-bbush-ring-2", "Wasteland Ring Challenge 2", 18, 743_001_115),
    ActivityData(116, "wascity-bbush-ring-3", "Spargus Ring Challenge 1", 20, 743_001_116),
    ActivityData(117, "wascity-bbush-ring-4", "Spargus Ring Challenge 2", 22, 743_001_117),
    ActivityData(118, "city-bbush-ring-5", "Haven Ring Challenge 1", 24, 743_001_118),
    ActivityData(119, "city-bbush-ring-6", "Haven Ring Challenge 2", 26, 743_001_119),
    ActivityData(120, "desert-bbush-egg-spider-1", "Destroy the Metal Spider", 28, 743_001_120),
    ActivityData(121, "desert-bbush-spirit-chase-1", "Wasteland Spirit Chase", 30, 743_001_121),
    ActivityData(122, "wascity-bbush-spirit-chase-2", "Spargus Spirit Chase", 32, 743_001_122),
    ActivityData(123, "city-bbush-spirit-chase-3", "Haven Spirit Chase", 34, 743_001_123),
    ActivityData(124, "desert-bbush-timer-chase-1", "Wasteland Time Freeze", 36, 743_001_124),
    ActivityData(125, "wascity-bbush-timer-chase-2", "Spargus Time Freeze", 38, 743_001_125),
    ActivityData(126, "desert-bbush-air-time", "Single Jump Air Time", 40, 743_001_126),
    ActivityData(127, "desert-bbush-total-air-time", "Total Jump Air Time", 42, 743_001_127),
    ActivityData(128, "desert-bbush-jump-distance", "Single Jump Distance", 44, 743_001_128),
    ActivityData(129, "desert-bbush-total-jump-distance", "Total Jump Distance", 46, 743_001_129),
    ActivityData(130, "desert-bbush-roll-count", "Wasteland Roll Challenge", 48, 743_001_130),
    ActivityData(131, "desert-bbush-time-trial-1", "Wasteland Time Trial", 50, 743_001_131),
    ActivityData(132, "desert-bbush-rally", "Wasteland Rally", 52, 743_001_132),
    ActivityData(133, "city-bbush-port-attack", "Defend the Port Side Mission", 54, 743_001_133),
    ActivityData(134, "desert-rescue-bbush", "Wastelander Rescue Side Mission", 56, 743_001_134),
    ActivityData(135, "city-gun-course-play-for-fun", "Gun Course Free Play", 58, 743_001_135),
    ActivityData(136, "city-jetboard-bbush", "Haven Jetboard Challenge", 60, 743_001_136),
    ActivityData(137, "desert-bbush-destroy-interceptors", "Destroy the Interceptors", 62, 743_001_137),
)

ACTIVITY_BY_ID = {activity.task_id: activity for activity in ACTIVITIES}
CHECK_BY_TASK = {**MISSION_BY_ID, **ACTIVITY_BY_ID}

# Repeated progressive items apply the next native OpenGOAL feature bit. Logic
# classification is derived from the requirement tables below; upgrades which
# only improve survivability or capacity stay useful rather than progression.
EQUIPMENT: tuple[EquipmentData, ...] = (
    EquipmentData("Progressive Scatter Gun", 3, 0, "Weapons", 743_000_100),
    EquipmentData("Progressive Blaster", 3, 1, "Weapons", 743_000_101),
    EquipmentData("Progressive Vulcan Fury", 3, 2, "Weapons", 743_000_102),
    EquipmentData("Progressive Peace Maker", 3, 3, "Weapons", 743_000_103),
    EquipmentData("Progressive Red Ammo Capacity", 2, 4, "Gun Upgrades", 743_000_104),
    EquipmentData("Progressive Yellow Ammo Capacity", 2, 5, "Gun Upgrades", 743_000_105),
    EquipmentData("Progressive Blue Ammo Capacity", 2, 6, "Gun Upgrades", 743_000_106),
    EquipmentData("Progressive Dark Ammo Capacity", 2, 7, "Gun Upgrades", 743_000_107),
    EquipmentData("Jetboard", 1, 8, "Vehicles", 743_000_108),
    EquipmentData("Tough Puppy", 1, 9, "Vehicles", 743_000_109),
    EquipmentData("Sand Shark", 1, 10, "Vehicles", 743_000_110),
    EquipmentData("Gila Stomper", 1, 11, "Vehicles", 743_000_111),
    EquipmentData("Dune Hopper", 1, 12, "Vehicles", 743_000_112),
    EquipmentData("Slam Dozer", 1, 13, "Vehicles", 743_000_113),
    EquipmentData("Progressive Dark Jak Power", 4, 14, "Powers", 743_000_114),
    EquipmentData("Progressive Light Jak Power", 4, 15, "Powers", 743_000_115),
    EquipmentData("Progressive Armor", 4, 16, "Armor", 743_000_116),
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

TRAP_DATA: tuple[RuntimeItemData, ...] = (
    RuntimeItemData("Ammo Trap", 743_003_000, 0),
    RuntimeItemData("Camera Trap", 743_003_001, 1),
    RuntimeItemData("Dark Trap", 743_003_002, 2),
    RuntimeItemData("Darkness Trap", 743_003_003, 3),
    RuntimeItemData("Earthquake Trap", 743_003_004, 4),
    RuntimeItemData("Gravity Trap", 743_003_005, 5),
    RuntimeItemData("Health Trap", 743_003_006, 6),
    RuntimeItemData("Hero Trap", 743_003_007, 7),
    RuntimeItemData("High Alert Trap", 743_003_008, 8),
    RuntimeItemData("Ledge Trap", 743_003_009, 9),
    RuntimeItemData("Mirror Trap", 743_003_010, 10),
    RuntimeItemData("Pacifism Trap", 743_003_011, 11),
    RuntimeItemData("Slip Trap", 743_003_012, 12),
    RuntimeItemData("Slow Trap", 743_003_013, 13),
    RuntimeItemData("Speed Trap", 743_003_014, 14),
    RuntimeItemData("Teleport Trap", 743_003_015, 15),
    RuntimeItemData("Trip Trap", 743_003_016, 16),
)

FILLER_DATA: tuple[RuntimeItemData, ...] = (
    RuntimeItemData("Health Pack", 743_002_000, 0),
    RuntimeItemData("Red Ammo Crate", 743_002_001, 1),
    RuntimeItemData("Yellow Ammo Crate", 743_002_002, 2),
    RuntimeItemData("Blue Ammo Crate", 743_002_003, 3),
    RuntimeItemData("Dark Ammo Crate", 743_002_004, 4),
    RuntimeItemData("Light Eco", 743_002_005, 5),
    RuntimeItemData("Dark Eco", 743_002_006, 6),
)

# Compatibility views used by the current generator and protocol payload.
# Their order is no longer an ID or runtime-kind authority.
TRAPS = tuple(item.name for item in TRAP_DATA)
FILLERS = tuple(item.name for item in FILLER_DATA)
TRAP_KIND_BY_NAME = {item.name: item.kind for item in TRAP_DATA}
FILLER_KIND_BY_NAME = {item.name: item.kind for item in FILLER_DATA}


def build_name_to_id(
    entries: Iterable[StableIdData], table_name: str
) -> dict[str, int]:
    """Build a deterministic ID table and reject ambiguous public identities."""

    ordered_entries = sorted(entries, key=lambda entry: (entry.name, entry.code))
    by_name: dict[str, int] = {}
    by_code: dict[int, str] = {}
    for entry in ordered_entries:
        if entry.name in by_name:
            raise ValueError(f"Duplicate {table_name} name: {entry.name!r}")
        if entry.code in by_code:
            raise ValueError(
                f"Duplicate {table_name} ID {entry.code}: "
                f"{by_code[entry.code]!r} and {entry.name!r}"
            )
        by_name[entry.name] = entry.code
        by_code[entry.code] = entry.name
    return by_name


def stable_table_fingerprint(table: dict[str, int]) -> str:
    """Hash UTF-8 ``name<TAB>id<LF>`` rows in ordinal name order."""

    payload = "".join(f"{name}\t{code}\n" for name, code in sorted(table.items()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


ITEM_ID_DATA: tuple[StableIdData, ...] = (
    *(StableIdData(mission.item_name, mission.item_id)
      for mission in MISSIONS if mission.item_id is not None),
    *(StableIdData(equipment.name, equipment.item_id) for equipment in EQUIPMENT),
    *(StableIdData(item.name, item.item_id) for item in FILLER_DATA),
    *(StableIdData(item.name, item.item_id) for item in TRAP_DATA),
)
LOCATION_ID_DATA: tuple[StableIdData, ...] = (
    *(StableIdData(mission.location_name, mission.location_id) for mission in MISSIONS),
    *(StableIdData(activity.location_name, activity.location_id) for activity in ACTIVITIES),
)

ITEM_NAME_TO_ID = build_name_to_id(ITEM_ID_DATA, "item")
LOCATION_NAME_TO_ID = build_name_to_id(LOCATION_ID_DATA, "location")

_cross_table_id_overlap = set(ITEM_NAME_TO_ID.values()) & set(LOCATION_NAME_TO_ID.values())
if _cross_table_id_overlap:
    raise ValueError(
        "Item and location ID tables overlap: "
        + ", ".join(map(str, sorted(_cross_table_id_overlap)))
    )

ITEM_TABLE_FINGERPRINT = stable_table_fingerprint(ITEM_NAME_TO_ID)
LOCATION_TABLE_FINGERPRINT = stable_table_fingerprint(LOCATION_NAME_TO_ID)
