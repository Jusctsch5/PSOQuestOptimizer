#!/usr/bin/env python3
"""
CLI: expected PD value / net EV for Ephinea Coren gambling by UTC weekday and bet size.

Rules: https://wiki.pioneer2.net/w/Coren
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from price_guide import BasePriceStrategy, PriceGuideFixed
from price_guide.coren_value import coren_prize_pd, meseta_stake_to_pd
from quest_optimizer.coren import (
    TIER_ODDS,
    VALID_BETS,
    VALID_WEEKDAYS,
    WIKI_URL,
    expected_prize_pd_for_bet,
    load_coren_pools,
    total_win_probability,
    win_probability_breakdown,
)


def _default_paths(repo_root: Path) -> tuple[Path, Path]:
    data = repo_root / "price_guide" / "data"
    return data / "coren_pools.json", data


def _print_coren_table(rows: List[Dict[str, Any]]) -> None:
    """Aligned header + rule, matching optimize_quests / id_advantage_report style."""
    if not rows:
        print("No results.")
        return

    wd_w = max(len("Weekday"), *(len(r["weekday"]) for r in rows))
    bet_w = max(len("Bet (mst)"), *(len(f"{r['bet_meseta']:,}") for r in rows))
    ep_w = 12
    st_w = 12
    nv_w = 12

    header_parts = [
        f"{'Weekday':<{wd_w}}",
        f"{'Bet (mst)':>{bet_w}}",
        f"{'E[prize] PD':>{ep_w}}",
        f"{'Stake PD':>{st_w}}",
        f"{'Net EV PD':>{nv_w}}",
    ]
    header = " ".join(header_parts)
    print("\n" + header)
    print("-" * len(header))

    for row in rows:
        line_parts = [
            f"{row['weekday']:<{wd_w}}",
            f"{row['bet_meseta']:>{bet_w},}",
            f"{row['expected_prize_pd']:>{ep_w}.4f}",
            f"{row['stake_pd']:>{st_w}.4f}",
            f"{row['net_ev_pd']:>{nv_w}.4f}",
        ]
        print(" ".join(line_parts))
        miss = row["missing_price_items"]
        if miss:
            names = ", ".join(miss)
            print(f"  * missing from price guide (counted as 0 PD): {names}")


def _enrich_breakdown_with_pd(
    breakdown: List[Dict[str, Any]],
    pg: PriceGuideFixed,
) -> List[Dict[str, Any]]:
    """Add pd (Coren price) and p_times_pd (EV contribution) per row."""
    rows: List[Dict[str, Any]] = []
    for r in breakdown:
        force = r.get("force_type")
        force_s = str(force).strip().lower() if force else None
        pdv = coren_prize_pd(r["name"], pg, force_type=force_s)
        pd_f = float(pdv) if pdv is not None else 0.0
        row = dict(r)
        row["pd"] = pd_f
        row["p_times_pd"] = float(r["p_win"]) * pd_f
        row["missing_price"] = pdv is None
        rows.append(row)
    return rows


def _print_prob_audit(
    weekday: str,
    bet_meseta: int,
    breakdown: List[Dict[str, Any]],
    *,
    price_guide_dir: Path,
    bps: BasePriceStrategy,
    pg: PriceGuideFixed,
    as_json: bool,
) -> None:
    """Print full P(win) per item with tier math + PD value and EV contribution."""
    p_any = total_win_probability(bet_meseta)
    sum_p = sum(r["p_win"] for r in breakdown)
    enriched = _enrich_breakdown_with_pd(breakdown, pg)
    stake_pd = meseta_stake_to_pd(bet_meseta, price_guide_dir, bps)
    e_prize = sum(r["p_times_pd"] for r in enriched)
    net_ev = e_prize - stake_pd

    if as_json:
        print(
            json.dumps(
                {
                    "wiki": WIKI_URL,
                    "formula": "P(win item) = P(tier) * weight / sum_weights_in_tier; weight = 13 - stars",
                    "price_note": "pd = Coren/min-stat price guide PD; p_times_pd = P(win)*pd sums to E[prize]",
                    "weekday": weekday,
                    "bet_meseta": bet_meseta,
                    "p_win_any_prize": p_any,
                    "sum_p_win_all_items": sum_p,
                    "expected_prize_pd": e_prize,
                    "stake_pd": stake_pd,
                    "net_ev_pd": net_ev,
                    "rows": enriched,
                },
                indent=2,
            )
        )
        return

    print("Coren win probabilities (audit) + PD value")
    print(f"  {WIKI_URL}")
    print(f"  weekday={weekday}  bet={bet_meseta:,} meseta  |  price strategy: {bps.value}")
    print(f"  Formula: P(win item) = P(tier) * (weight / tier_total_weight), weight = 13 - stars")
    print(f"  P(win any prize) = {p_any:.6f} ({p_any * 100:.4f}%)  [sum of tier odds for this bet]")
    print(f"  PD = Coren-valued prize (min stats / no attrs); P×PD sums to E[prize]; Net EV = E[prize] − stake")
    print()

    tier_w = 6
    item_w = len("Item")
    if breakdown:
        item_w = max(item_w, max(len(r["name"]) for r in breakdown))
    pd_w = 10
    ptpd_w = 12
    header = (
        f"{'Tier':<{tier_w}} "
        f"{'Item':<{item_w}} "
        f"{'*':>3} "
        f"{'wt':>3} "
        f"{'Wtot':>4} "
        f"{'P(tier)':>10} "
        f"{'P|tier':>10} "
        f"{'P(win)':>12} "
        f"{'Pct':>8} "
        f"{'!':>2} "
        f"{'PD':>{pd_w}} "
        f"{'P×PD':>{ptpd_w}}"
    )
    print(header)
    print("-" * len(header))

    for r in sorted(enriched, key=lambda x: (-x["p_times_pd"], -x["p_win"], x["tier"], x["name"])):
        pt = r["p_tier"]
        pc = r["p_item_given_tier"]
        pw = r["p_win"]
        flag = "*" if r["missing_price"] else " "
        print(
            f"{r['tier']:<{tier_w}} "
            f"{r['name']:<{item_w}} "
            f"{r['stars']:>3} "
            f"{r['weight']:>3} "
            f"{r['tier_total_weight']:>4} "
            f"{pt:>10.6f} "
            f"{pc:>10.6f} "
            f"{pw:>12.8f} "
            f"{pw * 100:>7.3f}% "
            f"{flag:>2} "
            f"{r['pd']:>{pd_w}.4f} "
            f"{r['p_times_pd']:>{ptpd_w}.6f}"
        )

    print("-" * len(header))
    print(f"SUM P(win):     {sum_p:.8f} ({sum_p * 100:.4f}%)")
    if abs(sum_p - p_any) > 1e-9:
        print(f"  WARNING: sum P(win) ({sum_p}) != P(any prize) ({p_any}); check pools.", file=sys.stderr)
    else:
        print("  (sum P(win) matches P(win any prize).)")
    print(f"SUM P×PD (E[prize]): {e_prize:.6f} PD  (each row: P(win)×PD; sum = expected prize PD)")
    if p_any > 0:
        e_given_win = e_prize / p_any
        print(f"E[PD | win something]: {e_given_win:.6f} PD  (= E[prize] / P(win any prize))")
    print(f"Stake (meseta→PD):  {stake_pd:.6f} PD")
    print(f"Net EV PD:          {net_ev:.6f} PD  (= E[prize] − stake, same as main EV table)")
    missing_named = sorted({r["name"] for r in enriched if r["missing_price"]})
    if missing_named:
        print(f"  * PD=0: no price guide entry for: {', '.join(missing_named)}")


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    default_pools, default_pg = _default_paths(repo_root)

    parser = argparse.ArgumentParser(
        description="Coren gambling expected value (Ephinea, UTC weekday).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Validate probabilities vs wiki (https://wiki.pioneer2.net/w/Coren):\n"
            "  %(prog)s --list-probs --weekday Wednesday --bet 10000\n"
            "  %(prog)s --show-prob \"Cure/Slow\" --weekday Wednesday --bet 10000\n"
            "Wiki check: 10k tier1 6%% × weight 4 / W 25 = 0.0096 (~1/104.17) for Cure/Slow Wed tier1."
        ),
    )
    parser.add_argument(
        "--pools",
        type=Path,
        default=default_pools,
        help=f"Path to coren_pools.json (default: {default_pools})",
    )
    parser.add_argument(
        "--price-guide",
        type=Path,
        default=default_pg,
        help=f"Price guide data directory (default: {default_pg})",
    )
    parser.add_argument(
        "--price-strategy",
        choices=[s.value for s in BasePriceStrategy],
        default=BasePriceStrategy.MINIMUM.value,
        help="Applied to meseta/PD conversion and price ranges",
    )
    parser.add_argument(
        "--weekday",
        choices=list(VALID_WEEKDAYS),
        default=None,
        help="UTC weekday (same as in-game /time); default: all weekdays",
    )
    parser.add_argument(
        "--bet",
        type=int,
        choices=sorted(VALID_BETS),
        default=None,
        help="Meseta bet (1000, 10000, or 100000); default: all three",
    )
    parser.add_argument(
        "--all-bets",
        action="store_true",
        help="All three bet sizes (default when --bet is omitted; explicit no-op)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON on stdout",
    )
    parser.add_argument(
        "--list-probs",
        action="store_true",
        help="Full table: probabilities + PD per item + P×PD (sums to E[prize]) + footer Net EV; "
        "needs --weekday and --bet",
    )
    parser.add_argument(
        "--show-prob",
        metavar="ITEM",
        help="P(win one item) with per-tier steps; requires --weekday and --bet",
    )

    args = parser.parse_args()

    if args.bet is not None and args.all_bets:
        parser.error("Do not combine --bet with --all-bets")
    if args.list_probs and args.show_prob:
        parser.error("Use either --list-probs or --show-prob, not both")
    if args.list_probs and not args.weekday:
        parser.error("--list-probs requires --weekday")
    if args.list_probs and args.bet is None:
        parser.error("--list-probs requires --bet (1000, 10000, or 100000)")
    if args.show_prob and not args.weekday:
        parser.error("--show-prob requires --weekday")
    if args.show_prob and args.bet is None:
        parser.error("--show-prob requires --bet (1000, 10000, or 100000)")

    if not args.pools.exists():
        print(f"Error: pools file not found: {args.pools}", file=sys.stderr)
        return 1
    if not args.price_guide.exists():
        print(f"Error: price guide directory not found: {args.price_guide}", file=sys.stderr)
        return 1

    bps = BasePriceStrategy(args.price_strategy.upper())
    pg = PriceGuideFixed(str(args.price_guide), base_price_strategy=bps)
    pools = load_coren_pools(args.pools)

    bets = sorted(VALID_BETS) if args.bet is None else [args.bet]

    if args.list_probs:
        assert args.weekday is not None and args.bet is not None
        bd = win_probability_breakdown(args.weekday, args.bet, pools)
        _print_prob_audit(
            args.weekday,
            args.bet,
            bd,
            price_guide_dir=args.price_guide,
            bps=bps,
            pg=pg,
            as_json=args.json,
        )
        return 0

    if args.show_prob:
        assert args.weekday is not None and args.bet is not None
        item = args.show_prob.strip()
        bd = win_probability_breakdown(args.weekday, args.bet, pools)
        matching = [r for r in bd if r["name"] == item]
        if not matching:
            print(f"No pool entry named {item!r} for {args.weekday} at bet {args.bet:,}.", file=sys.stderr)
            print(f"Use --list-probs --weekday {args.weekday} --bet {args.bet} to see exact names.", file=sys.stderr)
            return 1
        p_total = sum(r["p_win"] for r in matching)
        if p_total > 0:
            print(f"P(win {item}) = {p_total:.8f}  (~1 in {1 / p_total:.2f})")
        else:
            print(f"P(win {item}) = 0")
        print(f"  weekday={args.weekday}  bet={args.bet:,} meseta  |  {WIKI_URL}")
        print("  Per tier: P(win item) = P(tier) * P(item|tier) = P(tier) * (weight / W)")
        for r in matching:
            print(
                f"    {r['tier']}: P(tier)={r['p_tier']:.4f}  weight={r['weight']}  W={r['tier_total_weight']}  "
                f"P(item|tier)={r['p_item_given_tier']:.6f}  ->  {r['p_win']:.8f}"
            )
        return 0

    weekdays = [args.weekday] if args.weekday is not None else list(VALID_WEEKDAYS)

    rows: List[Dict[str, Any]] = []
    for wd in weekdays:
        for bet in bets:
            r = expected_prize_pd_for_bet(
                wd,
                bet,
                pools,
                pg,
                price_guide_dir=args.price_guide,
                bps=bps,
            )
            rows.append(
                {
                    "weekday": r.weekday,
                    "bet_meseta": r.bet_meseta,
                    "expected_prize_pd": r.expected_prize_pd,
                    "stake_pd": r.stake_pd,
                    "net_ev_pd": r.net_ev_pd,
                    "missing_price_items": list(r.missing_items),
                }
            )

    if args.json:
        print(json.dumps({"wiki": WIKI_URL, "rows": rows}, indent=2))
        return 0

    print("Coren expected value (UTC weekday)")
    print(f"  {WIKI_URL}")
    print(f"  Price strategy: {bps.value}  |  pools: {args.pools.name}")
    _print_coren_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
