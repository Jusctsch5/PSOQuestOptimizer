#!/usr/bin/env python3
"""
Script to calculate average weapon value based on drop location and patterns.

This script demonstrates the weapon value calculation and shows
the probability distributions for different attribute/hit combinations.
"""

import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from bisect import bisect

from price_guide import PriceGuideFixed
from drop_tables.weapon_patterns import (
    PATTERN_ATTRIBUTE_PROBABILITIES,
    PATTERN_5_HIT_PROBABILITIES,
    AREA_ATTRIBUTE_RATES,
    calculate_weapon_attributes,
    get_hit_breakdown_data,
)

def format_probability(prob: float) -> str:
    """Format probability as percentage with 6-7 decimal places for precision."""
    return f"{prob * 100:.7f}%"


def print_calculation_breakdown(
    price_guide: PriceGuideFixed,
    weapon_name: str,
    drop_area: str,
    avg_value: float,
):
    """Print detailed breakdown of the calculation."""
    print(f"\n{'='*80}")
    print(f"WEAPON VALUE CALCULATION BREAKDOWN")
    print(f"{'='*80}")
    print(f"Weapon: {weapon_name}")
    print(f"Drop Area: {drop_area}")
    print(f"Average Expected Value: {avg_value:.4f} PD")
    print(f"\n{'-'*80}")
    
    # Get breakdown from price guide
    breakdown = price_guide.get_weapon_value_breakdown(weapon_name, drop_area)
    weapon_data = breakdown["weapon_data"]
    attr_results = breakdown["attr_results"]
    hit_breakdown = breakdown["hit_breakdown"]
    total_hit_contrib = breakdown["hit_contribution"]
    base_price = breakdown["base_price"]
    
    # Get area rates if area is specified
    area_rates = None
    hit_breakdown_data = get_hit_breakdown_data(drop_area)
    hit_probability = hit_breakdown_data["single_roll_hit_prob"]
    three_roll_hit_prob = hit_breakdown_data["three_roll_hit_prob"]
    no_hit_prob = hit_breakdown_data["no_hit_prob"]
    
    if drop_area and drop_area != "Pattern 5 (Rare Weapon)" and drop_area in AREA_ATTRIBUTE_RATES:
        area_rates = AREA_ATTRIBUTE_RATES[drop_area]
        # Handle both dict and dataclass formats
        if isinstance(area_rates, dict):
            total_rate = sum(area_rates.values())
            if total_rate > 0:
                print("AREA ATTRIBUTE PROBABILITIES:")
                print(f"{'-'*80}")
                print(f"Native:        {format_probability(area_rates['native'] / total_rate)}")
                print(f"A.Beast:       {format_probability(area_rates['abeast'] / total_rate)}")
                print(f"Machine:       {format_probability(area_rates['machine'] / total_rate)}")
                print(f"Dark:          {format_probability(area_rates['dark'] / total_rate)}")
                print(f"Hit:           {format_probability(hit_probability)}")
                print(f"No Attribute:  {format_probability(area_rates['no_attribute'] / total_rate)}")
                print(f"\n{'-'*80}")
    
    if weapon_data:
        print(f"Base Price: {base_price:.4f} PD")
    
    # For rare weapons, always use Pattern 5
    print(f"\n{'-'*80}")
    print("PATTERN CONFIGURATION:")
    print(f"{'-'*80}")
    print("Rare weapons always use Pattern 5 for all attributes and hit.")
    
    # Print Pattern 5 attribute probabilities
    print(f"\n{'-'*80}")
    print("PATTERN 5 ATTRIBUTE PROBABILITIES:")
    print(f"{'-'*80}")
    print(f"  {'Value':<8} {'Probability':<15}")
    print(f"  {'-'*8} {'-'*15}")
    for attr_val in sorted(PATTERN_ATTRIBUTE_PROBABILITIES[5].keys()):
        prob = PATTERN_ATTRIBUTE_PROBABILITIES[5][attr_val]
        print(f"  {attr_val:<8} {format_probability(prob):<15}")
    
    # Calculate and print hit distribution
    if weapon_data and "hit_values" in weapon_data:
        hit_values = weapon_data["hit_values"]
        sorted_hits = sorted(map(int, hit_values.keys()))
        
        print(f"\n{'-'*80}")
        print("HIT VALUE DISTRIBUTION:")
        print(f"{'-'*80}")
        print("For rare weapons, hit uses Pattern 5:")
        if area_rates:
            print(f"  1. First roll for hit: {format_probability(hit_probability)} (from area rates)")
        else:
            print(f"  1. First roll for hit: (area not specified, using default)")
            hit_probability = 0.05  # Default 5%
        print("  2. Then roll Pattern 5 to determine hit value")
        
        print(f"\nHit Probability Summary (Three Rolls):")
        print(f"  Single Roll Hit Chance: {format_probability(hit_probability)}")
        print(f"  No Hit (all three rolls): {format_probability(no_hit_prob)}")
        print(f"  Hit Rolled (at least one): {format_probability(three_roll_hit_prob)}")
        print(f"  Total: {format_probability(no_hit_prob + three_roll_hit_prob)}")
        
        # Show detailed Pattern 5 breakdown with combined probabilities
        print(f"\nPattern 5 Hit Value Breakdown:")
        print(f"  {'Hit':<6} {'Combined Prob':<20} {'Teched Hit':<12} {'Price Range':<20} {'Price (avg)':<15} {'Expected Value':<15}")
        print(f"  {'-'*6} {'-'*20} {'-'*12} {'-'*20} {'-'*15} {'-'*15}")
        
        # Add 0 hit row (no hit rolled)
        print(f"  {'0':<6} {format_probability(no_hit_prob):<20} {'0':<12} {'N/A':<20} {'0.0000':<15} {'0.0000':<15}")
        
        total_expected = 0.0
        total_combined_prob_check = no_hit_prob
        
        # Recalculate combined probabilities using three_roll_hit_prob to ensure they sum to 100%
        for item in hit_breakdown:
            # Recalculate combined_prob using three_roll_hit_prob instead of hit_assigned_prob
            # This ensures probabilities sum correctly
            corrected_combined_prob = three_roll_hit_prob * item['pattern5_prob']
            expected_value = item['price'] * corrected_combined_prob
            
            total_expected += expected_value
            total_combined_prob_check += corrected_combined_prob
            teched_hit = item.get('teched_hit', item['hit_value'] + 10)
            print(f"  {item['hit_value']:<6} {format_probability(corrected_combined_prob):<20} {teched_hit:<12} {item['price_range']:<20} {item['price']:<15.4f} {expected_value:<15.4f}")
        
        # Verify probabilities sum to 100%
        print(f"  {'Total':<6} {format_probability(total_combined_prob_check):<20} {'':<12} {'':<20} {'':<15} {total_expected:<15.4f}")
        print(f"\n  Probability Check:")
        print(f"    Combined probabilities (no hit + all hit values) sum to: {format_probability(total_combined_prob_check)}")
    
    # Calculate and print attribute contribution (multiply by prices)
    total_attr_contrib = breakdown["attribute_contribution"]
    if weapon_data:
        modifiers = weapon_data.get("modifiers", {})
        if modifiers:
            print(f"\n{'-'*80}")
            print("ATTRIBUTE VALUE DISTRIBUTION (Pattern 5, >=50% only):")
            print(f"{'-'*80}")
            
            attr_to_modifier = {"native": "N", "abeast": "AB", "machine": "M", "dark": "D"}
            for attr_name, attr_type in attr_to_modifier.items():
                if attr_type in modifiers and attr_name in attr_results:
                    modifier_price_str = modifiers[attr_type]
                    try:
                        modifier_price = PriceGuideFixed.get_price_from_range(
                            modifier_price_str,
                            price_guide.bps
                        )
                        # attr_results[attr_name] is already probability * Pattern 5 prob sum (>=50%)
                        attr_contrib = attr_results[attr_name] * modifier_price
                        print(f"  {attr_type}: Expected contribution = {attr_contrib:.4f} PD")
                        print(f"    (Probability assigned * Pattern 5 prob sum >= 50% * modifier price)")
                    except Exception:
                        continue
    
    # Build hit contribution terms for display
    hit_contrib_terms = []
    if weapon_data and "hit_values" in weapon_data:
        hit_values = weapon_data["hit_values"]
        hit_assigned_prob = attr_results.get("hit", 0.0)
        
        # Handle 0 hit case (no hit rolled)
        if "0" in hit_values:
            try:
                no_hit_price = price_guide.get_price_from_range(
                    hit_values["0"],
                    price_guide.bps
                )
                no_hit_term_value = no_hit_price * no_hit_prob
                if no_hit_term_value > 0:
                    hit_contrib_terms.append((0, no_hit_price, no_hit_prob, no_hit_term_value))
            except Exception:
                pass
        
        # Add terms from breakdown
        for item in hit_breakdown:
            if item["expected_value"] > 0:
                hit_contrib_terms.append((
                    item["hit_value"],
                    item["price"],
                    item["combined_prob"],
                    item["expected_value"]
                ))
    
    # Print equation
    print(f"\n{'-'*80}")
    print("CALCULATION EQUATION:")
    print(f"{'-'*80}")
    print("Final Value = Base Price + Hit Contribution + Attribute Contribution")
    print()
    print("Where:")
    print(f"  Base Price = {base_price:.4f} PD")
    print()
    print("  Hit Contribution = (no_hit_prob * hit_price[0]) + Sum(hit_val>0) [hit_price[hit_val] * (three_roll_hit_prob * Pattern5_prob[hit_val])]")
    print("    where three_roll_hit_prob = 1 - (1 - single_roll_hit_prob)^3")
    if hit_contrib_terms:
        # Sort terms: 0 hit first, then others
        hit_contrib_terms_sorted = sorted(hit_contrib_terms, key=lambda x: x[0])
        
        # Print each term on a new line for readability
        for i, (hit_val, price, prob, term_val) in enumerate(hit_contrib_terms_sorted):
            if hit_val == 0:
                term_str = f"hit0 (no hit): {price:.4f} * {format_probability(prob)} = {term_val:.4f}"
            else:
                term_str = f"hit{hit_val}: {price:.4f} * {format_probability(prob)} = {term_val:.4f}"
            
            if i == 0:
                print(f"                    = {term_str}")
            else:
                print("                      + " + term_str)
        print(f"                    = {total_hit_contrib:.4f} PD")
    else:
        print(f"                    = {total_hit_contrib:.4f} PD")
    
    print()
    print("  Attribute Contribution = Sum(attr_type) [modifier_price[attr_type] * Sum(attr_val>=50) Pattern5_prob[attr_val]]")
    if weapon_data:
        modifiers = weapon_data.get("modifiers", {})
        attr_terms = []
        for attr_type in ["N", "AB", "M", "D"]:
            if attr_type in modifiers:
                modifier_price_str = modifiers[attr_type]
                try:
                    modifier_price = PriceGuideFixed.get_price_from_range(
                        modifier_price_str,
                        price_guide.bps
                    )
                    # Sum Pattern 5 probabilities for attributes >= 50%
                    attr_prob_sum = sum(
                        prob for attr_val, prob in PATTERN_ATTRIBUTE_PROBABILITIES[5].items()
                        if attr_val >= 50
                    )
                    if attr_prob_sum > 0 and modifier_price > 0:
                        attr_contrib = modifier_price * attr_prob_sum
                        attr_terms.append(f"{attr_type}: {modifier_price:.4f} * {format_probability(attr_prob_sum)} = {attr_contrib:.4f}")
                except Exception:
                    pass
        if attr_terms:
            for term in attr_terms:
                print(f"                         {term}")
        else:
            print(f"                         = 0.0000")
    print(f"                         = {total_attr_contrib:.4f} PD")
    print()
    print(f"Calculation:")
    print(f"  {base_price:.4f} + {total_hit_contrib:.4f} + {total_attr_contrib:.4f} = {base_price + total_hit_contrib + total_attr_contrib:.4f} PD")
    
    final_result = base_price + total_hit_contrib + total_attr_contrib
    print(f"\n{'-'*80}")
    print(f"FINAL RESULT: {final_result:.4f} PD")
    print(f"{'='*80}\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Calculate average weapon value based on drop location and Pattern 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate VJAYA value (uses Pattern 5 for rare weapons)
  python calculate_weapon_value.py VJAYA
  
  # Calculate EXCALIBUR value
  python calculate_weapon_value.py EXCALIBUR
  
  # Use custom price guide directory
  python calculate_weapon_value.py VJAYA --price-guide ../PSOPriceGuide/pso_price_guide/data
        """
    )
    
    parser.add_argument(
        "weapon",
        type=str,
        help="Weapon name (e.g., VJAYA, EXCALIBUR)"
    )
    
    parser.add_argument(
        "--area",
        type=str,
        default=None,
        help="Drop area (e.g., 'Forest 1', 'Ruins 3', 'VR Temple Alpha'). Affects hit probability."
    )
    
    parser.add_argument(
        "--price-guide",
        type=str,
        default=None,
        help="Path to price guide data directory (default: ./price_guide/data)"
    )
    
    args = parser.parse_args()
    
    # Set up paths
    base_path = Path(__file__).parent
    drop_table_path = base_path / "drop_tables" / "drop_tables_ultimate.json"
    
    if args.price_guide:
        price_guide_path = Path(args.price_guide)
    else:
        price_guide_path = base_path / "price_guide" / "data"
    
    if not price_guide_path.exists():
        print(f"Error: Price guide directory not found at {price_guide_path}")
        print(f"Please specify the correct path with --price-guide")
        return 1
    
    # Initialize price guide
    try:
        price_guide = PriceGuideFixed(str(price_guide_path))
    except Exception as e:
        print(f"Error initializing price guide: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Validate area if provided
    if args.area and args.area not in AREA_ATTRIBUTE_RATES:
        print(f"Error: Unknown drop area '{args.area}'")
        print(f"\nValid areas:")
        for area in sorted(AREA_ATTRIBUTE_RATES.keys()):
            print(f"  - {area}")
        return 1
    
    # Calculate average value (rare weapons always use Pattern 5)
    # Note: Area affects hit probability (first roll), but attributes always use Pattern 5
    try:
        avg_value = price_guide.get_weapon_expected_value(args.weapon, args.area)
    except Exception as e:
        print(f"Error calculating value: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print detailed breakdown
    drop_area = args.area if args.area else "Pattern 5 (Rare Weapon)"
    print_calculation_breakdown(
        price_guide,
        args.weapon,
        drop_area,
        avg_value
    )
    
    return 0


if __name__ == "__main__":
    exit(main())

