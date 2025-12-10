"""
Calculate average weapon value based on drop location and attribute/hit patterns.

This module handles the probabilistic calculation of weapon values when dropped
from specific areas, taking into account:
- Area attribute probabilities (Native, A.Beast, Machine, Dark, Hit, No Attribute)
- Pattern value distributions (how many attributes roll and their value ranges)
- Price guide lookups for each possible combination
"""

from bisect import bisect
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from drop_tables.weapon_patterns import (
    AREA_ATTRIBUTE_RATES,
    PATTERN_ATTRIBUTE_PROBABILITIES,
    calculate_common_weapon_attributes,
    calculate_rare_weapon_attributes,
    get_hit_probability,
    get_three_roll_hit_probability,
)

if TYPE_CHECKING:
    from price_guide.price_guide import PriceGuideAbstract


def format_probability(prob: float) -> str:
    """Format probability as percentage with 6-7 decimal places for precision."""
    return f"{prob * 100:.7f}%"


class WeaponValueCalculator:
    """
    Calculate expected weapon values by combining pattern probabilities with prices.

    This is the "connective tissue" that takes pattern probabilities from
    weapon_patterns.py and multiplies them by prices from price_guide.py.
    """

    def __init__(self, price_guide: PriceGuideAbstract):
        """
        Initialize calculator with a price guide instance.

        Args:
            price_guide: PriceGuideAbstract instance for price lookups
        """
        self.price_guide = price_guide

    def calculate_weapon_expected_value(
        self,
        weapon_name: str,
        drop_area: Optional[str] = None,
    ) -> float:
        """
        Calculate expected weapon value based on pattern probabilities.

        For rare weapons: Always uses Pattern 5 for all attributes.
        For common weapons: Uses area-specific patterns.

        Args:
            weapon_name: Name of the weapon
            drop_area: Area where weapon drops (for hit probability calculation)

        Returns:
            Expected PD value
        """

        # Get weapon data (case-insensitive via price guide helper)
        weapon_data = self.price_guide.get_weapon_data(weapon_name)
        if not weapon_data:
            return 0.0

        if not weapon_data:
            return 0.0

        # For rare weapons, always use Pattern 5
        # Get Pattern 5 contributions (probabilities, not prices)
        attr_results = calculate_rare_weapon_attributes(weapon_data)

        # Calculate attribute contributions (multiply Pattern 5 prob by modifier price)
        attribute_contribution = self._calculate_attribute_contribution(weapon_data, attr_results)

        # Calculate hit probabilities once
        three_roll_hit_prob = get_three_roll_hit_probability(drop_area)
        no_hit_prob = 1.0 - three_roll_hit_prob

        # Calculate hit contribution using pre-calculated probabilities
        hit_contribution = self._calculate_hit_contribution(weapon_data, attr_results, three_roll_hit_prob, no_hit_prob)

        # Total expected value = hit + attribute (no separate base component)
        return attribute_contribution + hit_contribution

    def _calculate_attribute_contribution(
        self,
        weapon_data: Dict,
        attr_results: Dict[str, float],
    ) -> float:
        """
        Calculate expected PD value from attributes.

        Args:
            weapon_data: Weapon data from price guide
            attr_results: Results from calculate_weapon_attributes (probabilities)

        Returns:
            Expected attribute contribution in PD
        """
        modifiers = weapon_data.get("modifiers", {})
        attr_to_modifier = {
            "native": "N",
            "abeast": "AB",
            "machine": "M",
            "dark": "D",
        }

        attribute_contribution = 0.0
        for attr_name, mod_key in attr_to_modifier.items():
            if mod_key in modifiers and attr_name in attr_results:
                try:
                    modifier_price = self.price_guide.get_price_from_range(modifiers[mod_key], self.price_guide.bps)
                    attribute_contribution += attr_results[attr_name] * modifier_price
                except Exception:
                    pass

        return attribute_contribution

    def _calculate_hit_contribution(
        self,
        weapon_data: Dict,
        attr_results: Dict[str, float],
        three_roll_hit_prob: float,
        no_hit_prob: float,
    ) -> float:
        """
        Calculate expected hit value contribution.

        Uses teched hit values (original + 10) for price lookups.

        Args:
            weapon_data: Weapon data from price guide
            attr_results: Results from calculate_weapon_attributes
            three_roll_hit_prob: Pre-calculated probability of hitting in at least one of three rolls
            no_hit_prob: Pre-calculated probability of not hitting in any of three rolls

        Returns:
            Expected hit contribution in PD
        """
        hit_values = weapon_data.get("hit_values", {})
        if not hit_values or "hit" not in attr_results:
            return 0.0

        # Calculate hit contribution by iterating through Pattern 5 hit values
        hit_contribution = 0.0
        sorted_hits = sorted(map(int, hit_values.keys()))

        # No-hit contribution (if a 0-hit price exists)
        if "0" in hit_values:
            try:
                no_hit_price = self.price_guide.get_price_from_range(hit_values["0"], self.price_guide.bps)
                hit_contribution += no_hit_price * no_hit_prob
            except Exception:
                pass

        for hit_val, pattern5_prob in PATTERN_ATTRIBUTE_PROBABILITIES[5].items():
            # Combined probability = (three-roll hit prob) * (Pattern 5 prob for this hit value)
            combined_prob = three_roll_hit_prob * pattern5_prob

            # Tech the hit value: add 10 to the original hit value
            teched_hit = hit_val + 10

            # Find the price threshold for the teched hit value
            index = bisect(sorted_hits, teched_hit) - 1
            if index >= 0:
                threshold = sorted_hits[index]
                price_range = hit_values[str(threshold)]
                try:
                    hit_price = self.price_guide.get_price_from_range(price_range, self.price_guide.bps)
                    hit_contribution += hit_price * combined_prob
                except Exception:
                    pass

        return hit_contribution

    def get_rare_weapon_value_breakdown(
        self,
        weapon_name: str,
        drop_area: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed breakdown of weapon value calculation.

        Args:
            weapon_name: Name of the weapon
            drop_area: Area where weapon drops

        Returns:
            Dictionary with breakdown:
            {
                "base_price": float,
                "attribute_contribution": float,
                "hit_contribution": float,
                "total": float,
                "weapon_data": Dict,
                "attr_results": Dict,
                "hit_breakdown": List[Dict],
            }
        """

        # Get weapon data (case-insensitive via price guide helper)
        weapon_data = self.price_guide.get_weapon_data(weapon_name)

        # Get attribute and hit results (probabilities from weapon_patterns)
        attr_results = calculate_rare_weapon_attributes(weapon_data)

        # Calculate attribute contributions
        attribute_contribution = self._calculate_attribute_contribution(weapon_data, attr_results)

        # Calculate hit probabilities once
        three_roll_hit_prob = get_three_roll_hit_probability(drop_area)
        no_hit_prob = 1.0 - three_roll_hit_prob

        # Calculate hit breakdown using pre-calculated probabilities
        hit_breakdown = self._get_hit_breakdown(weapon_data, attr_results, three_roll_hit_prob, no_hit_prob)
        hit_contribution = sum(item["expected_value"] for item in hit_breakdown)

        return {
            "base_price": 0.0,
            "attribute_contribution": attribute_contribution,
            "hit_contribution": hit_contribution,
            "total": attribute_contribution + hit_contribution,
            "weapon_data": weapon_data,
            "attr_results": attr_results,
            "hit_breakdown": hit_breakdown,
        }

    def _get_hit_breakdown(
        self,
        weapon_data: Dict,
        attr_results: Dict[str, float],
        three_roll_hit_prob: float,
        no_hit_prob: float,
    ) -> List[Dict[str, Any]]:
        """
        Get detailed breakdown of hit value contributions.

        This uses the same logic as _calculate_hit_contribution but returns
        a detailed breakdown for display purposes.

        Args:
            weapon_data: Weapon data from price guide
            attr_results: Results from calculate_weapon_attributes
            three_roll_hit_prob: Pre-calculated probability of hitting in at least one of three rolls
            no_hit_prob: Pre-calculated probability of not hitting in any of three rolls

        Returns:
            List of dictionaries with hit value, probability, price, and expected value
        """

        hit_values = weapon_data.get("hit_values", {})
        if not hit_values or "hit" not in attr_results:
            return []
        sorted_hits = sorted(map(int, hit_values.keys()))
        breakdown = []

        # No-hit contribution if a 0-hit price is provided
        if "0" in hit_values:
            try:
                no_hit_price = self.price_guide.get_price_from_range(hit_values["0"], self.price_guide.bps)
                breakdown.append(
                    {
                        "hit_value": 0,
                        "teched_hit": 0,
                        "pattern5_prob": None,
                        "combined_prob": no_hit_prob,
                        "price_range": hit_values["0"],
                        "price": no_hit_price,
                        "expected_value": no_hit_price * no_hit_prob,
                    }
                )
            except Exception:
                pass

        for hit_val, pattern5_prob in PATTERN_ATTRIBUTE_PROBABILITIES[5].items():
            # Combined probability = (three-roll hit prob) * (Pattern 5 prob for this hit value)
            combined_prob = three_roll_hit_prob * pattern5_prob

            # Tech the hit value: add 10 to the original hit value
            teched_hit = hit_val + 10

            # Find the price threshold for the teched hit value
            index = bisect(sorted_hits, teched_hit) - 1
            if index >= 0:
                threshold = sorted_hits[index]
                price_range = hit_values[str(threshold)]
                try:
                    hit_price = self.price_guide.get_price_from_range(price_range, self.price_guide.bps)
                    expected_value = hit_price * combined_prob
                    breakdown.append(
                        {
                            "hit_value": hit_val,
                            "teched_hit": teched_hit,
                            "pattern5_prob": pattern5_prob,
                            "combined_prob": combined_prob,
                            "price_range": price_range,
                            "price": hit_price,
                            "expected_value": expected_value,
                        }
                    )
                except Exception:
                    pass

        return breakdown

    def print_calculation_breakdown(self, weapon_name: str, drop_area: Optional[str] = None):
        """Print detailed breakdown of the calculation."""

        avg_value = self.calculate_weapon_expected_value(weapon_name, drop_area)

        print(f"\n{'=' * 80}")
        print(f"WEAPON VALUE CALCULATION BREAKDOWN")
        print(f"{'=' * 80}")
        print(f"Weapon: {weapon_name}")
        print(f"Average Expected Value: {avg_value:.4f} PD")
        print(f"\n{'-' * 80}")

        # Get breakdown from price guide
        breakdown = self.get_rare_weapon_value_breakdown(weapon_name, drop_area)
        weapon_data = breakdown["weapon_data"]
        attr_results = breakdown["attr_results"]
        hit_breakdown = breakdown["hit_breakdown"]
        total_hit_contrib = breakdown["hit_contribution"]

        # Get area rates if area is specified
        area_rates = None
        # Get hit probabilities directly (not from breakdown)
        hit_probability = get_hit_probability(drop_area)
        three_roll_hit_prob = get_three_roll_hit_probability(drop_area)
        no_hit_prob = 1.0 - three_roll_hit_prob

        if drop_area and drop_area != "Pattern 5 (Rare Weapon)" and drop_area in AREA_ATTRIBUTE_RATES:
            area_rates = AREA_ATTRIBUTE_RATES[drop_area]
            # Handle both dict and dataclass formats
            if isinstance(area_rates, dict):
                total_rate = sum(area_rates.values())
                if total_rate > 0:
                    print("AREA ATTRIBUTE PROBABILITIES:")
                    print(f"{'-' * 80}")
                    print(f"Native:        {format_probability(area_rates['native'] / total_rate)}")
                    print(f"A.Beast:       {format_probability(area_rates['abeast'] / total_rate)}")
                    print(f"Machine:       {format_probability(area_rates['machine'] / total_rate)}")
                    print(f"Dark:          {format_probability(area_rates['dark'] / total_rate)}")
                    print(f"Hit:           {format_probability(hit_probability)}")
                    print(f"No Attribute:  {format_probability(area_rates['no_attribute'] / total_rate)}")
                    print(f"\n{'-' * 80}")

        # For rare weapons, always use Pattern 5
        print(f"\n{'-' * 80}")
        print("PATTERN CONFIGURATION: Pattern 5 (Rare weapons always use Pattern 5 for all attributes and hit)")
        print("")
        print(f"  {'Value':<8} {'Probability':<15}")
        print(f"  {'-' * 8} {'-' * 15}")
        for attr_val in sorted(PATTERN_ATTRIBUTE_PROBABILITIES[5].keys()):
            prob = PATTERN_ATTRIBUTE_PROBABILITIES[5][attr_val]
            print(f"  {attr_val:<8} {format_probability(prob):<15}")

        # Calculate and print hit distribution
        if weapon_data and "hit_values" in weapon_data:
            print(f"\n{'-' * 80}")
            print("HIT VALUE DISTRIBUTION:")
            print(f"{'-' * 80}")

            print(f"\nHit Probability Summary (Three Rolls):")
            print(f"  Hit Rolled (at least one): {format_probability(three_roll_hit_prob)}")
            print(f"  No Hit: {format_probability(no_hit_prob)}")
            print(f"  Total: {format_probability(no_hit_prob + three_roll_hit_prob)}")

            # Show detailed Pattern 5 breakdown with combined probabilities
            print(f"\nHit Value Prices and Expected Values:")
            print(
                f"  {'Hit':<6} {'Combined Prob':<20} {'Teched Hit':<12} "
                f"{'Price Range':<20} {'Price (avg)':<15} {'Expected Value':<18}"
            )
            print(f"  {'-' * 6} {'-' * 20} {'-' * 12} {'-' * 20} {'-' * 15} {'-' * 18}")

            total_expected = 0.0
            total_combined_prob_check = 0.0

            # Use combined_prob directly from breakdown (already includes three-roll hit logic)
            for item in hit_breakdown:
                combined_prob = item["combined_prob"]
                expected_value = item["expected_value"]

                total_expected += expected_value
                total_combined_prob_check += combined_prob
                teched_hit = item.get("teched_hit", item["hit_value"] + 10)
                price_range = item.get("price_range", "N/A")
                price_val = item.get("price", 0.0)
                print(
                    f"  {item['hit_value']:<6} {format_probability(combined_prob):<20} "
                    f"{teched_hit:<12} {price_range:<20} {price_val:<15.4f} {expected_value:<18.7f}"
                )

            # Verify probabilities sum to 100%
            print(
                f"  {'Total':<6} {format_probability(total_combined_prob_check):<20} "
                f"{'':<12} {'':<20} {'':<15} {total_expected:<18.7f}"
            )
            print(f"\n  Probability Check:")
            print(
                f"    Combined probabilities (no hit + all hit values) sum to: {format_probability(total_combined_prob_check)}"
            )

        # Calculate and print attribute contribution (multiply by prices)
        total_attr_contrib = breakdown["attribute_contribution"]
        if weapon_data:
            modifiers = weapon_data.get("modifiers", {})
            if modifiers:
                print(f"\n{'-' * 80}")
                print("ATTRIBUTE VALUE DISTRIBUTION (Pattern 5, >=50% only):")
                print(f"{'-' * 80}")

                attr_to_modifier = {"native": "N", "abeast": "AB", "machine": "M", "dark": "D"}
                for attr_name, attr_type in attr_to_modifier.items():
                    if attr_type in modifiers and attr_name in attr_results:
                        modifier_price_str = modifiers[attr_type]
                        try:
                            modifier_price = self.price_guide.get_price_from_range(modifier_price_str, self.price_guide.bps)
                            # attr_results[attr_name] is already probability * Pattern 5 prob sum (>=50%)
                            attr_contrib = attr_results[attr_name] * modifier_price
                            print(f"  {attr_type}: Expected contribution = {attr_contrib:.4f} PD")
                            print(f"    (Probability assigned * Pattern 5 prob sum >= 50% * modifier price)")
                        except Exception:
                            continue

        # Print equation
        print(f"\n{'-' * 80}")
        print("CALCULATION EQUATION:")
        print(f"{'-' * 80}")
        print("Final Value = Hit Contribution + Attribute Contribution")
        print()
        print("Where:")
        print("  Hit Contribution = sum over hit rows [price(hit) * combined_prob(hit)]")
        print("    combined_prob already includes the three-roll hit chance and Pattern 5 distribution")
        print(f"                    = {total_hit_contrib:.4f} PD")

        print()
        print("  Attribute Contribution (Pattern 5, >=50% prob slice already baked in)")
        print(f"                         = {total_attr_contrib:.4f} PD")
        print()
        print(f"Calculation:")
        print(f"  {total_hit_contrib:.4f} + {total_attr_contrib:.4f} = {total_hit_contrib + total_attr_contrib:.4f} PD")

        final_result = total_hit_contrib + total_attr_contrib
        print(f"\n{'-' * 80}")
        print(f"FINAL RESULT: {final_result:.4f} PD")
        print(f"{'=' * 80}\n")
