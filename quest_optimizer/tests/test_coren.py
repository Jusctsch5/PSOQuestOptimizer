"""Tests for Ephinea Coren tier weights and probabilities (wiki: Coren)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quest_optimizer.coren import (
    TIER_ODDS,
    VALID_WEEKDAYS,
    coren_weight,
    item_probability_in_pool,
    load_coren_pools,
    tier_total_weight,
    total_win_probability,
    win_probability_breakdown,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
POOLS_PATH = REPO_ROOT / "price_guide" / "data" / "coren_pools.json"


WED_T1_FIXTURE = [
    {"name": "God/Legs", "stars": 11},
    {"name": "Hero/Ability", "stars": 10},
    {"name": "TP/Revival", "stars": 9},
    {"name": "Devil/Battle", "stars": 9},
    {"name": "Cure/Slow", "stars": 9},
    {"name": "Tablet", "stars": 5},
]


def test_wednesday_tier1_total_weight_matches_wiki() -> None:
    """Wiki example: total weight 25 for Wednesday Tier 1."""
    assert tier_total_weight(WED_T1_FIXTURE) == 25


def test_coren_weight_formula() -> None:
    assert coren_weight(11) == 2
    assert coren_weight(5) == 8


def test_cure_slow_rate_10k_bet() -> None:
    """10k bet: Tier 1 = 6%; Cure/Slow weight 4 / 25 → 0.06 * 4/25."""
    p_tier = TIER_ODDS[10000]["tier1"]
    p_cond = item_probability_in_pool(list(WED_T1_FIXTURE), "Cure/Slow")
    assert p_cond is not None
    assert abs(p_tier * p_cond - 0.06 * (4 / 25)) < 1e-12


@pytest.mark.skipif(not POOLS_PATH.exists(), reason="coren_pools.json not present")
def test_load_pools_has_all_weekdays() -> None:
    data = load_coren_pools(POOLS_PATH)
    for d in (
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ):
        assert d in data["weekdays"]
        day = data["weekdays"][d]
        for tier in ("tier1", "tier2", "tier3"):
            assert tier in day
            assert isinstance(day[tier], list)


@pytest.mark.skipif(not POOLS_PATH.exists(), reason="coren_pools.json not present")
def test_win_probability_breakdown_sums_to_tier_odds() -> None:
    """Sum of P(win each item) must equal wiki 'any prize' rate for that bet (tiers fully populated)."""
    pools = load_coren_pools(POOLS_PATH)
    for bet in (1000, 10000, 100000):
        expect = total_win_probability(bet)
        for wd in VALID_WEEKDAYS:
            bd = win_probability_breakdown(wd, bet, pools)
            got = sum(r["p_win"] for r in bd)
            assert abs(got - expect) < 1e-9, f"{wd} bet {bet}: sum P={got} want {expect}"


@pytest.mark.skipif(not POOLS_PATH.exists(), reason="coren_pools.json not present")
def test_pools_json_validates_entries() -> None:
    data = json.loads(POOLS_PATH.read_text(encoding="utf-8"))
    for wd, tiers in data["weekdays"].items():
        for tier_name, entries in tiers.items():
            assert tier_name.startswith("tier")
            for e in entries:
                assert "name" in e and "stars" in e
                assert isinstance(e["stars"], int)
                assert 1 <= e["stars"] <= 12
