"""
Tests for ArmorValueCalculator uniform joint DFP×EVP expected value.

Max tier requires both DFP and EVP at range max. Primary axis (DFP for frames,
EVP for barriers) drives Min→Med→High; max primary alone uses High.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from drop_tables.armor_stat_ranges import ArmorStatRanges
from price_guide import (
    BasePriceStrategy,
    PriceGuideExceptionItemNameNotFound,
    PriceGuideFixed,
)
from price_guide.armor_value_calculator import (
    ArmorValueCalculator,
    interpolate_tier_price,
)
from price_guide.price_guide import PriceGuideAbstract

PROJECT_ROOT = Path(__file__).parent.parent.parent
PRICE_GUIDE_PATH = PROJECT_ROOT / "price_guide" / "data"


class FakePriceGuide:
    """Minimal price guide surface for ArmorValueCalculator unit tests."""

    def __init__(
        self,
        frame_prices: Optional[Dict[str, Any]] = None,
        barrier_prices: Optional[Dict[str, Any]] = None,
        bps: BasePriceStrategy = BasePriceStrategy.MINIMUM,
    ):
        self.bps = bps
        self.frame_prices = frame_prices or {}
        self.barrier_prices = barrier_prices or {}

    def _ci_key(self, mapping: Dict[str, Any], name: str) -> Optional[str]:
        return PriceGuideAbstract._ci_key(mapping, name)

    def get_price_from_range(self, price_range, bps):
        return PriceGuideAbstract.get_price_from_range(price_range, bps)


def _tiered_frame_guide(**overrides: Any) -> FakePriceGuide:
    data = {
        "base": "1",
        "Min Stat": "1",
        "Med Stat": "3",
        "High Stat": "5",
        "Max Stat": "100",
    }
    data.update(overrides)
    return FakePriceGuide(frame_prices={"Test Frame": data})


def _tiered_barrier_guide(**overrides: Any) -> FakePriceGuide:
    data = {
        "base": "2",
        "Min Stat": "2",
        "Med Stat": "4",
        "High Stat": "6",
        "Max EVP": "50",
    }
    data.update(overrides)
    return FakePriceGuide(barrier_prices={"Test Shield": data})


@pytest.fixture
def real_price_guide() -> PriceGuideFixed:
    return PriceGuideFixed(str(PRICE_GUIDE_PATH), base_price_strategy=BasePriceStrategy.MINIMUM)


def test_interpolate_tier_price_anchors():
    assert interpolate_tier_price(0.0, 1, 5, 9) == pytest.approx(1.0)
    assert interpolate_tier_price(0.5, 1, 5, 9) == pytest.approx(5.0)
    assert interpolate_tier_price(1.0, 1, 5, 9) == pytest.approx(9.0)
    assert interpolate_tier_price(0.25, 1, 5, 9) == pytest.approx(3.0)
    assert interpolate_tier_price(0.75, 1, 5, 9) == pytest.approx(7.0)


def test_fixed_stat_frame_uses_max_when_both_fixed():
    guide = FakePriceGuide(frame_prices={"Dress Plate": {"base": "15-20"}})
    ranges = ArmorStatRanges.from_dicts(
        frames={"Dress Plate": {"dfp": [30, 30], "evp": [30, 30]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    # Both fixed ⇒ both max; tiers collapse to base MINIMUM 15
    assert calc.calculate_frame_expected_value("Dress Plate") == pytest.approx(15.0)
    breakdown = calc.get_frame_value_breakdown("Dress Plate")
    assert len(breakdown["roll_details"]) == 1
    assert breakdown["roll_details"][0]["dfp"] == 30
    assert breakdown["roll_details"][0]["evp"] == 30
    assert breakdown["roll_details"][0]["both_max"] is True
    assert breakdown["roll_details"][0]["probability"] == pytest.approx(1.0)


def test_uniform_dfp_with_fixed_evp_exact_expectation():
    """
    DFP 10-12, EVP fixed 0 → three outcomes (EVP always max).
      10 → min=1
      11 → high=5
      12 → both max → 100
    """
    guide = _tiered_frame_guide()
    ranges = ArmorStatRanges.from_dicts(
        frames={"Test Frame": {"dfp": [10, 12], "evp": [0, 0]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    expected = (1.0 + 5.0 + 100.0) / 3.0
    assert calc.calculate_frame_expected_value("Test Frame") == pytest.approx(expected)

    breakdown = calc.get_frame_value_breakdown("Test Frame")
    assert len(breakdown["roll_details"]) == 3
    prices = [d["price"] for d in breakdown["roll_details"]]
    assert prices == pytest.approx([1.0, 5.0, 100.0])
    assert [d["both_max"] for d in breakdown["roll_details"]] == [False, False, True]
    assert [d["evp"] for d in breakdown["roll_details"]] == [0, 0, 0]


def test_max_requires_both_dfp_and_evp():
    """
    DFP 10-11, EVP 20-21 → 4 joint outcomes.
    Max=100 only on (11,21). Max DFP with non-max EVP → High=5.

      (10,20) (10,21) → min=1
      (11,20) → high=5
      (11,21) → max=100
    """
    guide = _tiered_frame_guide()
    ranges = ArmorStatRanges.from_dicts(
        frames={"Test Frame": {"dfp": [10, 11], "evp": [20, 21]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    expected = (1.0 + 1.0 + 5.0 + 100.0) / 4.0
    assert calc.calculate_frame_expected_value("Test Frame") == pytest.approx(expected)

    breakdown = calc.get_frame_value_breakdown("Test Frame")
    assert len(breakdown["roll_details"]) == 4
    by_pair = {(d["dfp"], d["evp"]): d for d in breakdown["roll_details"]}

    assert by_pair[(10, 20)]["price"] == pytest.approx(1.0)
    assert by_pair[(10, 20)]["both_max"] is False
    assert by_pair[(10, 21)]["price"] == pytest.approx(1.0)
    assert by_pair[(10, 21)]["both_max"] is False
    assert by_pair[(11, 20)]["price"] == pytest.approx(5.0)
    assert by_pair[(11, 20)]["both_max"] is False
    assert by_pair[(11, 21)]["price"] == pytest.approx(100.0)
    assert by_pair[(11, 21)]["both_max"] is True

    for detail in breakdown["roll_details"]:
        assert detail["probability"] == pytest.approx(0.25)

    display = calc.get_frame_calculation_breakdown("Test Frame")
    assert display["outcome_count"] == 4
    assert display["dfp_outcomes"] == 2
    assert display["evp_outcomes"] == 2
    assert display["both_max_probability"] == pytest.approx(0.25)
    assert display["both_max_contribution"] == pytest.approx(100.0 * 0.25)
    assert display["primary_stat"] == "dfp"


def test_max_dfp_alone_is_high_not_max():
    """Max DFP with any non-max EVP must not receive Max Stat."""
    guide = _tiered_frame_guide()
    ranges = ArmorStatRanges.from_dicts(
        frames={"Test Frame": {"dfp": [10, 12], "evp": [1, 3]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    breakdown = calc.get_frame_value_breakdown("Test Frame")
    assert len(breakdown["roll_details"]) == 9  # 3×3

    dual_max = next(d for d in breakdown["roll_details"] if d["both_max"])
    assert dual_max["dfp"] == 12
    assert dual_max["evp"] == 3
    assert dual_max["price"] == pytest.approx(100.0)
    assert dual_max["probability"] == pytest.approx(1.0 / 9.0)

    for evp in (1, 2):
        roll = next(d for d in breakdown["roll_details"] if d["dfp"] == 12 and d["evp"] == evp)
        assert roll["both_max"] is False
        assert roll["price"] == pytest.approx(5.0)

    # Dual-max probability is 1/(3*3)
    display = calc.get_frame_calculation_breakdown("Test Frame")
    assert display["both_max_probability"] == pytest.approx(1.0 / 9.0)


def test_max_dfp_key_is_recognized():
    guide = FakePriceGuide(
        frame_prices={
            "Crimson Coat": {
                "base": "1",
                "Min Stat": "1",
                "Med Stat": "2",
                "High Stat": "5",
                "Max DFP": "25",
            }
        }
    )
    ranges = ArmorStatRanges.from_dicts(
        frames={"Crimson Coat": {"dfp": [158, 170], "evp": [136, 148]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    breakdown = calc.get_frame_value_breakdown("Crimson Coat")
    assert breakdown["tier_prices"]["max"] == pytest.approx(25.0)
    assert breakdown["tier_prices"]["max_key"] == "Max DFP"
    assert len(breakdown["roll_details"]) == 13 * 13  # 158..170 × 136..148

    dual_max = next(d for d in breakdown["roll_details"] if d["both_max"])
    assert dual_max["dfp"] == 170
    assert dual_max["evp"] == 148
    assert dual_max["price"] == pytest.approx(25.0)

    max_dfp_only = next(d for d in breakdown["roll_details"] if d["dfp"] == 170 and d["evp"] == 136)
    assert max_dfp_only["both_max"] is False
    assert max_dfp_only["price"] == pytest.approx(5.0)


def test_barrier_max_requires_both_stats():
    """
    EVP primary. Max EVP alone → High; both max → Max EVP.
      (1,10) (2,10) → min=2
      (1,11) → high=6
      (2,11) → max=50
    """
    guide = _tiered_barrier_guide()
    ranges = ArmorStatRanges.from_dicts(
        barriers={"Test Shield": {"dfp": [1, 2], "evp": [10, 11]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    expected = (2.0 + 2.0 + 6.0 + 50.0) / 4.0
    assert calc.calculate_barrier_expected_value("Test Shield") == pytest.approx(expected)

    breakdown = calc.get_barrier_value_breakdown("Test Shield")
    assert breakdown["primary_stat"] == "evp"
    assert breakdown["tier_prices"]["max_key"] == "Max EVP"
    assert len(breakdown["roll_details"]) == 4

    by_pair = {(d["dfp"], d["evp"]): d for d in breakdown["roll_details"]}
    assert by_pair[(1, 10)]["price"] == pytest.approx(2.0)
    assert by_pair[(2, 10)]["price"] == pytest.approx(2.0)
    assert by_pair[(1, 11)]["price"] == pytest.approx(6.0)
    assert by_pair[(1, 11)]["both_max"] is False
    assert by_pair[(2, 11)]["price"] == pytest.approx(50.0)
    assert by_pair[(2, 11)]["both_max"] is True

    display = calc.get_barrier_calculation_breakdown("Test Shield")
    assert display["both_max_probability"] == pytest.approx(0.25)
    assert display["both_max_contribution"] == pytest.approx(50.0 * 0.25)
    assert display["primary_stat"] == "evp"


def test_barrier_max_evp_alone_is_high_not_max():
    guide = _tiered_barrier_guide()
    ranges = ArmorStatRanges.from_dicts(
        barriers={"Test Shield": {"dfp": [1, 3], "evp": [10, 12]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    breakdown = calc.get_barrier_value_breakdown("Test Shield")
    assert len(breakdown["roll_details"]) == 9

    for dfp in (1, 2):
        roll = next(d for d in breakdown["roll_details"] if d["evp"] == 12 and d["dfp"] == dfp)
        assert roll["both_max"] is False
        assert roll["price"] == pytest.approx(6.0)

    dual_max = next(d for d in breakdown["roll_details"] if d["both_max"])
    assert dual_max["dfp"] == 3 and dual_max["evp"] == 12
    assert dual_max["price"] == pytest.approx(50.0)


def test_price_for_stats_direct():
    guide = _tiered_frame_guide()
    ranges = ArmorStatRanges.from_dicts(
        frames={"Test Frame": {"dfp": [10, 12], "evp": [20, 22]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]
    tiers = calc.get_frame_value_breakdown("Test Frame")["tier_prices"]

    assert calc.price_for_stats(10, 20, 10, 12, 20, 22, "dfp", tiers) == pytest.approx(1.0)
    assert calc.price_for_stats(12, 20, 10, 12, 20, 22, "dfp", tiers) == pytest.approx(5.0)
    assert calc.price_for_stats(12, 22, 10, 12, 20, 22, "dfp", tiers) == pytest.approx(100.0)


def test_base_only_item_all_rolls_same_price():
    guide = FakePriceGuide(frame_prices={"Brightness Circle": {"base": "10-15"}})
    ranges = ArmorStatRanges.from_dicts(
        frames={"Brightness Circle": {"dfp": [190, 240], "evp": [116, 136]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    assert calc.calculate_frame_expected_value("Brightness Circle") == pytest.approx(10.0)
    breakdown = calc.get_frame_value_breakdown("Brightness Circle")
    assert len(breakdown["roll_details"]) == 51 * 21
    assert all(d["price"] == pytest.approx(10.0) for d in breakdown["roll_details"])

    display = calc.get_frame_calculation_breakdown("Brightness Circle")
    assert display["outcome_count"] == 51 * 21
    assert display["both_max_probability"] == pytest.approx(1.0 / (51 * 21))


def test_min_stat_preferred_over_base_for_floor():
    guide = FakePriceGuide(
        frame_prices={
            "Select Cloak": {
                "base": "10",
                "Min Stat": "15-18",
                "Med Stat": "25-30",
            }
        }
    )
    ranges = ArmorStatRanges.from_dicts(
        frames={"Select Cloak": {"dfp": [172, 180], "evp": [146, 154]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]

    breakdown = calc.get_frame_value_breakdown("Select Cloak")
    assert breakdown["tier_prices"]["min"] == pytest.approx(15.0)
    assert breakdown["tier_prices"]["base"] == pytest.approx(10.0)
    # Without Max Stat, dual-max falls back to High (= Med here) not a premium max
    assert breakdown["tier_prices"]["max"] == pytest.approx(25.0)

    min_roll = next(d for d in breakdown["roll_details"] if d["dfp"] == 172 and d["evp"] == 146)
    assert min_roll["price"] == pytest.approx(15.0)
    assert min_roll["both_max"] is False


def test_display_price_groups_mark_both_max():
    guide = _tiered_frame_guide()
    ranges = ArmorStatRanges.from_dicts(
        frames={"Test Frame": {"dfp": [10, 11], "evp": [20, 21]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]
    display = calc.get_frame_calculation_breakdown("Test Frame")

    max_group = next(g for g in display["price_groups"] if g["includes_both_max"])
    assert max_group["price"] == pytest.approx(100.0)
    assert max_group["probability"] == pytest.approx(0.25)
    assert all(not g["includes_both_max"] for g in display["price_groups"] if g["price"] != 100.0)


def test_missing_price_guide_item_raises():
    guide = FakePriceGuide(frame_prices={})
    ranges = ArmorStatRanges.from_dicts(frames={"Aura Field": {"dfp": [235, 285], "evp": [134, 154]}})
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]
    with pytest.raises(PriceGuideExceptionItemNameNotFound):
        calc.calculate_frame_expected_value("Aura Field")


def test_missing_stat_range_raises():
    guide = FakePriceGuide(frame_prices={"Unknown Frame": {"base": "1"}})
    ranges = ArmorStatRanges.from_dicts(frames={})
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]
    with pytest.raises(PriceGuideExceptionItemNameNotFound):
        calc.calculate_frame_expected_value("Unknown Frame")


def test_case_insensitive_lookup():
    guide = FakePriceGuide(
        frame_prices={"Aura Field": {"base": "2", "Min Stat": "2", "Max Stat": "100"}}
    )
    ranges = ArmorStatRanges.from_dicts(
        frames={"Aura Field": {"dfp": [235, 285], "evp": [134, 154]}},
    )
    calc = ArmorValueCalculator(guide, ranges)  # type: ignore[arg-type]
    assert calc.calculate_frame_expected_value("aura field") == calc.calculate_frame_expected_value(
        "Aura Field"
    )


def test_real_guide_integration_smoke(real_price_guide: PriceGuideFixed):
    calc = ArmorValueCalculator(real_price_guide)
    frame_value = calc.calculate_frame_expected_value("Aura Field")
    barrier_value = calc.calculate_barrier_expected_value("Standstill Shield")
    assert frame_value > 0
    assert barrier_value > 0
    assert frame_value > 2.0

    display = calc.get_frame_calculation_breakdown("Aura Field")
    assert display["dfp_outcomes"] == 51
    assert display["evp_outcomes"] == 21
    assert display["outcome_count"] == 51 * 21
    assert display["both_max_probability"] == pytest.approx(1.0 / (51 * 21))
    assert display["both_max_contribution"] == pytest.approx(
        display["tier_prices"]["max"] / (51 * 21)
    )
