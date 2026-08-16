"""
Calculate average armor (frame) and shield (barrier) value from uniform DFP/EVP rolls.

Drops roll absolute DFP and EVP independently and uniformly over each item's
inclusive wiki range (see drop_tables/armor_stat_ranges.json).

Expected PD uses the price guide's Min/Med/High/Max tier listings:

- Primary axis quality (frames: DFP, barriers: EVP) drives Min → Med → High
  interpolation for non-perfect rolls.
- Max Stat / Max DFP / Max EVP applies only when BOTH DFP and EVP are at their
  range maximum. Max primary with non-max secondary uses the High tier instead.

Missing tiers fall back toward Min Stat, then base.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from drop_tables.armor_stat_ranges import ArmorStatRange, ArmorStatRanges, get_armor_stat_ranges
from price_guide import PriceGuideExceptionItemNameNotFound

if TYPE_CHECKING:
    from price_guide.price_guide import PriceGuideAbstract


def format_probability(prob: float) -> str:
    """Format probability as percentage with 6-7 decimal places for precision."""
    return f"{prob * 100:.7f}%"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def interpolate_tier_price(quality: float, min_price: float, med_price: float, high_price: float) -> float:
    """
    Piecewise-linear price for quality in [0, 1].

    Anchors: 0 → min, 0.5 → med, 1 → high.
    """
    q = max(0.0, min(1.0, quality))
    if q <= 0.5:
        return _lerp(min_price, med_price, q / 0.5)
    return _lerp(med_price, high_price, (q - 0.5) / 0.5)


class ArmorValueCalculator:
    """
    Expected frame/barrier PD from independent uniform DFP×EVP rolls × price tiers.
    """

    def __init__(
        self,
        price_guide: "PriceGuideAbstract",
        armor_stat_ranges: Optional[ArmorStatRanges] = None,
    ):
        self.price_guide = price_guide
        self.armor_stat_ranges = armor_stat_ranges or get_armor_stat_ranges()

    def calculate_frame_expected_value(self, frame_name: str) -> float:
        """Expected frame PD from uniform independent DFP/EVP rolls."""
        return self.get_frame_value_breakdown(frame_name)["total"]

    def calculate_barrier_expected_value(self, barrier_name: str) -> float:
        """Expected barrier PD from uniform independent DFP/EVP rolls."""
        return self.get_barrier_value_breakdown(barrier_name)["total"]

    def _get_frame_data(self, frame_name: str) -> Tuple[str, Dict[str, Any]]:
        frame_key = self.price_guide._ci_key(self.price_guide.frame_prices, frame_name)
        if frame_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {frame_name} not found in frame_prices")
        return frame_key, self.price_guide.frame_prices[frame_key]

    def _get_barrier_data(self, barrier_name: str) -> Tuple[str, Dict[str, Any]]:
        barrier_key = self.price_guide._ci_key(self.price_guide.barrier_prices, barrier_name)
        if barrier_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {barrier_name} not found in barrier_prices")
        return barrier_key, self.price_guide.barrier_prices[barrier_key]

    def _require_stat_range(self, item_name: str, kind: str) -> ArmorStatRange:
        if kind == "frame":
            stat_range = self.armor_stat_ranges.get_frame(item_name)
        else:
            stat_range = self.armor_stat_ranges.get_barrier(item_name)
        if stat_range is None:
            raise PriceGuideExceptionItemNameNotFound(
                f"Item name {item_name} not found in armor_stat_ranges ({kind})"
            )
        return stat_range

    def _parse_optional_price(self, price_str: Any) -> Optional[float]:
        if price_str is None:
            return None
        text = str(price_str).strip()
        if not text or text.upper() in {"N/A", "NA"}:
            return None
        # Skip guide cross-references that are not numeric ranges
        if any(token in text.lower() for token in ("see ", "combination", "rare frames")):
            return None
        try:
            return self.price_guide.get_price_from_range(price_str, self.price_guide.bps)
        except Exception:
            return None

    def _resolve_tier_prices(self, item_data: Dict[str, Any], max_keys: Sequence[str]) -> Dict[str, float]:
        """
        Resolve Min/Med/High/Max PD anchors.

        Prefer Min Stat over base for the floor. Missing higher tiers inherit
        from the next-lower resolved tier (then base).
        """
        base_price = self._parse_optional_price(item_data.get("base"))
        if base_price is None:
            base_price = 0.0

        min_stat = self._parse_optional_price(item_data.get("Min Stat"))
        med_stat = self._parse_optional_price(item_data.get("Med Stat"))
        high_stat = self._parse_optional_price(item_data.get("High Stat"))

        max_stat: Optional[float] = None
        max_key_used: Optional[str] = None
        for key in max_keys:
            parsed = self._parse_optional_price(item_data.get(key))
            if parsed is not None:
                max_stat = parsed
                max_key_used = key
                break

        min_price = min_stat if min_stat is not None else base_price
        med_price = med_stat if med_stat is not None else min_price
        high_price = high_stat if high_stat is not None else med_price
        max_price = max_stat if max_stat is not None else high_price

        return {
            "base": base_price,
            "min": min_price,
            "med": med_price,
            "high": high_price,
            "max": max_price,
            "max_key": max_key_used or "",
            "raw": {
                "base": item_data.get("base"),
                "Min Stat": item_data.get("Min Stat"),
                "Med Stat": item_data.get("Med Stat"),
                "High Stat": item_data.get("High Stat"),
                **{k: item_data.get(k) for k in max_keys},
            },
        }

    def price_for_stats(
        self,
        dfp: int,
        evp: int,
        dfp_lo: int,
        dfp_hi: int,
        evp_lo: int,
        evp_hi: int,
        primary_stat: str,
        tier_prices: Dict[str, float],
    ) -> float:
        """
        Map one (DFP, EVP) roll to PD.

        Max tier requires both stats at their range max. Otherwise price by
        primary-stat quality using Min→Med→High (max primary alone → High).
        """
        if dfp_hi < dfp_lo or evp_hi < evp_lo:
            raise ValueError(f"Invalid stat ranges DFP[{dfp_lo},{dfp_hi}] EVP[{evp_lo},{evp_hi}]")

        both_max = dfp == dfp_hi and evp == evp_hi
        if both_max:
            return float(tier_prices["max"])

        if primary_stat == "dfp":
            return self._price_primary_non_max(dfp, dfp_lo, dfp_hi, tier_prices)
        return self._price_primary_non_max(evp, evp_lo, evp_hi, tier_prices)

    def _price_primary_non_max(
        self,
        value: int,
        lo: int,
        hi: int,
        tier_prices: Dict[str, float],
    ) -> float:
        """Price a non-dual-max roll from primary-stat quality (never Max tier)."""
        span = hi - lo
        if span == 0:
            # Fixed primary: always at its only value, but secondary not max → High
            return float(tier_prices["high"])

        if value == hi:
            # Max primary without max secondary → High, not Max
            return float(tier_prices["high"])

        non_max_span = span - 1
        if non_max_span <= 0:
            return float(tier_prices["min"])

        quality = (value - lo) / non_max_span
        return interpolate_tier_price(
            quality,
            float(tier_prices["min"]),
            float(tier_prices["med"]),
            float(tier_prices["high"]),
        )

    def _expected_value_for_joint_rolls(
        self,
        dfp_lo: int,
        dfp_hi: int,
        evp_lo: int,
        evp_hi: int,
        primary_stat: str,
        tier_prices: Dict[str, float],
    ) -> Tuple[float, List[Dict[str, Any]]]:
        dfp_values = list(range(dfp_lo, dfp_hi + 1))
        evp_values = list(range(evp_lo, evp_hi + 1))
        n = len(dfp_values) * len(evp_values)
        if n == 0:
            raise ValueError(f"Empty joint range DFP[{dfp_lo},{dfp_hi}] EVP[{evp_lo},{evp_hi}]")

        prob = 1.0 / n
        details: List[Dict[str, Any]] = []
        expected = 0.0
        for dfp in dfp_values:
            for evp in evp_values:
                both_max = dfp == dfp_hi and evp == evp_hi
                price = self.price_for_stats(
                    dfp, evp, dfp_lo, dfp_hi, evp_lo, evp_hi, primary_stat, tier_prices
                )
                contrib = price * prob
                expected += contrib
                details.append(
                    {
                        "dfp": dfp,
                        "evp": evp,
                        "both_max": both_max,
                        "price": price,
                        "probability": prob,
                        "contribution": contrib,
                    }
                )
        return expected, details

    def get_frame_value_breakdown(self, frame_name: str) -> Dict[str, Any]:
        frame_key, frame_data = self._get_frame_data(frame_name)
        stat_range = self._require_stat_range(frame_key, "frame")
        tier_prices = self._resolve_tier_prices(frame_data, ("Max Stat", "Max DFP"))
        dfp_lo, dfp_hi = stat_range.dfp
        evp_lo, evp_hi = stat_range.evp
        total, roll_details = self._expected_value_for_joint_rolls(
            dfp_lo, dfp_hi, evp_lo, evp_hi, "dfp", tier_prices
        )

        return {
            "item_name": frame_key,
            "kind": "frame",
            "primary_stat": "dfp",
            "stat_range": {"dfp": list(stat_range.dfp), "evp": list(stat_range.evp)},
            "tier_prices": tier_prices,
            "roll_details": roll_details,
            "total": total,
            "item_data": frame_data,
        }

    def get_barrier_value_breakdown(self, barrier_name: str) -> Dict[str, Any]:
        barrier_key, barrier_data = self._get_barrier_data(barrier_name)
        stat_range = self._require_stat_range(barrier_key, "barrier")
        tier_prices = self._resolve_tier_prices(barrier_data, ("Max EVP", "Max Stat"))
        dfp_lo, dfp_hi = stat_range.dfp
        evp_lo, evp_hi = stat_range.evp
        total, roll_details = self._expected_value_for_joint_rolls(
            dfp_lo, dfp_hi, evp_lo, evp_hi, "evp", tier_prices
        )

        return {
            "item_name": barrier_key,
            "kind": "barrier",
            "primary_stat": "evp",
            "stat_range": {"dfp": list(stat_range.dfp), "evp": list(stat_range.evp)},
            "tier_prices": tier_prices,
            "roll_details": roll_details,
            "total": total,
            "item_data": barrier_data,
        }

    def get_frame_calculation_breakdown(self, frame_name: str) -> Dict[str, Any]:
        breakdown = self.get_frame_value_breakdown(frame_name)
        return self._to_display_breakdown(breakdown)

    def get_barrier_calculation_breakdown(self, barrier_name: str) -> Dict[str, Any]:
        breakdown = self.get_barrier_value_breakdown(barrier_name)
        return self._to_display_breakdown(breakdown)

    def _to_display_breakdown(self, breakdown: Dict[str, Any]) -> Dict[str, Any]:
        tier_prices = breakdown["tier_prices"]
        roll_details = breakdown["roll_details"]
        primary = breakdown["primary_stat"]
        dfp_lo, dfp_hi = breakdown["stat_range"]["dfp"]
        evp_lo, evp_hi = breakdown["stat_range"]["evp"]
        n_dfp = dfp_hi - dfp_lo + 1
        n_evp = evp_hi - evp_lo + 1
        outcome_count = len(roll_details)

        both_max_details = [d for d in roll_details if d.get("both_max")]
        both_max_prob = sum(d["probability"] for d in both_max_details)
        both_max_contrib = sum(d["contribution"] for d in both_max_details)

        # Compact summary: group by distinct price for display
        price_groups: Dict[float, Dict[str, Any]] = {}
        for detail in roll_details:
            price = detail["price"]
            group = price_groups.setdefault(
                price,
                {
                    "price": price,
                    "values": [],
                    "pairs": [],
                    "probability": 0.0,
                    "contribution": 0.0,
                    "includes_both_max": False,
                },
            )
            primary_value = detail["dfp"] if primary == "dfp" else detail["evp"]
            if primary_value not in group["values"]:
                group["values"].append(primary_value)
            group["pairs"].append({"dfp": detail["dfp"], "evp": detail["evp"]})
            group["probability"] += detail["probability"]
            group["contribution"] += detail["contribution"]
            if detail.get("both_max"):
                group["includes_both_max"] = True

        for group in price_groups.values():
            group["values"].sort()

        return {
            "item_name": breakdown["item_name"],
            "kind": breakdown["kind"],
            "primary_stat": primary,
            "total_value": breakdown["total"],
            "base_price": tier_prices["base"],
            "base_price_str": breakdown["item_data"].get("base", "0"),
            "stat_range": breakdown["stat_range"],
            "primary_range": list(breakdown["stat_range"][primary]),
            "dfp_outcomes": n_dfp,
            "evp_outcomes": n_evp,
            "outcome_count": outcome_count,
            "both_max_probability": both_max_prob,
            "both_max_contribution": both_max_contrib,
            "tier_prices": {
                "min": tier_prices["min"],
                "med": tier_prices["med"],
                "high": tier_prices["high"],
                "max": tier_prices["max"],
                "max_key": tier_prices["max_key"],
            },
            "roll_details": roll_details,
            "price_groups": list(price_groups.values()),
            "item_data": breakdown["item_data"],
        }

    def print_frame_calculation_breakdown(self, frame_name: str) -> None:
        self._print_breakdown(self.get_frame_calculation_breakdown(frame_name))

    def print_barrier_calculation_breakdown(self, barrier_name: str) -> None:
        self._print_breakdown(self.get_barrier_calculation_breakdown(barrier_name))

    def _print_breakdown(self, breakdown: Dict[str, Any]) -> None:
        kind = breakdown["kind"].upper()
        primary = breakdown["primary_stat"].upper()
        dfp_lo, dfp_hi = breakdown["stat_range"]["dfp"]
        evp_lo, evp_hi = breakdown["stat_range"]["evp"]
        n = breakdown["outcome_count"]

        print(f"\n{'=' * 80}")
        print(f"{kind} VALUE CALCULATION BREAKDOWN")
        print(f"{'=' * 80}")
        print(f"{kind.title()}: {breakdown['item_name']}")
        print(f"Average Expected Value: {breakdown['total_value']:.4f} PD")
        print(f"\n{'-' * 80}")
        print(
            f"JOINT ROLLS: DFP[{dfp_lo},{dfp_hi}] × EVP[{evp_lo},{evp_hi}] "
            f"= {n} outcomes, p={1 / n:.6f} each"
        )
        print(f"Primary axis for Min/Med/High: {primary}")
        print(
            f"Max tier only when both max "
            f"(p={format_probability(breakdown['both_max_probability'])})"
        )
        print(f"{'-' * 80}")

        tiers = breakdown["tier_prices"]
        print(f"\n{'-' * 80}")
        print("TIER PRICE ANCHORS:")
        print(f"{'-' * 80}")
        print(f"  Base: {breakdown['base_price_str']} = {breakdown['base_price']:.4f} PD")
        print(f"  Min:  {tiers['min']:.4f} PD")
        print(f"  Med:  {tiers['med']:.4f} PD")
        print(f"  High: {tiers['high']:.4f} PD")
        max_label = tiers["max_key"] or "Max (fallback)"
        print(f"  Max:  {tiers['max']:.4f} PD ({max_label}; requires max DFP and max EVP)")

        print(f"\n{'-' * 80}")
        print("PRICE GROUPS (rolls sharing the same PD):")
        print(f"{'-' * 80}")
        print(f"  {'Primary values':<28} {'Price':<12} {'Prob':<18} {'Contribution':<14}")
        print(f"  {'-' * 28} {'-' * 12} {'-' * 18} {'-' * 14}")
        for group in breakdown["price_groups"]:
            values = group["values"]
            if group.get("includes_both_max"):
                value_str = f"both max ({dfp_hi}/{evp_hi})"
            elif len(values) <= 4:
                value_str = ",".join(str(v) for v in values)
            else:
                value_str = f"{values[0]}..{values[-1]} ({len(values)})"
            print(
                f"  {value_str:<28} {group['price']:<12.4f} "
                f"{format_probability(group['probability']):<18} {group['contribution']:<14.7f}"
            )

        print(f"\n{'-' * 80}")
        print("CALCULATION:")
        print(f"{'-' * 80}")
        print(f"  E[PD] = (1/{n}) * sum(price(dfp, evp) for all joint rolls)")
        print(f"  E[PD] = {breakdown['total_value']:.4f} PD")
        print(f"\n{'-' * 80}")
        print(f"FINAL RESULT: {breakdown['total_value']:.4f} PD")
        print(f"{'=' * 80}\n")
