"""Tests for Black Paper's Dangerous Deal EV helpers."""

from pathlib import Path

import pytest

from price_guide import BasePriceStrategy, PriceGuideFixed
from quest_optimizer.bpd import (
    analyze_bpd_scenarios,
    expected_pd_one_roll_bpd1,
    expected_pd_one_roll_bpd2,
    load_bpd_pools,
    top_items_bpd_scenario,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
POOLS_PATH = REPO_ROOT / "price_guide" / "data" / "bpd_pools.json"
PRICE_DIR = REPO_ROOT / "price_guide" / "data"


@pytest.fixture
def price_guide():
    return PriceGuideFixed(str(PRICE_DIR), BasePriceStrategy.MINIMUM)


def test_load_bpd_pools():
    if not POOLS_PATH.exists():
        pytest.skip("bpd_pools.json not present")
    data = load_bpd_pools(POOLS_PATH)
    assert "bpd1" in data and "bpd2" in data
    assert "sand_rappy" in data["bpd1"]["arenas"]


def test_bpd1_weight_denominator():
    """1 good + 3 junk slots + meseta weight 6 => denominator 10; each non-meseta outcome p=0.1."""
    from price_guide.coren_value import coren_prize_pd

    pg = PriceGuideFixed(str(PRICE_DIR), BasePriceStrategy.MINIMUM)

    def v(name: str) -> float:
        x = coren_prize_pd(name, pg)
        return float(x) if x is not None else 0.0

    # Tools priced in repo data (stand-ins for the three equal-weight junk slots)
    junk = ["Photon Crystal", "Photon Hoard", "Photon Sphere"]
    for n in ("Smartlink", *junk):
        assert coren_prize_pd(n, pg) is not None

    ev, miss = expected_pd_one_roll_bpd1(
        good_items=["Smartlink"],
        junk_equal=junk,
        meseta_weight=6,
        meseta_pd_value=0.0,
        pg=pg,
    )
    exp = 0.1 * v("Smartlink") + 0.1 * sum(v(x) for x in junk)
    assert abs(ev - exp) < 1e-6
    assert not miss


def test_bpd2_uniform_two_items():
    from price_guide.coren_value import coren_prize_pd

    pg = PriceGuideFixed(str(PRICE_DIR), BasePriceStrategy.MINIMUM)
    ev, miss = expected_pd_one_roll_bpd2(["Smartlink", "Smartlink"], pg)
    pv = coren_prize_pd("Smartlink", pg)
    assert pv is not None
    assert not miss
    assert abs(ev - float(pv)) < 1e-6


@pytest.mark.skipif(not POOLS_PATH.exists(), reason="bpd_pools.json not present")
def test_pools_sand_rappy_ultimate_has_rappy_beak(price_guide: PriceGuideFixed):
    pools = load_bpd_pools(POOLS_PATH)
    u = pools["bpd1"]["arenas"]["sand_rappy"]["Ultimate"]
    assert "Rappy's Beak" in u


@pytest.mark.skipif(not POOLS_PATH.exists(), reason="bpd_pools.json not present")
def test_bpd2_ultimate_pool_nonempty(price_guide: PriceGuideFixed):
    pools = load_bpd_pools(POOLS_PATH)
    assert len(pools["bpd2"]["pools"]["Ultimate"]) >= 10


@pytest.mark.skipif(not POOLS_PATH.exists(), reason="bpd_pools.json not present")
def test_top_items_contributions_sum_to_expected_prize(price_guide: PriceGuideFixed):
    pools = load_bpd_pools(POOLS_PATH)
    for r in analyze_bpd_scenarios(pools, price_guide):
        ti = top_items_bpd_scenario(r, pools, price_guide, top_n=None)
        total = sum(float(x["pd_value"]) for x in ti)
        assert abs(total - r.expected_prize_pd_per_run) < 1e-5, (r, total, r.expected_prize_pd_per_run)
