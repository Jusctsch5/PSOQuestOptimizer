"""
Ephinea Coren gambling expected value (meseta tiers, weekday pools, star weights).

Rules: https://wiki.pioneer2.net/w/Coren
- UTC weekday determines the prize pool.
- Bets: 1,000 / 10,000 / 100,000 meseta.
- Tier hit chances are mutually exclusive with losing the stake (remainder = no prize).
- Within a tier, P(item) = P(tier) * (weight_i / sum_weights), weight = 13 - star_rarity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from price_guide import BasePriceStrategy, PriceGuideFixed
from price_guide.coren_value import coren_prize_pd, meseta_stake_to_pd

WIKI_URL = "https://wiki.pioneer2.net/w/Coren"

# Bet (meseta) -> tier key -> probability (mutually exclusive, including implicit "lose")
TIER_ODDS: Dict[int, Dict[str, float]] = {
    1000: {"tier1": 0.04},
    10000: {"tier1": 0.06, "tier2": 0.04},
    100000: {"tier1": 0.08, "tier2": 0.06, "tier3": 0.04},
}

VALID_BETS = frozenset(TIER_ODDS.keys())
VALID_WEEKDAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)


def coren_weight(star_rarity: int) -> int:
    """Weight for star rarity r: 13 - r (Ephinea Coren)."""
    return 13 - int(star_rarity)


def tier_total_weight(entries: Iterable[Mapping[str, Any]]) -> int:
    return sum(coren_weight(int(e["stars"])) for e in entries)


def item_probability_in_pool(
    entries: List[Mapping[str, Any]],
    item_name: str,
) -> Optional[float]:
    """P(item | tier hit): weight_i / total_weight. None if item not in pool."""
    total = tier_total_weight(entries)
    if total <= 0:
        return None
    for e in entries:
        if str(e["name"]).strip() == item_name:
            return coren_weight(int(e["stars"])) / total
    return None


def load_coren_pools(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "weekdays" not in data:
        raise ValueError("coren_pools.json missing 'weekdays'")
    return data


def _tier_entries(weekday_data: Mapping[str, Any], tier_key: str) -> List[Dict[str, Any]]:
    raw = weekday_data.get(tier_key)
    if not raw:
        return []
    return list(raw)


@dataclass(frozen=True)
class CorenEVResult:
    weekday: str
    bet_meseta: int
    expected_prize_pd: float
    stake_pd: float
    net_ev_pd: float
    missing_items: Tuple[str, ...]


def win_probability_breakdown(
    weekday: str,
    bet_meseta: int,
    pools: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """
    Every possible prize outcome for this weekday/bet with full audit math.

    For each (tier, item): P(win this item) = P(tier) * (weight_i / sum_weights_in_tier).
    Sum of P(win) over all rows equals total chance to win any prize (e.g. 10% for 10k bet).

    Use this to validate against https://wiki.pioneer2.net/w/Coren (Prize Odds + weight table).
    """
    if bet_meseta not in TIER_ODDS:
        raise ValueError(f"Unsupported bet {bet_meseta}; valid: {sorted(VALID_BETS)}")
    wd = pools["weekdays"].get(weekday)
    if wd is None:
        raise KeyError(f"Unknown weekday {weekday!r}; expected one of {VALID_WEEKDAYS}")

    out: List[Dict[str, Any]] = []
    odds = TIER_ODDS[bet_meseta]
    for tier_key, p_tier in odds.items():
        entries = _tier_entries(wd, tier_key)
        if not entries:
            continue
        tw = tier_total_weight(entries)
        if tw <= 0:
            continue
        for e in entries:
            name = str(e["name"])
            stars = int(e["stars"])
            w = coren_weight(stars)
            p_cond = w / tw
            p_win = p_tier * p_cond
            ft = e.get("force_type")
            out.append(
                {
                    "tier": tier_key,
                    "name": name,
                    "stars": stars,
                    "weight": w,
                    "tier_total_weight": tw,
                    "p_tier": p_tier,
                    "p_item_given_tier": p_cond,
                    "p_win": p_win,
                    **({"force_type": ft} if ft is not None else {}),
                }
            )
    return out


def total_win_probability(bet_meseta: int) -> float:
    """Sum of tier hit chances for this bet (probability of winning any prize)."""
    return float(sum(TIER_ODDS[bet_meseta].values()))


def expected_prize_pd_for_bet(
    weekday: str,
    bet_meseta: int,
    pools: Mapping[str, Any],
    pg: PriceGuideFixed,
    *,
    price_guide_dir: Path,
    bps: BasePriceStrategy,
) -> CorenEVResult:
    """
    Expected prize value (PD) and net EV after converting meseta stake to PD.

    Items missing from the price guide contribute 0 PD and are listed in missing_items.
    """
    if bet_meseta not in TIER_ODDS:
        raise ValueError(f"Unsupported bet {bet_meseta}; valid: {sorted(VALID_BETS)}")
    wd = pools["weekdays"].get(weekday)
    if wd is None:
        raise KeyError(f"Unknown weekday {weekday!r}; expected one of {VALID_WEEKDAYS}")

    odds = TIER_ODDS[bet_meseta]
    ev = 0.0
    missing: List[str] = []

    for tier_key, p_tier in odds.items():
        entries = _tier_entries(wd, tier_key)
        if not entries:
            continue
        tw = tier_total_weight(entries)
        if tw <= 0:
            continue
        for e in entries:
            name = str(e["name"])
            stars = int(e["stars"])
            w = coren_weight(stars)
            p_item = p_tier * (w / tw)
            force = e.get("force_type")
            force_s = str(force).strip().lower() if force else None
            val = coren_prize_pd(name, pg, force_type=force_s)
            if val is None:
                missing.append(name)
                val = 0.0
            ev += p_item * val

    stake_pd = meseta_stake_to_pd(bet_meseta, price_guide_dir, bps)
    return CorenEVResult(
        weekday=weekday,
        bet_meseta=bet_meseta,
        expected_prize_pd=ev,
        stake_pd=stake_pd,
        net_ev_pd=ev - stake_pd,
        missing_items=tuple(sorted(set(missing))),
    )
