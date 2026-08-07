"""Frozen protocol-1 network-ID compatibility ledger.

This literal snapshot is independent of the mutable Milestone 0-3 scaffold in
worlds.jak3.data. A non-null retained_concept is the exact first-release
semantic identity allowed to keep that legacy code; a null value reserves the
code permanently.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrozenLegacyIdRecord:
    legacy_name: str
    code: int
    retained_concept: str | None


FROZEN_LEGACY_ITEM_IDS: tuple[FrozenLegacyIdRecord, ...] = (
    FrozenLegacyIdRecord(
        "Mission Unlock: Survive the Desert Ambush", 743_000_007, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Complete Vehicle Training I", 743_000_008, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Complete Vehicle Training II", 743_000_009, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Complete Arena Training", 743_000_010, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Earn the First War Amulet", 743_000_011, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Catch the Kanga Rats", 743_000_012, None),
    FrozenLegacyIdRecord("Mission Unlock: Unlock the Satellite", 743_000_013, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Learn to Ride the Tough Puppy", 743_000_014, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Beat Kleiver in the Desert Race", 743_000_015, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Collect Artifacts", 743_000_016, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Beat the Monks in the Leaper Race", 743_000_017, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Metal Head Beasts", 743_000_018, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Earn the Second War Amulet", 743_000_019, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Corral the Wild Leapers", 743_000_020, None),
    FrozenLegacyIdRecord("Mission Unlock: Rescue the Wastelanders", 743_000_021, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Beat the Turret Challenge", 743_000_022, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Defeat the Marauders in the Arena", 743_000_023, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Eggs in the Nest", 743_000_024, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Climb the Monk Temple Tower", 743_000_025, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Glide to the Volcano", 743_000_026, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Find the Satellite at the Volcano", 743_000_027, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Meet the Monk Temple Oracle", 743_000_028, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Protect Ashelin at the Oasis", 743_000_029, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Complete the Monk Temple Tests", 743_000_030, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Travel Through the Catacomb Subrails", 743_000_031, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Explore the Eco Mine", 743_000_032, None),
    FrozenLegacyIdRecord("Mission Unlock: Escort the Bomb Train", 743_000_033, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Defeat Veger's Precursor Robot", 743_000_034, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Reach the Metal Head Area via Sewer", 743_000_035, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Complete Haven Vehicle Training", 743_000_036, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Defend the Port from Attack", 743_000_037, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Defeat the Incoming Blast Bots", 743_000_038, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Beat Gun Course I", 743_000_039, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Sniper Cannons", 743_000_040, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Reach Freedom HQ", 743_000_041, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Dark Eco Tanks", 743_000_042, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Kill the Dark Plants in the Forest", 743_000_043, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Eco Grid with Jinx", 743_000_044, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Hijack the Eco Vehicle", 743_000_045, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Defend the Port with the Jetboard", 743_000_046, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Beat Gun Course II", 743_000_047, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Barricade with the Bomb Bot", 743_000_048, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Defend Freedom HQ", 743_000_049, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Find the Switch in the Sewers", 743_000_050, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Find the Cipher in the Eco Grid", 743_000_051, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Race for More Artifacts", 743_000_052, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Metal-pedes in the Nest", 743_000_053, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Marauder Beasts", 743_000_054, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Test Drive the Dune Hopper", 743_000_055, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Chase the Marauders", 743_000_056, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Chase the Precursor Rings", 743_000_057, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the War Factory Defenses", 743_000_058, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Assault the War Factory", 743_000_059, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Defeat the War Factory Boss", 743_000_060, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Defend the Monk Temple", 743_000_061, None),
    FrozenLegacyIdRecord("Mission Unlock: Defend Spargus", 743_000_062, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Activate the Astro-Viewer in the Forest", 743_000_063, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Explore the Precursor Core", 743_000_064, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Break Through the City Tower", 743_000_065, None
    ),
    FrozenLegacyIdRecord(
        "Mission Unlock: Destroy the Dark Maker Tower", 743_000_066, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Reach the Palace Ruins", 743_000_067, None),
    FrozenLegacyIdRecord("Mission Unlock: Defend the Palace Ruins", 743_000_068, None),
    FrozenLegacyIdRecord(
        "Mission Unlock: Complete the Catacomb Rail Ride", 743_000_069, None
    ),
    FrozenLegacyIdRecord("Mission Unlock: Destroy the Dark Ship", 743_000_070, None),
    FrozenLegacyIdRecord("Mission Unlock: Defeat Cyber Errol", 743_000_071, None),
    FrozenLegacyIdRecord("Progressive Scatter Gun", 743_000_100, None),
    FrozenLegacyIdRecord("Progressive Blaster", 743_000_101, None),
    FrozenLegacyIdRecord("Progressive Vulcan Fury", 743_000_102, None),
    FrozenLegacyIdRecord("Progressive Peace Maker", 743_000_103, None),
    FrozenLegacyIdRecord(
        "Progressive Red Ammo Capacity",
        743_000_104,
        "ammo_capacity:Progressive Red Ammo Capacity",
    ),
    FrozenLegacyIdRecord(
        "Progressive Yellow Ammo Capacity",
        743_000_105,
        "ammo_capacity:Progressive Yellow Ammo Capacity",
    ),
    FrozenLegacyIdRecord(
        "Progressive Blue Ammo Capacity",
        743_000_106,
        "ammo_capacity:Progressive Blue Ammo Capacity",
    ),
    FrozenLegacyIdRecord(
        "Progressive Dark Ammo Capacity",
        743_000_107,
        "ammo_capacity:Progressive Dark Ammo Capacity",
    ),
    FrozenLegacyIdRecord("Jetboard", 743_000_108, "capability:Jetboard"),
    FrozenLegacyIdRecord("Tough Puppy", 743_000_109, None),
    FrozenLegacyIdRecord("Sand Shark", 743_000_110, None),
    FrozenLegacyIdRecord("Gila Stomper", 743_000_111, None),
    FrozenLegacyIdRecord("Dune Hopper", 743_000_112, None),
    FrozenLegacyIdRecord("Slam Dozer", 743_000_113, "vehicle:Ram 'Rod / Slam Dozer"),
    FrozenLegacyIdRecord("Progressive Dark Jak Power", 743_000_114, None),
    FrozenLegacyIdRecord("Progressive Light Jak Power", 743_000_115, None),
    FrozenLegacyIdRecord("Progressive Armor", 743_000_116, "armor:Progressive Armor"),
    FrozenLegacyIdRecord("Health Pack", 743_002_000, None),
    FrozenLegacyIdRecord("Red Ammo Crate", 743_002_001, None),
    FrozenLegacyIdRecord("Yellow Ammo Crate", 743_002_002, None),
    FrozenLegacyIdRecord("Blue Ammo Crate", 743_002_003, None),
    FrozenLegacyIdRecord("Dark Ammo Crate", 743_002_004, None),
    FrozenLegacyIdRecord("Light Eco", 743_002_005, None),
    FrozenLegacyIdRecord("Dark Eco", 743_002_006, None),
    FrozenLegacyIdRecord("Ammo Trap", 743_003_000, None),
    FrozenLegacyIdRecord("Camera Trap", 743_003_001, None),
    FrozenLegacyIdRecord("Dark Trap", 743_003_002, None),
    FrozenLegacyIdRecord("Darkness Trap", 743_003_003, None),
    FrozenLegacyIdRecord("Earthquake Trap", 743_003_004, None),
    FrozenLegacyIdRecord("Gravity Trap", 743_003_005, None),
    FrozenLegacyIdRecord("Health Trap", 743_003_006, None),
    FrozenLegacyIdRecord("Hero Trap", 743_003_007, None),
    FrozenLegacyIdRecord("High Alert Trap", 743_003_008, None),
    FrozenLegacyIdRecord("Ledge Trap", 743_003_009, None),
    FrozenLegacyIdRecord("Mirror Trap", 743_003_010, None),
    FrozenLegacyIdRecord("Pacifism Trap", 743_003_011, None),
    FrozenLegacyIdRecord("Slip Trap", 743_003_012, None),
    FrozenLegacyIdRecord("Slow Trap", 743_003_013, None),
    FrozenLegacyIdRecord("Speed Trap", 743_003_014, None),
    FrozenLegacyIdRecord("Teleport Trap", 743_003_015, None),
    FrozenLegacyIdRecord("Trip Trap", 743_003_016, None),
)


FROZEN_LEGACY_LOCATION_IDS: tuple[FrozenLegacyIdRecord, ...] = (
    FrozenLegacyIdRecord("Complete Mission: Watch Intro Movie", 743_001_006, None),
    FrozenLegacyIdRecord(
        "Complete Mission: Survive the Desert Ambush", 743_001_007, None
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Complete Vehicle Training I", 743_001_008, None
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Complete Vehicle Training II", 743_001_009, None
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Complete Arena Training", 743_001_010, "story_completion:10"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Earn the First War Amulet",
        743_001_011,
        "story_completion:11",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Catch the Kanga Rats", 743_001_012, "story_completion:12"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Unlock the Satellite", 743_001_013, "story_completion:13"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Learn to Ride the Tough Puppy",
        743_001_014,
        "story_completion:14",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Beat Kleiver in the Desert Race",
        743_001_015,
        "story_completion:15",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Collect Artifacts", 743_001_016, "story_completion:16"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Beat the Monks in the Leaper Race",
        743_001_017,
        "story_completion:17",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Metal Head Beasts",
        743_001_018,
        "story_completion:18",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Earn the Second War Amulet",
        743_001_019,
        "story_completion:19",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Corral the Wild Leapers", 743_001_020, "story_completion:20"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Rescue the Wastelanders", 743_001_021, "story_completion:21"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Beat the Turret Challenge",
        743_001_022,
        "story_completion:22",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defeat the Marauders in the Arena",
        743_001_023,
        "story_completion:23",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Eggs in the Nest",
        743_001_024,
        "story_completion:24",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Climb the Monk Temple Tower",
        743_001_025,
        "story_completion:25",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Glide to the Volcano", 743_001_026, "story_completion:26"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Find the Satellite at the Volcano",
        743_001_027,
        "story_completion:27",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Meet the Monk Temple Oracle",
        743_001_028,
        "story_completion:28",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Protect Ashelin at the Oasis",
        743_001_029,
        "story_completion:29",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Complete the Monk Temple Tests",
        743_001_030,
        "story_completion:30",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Travel Through the Catacomb Subrails",
        743_001_031,
        "story_completion:31",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Explore the Eco Mine", 743_001_032, "story_completion:32"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Escort the Bomb Train", 743_001_033, "story_completion:33"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defeat Veger's Precursor Robot",
        743_001_034,
        "story_completion:34",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Reach the Metal Head Area via Sewer",
        743_001_035,
        "story_completion:35",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Complete Haven Vehicle Training", 743_001_036, None
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defend the Port from Attack",
        743_001_037,
        "story_completion:37",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defeat the Incoming Blast Bots",
        743_001_038,
        "story_completion:38",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Beat Gun Course I", 743_001_039, "story_completion:39"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Sniper Cannons",
        743_001_040,
        "story_completion:40",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Reach Freedom HQ", 743_001_041, "story_completion:41"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Dark Eco Tanks",
        743_001_042,
        "story_completion:42",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Kill the Dark Plants in the Forest",
        743_001_043,
        "story_completion:43",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Eco Grid with Jinx",
        743_001_044,
        "story_completion:44",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Hijack the Eco Vehicle", 743_001_045, "story_completion:45"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defend the Port with the Jetboard",
        743_001_046,
        "story_completion:46",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Beat Gun Course II", 743_001_047, "story_completion:47"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Barricade with the Bomb Bot",
        743_001_048,
        "story_completion:48",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defend Freedom HQ", 743_001_049, "story_completion:49"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Find the Switch in the Sewers",
        743_001_050,
        "story_completion:50",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Find the Cipher in the Eco Grid",
        743_001_051,
        "story_completion:51",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Race for More Artifacts", 743_001_052, "story_completion:52"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Metal-pedes in the Nest",
        743_001_053,
        "story_completion:53",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Marauder Beasts",
        743_001_054,
        "story_completion:54",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Test Drive the Dune Hopper",
        743_001_055,
        "story_completion:55",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Chase the Marauders", 743_001_056, "story_completion:56"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Chase the Precursor Rings",
        743_001_057,
        "story_completion:57",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the War Factory Defenses",
        743_001_058,
        "story_completion:58",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Assault the War Factory", 743_001_059, "story_completion:59"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defeat the War Factory Boss",
        743_001_060,
        "story_completion:60",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defend the Monk Temple", 743_001_061, "story_completion:61"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defend Spargus", 743_001_062, "story_completion:62"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Activate the Astro-Viewer in the Forest",
        743_001_063,
        "story_completion:63",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Explore the Precursor Core",
        743_001_064,
        "story_completion:64",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Break Through the City Tower",
        743_001_065,
        "story_completion:65",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Dark Maker Tower",
        743_001_066,
        "story_completion:66",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Reach the Palace Ruins", 743_001_067, "story_completion:67"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defend the Palace Ruins", 743_001_068, "story_completion:68"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Complete the Catacomb Rail Ride",
        743_001_069,
        "story_completion:69",
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Destroy the Dark Ship", 743_001_070, "story_completion:70"
    ),
    FrozenLegacyIdRecord(
        "Complete Mission: Defeat Cyber Errol", 743_001_071, "story_completion:71"
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 1", 743_001_073, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 2", 743_001_074, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 3", 743_001_075, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 4", 743_001_076, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 5", 743_001_077, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 6", 743_001_078, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 7", 743_001_079, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 8", 743_001_080, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 9", 743_001_081, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 11", 743_001_082, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 12", 743_001_083, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 14", 743_001_084, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 16", 743_001_085, None
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Discovery 17", 743_001_086, None
    ),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 18", 743_001_087, None),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 19", 743_001_088, None),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 20", 743_001_089, None),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 21", 743_001_090, None),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 22", 743_001_091, None),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 23", 743_001_092, None),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 24", 743_001_093, None),
    FrozenLegacyIdRecord("Complete Challenge: Spargus Discovery 25", 743_001_094, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 26", 743_001_095, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 27", 743_001_096, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 28", 743_001_097, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 29", 743_001_098, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 30", 743_001_099, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 31", 743_001_100, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 32", 743_001_101, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 33", 743_001_102, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 34", 743_001_103, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 35", 743_001_104, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 36", 743_001_105, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 37", 743_001_106, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 38", 743_001_107, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 39", 743_001_108, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 40", 743_001_109, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 41", 743_001_110, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 42", 743_001_111, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 43", 743_001_112, None),
    FrozenLegacyIdRecord("Complete Challenge: Haven Discovery 44", 743_001_113, None),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Ring Challenge 1",
        743_001_114,
        "selected_side_challenge:114",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Ring Challenge 2",
        743_001_115,
        "selected_side_challenge:115",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Spargus Ring Challenge 1",
        743_001_116,
        "selected_side_challenge:116",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Spargus Ring Challenge 2",
        743_001_117,
        "selected_side_challenge:117",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Haven Ring Challenge 1",
        743_001_118,
        "selected_side_challenge:118",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Haven Ring Challenge 2",
        743_001_119,
        "selected_side_challenge:119",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Destroy the Metal Spider",
        743_001_120,
        "selected_side_challenge:120",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Spirit Chase",
        743_001_121,
        "selected_side_challenge:121",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Spargus Spirit Chase",
        743_001_122,
        "selected_side_challenge:122",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Haven Spirit Chase",
        743_001_123,
        "selected_side_challenge:123",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Time Freeze",
        743_001_124,
        "selected_side_challenge:124",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Spargus Time Freeze",
        743_001_125,
        "selected_side_challenge:125",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Single Jump Air Time",
        743_001_126,
        "selected_side_challenge:126",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Total Jump Air Time",
        743_001_127,
        "selected_side_challenge:127",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Single Jump Distance",
        743_001_128,
        "selected_side_challenge:128",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Total Jump Distance",
        743_001_129,
        "selected_side_challenge:129",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Roll Challenge",
        743_001_130,
        "selected_side_challenge:130",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Time Trial",
        743_001_131,
        "selected_side_challenge:131",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wasteland Rally",
        743_001_132,
        "selected_side_challenge:132",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Defend the Port Side Mission",
        743_001_133,
        "selected_side_challenge:133",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Wastelander Rescue Side Mission",
        743_001_134,
        "selected_side_challenge:134",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Gun Course Free Play",
        743_001_135,
        "selected_side_challenge:135",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Haven Jetboard Challenge",
        743_001_136,
        "selected_side_challenge:136",
    ),
    FrozenLegacyIdRecord(
        "Complete Challenge: Destroy the Interceptors",
        743_001_137,
        "selected_side_challenge:137",
    ),
)
