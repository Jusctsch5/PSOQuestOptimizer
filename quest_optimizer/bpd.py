"""
Black Paper's Dangerous Deal (1 & 2) — expected PD per Photon Crystal trade.

Wiki:
  https://wiki.pioneer2.net/w/Black_Paper%27s_Dangerous_Deal
  https://wiki.pioneer2.net/w/Black_Paper%27s_Dangerous_Deal_2

BPD1: each reward roll is one draw from (arena good pool + junk atomizers + Meseta);
      all outcomes weight 1 except Meseta weight 6 (wiki).
BPD2: each roll is uniform over the listed items for that difficulty (no junk).

Prize valuation matches Coren-style drops (min stats / no attributes): `coren_prize_pd`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from price_guide import PriceGuideAbstract
from price_guide.coren_value import coren_prize_pd

DIFFICULTIES = ("Normal", "Hard", "Very Hard", "Ultimate")


def load_bpd_pools(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "bpd1" not in data or "bpd2" not in data:
        raise ValueError("bpd_pools.json missing bpd1 or bpd2")
    return data


def _item_pd(name: str, pg: PriceGuideAbstract) -> Tuple[float, bool]:
    v = coren_prize_pd(name.strip(), pg)
    if v is None:
        return 0.0, True
    return float(v), False


def expected_pd_one_roll_bpd1(
    good_items: Sequence[str],
    junk_equal: Sequence[str],
    meseta_weight: int,
    meseta_pd_value: float,
    pg: PriceGuideAbstract,
) -> Tuple[float, List[str]]:
    """E[PD] for a single BPD1 reward roll (cost of roll not subtracted)."""
    goods = [g.strip() for g in good_items if g.strip()]
    junks = [j.strip() for j in junk_equal if j.strip()]
    mw = max(0, int(meseta_weight))
    total_w = len(goods) + len(junks) + mw
    if total_w <= 0:
        return 0.0, []
    ev = 0.0
    missing: List[str] = []
    for g in goods:
        p = 1.0 / total_w
        pdv, miss = _item_pd(g, pg)
        ev += p * pdv
        if miss:
            missing.append(g)
    for j in junks:
        p = 1.0 / total_w
        pdv, miss = _item_pd(j, pg)
        ev += p * pdv
        if miss:
            missing.append(j)
    if mw > 0:
        ev += (mw / total_w) * float(meseta_pd_value)
    return ev, sorted(set(missing))


def expected_pd_one_roll_bpd2(pool_items: Sequence[str], pg: PriceGuideAbstract) -> Tuple[float, List[str]]:
    """E[PD] for one BPD2 reward roll (uniform over pool)."""
    items = [x.strip() for x in pool_items if x.strip()]
    n = len(items)
    if n <= 0:
        return 0.0, []
    ev = 0.0
    missing: List[str] = []
    p = 1.0 / n
    for g in items:
        pdv, miss = _item_pd(g, pg)
        ev += p * pdv
        if miss:
            missing.append(g)
    return ev, sorted(set(missing))


@dataclass(frozen=True)
class BpdScenarioResult:
    quest: str
    arena: Optional[str]
    difficulty: str
    rolls: int
    expected_prize_pd_per_run: float
    photon_crystal_cost_pd: float
    net_ev_pd_per_run: float
    missing_price_items: Tuple[str, ...]


def analyze_bpd_scenarios(
    pools: Mapping[str, Any],
    pg: PriceGuideAbstract,
    *,
    photon_crystal_cost_pd: float = 1.0,
) -> List[BpdScenarioResult]:
    """One result row per (BPD1 arena × difficulty) plus BPD2 × difficulty."""
    meseta_pd = float(pools.get("meseta_reward_pd_if_known", 0.0))
    b1 = pools["bpd1"]
    b2 = pools["bpd2"]
    rolls1: Dict[str, int] = {k: int(v) for k, v in b1["rewards_per_difficulty"].items()}
    rolls2: Dict[str, int] = {k: int(v) for k, v in b2["rewards_per_difficulty"].items()}
    junk = b1["junk_items_equal_weight"]
    mw = int(b1["junk_meseta_weight"])

    out: List[BpdScenarioResult] = []
    for diff in DIFFICULTIES:
        r1 = rolls1.get(diff, 0)
        r2 = rolls2.get(diff, 0)
        for arena, by_diff in b1["arenas"].items():
            goods = by_diff.get(diff, [])
            ev_roll, miss = expected_pd_one_roll_bpd1(goods, junk, mw, meseta_pd, pg)
            prize = float(r1) * ev_roll
            out.append(
                BpdScenarioResult(
                    quest="BPD1",
                    arena=str(arena),
                    difficulty=diff,
                    rolls=int(r1),
                    expected_prize_pd_per_run=prize,
                    photon_crystal_cost_pd=float(photon_crystal_cost_pd),
                    net_ev_pd_per_run=prize - float(photon_crystal_cost_pd),
                    missing_price_items=tuple(miss),
                )
            )
        pool = b2["pools"].get(diff, [])
        ev_roll2, miss2 = expected_pd_one_roll_bpd2(pool, pg)
        prize2 = float(r2) * ev_roll2
        out.append(
            BpdScenarioResult(
                quest="BPD2",
                arena=None,
                difficulty=diff,
                rolls=int(r2),
                expected_prize_pd_per_run=prize2,
                photon_crystal_cost_pd=float(photon_crystal_cost_pd),
                net_ev_pd_per_run=prize2 - float(photon_crystal_cost_pd),
                missing_price_items=tuple(miss2),
            )
        )
    return out


def best_bpd1_arena_per_difficulty(results: Sequence[BpdScenarioResult]) -> Dict[str, BpdScenarioResult]:
    """Highest net EV among BPD1 rows for each difficulty."""
    best: Dict[str, BpdScenarioResult] = {}
    for r in results:
        if r.quest != "BPD1":
            continue
        cur = best.get(r.difficulty)
        if cur is None or r.net_ev_pd_per_run > cur.net_ev_pd_per_run:
            best[r.difficulty] = r
    return best


def top_items_bpd_scenario(
    result: BpdScenarioResult,
    pools: Mapping[str, Any],
    pg: PriceGuideAbstract,
    *,
    top_n: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Items ranked by expected PD contribution to this scenario (per crystal run), like quest ``top_items``.

    Each entry: ``item``, ``pd_value`` (contribution toward ``expected_prize_pd_per_run``),
    ``enemies`` (single-element list: pool label for display).
    """
    meseta_pd = float(pools.get("meseta_reward_pd_if_known", 0.0))
    rolls = int(result.rolls)
    if rolls <= 0:
        return []

    rows: List[Tuple[str, float, str]] = []  # item, contrib_pd, source_label

    if result.quest == "BPD2":
        pool = list(pools["bpd2"]["pools"].get(result.difficulty, []))
        pool = [x.strip() for x in pool if x.strip()]
        n = len(pool)
        if n <= 0:
            return []
        p = 1.0 / n
        for name in pool:
            pdv, _ = _item_pd(name, pg)
            contrib = float(rolls) * p * pdv
            rows.append((name, contrib, "BPD2"))
    else:
        b1 = pools["bpd1"]
        arena = str(result.arena) if result.arena else ""
        goods = list(b1["arenas"].get(arena, {}).get(result.difficulty, []))
        goods = [g.strip() for g in goods if g.strip()]
        junks = [j.strip() for j in b1["junk_items_equal_weight"] if j.strip()]
        mw = max(0, int(b1["junk_meseta_weight"]))
        total_w = len(goods) + len(junks) + mw
        if total_w <= 0:
            return []
        p_slot = 1.0 / total_w
        src_arena = arena or "BPD1"
        for name in goods:
            pdv, _ = _item_pd(name, pg)
            rows.append((name, float(rolls) * p_slot * pdv, src_arena))
        for name in junks:
            pdv, _ = _item_pd(name, pg)
            rows.append((name, float(rolls) * p_slot * pdv, "Junk"))
        if mw > 0:
            rows.append((str(b1.get("junk_meseta_label", "Meseta")), float(rolls) * (mw / total_w) * float(meseta_pd), "Meseta"))

    # merge same (item, source) — should not occur; merge same item name
    merged: Dict[Tuple[str, str], float] = {}
    order: List[Tuple[str, str]] = []
    for name, contrib, src in rows:
        key = (name, src)
        if key not in merged:
            order.append(key)
            merged[key] = 0.0
        merged[key] += contrib

    out_list: List[Dict[str, Any]] = []
    for key in order:
        name, src = key
        out_list.append({"item": name, "pd_value": merged[key], "enemies": [src]})

    out_list.sort(key=lambda x: float(x["pd_value"]), reverse=True)
    if top_n is not None and top_n > 0:
        out_list = out_list[:top_n]
    return out_list


def best_quest_per_difficulty(results: Sequence[BpdScenarioResult]) -> Dict[str, Tuple[str, Optional[str], float]]:
    """For each difficulty, (quest_label, arena_or_none, net_ev): BPD1 best arena vs BPD2."""
    out: Dict[str, Tuple[str, Optional[str], float]] = {}
    b1_best = best_bpd1_arena_per_difficulty(results)
    by_key = {(r.quest, r.difficulty, r.arena): r for r in results}
    for diff in DIFFICULTIES:
        b1 = b1_best.get(diff)
        b2 = by_key.get(("BPD2", diff, None))
        if b1 is None and b2 is None:
            continue
        candidates: List[Tuple[str, Optional[str], float]] = []
        if b1 is not None:
            candidates.append(("BPD1", b1.arena, b1.net_ev_pd_per_run))
        if b2 is not None:
            candidates.append(("BPD2", None, b2.net_ev_pd_per_run))
        out[diff] = max(candidates, key=lambda x: x[2])
    return out
