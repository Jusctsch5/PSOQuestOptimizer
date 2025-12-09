"""
Parse price guide HTML and extract data into JSON files.

This script parses price_guide_sample.html and extracts all price guide
tables into structured JSON files.
"""

import html
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup, Tag, NavigableString


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove HTML entities
    text = text.replace("\xa0", " ")  # Non-breaking space
    return text.strip()


def extract_item_name(cell: Tag) -> str:
    """Extract item name from a table cell."""
    # Look for <a> tag with class "rare" or any <a> tag
    link = cell.find("a", class_="rare")
    if not link:
        link = cell.find("a")
    
    if link:
        # Get text from the link
        name = clean_text(link.get_text())
        if name:
            return name
    
    # Fall back to cell text
    text = clean_text(cell.get_text())
    return text


def parse_price_value(text: str) -> Optional[str]:
    """Parse price value, handling special cases."""
    if not text:
        return None
    
    text = clean_text(text)
    
    # Handle special values
    if text.upper() in ["N/A", "NA", "-", ""]:
        return None
    
    if text.upper() == "INESTIMABLE":
        return "Inestimable"
    
    # Return as-is (could be "1", "1-2", "0.5-1", etc.)
    return text


def get_table_headers(table: Tag) -> List[str]:
    """Extract table headers, handling rowspan/colspan."""
    headers = []
    thead = table.find("thead")
    if not thead:
        return headers
    
    # Find all header rows
    header_rows = thead.find_all("tr")
    if not header_rows:
        return headers
    
    # For now, get the last row of headers (most specific)
    last_row = header_rows[-1]
    for th in last_row.find_all("th"):
        text = clean_text(th.get_text())
        if text:
            headers.append(text)
    
    return headers


def parse_simple_table(table: Tag) -> List[Dict[str, Any]]:
    """Parse a simple 2-column table (Item Name, Price)."""
    results = []
    tbody = table.find("tbody")
    if not tbody:
        return results
    
    # Skip header row
    rows = tbody.find_all("tr")
    for row in rows:
        # Skip if this is a header row (all cells are th)
        if all(cell.name == "th" for cell in row.find_all(["td", "th"])):
            continue
        
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            item_name = extract_item_name(cells[0])
            price = parse_price_value(cells[1].get_text())
            # Skip if item_name looks like a header
            if item_name and item_name.lower() not in ["item name", "class", "technique", "price"]:
                results.append({
                    "item": item_name,
                    "price": price
                })
    
    return results


def parse_hit_table(table: Tag) -> Dict[str, Dict[str, str]]:
    """
    Parse a table with hit columns (e.g., 50%, 55%, 60% or 0%, 15%, 20%).
    Structure: Weapon Type, Special, Hit columns
    Handles rowspan and colspan correctly.
    """
    results = {}
    tbody = table.find("tbody")
    if not tbody:
        return results
    
    # Get headers from thead
    thead = table.find("thead")
    hit_headers = []
    if thead:
        # Find the row with hit headers (usually second row)
        header_rows = thead.find_all("tr")
        if len(header_rows) >= 2:
            hit_row = header_rows[1]
            for th in hit_row.find_all("th"):
                text = clean_text(th.get_text())
                if "%" in text or text.isdigit():
                    hit_headers.append(text.replace("%", "").strip())
    
    current_weapon = None
    current_special = None
    
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        
        # Check if first cell is a weapon name (might have rowspan)
        first_cell = cells[0]
        if first_cell.get("rowspan"):
            current_weapon = extract_item_name(first_cell)
            if current_weapon and current_weapon not in results:
                results[current_weapon] = {}
            # Move to next cell for special
            if len(cells) > 1:
                current_special = clean_text(cells[1].get_text())
        else:
            # This row continues a weapon, new special
            current_special = clean_text(cells[0].get_text())
        
        if not current_weapon or not current_special:
            continue
        
        if current_weapon not in results:
            results[current_weapon] = {}
        if current_special not in results[current_weapon]:
            results[current_weapon][current_special] = {}
        
        # Parse hit columns, handling colspan
        # Start after weapon type and special columns
        if first_cell.get("rowspan"):
            # Weapon has rowspan, so special is in cells[1], hit data starts at cells[2]
            data_start_idx = 2
        else:
            # No rowspan, special is in cells[0], hit data starts at cells[1]
            data_start_idx = 1
        
        hit_idx = 0
        cell_idx = data_start_idx
        
        while cell_idx < len(cells) and hit_idx < len(hit_headers):
            cell = cells[cell_idx]
            colspan = int(cell.get("colspan", 1))
            price = parse_price_value(cell.get_text())
            
            # Apply price to all hit values covered by this colspan
            for _ in range(colspan):
                if hit_idx < len(hit_headers):
                    hit_value = hit_headers[hit_idx]
                    if price:
                        results[current_weapon][current_special][hit_value] = price
                    hit_idx += 1
            
            cell_idx += 1
    
    return results


def parse_rare_weapon_table(table: Tag) -> Dict[str, Dict[str, Any]]:
    """
    Parse a rare weapon table with Item Name, optionally High Attribute Value (N, AB, M, D),
    and Hit Amount columns (0%, 15%, 20%, etc.).
    Some tables have modifiers, some don't.
    
    Uses data-attributes when available (more reliable), falls back to column-based parsing.
    """
    results = {}
    tbody = table.find("tbody")
    if not tbody:
        return results
    
    # Get headers from thead to detect if modifiers exist
    thead = table.find("thead")
    has_modifiers = False
    modifier_headers = ["N", "AB", "M", "D"]
    hit_headers = []
    
    if thead:
        header_rows = thead.find_all("tr")
        if len(header_rows) >= 1:
            # Check first row for "High Attribute Value"
            first_row = header_rows[0]
            for th in first_row.find_all("th"):
                text = clean_text(th.get_text())
                if "High Attribute Value" in text or "Attribute" in text:
                    has_modifiers = True
                    break
        
        if len(header_rows) >= 2:
            # Second row has the actual column headers
            header_row = header_rows[1]
            for th in header_row.find_all("th"):
                text = clean_text(th.get_text())
                if text in modifier_headers:
                    continue  # Modifiers are in first row
                elif "%" in text or text.isdigit():
                    hit_headers.append(text.replace("%", "").strip())
    
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells or len(cells) < 2:
            continue
        
        item_name = extract_item_name(cells[0])
        if not item_name:
            continue
        
        if item_name not in results:
            results[item_name] = {
                "base": None,
                "modifiers": {},
                "hit_values": {}
            }
        
        # Check if any cell has data-attributes (more reliable method)
        has_data_attributes = any(
            cell.get("data-attributes") for cell in cells[1:] if isinstance(cell, Tag)
        )
        
        if has_data_attributes:
            # Use data-attributes method (most reliable) - DO NOT fall back to column-based
            for cell_idx in range(1, len(cells)):  # Start at 1 (skip item name)
                cell = cells[cell_idx]
                if not isinstance(cell, Tag):
                    continue
                
                data_attrs = cell.get("data-attributes")
                if not data_attrs:
                    continue  # Skip cells without data-attributes
                
                price = parse_price_value(cell.get_text())
                
                try:
                    # Parse the JSON in data-attributes
                    # BeautifulSoup already unescapes HTML entities, but we need to handle &quot;
                    data_attrs_clean = data_attrs.replace("&quot;", '"')
                    attrs = json.loads(data_attrs_clean)
                    
                    # Check if this cell has hit values
                    if "hit" in attrs:
                        hit_data = attrs["hit"]
                        if isinstance(hit_data, list):
                            # Multiple hit values (e.g., [0,15,20,25,30])
                            for hit_val in hit_data:
                                if price:
                                    results[item_name]["hit_values"][str(hit_val)] = price
                        elif isinstance(hit_data, (int, float)):
                            # Single hit value
                            if price:
                                results[item_name]["hit_values"][str(int(hit_data))] = price
                    
                    # Check if this cell has modifier values (N, AB, M, D)
                    for mod_type in ["N", "AB", "M", "D"]:
                        if mod_type in attrs:
                            mod_value = attrs[mod_type]
                            if isinstance(mod_value, list):
                                # Multiple values - use first or join
                                if price:
                                    results[item_name]["modifiers"][mod_type] = price
                            elif isinstance(mod_value, (int, float, str)):
                                # Single value - use the price from cell
                                if price:
                                    results[item_name]["modifiers"][mod_type] = price
                                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    # If data-attributes parsing fails, skip this cell but continue
                    # Don't fall back to column-based parsing for this row
                    continue
        else:
            # Fall back to column-based parsing (old method)
            # Track current position in data columns (0 = item name, 1+ = data)
            current_col = 0  # Start after item name
            
            if has_modifiers:
                # Process cells, tracking which column we're at
                for cell_idx in range(1, len(cells)):  # Start at 1 (skip item name)
                    cell = cells[cell_idx]
                    colspan = int(cell.get("colspan", 1))
                    price = parse_price_value(cell.get_text())
                    
                    # Process this cell's colspan
                    for _ in range(colspan):
                        if current_col < 4:
                            # Still in modifier columns (0-3 = N, AB, M, D)
                            mod = modifier_headers[current_col]
                            if price and price.upper() != "N/A":
                                results[item_name]["modifiers"][mod] = price
                        else:
                            # In hit value columns (4+)
                            hit_col = current_col - 4  # Convert to hit column index
                            if hit_col < len(hit_headers):
                                hit_value = hit_headers[hit_col]
                                if price:
                                    results[item_name]["hit_values"][hit_value] = price
                        current_col += 1
            else:
                # No modifiers, hit columns start immediately
                hit_idx = 0
                
                for cell_idx in range(1, len(cells)):  # Start at 1 (skip item name)
                    if hit_idx >= len(hit_headers):
                        break
                    
                    cell = cells[cell_idx]
                    colspan = int(cell.get("colspan", 1))
                    price = parse_price_value(cell.get_text())
                    
                    # Apply price to all hit values covered by this colspan
                    for _ in range(colspan):
                        if hit_idx < len(hit_headers):
                            hit_value = hit_headers[hit_idx]
                            if price:
                                results[item_name]["hit_values"][hit_value] = price
                            hit_idx += 1
        
        # If no hit values but we have a base price, check if all cells are the same
        if not results[item_name]["hit_values"] and len(cells) > 1:
            # Check if all modifier cells have the same value (could be base price)
            first_price = parse_price_value(cells[1].get_text())
            if first_price and first_price.upper() not in ["N/A", "NA"]:
                # Check if all modifier columns have same value
                all_same = all(
                    parse_price_value(cells[i + 1].get_text()) == first_price
                    for i in range(min(4, len(cells) - 1))
                )
                if all_same:
                    results[item_name]["base"] = first_price
    
    return results


def parse_stat_table(table: Tag) -> Dict[str, Dict[str, str]]:
    """
    Parse a table with stat columns (Min Stat, Med Stat, High Stat, Max DFP, Max Stat).
    Used for frames.
    """
    results = {}
    tbody = table.find("tbody")
    if not tbody:
        return results
    
    headers = get_table_headers(table)
    stat_columns = [h for h in headers if h not in ["Item Name"]]
    
    for row in tbody.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells or len(cells) < 2:
            continue
        
        item_name = extract_item_name(cells[0])
        if not item_name:
            continue
        
        if item_name not in results:
            results[item_name] = {}
        
        # Parse stat columns
        for i, stat_col in enumerate(stat_columns):
            if i + 1 < len(cells):
                price = parse_price_value(cells[i + 1].get_text())
                if price:
                    results[item_name][stat_col] = price
    
    return results


def find_section_tables(soup: BeautifulSoup, section_id: str) -> List[Tag]:
    """Find all tables within a section identified by heading ID."""
    section = soup.find(id=section_id)
    if not section:
        return []
    
    # Find the parent heading
    heading = section.find_parent(["h2", "h3", "h4", "h5"])
    if not heading:
        return []
    
    tables = []
    # Find all tables after this heading until next same-level heading
    current = heading.next_sibling
    while current:
        if isinstance(current, Tag):
            # Check if we hit another heading of same or higher level
            if current.name in ["h2", "h3", "h4", "h5"]:
                if current.name <= heading.name:
                    break
            
            # Check for tables
            if current.name == "table":
                tables.append(current)
            else:
                # Look for tables within this element
                tables.extend(current.find_all("table"))
        
        current = current.next_sibling
    
    return tables


def save_json(data: Dict[str, Any], filepath: Path, merge: bool = False):
    """Save data to JSON file, optionally merging with existing."""
    if merge and filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # Merge data (new data takes precedence)
        if isinstance(existing, dict) and isinstance(data, dict):
            existing.update(data)
            data = existing
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_meseta(soup: BeautifulSoup, output_dir: Path):
    """Extract Meseta section."""
    section = soup.find(id="Meseta")
    if not section:
        print("Meseta section not found")
        return
    
    # Find table after the heading
    heading = section.find_parent("h2")
    if not heading:
        return
    
    table = None
    current = heading.next_sibling
    while current:
        if isinstance(current, Tag):
            if current.name == "table":
                table = current
                break
            # Look for table in nested divs
            nested_table = current.find("table")
            if nested_table:
                table = nested_table
                break
            # Stop at next h2
            if current.name == "h2":
                break
        current = current.next_sibling
    
    if not table:
        print("Meseta table not found")
        return
    
    # Parse simple table
    tbody = table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
        if len(rows) >= 2:
            # Second row has the value
            cells = rows[1].find_all("td")
            if cells:
                value = clean_text(cells[0].get_text())
                data = {"meseta_per_pd": value}
                
                output_file = output_dir / "meseta.json"
                save_json(data, output_file)
                print(f"Extracted Meseta: {value}")
                return
    
    print("Could not parse Meseta table")


def extract_services(soup: BeautifulSoup, output_dir: Path):
    """Extract Services section (Unsealing and Instant unsealing)."""
    data = {
        "unsealing": {},
        "instant_unsealing": {}
    }
    
    # Extract Unsealing
    unsealing_section = soup.find(id="Unsealing")
    if unsealing_section:
        heading = unsealing_section.find_parent("h3")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name in ["h2", "h3"]:
                        break
                current = current.next_sibling
            
            if table:
                items = parse_simple_table(table)
                for item in items:
                    if item["item"] and item["price"]:
                        data["unsealing"][item["item"]] = item["price"]
    
    # Extract Instant unsealing
    instant_section = soup.find(id="Instant_unsealing")
    if instant_section:
        heading = instant_section.find_parent("h3")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name in ["h2", "h3"]:
                        break
                current = current.next_sibling
            
            if table:
                # This table has rowspan in header, handle differently
                tbody = table.find("tbody")
                if tbody:
                    rows = tbody.find_all("tr")
                    # Skip header rows
                    for row in rows[2:]:  # Skip first two header rows
                        cells = row.find_all("td")
                        if len(cells) >= 3:
                            item_name = extract_item_name(cells[0])
                            per_kill = parse_price_value(cells[1].get_text())
                            total = parse_price_value(cells[2].get_text())
                            if item_name:
                                data["instant_unsealing"][item_name] = {
                                    "per_kill": per_kill,
                                    "total": total
                                }
    
    output_file = output_dir / "services.json"
    save_json(data, output_file)
    print(f"Extracted Services: {len(data['unsealing'])} unsealing items, {len(data['instant_unsealing'])} instant unsealing items")


def extract_techniques(soup: BeautifulSoup, output_dir: Path):
    """Extract Techniques section (sets and individual techniques)."""
    data = {
        "sets": {},
        "individual": {}
    }
    
    # Extract Technique sets
    sets_section = soup.find(id="Technique_sets")
    if sets_section:
        heading = sets_section.find_parent("h3")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name in ["h2", "h3"]:
                        break
                current = current.next_sibling
            
            if table:
                items = parse_simple_table(table)
                for item in items:
                    if item["item"] and item["price"]:
                        # Handle multiple classes in one cell (e.g., "HUmar, RAmar")
                        classes = [c.strip() for c in item["item"].split(",")]
                        for cls in classes:
                            data["sets"][cls] = item["price"]
    
    # Extract Individual techniques - Attack techniques
    attack_section = soup.find(id="Attack_techniques")
    if attack_section:
        heading = attack_section.find_parent("h4")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name in ["h2", "h3", "h4"]:
                        break
                current = current.next_sibling
            
            if table:
                tbody = table.find("tbody")
                if tbody:
                    # Find header rows to get level columns
                    header_rows = tbody.find_all("tr")
                    level_headers = []
                    if len(header_rows) >= 2:
                        # Second header row has level numbers
                        level_row = header_rows[1]
                        for th in level_row.find_all("th"):
                            text = clean_text(th.get_text())
                            # Extract level number (e.g., "Level 15" -> "15")
                            match = re.search(r'(\d+)', text)
                            if match:
                                level_headers.append(match.group(1))
                    
                    # Parse data rows
                    for row in header_rows[2:]:  # Skip header rows
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue
                        
                        # Extract technique name
                        tech_link = cells[0].find("a", class_="link")
                        if tech_link:
                            tech_name = clean_text(tech_link.get_text())
                        else:
                            tech_name = clean_text(cells[0].get_text())
                        
                        if not tech_name or tech_name.lower() == "technique":
                            continue
                        
                        if tech_name not in data["individual"]:
                            data["individual"][tech_name] = {}
                        
                        # Parse level columns
                        for i, level in enumerate(level_headers):
                            if i + 1 < len(cells):
                                price = parse_price_value(cells[i + 1].get_text())
                                if price:
                                    data["individual"][tech_name][level] = price
    
    # Extract Individual techniques - Recovery and Support techniques
    recovery_section = soup.find(id="Recovery_and_Support_techniques")
    if recovery_section:
        heading = recovery_section.find_parent("h4")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name in ["h2", "h3", "h4"]:
                        break
                current = current.next_sibling
            
            if table:
                tbody = table.find("tbody")
                if tbody:
                    header_rows = tbody.find_all("tr")
                    level_headers = []
                    if len(header_rows) >= 2:
                        level_row = header_rows[1]
                        for th in level_row.find_all("th"):
                            text = clean_text(th.get_text())
                            match = re.search(r'(\d+)', text)
                            if match:
                                level_headers.append(match.group(1))
                    
                    for row in header_rows[2:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue
                        
                        tech_link = cells[0].find("a", class_="link")
                        if tech_link:
                            tech_name = clean_text(tech_link.get_text())
                        else:
                            tech_name = clean_text(cells[0].get_text())
                        
                        if not tech_name or tech_name.lower() == "technique":
                            continue
                        
                        if tech_name not in data["individual"]:
                            data["individual"][tech_name] = {}
                        
                        for i, level in enumerate(level_headers):
                            if i + 1 < len(cells):
                                price = parse_price_value(cells[i + 1].get_text())
                                if price:
                                    data["individual"][tech_name][level] = price
    
    output_file = output_dir / "techniques.json"
    save_json(data, output_file)
    print(f"Extracted Techniques: {len(data['sets'])} sets, {len(data['individual'])} individual techniques")


def extract_common_weapons(soup: BeautifulSoup, output_dir: Path):
    """Extract Common Weapons section (all subsections)."""
    data = {
        "melee": {},
        "ranged": {},
        "technique": {},
        "combination": {},
        "claires_deal_5": {},
        "event": {}
    }
    
    # List of subsections to extract
    subsections = [
        ("Melee_commons", "melee"),
        ("Ranged_commons", "ranged"),
        ("Technique_commons", "technique"),
        ("Combination_commons", "combination"),
        ("Claire's_Deal_5_commons", "claires_deal_5"),
        ("Event_commons", "event")
    ]
    
    for section_id, key in subsections:
        section = soup.find(id=section_id)
        if not section:
            # Try alternative ID format
            section = soup.find(id=section_id.replace("'", ".27"))
            if not section:
                print(f"  {section_id} not found, skipping...")
                continue
        
        heading = section.find_parent(["h3", "h4"])
        if not heading:
            continue
        
        # Find table after heading
        table = None
        current = heading.next_sibling
        while current:
            if isinstance(current, Tag):
                if current.name == "table":
                    table = current
                    break
                nested_table = current.find("table")
                if nested_table:
                    table = nested_table
                    break
                if current.name in ["h2", "h3", "h4"]:
                    break
            current = current.next_sibling
        
        if table:
            parsed = parse_hit_table(table)
            data[key] = parsed
            print(f"  Extracted {section_id}: {len(parsed)} weapons")
    
    output_file = output_dir / "common_weapons.json"
    save_json(data, output_file)
    total_weapons = sum(len(v) for v in data.values())
    print(f"Extracted Common Weapons: {total_weapons} total weapons across all subsections")


def extract_rare_weapons(soup: BeautifulSoup, output_dir: Path):
    """Extract Rare Weapons section (all subsections)."""
    # Load existing weapons.json if it exists
    existing_file = output_dir / "weapons.json"
    existing_data = {}
    if existing_file.exists():
        with open(existing_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    
    # List of all rare weapon subsections
    subsections = [
        ("Sabers", "Melee_weapons"),
        ("Swords", "Melee_weapons"),
        ("Daggers", "Melee_weapons"),
        ("Partisans", "Melee_weapons"),
        ("Slicers", "Melee_weapons"),
        ("Double_Sabers", "Melee_weapons"),
        ("Claws", "Melee_weapons"),
        ("Katanas", "Melee_weapons"),
        ("Twin_Swords", "Melee_weapons"),
        ("Fists", "Melee_weapons"),
        ("Handguns", "Ranged_weapons"),
        ("Rifles", "Ranged_weapons"),
        ("Mechguns", "Ranged_weapons"),
        ("Shots", "Ranged_weapons"),
        ("Bazookas", "Ranged_weapons"),
        ("Canes", "Technique_weapons"),
        ("Rods", "Technique_weapons"),
        ("Wands", "Technique_weapons"),
        ("Cards", "Technique_weapons"),
        ("Specials", "ES_weapons"),
        ("TypeM_weapons", None)
    ]
    
    total_extracted = 0
    for section_id, parent_section in subsections:
        section = soup.find(id=section_id)
        if not section:
            continue
        
        heading = section.find_parent(["h4", "h5", "h3"])
        if not heading:
            continue
        
        # Find table after heading
        table = None
        current = heading.next_sibling
        while current:
            if isinstance(current, Tag):
                if current.name == "table":
                    table = current
                    break
                nested_table = current.find("table")
                if nested_table:
                    table = nested_table
                    break
                if current.name in ["h2", "h3", "h4", "h5"]:
                    break
            current = current.next_sibling
        
        if table:
            parsed = parse_rare_weapon_table(table)
            # Merge with existing data
            for item_name, item_data in parsed.items():
                # Use uppercase for consistency
                item_key = item_name.upper()
                existing_data[item_key] = item_data
            total_extracted += len(parsed)
            print(f"  Extracted {section_id}: {len(parsed)} weapons")
    
    # Save merged data
    output_file = output_dir / "weapons.json"
    save_json(existing_data, output_file)
    print(f"Extracted Rare Weapons: {total_extracted} new/updated weapons (total: {len(existing_data)})")


def extract_frames(soup: BeautifulSoup, output_dir: Path):
    """Extract Frames section."""
    # Load existing frames.json if it exists
    existing_file = output_dir / "frames.json"
    existing_data = {}
    if existing_file.exists():
        with open(existing_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    
    # Extract Common frames
    common_section = soup.find(id="Frames")
    if common_section:
        heading = common_section.find_parent("h2")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name == "h2":
                        break
                current = current.next_sibling
            
            if table:
                items = parse_simple_table(table)
                for item in items:
                    if item["item"] and item["price"]:
                        # Common frames have slot-based pricing
                        item_key = item["item"]
                        if item_key not in existing_data:
                            existing_data[item_key] = {}
                        # Note: This is simplified - actual structure has 1-3 slots and 4 slots
    
    # Extract Rare frames - Offensive frames
    offensive_section = soup.find(id="Offensive_frames")
    if offensive_section:
        heading = offensive_section.find_parent("h4")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name in ["h2", "h3", "h4"]:
                        break
                current = current.next_sibling
            
            if table:
                parsed = parse_stat_table(table)
                for item_name, stats in parsed.items():
                    if item_name not in existing_data:
                        existing_data[item_name] = {}
                    # Add stat-based pricing
                    existing_data[item_name].update(stats)
                    # If no base price, use min stat as base
                    if "base" not in existing_data[item_name] and stats:
                        first_stat = list(stats.values())[0]
                        if first_stat:
                            existing_data[item_name]["base"] = first_stat
    
    # Extract Rare frames - Technique frames
    tech_section = soup.find(id="Technique_frames")
    if tech_section:
        heading = tech_section.find_parent("h4")
        if heading:
            table = None
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        table = current
                        break
                    nested_table = current.find("table")
                    if nested_table:
                        table = nested_table
                        break
                    if current.name in ["h2", "h3", "h4"]:
                        break
                current = current.next_sibling
            
            if table:
                parsed = parse_stat_table(table)
                for item_name, stats in parsed.items():
                    if item_name not in existing_data:
                        existing_data[item_name] = {}
                    existing_data[item_name].update(stats)
                    if "base" not in existing_data[item_name] and stats:
                        first_stat = list(stats.values())[0]
                        if first_stat:
                            existing_data[item_name]["base"] = first_stat
    
    output_file = output_dir / "frames.json"
    save_json(existing_data, output_file)
    print(f"Extracted Frames: {len(existing_data)} frames")


def verify_other_sections(soup: BeautifulSoup, output_dir: Path):
    """Verify and extract other sections (barriers, units, tools, mags, etc.)."""
    sections_to_verify = [
        ("Barriers", "barriers.json", "Rare_barriers"),
        ("Units", "units.json", "Rare_units"),
        ("Tools", "tools.json", "Currencies"),
        ("Mags", "mags.json", "Mag_types"),
    ]
    
    for section_name, filename, section_id in sections_to_verify:
        section = soup.find(id=section_id)
        if not section:
            print(f"  {section_name}: Section not found, skipping...")
            continue
        
        # Load existing file
        existing_file = output_dir / filename
        existing_data = {}
        if existing_file.exists():
            with open(existing_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        
        # Find all tables in this section and extract
        heading = section.find_parent(["h2", "h3", "h4"])
        if heading:
            tables = []
            current = heading.next_sibling
            while current:
                if isinstance(current, Tag):
                    if current.name == "table":
                        tables.append(current)
                    elif current.name in ["h2", "h3"]:
                        # Stop at next major section
                        if current.name == "h2":
                            break
                    else:
                        nested_tables = current.find_all("table")
                        tables.extend(nested_tables)
                current = current.next_sibling
            
            # Extract from all tables
            for table in tables:
                items = parse_simple_table(table)
                for item in items:
                    if item["item"] and item["price"]:
                        item_key = item["item"]
                        if item_key not in existing_data:
                            existing_data[item_key] = {}
                        if isinstance(existing_data[item_key], dict):
                            if "base" not in existing_data[item_key]:
                                existing_data[item_key]["base"] = item["price"]
                        else:
                            # If it's not a dict, replace it
                            existing_data[item_key] = {"base": item["price"]}
        
        # Save updated data
        output_file = output_dir / filename
        save_json(existing_data, output_file)
        print(f"  Verified {section_name}: {len(existing_data)} items")


def main():
    """Main function to parse HTML and extract all sections."""
    script_dir = Path(__file__).parent
    html_file = script_dir / "price_guide_sample.html"
    output_dir = script_dir.parent / "data"
    
    if not html_file.exists():
        print(f"Error: {html_file} not found")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading HTML from {html_file}")
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, "lxml")
    
    print("HTML loaded, starting extraction...")
    
    # Extract simple sections first
    print("\n=== Extracting Meseta ===")
    extract_meseta(soup, output_dir)
    
    print("\n=== Extracting Services ===")
    extract_services(soup, output_dir)
    
    print("\n=== Extracting Techniques ===")
    extract_techniques(soup, output_dir)
    
    print("\n=== Extracting Common Weapons ===")
    extract_common_weapons(soup, output_dir)
    
    print("\n=== Extracting Rare Weapons ===")
    extract_rare_weapons(soup, output_dir)
    
    print("\n=== Extracting Frames ===")
    extract_frames(soup, output_dir)
    
    print("\n=== Verifying Other Sections ===")
    verify_other_sections(soup, output_dir)
    
    print("\nExtraction complete!")


if __name__ == "__main__":
    main()

