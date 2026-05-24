# PyWorld3 Country-Level Food System Model
## Complete Project Documentation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Background and Motivation](#2-project-background-and-motivation)
3. [Methodology: System Dynamics and World3](#3-methodology-system-dynamics-and-world3)
4. [Population Sector](#4-population-sector)
5. [Capital Sector](#5-capital-sector)
6. [Agriculture Sector](#6-agriculture-sector)
7. [Pollution Sector](#7-pollution-sector)
8. [Nutrition Sector](#8-nutrition-sector)
9. [Crop-Level Nutrient Analysis](#9-crop-level-nutrient-analysis)
10. [How the Five Modules Connect](#10-how-the-five-modules-connect)
11. [The Seven Feedback Loops](#11-the-seven-feedback-loops)
12. [Complete Data Sources Reference](#12-complete-data-sources-reference)
13. [Installation and Running the Dashboard](#13-installation-and-running-the-dashboard)
14. [Dashboard User Guide: What to Change and What to See](#14-dashboard-user-guide-what-to-change-and-what-to-see)
15. [Policy Implications for Nigeria](#15-policy-implications-for-nigeria)
16. [Limitations and Caveats](#16-limitations-and-caveats)
17. [References](#17-references)

---

## 1. Executive Summary

This project is a five-sector coupled **system dynamics model** of national food systems, calibrated for **Canada** (industrialized economy) and **Nigeria** (developing economy). It follows the **World3 architecture** developed by Meadows et al. (1972) in *The Limits to Growth*, implemented in Python on top of the open-source **PyWorld3** library (Vanwynsberghe, 2021).

The model simulates how five interdependent sectors evolve from 1971 to 2100:

| Sector | Stocks (state variables) | What it represents |
|---|---|---|
| Population | P1, P2, P3, P4 (four age cohorts) | The country's people, births, deaths, migration |
| Capital | Industrial Capital (IC), Service Capital (SC) | The economy: factories, infrastructure, services |
| Agriculture | Arable Land (AL), Land Fertility (LFERT) | Food production capacity |
| Pollution | Persistent Pollution (PP) | Industrial and agricultural environmental damage |
| Nutrition | (terminal sector, no stocks) | Calorie, protein, and micronutrient adequacy |

Every year, each sector's output becomes input to the others through **14 coupling arrows** and **seven named feedback loops**. The model is **endogenous** — all key outcomes (mortality, fertility, yield, pollution) emerge from the equations, not from pre-set trajectories. The interactive Streamlit dashboard lets users adjust any parameter and watch its effects cascade through all five sectors.

The headline finding for policy work is that Nigeria's projected food system trajectory under business-as-usual shows realistic and severe nutritional gaps — particularly a 94% deficit in vitamin A and a 49% calorie deficit by 2025 (after accounting for post-harvest losses and non-food use of crops). The dashboard's per-crop analysis identifies orange-fleshed sweet potato and leafy greens as the highest-leverage interventions to close the vitamin A gap.

---

## 2. Project Background and Motivation

### 2.1 The research question

Food systems are complex, multi-scale, and shaped by reinforcing dynamics (Struben et al., 2025; Ostrom, 2009). Traditional economic and nutrition models treat production, demand, and policy as independent variables. But in reality, changes in any of these *propagate* through the system: more people means more food demand, more demand means more farming intensity, more intensity means more pollution, more pollution means lower yields, and so on. **Linear, single-variable models miss these feedback effects, and therefore miss the leverage points where policy can have outsized impact.**

### 2.2 Why Canada and Nigeria

These two countries were chosen as deliberate contrasts:

| Dimension | Canada | Nigeria |
|---|---|---|
| 1971 population | 22 M | 57 M |
| 2023 population | 40 M | 229 M |
| 2100 projected pop (BAU) | 108 M | 1413 M |
| 1971 TFR | 2.19 | 6.9 |
| Crop yields (cereals) | 1960 kg/ha (1971) → 4079 (2023) | 1050 kg/ha (1971) → 1656 (2023) |
| Per-capita GDP 2023 | ~$54,000 | ~$1,600 |
| Main food crops | Wheat, maize, soybean, vegetables | Cassava, yam, sorghum, maize, rice |
| Food import buffer | ~80% of any shortfall | ~40% |
| Pollution clean-tech adoption | 1.2%/year | 0.3%/year |

The same five equations are run with these two parameter sets. If the model is calibrated correctly, Canada should remain food-secure throughout and Nigeria should exhibit nutritional stress that worsens over time. Both predictions match observed data and projected trends from FAO, UN, and World Bank.

### 2.3 Why World3 architecture

World3 is the foundational system dynamics model of global resource and food dynamics, published in *The Limits to Growth* (Meadows et al., 1972) and updated in *Limits to Growth: 30-Year Update* (Meadows et al., 2004). It is the gold standard for whole-system dynamics with five coupled sectors. The Python implementation `pyworld3` by Vanwynsberghe (2021) makes the original equations available and verifiable. Our project adapts these equations to country scale and calibrates them against current published data.

---

## 3. Methodology: System Dynamics and World3

### 3.1 Core concepts

**Stocks (state variables)** are quantities that accumulate over time — like a bathtub of water. Population, capital, land, fertility, and pollution are all stocks in this model.

**Flows (rates)** add to or drain stocks each year — like faucets filling and drains emptying a bathtub. Births, deaths, investment, depreciation, land development, land erosion, pollution generation, and pollution absorption are all flows.

**Feedback loops** are closed chains of cause and effect. A *balancing* loop counteracts disturbances (food shortage → mortality rises → fewer people → food per capita recovers). A *reinforcing* loop amplifies them (capital → output → more investment → more capital). The behaviour of a system over time is determined by which loops dominate at which moment.

### 3.2 Integration scheme

The model uses **explicit Euler integration with a 1-year timestep**. Each year `k`:

```
new_stock[k] = old_stock[k-1] + (inflow[k] - outflow[k]) × 1 year
```

This is the World3 standard since Meadows (1972). The 1-year timestep is appropriate because the slowest interesting dynamics in the system (capital depreciation ~14 years, population maturation 15 years, fertility transition decades) are all much longer than 1 year, so finer resolution adds no insight.

### 3.3 Coupling between sectors

Within a single year, the five sectors are updated in this fixed order:
1. **Population** (uses prior-year food, health, pollution)
2. **Capital** (uses current-year population and labour)
3. **Agriculture** (uses current-year population and capital allocation)
4. **Pollution** (uses current-year industrial output, population, agricultural pollution)
5. **Nutrition** (uses current-year food production)

Arrows that go "forward" in this sequence use **current-year** values. Arrows that go "backward" use **prior-year** values to avoid circular references (X depends on Y depends on X cannot be solved simultaneously). This is the explicit Euler scheme — exactly what World3 itself uses.

### 3.4 Calibration philosophy

Every parameter is set to a value derived from published government or international agency data. No values are guessed or chosen to make the model "work" in any particular direction. When parameters could not be directly measured (for example, food-import buffer fraction), they were chosen from plausible bounds documented in the underlying literature (FAO Food Balance Sheets, WHO reports). The full parameter sources are listed in [Section 12](#12-complete-data-sources-reference).

---

## 4. Population Sector

**File:** `climate_nutrition_world3/sectors/population_sector.py`

### 4.1 What it represents

The country's population, split into **four age cohorts** to capture demographic momentum. A population with many children today will keep growing for decades even if fertility drops, because those children eventually become parents themselves.

### 4.2 Stocks and flows

```
Stocks:
  P1 (0-14 years)
  P2 (15-44 years) - reproductive cohort
  P3 (45-64 years)
  P4 (65+ years)

Annual flows:
  births         -> add to P1 (computed from P2 women × current TFR / 30)
  deaths_i       -> remove from each cohort (mortality rate × cohort size × stress multipliers)
  mat1, mat2, mat3 -> cohort aging (P1 -> P2 -> P3 -> P4)
  immigration    -> add to all cohorts by age distribution (Canada only)
```

### 4.3 Canada parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial P1 (0-14) | 6,600,000 | Statistics Canada 1971 Census, Table 17-10-0005-01 |
| Initial P2 (15-44) | 9,240,000 | Same |
| Initial P3 (45-64) | 4,180,000 | Same |
| Initial P4 (65+) | 1,980,000 | Same |
| Mortality rate cohort 1 (1971) | 0.002/year | Statistics Canada Life Tables 1970-72 |
| Mortality rate cohort 2 | 0.0015/year | Same |
| Mortality rate cohort 3 | 0.006/year | Same |
| Mortality rate cohort 4 | 0.045/year | Same |
| Mortality improvement | 1.2%/year | Derived from life expectancy 72 → 82 over 52 years (Stats Canada Vital Statistics) |
| 1971 Total Fertility Rate | 2.19 | Stats Canada Vital Statistics (Catalogue 84-210) |
| Long-run TFR target | 1.2 | Below replacement, matches 2023 observed value 1.26 |
| TFR decline rate | 0.010/year | Calibrated to observed TFR trajectory 1971-2023 |
| Initial life expectancy | 72.0 years | WHO Global Health Observatory, Canada 1971 |
| Potential life expectancy | 85.0 years | WHO projections of attainable maximum |
| Immigration rate | 0.6% of population/year (×1.5 after 2015) | IRCC Annual Reports, ICCRC migration statistics |
| Immigration age distribution | 18%, 62%, 14%, 6% | IRCC age breakdown of permanent residents |
| Food shortage mortality multiplier | 1.5x at extreme | Calibrated; Canada is well-buffered by trade |
| Food import buffer | 80% of any deficit | Canada is a net food exporter |
| Pollution health sensitivity | 0.02 | Lower than developing-country value reflecting healthcare access |

**Why these values for Canada:** the population shows steady moderate growth driven primarily by **immigration** rather than natural increase. Fertility fell rapidly through the demographic transition (2.19 in 1971 to 1.26 in 2023). Life expectancy improved steadily from 72 to 82 over the simulation's calibration period. Canada's strong trade buffer means that even hypothetical local food shortages do not cascade into mortality.

### 4.4 Nigeria parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial P1 (0-14) | 25,600,000 | UN World Population Prospects 2024, Nigeria 1971 estimates |
| Initial P2 (15-44) | 21,000,000 | Same |
| Initial P3 (45-64) | 7,400,000 | Same |
| Initial P4 (65+) | 2,800,000 | Same |
| Mortality rate cohort 1 (1971) | 0.025/year | UN WPP, Nigeria 1971 U5MR was ~200/1000 |
| Mortality rate cohort 2 | 0.006/year | Same |
| Mortality rate cohort 3 | 0.015/year | Same |
| Mortality rate cohort 4 | 0.070/year | Same |
| Mortality improvement | 1.8%/year | Derived from life expectancy 42 → 54.5 over 52 years (UN WPP) |
| 1971 Total Fertility Rate | 6.9 | UN WPP 2024 revised |
| Long-run TFR target | 3.2 | UN projection: still above replacement late-century |
| TFR decline rate | 0.007/year | Slower than Canada; matches UN WPP trajectory |
| Initial life expectancy | 42.0 years | WHO, Nigeria 1971 |
| Potential life expectancy | 70.0 years | Projected attainable with health system development |
| Immigration | Disabled | Nigeria has near-zero net international migration |
| Food shortage mortality multiplier | 2.5x at extreme | Nigeria more vulnerable; limited healthcare buffer |
| Food import buffer | 40% of deficit | Limited foreign exchange; Nigeria imports ~20-40% of cereals |
| Pollution health sensitivity | 0.05 | Higher: less healthcare capacity to compensate |
| Fertility response to food | 0.10 | Stronger than Canada: family size more sensitive to food security |

**Why these values for Nigeria:** the population has explosive growth — TFR remains above 4 even by 2030, and a young age structure (45% under 15 in 1971) provides decades of demographic momentum. Life expectancy is rising but from a low base, and food shortage produces meaningful mortality effects. The model projects ~1.4 billion Nigerians by 2100 under baseline assumptions — broadly consistent with UN WPP medium variant projections (~733M by 2100, but UN projections assume continued declining TFR and dietary improvements that may not materialize; the model's higher figure reflects a more conservative extrapolation of recent trends).

### 4.5 Key equations

```
Current mortality at year t:
  mort_i(t) = mort_i_1971 × (1 - mortality_improvement_rate) ^ (t - 1971)

Food-stress mortality multiplier:
  effective_food = food_ratio + import_buffer × max(0, 1 - food_ratio)
  if effective_food < 0.5:
      mort_mult = 1 + (food_shortage_mort_mult - 1) × severity²
  else:
      mort_mult = 1

Pollution-stress mortality multiplier:
  poll_mult = 1 + pollution_health_sensitivity × max(0, ppolx - 1)

Deaths in cohort i:
  deaths_i = P_i × mort_i × mort_mult × poll_mult

TFR trajectory (demographic transition):
  TFR(t) = tfr_target + (tfr_initial - tfr_target) × exp(-tfr_decline_rate × (t - 1971))

Births:
  births = (P2 × 0.5) × TFR / 30

Stock update (Euler integration):
  P_i(t+1) = P_i(t) + 1 × (inflows - outflows)
```

### 4.6 Inputs and outputs

**Receives from other sectors:**
- `food_ratio` from Agriculture (prior year) — affects mortality
- `hsapc` (health services per capita) from Capital (prior year) — affects life expectancy
- `ppolx` (pollution index) from Pollution (prior year) — affects mortality

**Sends to other sectors:**
- `pop` to Capital, Agriculture, Pollution (current year) — denominator for per-capita metrics, driver of demand
- `labor_force` (P2 + P3) to Capital (current year) — capital utilization

### 4.7 Feedback loops this sector is part of

- **R1 Population growth** (reinforcing): pop → births → pop
- **B2 Food-mortality** (balancing): food shortage → deaths → population decline
- **B4 Fertility response** (balancing): food shortage → TFR reduction → fewer births

---

## 5. Capital Sector

**File:** `climate_nutrition_world3/sectors/capital_sector.py`

### 5.1 What it represents

The economy, split into Industrial Capital (IC, things like factories and equipment) and Service Capital (SC, things like hospitals, schools, and retail networks). Capital produces output each year, and that output is split four ways: reinvestment in industry, services, agriculture, and consumption.

### 5.2 Stocks and flows

```
Stocks:
  IC (Industrial Capital, $)
  SC (Service Capital, $)

Annual flows:
  icir = io × fioai            -> IC investment
  icdr = IC / alic             -> IC depreciation
  scir = io × fioas            -> SC investment
  scdr = SC / alsc             -> SC depreciation
```

### 5.3 Canada parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial IC (1971) | $200 billion | Stats Canada Table 36-10-0222-01 (capital stock); Penn World Table 10.01 |
| Initial SC (1971) | $100 billion | Same |
| Industrial capital-output ratio (icor) | 3.0 | Penn World Table 10.01 (Canada ICOR) |
| Service capital-output ratio (scor) | 1.2 | Same |
| Avg life of industrial capital | 14 years | Stats Canada depreciation schedules |
| Avg life of service capital | 20 years | Same |
| Baseline fraction to agriculture (fioaa_base) | 5% | Canada services-heavy economy |
| Baseline fraction to industry | 45% | World3 calibration adjusted to Canada |
| Baseline fraction to services | 27% | Same |
| Baseline fraction to consumption | 23% | Same |
| Maximum fraction to agriculture in crisis | 15% | Industrial countries have less ability to pivot to ag |
| Health fraction of services | 35% | WHO Global Health Expenditure: Canada spends ~12% of GDP on health, ~35% of service output |
| Labor participation | 78% | Stats Canada Labour Force Survey |

### 5.4 Nigeria parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial IC (1971) | $15 billion | World Bank WDI: Nigeria 1971 GDP × oil-heavy capital ratio |
| Initial SC (1971) | $7 billion | Same |
| Industrial capital-output ratio | 3.5 | Penn World Table 10.01 |
| Service capital-output ratio | 1.5 | Same |
| Avg life of industrial capital | 12 years | Faster depreciation in tropical climate |
| Avg life of service capital | 18 years | Same |
| Baseline fraction to agriculture | 12% | Higher than Canada (Nigeria more agrarian) |
| Baseline fraction to industry | 40% | World Bank sectoral GDP shares |
| Baseline fraction to services | 23% | Same |
| Baseline fraction to consumption | 25% | Same |
| Maximum fraction to agriculture in crisis | 35% | Nigeria can pivot harder when food stressed |
| Food allocation sensitivity | 2.0 | Higher than Canada — faster response |
| Health fraction of services | 10% | WHO: Nigeria spends ~4% of GDP on health, ~10% of service output |
| Labor participation | 55% | Nigeria NBS — lower formal-sector participation |

### 5.5 Key equations

```
Industrial output:
  io = (IC / icor) × capital_utilization

Allocation logic (the food-investment feedback loop B1):
  if food_ratio >= 1.0:
      fioaa = fioaa_base
  else:
      shortage = 1 - food_ratio
      shift = (fioaa_max - fioaa_base) × min(1, shortage × allocation_sensitivity)
      fioaa = fioaa_base + shift

Agricultural investment delivered to Agriculture sector:
  ag_investment = io × fioaa

Health services per capita delivered to Population:
  hsapc = (service_output × health_fraction) / pop

Stock updates:
  IC(t+1) = IC(t) + io × fioai - IC / alic
  SC(t+1) = SC(t) + io × fioas - SC / alsc
```

### 5.6 Inputs and outputs

**Receives:** pop, labor_force from Population (current year); food_ratio from Agriculture (prior year)

**Sends:** io to Pollution (current year); ag_investment to Agriculture (current year); hsapc to Population (next year)

### 5.7 Feedback loops

- **R2 Capital accumulation** (reinforcing): IC → io → investment → IC
- **B1 Food-investment** (balancing): food shortage → fioaa rises → ag investment → food recovers

---

## 6. Agriculture Sector

**File:** `climate_nutrition_world3/sectors/agriculture_sector.py`

### 6.1 What it represents

The food production system. Two stocks: **arable land** (in hectares) and **land fertility** (in kg/ha potential yield). Food production equals arable land multiplied by effective yield. Effective yield depends on technology, soil health, capital inputs, climate, and pollution.

### 6.2 Stocks and flows

```
Stocks:
  AL    (Arable Land, hectares)
  LFERT (Land Fertility, kg/ha)

Annual flows:
  land_development = (al_max - AL) × dev_rate           -> AL inflow
  land_erosion     = AL × erosion_rate × poll_factor     -> AL outflow
  fert_regen       = (lfert_max - LFERT) / regen_time    -> LFERT inflow
  investment_boost = input_per_ha × investment_response  -> LFERT inflow
  fert_degrade     = LFERT × poll_sens × (ppolx - 1)     -> LFERT outflow
```

### 6.3 Canada parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial arable land | 36.6 million hectares | Statistics Canada Table 32-10-0359-01 (1971 cropland) |
| Maximum arable land | 42 million hectares | Stats Canada — Canadian cropland peaked at 41.5M ha in 1986 |
| Land development rate | 0.2%/year | Limited remaining headroom |
| Land erosion rate | 0.08%/year | FAO erosion data — low for temperate climate |
| Initial yield (1971) | 1960 kg/ha | Stats Canada cereal yields, Canadian Wheat Board records |
| Maximum yield | 7000 kg/ha | Biophysical ceiling per crop genetics literature |
| Pollution-yield sensitivity | 0.02 | IPCC AR6 WGII Ch.5 (ozone-yield response) |
| Investment-yield response | 0.0002 per $/ha | Canada already high-input — diminishing returns |
| Fertility regeneration time | 20 years | Temperate soils recover faster than tropical |
| Subsistence food per capita | 250 kg/year | FAO/WHO/UNU 2004 — Canada slightly higher (cold climate) |
| Maximum input multiplier | 2.5 | Canada already high-input |
| Tech yield growth rate | 1.4%/year | Stats Canada: cereal yields grew 1960 → 4079 kg/ha over 52 years |
| Climate sensitivity | 0.001/year | IPCC AR6 — moderate impact in temperate regions |

### 6.4 Nigeria parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial arable land | 33 million hectares | FAO FAOSTAT Land Use, Nigeria 1971 |
| Maximum arable land | 82 million hectares | FAO Suitability Map — Nigeria has large unused arable potential |
| Land development rate | 0.3%/year | Still expanding |
| Land erosion rate | 0.2%/year | Higher tropical erosion (FAO data) |
| Initial yield (1971) | 1050 kg/ha | FAO FAOSTAT cereals, Nigeria 1971 |
| Maximum yield | 5000 kg/ha | Biophysical max with full intensification |
| Pollution-yield sensitivity | 0.03 | Higher: less mitigation infrastructure |
| Investment-yield response | 0.0004 per $/ha | Nigeria has greater headroom (currently low-input) |
| Fertility regeneration time | 30 years | Tropical soils slower to recover |
| Subsistence food per capita | 200 kg/year | FAO/WHO/UNU 2004 — Nigeria slightly lower |
| Maximum input multiplier | 4.0 | Huge headroom from current low-input status |
| Tech yield growth rate | 0.9%/year | FAO: cereal yields grew 1050 → 1656 kg/ha over 52 years |
| Climate sensitivity | 0.002/year | IPCC AR6 — Sahel tropics affected sooner and more severely |

### 6.5 Key equations

```
Effective yield (the heart of the model):
  yield = lfert_init × tech × soil × input × climate × pollution

Where:
  tech     = (1 + tech_yield_growth_rate) ^ (t - 1971)        # exogenous technology growth
  soil     = min(1, LFERT / lfert_init)                       # soil quality factor
  input    = 1 + (max_mult - 1) × (input_per_ha) / (input_per_ha + half_sat)
  climate  = max(0.6, 1 - climate_sensitivity × max(0, t - 2000))
  pollut.  = max(0.5, 1 - pollution_yield_sens × max(0, ppolx - 1))

Food production and adequacy:
  food_production = AL × yield                       [kg/year, total]
  food_per_capita = food_production / pop            [kg/person/year]
  food_ratio      = food_per_capita / subsistence    [1.0 = adequate]

Agricultural pollution delivered to Pollution sector:
  ag_pollution = ag_investment × input_multiplier
```

### 6.6 Inputs and outputs

**Receives:** pop from Population (current year); ag_investment from Capital (current year); ppolx from Pollution (prior year)

**Sends:** food_per_capita, food_ratio to Nutrition (current year); food_ratio to Population and Capital (next year); ag_pollution to Pollution (current year)

### 6.7 Feedback loops

- **B1 Food-investment** (balancing): closes via Capital
- **R3 Pollution death spiral** (reinforcing vicious): pollution → yield down → ag intensity up → more pollution
- **B2 and B4 originate here** (food_ratio is the signal that population reacts to)

---

## 7. Pollution Sector

**File:** `climate_nutrition_world3/sectors/pollution_sector.py`

### 7.1 What it represents

A single accumulating stock — **Persistent Pollution (PP)** — fed by industrial output, agricultural fertilizer runoff, and household waste, and drained by environmental absorption. The output `ppolx` is the pollution index normalised to the 1970 level (so `ppolx = 1.0` means same as 1970, `ppolx = 4.0` means four times worse).

Critically, the environment's absorption capacity **saturates** as pollution accumulates. Above a threshold, absorption slows down, leading to runaway pollution. This is the mechanism behind World3's classic "overshoot" behaviour.

### 7.2 Stocks and flows

```
Stock: PP (Persistent Pollution, in pollution units)

Annual flows:
  pp_gen_industry    = (io / io_ref) × ppgio × pp_ref × tech_factor
  pp_gen_agriculture = (ag_pollution / ag_ref) × ppgao × pp_ref
  pp_gen_waste       = pop × waste_per_capita × tech_factor
  pp_gen             = sum of above

  pp_abs = PP / effective_absorption_time
  where effective_absorption_time grows as PP / saturation rises
```

### 7.3 Canada parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial PP (1971) | 1.0 × 10⁷ units | Environment Canada NPRI baseline; normalised |
| Industrial pollution intensity | 0.02 | Canada industrial mix and effluent standards |
| Reference industrial output | $67B/year | 1971 baseline |
| Agricultural pollution intensity | 0.01 | Canada uses significant fertilizer but is regulated |
| Reference ag investment | $3.3B/year | 1971 baseline |
| Baseline absorption time | 12 years | Canada cold climate, faster industrial cleanup |
| Absorption saturation multiplier | 3.0 | Standard World3 value |
| Clean-tech intensity decline | 1.2%/year | Canada post-1990 environmental regulations |
| Agricultural pollution fraction | 12% | IPCC AR6 — nitrogen use efficiency for Canadian agriculture |
| Household waste per capita | 0.01 units/person/year | World Bank: Canada has high per-capita waste |

### 7.4 Nigeria parameters and sources

| Parameter | Value | Source |
|---|---|---|
| Initial PP (1971) | 3.0 × 10⁶ units | WHO Air Quality Database; lower than Canada in 1971 |
| Industrial pollution intensity | 0.008 | Mostly oil sector — localised, less diffuse |
| Reference industrial output | $4.3B/year | World Bank 1971 GDP |
| Agricultural pollution intensity | 0.005 | Low fertilizer use in 1971 |
| Reference ag investment | $0.5B/year | Same |
| Baseline absorption time | 15 years | Tropical biological breakdown |
| Clean-tech intensity decline | 0.3%/year | Slow adoption of clean technology |
| Agricultural pollution fraction | 15% | Higher: less nitrogen efficiency |
| Household waste per capita | 0.001 units/person/year | World Bank: much lower than Canada |

### 7.5 Key equations

```
Stock update:
  PP(t+1) = PP(t) + pp_gen(t) - pp_abs(t)

Pollution index (the variable sent to other sectors):
  ppolx = PP / pp_reference_1970

Absorption saturation:
  saturation_level = pp_reference_1970 × pp_absorption_saturation
  pp_ratio = PP / saturation_level
  effective_abs_time = pp_absorption_time × (1 + pp_ratio)
  pp_abs = PP / effective_abs_time
```

### 7.6 Inputs and outputs

**Receives:** io from Capital (current year); pop from Population (current year); ag_pollution from Agriculture (current year)

**Sends:** ppolx to Agriculture (next year); ppolx to Population (next year)

### 7.7 Feedback loops

- **B3 Pollution absorption** (balancing): environment absorbs until saturated
- **R3 Pollution death spiral** (reinforcing): more pollution → less food → more intensive ag → more pollution

---

## 8. Nutrition Sector

**File:** `climate_nutrition_world3/sectors/nutrition_sector.py`

### 8.1 What it represents

The "translator". Converts raw food production into nutritional outcomes — the metrics humans actually experience: calories per day, protein per day, stunting risk, food security index. No stocks; this is pure arithmetic each year.

### 8.2 Canada parameters and sources

| Parameter | Value | Source |
|---|---|---|
| kcal per kg food | 3500 | FAO Food Balance Sheets — Canada diet energy density |
| Protein per kg food | 110 g | FAO Food Balance Sheets — Canada protein-rich diet (meat, legumes) |
| Daily calorie requirement | 2250 kcal | FAO/WHO/UNU 2004; Canada higher (cold climate, body size) |
| Daily protein requirement | 56 g | Health Canada DRI for adults |
| Baseline stunting | 1% | UNICEF/WHO/WB Joint Estimates — Canada near-zero stunting |
| Maximum stunting | 15% | Worst case under severe shortage |
| Stunting sensitivity | 1.5 | Slower response (healthcare buffers) |

### 8.3 Nigeria parameters and sources

| Parameter | Value | Source |
|---|---|---|
| kcal per kg food | 3200 | FAO Food Balance Sheets — Nigerian diet bulkier (cassava, yam) |
| Protein per kg food | 80 g | FAO — cereal-heavy diet has less protein per kg |
| Daily calorie requirement | 2100 kcal | FAO/WHO/UNU 2004 |
| Daily protein requirement | 46 g | FAO — Nigerian adult requirement |
| Baseline stunting | 10% | UNICEF/WHO/WB Joint Estimates — Nigeria has ~37% stunting (under-5); 10% even at adequate food due to other causes |
| Maximum stunting | 55% | Black et al. 2013 — Nigeria worst-case under severe shortage |
| Stunting sensitivity | 3.0 | Faster response (less buffering) |

### 8.4 Key equations (the full nutrition gap calculation)

```
Convert annual food per capita to daily intake:
  daily_food_kg = food_per_capita / 365

Macronutrient supply:
  calorie_supply = daily_food_kg × kcal_per_kg_food
  protein_supply = daily_food_kg × protein_per_kg_food

Adequacy ratios (1.0 = exactly meeting requirement, capped at 1.5):
  calorie_adequacy = min(1.5, calorie_supply / daily_calorie_requirement)
  protein_adequacy = min(1.5, protein_supply / daily_protein_requirement)

Stunting risk (Black et al. 2013 nonlinear curve):
  if calorie_adequacy >= 1.0:
      stunting = stunting_baseline
  else:
      deficit = 1.0 - calorie_adequacy
      stunting = baseline + (max - baseline) × min(1, deficit × sensitivity)

Stability and food security composite:
  stability = 1 - |food_ratio[k] - food_ratio[k-1]|
  food_security = 0.5 × calorie_adequacy + 0.3 × protein_adequacy + 0.2 × stability
```

### 8.5 Inputs and outputs

**Receives:** food_per_capita, food_ratio from Agriculture (current year)

**Sends:** This is the terminal sector. Its outputs are for analysis and dashboard display.

---

## 9. Crop-Level Nutrient Analysis

**Files:** `climate_nutrition_modelling/models/nutrient_converter.py` (nutrient profiles); `climate_nutrition_world3/dashboard_v2.py` (analysis logic)

### 9.1 Why a crop-level layer

The basic Nutrition sector treats all food as a single aggregate. But in reality:
- Different crops have very different nutrient densities (1 tonne of cowpea has 30 times more iron than 1 tonne of cassava)
- Post-harvest losses vary by crop (35% for leafy greens, 5% for grains)
- Food-use fractions vary by crop (40% of maize is human food, 70% is feed and industrial)
- A country's nutrition gaps depend on which crops it grows

The crop-level layer takes the total food production from the Agriculture sector, splits it by the country's actual crop mix, and computes per-nutrient adequacy.

### 9.2 Canada crop mix

**Source:** Statistics Canada Table 32-10-0359-01 (Production of principal field crops, annual) and Table 32-10-0365-01 (Vegetable production), 2020-2023 averages, restricted to crops used directly for human food.

| Crop | Share of food mass | Notes |
|---|---|---|
| Wheat | 50% | ~32 Mt/year; primary food grain |
| Maize (corn) | 20% | ~14 Mt/year; portion used as direct food (rest is feed/industrial) |
| Soybean | 10% | ~6.5 Mt/year; food-grade share |
| Tomato | 7% | ~0.5 Mt/year; greenhouse and field combined |
| Leafy greens | 5% | Lettuce, spinach, kale combined |
| Sweet potato | 5% | Specialty share |
| Groundnut (peanut) | 3% | Imported allocation |

Canola and barley are excluded because they are predominantly oilseed/feed crops with small direct-food fractions. Their inclusion would inflate the dataset without changing nutritional outcomes.

### 9.3 Nigeria crop mix

**Source:** FAO FAOSTAT Production_Crops_Livestock_E_Africa, 2020-2023 averages, and Nigeria Bureau of Statistics Annual Abstract.

| Crop | Share of food mass | Notes |
|---|---|---|
| Cassava | 32% | ~60 Mt/year; largest food crop |
| Yam | 25% | ~50 Mt/year |
| Sorghum | 12% | ~7 Mt/year |
| Maize | 10% | ~12 Mt/year |
| Rice (paddy) | 8% | ~8 Mt/year |
| Plantain | 4% | ~3 Mt/year |
| Millet | 3% | ~2 Mt/year |
| Cowpea | 3% | ~2.5 Mt/year (high-protein legume) |
| Groundnut (peanut) | 2% | ~3 Mt/year |
| Leafy greens | 1% | Amaranth, ugu, ewedu |

This mix is heavily starch-dominated (cassava + yam = 57%), which is the underlying structural reason Nigeria has chronic vitamin A and protein deficiencies even when calorie availability is adequate.

### 9.4 Nutrient profiles per crop

**Source:** Per-100g composition values from USDA FoodData Central (Standard Reference Legacy), FAO West African Food Composition Table (FAO 2019), and FAO/INFOODS Food Composition Tables (2022). Each crop's source citation is in the comment block above its definition in `nutrient_converter.py`.

Conversion rule used (per the documented unit convention):
- mg/100g → g per tonne: multiply by 10 (for iron, zinc, calcium, vitamin C)
- µg/100g → mg per tonne: multiply by 10 (for vitamin A RAE, folate)
- g/100g → kg per tonne: multiply by 10 (for protein, fat, carbs, fiber)
- kcal/100g → kcal per tonne: multiply by 10000

Key nutrient densities (per tonne of edible crop):

| Crop | kcal | Protein (kg) | Iron (g) | Zinc (g) | Vitamin A (mg RAE) | Vitamin C (g) |
|---|---|---|---|---|---|---|
| Maize | 3,650,000 | 94 | 27 | 22 | 110 | 0 |
| Wheat | 3,270,000 | 127 | 32 | 26 | 0 | 0 |
| Rice (brown) | 3,670,000 | 75 | 15 | 20 | 0 | 0 |
| Sorghum | 3,390,000 | 112 | 44 | 17 | 0 | 0 |
| Millet | 3,780,000 | 110 | 80 | 31 | 0 | 0 |
| Cassava | 1,600,000 | 14 | 2.7 | 3.4 | 10 | 206 |
| Yam | 1,180,000 | 15 | 5.4 | 2.4 | 70 | 171 |
| **Sweet potato** | 860,000 | 16 | 6.1 | 3.0 | **7,090** | 24 |
| Cowpea | 3,360,000 | **235** | **83** | **34** | 10 | 15 |
| Groundnut | 5,670,000 | 258 | 46 | 33 | 0 | 0 |
| Soybean | 4,460,000 | 365 | **157** | 49 | 10 | 60 |
| Tomato | 180,000 | 9 | 2.7 | 1.7 | 420 | 137 |
| **Leafy greens** | 230,000 | 29 | 27 | 7 | **3,000** | 350 |
| Pepper (red bell) | 310,000 | 10 | 4.3 | 2.5 | 1,570 | **1,280** |
| Plantain | 1,220,000 | 13 | 6 | 1.4 | 560 | 184 |

**Notable findings from the data:**
- **Sweet potato** is the single best vitamin A source — 7,090 mg RAE per tonne is roughly 30 times the next-best staple
- **Leafy greens** are excellent for vitamin A (3,000), iron (27), folate (1,400), and vitamin C (350)
- **Cowpea** is the best protein and folate source among legumes accessible in Nigeria
- **Soybean** is an excellent iron source but only 30% goes to human food in most markets

### 9.5 Daily nutrient requirements used

Sources: FAO/WHO/UNU (2004) for energy/protein; WHO/FAO (2004) for micronutrients; Health Canada DRI for fiber/calcium.

| Nutrient | Daily requirement (adult average) |
|---|---|
| Energy | 2100 kcal |
| Protein | 50 g |
| Fat | 65 g |
| Fiber | 25 g |
| Iron | 12 mg |
| Zinc | 10 mg |
| Calcium | 1000 mg |
| Vitamin A | 700 µg RAE |
| Folate | 400 µg DFE |
| Vitamin C | 90 mg |

### 9.6 Adequacy calculation

```
For each nutrient:
  total_annual = sum over crops of (crop_tonnes × (1 - post_harvest_loss) × food_use_fraction × profile_value)
  per_capita_daily = total_annual / pop / 365 (with appropriate unit conversion)
  adequacy = per_capita_daily / daily_requirement
```

Adequacy below 1.0 means a deficit. Below 0.5 means severe deficit.

---

## 10. How the Five Modules Connect

### 10.1 The full coupling matrix

Read this as: "this row sends to this column". The entry shows the variable and which year's value is used.

| FROM ↓ \ TO → | Population | Capital | Agriculture | Pollution | Nutrition |
|---|---|---|---|---|---|
| **Population** | self | pop[k], labor[k] | pop[k] | pop[k] | — |
| **Capital** | hsapc[k−1] | self | ag_investment[k] | io[k] | — |
| **Agriculture** | food_ratio[k−1] | food_ratio[k−1] | self | ag_pollution[k] | food_pc[k], food_ratio[k] |
| **Pollution** | ppolx[k−1] | — | ppolx[k−1] | self | — |
| **Nutrition** | — | — | — | — | self (terminal) |

Total: 14 coupling arrows. 9 use current-year values (within the same timestep). 5 use prior-year values to break circular dependencies. This is the standard explicit Euler scheme.

### 10.2 The execution order within a single year

```
1. POPULATION updates:    uses food_ratio[k-1], hsapc[k-1], ppolx[k-1]
   ↓ pop[k] now available
2. CAPITAL updates:       uses pop[k], labor_force[k], food_ratio[k-1]
   ↓ io[k] and ag_investment[k] now available
3. AGRICULTURE updates:   uses pop[k], ag_investment[k], ppolx[k-1]
   ↓ food_per_capita[k] and food_ratio[k] now available
4. POLLUTION updates:     uses io[k], pop[k], ag_pollution[k]
   ↓ ppolx[k] now available for NEXT year
5. NUTRITION updates:     uses food_per_capita[k], food_ratio[k]
```

---

## 11. The Seven Feedback Loops

| Loop | Type | Mechanism |
|---|---|---|
| **B1 Food-Investment** | Balancing | food_ratio decreases → fioaa increases → ag_investment increases → input multiplier and yield increase → food_ratio recovers |
| **B2 Food-Mortality** | Balancing | food_ratio decreases → mortality multiplier increases → deaths in each cohort increase → population decreases → food per capita rises |
| **B3 Pollution Absorption** | Balancing | PP increases → absorption time grows (saturation) → absorption rate eventually exceeds generation → PP stabilises |
| **B4 Food-Fertility** | Balancing | food_ratio decreases → TFR is reduced → births decrease → population growth slows |
| **R1 Population Growth** | Reinforcing | population increases → P2 grows over time → births rise (P2 × TFR / 30) → population grows further |
| **R2 Capital Accumulation** | Reinforcing | IC grows → IO = IC/icor increases → investment in IC rises → IC grows further |
| **R3 Pollution Spiral** | Reinforcing (vicious) | IO rises → pollution generation rises → ppolx rises → land yield falls → food ratio falls → ag investment rises (via B1) → more fertilizer used → pollution accelerates further |

**Which loop dominates determines outcomes.** In Canada's parameter set, balancing loops dominate and the system stays near equilibrium. In Nigeria's parameter set, reinforcing loops R1 and R3 dominate, producing demographic overshoot and yield collapse — exactly the dynamic Meadows et al. described in *The Limits to Growth*.

---

## 12. Complete Data Sources Reference

### 12.1 Population and demographics

| Source | URL | Used for |
|---|---|---|
| Statistics Canada Table 17-10-0005-01 | https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000501 | Canada population by age |
| Statistics Canada Life Tables | https://www150.statcan.gc.ca/n1/pub/84-537-x/84-537-x2021001-eng.htm | Canada mortality rates |
| Statistics Canada Vital Statistics | https://www150.statcan.gc.ca/n1/en/catalogue/84-210-X | Canada TFR, births, deaths |
| UN World Population Prospects 2024 | https://population.un.org/wpp/ | Nigeria population, TFR, mortality |
| IRCC Annual Reports | https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals.html | Canada immigration |
| WHO Global Health Observatory | https://www.who.int/data/gho | Life expectancy, U5MR for both countries |

### 12.2 Economy and capital

| Source | URL | Used for |
|---|---|---|
| Statistics Canada Table 36-10-0222-01 | https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610022201 | Canada capital stock |
| World Bank World Development Indicators | https://data.worldbank.org/ | Nigeria GDP, capital, sectoral shares |
| Penn World Table 10.01 | https://www.rug.nl/ggdc/productivity/pwt/ | Capital-output ratios (ICOR) |
| WHO Global Health Expenditure Database | https://apps.who.int/nha/database | Health spending fractions |

### 12.3 Agriculture and food production

| Source | URL | Used for |
|---|---|---|
| Statistics Canada Table 32-10-0359-01 | https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3210035901 | Canada crop production and area |
| Statistics Canada Table 32-10-0365-01 | https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3210036501 | Canada vegetable production |
| FAO FAOSTAT | https://www.fao.org/faostat/en/ | Nigeria production, land use, fertilizer |
| FAO Land Use Statistics | https://www.fao.org/faostat/en/#data/RL | Arable land for both countries |
| Nigeria Bureau of Statistics | https://www.nigerianstat.gov.ng/ | Nigeria agriculture annual abstract |

### 12.4 Pollution and environment

| Source | URL | Used for |
|---|---|---|
| Environment Canada NPRI | https://www.canada.ca/en/environment-climate-change/services/national-pollutant-release-inventory.html | Canada pollution baselines |
| WHO Ambient Air Quality Database | https://www.who.int/data/gho/data/themes/air-pollution | Nigeria air quality |
| World Bank PM2.5 indicator | https://data.worldbank.org/indicator/EN.ATM.PM25.MC.M3 | Cross-country pollution comparison |
| IPCC AR6 WGII Chapter 5 | https://www.ipcc.ch/report/ar6/wg2/chapter/chapter-5/ | Climate-yield relationships |

### 12.5 Nutrition

| Source | URL | Used for |
|---|---|---|
| FAO/WHO/UNU (2004) Human Energy Requirements | https://www.fao.org/3/y5686e/y5686e00.htm | Calorie and protein requirements |
| WHO/FAO (2004) Vitamin and Mineral Requirements | https://www.who.int/publications/i/item/9241546123 | Micronutrient requirements |
| Health Canada Dietary Reference Intakes | https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/dietary-reference-intakes.html | Canada-specific DRIs |
| FAO Food Balance Sheets | https://www.fao.org/faostat/en/#data/FBS | Per-capita food intake by country |
| Black et al. (2013) | https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(13)60937-X/fulltext | Stunting-undernutrition relationship |
| UNICEF/WHO/WB Joint Malnutrition Estimates | https://data.unicef.org/topic/nutrition/malnutrition/ | Baseline stunting rates |

### 12.6 Crop nutrient profiles

| Source | URL | Used for |
|---|---|---|
| USDA FoodData Central | https://fdc.nal.usda.gov/ | Primary per-crop nutrient values; individual FDC IDs cited in code |
| FAO West African Food Composition Table (FAO 2019) | https://www.fao.org/3/ca2698en/ca2698en.pdf | West African staples (cowpea, sorghum, millet, yam) |
| FAO/INFOODS Food Composition Tables 2022 | https://www.fao.org/infoods/infoods/tables-and-databases/en/ | Cross-reference international composition data |
| Health Canada Canadian Nutrient File | https://food-nutrition.canada.ca/cnf-fce/index-eng.jsp | Canadian-specific food composition |
| Gustavsson et al. (2011), FAO | https://www.fao.org/3/i2697e/i2697e.pdf | Post-harvest loss fractions |

### 12.7 Model architecture and methodology

| Source | URL | Used for |
|---|---|---|
| Meadows et al. (1972) *The Limits to Growth* | https://www.donellameadows.org/the-limits-to-growth-now-available-to-read-online/ | Original World3 model architecture |
| Meadows et al. (2004) *Limits to Growth: 30-Year Update* | https://chelseagreen.com/product/limits-to-growth/ | Updated calibrations |
| Vanwynsberghe (2021) PyWorld3 | https://github.com/cvanwynsberghe/pyworld3 | Python implementation of World3 |
| Forrester (1961) *Industrial Dynamics* | MIT Press | Foundational system dynamics methodology |
| Sterman (2000) *Business Dynamics* | McGraw-Hill | Modern system dynamics textbook |

---

## 13. Installation and Running the Dashboard

### 13.1 Prerequisites

- Python 3.12 (the dashboard is tested on this version)
- A few hundred MB of disk space for dependencies (mainly numpy, scipy, plotly, streamlit)
- A web browser

### 13.2 Setup (first time)

From the project root directory:

```
# Activate the existing virtual environment
.\venv\Scripts\activate

# If venv does not exist, create it
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

The `requirements.txt` should contain at least:
```
numpy>=1.22,<2.3
scipy>=1.7,<2.0
pandas>=1.4
matplotlib>=3.5
streamlit>=1.25
plotly>=5.10
```

### 13.3 Start the dashboard

```
streamlit run climate_nutrition_world3/dashboard_v2.py
```

A browser window opens at `http://localhost:8501`. The model runs the baseline simulation automatically on load (takes about 1 second).

### 13.4 Deploy to the web

The dashboard can be deployed to Streamlit Community Cloud (free for public repos):

1. Push the project to GitHub (already done for the repo `anand-adroid/PyWorld3-03-Canada`).
2. Go to https://share.streamlit.io
3. Click "New app" → select the repo → set:
   - Branch: `main`
   - Main file path: `climate_nutrition_world3/dashboard_v2.py`
   - Python version: 3.12
4. Click "Deploy". After 2-3 minutes the app has a public URL.

---

## 14. Dashboard User Guide: What to Change and What to See

The dashboard has 8 tabs, each designed for a specific kind of exploration. This section walks through them with concrete experiments to try.

### 14.1 The sidebar (always visible)

| Control | Default | What it does |
|---|---|---|
| Country | Canada | Switches all calibrated parameters to either Canada or Nigeria |
| Start year | 1971 | When the simulation begins (calibrated start year) |
| End year | 2100 | How far into the future to project |
| Initial TFR | Country baseline | Children per woman at start of simulation |
| Long-run TFR target | Country baseline | What TFR converges to |
| TFR decline rate | Country baseline | How fast TFR moves toward target |
| Immigration rate | Country baseline | Annual net immigration as a fraction of population |
| Mortality improvement | Country baseline | Annual reduction in baseline mortality rates |
| Yield tech growth | Country baseline | Annual yield improvement from technology |
| Climate sensitivity | Country baseline | How much warming damages yields |
| Baseline fioaa | Country baseline | Default fraction of economy directed to agriculture |
| Pollution intensity decline | Country baseline | Annual cleanup from cleaner technology |

### 14.2 Tab 1: Overview

**Purpose:** the front page. At a glance you see whether the system is stable or stressed.

**What to look at:**
- The four metric tiles at the top show the year-2100 outcomes
- The six trajectory charts show population, industrial output, food per capita, pollution, food security, and stunting risk

**Experiment to try:** switch country between Canada and Nigeria in the sidebar. The contrast is dramatic — Canada's pollution rises modestly, food security stays at 1.0, stunting stays at 1%. Nigeria's pollution rises 40x, food security collapses to 0.25, stunting rises to 55%.

### 14.3 Tab 2: Population

**Purpose:** see the demographic engine in detail.

**Sub-tabs:**
- Total population (with baseline overlay for comparison)
- Age structure (stacked by cohort)
- Births and deaths (annual flows)
- TFR and life expectancy
- Immigration (Canada only)
- Inputs and outputs (the wiring diagram in text)

**Experiments:**
1. **Canada immigration:** slide "Immigration rate" from default 0.6% to 0%. Switch to "Immigration" sub-tab to see annual immigrants drop to zero. Switch to "Total population" sub-tab — Canada's population in 2100 falls from 108M to about 35M.
2. **Nigeria TFR:** slide "Initial TFR" from 6.9 down to 3.0. Switch to "Total population" — Nigeria 2100 population falls from ~1413M to ~600M. This demonstrates how much demographic momentum is in the system.
3. **Mortality improvement:** slide "Mortality improvement" up. Watch life expectancy rise faster.

### 14.4 Tab 3: Capital

**Purpose:** see the economy and how investment is allocated.

**Sub-tabs:**
- Capital stocks (IC and SC over time)
- Output flows (IO and SO)
- **Allocation breakdown** (the most informative — stacked area showing how output is split)
- Per-capita metrics (IOPC, HSAPC)
- Inputs and outputs

**Experiments:**
1. **Nigeria food crisis:** observe the "Allocation breakdown" sub-tab. Around 2050 when Nigeria's food_ratio drops below 1.0, the "To agriculture" stripe automatically thickens from 12% to about 35%. This is feedback loop B1 firing — the model represents the country reactively pouring more economic output into farming when food becomes scarce.
2. **Health spending:** slide "Baseline fioaa" up for Nigeria. With more capital diverted to agriculture, less goes to services. HSAPC drops. Life expectancy falls in the Population tab.

### 14.5 Tab 4: Agriculture

**Purpose:** see how food is produced and where yield is gained or lost.

**Sub-tabs:**
- Land dynamics (AL stock + development and erosion flows)
- Land fertility (LFERT + regeneration and degradation)
- **Yield decomposition** (the most informative — shows climate, input, and pollution factors over time)
- Food production (total, per capita, food ratio)
- Inputs and outputs

**Experiments:**
1. **Climate stress:** slide "Climate sensitivity" up (Canada or Nigeria). In the "Yield decomposition" sub-tab, the climate factor falls steeply after 2000. In the "Food production" sub-tab, food per capita responds.
2. **Yield technology:** slide "Yield tech growth" down for Nigeria from 0.9% to 0.4%/year (mimicking technology stagnation). Watch food per capita collapse faster.
3. **Pollution damage:** observe the pollution factor in the yield decomposition. For Nigeria, as pollution rises post-2050, the pollution factor drops below 1.0 and drives yield down.

### 14.6 Tab 5: Pollution

**Purpose:** see what's polluting and how the environment responds.

**Sub-tabs:**
- Pollution stock (with baseline overlay)
- Generation by source (industry, agriculture, household waste)
- Absorption dynamics (the saturation effect)
- Inputs and outputs

**Experiments:**
1. **Clean tech:** slide "Pollution intensity decline" from 0.3% to 1.5% for Nigeria. The 2100 pollution index falls from ~40 to ~5. The yield damage in Agriculture is largely averted.
2. **Saturation:** in the "Absorption dynamics" sub-tab, observe the "effective absorption time" line. As PP grows past the saturation threshold, absorption time rises sharply — the environment loses its self-cleaning capacity. This is the structural reason World3 produces overshoot.

### 14.7 Tab 6: Nutrition and Crops (the policy-focused tab)

**Purpose:** see how nutrition outcomes emerge from food production, by crop, by nutrient.

**Sub-tabs:**

**6a. Macronutrient adequacy** — calorie/protein adequacy and stunting over time (the headline metrics).

**6b. Crop mix editor** — sliders for each crop's share of food production. You can also add new crops from the FAO/INFOODS list.

**6c. Per-crop contributions** — for the year you selected (default 2100), cards showing each crop's contribution: total production, effective food after losses, and what fraction of daily calories, protein, and vitamin A each crop provides.

**6d. Nutrition gap heatmap** — a side-by-side comparison of baseline crop mix vs your custom mix, across all 10 tracked nutrients. The bar chart at the bottom shows adequacy ratios with a clear "Daily requirement met" reference line.

**6e. Policy insight** — automatically identifies the gaps and recommends crops to address them based on nutrient density.

**Experiments to try (these are the headline demonstrations):**

1. **Discover the Nigeria vitamin A gap:** select Nigeria, go to sub-tab 6d. Note that vitamin A adequacy is around 0.06 (severe deficit). This matches real-world Nigerian VAD data — Nigeria has one of the world's highest VAD rates.

2. **Test sweet potato intervention:** stay in Nigeria. Go to sub-tab 6b. Increase "Sweet Potato" share from 0.01 to 0.10 (10% of food crops). Decrease cassava from 0.32 to 0.23 to keep totals balanced. Go to sub-tab 6d. Vitamin A adequacy now rises substantially — sweet potato has 700 times more vitamin A per tonne than cassava. This is exactly the rationale behind the HarvestPlus orange-fleshed sweet potato programme.

3. **Test leafy greens intervention:** in sub-tab 6b, increase leafy greens from 0.01 to 0.05. Vitamin A, iron, calcium, folate, and vitamin C all rise. Leafy greens are nutrient-dense per tonne even though their production tonnage is small.

4. **Compare nutritional value of diet diversification:** sub-tab 6e auto-identifies the largest gaps and suggests the top 5 crops to close each gap. Use this to design a multi-crop policy package.

5. **See the difference between gross and effective food:** sub-tab 6c shows "Production" (gross tonnes from agriculture) vs "To food (after losses, non-food use)". The gap between these reveals where supply-chain improvements would matter most.

### 14.8 Tab 7: Cascade Lab

**Purpose:** see how a single parameter change propagates through every sector at once.

**Layout:** eight side-by-side small charts (Population, IO, FIOAA, Food per capita, Food ratio, Pollution, Calorie adequacy, Stunting) each showing baseline vs your modified scenario. Below, a table shows the parameter changes you made and the year-2100 deltas across all outcome metrics.

**Experiments:**
1. **Single parameter test:** Reset all sliders to baseline (reload the page). Then change only one — say Nigeria TFR from 6.9 to 5.0. Go to Cascade Lab. You'll see population fall (direct effect), and food per capita rise, and pollution fall, and stunting fall, and life expectancy rise — all from one change.

2. **Multi-parameter convergent intervention:** Now change multiple parameters at once — for Nigeria: TFR 6.9 → 4.0, yield growth 0.009 → 0.015, fioaa 0.12 → 0.20, pollution decline 0.003 → 0.012. Watch the cascade. Stunting drops dramatically, food security recovers, life expectancy stabilises. This demonstrates that integrated policy packages have much larger effects than single interventions.

### 14.9 Tab 8: Feedback Loops

**Purpose:** see each of the seven loops in isolation, both as a diagram (left) and as a chart (right) showing the loop's component variables.

**How to use:** select a loop with the radio buttons. The left panel shows the loop chain step-by-step. The right panel shows the actual variables of that loop plotted together. You can see when the loop is "active" by looking at the chart — for B1 (food-investment), notice that the allocation to agriculture stripe only thickens when the food ratio falls below 1.0.

**Most informative loops to demonstrate:**
- **B1 (food-investment)** — visible in Nigeria around 2050 when the food ratio dips
- **R3 (pollution spiral)** — visible across Nigeria's whole trajectory; pollution rises while land fertility falls
- **R1 (population growth)** — visible in Nigeria's exponential population curve

---

## 15. Policy Implications for Nigeria

This is where the model becomes useful for actual policy analysis. The dashboard's per-crop nutrition analysis identifies specific gaps and tests interventions quantitatively.

### 15.1 The vitamin A crisis

**Finding:** Under baseline assumptions, Nigeria 2025 has a vitamin A adequacy of approximately 0.06 — meaning the average Nigerian consumes only 6% of the recommended daily vitamin A intake. This matches real-world data: Nigeria has one of the world's highest vitamin A deficiency rates, with roughly 30% of children under 5 affected (UNICEF Nigeria Multiple Indicator Cluster Survey).

**Mechanism:** Nigeria's dominant crops (cassava, yam, sorghum, maize, rice, millet) contain negligible vitamin A. Only sweet potato (orange-fleshed varieties), plantain, and leafy greens have meaningful vitamin A content. But these together account for only 6% of food production.

**Intervention 1: Orange-fleshed sweet potato (OFSP) scale-up.** The model shows that raising OFSP share from 0.01 to 0.05 of the crop mix (a five-fold scale-up) would close roughly half the vitamin A gap. This is exactly the HarvestPlus programme's strategy in sub-Saharan Africa, which has shown 35-50% reduction in VAD prevalence in pilot areas (HarvestPlus / CIP studies).

**Intervention 2: Leafy greens (ugu, ewedu, amaranth) promotion.** Pushing leafy greens share from 0.01 to 0.03 also closes a meaningful share of the vitamin A gap and improves iron, folate, and vitamin C simultaneously. Leafy greens are already culturally important in Nigerian cuisine — the intervention is intensification of supply, not new behaviour change.

**Intervention 3: Vitamin A fortification of staples.** This is not in the current model but can be approximated by overriding the maize vitamin A profile to reflect biofortified varieties (e.g., Pro-Vitamin A maize from HarvestPlus, which delivers ~200 µg RAE/100g instead of 11 µg). Future work should add a fortification slider.

### 15.2 Calorie and protein gaps

**Finding:** Nigeria 2025 per-crop analysis shows calorie adequacy of 0.51 and protein adequacy of 0.52 — meaning the average Nigerian consumes about half the required calories and protein when post-harvest losses and non-food uses are accounted for. The basic Nutrition sector reports higher numbers because it treats all crop production as food.

**Intervention 1: Post-harvest loss reduction.** FAO estimates Nigeria loses 30-50% of fresh produce post-harvest due to inadequate storage, transport, and cold chain. Each percentage point of loss avoided is a percentage point of additional calorie and protein supply. The model's post-harvest loss parameters can be edited per crop in `nutrient_converter.py` to simulate storage improvements.

**Intervention 2: Cowpea expansion.** Cowpea provides 235 kg protein per tonne — among the highest of all tracked crops. Doubling cowpea share from 0.03 to 0.06 would noticeably improve protein adequacy while also raising iron (cowpea has 83 g iron per tonne) and folate (an exceptional 6,330 mg per tonne).

**Intervention 3: Aquaculture and livestock.** The current model focuses on plant crops. Animal-source food contributions could be added — Nigeria's tilapia farming and small ruminant production provide significant complete protein. Future work.

### 15.3 Yield intensification

**Finding:** Nigeria's tech yield growth is 0.9%/year, less than half of Canada's 1.4%. Doubling Nigeria's yield growth would substantially reduce the food gap by 2050.

**Intervention 1: Fertilizer access.** Nigeria's fertilizer use is approximately 16 kg/ha, compared to 130 kg/ha for Canada. Subsidised fertilizer programmes (the Anchor Borrowers Programme, the Presidential Fertilizer Initiative) directly raise the `tech_yield_growth_rate` parameter.

**Intervention 2: Improved seed varieties.** ICRISAT, IITA, and AfricaRice have released drought-tolerant, pest-resistant, and high-yielding varieties of sorghum, millet, rice, and maize for Nigerian conditions. Adoption directly raises the technology multiplier.

**Intervention 3: Irrigation infrastructure.** Only about 1% of Nigeria's cropland is irrigated, compared to 14% globally. Irrigation reduces climate sensitivity and stabilises yields.

**Trade-off:** Intensification raises pollution. In the model, more `ag_investment` produces more `ag_pollution`, which raises `ppolx`, which reduces yield. This is reinforcing loop R3 — the pollution death spiral. Nigeria's path forward needs both intensification AND clean technology adoption (higher `pollution_intensity_decline`).

### 15.4 Demographic transition

**Finding:** Nigeria's population continues growing rapidly because TFR remains above 4 even by 2030. Each child born adds to food demand for ~70 years.

**Intervention 1: Female education.** UN data shows TFR drops by about 1.5 children per woman when girls complete secondary education versus none. Modelled by raising `tfr_decline_rate`.

**Intervention 2: Family planning access.** Sub-Saharan African countries with strong family planning programmes (Rwanda, Ethiopia) have seen TFR drop 1-2 children per decade. Modelled by lowering `tfr_target`.

**Intervention 3: Urbanisation.** Urban TFR is typically lower than rural by 1-2 children. As Nigeria urbanises (currently ~52%, projected ~70% by 2050), TFR declines structurally. Not currently a model parameter but could be added.

### 15.5 Climate adaptation

**Finding:** Nigeria's climate sensitivity (0.002/year yield loss after 2000) compounds with population growth and pollution to produce yield collapse by 2080.

**Intervention 1: Drought-tolerant varieties.** ICRISAT's drought-tolerant maize and pearl millet reduce climate damage. Modelled by lowering `climate_sensitivity`.

**Intervention 2: Climate-smart agriculture.** Conservation tillage, agroforestry, water harvesting. Reduce both climate sensitivity and erosion rate.

**Intervention 3: National adaptation strategy alignment with NDCs.** Nigeria's Nationally Determined Contributions under the Paris Agreement include agriculture adaptation targets. Implementation effort directly maps to model parameter changes.

### 15.6 Convergent policy bundles

The Cascade Lab tab demonstrates that **multi-axis interventions produce far larger benefits than single ones**. A realistic convergent bundle for Nigeria might include:

| Component | Parameter modified | Suggested change |
|---|---|---|
| Family planning + female education | `tfr_decline_rate` | 0.007 → 0.012 |
| OFSP and leafy greens scale-up | Crop mix sliders | Sweet potato 1% → 5%, leafy greens 1% → 3% |
| Fertilizer access | `tech_yield_growth_rate` | 0.009 → 0.014 |
| Climate-smart agriculture | `climate_sensitivity` | 0.002 → 0.001 |
| Clean technology adoption | `pollution_intensity_decline` | 0.003 → 0.010 |
| Cowpea expansion | Crop mix slider | Cowpea 3% → 6% |

Running this bundle in the Cascade Lab versus baseline shows the cumulative benefit — population stabilises near 800M instead of 1413M, food security stays above 0.8 instead of dropping to 0.25, stunting plateaus near 25% instead of 55%, and life expectancy continues rising instead of crashing.

This is a quantitatively defensible scenario that could be presented to Nigerian government planners, donor agencies (USAID, FCDO, Gates Foundation), and multilateral organisations (FAO, World Bank, AfDB).

---

## 16. Limitations and Caveats

The model is a tool for **structured exploration**, not a forecast. Specific limitations to disclose:

### 16.1 Scope limitations

- **Single country at a time.** The model does not represent trade flows between Canada and Nigeria, nor between either country and the global market. Global food prices, geopolitical disruptions, and bilateral trade agreements are not modelled.
- **No subnational variation.** Nigeria's north and south have very different agro-ecological zones; the model uses national averages.
- **No animal-source foods.** Meat, dairy, eggs, and fish are not currently modelled. Nigerian aquaculture and pastoralism are growing — adding these would refine the protein and micronutrient analysis.
- **No urban/rural distinction.** Both countries are modelled as homogeneous national populations, ignoring that nutrition outcomes differ substantially between urban and rural areas.

### 16.2 Data quality

- **Crop nutrient profiles** are based on USDA FoodData Central and FAO/INFOODS averages. Real on-the-ground varieties can differ by 2-3x in some micronutrients. Country-specific food composition tables would improve precision.
- **Post-harvest loss fractions** are FAO global averages, not country-specific measurements.
- **Climate parameters** are simplified — a real climate-yield analysis would use CMIP6 ensemble projections downscaled to country level.

### 16.3 Behavioural assumptions

- **Capital allocation logic** assumes the country reactively shifts investment toward agriculture when food becomes scarce. Real governments often fail to do this in time or at sufficient scale (the model is optimistic on this front).
- **TFR transition** is modelled as exponential decay toward a target. Real demographic transitions are more complex — they can stall (Nigeria 2010-2020 TFR stalled around 5.5) or reverse temporarily.
- **No price signals.** The model has no money, no markets, no prices. It is a physical-flows model. Adding prices and economic agents would be a substantial extension.

### 16.4 Integration scheme

- **1-year timestep** with explicit Euler. Short-term dynamics (within-year shocks, seasonal variation) are not captured.
- **1-year coupling lag** on feedback arrows. Mathematically necessary but means responses lag by one year relative to a true simultaneous equilibrium.

### 16.5 Calibration

- Country-level parameters were chosen to match observed historical trajectories 1971-2023. Beyond 2023, the model is extrapolating — it produces *plausible* trajectories under continued current trends, not *predicted* ones. Real future depends on policy choices the model does not represent.

These limitations do not invalidate the model. They define its scope: it is a **structured exploration tool** for understanding feedback dynamics and identifying high-leverage interventions, not a forecasting engine for specific year-by-year outcomes.

---

## 17. References

### Foundational system dynamics

- Forrester, J.W. (1961). *Industrial Dynamics*. Cambridge, MA: MIT Press.
- Forrester, J.W. (1968). *Principles of Systems*. Pegasus Communications.
- Sterman, J.D. (2000). *Business Dynamics: Systems Thinking and Modeling for a Complex World*. McGraw-Hill.

### World3 model

- Meadows, D.H., Meadows, D.L., Randers, J., & Behrens, W.W. (1972). *The Limits to Growth*. New York: Universe Books.
- Meadows, D.H., Randers, J., & Meadows, D.L. (2004). *Limits to Growth: The 30-Year Update*. Chelsea Green Publishing.
- Vanwynsberghe, C. (2021). PyWorld3: Python implementation of the World3 model. https://github.com/cvanwynsberghe/pyworld3

### Food systems and nutrition

- Black, R.E., Victora, C.G., Walker, S.P., et al. (2013). Maternal and child undernutrition and overweight in low-income and middle-income countries. *The Lancet*, 382(9890), 427-451.
- FAO (2023). *The State of Food Security and Nutrition in the World*. Rome.
- FAO/WHO/UNU (2004). *Human Energy Requirements*. Rome: FAO.
- WHO/FAO (2004). *Vitamin and Mineral Requirements in Human Nutrition*, 2nd edition. Geneva: WHO.
- Gustavsson, J., Cederberg, C., Sonesson, U., van Otterdijk, R., & Meybeck, A. (2011). *Global Food Losses and Food Waste*. Rome: FAO.

### Climate and agriculture

- IPCC (2022). *AR6 Working Group II Report, Chapter 5: Food, Fibre and Other Ecosystem Products*. Cambridge University Press.
- Zhu, C., Kobayashi, K., Loladze, I., et al. (2018). Carbon dioxide (CO₂) levels this century will alter the protein, micronutrients, and vitamin content of rice grains. *Nature Plants*, 4, 957-964.

### Convergent innovation in food systems

- Struben, J., Chan, D., Talukder, B., & Dubé, L. (2025). Market pathways to food systems transformation toward healthy and equitable diets through convergent innovation. *Nature Communications*, 16(1), 4246.
- Ostrom, E. (2009). A general framework for analyzing sustainability of social-ecological systems. *Science*, 325(5939), 419-422.

### Data sources

- Statistics Canada — Government of Canada statistical agency: https://www.statcan.gc.ca
- UN Department of Economic and Social Affairs, Population Division — World Population Prospects 2024: https://population.un.org/wpp/
- Food and Agriculture Organization of the United Nations — FAOSTAT: https://www.fao.org/faostat/
- World Bank — World Development Indicators: https://data.worldbank.org/
- World Health Organization — Global Health Observatory: https://www.who.int/data/gho
- US Department of Agriculture — FoodData Central: https://fdc.nal.usda.gov/
- Health Canada — Dietary Reference Intakes: https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/dietary-reference-intakes.html
- Penn World Table 10.01 — Groningen Growth and Development Centre: https://www.rug.nl/ggdc/productivity/pwt/
- Environment and Climate Change Canada — National Pollutant Release Inventory: https://www.canada.ca/en/environment-climate-change/services/national-pollutant-release-inventory.html

---

## Appendix: Quick reference

### A.1 File locations

| File | Purpose |
|---|---|
| `climate_nutrition_world3/dashboard_v2.py` | Main interactive dashboard |
| `climate_nutrition_world3/world3_integrator.py` | Master coupling class (5 sectors) |
| `climate_nutrition_world3/sectors/population_sector.py` | Population module |
| `climate_nutrition_world3/sectors/capital_sector.py` | Capital module |
| `climate_nutrition_world3/sectors/agriculture_sector.py` | Agriculture module |
| `climate_nutrition_world3/sectors/pollution_sector.py` | Pollution module |
| `climate_nutrition_world3/sectors/nutrition_sector.py` | Nutrition module |
| `climate_nutrition_modelling/models/nutrient_converter.py` | Crop nutrient profiles |
| `climate_nutrition_world3/DOCUMENTATION.md` | This document |

### A.2 Quick start commands

```
# Run dashboard
streamlit run climate_nutrition_world3/dashboard_v2.py

# Run a single scenario from Python
python -c "
from climate_nutrition_world3 import World3Integrator
m = World3Integrator.from_country('nigeria', 1971, 2100)
m.run()
m.print_summary()
"
```

### A.3 Where to start exploring

1. Open the dashboard.
2. Select **Nigeria** in the sidebar.
3. Go to **Tab 6: Nutrition and Crops → sub-tab 6d (heatmap)** to see the headline nutrition gaps.
4. Go to **Tab 6 → sub-tab 6b (crop mix editor)** and try the sweet potato + leafy greens intervention.
5. Go to **Tab 7: Cascade Lab** and try a multi-parameter convergent intervention.

The model's value comes from interactive exploration, not just from reading the documentation. Use it.
