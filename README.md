# PyWorld3 Country-Level Food System Model

A five-sector coupled system dynamics model of national food systems,
calibrated for **Canada** and **Nigeria**. Based on the World3 architecture
of Meadows et al. (1972) *The Limits to Growth*, implemented in Python
on top of PyWorld3 (Vanwynsberghe, 2021), with an IPCC AR6 climate
overlay (Zhu et al. 2018) for SSP scenario analysis.

The model simulates how five interdependent sectors evolve from 1971 to
2100 under bidirectional feedback:

| Sector | Stocks (state variables) |
|---|---|
| Population | Four age cohorts (0-14, 15-44, 45-64, 65+) |
| Capital | Industrial Capital, Service Capital |
| Agriculture | Arable Land, Land Fertility |
| Pollution | Persistent Pollution |
| Nutrition | (terminal sector — calories, protein, micronutrients) |

Plus an **exogenous climate module** (ClimateAgricultureBridge) that
optionally overlays IPCC AR6 SSP1-2.6 / SSP2-4.5 / SSP3-7.0 / SSP5-8.5
temperature, precipitation, and CO2 trajectories onto the agriculture
sector. CO2-induced nutrient dilution (protein, iron, zinc) follows
Zhu et al. (2018) *Nature Plants*.

The interactive Streamlit dashboard (9 tabs) lets users adjust any
parameter, crop mix, or IPCC scenario and watch the effects cascade
through all five sectors and seven named feedback loops.

## Quick start

Install dependencies:

```
pip install -r requirements.txt
```

Run the interactive dashboard:

```
streamlit run climate_nutrition_world3/dashboard_v2.py
```

Or run a scenario from Python:

```python
from climate_nutrition_world3 import World3Integrator

# Baseline with simple linear climate model
model = World3Integrator.from_country('nigeria', 1971, 2100)
model.run()
df = model.get_all_results()
model.print_summary()

# Same country under IPCC SSP5-8.5 (fossil-fuel future)
model_climate = World3Integrator.from_country(
    'nigeria', 1971, 2100, climate_scenario='ssp585'
)
model_climate.run()
print(f"Climate factor 2100: {model_climate.agriculture.climate_factor[-1]:.2f}")
print(f"Temperature 2100:    {model_climate.climate_bridge.temperature[-1]:.1f} C")
print(f"CO2 2100:            {model_climate.climate_bridge.co2_ppm[-1]:.0f} ppm")
```

## Documentation

See [DOCUMENTATION.md](DOCUMENTATION.md) for the complete project reference:

- Methodology (system dynamics, World3, calibration philosophy)
- Each sector explained with every parameter and its data source
- Inter-module coupling and the seven feedback loops
- Crop-level nutrient analysis with per-crop profiles
- Complete data sources with URLs
- Dashboard user guide with experiments to try
- Policy implications for Nigeria

## Data sources

All parameters are calibrated against published government and
international agency data. Primary sources:

- Statistics Canada (population, capital, agriculture, pollution)
- UN World Population Prospects 2024 (Nigeria demographics)
- FAO FAOSTAT (Nigeria agriculture, fertilizer)
- World Bank World Development Indicators (Nigeria economy)
- WHO Global Health Observatory (life expectancy, mortality)
- USDA FoodData Central (per-crop nutrient profiles)
- FAO/INFOODS Food Composition Tables (2022)
- FAO West African Food Composition Table (FAO 2019)
- IPCC AR6 (climate trajectories)
- Penn World Table 10.01 (capital-output ratios)

Full citations and direct URLs in DOCUMENTATION.md.

## Project structure

```
PyWorld3-Country-Food-System/
├── README.md
├── DOCUMENTATION.md
├── requirements.txt
├── .python-version
├── LICENSE
├── climate_nutrition_world3/
│   ├── __init__.py
│   ├── dashboard_v2.py                       Interactive Streamlit dashboard (9 tabs)
│   ├── world3_integrator.py                  5-sector coupling engine + IPCC bridge support
│   └── sectors/
│       ├── population_sector.py
│       ├── capital_sector.py
│       ├── agriculture_sector.py
│       ├── pollution_sector.py
│       ├── nutrition_sector.py
│       └── climate_agriculture_bridge.py     IPCC SSP -> agriculture overlay
└── climate_nutrition_modelling/
    └── models/
        ├── nutrient_converter.py             Crop nutrient profiles (FAO/INFOODS, USDA)
        └── climate_scenarios.py              IPCC AR6 SSP scenario generator
```

## Architecture references

- Meadows, D.H. et al. (1972). *The Limits to Growth*. Universe Books.
- Meadows, D.H. et al. (2004). *Limits to Growth: 30-Year Update*. Chelsea Green.
- Forrester, J.W. (1961). *Industrial Dynamics*. MIT Press.
- Sterman, J.D. (2000). *Business Dynamics*. McGraw-Hill.
- Vanwynsberghe, C. (2021). PyWorld3. https://github.com/cvanwynsberghe/pyworld3

## License

MIT - see LICENSE file.
