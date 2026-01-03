# Ephinea PSO Quest Optimizer

This repository defines a system to calculate the most optimal PSO quests quests for PD value farming by parsing drop tables, cross-referencing with quest enemy counts, applying boosts (rbr, weekly), and calculating expected PD value per quest.

This particular implementation is tailored for the Ephinea PSO server, but could be made modular for other servers, given core logic for calculating drop rates and weapon attributes.

The purpose of this project is to provide some guidance on how to be efficient with your time. At the end of the day, these are merely suggestions based on ever-changing price guide data, so you should always use your own judgement to best suit your own playstyle.

## Usage
This repository currently includes scripts to make use of the surrounding logic to parse quests, drop tables, and price guide data.
- `optimize_quests.py` - Ranks quests by PD efficiency (PD per quest) with filtering options:
  - Filter by quest name
  - Filter by section ID
  - Specify if RBR boost is active
  - Specify what weekly boost is active

- `calculate_weapon_value.py` - Calculates the average value of a rare weapon based on drop location and pattern 5 hit probabilities. The underlying logic here is used by `optimize_quests.py` to calculate the expected value of the other items dropped.

- `optimize_weapon_hunting.py` - Finds the best quest and Section ID for hunting a specific weapon.

### Optimize Quests Example

Let's say I want to understand christmas quests, take CF4, which is a christmas quest that rewards 6 coal on completion in Ultimate. Let's say we are running CF4 during RDR week during the christmas event (double boost).

```bash
PS C:\Users\JSchumac\source\repos\PSOQuestOptimizer> python .\optimize_quests.py --quest CF4 --christmas-boost --weekly-boost RDR
Filtered to 1 quest(s) matching 'CF4'
Ranking quests by PD efficiency...
  Section ID: All (ranking across all Section IDs)
  RBR Active: False
  Weekly Boost: WeeklyBoost.RDR
  Christmas Boost: True
  Quest Filter: CF4


Rank   Quest Name                     Section ID   Episode  PD/Quest     PD/min       Enemies    Raw PD/Quest    Quest Reward  | Notable Item 1                                       Notable Item 2                                       Notable Item 3                                       Notable Item 4                                       Notable Item 5
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1      Christmas Fiasco E4 (CF4)      Pinkal       4        4.7739       N/A          587        0.8489          Coal (0.7500) | Limiter (Girtablulu: 1.8566)                         V801 (Zu: 0.6311)                                    Mother Garb (Pyro Goran: 0.1406)                     Photon Crystal (Yowie: 0.1019)                       Ophelie Seize (Merissa AA: 0.0991)
2      Christmas Fiasco E4 (CF4)      Viridia      4        4.4197       N/A          587        0.8489          Coal (0.7500) | Limiter (Girtablulu: 1.8566)                         Liberta Kit (Goran Detonator: 0.3334)                Lame d'Argent (Dorphon Eclair: 0.2299)               L&K38 Combat (Pazuzu: 0.1336)                        Photon Crystal (Yowie: 0.1019)
3      Christmas Fiasco E4 (CF4)      Oran         4        3.9641       N/A          587        0.8489          Coal (0.7500) | Syncesta (Girtablulu: 0.9888)                        V801 (Zu: 0.6311)                                    Heavenly/Battle (Dorphon: 0.1480)                    Blue Odoshi Violet Nimaidou (Dorphon Eclair: 0.1187) Photon Crystal (Yowie: 0.1019)
4      Christmas Fiasco E4 (CF4)      Yellowboze   4        3.5501       N/A          587        0.8489          Coal (0.7500) | Swordsman Lore (Girtablulu: 0.7141)                  Select Cloak (Pyro Goran: 0.4685)                    Photon Filter (Ze Boota: 0.1717)                     Black Hound Cuirass (Dorphon: 0.1316)                Heavenly/Power (Zu: 0.1240)
5      Christmas Fiasco E4 (CF4)      Greenill     4        3.5417       N/A          587        0.8489          Coal (0.7500) | V101 (Zu: 1.1269)                                    Heaven Striker (Pyro Goran: 0.2283)                  Black Hound Cuirass (Dorphon: 0.1316)                Heavenly/Power (Merissa AA: 0.1172)                  Cannon Rouge (Dorphon Eclair: 0.1090)
6      Christmas Fiasco E4 (CF4)      Skyly        4        3.2447       N/A          587        0.8489          Coal (0.7500) | Blue Odoshi Violet Nimaidou (Girtablulu: 0.4286)     Liberta Kit (Dorphon Eclair: 0.3164)                 Lame d'Argent (Goran Detonator: 0.3101)              Yata Mirror (Merissa A: 0.1896)                      Heavenly/Mind (Zu: 0.1240)
7      Christmas Fiasco E4 (CF4)      Purplenum    4        3.1110       N/A          587        0.8489          Coal (0.7500) | V801 (Pazuzu: 0.7588)                                Heavenly/Battle (Dorphon: 0.1480)                    Photon Crystal (Yowie: 0.1019)                       Ophelie Seize (Merissa AA: 0.0991)                   Tempest Cloak (Pyro Goran: 0.0937)
8      Christmas Fiasco E4 (CF4)      Bluefull     4        2.6846       N/A          587        0.8489          Coal (0.7500) | Limiter (Astark: 0.3015)                             Photon Crystal (Satellite Lizard: 0.1048)            Heavenly/HP (Dorphon: 0.0987)                        Nei's Claw (Girtablulu: 0.0980)                      Vjaya (Boota: 0.0942)
9      Christmas Fiasco E4 (CF4)      Whitill      4        2.6553       N/A          587        0.8489          Coal (0.7500) | Liberta Kit (Dorphon Eclair: 0.3164)                 Black Hound Cuirass (Dorphon: 0.1316)                Pioneer Parts (Pyro Goran: 0.1205)                   Photon Crystal (Yowie: 0.1019)                       Ophelie Seize (Pazuzu: 0.0917)
10     Christmas Fiasco E4 (CF4)      Redria       4        2.3971       N/A          587        0.8489          Coal (0.7500) | Heaven Striker (Pyro Goran: 0.2283)                  Heavenly/Battle (Dorphon: 0.1480)                    Heavenly/Mind (Zu: 0.1240)                           Photon Crystal (Satellite Lizard: 0.1048)            Cannon Rouge (Ba Boota: 0.0814)
```

This spits out a PD/Quest value for each ID, which represents the average PD value per quest for that ID, taking into account the quest reward, raw PD drops, and expected value of the other items dropped.
We can see the outstanding value that Pinkal and Viridia provide, and a good chunk of that is the Limiter drop from the Girts (1.8566 PD value per quest). We can see a breakdown per ID if we supply the `--detailed` flag.

```bash
Rank   Quest Name                     Section ID   Episode  PD/Quest     PD/min       Enemies    Raw PD/Quest    Quest Reward  | Notable Item 1                                       Notable Item 2                                       Notable Item 3                                       Notable Item 4                                       Notable Item 5
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1      Christmas Fiasco E4 (CF4)      Pinkal       4        4.7739       N/A          587        0.8489          Coal (0.7500) | Limiter (Girtablulu: 1.8566)                         V801 (Zu: 0.6311)                                    Mother Garb (Pyro Goran: 0.1406)                     Photon Crystal (Yowie: 0.1019)                       Ophelie Seize (Merissa AA: 0.0991)
  Enemy Breakdown:
  Enemy                Drop                           DAR        RDR          Rate         Count    Exp Drops    PD Value     Exp Value
  ------------------------------------------------------------------------------------------------------------------------------------------
  Boota                Black Odoshi Domaru            0.303030   0.00659051   0.00199712   11       0.02196837   1.00000000   0.02196837
  Goran                Guardianna                     0.303030   0.00476039   0.00144254   48       0.06924209   0.04594222   0.00318114
  Ze Boota             Rianov 303SNR-3                0.384615   0.00476039   0.00183092   15       0.02746381   0.00000000   0.00000000
  Pyro Goran           Mother Garb                    0.344828   0.00256366   0.00088402   53       0.04685318   3.00000000   0.14055953
  Ba Boota             Earth Wand: Brownie            0.344828   0.00476039   0.00164152   18       0.02954727   0.00000000   0.00000000
  Goran Detonator      Solferino                      0.344828   0.00952381   0.00328407   33       0.10837438   0.14284707   0.01548096
  Astark               Heavenly/Mind                  0.833333   0.00201423   0.00167853   19       0.03189204   1.00000000   0.03189204
  Merissa A            Slicer of Fanatic              0.270270   0.00402793   0.00108863   79.84375 0.08692021   0.80255145   0.06975794
  Merissa AA           Ophelie Seize                  1.000000   0.75000000   0.75000000   0.15625  0.11718750   0.84578636   0.09911559
  Dorphon              Heavenly/HP                    0.833333   0.00439496   0.00366247   26.947265625 0.09869347   1.00000000   0.09869347
  Dorphon Eclair       Clio                           1.000000   0.75000000   0.75000000   0.052734375 0.03955078   1.86440612   0.07373872
  Girtablulu           Limiter                        0.833333   0.00476039   0.00396699   18       0.07140590   26.00000000  1.85655348
  Sand Rappy           Maguwa                         1.000000   0.00256366   0.00256366   80.841796875 0.20725123   0.00000000   0.00000000
  Del Rappy            Heavenly/Body                  1.000000   0.75000000   0.75000000   0.158203125 0.11865234   0.00000000   0.00000000
  Satellite Lizard     Glide Divine                   0.303030   0.00512645   0.00155347   59       0.09165476   0.14596243   0.01337815
  Yowie                Photon Crystal                 0.454545   0.00439496   0.00199771   51       0.10188317   1.00000000   0.10188317
  Zu                   V801                           0.833333   0.00146484   0.00122070   73.85546875 0.09015560   7.00000000   0.63108921
  Pazuzu               Kunai                          1.000000   0.75000000   0.75000000   0.14453125 0.10839844   0.16361797   0.01773593
```
Where `DAR/RDR` are Drop Anything Rate and Rare Drop Rate respectively. `Rate` is the probability of an enemy dropping the item. These rates are quest-indepentent.

Moving to the quest dependent values, `Count` is the number of enemies that appear in the quest. Note that there is a rare enemy breakdown here (ex: see Merissa A and Merissa AA above).Taking `Rate/Count` into effect, `Exp Drops` is the expected number of drops from the enemy from a single quest. `PD Value` is the AVERAGE price guide value of the item (where the average is taken from the percentage of dropping with hit from the price guide.
`Exp Value` is the expected value of the item from a single quest.

### Calculate Weapon Value Example

PS C:\Users\JSchumac\source\repos\PSOQuestOptimizer> python .\calculate_weapon_value.py VJAYA
```bash
================================================================================
WEAPON VALUE CALCULATION BREAKDOWN
================================================================================
Weapon: VJAYA
Average Expected Value: 0.6375 PD

--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
PATTERN CONFIGURATION: Pattern 5 (Rare weapons always use Pattern 5 for all attributes and hit)

  Value    Probability
  -------- ---------------
  5        29.2100000%
  10       23.0900000%
  15       19.0800000%
  20       13.8900000%
  25       8.6500000%
  30       3.1000000%
  35       1.5600000%
  40       0.6700000%
  45       0.4200000%
  50       0.1600000%
  55       0.0800000%
  60       0.0300000%
  65       0.0100000%
  70       0.0100000%
  75       0.0100000%
  80       0.0100000%
  85       0.0100000%
  90       0.0100000%

--------------------------------------------------------------------------------
HIT VALUE DISTRIBUTION:
--------------------------------------------------------------------------------

Hit Probability Summary (Three Rolls):
  Hit Rolled (at least one): 14.2625000%
  No Hit: 85.7375000%
  Total: 100.0000000%

Hit Value Prices and Expected Values:
  Hit    Combined Prob        Teched Hit   Price Range          Price (avg)     Expected Value
  ------ -------------------- ------------ -------------------- --------------- ------------------
  0      85.7375000%          0            0                    0.0000          0.0000000
  5      4.1660763%           15           0                    0.0000          0.0000000
  10     3.2932113%           20           0                    0.0000          0.0000000
  15     2.7212850%           25           0                    0.0000          0.0000000
  20     1.9810613%           30           0                    0.0000          0.0000000
  25     1.2337063%           35           1                    1.0000          0.0123371
  30     0.4421375%           40           2-8                  2.0000          0.0088428
  35     0.2224950%           45           10-45                10.0000         0.0222495
  40     0.0955588%           50           50-100               50.0000         0.0477794
  45     0.0599025%           55           100-200              100.0000        0.0599025
  50     0.0228200%           60           200-450              200.0000        0.0456400
  55     0.0114100%           65           400-670              400.0000        0.0456400
  60     0.0042788%           70           900-1300             900.0000        0.0385088
  65     0.0014263%           75           1500-3500            1500.0000       0.0213938
  70     0.0014263%           80           1500-3500            1500.0000       0.0213938
  75     0.0014263%           85           1500-3500            1500.0000       0.0213938
  80     0.0014263%           90           1500-3500            1500.0000       0.0213938
  85     0.0014263%           95           9500                 9500.0000       0.1354938
  90     0.0014263%           100          9500                 9500.0000       0.1354938
  Total  100.0000000%                                                           0.6374624

  Probability Check:
    Combined probabilities (no hit + all hit values) sum to: 100.0000000%

--------------------------------------------------------------------------------
CALCULATION EQUATION:
--------------------------------------------------------------------------------
Final Value = Hit Contribution + Attribute Contribution

Where:
  Hit Contribution = sum over hit rows [price(hit) * combined_prob(hit)]
    combined_prob already includes the three-roll hit chance and Pattern 5 distribution
                    = 0.6375 PD

  Attribute Contribution (Pattern 5, >=50% prob slice already baked in)
                         = 0.0000 PD

Calculation:
  0.6375 + 0.0000 = 0.6375 PD

--------------------------------------------------------------------------------
FINAL RESULT: 0.6375 PD
================================================================================
```

(As an aside, the default price strategy is `minimum`, which is the lowest price for an item. This is the default strategy used by `optimize_quests.py` as well. The minimum frankly seems to be the most reliable selling strategy on the discord. This can be specified as an argument as well.)

This result is interesting. Despite the fact that `VJAYA` only has any real value at 35+hit, higher hit values of the weapon REALLY contribute to the overall value of the weapon, despite the rare chance you roll that level of hit.

#### Example 2: HEAVEN STRIKER
Let's look at another weapon, "HEAVEN STRIKER", slightly simplified from the above output for brevity.
```bash
--------------------------------------------------------------------------------
HIT VALUE DISTRIBUTION:
--------------------------------------------------------------------------------

Hit Probability Summary (Three Rolls):
  Hit Rolled (at least one): 14.2625000%
  No Hit: 85.7375000%
  Total: 100.0000000%

Hit Value Prices and Expected Values:
  Hit    Combined Prob        Teched Hit   Price Range          Price (avg)     Expected Value
  ------ -------------------- ------------ -------------------- --------------- ------------------
  0      85.7375000%          0            2-3                  2.0000          1.7147500
  5      4.1660763%           15           5-15                 5.0000          0.2083038
  10     3.2932113%           20           20-40                20.0000         0.6586423
  15     2.7212850%           25           50-60                50.0000         1.3606425
  20     1.9810613%           30           140-250              140.0000        2.7734858
  25     1.2337063%           35           500-650              500.0000        6.1685313
  30     0.4421375%           40           1600-1800            1600.0000       7.0742000
  35     0.2224950%           45           2700-3200            2700.0000       6.0073650
  40     0.0955588%           50           4700                 4700.0000       4.4912613
  45     0.0599025%           55           6000                 6000.0000       3.5941500
  50     0.0228200%           60           7500                 7500.0000       1.7115000
  55     0.0114100%           65           9500                 9500.0000       1.0839500
  60     0.0042788%           70           12000                12000.0000      0.5134500
  65     0.0014263%           75           15000                15000.0000      0.2139375
  70     0.0014263%           80           18500                18500.0000      0.2638563
  75     0.0014263%           85           22500                22500.0000      0.3209063
  80     0.0014263%           90           27000                27000.0000      0.3850875
  85     0.0014263%           95           32000                32000.0000      0.4564000
  90     0.0014263%           100          37500                37500.0000      0.5348438
  Total  100.0000000%                                                           39.5352631
```

Wow, so the average expected value of a HEAVEN STRIKER is 39.5 PD. That's incredible!
However, if you are strictly looking at PD/quest value, somewhat surprisingly, these weapons are often lesser contributers to a quest's value than items that have a more reliable price.


### Optimize Item Hunting Example

This is a simple script to allow people to approach hunting from the 'use-case' perspective of "hey, I want this item, what's the best way to get it?"
Let's look at hunting the "M&A60 Vise" weapon.

```bash
PS C:\Users\JSchumac\source\repos\PSOQuestOptimizer> python .\optimize_item_hunting.py "M&A60 Vise"
Loading quest and drop table data...
Loaded 76 quests.

Searching for 'M&A60 Vise' across all quests and Section IDs...
  Christmas Boost: False


================================================================================
Enemies that drop: M&A60 Vise
================================================================================

1. Ze Boota (Episode 4)
   Section ID: Purplenum
   DAR: 0.3846, RDR: 0.015625
   Drop Rate: 0.600962% per kill
   (1 in 166.4 kills)

2. Canadine (Episode 1)
   Section ID: Purplenum
   DAR: 0.3448, RDR: 0.015625
   Drop Rate: 0.538793% per kill
   (1 in 185.6 kills)

3. Merissa A (Episode 4)
   Section ID: Purplenum
   DAR: 0.2703, RDR: 0.017575
   Drop Rate: 0.474992% per kill
   (1 in 210.5 kills)

4. Evil Shark (Episode 1)
   Section ID: Purplenum
   DAR: 0.3030, RDR: 0.015625
   Drop Rate: 0.473485% per kill
   (1 in 211.2 kills)

5. Ul Gibbon (Episode 2)
   Section ID: Purplenum
   DAR: 0.3030, RDR: 0.015625
   Drop Rate: 0.473485% per kill
   (1 in 211.2 kills)


No boxes found that drop 'M&A60 Vise'.

================================================================================
Best quests for hunting: M&A60 Vise
================================================================================

1. Quest: SA2 (Silent Afterimage 2)
   Section ID: Purplenum
   Drop Probability: 76.916797% per quest run
   (1 in 1.3 quest runs)
   Contributions:
     - Vulmer: 68 kills
       DAR: 0.3030, RDR: 0.015625
       Contribution: 32.196970%
     - Canabin: 83 kills
       DAR: 0.3448, RDR: 0.015625
       Contribution: 44.719828%

2. Quest: SR3 (Scarlet Realm 3)
   Section ID: Purplenum
   Drop Probability: 76.508621% per quest run
   (1 in 1.3 quest runs)
   Contributions:
     - Canabin: 142 kills
       DAR: 0.3448, RDR: 0.015625
       Contribution: 76.508621%

3. Quest: EN2 (Endless Nightmare 2)
   Section ID: Purplenum
   Drop Probability: 71.969697% per quest run
   (1 in 1.4 quest runs)
   Contributions:
     - Vulmer: 152 kills
       DAR: 0.3030, RDR: 0.015625
       Contribution: 71.969697%

4. Quest: CF1 (Christmas Fiasco E1)
   Section ID: Purplenum
   Drop Probability: 68.214472% per quest run
   (1 in 1.5 quest runs)
   Contributions:
     - Evil Shark: 28 kills
       DAR: 0.3030, RDR: 0.015625
       Contribution: 13.257576%
     - Canadine: 102 kills
       DAR: 0.3448, RDR: 0.015625
       Contribution: 54.956897%

5. Quest: LIS (Lost ICE SPINNER)
   Section ID: Purplenum
   Drop Probability: 61.079545% per quest run
   (1 in 1.6 quest runs)
   Contributions:
     - Vulmer: 129 kills
       DAR: 0.3030, RDR: 0.015625
       Contribution: 61.079545%

6. Quest: SR2 (Scarlet Realm 2)
   Section ID: Purplenum
   Drop Probability: 60.606061% per quest run
   (1 in 1.6 quest runs)
   Contributions:
     - Vulmer: 128 kills
       DAR: 0.3030, RDR: 0.015625
       Contribution: 60.606061%

7. Quest: CF4 (Christmas Fiasco E4)
   Section ID: Purplenum
   Drop Probability: 46.939541% per quest run
   (1 in 2.1 quest runs)
   Contributions:
     - Ze Boota: 15 kills
       DAR: 0.3846, RDR: 0.015625
       Contribution: 9.014423%
     - Merissa A: 79.84375 kills
       DAR: 0.2703, RDR: 0.017575
       Contribution: 37.925118%

8. Quest: EN3 (Endless Nightmare 3)
   Section ID: Purplenum
   Drop Probability: 45.258621% per quest run
   (1 in 2.2 quest runs)
   Contributions:
     - Canabin: 84 kills
       DAR: 0.3448, RDR: 0.015625
       Contribution: 45.258621%

9. Quest: WOL2 (War of Limits #2)
   Section ID: Purplenum
   Drop Probability: 44.471154% per quest run
   (1 in 2.2 quest runs)
   Contributions:
     - Ze Boota: 74 kills
       DAR: 0.3846, RDR: 0.015625
       Contribution: 44.471154%

10. Quest: SU3 (Sweep Up Operation 3)
   Section ID: Purplenum
   Drop Probability: 42.564655% per quest run
   (1 in 2.3 quest runs)
   Contributions:
     - Canabin: 79 kills
       DAR: 0.3448, RDR: 0.015625
       Contribution: 42.564655%

... and 32 more results.

================================================================================
BEST OPTION:
  Quest: SA2 (Silent Afterimage 2)
  Section ID: Purplenum
  Drop Chance: 76.916797% per quest run
  Expected runs: 1.3
================================================================================``
```


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

### Web Interface
A static web interface (html, w/ css for styling, js for interactivity) for the PSO Quest Optimizer, running entirely in the browser using Pyodide. The goal here is to minimize this logic as much as possible, so the scriptage can be first-class as well.

Caching - The web interface uses a caching mechanism to improve performance, and put less strain on github. This is done using IndexedDB, and is automatically managed by the deployment workflow. The cache lasts for 7 days, or until the version changes by some meaningful update. The cache can be manually cleared via browser DevTools if needed.

## Coding Stuff
- uses python 3.x
- uses ruff for linting and formatting (recommend the ruff extension for vscode, uses the pyproject.toml file for configuration+)
- mypy for type checking
- uses pytest for testing+

### Formatting
All code should be formatted using ruff. The ruff extension for vscode is recommended, ruff can also be installed independently using `pip install ruff` and run via `ruff format` and `ruff check` to lint the code.

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
