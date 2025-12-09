#!/usr/bin/env python3
"""Test data-attributes parsing."""

import json
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
    
    first_cell_text = cells[0].get_text() if cells else ""
    if "Diska of Braveman" in first_cell_text:
        print("Testing data-attributes parsing:")
        for i, cell in enumerate(cells[1:4], 1):
            data_attrs = cell.get("data-attributes")
            price = cell.get_text().strip()
            print(f"\nCell {i}: price='{price}'")
            if data_attrs:
                print(f"  data-attributes: {data_attrs[:100]}...")
                try:
                    attrs = json.loads(data_attrs)
                    print(f"  Parsed successfully!")
                    if "hit" in attrs:
                        hit_data = attrs["hit"]
                        print(f"  hit: {hit_data} (type: {type(hit_data)})")
                        if isinstance(hit_data, list):
                            print(f"  -> Will set hit values: {hit_data} to price '{price}'")
                        elif isinstance(hit_data, (int, float)):
                            print(f"  -> Will set hit value: {int(hit_data)} to price '{price}'")
                except Exception as e:
                    print(f"  ERROR parsing JSON: {e}")
        break

