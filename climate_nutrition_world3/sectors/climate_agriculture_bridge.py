"""
Climate-Agriculture Bridge — Connects IPCC crop model to World3 agriculture.

This module bridges the detailed crop-level IPCC model (from climate_nutrition_modelling)
into the World3 system dynamics agriculture sector. The crop model provides
mechanistic yield predictions under SSP climate scenarios; the World3 provides
the feedback structure (population pressure, capital allocation, pollution).

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │              Climate-Agriculture Bridge                     │
    │                                                             │
    │  IPCC SSP Scenario ──→ ClimateScenarioManager               │
    │         │                    │                               │
    │         │              temperature, precip, CO2              │
    │         ▼                    ▼                               │
    │  Climate stress factor ──→ World3 Agriculture Sector        │
    │                                                             │
    │  NutrientConverter ──→ Crop-specific nutrient profiles      │
    │         │                    │                               │
    │         ▼                    ▼                               │
    │  Micronutrient analysis → Enhanced Nutrition Sector          │
    │  (iron, zinc, vitamin A, protein by crop)                   │
    └─────────────────────────────────────────────────────────────┘

WHAT THIS BRIDGE DOES:
    1. Replaces the World3 agriculture sector's simple climate_sensitivity
       parameter with actual IPCC SSP-derived climate stress factors
    2. Provides crop-specific yield multipliers (not just generic cereal)
    3. Feeds CO2-induced nutrient degradation into the nutrition sector
    4. Enables scenario comparison: SSP1-2.6 vs SSP2-4.5 vs SSP5-8.5

References:
    - IPCC AR6 WGI SPM Table SPM.1 — Global warming trajectories
    - IPCC AR6 WGII Ch.5 — Climate impacts on food systems
    - Zhu et al. (2018) Nature Plants — CO2 and nutrient dilution
    - FAO/INFOODS (2022) — Crop nutrient profiles

Author: Climate-Nutrition World3 Integration Project
"""

import numpy as np
import sys
import os

# Add parent path so we can import from climate_nutrition_modelling
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from climate_nutrition_modelling.models.climate_scenarios import (
    ClimateScenarioManager, RegionalClimateBaseline, REGIONAL_BASELINES
)
from climate_nutrition_modelling.models.nutrient_converter import (
    NutrientConverter, CROP_NUTRIENT_PROFILES
)


class ClimateAgricultureBridge:
    """
    Bridges IPCC climate scenarios into the World3 agriculture sector.

    Instead of a simple linear climate_sensitivity parameter, this bridge
    uses the full IPCC SSP climate projection machinery to compute
    year-by-year climate stress factors that are fed into the World3
    agriculture sector at each timestep.

    It also computes crop-specific nutrient availability using the
    NutrientConverter, enabling the nutrition sector to track
    micronutrients (iron, zinc, vitamin A) — not just calories/protein.

    Usage:
        bridge = ClimateAgricultureBridge.for_nigeria(scenario='ssp245')
        # During World3 integration loop:
        climate_factor = bridge.get_climate_factor(k)
        nutrient_detail = bridge.get_nutrient_breakdown(k, food_production_kg)
    """

    # Nigeria's key crops and their share of total cereal-equivalent production
    # Source: FAO FAOSTAT — Nigeria production statistics (2020-2023 average)
    NIGERIA_CROP_MIX = {
        'cassava': 0.30,        # 30% of food production (by weight)
        'maize_grain': 0.15,    # 15%
        'rice_paddy': 0.10,     # 10%
        'sorghum': 0.12,        # 12%
        'millet': 0.08,         # 8%
        'yam': 0.12,            # 12%
        'cowpea': 0.05,         # 5%
        'groundnut': 0.04,      # 4%
        'plantain': 0.04,       # 4%
    }

    # Canada's key crops
    # Source: Statistics Canada Table 32-10-0359-01
    CANADA_CROP_MIX = {
        'wheat': 0.45,          # 45% — dominant crop
        'maize_grain': 0.25,    # 25% — corn
        'soybean': 0.15,        # 15%
        'tomato': 0.05,         # 5%
        'leafy_greens': 0.05,   # 5%
        'sweet_potato': 0.05,   # 5%
    }

    def __init__(self,
                 baseline: RegionalClimateBaseline,
                 scenario: str = 'ssp245',
                 crop_mix: dict = None,
                 year_start: int = 1971,
                 year_end: int = 2100,
                 seed: int = 42):
        """
        Initialize the climate-agriculture bridge.

        Args:
            baseline: Regional climate baseline (from ClimateScenarioManager)
            scenario: IPCC SSP scenario ('ssp126', 'ssp245', 'ssp370', 'ssp585')
            crop_mix: Dict of crop_key → fraction of total production
            year_start: Simulation start year
            year_end: Simulation end year
            seed: Random seed for climate variability
        """
        self.scenario = scenario
        self.year_start = year_start
        self.year_end = year_end
        self.crop_mix = crop_mix or {}

        # Generate climate scenario data
        self.climate_mgr = ClimateScenarioManager(baseline)
        self.climate_data = self.climate_mgr.generate_scenario(
            scenario=scenario,
            year_start=year_start,
            year_end=year_end,
            seed=seed,
        )

        # Pre-compute climate stress factors for each year
        n = year_end - year_start + 1
        self.time = np.arange(year_start, year_end + 1)
        self.climate_stress = self.climate_data['Climate_Stress_Factor'].values
        self.co2_ppm = self.climate_data['CO2_ppm'].values
        self.temperature = self.climate_data['Temperature_C'].values
        self.precipitation = self.climate_data['Precipitation_mm'].values

        # CO2-induced nutrient degradation factors
        # Source: Zhu et al. (2018) Nature Plants — CO2 reduces protein, Fe, Zn
        co2_above_ref = np.maximum(0, self.co2_ppm - 400)
        self.protein_degradation = 1.0 - 0.00015 * co2_above_ref  # ~5% loss at 700ppm
        self.iron_degradation = 1.0 - 0.00015 * co2_above_ref
        self.zinc_degradation = 1.0 - 0.00010 * co2_above_ref

        # Nutrient converter for crop-specific analysis
        self.nutrient_converter = NutrientConverter()

    @classmethod
    def for_nigeria(cls, scenario: str = 'ssp245', **kwargs):
        """Create bridge pre-configured for Nigeria."""
        # Use northern Nigeria baseline (savanna — major food producing region)
        baseline = REGIONAL_BASELINES['nigeria_north']
        return cls(baseline=baseline, scenario=scenario,
                   crop_mix=cls.NIGERIA_CROP_MIX, **kwargs)

    @classmethod
    def for_canada(cls, scenario: str = 'ssp245', **kwargs):
        """Create bridge pre-configured for Canada."""
        baseline = REGIONAL_BASELINES['canada_ontario']
        return cls(baseline=baseline, scenario=scenario,
                   crop_mix=cls.CANADA_CROP_MIX, **kwargs)

    def get_climate_factor(self, k: int) -> float:
        """
        Get IPCC-derived climate stress factor for timestep k.

        This replaces the simple linear climate_sensitivity in the
        World3 agriculture sector with a mechanistic climate projection.

        Returns:
            float: Climate factor (1.0 = no stress, <1.0 = climate damage)
                   Derived from IPCC SSP temperature/precipitation projections.
        """
        if k < 0 or k >= len(self.climate_stress):
            return 1.0
        return float(self.climate_stress[k])

    def get_co2_ppm(self, k: int) -> float:
        """Get atmospheric CO2 concentration at timestep k."""
        if k < 0 or k >= len(self.co2_ppm):
            return 412.0
        return float(self.co2_ppm[k])

    def get_nutrient_degradation(self, k: int) -> dict:
        """
        Get CO2-induced nutrient degradation factors at timestep k.

        As CO2 rises, crops produce more carbohydrates but less protein,
        iron, and zinc per unit weight (Zhu et al. 2018).

        Returns:
            dict with keys: protein_factor, iron_factor, zinc_factor
            (1.0 = no degradation, <1.0 = nutrient loss)
        """
        if k < 0 or k >= len(self.protein_degradation):
            return {'protein_factor': 1.0, 'iron_factor': 1.0, 'zinc_factor': 1.0}
        return {
            'protein_factor': float(self.protein_degradation[k]),
            'iron_factor': float(self.iron_degradation[k]),
            'zinc_factor': float(self.zinc_degradation[k]),
        }

    def get_nutrient_breakdown(self, k: int, total_food_kg: float) -> dict:
        """
        Convert total food production to crop-specific nutrient breakdown.

        Uses the crop mix proportions and NutrientConverter to compute
        detailed nutrient availability (11 nutrients × N crops).

        Args:
            k: Timestep index
            total_food_kg: Total food production in kg from agriculture sector

        Returns:
            dict with nutrient totals and per-crop breakdown
        """
        total_food_tonnes = total_food_kg / 1000.0

        converter = NutrientConverter()

        for crop_key, fraction in self.crop_mix.items():
            crop_tonnes = total_food_tonnes * fraction
            converter.convert_crop(crop_key, crop_tonnes)

        totals = converter.get_total_nutrients()

        # Apply CO2-induced nutrient degradation
        if k < len(self.protein_degradation):
            totals['protein_kg'] *= self.protein_degradation[k]
            totals['iron_g'] *= self.iron_degradation[k]
            totals['zinc_g'] *= self.zinc_degradation[k]

        return totals

    def get_scenario_label(self) -> str:
        """Human-readable label for the current scenario."""
        labels = {
            'ssp126': 'SSP1-2.6 (Sustainability)',
            'ssp245': 'SSP2-4.5 (Middle of Road)',
            'ssp370': 'SSP3-7.0 (Regional Rivalry)',
            'ssp585': 'SSP5-8.5 (Fossil Fuel Dev)',
        }
        return labels.get(self.scenario, self.scenario)

    def get_climate_summary_at_year(self, year: int) -> dict:
        """Get climate conditions at a specific year."""
        k = year - self.year_start
        if k < 0 or k >= len(self.temperature):
            return {}
        return {
            'year': year,
            'temperature_c': float(self.temperature[k]),
            'precipitation_mm': float(self.precipitation[k]),
            'co2_ppm': float(self.co2_ppm[k]),
            'climate_stress': float(self.climate_stress[k]),
            'protein_degradation': float(self.protein_degradation[k]),
            'scenario': self.scenario,
        }
