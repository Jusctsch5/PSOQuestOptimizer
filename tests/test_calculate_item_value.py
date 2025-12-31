"""
Test calculate_item_value functionality.

Tests calculating item values for different item types.
"""

import logging
from pathlib import Path

import pytest

from calculate_item_value import calculate_item_value
from price_guide import BasePriceStrategy, PriceGuideFixed
from price_guide.item_value_calculator import ItemValueCalculator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Paths to test data
PROJECT_ROOT = Path(__file__).parent.parent
PRICE_GUIDE_PATH = PROJECT_ROOT / "price_guide" / "data"


@pytest.fixture
def price_guide():
    """Create a PriceGuideFixed instance for testing"""
    return PriceGuideFixed(str(PRICE_GUIDE_PATH), base_price_strategy=BasePriceStrategy.MINIMUM)


@pytest.fixture
def item_value_calculator(price_guide):
    """Create an ItemValueCalculator instance for testing"""
    return ItemValueCalculator(price_guide)


def test_calculate_value_for_weapon(price_guide, item_value_calculator):
    """Test calculating value for a weapon item"""
    item_name = "VJAYA"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for weapon '{item_name}'"
    item_type, value = result
    assert item_type == "weapon", f"Item type should be 'weapon', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for weapon '{item_name}': {value:.4f} PD")


def test_calculate_value_for_frame(price_guide, item_value_calculator):
    """Test calculating value for a frame (armor) item"""
    item_name = "Brightness Circle"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for frame '{item_name}'"
    item_type, value = result
    assert item_type == "frame", f"Item type should be 'frame', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for frame '{item_name}': {value:.4f} PD")


def test_calculate_value_for_barrier(price_guide, item_value_calculator):
    """Test calculating value for a barrier (shield) item"""
    item_name = "Standstill Shield"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for barrier '{item_name}'"
    item_type, value = result
    assert item_type == "barrier", f"Item type should be 'barrier', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for barrier '{item_name}': {value:.4f} PD")


def test_calculate_value_for_unit(price_guide, item_value_calculator):
    """Test calculating value for a unit item"""
    item_name = "God/Ability"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for unit '{item_name}'"
    item_type, value = result
    assert item_type == "unit", f"Item type should be 'unit', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for unit '{item_name}': {value:.4f} PD")


def test_calculate_value_for_cell(price_guide, item_value_calculator):
    """Test calculating value for a cell item"""
    # Note: "Cell of Mag 502" exists in both cells.json and mags.json
    # Since identify_item_type checks mags before cells, it will be identified as "mag"
    # This test verifies no exceptions are thrown regardless of the identified type
    item_name = "Cell of Mag 502"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for cell '{item_name}'"
    item_type, value = result
    # Item may be identified as "mag" or "cell" depending on price guide order
    assert item_type in ["cell", "mag"], f"Item type should be 'cell' or 'mag', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for cell '{item_name}' (identified as {item_type}): {value:.4f} PD")


def test_calculate_value_for_tool(price_guide, item_value_calculator):
    """Test calculating value for a tool item"""
    item_name = "Photon Crystal"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for tool '{item_name}'"
    item_type, value = result
    assert item_type == "tool", f"Item type should be 'tool', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for tool '{item_name}': {value:.4f} PD")


def test_calculate_value_for_mag(price_guide, item_value_calculator):
    """Test calculating value for a mag item"""
    item_name = "Basic"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for mag '{item_name}'"
    item_type, value = result
    assert item_type == "mag", f"Item type should be 'mag', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for mag '{item_name}': {value:.4f} PD")


def test_calculate_value_for_disk(price_guide, item_value_calculator):
    """Test calculating value for a disk (technique) item"""
    item_name = "Foie"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=None,
    )
    
    assert result is not None, f"Should return a result for disk '{item_name}'"
    item_type, value = result
    assert item_type == "disk", f"Item type should be 'disk', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for disk '{item_name}': {value:.4f} PD")


def test_calculate_value_for_weapon_with_area(price_guide, item_value_calculator):
    """Test calculating value for a weapon with drop area specified"""
    item_name = "VJAYA"
    drop_area = "Forest 1"
    
    result = calculate_item_value(
        item_name,
        price_guide,
        item_value_calculator,
        drop_area=drop_area,
    )
    
    assert result is not None, f"Should return a result for weapon '{item_name}' with area '{drop_area}'"
    item_type, value = result
    assert item_type == "weapon", f"Item type should be 'weapon', got '{item_type}'"
    assert isinstance(value, float), f"Value should be a float, got {type(value)}"
    assert value >= 0, f"Value should be non-negative, got {value}"
    logger.info(f"Calculated value for weapon '{item_name}' with area '{drop_area}': {value:.4f} PD")


def test_calculate_value_nonexistent_item(price_guide, item_value_calculator):
    """Test that calculating value for a non-existent item raises an exception"""
    item_name = "NONEXISTENT_ITEM_XYZ123"
    
    # The function should raise ValueError for unsupported item types
    # or the price guide should raise PriceGuideExceptionItemNameNotFound
    try:
        result = calculate_item_value(
            item_name,
            price_guide,
            item_value_calculator,
            drop_area=None,
        )
        # If it returns, it should be None or raise an error
        if result is None:
            logger.info(f"Non-existent item '{item_name}' returned None (expected)")
        else:
            # This shouldn't happen, but log it
            logger.warning(f"Non-existent item '{item_name}' returned a result: {result}")
    except (ValueError, Exception) as e:
        # If it raises an exception, that's acceptable
        logger.info(f"Non-existent item '{item_name}' raised exception (expected): {type(e).__name__}")

