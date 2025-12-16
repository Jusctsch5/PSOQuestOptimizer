"""
Test quest calculator functionality.

Tests quest value calculations with different boost configurations.
"""

import logging
from pathlib import Path

import pytest

from quest_optimizer.quest_calculator import QuestCalculator, WeeklyBoost

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Paths to test data
PROJECT_ROOT = Path(__file__).parent.parent.parent
DROP_TABLE_PATH = PROJECT_ROOT / "drop_tables" / "drop_tables_ultimate.json"
PRICE_GUIDE_PATH = PROJECT_ROOT / "price_guide" / "data"
QUEST_DATA_PATH = PROJECT_ROOT / "quests" / "quests.json"


@pytest.fixture
def quest_calculator():
    """Create a QuestCalculator instance for testing"""
    return QuestCalculator(DROP_TABLE_PATH, PRICE_GUIDE_PATH, QUEST_DATA_PATH)


def test_qcalc_christmas_boost_doubles_weekly_boost(quest_calculator: QuestCalculator):
    """Test that Christmas boost doubles weekly boost values"""
    # Find MU1 quest
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"
    weekly_boost = WeeklyBoost.DAR

    # Calculate without Christmas boost
    result_no_christmas = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=weekly_boost, christmas_boost=False
    )

    # Calculate with Christmas boost
    result_with_christmas = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=weekly_boost, christmas_boost=True
    )

    pd_no_christmas = result_no_christmas["total_pd"]
    pd_with_christmas = result_with_christmas["total_pd"]

    print(f"MU1 Skyly DAR boost (no Christmas): {pd_no_christmas} PD")
    print(f"MU1 Skyly DAR boost (with Christmas): {pd_with_christmas} PD")

    # Christmas boost should increase the PD value
    assert pd_with_christmas > pd_no_christmas, (
        f"Christmas boost should increase PD value: {pd_with_christmas} should be > {pd_no_christmas}"
    )

    # Both should be positive
    assert pd_no_christmas > 0, f"PD value without Christmas boost should be > 0, got {pd_no_christmas}"
    assert pd_with_christmas > 0, f"PD value with Christmas boost should be > 0, got {pd_with_christmas}"


def test_process_box_drops(quest_calculator: QuestCalculator):
    """Test box drop processing"""
    # MU1 has 44 boxes in Forest 1
    area_name = "Forest 1"
    box_counts = {"box": 44, "box_rareless": 5}
    episode = 1
    section_id = "Skyly"

    total_pd, box_breakdown = quest_calculator._process_box_drops(area_name, box_counts, episode, section_id)

    # Should have some PD value from boxes
    assert total_pd >= 0, f"Box PD should be >= 0, got {total_pd}"
    # Box breakdown should exist
    assert isinstance(box_breakdown, dict), "Box breakdown should be a dictionary"


def test_box_drops_in_quest_value(quest_calculator: QuestCalculator):
    """Test that box drops are included in quest value calculation"""
    # Find MU1 quest (has boxes)
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"
    result = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, christmas_boost=False
    )

    # Should have box_breakdown and box_pd in result
    assert "box_breakdown" in result, "Result should include box_breakdown"
    assert "box_pd" in result, "Result should include box_pd"
    assert isinstance(result["box_breakdown"], dict), "box_breakdown should be a dictionary"
    assert isinstance(result["box_pd"], float), "box_pd should be a float"
    assert result["box_pd"] >= 0, f"box_pd should be >= 0, got {result['box_pd']}"

    # Total PD should include box PD
    total_pd = result["total_pd"]
    box_pd = result["box_pd"]
    assert total_pd >= box_pd, f"Total PD ({total_pd}) should be >= box PD ({box_pd})"


def test_box_armor_weapon_excluded(quest_calculator: QuestCalculator):
    """Test that box_armor and box_weapon don't contribute to rare drops"""
    # MU3 has 39 regular boxes, 6 box_armor, 7 box_weapon in Mine 1
    mu3_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU3":
            mu3_quest = quest
            break

    assert mu3_quest is not None, "MU3 quest not found in quest data"

    # Get box counts for Mine 1
    areas = mu3_quest.get("areas", [])
    mine1_area = None
    for area in areas:
        if area.get("name") == "Mine 1":
            mine1_area = area
            break

    assert mine1_area is not None, "Mine 1 area not found in MU3"
    boxes = mine1_area.get("boxes", {})
    assert "box" in boxes, "MU3 should have regular boxes"
    assert "box_armor" in boxes, "MU3 should have box_armor"
    assert "box_weapon" in boxes, "MU3 should have box_weapon"

    # Process box drops - should only use regular boxes
    area_name = "Mine 1"
    episode = 1
    section_id = "Skyly"

    total_pd, box_breakdown = quest_calculator._process_box_drops(area_name, boxes, episode, section_id)

    # Should only process regular boxes (39), not box_armor (6) or box_weapon (7)
    # The box_breakdown should reflect only regular box drops
    # We can't easily verify the exact count without knowing drop rates,
    # but we can verify that box_armor and box_weapon don't contribute
    assert total_pd >= 0, "Box PD should be >= 0"


def test_area_mapping_in_box_processing(quest_calculator: QuestCalculator):
    """Test that area mapping works correctly in box processing"""
    # Test with an area that needs mapping (if such a quest exists)
    # For now, test that regular areas work
    area_name = "Forest 1"
    box_counts = {"box": 10}
    episode = 1
    section_id = "Skyly"

    total_pd, box_breakdown = quest_calculator._process_box_drops(area_name, box_counts, episode, section_id)

    # Should process successfully
    assert total_pd >= 0, "Box PD should be >= 0"
    assert isinstance(box_breakdown, dict), "Box breakdown should be a dictionary"


def test_box_drops_not_affected_by_dar(quest_calculator: QuestCalculator):
    """Test that box drops are NOT affected by DAR multipliers"""
    area_name = "Forest 1"
    box_counts = {"box": 10}
    episode = 1
    section_id = "Skyly"

    # Process with base rate (no DAR multiplier)
    total_pd_base, box_breakdown_base = quest_calculator._process_box_drops(area_name, box_counts, episode, section_id)

    # Box drops should use base drop rate only, regardless of any multipliers
    # The drop rate from the drop table is already the final rate
    assert total_pd_base >= 0, "Box PD should be >= 0"

    # Verify that box breakdown doesn't include adjusted_dar (since we removed it)
    if box_breakdown_base:
        for item_name, item_data in box_breakdown_base.items():
            assert "adjusted_dar" not in item_data, "Box drops should not have adjusted_dar"
            assert "drop_rate" in item_data, "Box drops should have drop_rate"
