"""
Test weapon expected value calculations with different boost configurations.

This module tests that weapon expected values are calculated correctly
with various boost combinations (RBR, weekly boosts, Halloween boosts).
"""

import logging
from pathlib import Path

import pytest

from price_guide import PriceGuideExceptionItemNameNotFound
from quest_optimizer.quest_calculator import QuestCalculator

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


def test_weapon_expected_value_simple(quest_calculator: QuestCalculator):
    """Test rare weapon expected value calculation"""

    # Test a weapon that is worth nothing.
    item_name = "Gae Bolg"
    drop_area = "Seabed Upper Levels"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value == 0, f"Expected value for {item_name} should be 0, got {expected_value}"
    logger.info(f"{item_name}: {expected_value} PD")

    item_name = "AGITO (1975)"
    drop_area = "Forest 1"

    expected_value = 5
    actual_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert actual_value == pytest.approx(expected_value, rel=1e-9), (
        f"Expected value for {item_name} should be {expected_value}, got {actual_value}"
    )

    # Test a weapon that has hit value pricing
    item_name = "Flowen's Sword (3077)"
    drop_area = "Ruins 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name}: {expected_value} PD")

    # Test a weapon that should have significant expected value
    item_name = "Psycho Wand"
    drop_area = "Mine 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name}: {expected_value} PD")

    # Test a weapon that has attribute modifiers, and is worth something.
    item_name = "EXCALIBUR"
    drop_area = "Mine 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name}: {expected_value} PD")


def test_weapon_expected_value_invalid_weapon(quest_calculator: QuestCalculator):
    """Test that invalid weapon names raise appropriate exception"""

    with pytest.raises(PriceGuideExceptionItemNameNotFound):
        quest_calculator._get_weapon_expected_value("NonExistent Weapon", "Forest 1")
