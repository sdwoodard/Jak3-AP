"""Authoritative first-release item, location, and mission registries.

This module freezes the design-version 0.3 identities without activating the
147-location generator.  The protocol-1 identities are copied literally into
an independent compatibility ledger so later scaffold changes cannot erase a
published ID or silently redefine a retained concept.

Network IDs are literal record fields.  Event items and event locations have
``None`` codes and therefore never enter Archipelago's network data package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .canonical import canonical_json_bytes, canonical_sha256
from .legacy_ids import (
    FROZEN_LEGACY_ITEM_IDS,
    FROZEN_LEGACY_LOCATION_IDS,
    FrozenLegacyIdRecord,
)
from .versions import ITEM_TABLE_VERSION, LOCATION_TABLE_VERSION, MISSION_TABLE_VERSION


@dataclass(frozen=True, slots=True)
class ItemRecord:
    name: str
    code: int
    classification: str
    family: str
    pool_count: int


@dataclass(frozen=True, slots=True)
class LocationRecord:
    name: str
    code: int
    family: str
    native_task_id: int | None = None
    native_node_id: int | None = None
    orb_threshold: int | None = None
    default_excluded: bool = False


@dataclass(frozen=True, slots=True)
class EventRecord:
    location_name: str
    item_name: str
    native_task_id: int
    code: None = None


@dataclass(frozen=True, slots=True)
class MissionRecord:
    task_id: int
    native_alias: str
    runtime_alias: str
    display_name: str
    bootstrap_profile_id: str | None = None
    shadow_profile_id: str | None = None


@dataclass(frozen=True, slots=True)
class MissionProfileRecord:
    profile_id: str
    native_task_id: int


@dataclass(frozen=True, slots=True)
class ReservedIdRecord:
    code: int
    legacy_name: str
    reason: str


RegistryRecord = (
    ItemRecord
    | LocationRecord
    | EventRecord
    | MissionRecord
    | MissionProfileRecord
    | ReservedIdRecord
)
NetworkRecord = ItemRecord | LocationRecord


# 26 progression instances across 24 unique network definitions.
PROGRESSION_ITEMS: tuple[ItemRecord, ...] = (
    ItemRecord(
        "Spargus Field Orders", 743_010_000, "progression", "route_authorization", 1
    ),
    ItemRecord(
        "Temple Expedition Orders", 743_010_001, "progression", "route_authorization", 1
    ),
    ItemRecord(
        "Haven City Access", 743_010_002, "progression", "route_authorization", 1
    ),
    ItemRecord(
        "Freedom League Orders", 743_010_003, "progression", "route_authorization", 1
    ),
    ItemRecord(
        "Wasteland Artifact Intel", 743_010_004, "progression", "route_authorization", 1
    ),
    ItemRecord(
        "War Factory Coordinates", 743_010_005, "progression", "route_authorization", 1
    ),
    ItemRecord(
        "Precursor Network Access", 743_010_006, "progression", "route_authorization", 1
    ),
    ItemRecord(
        "Dark Maker Targeting Data",
        743_010_007,
        "progression",
        "route_authorization",
        1,
    ),
    # Jetboard is exactly the legacy network concept and retains its ID.
    ItemRecord("Jetboard", 743_000_108, "progression", "capability", 1),
    ItemRecord("Jetboard Launch", 743_010_008, "progression", "capability", 1),
    ItemRecord("Invisibility Statues", 743_010_009, "progression", "capability", 1),
    ItemRecord("Dark Bomb", 743_010_010, "progression", "capability", 1),
    ItemRecord("Dark Strike", 743_010_011, "progression", "capability", 1),
    ItemRecord("Light Flight", 743_010_012, "progression", "capability", 1),
    ItemRecord(
        "Progressive Wasteland Vehicle License",
        743_010_013,
        "progression",
        "vehicle_license",
        3,
    ),
    ItemRecord("Blaster", 743_010_014, "progression_skip_balancing", "morph_gun", 1),
    ItemRecord(
        "Vulcan Fury", 743_010_015, "progression_skip_balancing", "morph_gun", 1
    ),
    ItemRecord(
        "Seal of Mar", 743_010_016, "progression_skip_balancing", "finale_relic", 1
    ),
    ItemRecord(
        "Cipher Glyph", 743_010_017, "progression_skip_balancing", "finale_relic", 1
    ),
    ItemRecord(
        "Holo Cube", 743_010_018, "progression_skip_balancing", "finale_relic", 1
    ),
    ItemRecord(
        "Quantum Reflector",
        743_010_019,
        "progression_skip_balancing",
        "finale_relic",
        1,
    ),
    ItemRecord(
        "Beam Generator", 743_010_020, "progression_skip_balancing", "finale_relic", 1
    ),
    ItemRecord(
        "Precursor Prism", 743_010_021, "progression_skip_balancing", "finale_relic", 1
    ),
    ItemRecord(
        "Time Map", 743_010_022, "progression_skip_balancing", "finale_relic", 1
    ),
)


# 28 useful instances across 21 unique network definitions.
USEFUL_ITEMS: tuple[ItemRecord, ...] = (
    ItemRecord("Scatter Gun", 743_010_100, "useful", "morph_gun", 1),
    ItemRecord("Wave Concussor", 743_010_101, "useful", "morph_gun", 1),
    ItemRecord("Plasmite RPG", 743_010_102, "useful", "morph_gun", 1),
    ItemRecord("Beam Reflexor", 743_010_103, "useful", "morph_gun", 1),
    ItemRecord("Gyro Burster", 743_010_104, "useful", "morph_gun", 1),
    ItemRecord("Arc Wielder", 743_010_105, "useful", "morph_gun", 1),
    ItemRecord("Needle Lazer", 743_010_106, "useful", "morph_gun", 1),
    ItemRecord("Peace Maker", 743_010_107, "useful", "morph_gun", 1),
    ItemRecord("Mass Imploder", 743_010_108, "useful", "morph_gun", 1),
    ItemRecord("Super Nova", 743_010_109, "useful", "morph_gun", 1),
    # These progressive capacity and armor concepts retain their legacy IDs.
    ItemRecord(
        "Progressive Red Ammo Capacity", 743_000_104, "useful", "ammo_capacity", 2
    ),
    ItemRecord(
        "Progressive Yellow Ammo Capacity", 743_000_105, "useful", "ammo_capacity", 2
    ),
    ItemRecord(
        "Progressive Blue Ammo Capacity", 743_000_106, "useful", "ammo_capacity", 2
    ),
    ItemRecord(
        "Progressive Dark Ammo Capacity", 743_000_107, "useful", "ammo_capacity", 2
    ),
    ItemRecord("Progressive Armor", 743_000_116, "useful", "armor", 4),
    ItemRecord("Jetboard Zap", 743_010_110, "useful", "jetboard", 1),
    ItemRecord("Light Regeneration", 743_010_111, "useful", "light_power", 1),
    ItemRecord("Flash Freeze", 743_010_112, "useful", "light_power", 1),
    ItemRecord("Light Shield", 743_010_113, "useful", "light_power", 1),
    ItemRecord("Dark Blast", 743_010_114, "useful", "dark_power", 1),
    # The display name is normalized, but the permanent Slam Dozer ownership
    # concept is unchanged and therefore retains legacy ID 743000113.
    ItemRecord("Ram 'Rod / Slam Dozer", 743_000_113, "useful", "vehicle", 1),
)


FILLER_ITEMS: tuple[ItemRecord, ...] = (
    ItemRecord("Precursor Orb Pack (5)", 743_012_000, "filler", "currency", 0),
    ItemRecord("Precursor Orb Pack (10)", 743_012_001, "filler", "currency", 0),
    ItemRecord("Precursor Orb Pack (25)", 743_012_002, "filler", "currency", 0),
    ItemRecord("Skull Gem Pack (1)", 743_012_003, "filler", "currency", 0),
    ItemRecord("Skull Gem Pack (3)", 743_012_004, "filler", "currency", 0),
    ItemRecord("Skull Gem Pack (5)", 743_012_005, "filler", "currency", 0),
    ItemRecord("Red Ammo Refill", 743_012_006, "filler", "consumable", 0),
    ItemRecord("Yellow Ammo Refill", 743_012_007, "filler", "consumable", 0),
    ItemRecord("Blue Ammo Refill", 743_012_008, "filler", "consumable", 0),
    ItemRecord("Dark Ammo Refill", 743_012_009, "filler", "consumable", 0),
    ItemRecord("Health Refill", 743_012_010, "filler", "consumable", 0),
    ItemRecord("Light Eco Refill", 743_012_011, "filler", "consumable", 0),
    ItemRecord("Dark Eco Refill", 743_012_012, "filler", "consumable", 0),
    ItemRecord("Vehicle Repair", 743_012_013, "filler", "consumable", 0),
    ItemRecord("Vehicle Turbo Refill", 743_012_014, "filler", "consumable", 0),
)


# Reserved now even though the supported default has trap_percentage: 0.
TRAP_ITEMS: tuple[ItemRecord, ...] = (
    ItemRecord("Sandstorm Trap", 743_013_000, "trap", "future_trap", 0),
    ItemRecord("Low Gravity Trap", 743_013_001, "trap", "future_trap", 0),
    ItemRecord("Gun Jam Trap", 743_013_002, "trap", "future_trap", 0),
    ItemRecord("Eco Leak Trap", 743_013_003, "trap", "future_trap", 0),
    ItemRecord("Vehicle Wobble Trap", 743_013_004, "trap", "future_trap", 0),
)


FIRST_RELEASE_ITEMS = PROGRESSION_ITEMS + USEFUL_ITEMS + FILLER_ITEMS + TRAP_ITEMS


STORY_COMPLETION_LOCATIONS: tuple[LocationRecord, ...] = (
    LocationRecord(
        "Complete Mission: Complete Arena Training",
        743_001_010,
        "story_completion",
        native_task_id=10,
    ),
    LocationRecord(
        "Complete Mission: Earn 1st War Amulet",
        743_001_011,
        "story_completion",
        native_task_id=11,
    ),
    LocationRecord(
        "Complete Mission: Catch Kanga-Rats",
        743_001_012,
        "story_completion",
        native_task_id=12,
    ),
    LocationRecord(
        "Complete Mission: Unlock Satellite",
        743_001_013,
        "story_completion",
        native_task_id=13,
    ),
    LocationRecord(
        "Complete Mission: Learn to Drive a Vehicle",
        743_001_014,
        "story_completion",
        native_task_id=14,
    ),
    LocationRecord(
        "Complete Mission: Beat Kleiver in Desert Race",
        743_001_015,
        "story_completion",
        native_task_id=15,
    ),
    LocationRecord(
        "Complete Mission: Race for Artifacts",
        743_001_016,
        "story_completion",
        native_task_id=16,
    ),
    LocationRecord(
        "Complete Mission: Beat Monks in Leaper Race",
        743_001_017,
        "story_completion",
        native_task_id=17,
    ),
    LocationRecord(
        "Complete Mission: Destroy Metal Head Beasts",
        743_001_018,
        "story_completion",
        native_task_id=18,
    ),
    LocationRecord(
        "Complete Mission: Earn 2nd War Amulet",
        743_001_019,
        "story_completion",
        native_task_id=19,
    ),
    LocationRecord(
        "Complete Mission: Corral Wild Leapers",
        743_001_020,
        "story_completion",
        native_task_id=20,
    ),
    LocationRecord(
        "Complete Mission: Rescue Wastelanders",
        743_001_021,
        "story_completion",
        native_task_id=21,
    ),
    LocationRecord(
        "Complete Mission: Beat Turret Challenge",
        743_001_022,
        "story_completion",
        native_task_id=22,
    ),
    LocationRecord(
        "Complete Mission: Defeat Marauders in Arena",
        743_001_023,
        "story_completion",
        native_task_id=23,
    ),
    LocationRecord(
        "Complete Mission: Destroy Eggs in Nest",
        743_001_024,
        "story_completion",
        native_task_id=24,
    ),
    LocationRecord(
        "Complete Mission: Climb Monk Temple Tower",
        743_001_025,
        "story_completion",
        native_task_id=25,
    ),
    LocationRecord(
        "Complete Mission: Glide to Volcano",
        743_001_026,
        "story_completion",
        native_task_id=26,
    ),
    LocationRecord(
        "Complete Mission: Find Satellite in Volcano",
        743_001_027,
        "story_completion",
        native_task_id=27,
    ),
    LocationRecord(
        "Complete Mission: Find Oracle in Monk Temple",
        743_001_028,
        "story_completion",
        native_task_id=28,
    ),
    LocationRecord(
        "Complete Mission: Defend Ashelin at Oasis",
        743_001_029,
        "story_completion",
        native_task_id=29,
    ),
    LocationRecord(
        "Complete Mission: Complete Monk Temple Tests",
        743_001_030,
        "story_completion",
        native_task_id=30,
    ),
    LocationRecord(
        "Complete Mission: Travel Through Catacomb Subrails",
        743_001_031,
        "story_completion",
        native_task_id=31,
    ),
    LocationRecord(
        "Complete Mission: Explore Eco Mine",
        743_001_032,
        "story_completion",
        native_task_id=32,
    ),
    LocationRecord(
        "Complete Mission: Escort Bomb Train",
        743_001_033,
        "story_completion",
        native_task_id=33,
    ),
    LocationRecord(
        "Complete Mission: Defeat Veger's Precursor Robot",
        743_001_034,
        "story_completion",
        native_task_id=34,
    ),
    LocationRecord(
        "Complete Mission: Reach Port via Sewer",
        743_001_035,
        "story_completion",
        native_task_id=35,
    ),
    LocationRecord(
        "Complete Mission: Destroy Incoming Blast Bots",
        743_001_037,
        "story_completion",
        native_task_id=37,
    ),
    LocationRecord(
        "Complete Mission: Destroy Barrier with Missile",
        743_001_038,
        "story_completion",
        native_task_id=38,
    ),
    LocationRecord(
        "Complete Mission: Beat Gun Course 1",
        743_001_039,
        "story_completion",
        native_task_id=39,
    ),
    LocationRecord(
        "Complete Mission: Destroy Sniper Cannons",
        743_001_040,
        "story_completion",
        native_task_id=40,
    ),
    LocationRecord(
        "Complete Mission: Reach Metal Head Area via Sewer",
        743_001_041,
        "story_completion",
        native_task_id=41,
    ),
    LocationRecord(
        "Complete Mission: Destroy Dark Eco Tanks",
        743_001_042,
        "story_completion",
        native_task_id=42,
    ),
    LocationRecord(
        "Complete Mission: Kill Dark Plants in Forest",
        743_001_043,
        "story_completion",
        native_task_id=43,
    ),
    LocationRecord(
        "Complete Mission: Destroy Eco Grid with Jinx",
        743_001_044,
        "story_completion",
        native_task_id=44,
    ),
    LocationRecord(
        "Complete Mission: Hijack Eco Vehicle",
        743_001_045,
        "story_completion",
        native_task_id=45,
    ),
    LocationRecord(
        "Complete Mission: Defend Port from Attack",
        743_001_046,
        "story_completion",
        native_task_id=46,
    ),
    LocationRecord(
        "Complete Mission: Beat Gun Course 2",
        743_001_047,
        "story_completion",
        native_task_id=47,
    ),
    LocationRecord(
        "Complete Mission: Break Barrier with Blast Bot",
        743_001_048,
        "story_completion",
        native_task_id=48,
    ),
    LocationRecord(
        "Complete Mission: Defend HQ from Attack",
        743_001_049,
        "story_completion",
        native_task_id=49,
    ),
    LocationRecord(
        "Complete Mission: Find Switch in Sewers",
        743_001_050,
        "story_completion",
        native_task_id=50,
    ),
    LocationRecord(
        "Complete Mission: Find Cipher in Eco Grid",
        743_001_051,
        "story_completion",
        native_task_id=51,
    ),
    LocationRecord(
        "Complete Mission: Race for More Artifacts",
        743_001_052,
        "story_completion",
        native_task_id=52,
    ),
    LocationRecord(
        "Complete Mission: Destroy Metal-pedes in Nest",
        743_001_053,
        "story_completion",
        native_task_id=53,
    ),
    LocationRecord(
        "Complete Mission: Chase Down Metal Head Beasts",
        743_001_054,
        "story_completion",
        native_task_id=54,
    ),
    LocationRecord(
        "Complete Mission: Defend Spargus Front Gate",
        743_001_055,
        "story_completion",
        native_task_id=55,
    ),
    LocationRecord(
        "Complete Mission: Take Out Marauder Stronghold",
        743_001_056,
        "story_completion",
        native_task_id=56,
    ),
    LocationRecord(
        "Complete Mission: Beat Pillar Ring Challenges",
        743_001_057,
        "story_completion",
        native_task_id=57,
    ),
    LocationRecord(
        "Complete Mission: Destroy War Factory Defenses",
        743_001_058,
        "story_completion",
        native_task_id=58,
    ),
    LocationRecord(
        "Complete Mission: Explore War Factory",
        743_001_059,
        "story_completion",
        native_task_id=59,
    ),
    LocationRecord(
        "Complete Mission: Defeat Cyber-Errol",
        743_001_060,
        "story_completion",
        native_task_id=60,
    ),
    LocationRecord(
        "Complete Mission: Rescue Seem at Temple",
        743_001_061,
        "story_completion",
        native_task_id=61,
    ),
    LocationRecord(
        "Complete Mission: Defend Spargus",
        743_001_062,
        "story_completion",
        native_task_id=62,
    ),
    LocationRecord(
        "Complete Mission: Activate Astro-Viewer",
        743_001_063,
        "story_completion",
        native_task_id=63,
    ),
    LocationRecord(
        "Complete Mission: Destroy Dark Ship Shield",
        743_001_064,
        "story_completion",
        native_task_id=64,
    ),
    LocationRecord(
        "Complete Mission: Blow Open Tower Door",
        743_001_065,
        "story_completion",
        native_task_id=65,
    ),
    LocationRecord(
        "Complete Mission: Destroy Metal Head Tower",
        743_001_066,
        "story_completion",
        native_task_id=66,
    ),
    LocationRecord(
        "Complete Mission: Reach Catacombs via Palace Ruins",
        743_001_067,
        "story_completion",
        native_task_id=67,
    ),
    LocationRecord(
        "Complete Mission: Break Through Ruins",
        743_001_068,
        "story_completion",
        native_task_id=68,
    ),
    LocationRecord(
        "Complete Mission: Reach Precursor Core",
        743_001_069,
        "story_completion",
        native_task_id=69,
    ),
    LocationRecord(
        "Complete Mission: Destroy Dark Ship",
        743_001_070,
        "story_completion",
        native_task_id=70,
    ),
    LocationRecord(
        "Complete Mission: Destroy Final Boss",
        743_001_071,
        "story_completion",
        native_task_id=71,
    ),
)


MAJOR_REWARD_LOCATIONS: tuple[LocationRecord, ...] = (
    LocationRecord(
        "Reward: Scatter Gun Introduction",
        743_020_010,
        "major_reward",
        native_task_id=11,
        native_node_id=10,
    ),
    LocationRecord(
        "Reward: Dark Bomb and Dark Blast Lesson",
        743_020_011,
        "major_reward",
        native_task_id=11,
        native_node_id=11,
    ),
    LocationRecord(
        "Reward: First War Amulet and Blaster",
        743_020_012,
        "major_reward",
        native_task_id=11,
        native_node_id=12,
    ),
    LocationRecord(
        "Reward: Tough Puppy Introduction",
        743_020_023,
        "major_reward",
        native_task_id=14,
        native_node_id=23,
    ),
    LocationRecord(
        "Reward: First Armor Upgrade",
        743_020_036,
        "major_reward",
        native_task_id=16,
        native_node_id=36,
    ),
    LocationRecord(
        "Reward: Sand Shark Introduction",
        743_020_039,
        "major_reward",
        native_task_id=18,
        native_node_id=39,
    ),
    LocationRecord(
        "Reward: Wave Concussor and Red Ammo Upgrade",
        743_020_041,
        "major_reward",
        native_task_id=19,
        native_node_id=41,
    ),
    LocationRecord(
        "Reward: Second War Amulet and Beam Reflexor",
        743_020_044,
        "major_reward",
        native_task_id=19,
        native_node_id=44,
    ),
    LocationRecord(
        "Reward: Dune Hopper",
        743_020_048,
        "major_reward",
        native_task_id=20,
        native_node_id=48,
    ),
    LocationRecord(
        "Reward: Vulcan Fury Introduction",
        743_020_063,
        "major_reward",
        native_task_id=23,
        native_node_id=63,
    ),
    LocationRecord(
        "Reward: Gila Stomper Introduction",
        743_020_067,
        "major_reward",
        native_task_id=24,
        native_node_id=67,
    ),
    LocationRecord(
        "Reward: Invisibility Statues",
        743_020_084,
        "major_reward",
        native_task_id=27,
        native_node_id=84,
    ),
    LocationRecord(
        "Reward: Light Regeneration Lesson",
        743_020_093,
        "major_reward",
        native_task_id=28,
        native_node_id=93,
    ),
    LocationRecord(
        "Reward: Jetboard and Seal of Mar",
        743_020_098,
        "major_reward",
        native_task_id=29,
        native_node_id=98,
    ),
    LocationRecord(
        "Reward: Flash Freeze Lesson",
        743_020_102,
        "major_reward",
        native_task_id=30,
        native_node_id=102,
    ),
    LocationRecord(
        "Reward: Light Shield",
        743_020_109,
        "major_reward",
        native_task_id=31,
        native_node_id=109,
    ),
    LocationRecord(
        "Reward: Second Armor Upgrade",
        743_020_113,
        "major_reward",
        native_task_id=32,
        native_node_id=113,
    ),
    LocationRecord(
        "Reward: Arc Wielder and Blue Ammo Upgrade",
        743_020_119,
        "major_reward",
        native_task_id=34,
        native_node_id=119,
    ),
    LocationRecord(
        "Reward: Port-Industrial Pass",
        743_020_129,
        "major_reward",
        native_task_id=38,
        native_node_id=129,
    ),
    LocationRecord(
        "Reward: Gyro Burster and Yellow Ammo Upgrade",
        743_020_132,
        "major_reward",
        native_task_id=39,
        native_node_id=132,
    ),
    LocationRecord(
        "Reward: Dark Strike Lesson",
        743_020_145,
        "major_reward",
        native_task_id=42,
        native_node_id=145,
    ),
    LocationRecord(
        "Reward: Port-Metal Head Pass",
        743_020_146,
        "major_reward",
        native_task_id=42,
        native_node_id=146,
    ),
    LocationRecord(
        "Reward: Third Armor Upgrade",
        743_020_149,
        "major_reward",
        native_task_id=43,
        native_node_id=149,
    ),
    LocationRecord(
        "Reward: Needle Lazer and Industrial Pass",
        743_020_152,
        "major_reward",
        native_task_id=44,
        native_node_id=152,
    ),
    LocationRecord(
        "Reward: Plasmite RPG and Red Ammo Upgrade",
        743_020_162,
        "major_reward",
        native_task_id=47,
        native_node_id=162,
    ),
    LocationRecord(
        "Reward: Peace Maker and Slums Pass",
        743_020_167,
        "major_reward",
        native_task_id=48,
        native_node_id=167,
    ),
    LocationRecord(
        "Reward: Cipher Glyph",
        743_020_175,
        "major_reward",
        native_task_id=51,
        native_node_id=175,
    ),
    LocationRecord(
        "Reward: Holo Cube",
        743_020_182,
        "major_reward",
        native_task_id=52,
        native_node_id=182,
    ),
    LocationRecord(
        "Reward: Quantum Reflector",
        743_020_191,
        "major_reward",
        native_task_id=54,
        native_node_id=191,
    ),
    LocationRecord(
        "Reward: Beam Generator",
        743_020_195,
        "major_reward",
        native_task_id=55,
        native_node_id=195,
    ),
    LocationRecord(
        "Reward: Precursor Prism",
        743_020_200,
        "major_reward",
        native_task_id=56,
        native_node_id=200,
    ),
    LocationRecord(
        "Reward: Mass Imploder and Dark Ammo Upgrade",
        743_020_232,
        "major_reward",
        native_task_id=61,
        native_node_id=232,
    ),
    LocationRecord(
        "Reward: Light Flight Lesson",
        743_020_238,
        "major_reward",
        native_task_id=61,
        native_node_id=238,
    ),
    LocationRecord(
        "Reward: Time Map",
        743_020_240,
        "major_reward",
        native_task_id=61,
        native_node_id=240,
    ),
    LocationRecord(
        "Reward: Third War Amulet and Fourth Armor Upgrade",
        743_020_243,
        "major_reward",
        native_task_id=62,
        native_node_id=243,
    ),
    LocationRecord(
        "Reward: Super Nova and Dark Ammo Upgrade",
        743_020_252,
        "major_reward",
        native_task_id=65,
        native_node_id=252,
    ),
    LocationRecord(
        "Reward: Slums-Generator Pass",
        743_020_256,
        "major_reward",
        native_task_id=67,
        native_node_id=256,
    ),
    LocationRecord(
        "Reward: Ram 'Rod / Slam Dozer",
        743_020_259,
        "major_reward",
        native_task_id=68,
        native_node_id=259,
    ),
)


SELECTED_SIDE_LOCATIONS: tuple[LocationRecord, ...] = (
    LocationRecord(
        "Complete Challenge: Desert Ring Challenge 1",
        743_001_114,
        "selected_side_challenge",
        native_task_id=114,
    ),
    LocationRecord(
        "Complete Challenge: Desert Ring Challenge 2",
        743_001_115,
        "selected_side_challenge",
        native_task_id=115,
    ),
    LocationRecord(
        "Complete Challenge: Spargus Ring Challenge 3",
        743_001_116,
        "selected_side_challenge",
        native_task_id=116,
    ),
    LocationRecord(
        "Complete Challenge: Spargus Ring Challenge 4",
        743_001_117,
        "selected_side_challenge",
        native_task_id=117,
    ),
    LocationRecord(
        "Complete Challenge: Haven Ring Challenge 5",
        743_001_118,
        "selected_side_challenge",
        native_task_id=118,
    ),
    LocationRecord(
        "Complete Challenge: Haven Ring Challenge 6",
        743_001_119,
        "selected_side_challenge",
        native_task_id=119,
    ),
    LocationRecord(
        "Complete Challenge: Egg Spider Challenge",
        743_001_120,
        "selected_side_challenge",
        native_task_id=120,
    ),
    LocationRecord(
        "Complete Challenge: Desert Spirit Chase",
        743_001_121,
        "selected_side_challenge",
        native_task_id=121,
    ),
    LocationRecord(
        "Complete Challenge: Spargus Spirit Chase",
        743_001_122,
        "selected_side_challenge",
        native_task_id=122,
    ),
    LocationRecord(
        "Complete Challenge: Haven Spirit Chase",
        743_001_123,
        "selected_side_challenge",
        native_task_id=123,
    ),
    LocationRecord(
        "Complete Challenge: Desert Timer Chase",
        743_001_124,
        "selected_side_challenge",
        native_task_id=124,
    ),
    LocationRecord(
        "Complete Challenge: Spargus Timer Chase",
        743_001_125,
        "selected_side_challenge",
        native_task_id=125,
    ),
    LocationRecord(
        "Complete Challenge: Single Air-Time Challenge",
        743_001_126,
        "selected_side_challenge",
        native_task_id=126,
    ),
    LocationRecord(
        "Complete Challenge: Total Air-Time Challenge",
        743_001_127,
        "selected_side_challenge",
        native_task_id=127,
        default_excluded=True,
    ),
    LocationRecord(
        "Complete Challenge: Single Jump-Distance Challenge",
        743_001_128,
        "selected_side_challenge",
        native_task_id=128,
    ),
    LocationRecord(
        "Complete Challenge: Total Jump-Distance Challenge",
        743_001_129,
        "selected_side_challenge",
        native_task_id=129,
        default_excluded=True,
    ),
    LocationRecord(
        "Complete Challenge: Vehicle Roll-Count Challenge",
        743_001_130,
        "selected_side_challenge",
        native_task_id=130,
        default_excluded=True,
    ),
    LocationRecord(
        "Complete Challenge: Wasteland Time Trial",
        743_001_131,
        "selected_side_challenge",
        native_task_id=131,
        default_excluded=True,
    ),
    LocationRecord(
        "Complete Challenge: Wasteland Rally",
        743_001_132,
        "selected_side_challenge",
        native_task_id=132,
        default_excluded=True,
    ),
    LocationRecord(
        "Complete Challenge: Port Attack Challenge",
        743_001_133,
        "selected_side_challenge",
        native_task_id=133,
    ),
    LocationRecord(
        "Complete Challenge: Wastelander Rescue Challenge",
        743_001_134,
        "selected_side_challenge",
        native_task_id=134,
    ),
    LocationRecord(
        "Complete Challenge: Gun Course Free Play",
        743_001_135,
        "selected_side_challenge",
        native_task_id=135,
    ),
    LocationRecord(
        "Complete Challenge: Jetboard Challenge",
        743_001_136,
        "selected_side_challenge",
        native_task_id=136,
        default_excluded=True,
    ),
    LocationRecord(
        "Complete Challenge: Destroy Interceptors Challenge",
        743_001_137,
        "selected_side_challenge",
        native_task_id=137,
    ),
)


ORB_THRESHOLD_LOCATIONS: tuple[LocationRecord, ...] = (
    LocationRecord(
        "Precursor Orb Threshold: 25",
        743_030_025,
        "precursor_orb_threshold",
        orb_threshold=25,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 50",
        743_030_050,
        "precursor_orb_threshold",
        orb_threshold=50,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 75",
        743_030_075,
        "precursor_orb_threshold",
        orb_threshold=75,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 100",
        743_030_100,
        "precursor_orb_threshold",
        orb_threshold=100,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 125",
        743_030_125,
        "precursor_orb_threshold",
        orb_threshold=125,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 150",
        743_030_150,
        "precursor_orb_threshold",
        orb_threshold=150,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 175",
        743_030_175,
        "precursor_orb_threshold",
        orb_threshold=175,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 200",
        743_030_200,
        "precursor_orb_threshold",
        orb_threshold=200,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 225",
        743_030_225,
        "precursor_orb_threshold",
        orb_threshold=225,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 250",
        743_030_250,
        "precursor_orb_threshold",
        orb_threshold=250,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 275",
        743_030_275,
        "precursor_orb_threshold",
        orb_threshold=275,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 300",
        743_030_300,
        "precursor_orb_threshold",
        orb_threshold=300,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 325",
        743_030_325,
        "precursor_orb_threshold",
        orb_threshold=325,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 350",
        743_030_350,
        "precursor_orb_threshold",
        orb_threshold=350,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 375",
        743_030_375,
        "precursor_orb_threshold",
        orb_threshold=375,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 400",
        743_030_400,
        "precursor_orb_threshold",
        orb_threshold=400,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 425",
        743_030_425,
        "precursor_orb_threshold",
        orb_threshold=425,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 450",
        743_030_450,
        "precursor_orb_threshold",
        orb_threshold=450,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 475",
        743_030_475,
        "precursor_orb_threshold",
        orb_threshold=475,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 500",
        743_030_500,
        "precursor_orb_threshold",
        orb_threshold=500,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 525",
        743_030_525,
        "precursor_orb_threshold",
        orb_threshold=525,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 550",
        743_030_550,
        "precursor_orb_threshold",
        orb_threshold=550,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 575",
        743_030_575,
        "precursor_orb_threshold",
        orb_threshold=575,
        default_excluded=True,
    ),
    LocationRecord(
        "Precursor Orb Threshold: 600",
        743_030_600,
        "precursor_orb_threshold",
        orb_threshold=600,
        default_excluded=True,
    ),
)


FIRST_RELEASE_LOCATIONS = (
    STORY_COMPLETION_LOCATIONS
    + MAJOR_REWARD_LOCATIONS
    + SELECTED_SIDE_LOCATIONS
    + ORB_THRESHOLD_LOCATIONS
)


MISSIONS: tuple[MissionRecord, ...] = (
    MissionRecord(6, "city-start", "city-start", "Opening", "task-6-opening"),
    MissionRecord(
        7,
        "desert-interceptors",
        "desert-interceptors",
        "Desert Interceptors",
        "task-7-desert-interceptors",
    ),
    MissionRecord(
        8,
        "desert-vehicle-training-1",
        "desert-vehicle-training-1",
        "Vehicle Tutorial 1",
        "task-8-vehicle-tutorial-1",
    ),
    MissionRecord(
        9,
        "desert-vehicle-training-2",
        "desert-vehicle-training-2",
        "Vehicle Tutorial 2",
        "task-9-vehicle-tutorial-2",
    ),
    MissionRecord(
        10,
        "arena-training-1",
        "arena-training-1",
        "Complete Arena Training",
        "task-10-arena-training",
    ),
    MissionRecord(
        11,
        "arena-fight-1",
        "arena-fight-1",
        "Earn 1st War Amulet",
        "task-11-power-lessons",
    ),
    MissionRecord(
        12, "wascity-chase", "wascity-chase", "Catch Kanga-Rats", "task-12-leaper-chase"
    ),
    MissionRecord(
        13,
        "wascity-pre-game",
        "wascity-pre-game",
        "Unlock Satellite",
        "task-13-satellite-turret",
    ),
    MissionRecord(
        14,
        "desert-turtle-training",
        "desert-turtle-training",
        "Learn to Drive a Vehicle",
        "task-14-tough-puppy-training",
    ),
    MissionRecord(
        15,
        "desert-course-race",
        "desert-course-race",
        "Beat Kleiver in Desert Race",
        "task-15-desert-race",
    ),
    MissionRecord(
        16,
        "desert-artifact-race-1",
        "desert-artifact-race-1",
        "Race for Artifacts",
        "task-16-artifact-race",
    ),
    MissionRecord(
        17,
        "wascity-leaper-race",
        "wascity-leaper-race",
        "Beat Monks in Leaper Race",
        "task-17-leaper-race",
    ),
    MissionRecord(
        18,
        "desert-hover",
        "desert-hover",
        "Destroy Metal Head Beasts",
        "task-18-sand-shark",
    ),
    MissionRecord(
        19,
        "arena-fight-2",
        "arena-fight-2",
        "Earn 2nd War Amulet",
        "task-19-gun-training",
    ),
    MissionRecord(
        20,
        "desert-catch-lizards",
        "desert-catch-lizards",
        "Corral Wild Leapers",
        "task-20-leaper-corral",
    ),
    MissionRecord(
        21,
        "desert-rescue",
        "desert-rescue",
        "Rescue Wastelanders",
        "task-21-rescue-satellite",
    ),
    MissionRecord(
        22,
        "wascity-gungame",
        "wascity-gungame",
        "Beat Turret Challenge",
        "task-22-turret-challenge",
    ),
    MissionRecord(
        23,
        "arena-fight-3",
        "arena-fight-3",
        "Defeat Marauders in Arena",
        "task-23-gun-training",
    ),
    MissionRecord(
        24, "nest-eggs", "nest-eggs", "Destroy Eggs in Nest", "task-24-gila-stomper"
    ),
    MissionRecord(25, "temple-climb", "temple-climb", "Climb Monk Temple Tower"),
    MissionRecord(
        26, "desert-glide", "desert-glide", "Glide to Volcano", "task-26-flut-flut"
    ),
    MissionRecord(
        27,
        "volcano-darkeco",
        "volcano-darkeco",
        "Find Satellite in Volcano",
        "task-27-volcano-daxter-invisibility",
    ),
    MissionRecord(
        28,
        "temple-oracle",
        "temple-oracle",
        "Find Oracle in Monk Temple",
        "task-28-light-regeneration",
    ),
    MissionRecord(
        29,
        "desert-oasis-defense",
        "desert-oasis-defense",
        "Defend Ashelin at Oasis",
        "task-29-oasis-defense",
    ),
    MissionRecord(
        30,
        "temple-tests",
        "temple-tests",
        "Complete Monk Temple Tests",
        "task-30-flash-freeze",
        "task-30-seal-portal",
    ),
    MissionRecord(
        31,
        "comb-travel",
        "comb-travel",
        "Travel Through Catacomb Subrails",
        "task-31-subrail",
    ),
    MissionRecord(
        32, "mine-explore", "mine-explore", "Explore Eco Mine", "task-32-mine-sequence"
    ),
    MissionRecord(
        33, "mine-blow", "mine-blow", "Escort Bomb Train", "task-33-bomb-train"
    ),
    MissionRecord(
        34,
        "mine-boss",
        "mine-boss",
        "Defeat Veger's Precursor Robot",
        "task-34-precursor-robot",
    ),
    MissionRecord(35, "sewer-met-hum", "sewer-met-hum", "Reach Port via Sewer"),
    MissionRecord(
        36,
        "city-vehicle-training",
        "city-vehicle-training",
        "Haven Hover-Zone Tutorial",
        "task-36-haven-vehicle-tutorial",
    ),
    MissionRecord(
        37,
        "city-port-fight",
        "city-port-fight",
        "Destroy Incoming Blast Bots",
        "task-37-blast-bots",
    ),
    MissionRecord(
        38,
        "city-port-attack",
        "city-port-attack",
        "Destroy Barrier with Missile",
        "task-38-missile",
    ),
    MissionRecord(
        39,
        "city-gun-course-1",
        "city-gun-course-1",
        "Beat Gun Course 1",
        "task-39-gun-course",
    ),
    MissionRecord(
        40, "city-sniper-fight", "city-sniper-fight", "Destroy Sniper Cannons"
    ),
    MissionRecord(
        41, "sewer-kg-met", "sewer-kg-met", "Reach Metal Head Area via Sewer"
    ),
    MissionRecord(
        42,
        "city-destroy-darkeco",
        "city-destroy-darkeco",
        "Destroy Dark Eco Tanks",
        "task-42-dark-strike",
    ),
    MissionRecord(
        43,
        "forest-kill-plants",
        "forest-kill-plants",
        "Kill Dark Plants in Forest",
        "task-43-board-trail",
    ),
    MissionRecord(
        44,
        "city-destroy-grid",
        "city-destroy-grid",
        "Destroy Eco Grid with Jinx",
        "task-44-jinx-vehicle",
    ),
    MissionRecord(
        45,
        "city-hijack-vehicle",
        "city-hijack-vehicle",
        "Hijack Eco Vehicle",
        "task-45-eco-vehicle",
    ),
    MissionRecord(
        46,
        "city-port-assault",
        "city-port-assault",
        "Defend Port from Attack",
        "task-46-port-defense",
    ),
    MissionRecord(
        47,
        "city-gun-course-2",
        "city-gun-course-2",
        "Beat Gun Course 2",
        "task-47-gun-course",
    ),
    MissionRecord(
        48,
        "city-blow-barricade",
        "city-blow-barricade",
        "Break Barrier with Blast Bot",
        "task-48-blast-bot",
    ),
    MissionRecord(49, "city-protect-hq", "city-protect-hq", "Defend HQ from Attack"),
    MissionRecord(50, "sewer-hum-kg", "sewer-hum-kg", "Find Switch in Sewers"),
    MissionRecord(
        51,
        "city-power-game",
        "city-power-game",
        "Find Cipher in Eco Grid",
        "task-51-eco-grid",
    ),
    MissionRecord(
        52,
        "desert-artifact-race-2",
        "desert-artifact-race-2",
        "Race for More Artifacts",
        "task-52-artifact-race",
    ),
    MissionRecord(
        53,
        "nest-hunt",
        "nest-hunt",
        "Destroy Metal-pedes in Nest",
        "task-53-gila-stomper",
    ),
    MissionRecord(
        54,
        "desert-beast-battle",
        "desert-beast-battle",
        "Chase Down Metal Head Beasts",
        "task-54-beast-chase",
    ),
    MissionRecord(
        55, "desert-jump-mission", "desert-jump-mission", "Defend Spargus Front Gate"
    ),
    MissionRecord(
        56,
        "desert-chase-marauders",
        "desert-chase-marauders",
        "Take Out Marauder Stronghold",
    ),
    MissionRecord(
        57, "forest-ring-chase", "forest-ring-chase", "Beat Pillar Ring Challenges"
    ),
    MissionRecord(
        58,
        "factory-sky-battle",
        "factory-sky-battle",
        "Destroy War Factory Defenses",
        "task-58-fighter",
    ),
    MissionRecord(
        59,
        "factory-assault",
        "factory-assault",
        "Explore War Factory",
        "task-59-factory-daxter-vehicle",
    ),
    MissionRecord(
        60, "factory-boss", "factory-boss", "Defeat Cyber-Errol", "task-60-factory-boss"
    ),
    MissionRecord(
        61,
        "temple-defend",
        "temple-defend",
        "Rescue Seem at Temple",
        "task-61-light-flight",
    ),
    MissionRecord(
        62,
        "wascity-defend",
        "wascity-defend",
        "Defend Spargus",
        "task-62-spargus-turret",
    ),
    MissionRecord(
        63,
        "forest-turn-on-machine",
        "forest-turn-on-machine",
        "Activate Astro-Viewer",
        "task-63-astro-viewer-combat",
        "task-63-astro-viewer-artifacts",
    ),
    MissionRecord(
        64,
        "precursor-tour",
        "precursor-tour",
        "Destroy Dark Ship Shield",
        "task-64-dark-maker-suit",
    ),
    MissionRecord(
        65,
        "city-blow-tower",
        "city-blow-tower",
        "Blow Open Tower Door",
        "task-65-mounted-shooter",
    ),
    MissionRecord(66, "tower-destroy", "tower-destroy", "Destroy Metal Head Tower"),
    MissionRecord(
        67,
        "palace-ruins-patrol",
        "palace-ruins-patrol",
        "Reach Catacombs via Palace Ruins",
    ),
    MissionRecord(
        68,
        "palace-ruins-attack",
        "palace-ruins-attack",
        "Break Through Ruins",
        "task-68-slam-dozer",
    ),
    MissionRecord(
        69,
        "comb-wild-ride",
        "comb-wild-ride",
        "Reach Precursor Core",
        "task-69-subrail",
    ),
    MissionRecord(
        70, "precursor-destroy-ship", "precursor-destroy-ship", "Destroy Dark Ship"
    ),
    MissionRecord(
        71,
        "desert-final-boss",
        "desert-final-boss",
        "Destroy Final Boss",
        "task-71-finale-loadout",
    ),
    MissionRecord(72, "city-win", "city-win", "City Win"),
    # Task 88 keeps native ID 88 while normalizing the source enum/node alias mismatch.
    MissionRecord(
        88,
        "desert-bbush-get-to-19",
        "wascity-bbush-get-to-19",
        "Orb Hunt / Get-To Challenge 16",
    ),
    MissionRecord(
        114, "desert-bbush-ring-1", "desert-bbush-ring-1", "Desert Ring Challenge 1"
    ),
    MissionRecord(
        115, "desert-bbush-ring-2", "desert-bbush-ring-2", "Desert Ring Challenge 2"
    ),
    MissionRecord(
        116,
        "wascity-bbush-ring-3",
        "wascity-bbush-ring-3",
        "Spargus Ring Challenge 3",
        "task-116-race-vehicle",
    ),
    MissionRecord(
        117,
        "wascity-bbush-ring-4",
        "wascity-bbush-ring-4",
        "Spargus Ring Challenge 4",
        "task-117-race-vehicle",
    ),
    MissionRecord(
        118,
        "city-bbush-ring-5",
        "city-bbush-ring-5",
        "Haven Ring Challenge 5",
        "task-118-haven-vehicle",
    ),
    MissionRecord(
        119,
        "city-bbush-ring-6",
        "city-bbush-ring-6",
        "Haven Ring Challenge 6",
        "task-119-haven-vehicle",
    ),
    MissionRecord(
        120,
        "desert-bbush-egg-spider-1",
        "desert-bbush-egg-spider-1",
        "Egg Spider Challenge",
    ),
    MissionRecord(
        121,
        "desert-bbush-spirit-chase-1",
        "desert-bbush-spirit-chase-1",
        "Desert Spirit Chase",
    ),
    MissionRecord(
        122,
        "wascity-bbush-spirit-chase-2",
        "wascity-bbush-spirit-chase-2",
        "Spargus Spirit Chase",
    ),
    MissionRecord(
        123,
        "city-bbush-spirit-chase-3",
        "city-bbush-spirit-chase-3",
        "Haven Spirit Chase",
        "task-123-haven-vehicle",
    ),
    MissionRecord(
        124,
        "desert-bbush-timer-chase-1",
        "desert-bbush-timer-chase-1",
        "Desert Timer Chase",
    ),
    MissionRecord(
        125,
        "wascity-bbush-timer-chase-2",
        "wascity-bbush-timer-chase-2",
        "Spargus Timer Chase",
    ),
    MissionRecord(
        126,
        "desert-bbush-air-time",
        "desert-bbush-air-time",
        "Single Air-Time Challenge",
    ),
    MissionRecord(
        127,
        "desert-bbush-total-air-time",
        "desert-bbush-total-air-time",
        "Total Air-Time Challenge",
    ),
    MissionRecord(
        128,
        "desert-bbush-jump-distance",
        "desert-bbush-jump-distance",
        "Single Jump-Distance Challenge",
    ),
    MissionRecord(
        129,
        "desert-bbush-total-jump-distance",
        "desert-bbush-total-jump-distance",
        "Total Jump-Distance Challenge",
    ),
    MissionRecord(
        130,
        "desert-bbush-roll-count",
        "desert-bbush-roll-count",
        "Vehicle Roll-Count Challenge",
    ),
    MissionRecord(
        131,
        "desert-bbush-time-trial-1",
        "desert-bbush-time-trial-1",
        "Wasteland Time Trial",
    ),
    MissionRecord(132, "desert-bbush-rally", "desert-bbush-rally", "Wasteland Rally"),
    MissionRecord(
        133,
        "city-bbush-port-attack",
        "city-bbush-port-attack",
        "Port Attack Challenge",
        "task-133-port-attack",
    ),
    MissionRecord(
        134,
        "desert-rescue-bbush",
        "desert-rescue-bbush",
        "Wastelander Rescue Challenge",
    ),
    MissionRecord(
        135,
        "city-gun-course-play-for-fun",
        "city-gun-course-play-for-fun",
        "Gun Course Free Play",
        "task-135-gun-course",
    ),
    MissionRecord(
        136, "city-jetboard-bbush", "city-jetboard-bbush", "Jetboard Challenge"
    ),
    MissionRecord(
        137,
        "desert-bbush-destroy-interceptors",
        "desert-bbush-destroy-interceptors",
        "Destroy Interceptors Challenge",
    ),
)


BOOTSTRAP_PROFILES: tuple[MissionProfileRecord, ...] = tuple(
    MissionProfileRecord(mission.bootstrap_profile_id, mission.task_id)
    for mission in MISSIONS
    if mission.bootstrap_profile_id is not None
)
SHADOW_STORY_PROFILES: tuple[MissionProfileRecord, ...] = tuple(
    MissionProfileRecord(mission.shadow_profile_id, mission.task_id)
    for mission in MISSIONS
    if mission.shadow_profile_id is not None
)


MISSION_COMPLETION_EVENTS: tuple[EventRecord, ...] = tuple(
    EventRecord(
        f"Mission Complete Event Location {mission.task_id}",
        f"Mission Complete Event {mission.task_id}",
        mission.task_id,
    )
    for mission in MISSIONS
    if (6 <= mission.task_id <= 35) or (37 <= mission.task_id <= 71)
)
VICTORY_EVENT = EventRecord("Victory Event Location", "Victory", 72)
EVENT_LOCATIONS = MISSION_COMPLETION_EVENTS + (VICTORY_EVENT,)


def _build_reservations(
    legacy_records: Iterable[FrozenLegacyIdRecord], table_name: str
) -> tuple[ReservedIdRecord, ...]:
    return tuple(
        sorted(
            (
                ReservedIdRecord(
                    legacy.code,
                    legacy.legacy_name,
                    f"Retired protocol-1 {table_name} concept; permanently unavailable for reuse.",
                )
                for legacy in legacy_records
                if legacy.retained_concept is None
            ),
            key=lambda record: record.code,
        )
    )


def _retained_concepts(
    legacy_records: Iterable[FrozenLegacyIdRecord],
) -> dict[int, str]:
    retained: dict[int, str] = {}
    for legacy in legacy_records:
        if legacy.retained_concept is not None:
            retained[legacy.code] = legacy.retained_concept
    return retained


def _reject_duplicate_frozen_ids(
    legacy_records: Iterable[FrozenLegacyIdRecord], table_name: str
) -> None:
    names: set[str] = set()
    codes: set[int] = set()
    for legacy in legacy_records:
        if legacy.legacy_name in names:
            raise ValueError(
                f"Duplicate frozen legacy {table_name} name: {legacy.legacy_name!r}"
            )
        if legacy.code in codes:
            raise ValueError(f"Duplicate frozen legacy {table_name} ID {legacy.code}.")
        names.add(legacy.legacy_name)
        codes.add(legacy.code)


RESERVED_LEGACY_ITEM_IDS = _build_reservations(FROZEN_LEGACY_ITEM_IDS, "item")
RESERVED_LEGACY_LOCATION_IDS = _build_reservations(
    FROZEN_LEGACY_LOCATION_IDS, "location"
)


def _reject_duplicate_names_and_codes(
    records: Iterable[NetworkRecord], table_name: str
) -> None:
    names: dict[str, int] = {}
    codes: dict[int, str] = {}
    for record in records:
        if record.name in names:
            raise ValueError(f"Duplicate {table_name} name: {record.name!r}")
        if record.code in codes:
            raise ValueError(
                f"Duplicate {table_name} ID {record.code}: "
                f"{codes[record.code]!r} and {record.name!r}"
            )
        names[record.name] = record.code
        codes[record.code] = record.name


def validate_registry(
    items: Iterable[ItemRecord] = FIRST_RELEASE_ITEMS,
    locations: Iterable[LocationRecord] = FIRST_RELEASE_LOCATIONS,
    item_reservations: Iterable[ReservedIdRecord] = RESERVED_LEGACY_ITEM_IDS,
    location_reservations: Iterable[ReservedIdRecord] = RESERVED_LEGACY_LOCATION_IDS,
) -> None:
    """Reject ambiguous public identities and accidental legacy-ID reuse."""

    item_rows = tuple(items)
    location_rows = tuple(locations)
    item_reserved = tuple(item_reservations)
    location_reserved = tuple(location_reservations)
    _reject_duplicate_names_and_codes(item_rows, "item")
    _reject_duplicate_names_and_codes(location_rows, "location")
    _reject_duplicate_frozen_ids(FROZEN_LEGACY_ITEM_IDS, "item")
    _reject_duplicate_frozen_ids(FROZEN_LEGACY_LOCATION_IDS, "location")

    item_reserved_codes = [record.code for record in item_reserved]
    location_reserved_codes = [record.code for record in location_reserved]
    if len(item_reserved_codes) != len(set(item_reserved_codes)):
        raise ValueError("Duplicate reserved legacy item ID.")
    if len(location_reserved_codes) != len(set(location_reserved_codes)):
        raise ValueError("Duplicate reserved legacy location ID.")

    item_codes = {record.code for record in item_rows}
    location_codes = {record.code for record in location_rows}
    if item_codes & location_codes:
        raise ValueError("First-release item and location ID tables overlap.")
    if item_codes & {record.code for record in item_reserved}:
        raise ValueError("An active item reuses a reserved legacy item ID.")
    if location_codes & {record.code for record in location_reserved}:
        raise ValueError("An active location reuses a reserved legacy location ID.")
    active_codes = item_codes | location_codes
    all_reserved_codes = {record.code for record in item_reserved + location_reserved}
    if active_codes & all_reserved_codes:
        raise ValueError("An active record reuses a reserved legacy network ID.")

    expected_item_reservations = _build_reservations(FROZEN_LEGACY_ITEM_IDS, "item")
    expected_location_reservations = _build_reservations(
        FROZEN_LEGACY_LOCATION_IDS, "location"
    )
    if set(item_reserved) != set(expected_item_reservations):
        raise ValueError("Frozen legacy item reservations were changed.")
    if set(location_reserved) != set(expected_location_reservations):
        raise ValueError("Frozen legacy location reservations were changed.")

    expected_items = _retained_concepts(FROZEN_LEGACY_ITEM_IDS)
    actual_items = {
        record.code: f"{record.family}:{record.name}"
        for record in item_rows
        if record.code in expected_items
    }
    if actual_items != expected_items:
        raise ValueError("A retained legacy item concept was changed or removed.")

    expected_locations = _retained_concepts(FROZEN_LEGACY_LOCATION_IDS)
    actual_locations = {
        record.code: f"{record.family}:{record.native_task_id}"
        for record in location_rows
        if record.code in expected_locations
    }
    if actual_locations != expected_locations:
        raise ValueError("A retained legacy location concept was changed or removed.")

    frozen_item_codes = {record.code for record in FROZEN_LEGACY_ITEM_IDS}
    frozen_location_codes = {record.code for record in FROZEN_LEGACY_LOCATION_IDS}
    if frozen_item_codes != set(expected_items) | set(item_reserved_codes):
        raise ValueError("Legacy item IDs are not completely retained or reserved.")
    if frozen_location_codes != set(expected_locations) | set(location_reserved_codes):
        raise ValueError("Legacy location IDs are not completely retained or reserved.")


def validate_mission_registry(
    missions: Iterable[MissionRecord] = MISSIONS,
    bootstrap_profiles: Iterable[MissionProfileRecord] = BOOTSTRAP_PROFILES,
    shadow_profiles: Iterable[MissionProfileRecord] = SHADOW_STORY_PROFILES,
) -> None:
    """Reject ambiguous native task and mission-profile identities."""

    mission_rows = tuple(missions)
    task_ids = [mission.task_id for mission in mission_rows]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Duplicate native mission task ID.")

    known_tasks = set(task_ids)
    profile_rows = tuple(bootstrap_profiles) + tuple(shadow_profiles)
    profile_ids = [profile.profile_id for profile in profile_rows]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("Duplicate mission profile ID.")
    for profile in profile_rows:
        if profile.native_task_id not in known_tasks:
            raise ValueError(
                f"Mission profile {profile.profile_id!r} references unknown "
                f"task {profile.native_task_id}."
            )


def _serialized_records(records: Iterable[RegistryRecord]) -> list[dict]:
    return [
        asdict(record)
        for record in sorted(
            records, key=lambda row: tuple(str(value) for value in asdict(row).values())
        )
    ]


def serialize_item_registry(
    records: Iterable[ItemRecord] = FIRST_RELEASE_ITEMS,
    reservations: Iterable[ReservedIdRecord] = RESERVED_LEGACY_ITEM_IDS,
) -> bytes:
    return canonical_json_bytes(
        {
            "table_version": ITEM_TABLE_VERSION,
            "items": _serialized_records(records),
            "reserved_legacy_ids": _serialized_records(reservations),
        }
    )


def serialize_location_registry(
    records: Iterable[LocationRecord] = FIRST_RELEASE_LOCATIONS,
    reservations: Iterable[ReservedIdRecord] = RESERVED_LEGACY_LOCATION_IDS,
) -> bytes:
    return canonical_json_bytes(
        {
            "table_version": LOCATION_TABLE_VERSION,
            "locations": _serialized_records(records),
            "reserved_legacy_ids": _serialized_records(reservations),
            "events": _serialized_records(EVENT_LOCATIONS),
        }
    )


def serialize_mission_registry(
    missions: Iterable[MissionRecord] = MISSIONS,
    bootstrap_profiles: Iterable[MissionProfileRecord] = BOOTSTRAP_PROFILES,
    shadow_profiles: Iterable[MissionProfileRecord] = SHADOW_STORY_PROFILES,
) -> bytes:
    return canonical_json_bytes(
        {
            "table_version": MISSION_TABLE_VERSION,
            "missions": _serialized_records(missions),
            "bootstrap_profiles": _serialized_records(bootstrap_profiles),
            "shadow_story_profiles": _serialized_records(shadow_profiles),
        }
    )


validate_registry()
validate_mission_registry()

FIRST_RELEASE_ITEM_NAME_TO_ID = {
    record.name: record.code for record in FIRST_RELEASE_ITEMS
}
FIRST_RELEASE_LOCATION_NAME_TO_ID = {
    record.name: record.code for record in FIRST_RELEASE_LOCATIONS
}
MISSION_BY_TASK_ID = {mission.task_id: mission for mission in MISSIONS}

ITEM_TABLE_HASH = canonical_sha256(
    {
        "table_version": ITEM_TABLE_VERSION,
        "items": _serialized_records(FIRST_RELEASE_ITEMS),
        "reserved_legacy_ids": _serialized_records(RESERVED_LEGACY_ITEM_IDS),
    }
)
LOCATION_TABLE_HASH = canonical_sha256(
    {
        "table_version": LOCATION_TABLE_VERSION,
        "locations": _serialized_records(FIRST_RELEASE_LOCATIONS),
        "reserved_legacy_ids": _serialized_records(RESERVED_LEGACY_LOCATION_IDS),
        "events": _serialized_records(EVENT_LOCATIONS),
    }
)
MISSION_TABLE_HASH = canonical_sha256(
    {
        "table_version": MISSION_TABLE_VERSION,
        "missions": _serialized_records(MISSIONS),
        "bootstrap_profiles": _serialized_records(BOOTSTRAP_PROFILES),
        "shadow_story_profiles": _serialized_records(SHADOW_STORY_PROFILES),
    }
)
