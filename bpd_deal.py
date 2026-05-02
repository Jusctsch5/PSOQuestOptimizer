#!/usr/bin/env python3
"""
CLI: expected PD value for Black Paper's Dangerous Deal 1 & 2 (Photon Crystal = 1 PD).

Table layout mirrors ``optimize_quests.print_rankings`` (fixed columns + top N notable items by EV).

Use ``--add-warnings`` to print per-row lines for items missing from the price guide; default is quiet.

Pools: price_guide/data/bpd_pools.json (regenerate with scripts/generate_bpd_pools.py).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from price_guide import BasePriceStrategy, PriceGuideFixed
from quest_optimizer.bpd import (
    DIFFICULTIES,
    BpdScenarioResult,
    analyze_bpd_scenarios,
    best_bpd1_arena_per_difficulty,
    best_quest_per_difficulty,
    load_bpd_pools,
    top_items_bpd_scenario,
)


def _default_paths(repo_root: Path) -> Path:
    return repo_root / "price_guide" / "data" / "bpd_pools.json"


def _sort_rows_for_display(rows: Sequence[BpdScenarioResult]) -> List[BpdScenarioResult]:
    def diff_key(d: str) -> int:
        try:
            return DIFFICULTIES.index(d)
        except ValueError:
            return 99

    return sorted(rows, key=lambda r: (-r.net_ev_pd_per_run, diff_key(r.difficulty)))


def _print_quest_style_table(
    rows: Sequence[BpdScenarioResult],
    pools: Dict[str, Any],
    pg: Any,
    *,
    notable_items_count: int,
    add_warnings: bool,
) -> None:
    rows_list = _sort_rows_for_display(list(rows))
    if not rows_list:
        print("No rows.")
        return

    # top_items per row (for width + cells)
    row_top: List[List[Dict[str, Any]]] = []
    max_item_width = len("Notable Item 1")
    for r in rows_list:
        ti = top_items_bpd_scenario(r, pools, pg, top_n=max(30, notable_items_count))
        row_top.append(ti)
        for item_data in ti[:notable_items_count]:
            item_name = str(item_data.get("item", "Unknown"))
            sources = item_data.get("enemies", [])
            source = ", ".join(str(s) for s in sources) if sources else "Unknown"
            pd_value = float(item_data.get("pd_value", 0.0))
            item_str = f"{item_name} ({source}: {pd_value:.4f})"
            max_item_width = max(max_item_width, len(item_str))
    max_item_width = max(max_item_width, 20)

    rank_w = 6
    q_w = 6
    ar_w = max(len("Arena"), *(len(str(r.arena or "")) for r in rows_list))
    d_w = max(len("Difficulty"), *(len(r.difficulty) for r in rows_list))
    r_w = 6
    ep_w = 14
    net_w = 12

    header_parts = [
        f"{'Rank':<{rank_w}}",
        f"{'Quest':<{q_w}}",
        f"{'Arena':<{ar_w}}",
        f"{'Difficulty':<{d_w}}",
        f"{'Rolls':>{r_w}}",
        f"{'E[prize] PD':>{ep_w}}",
        f"{'Net EV PD':>{net_w}}",
    ]
    for i in range(1, notable_items_count + 1):
        header_parts.append(f"{f'Notable Item {i}':<{max_item_width}}")
    header = " ".join(header_parts)
    print("\n" + header)
    print("-" * len(header))

    for idx, r in enumerate(rows_list, 1):
        arena = str(r.arena) if r.arena else "-"
        top = row_top[idx - 1]
        row_parts = [
            f"{idx:<{rank_w}}",
            f"{r.quest:<{q_w}}",
            f"{arena:<{ar_w}}",
            f"{r.difficulty:<{d_w}}",
            f"{r.rolls:>{r_w}}",
            f"{r.expected_prize_pd_per_run:>{ep_w}.4f}",
            f"{r.net_ev_pd_per_run:>{net_w}.4f}",
        ]
        for i in range(notable_items_count):
            if i < len(top) and top[i]:
                item_data = top[i]
                item_name = str(item_data.get("item", "Unknown"))
                sources = item_data.get("enemies", [])
                source = ", ".join(str(s) for s in sources) if sources else "Unknown"
                pd_value = float(item_data.get("pd_value", 0.0))
                item_str = f"{item_name} ({source}: {pd_value:.4f})"
                row_parts.append(f"{item_str:<{max_item_width}}")
            else:
                row_parts.append(f"{'':<{max_item_width}}")
        print(" ".join(row_parts))
        if add_warnings and r.missing_price_items:
            miss = ", ".join(r.missing_price_items)
            print(f"  * missing from price guide (counted as 0 PD): {miss}")


def _print_summary(
    rows: Sequence[BpdScenarioResult],
    pools: Dict[str, Any],
    pg: Any,
    *,
    as_json: bool,
    winners: Dict[str, Tuple[str, Optional[str], float]],
    notable_items_count: int,
    add_warnings: bool,
) -> None:
    if as_json:
        data = []
        for r in _sort_rows_for_display(list(rows)):
            ti = top_items_bpd_scenario(r, pools, pg, top_n=max(30, notable_items_count))
            data.append(
                {
                    "quest": r.quest,
                    "arena": r.arena,
                    "difficulty": r.difficulty,
                    "rolls": r.rolls,
                    "expected_prize_pd": r.expected_prize_pd_per_run,
                    "crystal_cost_pd": r.photon_crystal_cost_pd,
                    "net_ev_pd": r.net_ev_pd_per_run,
                    "missing_price_items": list(r.missing_price_items),
                    "top_items": ti[:notable_items_count],
                }
            )
        print(json.dumps(data, indent=2))
        return

    _print_quest_style_table(
        rows, pools, pg, notable_items_count=notable_items_count, add_warnings=add_warnings
    )

    print("\nBest quest (BPD1 = best arena vs BPD2) by difficulty:")
    for diff in DIFFICULTIES:
        if diff not in winners:
            continue
        q, ar, ev = winners[diff]
        a = f" ({ar})" if ar else ""
        print(f"  {diff}: {q}{a}  net EV {ev:.4f} PD / crystal")


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    default_pools = _default_paths(repo_root)
    pg_dir = repo_root / "price_guide" / "data"

    p = argparse.ArgumentParser(description="Black Paper Dangerous Deal expected PD (wiki pools + price guide).")
    p.add_argument("--pools", type=Path, default=default_pools, help=f"Path to bpd_pools.json (default: {default_pools})")
    p.add_argument(
        "--price-strategy",
        choices=["minimum", "maximum", "average"],
        default="minimum",
        help="Base price strategy for ranges (default: minimum)",
    )
    p.add_argument("--notable-items", type=int, default=5, help="Number of notable item columns (default: 5, max 20)")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    p.add_argument(
        "--add-warnings",
        action="store_true",
        help="Print lines for items missing from the price guide (otherwise omit)",
    )
    p.add_argument("--only-difficulty", choices=list(DIFFICULTIES), help="Filter output to one difficulty")
    args = p.parse_args()

    ni = max(1, min(20, int(args.notable_items)))

    bps = BasePriceStrategy(args.price_strategy.upper())
    try:
        pg = PriceGuideFixed(str(pg_dir), bps)
    except Exception as e:
        print(f"Failed to load price guide: {e}", file=sys.stderr)
        return 1

    try:
        pools = load_bpd_pools(args.pools)
    except Exception as e:
        print(f"Failed to load pools: {e}", file=sys.stderr)
        return 1

    all_rows = analyze_bpd_scenarios(pools, pg)
    winners = best_quest_per_difficulty(all_rows)
    rows = all_rows
    if args.only_difficulty:
        rows = [r for r in all_rows if r.difficulty == args.only_difficulty]

    _print_summary(
        rows,
        pools,
        pg,
        as_json=args.json,
        winners=winners,
        notable_items_count=ni,
        add_warnings=bool(args.add_warnings),
    )

    if not args.json:
        b1b = best_bpd1_arena_per_difficulty(all_rows)
        print("\nBest BPD1 arena only (for reference):")
        for diff in DIFFICULTIES:
            r = b1b.get(diff)
            if r:
                print(f"  {diff}: {r.arena}  net {r.net_ev_pd_per_run:.4f} PD")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
