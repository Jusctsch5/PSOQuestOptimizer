"""
Test quest listing functionality.

Tests the QuestListing class for loading quests, area mapping, and box type filtering.
"""

import logging
from pathlib import Path

import pytest

from quests.quest_listing import (
    BOX_TYPE_ARMOR,
    BOX_TYPE_RARELESS,
    BOX_TYPE_REGULAR,
    BOX_TYPE_WEAPON,
    QuestListing,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Paths to test data
PROJECT_ROOT = Path(__file__).parent.parent.parent
QUEST_DATA_PATH = PROJECT_ROOT / "quests" / "quests.json"


@pytest.fixture
def quest_listing():
    """Create a QuestListing instance for testing"""
    return QuestListing(QUEST_DATA_PATH)


def test_quest_listing_load(quest_listing: QuestListing):
    """Test that quest listing loads correctly"""
    assert quest_listing.quests is not None
    assert len(quest_listing.quests) > 0


def test_get_quest(quest_listing: QuestListing):
    """Test getting quest by name"""
    quest = quest_listing.get_quest("MU1")
    assert quest is not None
    assert quest.get("quest_name") == "MU1"
    assert quest.get("long_name") == "Mop-up Operation 1"

    # Test case-insensitive
    quest2 = quest_listing.get_quest("mu1")
    assert quest2 is not None
    assert quest2.get("quest_name") == "MU1"

    # Test non-existent quest
    quest3 = quest_listing.get_quest("NONEXISTENT")
    assert quest3 is None


def test_get_all_quests(quest_listing: QuestListing):
    """Test getting all quests"""
    all_quests = quest_listing.get_all_quests()
    assert len(all_quests) > 0
    assert all_quests == quest_listing.quests


def test_get_quests_by_episode(quest_listing: QuestListing):
    """Test filtering quests by episode"""
    episode1_quests = quest_listing.get_quests_by_episode(1)
    assert len(episode1_quests) > 0
    for quest in episode1_quests:
        assert quest.get("episode") == 1

    episode2_quests = quest_listing.get_quests_by_episode(2)
    assert len(episode2_quests) > 0
    for quest in episode2_quests:
        assert quest.get("episode") == 2


def test_get_areas_for_quest(quest_listing: QuestListing):
    """Test getting areas for a quest"""
    areas = quest_listing.get_areas_for_quest("MU1")
    assert len(areas) > 0
    assert areas[0].get("name") == "Forest 1"
    assert "boxes" in areas[0]

    # Test non-existent quest
    areas2 = quest_listing.get_areas_for_quest("NONEXISTENT")
    assert len(areas2) == 0


def test_get_boxes_for_area(quest_listing: QuestListing):
    """Test getting box counts for an area"""
    boxes = quest_listing.get_boxes_for_area("MU1", "Forest 1")
    assert "box" in boxes
    assert boxes["box"] == 44
    assert "box_rareless" in boxes
    assert boxes["box_rareless"] == 5

    # Test non-existent area
    boxes2 = quest_listing.get_boxes_for_area("MU1", "NONEXISTENT")
    assert len(boxes2) == 0


def test_area_mapping_under_the_dome(quest_listing: QuestListing):
    """Test area mapping: Under the Dome -> Cave 1"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("Under the Dome")
    assert mapped == "Cave 1"

    # Test case-insensitive
    mapped2 = quest_listing.map_quest_area_to_drop_table_area("under the dome")
    assert mapped2 == "Cave 1"


def test_area_mapping_underground_channel(quest_listing: QuestListing):
    """Test area mapping: Underground Channel -> Mine 1"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("Underground Channel")
    assert mapped == "Mine 1"


def test_area_mapping_monitor_room(quest_listing: QuestListing):
    """Test area mapping: Monitor Room -> Ruins 1"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("Monitor Room")
    assert mapped == "Ruins 1"


def test_area_mapping_question_marks(quest_listing: QuestListing):
    """Test area mapping: ???? -> Ruins 3"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("????")
    assert mapped == "Ruins 3"


def test_area_mapping_vr_temple_final(quest_listing: QuestListing):
    """Test area mapping: VR Temple Final -> VR Spaceship: Alpha"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("VR Temple Final")
    assert mapped == "VR Spaceship: Alpha"


def test_area_mapping_no_match(quest_listing: QuestListing):
    """Test that unmapped areas return original name"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("Forest 1")
    assert mapped == "Forest 1"

    mapped2 = quest_listing.map_quest_area_to_drop_table_area("Cave 2")
    assert mapped2 == "Cave 2"


def test_area_mapping_case_insensitive(quest_listing: QuestListing):
    """Test case-insensitive area mapping"""
    mapped = quest_listing.map_quest_area_to_drop_table_area("UNDER THE DOME")
    assert mapped == "Cave 1"

    mapped2 = quest_listing.map_quest_area_to_drop_table_area("underground channel")
    assert mapped2 == "Mine 1"


def test_is_rare_dropping_box(quest_listing: QuestListing):
    """Test box type filtering - only regular boxes can drop rares"""
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_REGULAR) is True
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_ARMOR) is False
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_WEAPON) is False
    assert quest_listing.is_rare_dropping_box(BOX_TYPE_RARELESS) is False
    assert quest_listing.is_rare_dropping_box("unknown") is False


def test_get_rare_dropping_box_count(quest_listing: QuestListing):
    """Test getting count of rare-dropping boxes"""
    # MU1 has 44 regular boxes and 5 box_rareless
    count = quest_listing.get_rare_dropping_box_count("MU1", "Forest 1")
    assert count == 44

    # MU3 has 39 regular boxes, 6 box_armor, 7 box_weapon
    count2 = quest_listing.get_rare_dropping_box_count("MU3", "Mine 1")
    assert count2 == 39

    # Test non-existent area
    count3 = quest_listing.get_rare_dropping_box_count("MU1", "NONEXISTENT")
    assert count3 == 0

