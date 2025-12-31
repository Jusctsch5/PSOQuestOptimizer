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

from price_guide import BasePriceStrategy, PriceGuideExceptionItemNameNotFound, PriceGuideFixed

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
    assert len(fixed_price_guide.techniques_prices) > 0
    assert len(fixed_price_guide.tool_prices) > 0

    assert fixed_price_guide.srank_weapon_prices is not None


def test_weapon_pricing_basic(fixed_price_guide: PriceGuideFixed):
    """Test weapons with simple base prices"""
    # Test fixed base price with zero price
    assert fixed_price_guide.get_price_weapon("EVIL CURST", {}, 0, 0, "") == 0
    # Test fixed base price with non-zero price
    assert fixed_price_guide.get_price_weapon("DB's Saber (3064)", {}, 0, 0, "") != 0
    # Test range base price
    assert fixed_price_guide.get_price_weapon("EXCALIBUR", {}, 0, 0, "") != 0
    # Test item with only hit values
    assert fixed_price_guide.get_price_weapon("HANDGUN: GULD", {}, 0, 0, "") != 0


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
    for hit in range(0, 100, 5):
        # Test MINIMUM strategy
        fixed_price_guide.bps = BasePriceStrategy.MINIMUM
        price_min = fixed_price_guide.get_price_weapon("EXCALIBUR", {}, hit, 0, "")
        assert price_min != 0

        # Test MAXIMUM strategy
        fixed_price_guide.bps = BasePriceStrategy.MAXIMUM
        price_max = fixed_price_guide.get_price_weapon("EXCALIBUR", {}, hit, 0, "")
        assert price_max != 0
        assert price_max >= price_min

        # Test AVERAGE strategy
        fixed_price_guide.bps = BasePriceStrategy.AVERAGE
        price_avg = fixed_price_guide.get_price_weapon("EXCALIBUR", {}, hit, 0, "")
        assert price_avg != 0
        assert price_avg >= price_min
        assert price_avg <= price_max


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
    price = fixed_price_guide.get_price_weapon("M&A60 VISE", {}, 0, 0, "")
    assert price == 0

    # Test weapon
    price = fixed_price_guide.get_price_weapon("Snow Queen", {}, 0, 0, "")
    assert price != 0


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


def test_technique_disk_pricing_valid_level(fixed_price_guide: PriceGuideFixed):
    """Test technique disk pricing with valid levels"""
    pg = fixed_price_guide

    # Test Foie Lv30 - should return a price (50-70 range, average = 60)
    pg.bps = BasePriceStrategy.AVERAGE
    price = pg.get_price_disk("Foie", 30)
    assert price > 0, "Foie Lv30 should have a price"
    assert 50 <= price <= 70, f"Foie Lv30 should be in range 50-70, got {price}"

    # Test Rafoie Lv30 - should return a price (30-70 range)
    price = pg.get_price_disk("Rafoie", 30)
    assert price > 0, "Rafoie Lv30 should have a price"
    assert 30 <= price <= 70, f"Rafoie Lv30 should be in range 30-70, got {price}"

    # Test Grants Lv30 - should return a price (20-40 range)
    price = pg.get_price_disk("Grants", 30)
    assert price > 0, "Grants Lv30 should have a price"
    assert 20 <= price <= 40, f"Grants Lv30 should be in range 20-40, got {price}"


def test_technique_disk_pricing_worthless_levels(fixed_price_guide: PriceGuideFixed):
    """
    Test technique disk pricing with levels that are worthless
    e.g. lie under 15/20/30 maxes level of the different classes
    (well, excluding 29 and grants/megid levels)
    """
    pg = fixed_price_guide

    assert pg.get_price_disk("Foie", 14) == 0, "Foie Lv14 is worthless"
    assert pg.get_price_disk("Foie", 16) == 0, "Foie Lv16 is worthless"
    assert pg.get_price_disk("Foie", 19) == 0, "Foie Lv19 is worthless"
    assert pg.get_price_disk("Foie", 21) == 0, "Foie Lv21 is worthless"
    assert pg.get_price_disk("Foie", 28) == 0, "Foie Lv28 is worthless"

    assert pg.get_price_disk("Resta", 1) == 0, "Rafoie Lv1 is worthless"
    assert pg.get_price_disk("Grants", 10) == 0, "Grants Lv10 is worthless"

    assert pg.get_price_disk("Anti", 4) == 0, "A Lv15 is worthless"


def test_technique_disk_pricing_case_insensitive(fixed_price_guide: PriceGuideFixed):
    """Test that technique disk pricing is case-insensitive"""
    pg = fixed_price_guide

    pg.bps = BasePriceStrategy.AVERAGE
    price_upper = pg.get_price_disk("FOIE", 30)
    price_lower = pg.get_price_disk("foie", 30)
    price_mixed = pg.get_price_disk("Foie", 30)

    assert price_upper == price_lower == price_mixed, f"Case-insensitive lookup should work: {price_upper} == {price_lower} == {price_mixed}"


def test_technique_disk_pricing_different_strategies(fixed_price_guide: PriceGuideFixed):
    """Test technique disk pricing with different base price strategies"""
    pg = fixed_price_guide

    # Test MINIMUM strategy
    pg.bps = BasePriceStrategy.MINIMUM
    price_min = pg.get_price_disk("Foie", 30)
    assert price_min == 50, f"Foie Lv30 MINIMUM should be 50, got {price_min}"

    # Test MAXIMUM strategy
    pg.bps = BasePriceStrategy.MAXIMUM
    price_max = pg.get_price_disk("Foie", 30)
    assert price_max == 70, f"Foie Lv30 MAXIMUM should be 70, got {price_max}"

    # Test AVERAGE strategy
    pg.bps = BasePriceStrategy.AVERAGE
    price_avg = pg.get_price_disk("Foie", 30)
    assert price_avg == 60, f"Foie Lv30 AVERAGE should be 60, got {price_avg}"

    # Verify ordering
    assert price_min <= price_avg <= price_max, f"Price ordering should be: {price_min} <= {price_avg} <= {price_max}"


def test_technique_disk_pricing_negative(fixed_price_guide: PriceGuideFixed):
    """Test technique disk pricing negative cases"""
    pg = fixed_price_guide

    try:
        _ = pg.get_price_disk("Foie", 31)
        assert False, "Foie Lv31 does not exist"
    except PriceGuideExceptionItemNameNotFound:
        pass

    try:
        _ = pg.get_price_disk("Foie", 0)
        assert False, "Foie Lv0 does not exist"
    except PriceGuideExceptionItemNameNotFound:
        pass

    try:
        _ = pg.get_price_disk("Ryuker", 2)
        assert False, "Ryuker Lv2 does not exist"
    except PriceGuideExceptionItemNameNotFound:
        pass

    try:
        _ = pg.get_price_disk("Reverser", 2)
        assert False, "Reverser Lv2 does not exist"
    except PriceGuideExceptionItemNameNotFound:
        pass

    try:
        _ = pg.get_price_disk("Anti", 8)
        assert False, "Anti Lv8 does not exist"
    except PriceGuideExceptionItemNameNotFound:
        pass

    try:
        _ = pg.get_price_disk("NonExistentTechnique", 30)
        assert False, "NonExistentTechnique Lv30 does not exist"
    except PriceGuideExceptionItemNameNotFound:
        pass


def test_technique_disk_pricing_multiple_techniques(fixed_price_guide: PriceGuideFixed):
    """Test multiple different techniques to ensure they all work"""
    pg = fixed_price_guide
    pg.bps = BasePriceStrategy.AVERAGE

    techniques = [
        ("Barta", 30, 20, 40),
        ("Zonde", 30, 20, 40),
        ("Razonde", 30, 20, 40),
        ("Megid", 30, 25, 50),
        ("Gifoie", 30, 100, 130),
    ]

    for technique_name, level, min_price, max_price in techniques:
        price = pg.get_price_disk(technique_name, level)
        assert price > 0, f"{technique_name} Lv{level} should have a price"
        assert min_price <= price <= max_price, f"{technique_name} Lv{level} should be in range {min_price}-{max_price}, got {price}"
