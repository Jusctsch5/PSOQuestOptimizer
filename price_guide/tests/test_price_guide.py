"""
Test the price guide module

This module tests the price guide module by loading the price guide and testing the price guide's functionality.

The price guide is loaded from the price guide directory and the price guide is tested for the following:
- Price guide loading
- Price guide pricing

It should not test the exact pricing values, but rather the functionality of the price guide.
This is because the pricing values are dynamic and can change.
TODO, consider adding frozen price guide data to the test suite.
"""

import logging
from pathlib import Path

import pytest

from price_guide import BasePriceStrategy, PriceGuideFixed

PRICE_DATA_DIR = Path(__file__).parent.parent / "data"

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
    assert fixed_price_guide.get_price_weapon("DB's Saber (3064)", {}, 0, 0, "") == 0
    # Test range base price
    assert fixed_price_guide.get_price_weapon("EXCALIBUR", {}, 0, 0, "") != 0
    # Test item with only hit values
    assert fixed_price_guide.get_price_weapon("HANDGUN:GULD", {}, 0, 0, "") != 0


def test_weapon_hit_adjustments(fixed_price_guide: PriceGuideFixed):
    """Test weapons with hit value modifications"""

    # Validate that the price increases with listed hit value
    last_price = 0.0
    for hit in fixed_price_guide.weapon_prices["EXCALIBUR"]["hit_values"].keys():
        price = fixed_price_guide.get_price_weapon("EXCALIBUR", {}, int(hit), 0, "")
        logger.info(f"EXCALIBUR hit {hit} price: {price}")
        assert price >= last_price
        last_price = price

    # Validate that the price increases with arbitrary hit value
    last_price = 0.0
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
    assert fixed_price_guide.get_price_barrier("Bunny Ears", {}, {}) == 3
    assert fixed_price_guide.get_price_barrier("Cat Ears", {}, {}) == 3


def test_edge_cases(fixed_price_guide: PriceGuideFixed):
    """Test boundary conditions and special cases"""
    # Test weapon with invalid price formatc
    price = fixed_price_guide.get_price_weapon("M&A60 VISE", {}, 0, 0, "")
    assert price == 0  # No base price and hit 0 is 0

    # Test weapon with N/A values
    price = fixed_price_guide.get_price_weapon("Snow Queen", {}, 0, 0, "")
    assert price == 0  # N/A should be treated as 0


def test_price_guide_units(fixed_price_guide: PriceGuideFixed):
    """Test units with simple base prices"""
    assert fixed_price_guide.get_price_unit("Adept") != 0
    assert fixed_price_guide.get_price_unit("Centurion/Ability") != 0


def test_case_insensitive_lookups(fixed_price_guide: PriceGuideFixed):
    """Ensure case-insensitive lookups across all price categories."""
    pg = fixed_price_guide

    # Weapons
    assert pg.get_price_weapon("EXCALIBUR", {}, 0, 0, "") == pg.get_price_weapon("excalibur", {}, 0, 0, "")
    assert pg.get_price_weapon("HEAVEN STRIKER", {}, 45, 0, "") == pg.get_price_weapon("heaven striker", {}, 45, 0, "")

    # S-Rank weapons (with ability)
    assert pg.get_price_srank_weapon("ES BLADE", "BERSERK", 0, "") == pg.get_price_srank_weapon("es blade", "berserk", 0, "")

    # Frames
    assert pg.get_price_frame("Brightness Circle", {}, {}, 4, None) == pg.get_price_frame("brightness circle", {}, {}, 4, None)

    # Barriers
    assert pg.get_price_barrier("Bunny Ears", {}, {}) == pg.get_price_barrier("BuNNY Ears", {}, {})

    # Units
    assert pg.get_price_unit("Centurion/Ability") == pg.get_price_unit("centurion/ability")

    # Mags
    assert pg.get_price_mag("Dragon Scale", 0) == pg.get_price_mag("dragon scale", 0)

    # Cells
    assert pg.get_price_cell("Dragon Scale") == pg.get_price_cell("dragon scale")

    # Tools (e.g., AddSlot)
    assert pg.get_price_tool("AddSlot", 1) == pg.get_price_tool("addslot", 1)


def test_cannon_rouge_pricing(fixed_price_guide: PriceGuideFixed):
    """Test Cannon Rouge pricing - rare weapon with no base price, only hit values"""
    pg = fixed_price_guide

    # Test case-insensitive lookup
    weapon_data = pg.get_weapon_data("Cannon Rouge")
    assert weapon_data is not None, "Cannon Rouge should be found in weapon_prices"
    assert weapon_data == pg.get_weapon_data("CANNON ROUGE"), "Case-insensitive lookup should work"

    # Test 0-hit price (should be 2-3, average = 2.5)
    pg.bps = BasePriceStrategy.AVERAGE
    price_0_hit = pg.get_price_weapon("Cannon Rouge", {}, 0, 0, "")
    assert price_0_hit == 2.5, f"Cannon Rouge 0-hit should be 2.5 PD (average of 2-3), got {price_0_hit}"


def test_rare_weapons_no_inestimable_hit_values(fixed_price_guide: PriceGuideFixed):
    """Test that no rare weapons have 'Inestimable' hit values"""
    pg = fixed_price_guide

    weapons_with_inestimable = []

    # Check all weapons in weapon_prices (these are rare weapons)
    for weapon_name, weapon_data in pg.weapon_prices.items():
        hit_values = weapon_data.get("hit_values", {})
        if not hit_values:
            continue

        # Check each hit value
        for hit_key, hit_value in hit_values.items():
            # Check if the value is "Inestimable" (case-insensitive)
            if isinstance(hit_value, str) and hit_value.upper() in ["INESTIMABLE", "INEST"]:
                weapons_with_inestimable.append((weapon_name, hit_key, hit_value))

    # Assert no weapons have Inestimable hit values
    if weapons_with_inestimable:
        error_msg = "Found weapons with 'Inestimable' hit values:\n"
        for weapon_name, hit_key, hit_value in weapons_with_inestimable:
            error_msg += f"  {weapon_name}: hit {hit_key} = {hit_value}\n"

        print(weapons_with_inestimable)
        assert False, error_msg
