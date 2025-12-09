# Ephinea PSO Quest Optimizer 

This repository defines a system to calculate the most optimal PSO quests quests for PD value farming by parsing drop tables, cross-referencing with quest enemy counts, applying boosts (rbr, weekly), and calculating expected PD value per quest.

This particular implementation is tailored for the Ephinea PSO server, but could be made modular for other servers, given core logic for calculating drop rates and weapon attributes.

The purpose of this project is to provide some guidance on how to be efficient with your time. At the end of the day, these are merely suggestions based on ever-changing price guide data, so you should always use your own judgement to best suit your own playstyle.

## Components

### 1. Drop Table Parser (`drop_table_parser.py`)

Parses the HTML drop table from `drop_table_example_ultimate.html` and extracts:
- Enemy drop data organized by episode and Section ID
- DAR (Drop Anything Rate) and RDR (Rare Drop Rate) for each enemy
- Item names and drop rates
- Box drop data (organized by area)

**Usage:**
```bash
python drop_table_parser.py
```

This generates `drop_tables_ultimate.json` with the parsed drop data.

### 2. Quest Calculator (`quest_calculator.py`)

Calculates expected PD value for quests by:
- Cross-referencing quest enemy counts with drop tables
- Applying RBR (+25% DAR, +25% RDR) and weekly boost (+50% to one rate) multipliers
- Looking up item values from the price guide
- Calculating total expected PD value per quest

**Usage:**
```python
from quest_calculator import QuestCalculator, load_quest
from pathlib import Path

calculator = QuestCalculator(
    drop_table_path=Path("drop_tables_ultimate.json"),
    price_guide_path=Path("../PSOGreedles/resources/data/price_guide")
)

quest_data = load_quest(Path("quests/example_quest.json"))
result = calculator.calculate_quest_value(
    quest_data,
    section_id="Redria",
    rbr_active=True,
    weekly_boost="RDR"
)

print(f"Total Expected PD: {result['total_pd']:.4f}")
```

### 3. Quest Optimizer (`quest_optimizer.py`)

Ranks quests by PD efficiency (PD per minute) with filtering options:
- Filter by episode
- Filter by Section ID
- Filter by active weekly boost type
- Filter by RBR status

**Usage:**
```python
from quest_optimizer import QuestOptimizer
from pathlib import Path

optimizer = QuestOptimizer(calculator)

rankings = optimizer.rank_quests(
    quest_paths=[Path("quests/quest1.json"), Path("quests/quest2.json")],
    section_id="Redria",
    rbr_active=True,
    weekly_boost="RDR",
    quest_times={"quest1": 15.0, "quest2": 10.0},  # minutes
    episode_filter=None  # or 1, 2, or 4
)

optimizer.print_rankings(rankings, top_n=10)
```

## Quest Data Format

Quest JSON files should be placed in the `quests/` directory with the following format:

```json
{
  "quest_name": "Phantasmal World 1",
  "episode": 1,
  "enemies": {
    "Bartle": 14,
    "Barble": 23,
    "Tollaw": 36,
    "Gulgus": 10,
    "Gulgus-Gue": 5,
    "Monest": 2
  }
}
```

## Quest Times

Optional quest time estimates can be provided in `quest_times.json`:

```json
{
  "Phantasmal World 1": 15.0,
  "Another Quest": 10.0
}
```

Times are in minutes and are used to calculate PD per minute rankings.

## Dependencies

- beautifulsoup4 (for HTML parsing)
- lxml (for HTML parsing)
- Existing PriceGuideFixed from PSOGreedles

Install dependencies:
```bash
pip install -r requirements.txt
```

## Notes

- The drop table HTML file must be saved before parsing
- Enemy name matching handles variants (e.g., "Bartle" matches "Booma/Bartle")
- Box drops are parsed but not yet integrated into quest calculations
- Item prices are looked up from the price guide; items not found in the price guide have 0 value

## Workflow

1. Save the `drop_table_example_ultimate.html` file
2. Run `drop_table_parser.py` to generate `drop_tables_ultimate.json`
3. Create quest JSON files in the `quests/` directory
4. (Optional) Create `quest_times.json` with time estimates
5. Use `quest_calculator.py` or `quest_optimizer.py` to calculate and rank quests

## References:

In addition to the following reference, the Ephinea 
| Reference | Description |
| --------- | ----------- |
| [Price Guide](https://wiki.pioneer2.net/w/Price_guide) | The basis of the price guide used in this repository |
| [Drop Tables](https://ephinea.pioneer2.net/drop-charts/ultimate/) | Listing of drop tables  |
| [RBR Spreadsheet](https://docs.google.com/spreadsheets/d/1sEiKgmFA1aC4XXfZ23lz3VBodYZEhF39XxOSKgULiWg/edit?gid=0#gid=0) | Excellent spreadsheet containing macros to calculate drop chances given quests and boosts|
