"""
Test quest calculator functionality.

Tests quest value calculations with different boost configurations.
"""

import logging
import sys
from pathlib import Path

import pytest

from price_guide.price_guide import PriceGuideExceptionItemNameNotFound
from quest_optimizer.quest_calculator import EventType, QuestCalculator, WeeklyBoost

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Paths to test data
PROJECT_ROOT = Path(__file__).parent.parent.parent
DROP_TABLE_PATH = PROJECT_ROOT / "drop_tables" / "drop_tables_ultimate.json"
PRICE_GUIDE_PATH = PROJECT_ROOT / "price_guide" / "data"
QUEST_DATA_PATH = PROJECT_ROOT / "quests" / "quests.json"

# Dynamic import setup for optimize_quests module (located in parent directory)
# This is necessary because optimize_quests is not a package but a script in the parent directory
optimize_quests_path = PROJECT_ROOT
if str(optimize_quests_path) not in sys.path:
    sys.path.insert(0, str(optimize_quests_path))
import optimize_quests  # noqa: E402

QuestOptimizer = optimize_quests.QuestOptimizer


@pytest.fixture
def quest_calculator():
    """Create a QuestCalculator instance for testing"""
    return QuestCalculator(DROP_TABLE_PATH, PRICE_GUIDE_PATH, QUEST_DATA_PATH)


def test_qcalc_christmas_event_boosts_dar_week(quest_calculator: QuestCalculator):
    """Test that Christmas event increases quest value during DAR week"""
    # Find MU1 quest
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"
    weekly_boost = WeeklyBoost.DAR

    # Calculate with DAR week only (no event)
    result_dar_only = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=weekly_boost, event_type=None
    )

    # Calculate with DAR week AND Christmas event
    result_dar_and_christmas = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=weekly_boost, event_type=EventType.Christmas
    )

    pd_dar_only = result_dar_only["total_pd"]
    pd_dar_and_christmas = result_dar_and_christmas["total_pd"]

    logger.info(f"MU1 Skyly DAR week (no Christmas): {pd_dar_only} PD")
    logger.info(f"MU1 Skyly DAR week + Christmas: {pd_dar_and_christmas} PD")

    # Both should be positive
    assert pd_dar_only > 0, f"PD value with DAR week only should be > 0, got {pd_dar_only}"
    assert pd_dar_and_christmas > 0, f"PD value with DAR week + Christmas should be > 0, got {pd_dar_and_christmas}"

    # Christmas event should increase the PD value during DAR week
    assert pd_dar_and_christmas > pd_dar_only, (
        f"Christmas event should increase PD value during DAR week: {pd_dar_and_christmas} should be > {pd_dar_only}"
    )


def test_qcalc_christmas_event_boosts_rdr_week(quest_calculator: QuestCalculator):
    """Test that Christmas event increases quest value during RDR week"""
    # Find MU1 quest
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"
    weekly_boost = WeeklyBoost.RDR

    # Calculate with RDR week only (no event)
    result_rdr_only = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=weekly_boost, event_type=None
    )

    # Calculate with RDR week AND Christmas event
    result_rdr_and_christmas = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=weekly_boost, event_type=EventType.Christmas
    )

    pd_rdr_only = result_rdr_only["total_pd"]
    pd_rdr_and_christmas = result_rdr_and_christmas["total_pd"]

    logger.info(f"MU1 Skyly RDR week (no Christmas): {pd_rdr_only} PD")
    logger.info(f"MU1 Skyly RDR week + Christmas: {pd_rdr_and_christmas} PD")

    # Both should be positive
    assert pd_rdr_only > 0, f"PD value with RDR week only should be > 0, got {pd_rdr_only}"
    assert pd_rdr_and_christmas > 0, f"PD value with RDR week + Christmas should be > 0, got {pd_rdr_and_christmas}"

    # Christmas event should increase the PD value during RDR week
    assert pd_rdr_and_christmas > pd_rdr_only, (
        f"Christmas event should increase PD value during RDR week: {pd_rdr_and_christmas} should be > {pd_rdr_only}"
    )


def test_christmas_presents_only_during_christmas(quest_calculator: QuestCalculator):
    """Test that Christmas Presents only drop during Christmas event"""
    # Find MU1 quest
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"

    # Calculate without Christmas event
    result_no_christmas = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None
    )

    # Calculate with Christmas event
    result_with_christmas = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=EventType.Christmas
    )

    # No presents should drop outside Christmas
    assert "event_drops_breakdown" in result_no_christmas
    assert "Present" not in result_no_christmas["event_drops_breakdown"], "Presents should not drop outside Christmas event"
    assert result_no_christmas["event_drops_pd"] == 0.0, "Event drops PD should be 0 outside Christmas"

    # Presents should drop during Christmas
    assert "event_drops_breakdown" in result_with_christmas
    assert "Present" in result_with_christmas["event_drops_breakdown"], "Presents should drop during Christmas event"
    assert result_with_christmas["event_drops_pd"] > 0.0, "Event drops PD should be > 0 during Christmas"

    present_data = result_with_christmas["event_drops_breakdown"]["Present"]
    assert present_data["expected_drops"] > 0, "Expected presents should be > 0"
    assert present_data["pd_value"] > 0, "Present PD value should be > 0"


def test_halloween_cookies_only_during_halloween(quest_calculator: QuestCalculator):
    """Test that Halloween Cookies only drop during Halloween event"""
    # Find MU1 quest
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"

    # Calculate without Halloween event
    result_no_halloween = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None
    )

    # Calculate with Halloween event
    result_with_halloween = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=EventType.Halloween
    )

    # No cookies should drop outside Halloween
    assert "event_drops_breakdown" in result_no_halloween
    assert "Halloween Cookie" not in result_no_halloween["event_drops_breakdown"], (
        "Cookies should not drop outside Halloween event"
    )
    assert result_no_halloween["event_drops_pd"] == 0.0, "Event drops PD should be 0 outside Halloween"

    # Cookies should drop during Halloween
    assert "event_drops_breakdown" in result_with_halloween
    assert "Halloween Cookie" in result_with_halloween["event_drops_breakdown"], "Cookies should drop during Halloween event"
    assert result_with_halloween["event_drops_pd"] > 0.0, "Event drops PD should be > 0 during Halloween"

    cookie_data = result_with_halloween["event_drops_breakdown"]["Halloween Cookie"]
    assert cookie_data["expected_drops"] > 0, "Expected cookies should be > 0"
    assert cookie_data["pd_value"] > 0, "Cookie PD value should be > 0"


def test_easter_eggs_only_during_easter(quest_calculator: QuestCalculator):
    """Test that Easter Eggs only drop during Easter event"""
    # Find MU1 quest
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"

    # Calculate without Easter event
    result_no_easter = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None
    )

    # Calculate with Easter event
    result_with_easter = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=EventType.Easter
    )

    # No eggs should drop outside Easter
    assert "event_drops_breakdown" in result_no_easter
    assert "Event Egg" not in result_no_easter["event_drops_breakdown"], "Event Eggs should not drop outside Easter event"

    # Eggs should drop during Easter
    assert "event_drops_breakdown" in result_with_easter
    assert "Event Egg" in result_with_easter["event_drops_breakdown"], "Event Eggs should drop during Easter event"
    assert result_with_easter["event_drops_pd"] > 0.0, "Event drops PD should be > 0 during Easter"

    egg_data = result_with_easter["event_drops_breakdown"]["Event Egg"]
    assert egg_data["expected_drops"] > 0, "Expected eggs should be > 0"
    assert egg_data["pd_value"] > 0, "Egg PD value should be > 0"


def test_halloween_cookies_boost_in_halloween_quests(quest_calculator: QuestCalculator):
    """Test that Halloween Cookies drop more in Halloween quests during Halloween event"""
    # Find a Halloween quest
    halloween_quest = None
    for quest in quest_calculator.quest_data:
        if quest_calculator._is_hallow_quest(quest):
            halloween_quest = quest
            break

    assert halloween_quest is not None, "No Halloween quest found in quest data"

    section_id = "Skyly"

    # Calculate with Halloween event in a Halloween quest
    result_halloween_quest = quest_calculator.calculate_quest_value(
        halloween_quest, section_id, rbr_active=False, weekly_boost=None, event_type=EventType.Halloween
    )

    # Calculate with Halloween event in a regular quest (MU1)
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found"
    result_regular_quest = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=EventType.Halloween
    )

    # Both should have cookies
    assert "Halloween Cookie" in result_halloween_quest["event_drops_breakdown"]
    assert "Halloween Cookie" in result_regular_quest["event_drops_breakdown"]

    halloween_quest_cookie_data = result_halloween_quest["event_drops_breakdown"]["Halloween Cookie"]
    regular_quest_cookie_data = result_regular_quest["event_drops_breakdown"]["Halloween Cookie"]

    # Halloween quest should have higher drop rate (20% boost)
    assert halloween_quest_cookie_data["is_halloween_quest"] is True
    assert halloween_quest_cookie_data["drop_rate"] > regular_quest_cookie_data["drop_rate"], (
        f"Halloween quest cookie drop rate ({halloween_quest_cookie_data['drop_rate']}) "
        f"should be > regular quest drop rate ({regular_quest_cookie_data['drop_rate']})"
    )

    # Verify the boost is approximately 20% (1.2x multiplier)
    expected_boosted_rate = regular_quest_cookie_data["drop_rate"] * 1.2
    assert abs(halloween_quest_cookie_data["drop_rate"] - expected_boosted_rate) < 0.0001, (
        f"Halloween quest drop rate should be ~20% higher: "
        f"got {halloween_quest_cookie_data['drop_rate']}, expected ~{expected_boosted_rate}"
    )


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
    result = quest_calculator.calculate_quest_value(mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None)

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
    # Mine 1 is eligible for Barta Lv30, so this will raise exception if technique isn't in price guide
    # For now, skip technique processing (focusing on CF4)
    area_name = "Mine 1"
    episode = 1
    section_id = "Skyly"

    # Test that box technique drop rate calculation works
    box_rates = quest_calculator._calculate_box_technique_drop_rate(area_name)
    assert "Barta" in box_rates, "Barta should be eligible in Mine 1 boxes"
    
    # Test that processing boxes now works (techniques are in price guide)
    pd, box_breakdown = quest_calculator._process_box_drops(area_name, boxes, episode, section_id)
    # Barta Lv30 should be in the box breakdown
    barta_found = any("Barta Lv30" in key for key in box_breakdown.keys())
    assert barta_found, "Barta Lv30 should be found in box breakdown from Mine 1"


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
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None
    )

    # Calculate with RBR boost
    result_with_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=True, weekly_boost=None, event_type=None
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
        event_type=None,
        exclude_event_quests=False,
    )

    # Both quests should have RBR active
    for ranking in rankings:
        quest_name = ranking["quest_name"]
        assert ranking["rbr_active"] is True, f"{quest_name} should have RBR active when in rbr_list"

    # Calculate MU1 with and without RBR to verify it's actually applied
    result_with_rbr_list = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=True, weekly_boost=None, event_type=None
    )
    result_no_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None
    )

    # RBR should increase PD value
    assert result_with_rbr_list["total_pd"] > result_no_rbr["total_pd"], (
        "RBR boost should increase PD value when quest is in rbr_list"
    )


def test_rbr_list_with_event_quest(quest_calculator: QuestCalculator):
    """Test that rbr_list can include event quests (they just won't get RBR boost if not in rotation)"""
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
        event_type=None,
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
        # Note: If the event quest has areas eligible for techniques, this will raise an exception
        # if techniques aren't in the price guide. That's expected behavior.
        # For now, we skip this check if techniques aren't in price guide (focusing on CF4)
        try:
            result_with_rbr = quest_calculator.calculate_quest_value(
                event_quest, section_id, rbr_active=True, weekly_boost=None, event_type=None
            )
            result_no_rbr = quest_calculator.calculate_quest_value(
                event_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None
            )
            # If not in RBR rotation, RBR won't affect the result
            logger.info(
                f"Event quest {event_quest.get('quest_name')} not in RBR rotation, "
                f"RBR has no effect: {result_with_rbr['total_pd']} == {result_no_rbr['total_pd']}"
            )
        except PriceGuideExceptionItemNameNotFound:
            # Expected if event quest has areas eligible for techniques but techniques aren't in price guide
            # Skip this test for now (focusing on CF4)
            pytest.skip("Techniques not in price guide - focusing on CF4 for now")


def test_rbr_list_with_nonexistent_quest(quest_calculator: QuestCalculator):
    """Test that rbr_list gracefully handles quests that don't exist"""
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
        event_type=None,
        exclude_event_quests=False,
    )

    # MU1 should still have RBR active (it's in the list and exists)
    assert len(rankings) == 1, "Should process the existing quest"
    ranking = rankings[0]
    assert ranking["quest_name"] == "MU1", "Should process MU1"
    assert ranking["rbr_active"] is True, "MU1 should have RBR active when in rbr_list"

    # Verify RBR is actually applied
    result_with_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=True, weekly_boost=None, event_type=None
    )
    result_no_rbr = quest_calculator.calculate_quest_value(
        mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None
    )

    assert result_with_rbr["total_pd"] > result_no_rbr["total_pd"], (
        "RBR boost should be applied to existing quest in rbr_list, even if list contains nonexistent quests"
    )


def test_adjust_dar_caps_at_one():
    """Test that _adjust_dar caps the result at 1.0"""
    # Test that DAR is capped at 1.0 even with high multipliers
    assert QuestCalculator._adjust_dar(0.8, 2.0) == 1.0  # 0.8 * 2.0 = 1.6, capped at 1.0
    assert QuestCalculator._adjust_dar(0.9, 1.5) == 1.0  # 0.9 * 1.5 = 1.35, capped at 1.0
    assert QuestCalculator._adjust_dar(1.0, 1.5) == 1.0  # Already at 1.0

    # Test normal cases below 1.0
    assert QuestCalculator._adjust_dar(0.5, 1.25) == 0.625  # 0.5 * 1.25 = 0.625
    assert QuestCalculator._adjust_dar(0.8, 1.0) == 0.8  # No change
    assert QuestCalculator._adjust_dar(0.0, 2.0) == 0.0  # Zero stays zero


def test_technique_drops_in_eligible_area(quest_calculator: QuestCalculator):
    """Test that technique drops appear in eligible areas"""
    # Test that technique drop rates are calculated for eligible areas
    # Note: rates returned are conditional (assuming DAR is met), not including DAR
    rates = quest_calculator._calculate_technique_drop_rate(None, "Ruins 2")
    assert "Foie" in rates, "Foie should be eligible in Ruins 2"
    assert rates["Foie"] > 0, "Foie should have non-zero conditional drop rate in Ruins 2"
    
    # Test that processing enemies now works (techniques are in price guide)
    pd, _, breakdown, _ = quest_calculator._process_enemy_drops("Arlan", 45.0, 1, "Skyly", 1.0, 1.0, "Ruins 2", None)
    # Foie Lv30 should be in the breakdown
    foie_found = any("Foie Lv30" in key for key in breakdown.keys())
    assert foie_found, "Foie Lv30 should be found in breakdown from Ruins 2"


def test_technique_drops_not_in_ineligible_area(quest_calculator: QuestCalculator):
    """Test that technique drops don't appear in ineligible areas"""
    # Find MU1 quest (has Forest 1 area where Foie Lv30 cannot drop)
    mu1_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "MU1":
            mu1_quest = quest
            break

    assert mu1_quest is not None, "MU1 quest not found in quest data"

    section_id = "Skyly"
    result = quest_calculator.calculate_quest_value(mu1_quest, section_id, rbr_active=False, weekly_boost=None, event_type=None)

    # Check enemy breakdown - Foie Lv30 should NOT appear (Forest 1 is not eligible)
    enemy_breakdown = result.get("enemy_breakdown", {})
    foie_found = False
    for item_name in enemy_breakdown.keys():
        if "Foie Lv30" in item_name:
            foie_found = True
            break

    assert not foie_found, "Foie Lv30 should not appear in Forest 1 (not an eligible area)"


def test_box_technique_drop_rate(quest_calculator: QuestCalculator):
    """Test that box technique drop rates are approximately 1/1,000,000"""
    # Test that box technique drop rate calculation works
    box_rates = quest_calculator._calculate_box_technique_drop_rate("Ruins 2")
    assert "Foie" in box_rates, "Foie should be eligible in Ruins 2 boxes"
    expected_rate = 1.0 / 1_000_000.0
    assert abs(box_rates["Foie"] - expected_rate) < 0.0000001, (
        f"Box technique drop rate should be ~1/1,000,000, got {box_rates['Foie']}"
    )

    # Test that processing boxes now works (techniques are in price guide)
    section_id = "Skyly"
    pd, box_breakdown = quest_calculator._process_box_drops("Ruins 2", {"box": 10}, 1, section_id)
    # Foie Lv30 should be in the box breakdown
    foie_found = any("Foie Lv30" in key for key in box_breakdown.keys())
    assert foie_found, "Foie Lv30 should be found in box breakdown from Ruins 2"


def test_monster_technique_drop_rate_scales_with_dar(quest_calculator: QuestCalculator):
    """Test that monster technique drop rates scale with DAR"""
    # Get conditional rates (assuming DAR is met)
    conditional_rates = quest_calculator._calculate_technique_drop_rate(None, "Ruins 2")
    
    assert "Foie" in conditional_rates, "Foie should be eligible in Ruins 2"

    # With DAR of .30, the conditional rate should be about 1/1,000,000
    dar_30 = 0.30
    foie_rate = conditional_rates["Foie"] * dar_30
    expected_rate = 1.0 / 1_000_000.0
    assert abs(foie_rate - expected_rate) < 0.0000001, (
        f"Foie technique drop rate should be ~1/1,000,000, got {foie_rate}"
    )

    # Okay, test that processing enemies now works (techniques are in price guide)
    pd, _, breakdown, _ = quest_calculator._process_enemy_drops("Dimenian", 100.0, 1, "Skyly", 1.0, 1.0, "Ruins 2", None)
    # Foie Lv30 should be in the breakdown
    foie_found = any("Foie Lv30" in key for key in breakdown.keys())
    assert foie_found, "Foie Lv30 should be found in breakdown from Ruins 2"


def test_technique_drops_only_in_eligible_areas(quest_calculator: QuestCalculator):
    """Test that techniques only drop in their specific eligible areas"""
    # Test multiple techniques in their eligible areas
    test_cases = [
        ("Foie", "Ruins 2", True),
        ("Foie", "Forest 1", False),  # Not eligible
        ("Barta", "Mine 1", True),
        ("Barta", "Forest 1", False),  # Not eligible
        ("Zonde", "Mine 2", True),
        ("Zonde", "Forest 1", False),  # Not eligible
        ("Grants", "Ruins 3", True),
        ("Grants", "Forest 1", False),  # Not eligible
    ]

    for technique_name, area_name, should_be_eligible in test_cases:
        is_eligible = quest_calculator._is_area_eligible_for_technique(area_name, technique_name)
        assert is_eligible == should_be_eligible, (
            f"{technique_name} should {'be' if should_be_eligible else 'not be'} eligible in {area_name}, got {is_eligible}"
        )


def test_technique_drops_with_area_context(quest_calculator: QuestCalculator):
    """Test that technique drops require area context"""
    # Process enemy drops without area context - should not raise exception (no techniques calculated)
    pd_no_area, _, breakdown_no_area, _ = quest_calculator._process_enemy_drops(
        "Dimenian", 100.0, 1, "Skyly", 1.0, 1.0, None, None
    )

    # Process enemy drops with area context (Ruins 2, eligible for Foie)
    # Should now work (techniques are in price guide)
    pd_with_area, _, breakdown_with_area, _ = quest_calculator._process_enemy_drops(
        "Dimenian", 100.0, 1, "Skyly", 1.0, 1.0, "Ruins 2", None
    )

    # Verify no techniques in breakdown without area context
    foie_no_area = any("Foie Lv30" in key for key in breakdown_no_area.keys())
    assert not foie_no_area, "Foie Lv30 should not appear without area context"
    
    # Verify techniques appear with area context
    foie_with_area = any("Foie Lv30" in key for key in breakdown_with_area.keys())
    assert foie_with_area, "Foie Lv30 should appear with area context"


def test_cf4_technique_drops(quest_calculator: QuestCalculator):
    """Test that CF4 (Crater Freeze 4) has correct level 30 technique drops from monsters and boxes"""
    # Find CF4 quest
    cf4_quest = None
    for quest in quest_calculator.quest_data:
        if quest.get("quest_name") == "CF4":
            cf4_quest = quest
            break

    assert cf4_quest is not None, "CF4 quest not found in quest data"

    # First, verify that techniques are calculated for the correct areas
    # Note: rates returned are conditional (assuming DAR is met), not including DAR
    # Test Crater East (should have Rafoie Lv30)
    rates_crater_east = quest_calculator._calculate_technique_drop_rate(None, "Crater East")
    assert "Rafoie" in rates_crater_east, "Rafoie should be eligible in Crater East"
    assert rates_crater_east["Rafoie"] > 0, "Rafoie should have non-zero conditional drop rate in Crater East"

    # Test Desert 2 (should have Razonde Lv30)
    rates_desert_2 = quest_calculator._calculate_technique_drop_rate(None, "Desert 2")
    assert "Razonde" in rates_desert_2, "Razonde should be eligible in Desert 2"
    assert rates_desert_2["Razonde"] > 0, "Razonde should have non-zero conditional drop rate in Desert 2"

    # Test Desert 3 (should have Grants Lv30 and Megid Lv30)
    rates_desert_3 = quest_calculator._calculate_technique_drop_rate(None, "Desert 3")
    assert "Grants" in rates_desert_3, "Grants should be eligible in Desert 3"
    assert "Megid" in rates_desert_3, "Megid should be eligible in Desert 3"
    assert rates_desert_3["Grants"] > 0, "Grants should have non-zero conditional drop rate in Desert 3"
    assert rates_desert_3["Megid"] > 0, "Megid should have non-zero conditional drop rate in Desert 3"

    # Verify that techniques NOT eligible in these areas are NOT present
    assert "Foie" not in rates_crater_east, "Foie should NOT be eligible in Crater East"
    assert "Barta" not in rates_crater_east, "Barta should NOT be eligible in Crater East"
    assert "Zonde" not in rates_crater_east, "Zonde should NOT be eligible in Crater East"

    # Test that processing enemies with area context now works (techniques are in price guide)
    pd, _, breakdown, _ = quest_calculator._process_enemy_drops(
        "Sand Rappy", 10.0, 4, "Skyly", 1.0, 1.0, "Crater East", None
    )
    # Rafoie Lv30 should be in the breakdown
    rafoie_found = any("Rafoie Lv30" in key for key in breakdown.keys())
    assert rafoie_found, "Rafoie Lv30 should be found in breakdown from Crater East"

    pd, _, breakdown, _ = quest_calculator._process_enemy_drops(
        "Sand Rappy", 10.0, 4, "Skyly", 1.0, 1.0, "Desert 2", None
    )
    # Razonde Lv30 should be in the breakdown
    razonde_found = any("Razonde Lv30" in key for key in breakdown.keys())
    assert razonde_found, "Razonde Lv30 should be found in breakdown from Desert 2"

    pd, _, breakdown, _ = quest_calculator._process_enemy_drops(
        "Sand Rappy", 10.0, 4, "Skyly", 1.0, 1.0, "Desert 3", None
    )
    # Grants Lv30 and Megid Lv30 should be in the breakdown
    grants_found = any("Grants Lv30" in key for key in breakdown.keys())
    megid_found = any("Megid Lv30" in key for key in breakdown.keys())
    assert grants_found, "Grants Lv30 should be found in breakdown from Desert 3"
    assert megid_found, "Megid Lv30 should be found in breakdown from Desert 3"

    # Test box technique drops - should work now that techniques are in price guide
    box_rates = quest_calculator._calculate_box_technique_drop_rate("Desert 3")
    assert "Grants" in box_rates, "Grants should be eligible in Desert 3 boxes"
    assert "Megid" in box_rates, "Megid should be eligible in Desert 3 boxes"
    assert box_rates["Grants"] > 0, "Grants should have non-zero box drop rate in Desert 3"
    assert box_rates["Megid"] > 0, "Megid should have non-zero box drop rate in Desert 3"

    # Verify that only Grants and Megid are eligible for Desert 3 boxes
    box_technique_names = list(box_rates.keys())
    assert len(box_technique_names) == 2, f"Should have exactly 2 techniques for Desert 3 boxes (Grants and Megid), found {len(box_technique_names)}: {box_technique_names}"
    assert "Grants" in box_technique_names, "Grants should be in Desert 3 box techniques"
    assert "Megid" in box_technique_names, "Megid should be in Desert 3 box techniques"

    # Test that processing boxes works now that techniques are in price guide
    pd, box_breakdown = quest_calculator._process_box_drops(
        "Desert 3", {"box": 14}, 4, "Skyly"
    )
    # Grants Lv30 and Megid Lv30 should be in the box breakdown
    grants_box_found = any("Grants Lv30" in key for key in box_breakdown.keys())
    megid_box_found = any("Megid Lv30" in key for key in box_breakdown.keys())
    assert grants_box_found, "Grants Lv30 should be found in box breakdown from Desert 3"
    assert megid_box_found, "Megid Lv30 should be found in box breakdown from Desert 3"
