"""
PyWorld3 Country-Level Food System Model
========================================

Five-sector coupled World3-style system dynamics model calibrated for
Canada and Nigeria. Sectors: Population, Capital, Agriculture, Pollution,
Nutrition. Architecture follows Meadows et al. (1972) The Limits to Growth;
Python implementation based on PyWorld3 (Vanwynsberghe 2021).

Usage:
    from climate_nutrition_world3 import World3Integrator
    model = World3Integrator.from_country('canada', 1971, 2100)
    model.run()
    df = model.get_all_results()

    # Or run as an interactive dashboard:
    # streamlit run climate_nutrition_world3/dashboard_v2.py

See DOCUMENTATION.md for the complete project reference.
"""

__version__ = "1.0.0"

from .world3_integrator import World3Integrator, run_scenario, COUNTRY_PRESETS
from .sectors import (
    PopulationSector, PopulationParams,
    CANADA_POPULATION_PARAMS, NIGERIA_POPULATION_PARAMS,
    CapitalSector, CapitalParams,
    CANADA_CAPITAL_PARAMS, NIGERIA_CAPITAL_PARAMS,
    AgricultureSector, AgricultureParams,
    CANADA_AGRICULTURE_PARAMS, NIGERIA_AGRICULTURE_PARAMS,
    PollutionSector, PollutionParams,
    CANADA_POLLUTION_PARAMS, NIGERIA_POLLUTION_PARAMS,
    NutritionSector, NutritionParams,
    CANADA_NUTRITION_PARAMS, NIGERIA_NUTRITION_PARAMS,
)
from .sectors.climate_agriculture_bridge import ClimateAgricultureBridge
