"""
Value Coren (Ephinea) gambling prizes in PD: no attributes, minimum stats.

See https://wiki.pioneer2.net/w/Coren — prizes have no attributes and minimum stats.

Weapons: `get_price_weapon` with no attribute contribution and hit 0 (naked / 0-hit row).
Frames: `Min Stat` tier when present in price data, else `base`.
Barriers: `base` only (no Min Stat tier in current data).
Other categories: same base lookups as normal drops (units, tools, mags, cells, disks).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from price_guide import BasePriceStrategy, PriceGuideAbstract
from price_guide.price_guide import CannotInferBasePriceException, PriceGuideExceptionItemNameNotFound


def load_meseta_per_pd_value(price_guide_dir: Path, bps: BasePriceStrategy) -> float:
    """Meseta exchange rate: meseta per one PD (from meseta.json range)."""
    path = price_guide_dir / "meseta.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    raw = str(data.get("meseta_per_pd", "")).replace(",", "")
    return float(PriceGuideAbstract.get_price_from_range(raw, bps))


def meseta_stake_to_pd(stake_meseta: int, price_guide_dir: Path, bps: BasePriceStrategy) -> float:
    """Convert a meseta stake to PD using the configured price strategy on the meseta/PD range."""
    rate = load_meseta_per_pd_value(price_guide_dir, bps)
    if rate <= 0:
        return 0.0
    return float(stake_meseta) / rate


def coren_prize_pd(
    item_name: str,
    pg: PriceGuideAbstract,
    *,
    force_type: Optional[str] = None,
) -> Optional[float]:
    """
    Approximate PD value of a Coren prize (minimum stats, no attributes).

    Returns None if the item is unknown to the price guide.
    """
    name = item_name.strip()
    if not name:
        return None

    if force_type:
        itype = force_type.strip().lower()
    else:
        itype = pg.identify_item_type(name)

    if itype is None:
        return None

    try:
        if itype == "weapon":
            return pg.get_price_weapon(name, {}, 0, 0, "")
        if itype == "frame":
            key = pg._ci_key(pg.frame_prices, name)
            if key is None:
                return None
            fd: Dict[str, Any] = pg.frame_prices[key]
            tier = fd.get("Min Stat") or fd.get("base")
            if not tier:
                return 0.0
            return float(pg.get_price_from_range(str(tier), pg.bps))
        if itype == "barrier":
            key = pg._ci_key(pg.barrier_prices, name)
            if key is None:
                return None
            bd: Dict[str, Any] = pg.barrier_prices[key]
            tier = bd.get("base")
            if not tier:
                return 0.0
            return float(pg.get_price_from_range(str(tier), pg.bps))
        if itype == "unit":
            return float(pg.get_price_unit(name))
        if itype == "tool":
            return float(pg.get_price_tool(name, 1))
        if itype == "mag":
            return float(pg.get_price_mag(name, 0))
        if itype == "cell":
            return float(pg.get_price_cell(name))
        if itype == "disk":
            return float(pg.get_price_disk(name, 30))
        if itype == "srank_weapon":
            return float(pg.get_price_srank_weapon(name, "", 0, ""))
        if itype == "common_weapon":
            return None
    except (
        PriceGuideExceptionItemNameNotFound,
        CannotInferBasePriceException,
        KeyError,
        ValueError,
    ):
        return None

    return None
