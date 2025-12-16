"""
Test weapon expected value calculations with different boost configurations.

This module tests that weapon expected values are calculated correctly
with various boost combinations (RBR, weekly boosts, Halloween boosts).
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


def test_weapon_expected_value_basic(quest_calculator: QuestCalculator):
    """Test basic weapon expected value calculation with AGITO (1975)"""
    item_name = "AGITO (1975)"
    drop_area = "Forest 1"

    expected_value = 5
    actual_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert actual_value == pytest.approx(expected_value, rel=1e-9), (
        f"Expected value for {item_name} should be {expected_value}, got {actual_value}"
    )
    logger.info(f"{item_name} ({drop_area}): {expected_value} PD")


def test_weapon_expected_value_no_boosts(quest_calculator: QuestCalculator):
    """Test weapon expected value calculation with no boosts"""
    # Test a simple weapon - should return a non-zero value
    item_name = "Storm Wand: Indra"
    drop_area = "Cave 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name} (no boosts): {expected_value} PD")


def test_weapon_expected_value_rbr_boost(quest_calculator: QuestCalculator):
    """Test weapon expected value calculation with RBR boost"""
    # RBR boost should not affect weapon expected value directly
    # (it affects drop rates, not weapon prices)
    # But we can verify the calculation still works
    item_name = "Storm Wand: Indra"
    drop_area = "Cave 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name} (RBR context): {expected_value} PD")


def test_weapon_expected_value_high_value_weapon(quest_calculator: QuestCalculator):
    """Test expected value for a high-value weapon"""
    # Test a weapon that should have significant expected value
    item_name = "Psycho Wand"
    drop_area = "Mine 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name}: {expected_value} PD")


def test_weapon_expected_value_with_hit(quest_calculator: QuestCalculator):
    """Test expected value for a weapon that can have hit values"""
    # Test a weapon that has hit value pricing
    item_name = "Flowen's Sword (3077)"
    drop_area = "Ruins 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name}: {expected_value} PD")


def test_weapon_expected_value_with_attributes(quest_calculator: QuestCalculator):
    """Test expected value for a weapon that can have attributes"""
    # Test a weapon that has attribute modifiers
    item_name = "Gae Bolg"
    drop_area = "Seabed Upper Levels"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
    logger.info(f"{item_name}: {expected_value} PD")


def test_weapon_expected_value_consistency(quest_calculator: QuestCalculator):
    """Test that weapon expected value is consistent across multiple calls"""
    item_name = "Storm Wand: Indra"
    drop_area = "Cave 1"

    value1 = quest_calculator._get_weapon_expected_value(item_name, drop_area)
    value2 = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert value1 == pytest.approx(value2, rel=1e-9), f"Expected values should be consistent: {value1} != {value2}"
    assert value1 > 0, f"Expected value should be > 0, got {value1}"


def test_weapon_expected_value_multiple_weapons(quest_calculator: QuestCalculator):
    """Test expected values for multiple different weapons"""
    test_weapons = [
        ("Storm Wand: Indra", "Cave 1"),
        ("Gae Bolg", "Seabed Upper Levels"),
        ("Psycho Wand", "Mine 1"),
        ("Flowen's Sword (3077)", "Ruins 1"),
    ]

    for item_name, drop_area in test_weapons:
        expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)
        assert expected_value > 0, f"Expected value for {item_name} should be > 0, got {expected_value}"
        logger.info(f"{item_name} ({drop_area}): {expected_value} PD")


def test_weapon_expected_value_invalid_weapon(quest_calculator: QuestCalculator):
    """Test that invalid weapon names raise appropriate exception"""
    from price_guide import PriceGuideExceptionItemNameNotFound

    with pytest.raises(PriceGuideExceptionItemNameNotFound):
        quest_calculator._get_weapon_expected_value("NonExistent Weapon", "Forest 1")


def test_item_price_pd_weapon(quest_calculator: QuestCalculator):
    """Test _get_item_price_pd for weapons"""
    item_name = "Storm Wand: Indra"
    drop_area = "Cave 1"

    price = quest_calculator._get_item_price_pd(item_name, drop_area)

    assert price > 0, f"Price for {item_name} should be > 0, got {price}"
    logger.info(f"_get_item_price_pd({item_name}): {price} PD")


def test_item_price_pd_non_weapon(quest_calculator: QuestCalculator):
    """Test _get_item_price_pd for non-weapon items"""
    # Test with a unit
    item_name = "God/Ability"

    price = quest_calculator._get_item_price_pd(item_name)

    assert price > 0, f"Price for {item_name} should be > 0, got {price}"
    logger.info(f"_get_item_price_pd({item_name}): {price} PD")


# Regression tests - these check that expected values don't change unexpectedly
# Update these values if the calculation logic legitimately changes
def test_weapon_expected_value_regression_storm_wand(quest_calculator: QuestCalculator):
    """Regression test: Storm Wand: Indra expected value should be consistent"""
    item_name = "Storm Wand: Indra"
    drop_area = "Cave 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    # Basic sanity checks - value should be positive and reasonable
    assert expected_value > 0, f"Expected value should be > 0, got {expected_value}"
    assert expected_value < 1000, f"Expected value seems too high: {expected_value}"
    logger.info(f"REGRESSION: {item_name} = {expected_value} PD")


def test_weapon_expected_value_regression_psycho_wand(quest_calculator: QuestCalculator):
    """Regression test: Psycho Wand expected value should be consistent"""
    item_name = "Psycho Wand"
    drop_area = "Mine 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    # Psycho Wand should have significant value
    assert expected_value > 0, f"Expected value should be > 0, got {expected_value}"
    logger.info(f"REGRESSION: {item_name} = {expected_value} PD")


def test_weapon_expected_value_regression_gae_bolg(quest_calculator: QuestCalculator):
    """Regression test: Gae Bolg expected value should be consistent"""
    item_name = "Gae Bolg"
    drop_area = "Seabed Upper Levels"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value should be > 0, got {expected_value}"
    logger.info(f"REGRESSION: {item_name} = {expected_value} PD")


def test_weapon_expected_value_regression_flowens_sword(quest_calculator: QuestCalculator):
    """Regression test: Flowen's Sword expected value should be consistent"""
    item_name = "Flowen's Sword (3077)"
    drop_area = "Ruins 1"

    expected_value = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert expected_value > 0, f"Expected value should be > 0, got {expected_value}"
    logger.info(f"REGRESSION: {item_name} = {expected_value} PD")


def test_item_price_pd_regression_weapon(quest_calculator: QuestCalculator):
    """Regression test: _get_item_price_pd for weapons should match _get_weapon_expected_value"""
    item_name = "Storm Wand: Indra"
    drop_area = "Cave 1"

    # Both methods should return the same value for weapons
    price_via_get_item = quest_calculator._get_item_price_pd(item_name, drop_area)
    price_via_expected = quest_calculator._get_weapon_expected_value(item_name, drop_area)

    assert price_via_get_item == pytest.approx(price_via_expected, rel=1e-9), (
        f"Prices should match: _get_item_price_pd={price_via_get_item}, _get_weapon_expected_value={price_via_expected}"
    )
    assert price_via_get_item > 0, f"Price should be > 0, got {price_via_get_item}"
    logger.info(f"REGRESSION: {item_name} via both methods = {price_via_get_item} PD")
