"""
Quest listing module for accessing quest data from quests.json.

Provides an abstraction layer for quest data access, similar to price_guide.py.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


# Box type constants
BOX_TYPE_REGULAR = "box"  # Can drop rare items
BOX_TYPE_ARMOR = "box_armor"  # Cannot drop rare items
BOX_TYPE_WEAPON = "box_weapon"  # Cannot drop rare items
BOX_TYPE_RARELESS = "box_rareless"  # Cannot drop rare items

# Mapping from quest area names to drop table area names
AREA_MAPPING = {
    "Under the Dome": "Cave 1",
    "Underground Channel": "Mine 1",
    "Monitor Room": "Ruins 1",
    "????": "Ruins 3",
    "VR Temple Final": "VR Spaceship: Alpha",
}


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
        for quest_area, drop_table_area in AREA_MAPPING.items():
            if quest_area.lower() == area_name_lower:
                return drop_table_area
        # No mapping found, return original
        return area_name

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

