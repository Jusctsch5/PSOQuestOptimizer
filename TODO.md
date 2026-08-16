# DONE
- [X] Add ruff/mypy integration
- [X] Add optimize_weapon_hunting.py to help direct to most efficient quests for hunting a specific weapon
- [X] Add behavior to fit inestimable price values for weapons
- [X] Treat item not found in price guide as error, fix all omitted items in price guide
- [X] Add christmas boost behavior, doubling weekly boosts
- [X] Add tests for test_weapon_expected_value.py
- [X] Add holloween quests to quests.json
- [X] Add holloween quest boosts to quest_calculator.py
- [X] Update README with proper usage instructions, reasoning for some of the choices made w/ user-facing scripts
- [X] Add Box Drops to Drop Tables
- [X] Add "is_in_rbr_rotation" field to quests.json, make sure RBR boost is only applied to quests in rotation
- [X] Add "is_event_quest" field to quests.json, allow filtering out event quests
- [X] Correct rare enemy mappings
- [X] Add "evergreen" quests to quests.json, i.e. TE and MaxAttack quests
- [X] Add event items (presents, cookies, eggs, etc) to price guide/drop tables
- [X] Add general item value calculation for all items (barriers, frames, etc) (i.e. calulate_weapon_value.py -> item_value_calculator.py)
- [X] Add Euler drop probability calculation to optimize_item_hunting.py
- [X] Implement short-name list filtering in optimize_quests.py/UI
- [X] Add disk drops to drop tables and item value calculation for quests
- [X] Add coren gambling script
- [X] Add BPD Script
- [X] Add Lost Soul Blade to quests.json
- [X] Add daily luck boost to quest_calculator.py
- [X] finish updating quests.json with enemies in areas
- [X] Implement random spawn quests such as AO1 and AO2. These are quests that spawn a random number of enemies in a given area.


# CORE TODO
- [ ] Central Tower actually shares drops with Seabed Lower not CCA, so fix that for many quests that take place in Tower.
- [X] Manage frame/shield values: wire ArmorValueCalculator to drop_tables/armor_stat_ranges.json (uniform DFP/EVP), map rolls to price-guide tiers / clarify base vs Min Stat
- [ ] Add common weapon value calculation to weapon_value_calculator.py, price guide, and drop tables (note only certain enemies drop common weapons)
- [ ] Consider reworking slime splitting to only split for drops that are worthwhile to split for
- [ ] Investigate modeling**
- [ ] Add "Attribute" value to items. If items drop with meaningful hit (dependnent per weapon), the other attributes become more valuable (probably follow the value as per sphering).
- [ ] Implement "random Mericarol" behavior. I added them as Mericarols so that spices up HP and other drops
- [ ] Add Mag parsing to price guide (e.g. ephinea specific mag colors, mags that have been transformed into mag from cell)
- [ ] Add Dark Flow parsing to price guide
- [ ] Add Weapon Heart Transformation parsing to price guide

# UI DONE
- [X] Implement base of UI
- [X] Add usable front-end for quest-optimizer/ item-value-calculator hosted by github pages
- [X] Add browsable price guide to UI
- [X] Add browsable quest list to UI
- [X] Add browsable drop tables to UI
- [X] Add tooltips to UI
- [X] Add links to/from UI to other tools (character viewer, price guide, drop tables, etc)
- [X] Add character bank uploading to UI
  
# UI TODO
- [ ] Add Run Simulation to UI, simulate x runs of a quest and report the results

# Not Doing
- Add mats/grinders/meseta(?) to price guide/drop tables. Too infrequent to be worth the effort


# Modeling Discussion

Places where more modeling could add value:
- Run-level variance/risk: compute per-quest variance/StdDev and percentiles (or CVaR) using Bernoulli rare drops + PD drops. That lets you rank by risk-adjusted PD/hour (e.g., mean – k·std) instead of pure expectation. Could be analytic (sum of p(1–p)·value²) or Monte Carlo.
- Time uncertainty: treat quest_time as a distribution (lognormal/gamma from player samples) and propagate to PD/hour distribution; report median and 95% CI instead of a single PD/min.
- Price uncertainty/sensitivity: the price guide is a range; sample or model prices with priors (e.g., triangular from min/median/max) to get PD value bands and show which items drive volatility.
- Scenario/what-if sweeps: grid or bootstrap over RBR/weekly boosts and present tornado plots of sensitivity. This would surface which quests are most responsive to boosts (and which aren't), and which boosts are most effective.
- Portfolio/planning optimization: given a time budget and acceptable risk, choose a mix of quests that maximizes expected PD while keeping variance below a threshold; classic knapSack/mean-variance framing on the per-quest stats.
- Tail-heavy drops: explicitly report probability of “jackpot” events (e.g., ≥X PD in one run) to guide whether to chase big-game-hunting vs. steady-eddie quests.
If you want one concrete next step: add optional --simulate n to quest_optimizer.py that Monte Carlo samples drops + quest_time + price ranges, then report mean/median/95th, std, and jackpot probability per quest; sort by risk-adjusted PD/hour.


From the above, Run-level variance is probably reasonable to model. Folks are going to have different feelings on how much variance they want to tolerate.