"""
One-time helper: build price_guide/data/coren_pools.json with star rarities from Ephinea wiki.

Run from repo root:
  python scripts/generate_coren_pools.py

Requires network. Regenerate only if Coren pools change.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "price_guide" / "data" / "coren_pools.json"

API = "https://wiki.pioneer2.net/api.php"

# Prize pools: UTC weekday order Sunday..Saturday (matches Ephinea wiki "Prize lists" section).
# Tier keys: tier1 = 1k bet pool, tier2 = 10k, tier3 = 100k.
POOLS: dict[str, dict[str, list[str]]] = {
    "Sunday": {
        "tier1": [
            "God/Power",
            "Cure/Poison",
            "Cure/Paralysis",
            "Cure/Slow",
            "Cure/Confuse",
            "Cure/Freeze",
            "Cure/Shock",
            "Tablet",
        ],
        "tier2": [
            "Kaladbolg",
            "Durandal",
            "Blade Dance",
            "M&A60 Vise",
            "H&S25 Justice",
            "L&K14 Combat",
            "Club of Laconium",
            "Photon Claw",
            "Silence Claw",
            "Stag Cutlery",
            "Holy Ray",
            "Ancient Saber",
            "Elysion",
            "Twin Psychogun",
            "Guilty Light",
            "Red Scorpio",
            "DB's Saber",
            "DF Field",
            "Morning Prayer",
            "S-Parts ver1.16",
            "Standstill Shield",
            "Kasami Bracer",
            "Secure Feet",
            "AddSlot",
            "Photon Crystal",
            "Dragon Scale",
            "Rappy's Beak",
        ],
        "tier3": [
            "Zero Divide",
            "Asteron Belt",
            "Raikiri",
            "Skyly Card",
            "Purplenum Card",
            "Oran Card",
            "Guren",
            "Black Odoshi Red Nimaidou",
            "V101",
        ],
    },
    "Monday": {
        "tier1": [
            "Three Seals",
            "God/Mind",
            "God/Arm",
            "Hero/Ability",
            "HP/Revival",
            "PB/Create",
            "Devil/Battle",
            "Cure/Slow",
        ],
        "tier2": [
            "Kaladbolg",
            "Flowen's Sword",
            "Last Survivor",
            "Dragon Slayer",
            "Rianov 303SNR",
            "H&S25 Justice",
            "L&K14 Combat",
            "Crush Bullet",
            "Meteor Smash",
            "Final Impact",
            "Club of Zumiuran",
            "Brave Hammer",
            "Alive Aqhu",
            "Ice Staff: Dagon",
            "Double Saber",
            "Elysion",
            "Red Saber",
            "Meteor Cudgel",
            "Red Sword",
            "Panzer Faust",
            "Plantain Leaf",
            "Fatsia",
            "Sange",
            "Kamui",
            "Talis",
            "DB's Saber",
            "Guardianna",
            "Regenerate Gear",
            "DB's Shield",
            "AddSlot",
            "Photon Crystal",
            "Dragon Scale",
            "Rappy's Beak",
        ],
        "tier3": [
            "Earth Wand: Brownie",
            "Viridia Card",
            "Greenill Card",
            "Yellowboze Card",
            "Yunchang",
            "Black Odoshi Domaru",
            "Revival Cuirass",
            "Gratia",
            "Regenerate Gear B.P.",
            "Honeycomb Reflector",
            "V501",
            "Heavenly/Battle",
        ],
    },
    "Tuesday": {
        "tier1": [
            "God/HP",
            "God/Body",
            "PB/Create",
            "Cure/Poison",
            "Cure/Paralysis",
            "Cure/Freeze",
        ],
        "tier2": [
            "Blade Dance",
            "Bloody Art",
            "Cross Scar",
            "Brionac",
            "Diska of Braveman",
            "M&A60 Vise",
            "Club of Laconium",
            "Mace of Adaman",
            "Twin Brand",
            "Brave Knuckle",
            "Angry Fist",
            "God Hand",
            "Red Dagger",
            "Maser Beam",
            "Asuka",
            "Talis",
            "DB's Saber",
            "Red Coat",
            "Secret Gear",
            "Regenerate Gear",
            "Black Ring",
            "AddSlot",
            "Photon Crystal",
            "Dragon Scale",
            "Rappy's Beak",
        ],
        "tier3": [
            "Zero Divide",
            "Asteron Belt",
            "Phoenix Claw",
            "Skyly Card",
            "Pinkal Card",
            "Whitill Card",
            "Morning Glory",
            "Ignition Cloak",
            "Bunny Ears",
            "Cat Ears",
            "V502",
            "Smartlink",
        ],
    },
    "Wednesday": {
        "tier1": [
            "God/Legs",
            "Hero/Ability",
            "TP/Revival",
            "Devil/Battle",
            "Cure/Slow",
            "Tablet",
        ],
        "tier2": [
            "Bloody Art",
            "Brionac",
            "Vjaya",
            "Rianov 303SNR",
            "Battle Verge",
            "Brave Hammer",
            "Alive Aqhu",
            "Soul Banish",
            "Red Partisan",
            "Yasminkov 2000H",
            "Yasminkov 7000V",
            "Maser Beam",
            "Musashi",
            "Yamato",
            "Zanba",
            "Ruby Bullet",
            "Sacred Guard",
            "S-Parts ver1.16",
            "S-Parts ver2.01",
            "Light Relief",
            "Attribute Wall",
            "AddSlot",
            "Photon Crystal",
            "Dragon Scale",
            "Rappy's Beak",
        ],
        "tier3": [
            "Phoenix Claw",
            "Bluefull Card",
            "Purplenum Card",
            "Pinkal Card",
            "Morning Glory",
            "Cannon Rouge",
            "Clio",
            "Morning Prayer",
            "Sacred Guard",
            "Honeycomb Reflector",
            "Heavenly/Legs",
        ],
    },
    "Thursday": {
        "tier1": [
            "God/TP",
            "Hero/Ability",
            "HP/Revival",
            "God/Technique",
            "Cure/Shock",
        ],
        "tier2": [
            "Gae Bolg",
            "Slicer of Assassin",
            "Diska of Liberator",
            "Diska of Braveman",
            "Varista",
            "M&A60 Vise",
            "Mace of Adaman",
            "Battle Verge",
            "Fire Scepter: Agni",
            "Ice Staff: Dagon",
            "Storm Wand: Indra",
            "Twin Brand",
            "Spread Needle",
            "Holy Ray",
            "Inferno Bazooka",
            "Victor Axe",
            "Flight Cutter",
            "Red Slicer",
            "Branch of Pakupaku",
            "Heart of Poumn",
            "Photon Launcher",
            "Guilty Light",
            "Talis",
            "Demolition Comet",
            "Ruby Bullet",
            "Guard Wave",
            "DF Field",
            "Luminous Field",
            "Morning Prayer",
            "Red Coat",
            "Infantry Mantle",
            "Regenerate Gear",
            "AddSlot",
            "Photon Crystal",
            "Dragon Scale",
            "Rappy's Beak",
        ],
        "tier3": [
            "Asteron Belt",
            "Earth Wand: Brownie",
            "Phoenix Claw",
            "Raikiri",
            "Greenill Card",
            "Redria Card",
            "Whitill Card",
            "Flamberge",
            "Cannon Rouge",
            "Glide Divine",
            "Star Cuirass",
            "Stink Shield",
        ],
    },
    "Friday": {
        "tier1": [
            "God/Luck",
            "TP/Revival",
            "PB/Create",
            "Devil/Battle",
            "Cure/Paralysis",
            "Cure/Slow",
            "Cure/Shock",
            "Tablet",
        ],
        "tier2": [
            "Varista",
            "Custom Ray ver.OO",
            "Bravace",
            "Visk-235W",
            "Rianov 303SNR",
            "M&A60 Vise",
            "H&S25 Justice",
            "Crush Bullet",
            "Club of Laconium",
            "Fire Scepter: Agni",
            "Victor Axe",
            "Caduceus",
            "Sting Tip",
            "Ancient Saber",
            "Red Saber",
            "Red Handgun",
            "Twin Psychogun",
            "Fatsia",
            "The Sigh of a God",
            "Guilty Light",
            "Talis",
            "Mahu",
            "Graviton Plate",
            "Attribute Plate",
            "Aura Field",
            "Electro Frame",
            "Sacred Cloth",
            "Smoking Plate",
            "Red Coat",
            "AddSlot",
            "Photon Crystal",
            "Dragon Scale",
            "Rappy's Beak",
        ],
        "tier3": [
            "Zero Divide",
            "Phoenix Claw",
            "Raikiri",
            "Power Maser",
            "Viridia Card",
            "Yellowboze Card",
            "Ophelie Seize",
            "Black Odoshi Domaru",
            "Black Odoshi Red Nimaidou",
        ],
    },
    "Saturday": {
        "tier1": [
            "Three Seals",
            "Hero/Ability",
            "God/Ability",
            "HP/Revival",
            "PB/Create",
            "Cure/Poison",
            "Cure/Paralysis",
            "Cure/Freeze",
        ],
        "tier2": [
            "Kaladbolg",
            "Varista",
            "Visk-235W",
            "Wals-MK2",
            "Justy-23ST",
            "Rianov 303SNR",
            "Club of Zumiuran",
            "Storm Wand: Indra",
            "Double Saber",
            "Caduceus",
            "Sting Tip",
            "Suppressed Gun",
            "Ancient Saber",
            "Twin Psychogun",
            "Red Mechgun",
            "Windmill",
            "Plantain Leaf",
            "Fatsia",
            "Revival Garment",
            "Spirit Garment",
            "Stink Frame",
            "D-Parts ver1.01",
            "D-Parts ver2.10",
            "Sense Plate",
            "Graviton Plate",
            "Custom Frame ver.OO",
            "AddSlot",
            "Photon Crystal",
            "Dragon Scale",
            "Rappy's Beak",
        ],
        "tier3": [
            "Earth Wand: Brownie",
            "Bluefull Card",
            "Redria Card",
            "Oran Card",
            "Kusanagi",
            "Honeycomb Reflector",
        ],
    },
}


def wiki_title(name: str) -> str:
    return name.replace(" ", "_")


def fetch_wikitext(title: str) -> str:
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
            "format": "json",
        }
    )
    url = f"{API}?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "PSOQuestOptimizer-coren-generator/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    if "missing" in page:
        raise RuntimeError(f"Missing wiki page: {title}")
    rev = page["revisions"][0]
    return rev["slots"]["main"]["*"]


# Wiki: items with no star rarity use 5★ for Coren weight (13-5=8). See Coren article.
STARS_OVERRIDE: dict[str, int] = {
    "Tablet": 5,
}


def parse_stars(wikitext: str) -> int | None:
    # {{Item | stars = 9 ...}} or |stars=9
    m = re.search(r"\|\s*stars\s*=\s*(\d+)", wikitext, re.I)
    if m:
        return int(m.group(1))
    # Some pages use {{Unit ... | stars = 11}}
    m = re.search(r"\{\{Unit[\s\S]*?\|\s*stars\s*=\s*(\d+)", wikitext, re.I)
    if m:
        return int(m.group(1))
    # {{Tool ... — Tablet uses Tool?
    m = re.search(r"\{\{Tool[\s\S]*?\|\s*stars\s*=\s*(\d+)", wikitext, re.I)
    if m:
        return int(m.group(1))
    return None


def main() -> None:
    unique: set[str] = set()
    for day in POOLS.values():
        for tier in day.values():
            unique.update(tier)

    title_to_stars: dict[str, int] = {}
    errors: list[str] = []

    for name in sorted(unique):
        if name in STARS_OVERRIDE:
            title_to_stars[name] = STARS_OVERRIDE[name]
            continue
        wt = wiki_title(name)
        try:
            text = fetch_wikitext(wt)
            stars = parse_stars(text)
            if stars is None:
                # Ephinea Coren: items with no listed rarity use 5★ (weight 8). See Coren wiki.
                stars = 5
                errors.append(f"Defaulted stars=5 (no |stars= in wikitext): {name}")
            title_to_stars[name] = stars
        except Exception as e:  # noqa: BLE001
            title_to_stars[name] = 5
            errors.append(f"Fetch failed, defaulted stars=5 for {name}: {e}")
        time.sleep(0.15)

    out: dict = {
        "schema_version": 1,
        "source": "https://wiki.pioneer2.net/w/Coren",
        "weekdays": {},
    }
    for day, tiers in POOLS.items():
        out["weekdays"][day] = {}
        for tier_key, names in tiers.items():
            out["weekdays"][day][tier_key] = [{"name": n, "stars": title_to_stars[n]} for n in names]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    err_path = REPO_ROOT / "scripts" / "generate_coren_pools_errors.txt"
    if errors:
        err_path.write_text("\n".join(errors), encoding="utf-8")
        print(f"Wrote {OUT_PATH} with gaps; see {err_path}")
    else:
        if err_path.exists():
            err_path.unlink()
        print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
