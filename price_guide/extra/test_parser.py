#!/usr/bin/env python3
"""Test script to debug Diska of Braveman parsing."""

from bs4 import BeautifulSoup
from pathlib import Path

html_file = Path("price_guide_sample.html")
with open(html_file, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "lxml")

# Find Diska of Braveman row
for row in soup.find_all("tr"):
    cells = row.find_all("td")
    if not cells:
        continue
    
    # Check if this row contains Diska of Braveman
    first_cell_text = cells[0].get_text() if cells else ""
    if "Diska of Braveman" in first_cell_text:
        print(f"Found row with {len(cells)} cells")
        print(f"First cell: {first_cell_text.strip()}")
        
        # Check for data-attributes
        has_data_attrs = any(c.get("data-attributes") for c in cells[1:])
        print(f"Has data-attributes: {has_data_attrs}")
        
        # Show first few data cells
        for i, cell in enumerate(cells[1:6], 1):
            data_attrs = cell.get("data-attributes")
            text = cell.get_text().strip()
            print(f"  Cell {i}: text='{text}', data-attributes={bool(data_attrs)}")
            if data_attrs:
                print(f"    Data: {data_attrs[:80]}...")
        break

