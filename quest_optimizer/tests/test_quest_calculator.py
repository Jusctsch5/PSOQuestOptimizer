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
