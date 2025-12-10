# Ephinea PSO Quest Optimizer

This repository defines a system to calculate the most optimal PSO quests quests for PD value farming by parsing drop tables, cross-referencing with quest enemy counts, applying boosts (rbr, weekly), and calculating expected PD value per quest.

This particular implementation is tailored for the Ephinea PSO server, but could be made modular for other servers, given core logic for calculating drop rates and weapon attributes.

The purpose of this project is to provide some guidance on how to be efficient with your time. At the end of the day, these are merely suggestions based on ever-changing price guide data, so you should always use your own judgement to best suit your own playstyle.

## Usage
This repository currently includes scripts to make use of the surrounding logic to parse quests, drop tables, and price guide data.
- `calculate_weapon_value.py` - Calculates the average value of a weapon based on drop location and pattern 5 hit probabilities.
- `optimize_quests.py` - Ranks quests by PD efficiency (PD per quest) with filtering options:
  - Filter by quest name
  - Filter by section ID


## Components
The following components are used for these scripts. These components take the form of python libraries, which are self-contained and can be used independently of the main scripts.

### Drop Tables
Python library containing enemy and box drop tables. These tables were parsed from the drop tables seen in the #references section below. Additionally, the logic around weapon attribute patterns have been lifted from the wiki's documentation

### Quests
Python library acting as a wrapper containing quest listings. These listings were parsed from the quest found in the ephinea wiki, as well as the RBR spreadsheet seen in the #references section below.

### Price Guide
Python library containing the price guide data. This data was parsed from the price guide seen in the #references section below. There have been a handful of modifications to the price guide data to make it more compatible with the rest of the project.
These modifications are summarized as the following:
- filling out "Indescribable" PD values for high-hit weapons, based on linear interpolation of known values
- Adjusting unsensible PD values for trash rares (e.g. Braniac going from .5PD to 0PD)
- Making sensible value adjustments for items with shifting market values (e.g. Limiters/Adepts/Cookies)
- Desensitizing the price guide to high hit rares as purely "collector's items"

As an aside, these adjustments are required for the project to function properly. Without adjusting common trash rares down to 0PD, the expected value of a quest would be artificially inflated, soley based on the value of that trash rare. Additionally, while an abnormally high PD value for an incredibly rare item is unlikely, frankly it has a pronounced effect on the average value of the rare.

### Quest Optimizer
Provides the connective tissue between the other libraries.

## Coding Stuff
- uses python 3.x
- uses ruff for linting and formatting (recommend the ruff extension for vscode, uses the pyproject.toml file for configuration+)
- mypy for type checking
- uses pytest for testing+

### Running unit tests
All of the tests use relative path strategies to find test files, so running the tests from the root directory is recommended.
```bash
python -m pytest ./
```

## References:

In addition to the following reference, the Ephinea
| Reference                                                                                                               | Description                                                                               |
| ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [Price Guide](https://wiki.pioneer2.net/w/Price_guide)                                                                  | The basis of the price guide used in this repository                                      |
| [Drop Tables](https://ephinea.pioneer2.net/drop-charts/ultimate/)                                                       | Listing of drop tables                                                                    |
| [RBR Spreadsheet](https://docs.google.com/spreadsheets/d/1sEiKgmFA1aC4XXfZ23lz3VBodYZEhF39XxOSKgULiWg/edit?gid=0#gid=0) | Excellent spreadsheet containing macros to calculate drop chances given quests and boosts |


## Thanks
This project would be impossible without the server administrators at Ephinea PSO, dedicated data-miners and statisticians who have parsed various equations and formulas used in the game, as well as the community at large who put together the wiki and price guide.
