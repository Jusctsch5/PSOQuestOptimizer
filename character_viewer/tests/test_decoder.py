"""Tests for character_viewer binary parsing.

Uses the public PSOBBCharacterItemViewer demo.zip (not personal account exports).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from character_viewer.decoder import decode_character_files, decode_from_zip
from price_guide import PriceGuideFixed

FIXTURES = Path(__file__).parent / "fixtures"
DEMO_ZIP = FIXTURES / "demo.zip"
PRICE_GUIDE_DIR = Path(__file__).resolve().parents[2] / "price_guide" / "data"


@pytest.fixture
def price_guide():
    return PriceGuideFixed(str(PRICE_GUIDE_DIR))


def _entries_from_zip(zip_path: Path):
    from character_viewer.decoder import _is_character_data_path

    entries = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if not _is_character_data_path(name):
                continue
            base = Path(name).name
            entries.append({"filename": base, "binary": zf.read(name)})
    return entries


def test_demo_zip_parses_characters_and_banks(price_guide):
    assert DEMO_ZIP.exists(), "demo.zip fixture missing"
    result = decode_from_zip(DEMO_ZIP.read_bytes(), price_guide)

    assert len(result["characters"]) > 0
    assert len(result["share_banks"]) > 0

    char = result["characters"][0]
    assert char["slot"] >= 1
    assert isinstance(char["name"], str) and len(char["name"]) > 0
    assert isinstance(char["inventory"], list)
    assert isinstance(char["bank"], list)
    assert len(char["inventory"]) > 0
    assert len(char["bank"]) > 0
    assert "total_pd" in char
    assert char["total_pd"] >= 0


def test_demo_zip_preserves_filenames_and_bank_stride(price_guide):
    entries = _entries_from_zip(DEMO_ZIP)
    filenames = [e["filename"].lower() for e in entries]
    assert any(f.endswith(".psobank") for f in filenames)
    assert any(f.endswith(".psochar") for f in filenames)
    assert not any(f.startswith("._") for f in filenames)

    result = decode_character_files(entries, price_guide)
    assert len(result["characters"]) >= 1
    assert len(result["share_banks"]) >= 1

    bank = result["share_banks"][0]
    assert bank["slot"] in ("ShareBank", "ShareBank(Classic)")
    assert len(bank["bank"]) > 0
    non_meseta = [e for e in bank["bank"] if e[1].get("type") != 10]
    assert non_meseta
    assert all(len(e[0]) == 6 for e in non_meseta)


def test_character_guild_card_is_digits(price_guide):
    result = decode_from_zip(DEMO_ZIP.read_bytes(), price_guide)
    for char in result["characters"]:
        assert char["guild_card_number"].isdigit()
        assert char["level"] >= 1
        assert char["section_id"] != ""
        assert char["character_class"] != ""


def test_all_items_totals(price_guide):
    result = decode_from_zip(DEMO_ZIP.read_bytes(), price_guide)
    assert len(result["all_items"]) == 2
    for bucket in result["all_items"]:
        assert "inventory" in bucket
        assert "total_pd" in bucket
        for idx, entry in enumerate(bucket["inventory"]):
            assert entry[-1] == idx
