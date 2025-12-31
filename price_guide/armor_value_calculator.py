"""
Calculate average armor (frame) and shield (barrier) value based on stat tier probabilities.

This module handles the probabilistic calculation of armor and shield values when dropped,
taking into account:
- Stat tier probabilities (Low, Medium, High, Max)
- Price guide lookups for each stat tier
- Base price fallbacks when tier prices are not defined
"""

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from price_guide import PriceGuideExceptionItemNameNotFound

if TYPE_CHECKING:
    from price_guide.price_guide import PriceGuideAbstract


def format_probability(prob: float) -> str:
    """Format probability as percentage with 6-7 decimal places for precision."""
    return f"{prob * 100:.7f}%"


class ArmorValueCalculator:
    """
    Calculate expected armor (frame) and shield (barrier) values by combining
    stat tier probabilities with prices.

    This is the "connective tissue" that takes stat tier probabilities and
    multiplies them by prices from price_guide.py.
    """

    def __init__(self, price_guide: "PriceGuideAbstract"):
        """
        Initialize calculator with a price guide instance.

        Args:
            price_guide: PriceGuideAbstract instance for price lookups
        """
        self.price_guide = price_guide

    def get_stat_probabilities(self) -> Dict[str, float]:
        """
        Get probability distribution for stat tiers.

        Returns:
            Dictionary mapping stat tier to probability:
            - "low": 0.396 (equal to medium)
            - "medium": 0.396 (equal to low)
            - "high": 0.198 (half of low/medium)
            - "max": 0.01 (1/100)
        """
        # Low and Medium are equal chance
        # High is half of that
        # Max stat is 1/100
        # 2x + x/2 + 0.01 = 1
        # 2.5x = 0.99
        # x = 0.396
        return {
            "low": 0.396,
            "medium": 0.396,
            "high": 0.198,
            "max": 0.01,
        }

    def calculate_frame_expected_value(self, frame_name: str) -> float:
        """
        Calculate expected frame (armor) value based on DEF stat probabilities.

        Args:
            frame_name: Name of the frame

        Returns:
            Expected PD value
        """
        # Get frame data from price guide
        frame_key = self.price_guide._ci_key(self.price_guide.frame_prices, frame_name)
        if frame_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {frame_name} not found in frame_prices")

        frame_data = self.price_guide.frame_prices[frame_key]

        # Calculate expected DEF value
        expected_def_value, _, _, _, _ = self._get_frame_def_value(frame_data)

        # Note: Slot value is not included in expected value calculation
        # as slots are typically added manually, not part of the drop

        return expected_def_value

    def calculate_barrier_expected_value(self, barrier_name: str) -> float:
        """
        Calculate expected barrier (shield) value based on EVP stat probabilities.

        Args:
            barrier_name: Name of the barrier

        Returns:
            Expected PD value
        """
        # Get barrier data from price guide
        barrier_key = self.price_guide._ci_key(self.price_guide.barrier_prices, barrier_name)
        if barrier_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {barrier_name} not found in barrier_prices")

        barrier_data = self.price_guide.barrier_prices[barrier_key]

        # Calculate expected EVP value
        expected_evp_value, _, _, _, _ = self._get_barrier_evp_value(barrier_data)

        return expected_evp_value

    def _get_frame_def_value(self, frame_data: Dict) -> Tuple[float, Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Get DEF value for a frame based on stat tier probabilities.

        Args:
            frame_data: Frame data dictionary from price guide

        Returns:
            Tuple of (expected_def_value, min_stat_price, med_stat_price, high_stat_price, max_stat_price)
            Prices are in PD, expected_def_value is weighted average
        """
        stat_probs = self.get_stat_probabilities()

        # Get base price (this is the "base" value, typically for min stat or no stat)
        base_price_str = frame_data.get("base", "0")
        base_price = self.price_guide.get_price_from_range(base_price_str, self.price_guide.bps)

        # Get stat tier prices
        min_stat_str = frame_data.get("Min Stat")
        med_stat_str = frame_data.get("Med Stat")
        high_stat_str = frame_data.get("High Stat")
        max_stat_str = frame_data.get("Max Stat")

        min_stat_price = None
        med_stat_price = None
        high_stat_price = None
        max_stat_price = None

        if min_stat_str:
            min_stat_price = self.price_guide.get_price_from_range(min_stat_str, self.price_guide.bps)
        if med_stat_str:
            med_stat_price = self.price_guide.get_price_from_range(med_stat_str, self.price_guide.bps)
        if high_stat_str:
            high_stat_price = self.price_guide.get_price_from_range(high_stat_str, self.price_guide.bps)
        if max_stat_str:
            max_stat_price = self.price_guide.get_price_from_range(max_stat_str, self.price_guide.bps)

        # Calculate expected value as weighted average of stat tier prices
        # Use base price as fallback if tier price is not defined
        expected_value = 0.0

        # Low tier
        if min_stat_price is not None:
            expected_value += min_stat_price * stat_probs["low"]
        else:
            # If min stat not defined, use base price for low tier
            expected_value += base_price * stat_probs["low"]

        # Medium tier
        if med_stat_price is not None:
            expected_value += med_stat_price * stat_probs["medium"]
        else:
            # If med stat not defined, use base price for medium tier
            expected_value += base_price * stat_probs["medium"]

        # High tier
        if high_stat_price is not None:
            expected_value += high_stat_price * stat_probs["high"]
        else:
            # If high stat not defined, use base price for high tier
            expected_value += base_price * stat_probs["high"]

        # Max tier
        if max_stat_price is not None:
            expected_value += max_stat_price * stat_probs["max"]
        else:
            # If max stat not defined, use base price for max tier
            expected_value += base_price * stat_probs["max"]

        return expected_value, min_stat_price, med_stat_price, high_stat_price, max_stat_price

    def _get_barrier_evp_value(self, barrier_data: Dict) -> Tuple[float, Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Get EVP (EVA) value for a barrier based on stat tier probabilities.

        Args:
            barrier_data: Barrier data dictionary from price guide

        Returns:
            Tuple of (expected_evp_value, min_stat_price, med_stat_price, high_stat_price, max_evp_price)
            Prices are in PD, expected_evp_value is weighted average
        """
        stat_probs = self.get_stat_probabilities()

        # Get base price (this is the "base" value, typically for min stat or no stat)
        base_price_str = barrier_data.get("base", "0")
        base_price = self.price_guide.get_price_from_range(base_price_str, self.price_guide.bps)

        # Get stat tier prices
        min_stat_str = barrier_data.get("Min Stat")
        med_stat_str = barrier_data.get("Med Stat")
        high_stat_str = barrier_data.get("High Stat")
        max_evp_str = barrier_data.get("Max EVP")

        min_stat_price = None
        med_stat_price = None
        high_stat_price = None
        max_evp_price = None

        if min_stat_str:
            min_stat_price = self.price_guide.get_price_from_range(min_stat_str, self.price_guide.bps)
        if med_stat_str:
            med_stat_price = self.price_guide.get_price_from_range(med_stat_str, self.price_guide.bps)
        if high_stat_str:
            high_stat_price = self.price_guide.get_price_from_range(high_stat_str, self.price_guide.bps)
        if max_evp_str:
            max_evp_price = self.price_guide.get_price_from_range(max_evp_str, self.price_guide.bps)

        # Calculate expected value as weighted average of stat tier prices
        # Use base price as fallback if tier price is not defined
        expected_value = 0.0

        # Low tier
        if min_stat_price is not None:
            expected_value += min_stat_price * stat_probs["low"]
        else:
            # If min stat not defined, use base price for low tier
            expected_value += base_price * stat_probs["low"]

        # Medium tier
        if med_stat_price is not None:
            expected_value += med_stat_price * stat_probs["medium"]
        else:
            # If med stat not defined, use base price for medium tier
            expected_value += base_price * stat_probs["medium"]

        # High tier
        if high_stat_price is not None:
            expected_value += high_stat_price * stat_probs["high"]
        else:
            # If high stat not defined, use base price for high tier
            expected_value += base_price * stat_probs["high"]

        # Max tier
        if max_evp_price is not None:
            expected_value += max_evp_price * stat_probs["max"]
        else:
            # If max evp not defined, use base price for max tier
            expected_value += base_price * stat_probs["max"]

        return expected_value, min_stat_price, med_stat_price, high_stat_price, max_evp_price

    def get_frame_value_breakdown(self, frame_name: str) -> Dict[str, Any]:
        """
        Get detailed breakdown of frame value calculation.

        Args:
            frame_name: Name of the frame

        Returns:
            Dictionary with breakdown:
            {
                "base_price": float,
                "stat_tier_contributions": Dict[str, float],
                "total": float,
                "frame_data": Dict,
                "stat_probs": Dict[str, float],
            }
        """
        # Get frame data from price guide
        frame_key = self.price_guide._ci_key(self.price_guide.frame_prices, frame_name)
        if frame_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {frame_name} not found in frame_prices")

        frame_data = self.price_guide.frame_prices[frame_key]
        stat_probs = self.get_stat_probabilities()

        # Get DEF value breakdown
        expected_value, min_stat_price, med_stat_price, high_stat_price, max_stat_price = self._get_frame_def_value(frame_data)

        # Get base price
        base_price_str = frame_data.get("base", "0")
        base_price = self.price_guide.get_price_from_range(base_price_str, self.price_guide.bps)

        # Calculate contributions for each tier
        stat_tier_contributions = {}
        stat_tier_contributions["low"] = (min_stat_price if min_stat_price is not None else base_price) * stat_probs["low"]
        stat_tier_contributions["medium"] = (med_stat_price if med_stat_price is not None else base_price) * stat_probs["medium"]
        stat_tier_contributions["high"] = (high_stat_price if high_stat_price is not None else base_price) * stat_probs["high"]
        stat_tier_contributions["max"] = (max_stat_price if max_stat_price is not None else base_price) * stat_probs["max"]

        return {
            "base_price": base_price,
            "stat_tier_contributions": stat_tier_contributions,
            "total": expected_value,
            "frame_data": frame_data,
            "stat_probs": stat_probs,
            "tier_prices": {
                "min_stat": min_stat_price,
                "med_stat": med_stat_price,
                "high_stat": high_stat_price,
                "max_stat": max_stat_price,
            },
        }

    def get_barrier_value_breakdown(self, barrier_name: str) -> Dict[str, Any]:
        """
        Get detailed breakdown of barrier value calculation.

        Args:
            barrier_name: Name of the barrier

        Returns:
            Dictionary with breakdown:
            {
                "base_price": float,
                "stat_tier_contributions": Dict[str, float],
                "total": float,
                "barrier_data": Dict,
                "stat_probs": Dict[str, float],
            }
        """
        # Get barrier data from price guide
        barrier_key = self.price_guide._ci_key(self.price_guide.barrier_prices, barrier_name)
        if barrier_key is None:
            raise PriceGuideExceptionItemNameNotFound(f"Item name {barrier_name} not found in barrier_prices")

        barrier_data = self.price_guide.barrier_prices[barrier_key]
        stat_probs = self.get_stat_probabilities()

        # Get EVP value breakdown
        expected_value, min_stat_price, med_stat_price, high_stat_price, max_evp_price = self._get_barrier_evp_value(barrier_data)

        # Get base price
        base_price_str = barrier_data.get("base", "0")
        base_price = self.price_guide.get_price_from_range(base_price_str, self.price_guide.bps)

        # Calculate contributions for each tier
        stat_tier_contributions = {}
        stat_tier_contributions["low"] = (min_stat_price if min_stat_price is not None else base_price) * stat_probs["low"]
        stat_tier_contributions["medium"] = (med_stat_price if med_stat_price is not None else base_price) * stat_probs["medium"]
        stat_tier_contributions["high"] = (high_stat_price if high_stat_price is not None else base_price) * stat_probs["high"]
        stat_tier_contributions["max"] = (max_evp_price if max_evp_price is not None else base_price) * stat_probs["max"]

        return {
            "base_price": base_price,
            "stat_tier_contributions": stat_tier_contributions,
            "total": expected_value,
            "barrier_data": barrier_data,
            "stat_probs": stat_probs,
            "tier_prices": {
                "min_stat": min_stat_price,
                "med_stat": med_stat_price,
                "high_stat": high_stat_price,
                "max_evp": max_evp_price,
            },
        }

    def get_frame_calculation_breakdown(self, frame_name: str) -> Dict[str, Any]:
        """
        Get detailed breakdown of the frame calculation as structured data.

        Args:
            frame_name: Name of the frame

        Returns:
            Dictionary with comprehensive breakdown data for display
        """
        breakdown = self.get_frame_value_breakdown(frame_name)
        frame_data = breakdown["frame_data"]
        stat_probs = breakdown["stat_probs"]
        stat_tier_contributions = breakdown["stat_tier_contributions"]
        tier_prices = breakdown["tier_prices"]
        total = breakdown["total"]
        base_price = breakdown["base_price"]

        # Build tier details
        tier_details = []
        tier_info = [
            ("low", "Min Stat", tier_prices["min_stat"]),
            ("medium", "Med Stat", tier_prices["med_stat"]),
            ("high", "High Stat", tier_prices["high_stat"]),
            ("max", "Max Stat", tier_prices["max_stat"]),
        ]

        for tier, stat_key, tier_price in tier_info:
            price_range = frame_data.get(stat_key, "N/A")
            price_val = tier_price if tier_price is not None else base_price
            prob = stat_probs[tier]
            contrib = stat_tier_contributions[tier]
            tier_details.append(
                {
                    "tier": tier,
                    "stat_key": stat_key,
                    "price_range": price_range,
                    "price": price_val,
                    "probability": prob,
                    "contribution": contrib,
                }
            )

        return {
            "frame_name": frame_name,
            "total_value": total,
            "base_price": base_price,
            "base_price_str": frame_data.get("base", "0"),
            "stat_probs": stat_probs,
            "tier_details": tier_details,
            "stat_tier_contributions": stat_tier_contributions,
            "tier_prices": tier_prices,
            "frame_data": frame_data,
        }

    def print_frame_calculation_breakdown(self, frame_name: str):
        """Print detailed breakdown of the frame calculation."""
        breakdown = self.get_frame_calculation_breakdown(frame_name)

        frame_name_display = breakdown["frame_name"]
        total = breakdown["total_value"]
        base_price = breakdown["base_price"]
        base_price_str = breakdown["base_price_str"]
        stat_probs = breakdown["stat_probs"]
        tier_details = breakdown["tier_details"]
        stat_tier_contributions = breakdown["stat_tier_contributions"]

        print(f"\n{'=' * 80}")
        print(f"FRAME VALUE CALCULATION BREAKDOWN")
        print(f"{'=' * 80}")
        print(f"Frame: {frame_name_display}")
        print(f"Average Expected Value: {total:.4f} PD")
        print(f"\n{'-' * 80}")

        # Print stat tier probabilities
        print("STAT TIER PROBABILITIES:")
        print(f"{'-' * 80}")
        print(f"  {'Tier':<10} {'Probability':<20}")
        print(f"  {'-' * 10} {'-' * 20}")
        for tier, prob in stat_probs.items():
            print(f"  {tier.capitalize():<10} {format_probability(prob):<20}")

        # Print base price
        print(f"\n{'-' * 80}")
        print("BASE PRICE:")
        print(f"{'-' * 80}")
        print(f"  Base Price: {base_price_str} = {base_price:.4f} PD")

        # Print stat tier prices and contributions
        print(f"\n{'-' * 80}")
        print("STAT TIER PRICES AND CONTRIBUTIONS:")
        print(f"{'-' * 80}")
        print(f"  {'Tier':<10} {'Price Range':<20} {'Price (avg)':<15} {'Probability':<20} {'Contribution':<18}")
        print(f"  {'-' * 10} {'-' * 20} {'-' * 15} {'-' * 20} {'-' * 18}")

        for tier_detail in tier_details:
            print(
                f"  {tier_detail['tier'].capitalize():<10} {str(tier_detail['price_range']):<20} "
                f"{tier_detail['price']:<15.4f} {format_probability(tier_detail['probability']):<20} "
                f"{tier_detail['contribution']:<18.7f}"
            )

        # Print equation
        print(f"\n{'-' * 80}")
        print("CALCULATION EQUATION:")
        print(f"{'-' * 80}")
        print("Final Value = sum over tiers [tier_price * tier_probability]")
        print()
        print("Where:")
        for tier_detail in tier_details:
            print(
                f"  {tier_detail['tier'].capitalize()} tier: {tier_detail['price']:.4f} * "
                f"{format_probability(tier_detail['probability'])} = {tier_detail['contribution']:.4f} PD"
            )
        print()
        print(f"Calculation:")
        total_check = sum(stat_tier_contributions.values())
        print(f"  {total_check:.4f} = {total:.4f} PD")

        print(f"\n{'-' * 80}")
        print(f"FINAL RESULT: {total:.4f} PD")
        print(f"{'=' * 80}\n")

    def get_barrier_calculation_breakdown(self, barrier_name: str) -> Dict[str, Any]:
        """
        Get detailed breakdown of the barrier calculation as structured data.

        Args:
            barrier_name: Name of the barrier

        Returns:
            Dictionary with comprehensive breakdown data for display
        """
        breakdown = self.get_barrier_value_breakdown(barrier_name)
        barrier_data = breakdown["barrier_data"]
        stat_probs = breakdown["stat_probs"]
        stat_tier_contributions = breakdown["stat_tier_contributions"]
        tier_prices = breakdown["tier_prices"]
        total = breakdown["total"]
        base_price = breakdown["base_price"]

        # Build tier details
        tier_details = []
        tier_info = [
            ("low", "Min Stat", tier_prices["min_stat"]),
            ("medium", "Med Stat", tier_prices["med_stat"]),
            ("high", "High Stat", tier_prices["high_stat"]),
            ("max", "Max EVP", tier_prices["max_evp"]),
        ]

        for tier, stat_key, tier_price in tier_info:
            price_range = barrier_data.get(stat_key, "N/A")
            price_val = tier_price if tier_price is not None else base_price
            prob = stat_probs[tier]
            contrib = stat_tier_contributions[tier]
            tier_details.append(
                {
                    "tier": tier,
                    "stat_key": stat_key,
                    "price_range": price_range,
                    "price": price_val,
                    "probability": prob,
                    "contribution": contrib,
                }
            )

        return {
            "barrier_name": barrier_name,
            "total_value": total,
            "base_price": base_price,
            "base_price_str": barrier_data.get("base", "0"),
            "stat_probs": stat_probs,
            "tier_details": tier_details,
            "stat_tier_contributions": stat_tier_contributions,
            "tier_prices": tier_prices,
            "barrier_data": barrier_data,
        }

    def print_barrier_calculation_breakdown(self, barrier_name: str):
        """Print detailed breakdown of the barrier calculation."""
        breakdown = self.get_barrier_calculation_breakdown(barrier_name)

        barrier_name_display = breakdown["barrier_name"]
        total = breakdown["total_value"]
        base_price = breakdown["base_price"]
        base_price_str = breakdown["base_price_str"]
        stat_probs = breakdown["stat_probs"]
        tier_details = breakdown["tier_details"]
        stat_tier_contributions = breakdown["stat_tier_contributions"]

        print(f"\n{'=' * 80}")
        print(f"BARRIER VALUE CALCULATION BREAKDOWN")
        print(f"{'=' * 80}")
        print(f"Barrier: {barrier_name_display}")
        print(f"Average Expected Value: {total:.4f} PD")
        print(f"\n{'-' * 80}")

        # Print stat tier probabilities
        print("STAT TIER PROBABILITIES:")
        print(f"{'-' * 80}")
        print(f"  {'Tier':<10} {'Probability':<20}")
        print(f"  {'-' * 10} {'-' * 20}")
        for tier, prob in stat_probs.items():
            print(f"  {tier.capitalize():<10} {format_probability(prob):<20}")

        # Print base price
        print(f"\n{'-' * 80}")
        print("BASE PRICE:")
        print(f"{'-' * 80}")
        print(f"  Base Price: {base_price_str} = {base_price:.4f} PD")

        # Print stat tier prices and contributions
        print(f"\n{'-' * 80}")
        print("STAT TIER PRICES AND CONTRIBUTIONS:")
        print(f"{'-' * 80}")
        print(f"  {'Tier':<10} {'Price Range':<20} {'Price (avg)':<15} {'Probability':<20} {'Contribution':<18}")
        print(f"  {'-' * 10} {'-' * 20} {'-' * 15} {'-' * 20} {'-' * 18}")

        for tier_detail in tier_details:
            print(
                f"  {tier_detail['tier'].capitalize():<10} {str(tier_detail['price_range']):<20} "
                f"{tier_detail['price']:<15.4f} {format_probability(tier_detail['probability']):<20} "
                f"{tier_detail['contribution']:<18.7f}"
            )

        # Print equation
        print(f"\n{'-' * 80}")
        print("CALCULATION EQUATION:")
        print(f"{'-' * 80}")
        print("Final Value = sum over tiers [tier_price * tier_probability]")
        print()
        print("Where:")
        for tier_detail in tier_details:
            print(
                f"  {tier_detail['tier'].capitalize()} tier: {tier_detail['price']:.4f} * "
                f"{format_probability(tier_detail['probability'])} = {tier_detail['contribution']:.4f} PD"
            )
        print()
        print(f"Calculation:")
        total_check = sum(stat_tier_contributions.values())
        print(f"  {total_check:.4f} = {total:.4f} PD")

        print(f"\n{'-' * 80}")
        print(f"FINAL RESULT: {total:.4f} PD")
        print(f"{'=' * 80}\n")
