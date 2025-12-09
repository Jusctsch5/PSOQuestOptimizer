"""
Test the price guide module

This module tests the price guide module by loading the price guide and testing the price guide's functionality.

The price guide is loaded from the price guide directory and the price guide is tested for the following:
- Price guide loading
- Price guide pricing

It should not test the exact pricing values, but rather the functionality of the price guide.
This is because the pricing values are dynamic and can change.
"""

import pytest
from pathlib import Path
import logging

from pso_price_guide import PriceGuideFixed, BasePriceStrategy
from pathlib import Path

PRICE_DATA_DIR = Path(__file__).parent.parent / "pso_price_guide" / "data"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.fixture
def fixed_price_guide():
    return PriceGuideFixed(PRICE_DATA_DIR)


def test_price_guide_load(fixed_price_guide: PriceGuideFixed):
    """Test price guide loading"""
    assert fixed_price_guide.weapon_prices is not None
    assert len(fixed_price_guide.weapon_prices) > 0
    assert len(fixed_price_guide.srank_weapon_prices) > 0
    assert len(fixed_price_guide.frame_prices) > 0
    assert len(fixed_price_guide.barrier_prices) > 0
    assert len(fixed_price_guide.unit_prices) > 0
    assert len(fixed_price_guide.mag_prices) > 0
    assert len(fixed_price_guide.disk_prices) > 0
    assert len(fixed_price_guide.tool_prices) > 0

    assert fixed_price_guide.srank_weapon_prices is not None


def test_weapon_pricing_basic(fixed_price_guide: PriceGuideFixed):
    """Test weapons with simple base prices"""
    # Test fixed base price
    assert fixed_price_guide.get_price_weapon("DB's Saber 3064", {}, 0, 0, "") != 0
    # Test range base price
    assert fixed_price_guide.get_price_weapon("EXCALIBUR", {}, 0, 0, "") != 0
    # Test item with only hit values
    assert fixed_price_guide.get_price_weapon("HANDGUN:GULD", {}, 0, 0, "") != 0


def test_weapon_hit_adjustments(fixed_price_guide: PriceGuideFixed):
    """Test weapons with hit value modifications"""

    # Validate that the price increases with listed hit value
    last_price = 0
    for hit in fixed_price_guide.weapon_prices["EXCALIBUR"]["hit_values"].keys():
        price = fixed_price_guide.get_price_weapon("EXCALIBUR", {}, int(hit), 0, "")
        logger.info(f"EXCALIBUR hit {hit} price: {price}")
        assert price >= last_price
        last_price = price

    # Validate that the price increases with arbitrary hit value
    last_price = 0
    for hit in range(0, 100, 5):
        price = fixed_price_guide.get_price_weapon("EXCALIBUR", {}, int(hit), 0, "")
        logger.info(f"EXCALIBUR hit {hit} price: {price}")
        assert price >= last_price
        last_price = price


def test_pricing_strategies(fixed_price_guide: PriceGuideFixed):
    """Test different base price strategies"""
    # Test MINIMUM strategy
    fixed_price_guide.bps = BasePriceStrategy.MINIMUM
    assert fixed_price_guide.get_price_weapon("EXCALIBUR", {}, 0, 0, "") == 9

    # Test MAXIMUM strategy
    fixed_price_guide.bps = BasePriceStrategy.MAXIMUM
    assert fixed_price_guide.get_price_weapon("EXCALIBUR", {}, 0, 0, "") == 12

    # Test AVERAGE strategy
    fixed_price_guide.bps = BasePriceStrategy.AVERAGE
    assert fixed_price_guide.get_price_weapon("EXCALIBUR", {}, 0, 0, "") == 10.5


def test_special_weapons(fixed_price_guide: PriceGuideFixed):
    """Test weapons with unique pricing structures"""

    price = fixed_price_guide.get_price_weapon("VJAYA", {}, 0, 0, "")
    assert price == 0  # Base is 0

    # Test weapon with both base and hit values
    price = fixed_price_guide.get_price_weapon("VJAYA", {}, 35, 0, "")
    assert price == 1  # Base is 0 + hit value 1

    # Test weapon with only hit values
    price = fixed_price_guide.get_price_weapon("HEAVEN STRIKER", {}, 45, 0, "")
    assert 2500 <= price <= 3000


def test_srank_weapons(fixed_price_guide: PriceGuideFixed):
    """Test S-rank weapons with unique pricing structures"""

    # Test weapon with only base price
    price = fixed_price_guide.get_price_srank_weapon("ES BLADE", "", 0, "")
    assert price == 35

    # Test weapon with both base and ability price
    price = fixed_price_guide.get_price_srank_weapon("ES BLADE", "HP REVIVAL", 0, "")
    assert price == 35 + 30
    price = fixed_price_guide.get_price_srank_weapon("ES BLADE", "BERSERK", 0, "")
    assert price == 35 + 40
    price = fixed_price_guide.get_price_srank_weapon("ES BLADE", "ZALURE", 0, "")
    assert price == 35 + 60
    price = fixed_price_guide.get_price_srank_weapon("ES BLADE", "KING'S", 0, "")
    assert price == 35 + 40


def test_frame_pricing(fixed_price_guide: PriceGuideFixed):
    """Test frames with unique pricing structures"""
    price = fixed_price_guide.get_price_frame("Brightness Circle", {}, {}, 4, None)
    assert price == 12


def test_price_guide_barriers(fixed_price_guide: PriceGuideFixed):
    """Test barriers with simple base prices"""
    assert fixed_price_guide.get_price_barrier("Adept") == 38
    assert fixed_price_guide.get_price_barrier("Centurion/Ability") == 7


def test_edge_cases(fixed_price_guide: PriceGuideFixed):
    """Test boundary conditions and special cases"""
    # Test weapon with invalid price formatc
    price = fixed_price_guide.get_price_weapon("M&A60 VISE", {}, 0, 0, "")
    assert price == 0  # No base price and hit 0 is 0

    # Test weapon with N/A values
    price = fixed_price_guide.get_price_weapon("Snow Queen", {}, 0, 0, "")
    assert price == 0  # N/A should be treated as 0


def test_grinder_and_element_adjustments(fixed_price_guide: PriceGuideFixed):
    """Test weapons with grinder and element modifications (if implemented)"""
    # This would need implementation details to test properly
    price = fixed_price_guide.get_price_weapon("EXCALIBUR", {}, 10, 0, "Fire")
    assert price
    # Add appropriate assertions based on your implementation


def test_price_guide_units(fixed_price_guide: PriceGuideFixed):
    """Test units with simple base prices"""
    assert fixed_price_guide.get_price_unit("Adept") == 38
    assert fixed_price_guide.get_price_unit("Centurion/Ability") == 7
