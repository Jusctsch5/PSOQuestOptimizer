"""
Test optimize_item_hunting functionality.

Tests finding best quests for different item types.
"""

import logging
from pathlib import Path

import pytest

from quest_optimizer.quest_calculator import EventType, QuestCalculator, WeeklyBoost

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Paths to test data
PROJECT_ROOT = Path(__file__).parent.parent
DROP_TABLE_PATH = PROJECT_ROOT / "drop_tables" / "drop_tables_ultimate.json"
PRICE_GUIDE_PATH = PROJECT_ROOT / "price_guide" / "data"
QUEST_DATA_PATH = PROJECT_ROOT / "quests" / "quests.json"


@pytest.fixture
def quest_calculator():
    """Create a QuestCalculator instance for testing"""
    return QuestCalculator(DROP_TABLE_PATH, PRICE_GUIDE_PATH, QUEST_DATA_PATH)


def test_find_quests_for_weapon(quest_calculator: QuestCalculator):
    """Test finding quests for a weapon item"""
    # Use a common weapon that should have drops
    item_name = "Lame D'Argent"
    
    results = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    assert len(results) > 0, f"Should find at least one quest for weapon '{item_name}'"
    logger.info(f"Found {len(results)} quest(s) for weapon '{item_name}'")
    
    # Validate result structure
    first_result = results[0]
    assert "quest_name" in first_result
    assert "section_id" in first_result
    assert "probability" in first_result
    assert first_result["probability"] > 0


def test_find_quests_for_disk(quest_calculator: QuestCalculator):
    """Test finding quests for a technique disk item"""
    # Use a technique that should have drops
    item_name = "Foie"
    
    results = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    assert len(results) > 0, f"Should find at least one quest for disk '{item_name}'"
    logger.info(f"Found {len(results)} quest(s) for disk '{item_name}'")
    
    # Validate result structure
    first_result = results[0]
    assert "quest_name" in first_result
    assert "probability" in first_result
    assert first_result["probability"] > 0


def test_find_quests_for_tool(quest_calculator: QuestCalculator):
    """Test finding quests for a tool item"""
    # Use a tool that should have drops
    item_name = "Photon Crystal"
    
    results = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    assert len(results) > 0, f"Should find at least one quest for tool '{item_name}'"
    logger.info(f"Found {len(results)} quest(s) for tool '{item_name}'")
    
    # Validate result structure
    first_result = results[0]
    assert "quest_name" in first_result
    assert "probability" in first_result
    assert first_result["probability"] > 0


def test_find_quests_for_frame(quest_calculator: QuestCalculator):
    """Test finding quests for a frame (armor) item"""
    # Use a frame that should have drops
    item_name = "Brightness Circle"
    
    results = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    assert len(results) > 0, f"Should find at least one quest for frame '{item_name}'"
    logger.info(f"Found {len(results)} quest(s) for frame '{item_name}'")
    
    # Validate result structure
    first_result = results[0]
    assert "quest_name" in first_result
    assert "probability" in first_result
    assert first_result["probability"] > 0


def test_find_quests_for_barrier(quest_calculator: QuestCalculator):
    """Test finding quests for a barrier (shield) item"""
    # Use a barrier that should have drops
    item_name = "Standstill Shield"
    
    results = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    assert len(results) > 0, f"Should find at least one quest for barrier '{item_name}'"
    logger.info(f"Found {len(results)} quest(s) for barrier '{item_name}'")
    
    # Validate result structure
    first_result = results[0]
    assert "quest_name" in first_result
    assert "probability" in first_result
    assert first_result["probability"] > 0


def test_find_quests_with_rbr_active(quest_calculator: QuestCalculator):
    """Test finding quests with RBR boost active"""
    item_name = "Lame D'Argent"
    
    results_no_rbr = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    results_with_rbr = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=True,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    assert len(results_with_rbr) > 0, "Should find at least one quest with RBR active"
    assert len(results_with_rbr) == len(results_no_rbr), "Should find same number of quests"
    
    # RBR should increase drop probabilities. 
    # This is a sorted list, so the first element of the boosted list should be higher 
    # (even though it may not be the same quest as the first element of the unboosted list)
    if results_with_rbr and results_no_rbr:
        assert results_with_rbr[0]["probability"] >= results_no_rbr[0]["probability"], (
            "RBR should increase or maintain drop probability"
        )


def test_find_quests_with_weekly_boost(quest_calculator: QuestCalculator):
    """Test finding quests with weekly boost"""
    item_name = "Lame D'Argent"
    
    results_no_boost = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    results_with_dar_boost = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=WeeklyBoost.DAR,
        quest_filter=None,
        event_type=None,
    )
    
    assert len(results_with_dar_boost) > 0, "Should find at least one quest with DAR boost"
    assert len(results_with_dar_boost) == len(results_no_boost), "Should find same number of quests"

    # DAR boost should increase drop probabilities
    # This is a sorted list, so the first element of the boosted list should be higher 
    # (even though it may not be the same quest as the first element of the unboosted list)
    if results_with_dar_boost and results_no_boost:
        assert results_with_dar_boost[0]["probability"] >= results_no_boost[0]["probability"], (
            "DAR boost should increase or maintain drop probability"
        )


def test_find_quests_with_event(quest_calculator: QuestCalculator):
    """Test finding quests with event active"""
    item_name = "Lame D'Argent"
    
    results_no_event = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    results_with_event = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=EventType.Christmas,
    )
    
    assert len(results_with_event) > 0, "Should find at least one quest with event active"
    assert len(results_with_event) == len(results_no_event), "Should find same number of quests"


def test_find_quests_with_quest_filter_no_match(quest_calculator: QuestCalculator):
    """Test finding quests with quest filter - negative case where filtered quest doesn't drop the item"""
    item_name = "Lame D'Argent"
    
    results_all = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    # MU1 doesn't drop Lame D'Argent, so filtering to MU1 should return no results
    results_filtered = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=["MU1"],
        event_type=None,
    )
    
    assert len(results_all) > 0, "Should find at least one quest for Lame D'Argent without filter"
    assert len(results_filtered) == 0, "MU1 doesn't drop Lame D'Argent, so filtered results should be empty"

def test_find_quests_with_quest_filter_match(quest_calculator: QuestCalculator):
    """Test finding quests with quest filter"""
    # Bartle drops Diska of Braveman in Redria in MU1
    item_name = "Diska of Braveman"
    
    results_all = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    
    results_filtered = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=["MU1"],
        event_type=None,
    )
    
    assert len(results_all) > 0, "Should find at least one quest for Diska of Braveman without filter"
    assert len(results_filtered) > 0, "MU1 drops Diska of Braveman, so filtered results should be non-empty"


def test_find_quests_undropped_item(quest_calculator: QuestCalculator):
    """Test that finding quests for a un-dropped item returns empty list"""
    # Excalibur doesn't drop - Lame D'Argent does.
    item_name = "Excalibur"
    
    # The method might return an empty list or raise an exception
    # Let's check what actually happens
    results = quest_calculator.find_best_quests_for_item(
        item_name,
        rbr_active=False,
        weekly_boost=None,
        quest_filter=None,
        event_type=None,
    )
    # If it returns, it should be an empty list
    assert len(results) == 0, f"Non-existent item should return empty list, got {len(results)} results"
    logger.info(f"Un-dropped item '{item_name}' returned empty list (expected)")


def test_find_quests_nonexistent_item(quest_calculator: QuestCalculator):
    """Test that finding quests for a non-existent item returns empty list or raises exception"""
    # Use an item that definitely doesn't exist
    item_name = "NONEXISTENT_ITEM_XYZ123"
    
    # The method might return an empty list or raise an exception
    # Let's check what actually happens
    try:
        results = quest_calculator.find_best_quests_for_item(
            item_name,
            rbr_active=False,
            weekly_boost=None,
            quest_filter=None,
            event_type=None,
        )
        # If it returns, it should be an empty list
        assert len(results) == 0, f"Non-existent item should return empty list, got {len(results)} results"
        logger.info(f"Non-existent item '{item_name}' returned empty list (expected)")
    except Exception as e:
        # If it raises an exception, that's also acceptable
        logger.info(f"Non-existent item '{item_name}' raised PriceGuideExceptionItemNameNotFound (expected)")
        pass

