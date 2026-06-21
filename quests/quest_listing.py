"""
Quest listing module for accessing quest data from quests.json.

Provides an abstraction layer for quest data access, similar to price_guide.py.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

EnemyCount = Union[int, float]


def resolve_area_enemies(area: Dict) -> Dict[str, float]:
    """
    Merge fixed area enemies with expected counts from random spawns.

    Random spawn fields (per area):
    - average_random_enemies: expected number of randomly spawned enemies
    - random_enemies: enemy name -> relative weight; expected count is
      average_random_enemies × (weight / sum(weights)). Weights are usually
      percents (sum 100) but may use another total (e.g. 28/92).

    Returns:
        Enemy name -> expected kill count (fixed + random contribution).
    """
    enemies: Dict[str, float] = {}
    fixed = area.get("enemies") or {}
    for name, count in fixed.items():
        enemies[name] = enemies.get(name, 0.0) + float(count)

    random_weights = area.get("random_enemies")
    if not random_weights:
        return enemies

    average = area.get("average_random_enemies")
    if average is None:
        return enemies

    avg = float(average)
    if avg <= 0:
        return enemies

    weight_sum = sum(float(weight) for weight in random_weights.values())
    if weight_sum <= 0:
        return enemies

    for name, weight in random_weights.items():
        expected = avg * float(weight) / weight_sum
        enemies[name] = enemies.get(name, 0.0) + expected

    return enemies


def area_has_enemy_spawns(area: Dict) -> bool:
    """True if an area defines fixed enemies and/or random spawn weights."""
    return bool(area.get("enemies") or area.get("random_enemies"))

# Box type constants
BOX_TYPE_REGULAR = "box"  # Can drop rare items
BOX_TYPE_ARMOR = "box_armor"  # Cannot drop rare items
BOX_TYPE_WEAPON = "box_weapon"  # Cannot drop rare items
BOX_TYPE_RARELESS = "box_rareless"  # Cannot drop rare items


# Mapping from quest area names to drop table area names
class Area(Enum):
    """Enum for quest areas."""

    # Episode 1
    FOREST_1 = "Forest 1"
    FOREST_2 = "Forest 2"
    UNDER_THE_DOME = "Under the Dome"  # Dragon
    CAVE_1 = "Cave 1"
    CAVE_2 = "Cave 2"
    CAVE_3 = "Cave 3"
    UNDERGROUND_CHANNEL = "Underground Channel"  # Dal Ra Lie
    MINE_1 = "Mine 1"
    MINE_2 = "Mine 2"
    MONITOR_ROOM = "Monitor Room"  # Vol Opt
    RUINS_1 = "Ruins 1"
    RUINS_2 = "Ruins 2"
    RUINS_3 = "Ruins 3"
    QUESTION_MARKS = "????"  # Dark Falz

    # Episode 2
    VR_TEMPLE_ALPHA = "VR Temple Alpha"
    VR_TEMPLE_BETA = "VR Temple Beta"
    VR_TEMPLE_FINAL = "VR Temple Final"  #  Barba Ray

    VR_SPACESHIP_ALPHA = "VR Spaceship Alpha"
    VR_SPACESHIP_BETA = "VR Spaceship Beta"
    VR_SPACESHIP_FINAL = "VR Spaceship Final"  # Gol Dragon

    JUNGLE_AREA_NORTH = "Jungle North"
    JUNGLE_AREA_EAST = "Jungle East"
    MOUNTAIN = "Mountain"
    SEASIDE_AREA = "Seaside"
    CENTRAL_CONTROL_AREA = "Central Control Area"
    CLIFFS_OF_GAL_DA_VAL = "Cliffs of Gal Da Val"  # Gal Gryphon

    SEABED_UPPER_LEVELS = "Seabed Upper"
    SEABED_LOWER_LEVELS = "Seabed Lower"
    TEST_SUBJECT_DISPOSAL_AREA = "Test Subject Disposal Area"  # Olga Flow

    EAST_TOWER = "East Tower"
    WEST_TOWER = "West Tower"

    # Episode 4
    CRATER_EAST = "Crater East"
    CRATER_WEST = "Crater West"
    CRATER_SOUTH = "Crater South"
    CRATER_NORTH = "Crater North"
    CRATER_INTERIOR = "Crater Interior"
    SUBTERRANEAN_DESERT_1 = "Desert 1"
    SUBTERRANEAN_DESERT_2 = "Desert 2"
    SUBTERRANEAN_DESERT_3 = "Desert 3"
    METEOR_IMPACT_SITE = "Meteor Impact Site"  # Saint-Milion


# Mapping from quest areas to drop table areas
AREA_MAPPING = {
    # Episode 1
    Area.UNDER_THE_DOME: Area.CAVE_1,
    Area.UNDERGROUND_CHANNEL: Area.MINE_1,
    Area.MONITOR_ROOM: Area.RUINS_1,
    Area.QUESTION_MARKS: Area.RUINS_3,
    # Episode 2
    Area.VR_TEMPLE_FINAL: Area.VR_SPACESHIP_ALPHA,
    Area.VR_SPACESHIP_FINAL: Area.CENTRAL_CONTROL_AREA,
    Area.CLIFFS_OF_GAL_DA_VAL: Area.SEABED_UPPER_LEVELS,
    Area.TEST_SUBJECT_DISPOSAL_AREA: Area.SEABED_LOWER_LEVELS,
    Area.EAST_TOWER: Area.CENTRAL_CONTROL_AREA,
    Area.WEST_TOWER: Area.CENTRAL_CONTROL_AREA,
    # Episode 4
    Area.METEOR_IMPACT_SITE: Area.SUBTERRANEAN_DESERT_3,
}


class CouldNotFindAreaError(Exception):
    """Exception raised when a quest area mapping is not found."""

    pass


class QuestListing:
    """Quest listing abstraction for accessing quest data."""

    def __init__(self, quest_data_path: Path):
        """
        Initialize quest listing with quest data.

        Args:
            quest_data_path: Path to quests.json file
        """
        self.quest_data_path = quest_data_path
        self.quests = self._load_quest_data(quest_data_path)

    def _load_quest_data(self, quest_data_path: Path) -> List[Dict]:
        """Load quest data from JSON file."""
        with open(quest_data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_quest(self, quest_name: str) -> Optional[Dict]:
        """
        Get quest by name (case-insensitive).

        Args:
            quest_name: Quest name to search for

        Returns:
            Quest dictionary or None if not found
        """
        quest_name_lower = quest_name.lower()
        for quest in self.quests:
            if quest.get("quest_name", "").lower() == quest_name_lower:
                return quest
        return None

    def get_all_quests(self) -> List[Dict]:
        """
        Get all quests.

        Returns:
            List of all quest dictionaries
        """
        return self.quests

    def get_quests_by_episode(self, episode: int) -> List[Dict]:
        """
        Get quests filtered by episode.

        Args:
            episode: Episode number (1, 2, or 4)

        Returns:
            List of quest dictionaries for the specified episode
        """
        return [quest for quest in self.quests if quest.get("episode") == episode]

    def get_areas_for_quest(self, quest_name: str) -> List[Dict]:
        """
        Get areas for a quest.

        Args:
            quest_name: Quest name

        Returns:
            List of area dictionaries, or empty list if quest not found
        """
        quest = self.get_quest(quest_name)
        if not quest:
            return []
        return quest.get("areas", [])

    def get_boxes_for_area(self, quest_name: str, area_name: str) -> Dict[str, int]:
        """
        Get box counts for a specific area in a quest.

        Args:
            quest_name: Quest name
            area_name: Area name

        Returns:
            Dictionary mapping box types to counts, or empty dict if not found
        """
        areas = self.get_areas_for_quest(quest_name)
        for area in areas:
            if area.get("name") == area_name:
                return area.get("boxes", {})
        return {}

    def map_quest_area_to_drop_table_area(self, area_name: str) -> str:
        """
        Map quest area name to drop table area name.

        Args:
            area_name: Quest area name

        Returns:
            Drop table area name (mapped if mapping exists, otherwise original)
        """
        # Case-insensitive lookup
        area_name_lower = area_name.lower()

        # Case-insensitive lookup for Area enum
        for quest_area in Area:
            if quest_area.value.lower() == area_name_lower:
                area_enum = quest_area
                break
        else:
            raise CouldNotFindAreaError(f"Could not find area for {area_name}")

        # Normalize area mapping for things like "Under the Dome" -> "Cave 1"
        if area_enum in AREA_MAPPING:
            return AREA_MAPPING[area_enum].value
        else:
            return area_enum.value

    def is_rare_dropping_box(self, box_type: str) -> bool:
        """
        Check if a box type can drop rare items.

        Args:
            box_type: Box type string (e.g., "box", "box_armor", "box_weapon", "box_rareless")

        Returns:
            True if box type can drop rare items, False otherwise
        """
        return box_type == BOX_TYPE_REGULAR

    def get_rare_dropping_box_count(self, quest_name: str, area_name: str) -> int:
        """
        Get count of boxes that can drop rare items for a specific area.

        Args:
            quest_name: Quest name
            area_name: Area name

        Returns:
            Count of rare-dropping boxes (only "box" type, not box_armor, box_weapon, or box_rareless)
        """
        boxes = self.get_boxes_for_area(quest_name, area_name)
        return boxes.get(BOX_TYPE_REGULAR, 0)
