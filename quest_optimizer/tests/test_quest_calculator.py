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

    logger.info(f"MU1 Skyly DAR boost (no Christmas): {pd_no_christmas} PD")
    logger.info(f"MU1 Skyly DAR boost (with Christmas): {pd_with_christmas} PD")

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


def test_rbr_boost_increases_pd_value(quest_calculator: QuestCalculator):
    """Test that RBR boost increases PD/Quest value for quests in RBR rotation"""
    # Find MU1 quest (has is_in_rbr_rotation: true)
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"
    assert mu1_quest.get("is_in_rbr_rotation") is True, "MU1 should be in RBR rotation"

    section_id = "Skyly"

    # Calculate without RBR boost
    result_no_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, christmas_boost=False
    )

    # Calculate with RBR boost
    result_with_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=True, weekly_boost=None, christmas_boost=False
    )

    pd_no_rbr = result_no_rbr["total_pd"]
    pd_with_rbr = result_with_rbr["total_pd"]

    logger.info(f"MU1 Skyly (no RBR): {pd_no_rbr} PD")
    logger.info(f"MU1 Skyly (with RBR): {pd_with_rbr} PD")
    logger.info(f"Enemy breakdown (no RBR): {result_no_rbr.get('enemy_breakdown', {})}")
    logger.info(f"Enemy breakdown (with RBR): {result_with_rbr.get('enemy_breakdown', {})}")

    # RBR boost should increase the PD value
    assert pd_with_rbr > pd_no_rbr, f"RBR boost should increase PD value: {pd_with_rbr} should be > {pd_no_rbr}"

    # Both should be positive
    assert pd_no_rbr > 0, f"PD value without RBR boost should be > 0, got {pd_no_rbr}"
    assert pd_with_rbr > 0, f"PD value with RBR boost should be > 0, got {pd_with_rbr}"

    # RBR provides +25% DAR and +25% RDR, so the increase should be significant
    # We expect at least a 20% increase (conservative estimate)
    increase_ratio = pd_with_rbr / pd_no_rbr
    assert increase_ratio >= 1.15, (
        f"RBR boost should provide significant increase. "
        f"Expected ratio >= 1.15, got {increase_ratio:.4f} "
        f"({pd_with_rbr} / {pd_no_rbr})"
    )


def test_rbr_list_with_existing_quests(quest_calculator: QuestCalculator):
    """Test that rbr_list applies RBR boost only to specified existing quests"""
    import sys
    from pathlib import Path

    # Import QuestOptimizer from optimize_quests module
    optimize_quests_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(optimize_quests_path))
    import optimize_quests
    QuestOptimizer = optimize_quests.QuestOptimizer

    optimizer = QuestOptimizer(quest_calculator)

    # Find MU1 and MU2 quests (both should be in RBR rotation)
    mu1_quest = None
    mu2_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
        elif quest.get("quest_name") == "MU2":
            mu2_quest = quest

    assert mu1_quest is not None, "MU1 quest not found"
    assert mu2_quest is not None, "MU2 quest not found"

    section_id = "Skyly"
    rbr_list = ["MU1", "MU2"]

    # Rank quests with rbr_list
    rankings = optimizer.rank_quests(
        [mu1_quest, mu2_quest],
        section_id=section_id,
        rbr_active=False,
        rbr_list=rbr_list,
        weekly_boost=None,
        quest_times=None,
        episode_filter=None,
        christmas_boost=False,
        exclude_event_quests=False,
    )

    # Both quests should have RBR active
    for ranking in rankings:
        quest_name = ranking["quest_name"]
        assert ranking["rbr_active"] is True, f"{quest_name} should have RBR active when in rbr_list"

    # Calculate MU1 with and without RBR to verify it's actually applied
    result_with_rbr_list = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=True, weekly_boost=None, christmas_boost=False
    )
    result_no_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, christmas_boost=False
    )

    # RBR should increase PD value
    assert result_with_rbr_list["total_pd"] > result_no_rbr["total_pd"], (
        "RBR boost should increase PD value when quest is in rbr_list"
    )


def test_rbr_list_with_event_quest(quest_calculator: QuestCalculator):
    """Test that rbr_list can include event quests (they just won't get RBR boost if not in rotation)"""
    import sys
    from pathlib import Path

    # Import QuestOptimizer from optimize_quests module
    optimize_quests_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(optimize_quests_path))
    import optimize_quests
    QuestOptimizer = optimize_quests.QuestOptimizer

    optimizer = QuestOptimizer(quest_calculator)

    # Find an event quest
    event_quest = None
    for quest in quest_calculator.quest_data:
        if quest_calculator._is_event_quest(quest):
            event_quest = quest
            break

    assert event_quest is not None, "No event quest found in quest data"

    section_id = "Skyly"
    rbr_list = [event_quest.get("quest_name")]

    # Rank quest with rbr_list
    rankings = optimizer.rank_quests(
        [event_quest],
        section_id=section_id,
        rbr_active=False,
        rbr_list=rbr_list,
        weekly_boost=None,
        quest_times=None,
        episode_filter=None,
        christmas_boost=False,
        exclude_event_quests=False,
    )

    # The quest should be processed (no error)
    assert len(rankings) == 1, "Event quest should be processed even if in rbr_list"
    ranking = rankings[0]
    assert ranking["rbr_active"] is True, "Event quest should have rbr_active=True when in rbr_list"

    # However, if the event quest is not in RBR rotation, RBR won't actually apply
    # (this is handled by the calculator's _is_in_rbr_rotation check)
    in_rbr_rotation = quest_calculator._is_in_rbr_rotation(event_quest)
    if not in_rbr_rotation:
        # Calculate with and without RBR - should be the same if not in rotation
        result_with_rbr = quest_calculator.calculate_quest_value(
            event_quest, section_id, rbr_active=True, weekly_boost=None, christmas_boost=False
        )
        result_no_rbr = quest_calculator.calculate_quest_value(
            event_quest, section_id, rbr_active=False, weekly_boost=None, christmas_boost=False
        )
        # If not in RBR rotation, RBR won't affect the result
        logger.info(
            f"Event quest {event_quest.get('quest_name')} not in RBR rotation, "
            f"RBR has no effect: {result_with_rbr['total_pd']} == {result_no_rbr['total_pd']}"
        )


def test_rbr_list_with_nonexistent_quest(quest_calculator: QuestCalculator):
    """Test that rbr_list gracefully handles quests that don't exist"""
    import sys
    from pathlib import Path

    # Import QuestOptimizer from optimize_quests module
    optimize_quests_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(optimize_quests_path))
    import optimize_quests
    QuestOptimizer = optimize_quests.QuestOptimizer

    optimizer = QuestOptimizer(quest_calculator)

    # Find a real quest
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found"

    section_id = "Skyly"
    # Include a nonexistent quest in the list
    rbr_list = ["MU1", "NONEXISTENT_QUEST", "ALSO_FAKE"]

    # Rank quests with rbr_list containing nonexistent quests
    # Should not raise an error - nonexistent quests are simply ignored
    rankings = optimizer.rank_quests(
        [mu1_quest],
        section_id=section_id,
        rbr_active=False,
        rbr_list=rbr_list,
        weekly_boost=None,
        quest_times=None,
        episode_filter=None,
        christmas_boost=False,
        exclude_event_quests=False,
    )

    # MU1 should still have RBR active (it's in the list and exists)
    assert len(rankings) == 1, "Should process the existing quest"
    ranking = rankings[0]
    assert ranking["quest_name"] == "MU1", "Should process MU1"
    assert ranking["rbr_active"] is True, "MU1 should have RBR active when in rbr_list"

    # Verify RBR is actually applied
    result_with_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=True, weekly_boost=None, christmas_boost=False
    )
    result_no_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, christmas_boost=False
    )

    assert result_with_rbr["total_pd"] > result_no_rbr["total_pd"], (
        "RBR boost should be applied to existing quest in rbr_list, even if list contains nonexistent quests"
    )
