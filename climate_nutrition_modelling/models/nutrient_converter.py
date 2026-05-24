"""
Nutrient Converter Module.

Converts crop production (tonnes) into nutritional content using
FAO/INFOODS food composition data and USDA FoodData Central values.

This is the bridge between agricultural output and human nutrition.

Data Sources:
- FAO/INFOODS Food Composition Tables (2022)
  https://www.fao.org/infoods/infoods/tables-and-databases/en/
- USDA FoodData Central
  https://fdc.nal.usda.gov/
- West African Food Composition Table (FAO, 2019)
  https://www.fao.org/3/ca2698en/ca2698en.pdf

Author: Climate-Nutrition Modelling Project
License: MIT
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class NutrientProfile:
    """
    Nutritional content per 1000 kg (1 tonne) of raw crop.
    Values account for average moisture content and edible portion.

    Units:
    - energy_kcal: kilocalories
    - protein_kg, fat_kg, carbs_kg, fiber_kg: kilograms
    - iron_g, zinc_g, calcium_g: grams
    - vitamin_a_mg_rae: milligrams Retinol Activity Equivalents
    - folate_mg: milligrams
    - vitamin_c_g: grams
    """
    crop_name: str
    energy_kcal: float = 0.0
    protein_kg: float = 0.0
    fat_kg: float = 0.0
    carbs_kg: float = 0.0
    fiber_kg: float = 0.0
    iron_g: float = 0.0
    zinc_g: float = 0.0
    calcium_g: float = 0.0
    vitamin_a_mg_rae: float = 0.0
    folate_mg: float = 0.0
    vitamin_c_g: float = 0.0

    # Post-harvest loss fraction (0 to 1)
    post_harvest_loss: float = 0.0

    # Fraction used for human food (rest is feed, seed, industrial)
    food_use_fraction: float = 1.0


# ============================================================
# CROP NUTRIENT PROFILES - VERIFIED VALUES
# ============================================================
#
# Units per 1000 kg (1 tonne) of raw, edible-portion crop:
#   energy_kcal      : kilocalories
#   protein_kg       : kilograms of protein
#   fat_kg           : kilograms of fat
#   carbs_kg         : kilograms of carbohydrates
#   fiber_kg         : kilograms of dietary fibre
#   iron_g           : grams of iron
#   zinc_g           : grams of zinc
#   calcium_g        : grams of calcium
#   vitamin_a_mg_rae : milligrams Retinol Activity Equivalents
#   folate_mg        : milligrams of folate (total folate)
#   vitamin_c_g      : grams of vitamin C (ascorbic acid)
#
# Conversion rule used: take the published per-100g value and multiply by 10
# to get the per-tonne value in the unit above.
#   Example: maize iron 2.7 mg/100g  ->  27 g/tonne  (iron_g = 27)
#   Example: tomato vit C 13.7 mg/100g -> 137 g/tonne (vitamin_c_g = 137)
#   Example: sweet potato vit A 709 ug RAE/100g -> 7090 mg/tonne (vitamin_a_mg_rae = 7090)
#
# Energy uses the x10000 rule (kcal/100g to kcal/tonne):
#   Example: maize 365 kcal/100g -> 3,650,000 kcal/tonne
#
# Macronutrient (protein/fat/carbs/fiber) uses the x10 rule:
#   Example: cowpea protein 23.5 g/100g -> 235 kg/tonne (protein_kg = 235)
#
# Per-100g composition source for each crop is cited in its definition.
# Primary references:
#   - USDA FoodData Central (Standard Reference Legacy) - U.S.D.A. ARS
#     https://fdc.nal.usda.gov/
#   - FAO/INFOODS Food Composition Tables (2022)
#   - FAO West African Food Composition Table (FAO, 2019)
#     https://www.fao.org/3/ca2698en/ca2698en.pdf
#   - Health Canada Canadian Nutrient File 2015
#
# Post-harvest loss and food-use fractions: FAO (2019) Food Loss and Waste
# Database; Gustavsson et al. (2011) Global Food Losses and Food Waste, FAO.

CROP_NUTRIENT_PROFILES = {
    # --- CEREALS ---
    'maize_grain': NutrientProfile(
        crop_name='Maize (Corn) Grain',
        # USDA FoodData Central, yellow corn raw, FDC ID 169998:
        # 365 kcal, 9.4g protein, 4.74g fat, 74.3g carbs, 7.3g fiber,
        # 2.71mg iron, 2.21mg zinc, 7mg Ca, 11ug RAE vitA, 19ug folate
        energy_kcal=3_650_000,
        protein_kg=94.0,
        fat_kg=47.0,
        carbs_kg=743.0,
        fiber_kg=73.0,
        iron_g=27.0,
        zinc_g=22.0,
        calcium_g=70.0,
        vitamin_a_mg_rae=110.0,
        folate_mg=190.0,
        vitamin_c_g=0.0,
        post_harvest_loss=0.10,
        food_use_fraction=0.40,
    ),
    'rice_paddy': NutrientProfile(
        crop_name='Rice (Brown, Raw)',
        # USDA FoodData Central, brown rice long-grain raw, FDC ID 169704:
        # 367 kcal, 7.5g protein, 2.7g fat, 77g carbs, 3.5g fiber,
        # 1.5mg iron, 2.0mg zinc, 33mg Ca, 0 vitA, 20ug folate
        energy_kcal=3_670_000,
        protein_kg=75.0,
        fat_kg=27.0,
        carbs_kg=770.0,
        fiber_kg=35.0,
        iron_g=15.0,
        zinc_g=20.0,
        calcium_g=330.0,
        vitamin_a_mg_rae=0.0,
        folate_mg=200.0,
        vitamin_c_g=0.0,
        post_harvest_loss=0.08,
        food_use_fraction=0.85,
    ),
    'sorghum': NutrientProfile(
        crop_name='Sorghum Grain',
        # USDA + FAO West African Food Composition (FAO 2019):
        # 339 kcal, 11.2g protein, 3.3g fat, 72.9g carbs, 6.7g fiber,
        # 4.4mg iron, 1.7mg zinc, 28mg Ca, 0 vitA, 20ug folate
        energy_kcal=3_390_000,
        protein_kg=112.0,
        fat_kg=33.0,
        carbs_kg=729.0,
        fiber_kg=67.0,
        iron_g=44.0,
        zinc_g=17.0,
        calcium_g=280.0,
        vitamin_a_mg_rae=0.0,
        folate_mg=200.0,
        vitamin_c_g=0.0,
        post_harvest_loss=0.12,
        food_use_fraction=0.70,
    ),
    'millet': NutrientProfile(
        crop_name='Pearl Millet Grain',
        # FAO West African Food Composition (FAO 2019); USDA cross-ref:
        # 378 kcal, 11g protein, 4.2g fat, 73g carbs, 8.5g fiber,
        # 8mg iron, 3.1mg zinc, 42mg Ca, 0 vitA, 85ug folate
        energy_kcal=3_780_000,
        protein_kg=110.0,
        fat_kg=42.0,
        carbs_kg=730.0,
        fiber_kg=85.0,
        iron_g=80.0,
        zinc_g=31.0,
        calcium_g=420.0,
        vitamin_a_mg_rae=0.0,
        folate_mg=850.0,
        vitamin_c_g=0.0,
        post_harvest_loss=0.15,
        food_use_fraction=0.80,
    ),
    'wheat': NutrientProfile(
        crop_name='Wheat Grain (Hard Red)',
        # USDA FoodData Central, hard red winter wheat, FDC ID 169721:
        # 327 kcal, 12.6g protein, 1.5g fat, 71.2g carbs, 12.2g fiber,
        # 3.2mg iron, 2.6mg zinc, 29mg Ca, 0 vitA, 38ug folate
        energy_kcal=3_270_000,
        protein_kg=127.0,
        fat_kg=15.0,
        carbs_kg=714.0,
        fiber_kg=122.0,
        iron_g=32.0,
        zinc_g=26.0,
        calcium_g=290.0,
        vitamin_a_mg_rae=0.0,
        folate_mg=380.0,
        vitamin_c_g=0.0,
        post_harvest_loss=0.05,
        food_use_fraction=0.75,
    ),

    # --- ROOT AND TUBER CROPS ---
    'cassava': NutrientProfile(
        crop_name='Cassava (Fresh Root)',
        # USDA FoodData Central, cassava raw, FDC ID 169985:
        # 160 kcal, 1.36g protein, 0.28g fat, 38g carbs, 1.8g fiber,
        # 0.27mg iron, 0.34mg zinc, 16mg Ca, 1ug RAE vitA, 27ug folate,
        # 20.6mg vitC
        energy_kcal=1_600_000,
        protein_kg=14.0,
        fat_kg=3.0,
        carbs_kg=380.0,
        fiber_kg=18.0,
        iron_g=2.7,
        zinc_g=3.4,
        calcium_g=160.0,
        vitamin_a_mg_rae=10.0,
        folate_mg=270.0,
        vitamin_c_g=206.0,
        post_harvest_loss=0.25,
        food_use_fraction=0.70,
    ),
    'yam': NutrientProfile(
        crop_name='Yam (White, Fresh)',
        # USDA, yam raw, FDC ID 169217; FAO West African Food Composition:
        # 118 kcal, 1.5g protein, 0.17g fat, 27.9g carbs, 4.1g fiber,
        # 0.54mg iron, 0.24mg zinc, 17mg Ca, 7ug RAE vitA, 23ug folate,
        # 17.1mg vitC
        energy_kcal=1_180_000,
        protein_kg=15.0,
        fat_kg=2.0,
        carbs_kg=279.0,
        fiber_kg=41.0,
        iron_g=5.4,
        zinc_g=2.4,
        calcium_g=170.0,
        vitamin_a_mg_rae=70.0,
        folate_mg=230.0,
        vitamin_c_g=171.0,
        post_harvest_loss=0.22,
        food_use_fraction=0.85,
    ),
    'sweet_potato': NutrientProfile(
        crop_name='Sweet Potato (Orange-fleshed, Raw)',
        # USDA, sweet potato raw, FDC ID 168482:
        # 86 kcal, 1.57g protein, 0.05g fat, 20.1g carbs, 3.0g fiber,
        # 0.61mg iron, 0.30mg zinc, 30mg Ca, 709ug RAE vitA, 11ug folate,
        # 2.4mg vitC
        energy_kcal=860_000,
        protein_kg=16.0,
        fat_kg=1.0,
        carbs_kg=201.0,
        fiber_kg=30.0,
        iron_g=6.1,
        zinc_g=3.0,
        calcium_g=300.0,
        vitamin_a_mg_rae=7090.0,
        folate_mg=110.0,
        vitamin_c_g=24.0,
        post_harvest_loss=0.20,
        food_use_fraction=0.90,
    ),

    # --- LEGUMES ---
    'cowpea': NutrientProfile(
        crop_name='Cowpea (Dry, Raw)',
        # USDA, cowpea dry raw, FDC ID 173757; FAO West African Food
        # Composition: 336 kcal, 23.5g protein, 1.26g fat, 60g carbs,
        # 10.7g fiber, 8.27mg iron, 3.37mg zinc, 110mg Ca,
        # 1ug RAE vitA, 633ug folate, 1.5mg vitC
        energy_kcal=3_360_000,
        protein_kg=235.0,
        fat_kg=13.0,
        carbs_kg=600.0,
        fiber_kg=107.0,
        iron_g=83.0,
        zinc_g=34.0,
        calcium_g=1100.0,
        vitamin_a_mg_rae=10.0,
        folate_mg=6330.0,
        vitamin_c_g=15.0,
        post_harvest_loss=0.08,
        food_use_fraction=0.90,
    ),
    'groundnut': NutrientProfile(
        crop_name='Groundnut (Peanut, Raw with Skin)',
        # USDA, peanut raw with skin, FDC ID 172430:
        # 567 kcal, 25.8g protein, 49.2g fat, 16.1g carbs, 8.5g fiber,
        # 4.58mg iron, 3.27mg zinc, 92mg Ca, 0 vitA, 240ug folate
        energy_kcal=5_670_000,
        protein_kg=258.0,
        fat_kg=492.0,
        carbs_kg=161.0,
        fiber_kg=85.0,
        iron_g=46.0,
        zinc_g=33.0,
        calcium_g=920.0,
        vitamin_a_mg_rae=0.0,
        folate_mg=2400.0,
        vitamin_c_g=0.0,
        post_harvest_loss=0.06,
        food_use_fraction=0.60,
    ),
    'soybean': NutrientProfile(
        crop_name='Soybean (Mature Seed, Raw)',
        # USDA, mature soybean raw, FDC ID 174270:
        # 446 kcal, 36.5g protein, 19.9g fat, 30.2g carbs, 9.3g fiber,
        # 15.7mg iron, 4.89mg zinc, 277mg Ca, 1ug RAE vitA, 375ug folate,
        # 6mg vitC
        energy_kcal=4_460_000,
        protein_kg=365.0,
        fat_kg=199.0,
        carbs_kg=302.0,
        fiber_kg=93.0,
        iron_g=157.0,
        zinc_g=49.0,
        calcium_g=2770.0,
        vitamin_a_mg_rae=10.0,
        folate_mg=3750.0,
        vitamin_c_g=60.0,
        post_harvest_loss=0.05,
        food_use_fraction=0.30,
    ),

    # --- VEGETABLES ---
    'tomato': NutrientProfile(
        crop_name='Tomato (Red, Ripe, Raw)',
        # USDA, tomato raw red ripe, FDC ID 170457:
        # 18 kcal, 0.88g protein, 0.2g fat, 3.89g carbs, 1.2g fiber,
        # 0.27mg iron, 0.17mg zinc, 10mg Ca, 42ug RAE vitA, 15ug folate,
        # 13.7mg vitC
        energy_kcal=180_000,
        protein_kg=9.0,
        fat_kg=2.0,
        carbs_kg=39.0,
        fiber_kg=12.0,
        iron_g=2.7,
        zinc_g=1.7,
        calcium_g=100.0,
        vitamin_a_mg_rae=420.0,
        folate_mg=150.0,
        vitamin_c_g=137.0,
        post_harvest_loss=0.30,
        food_use_fraction=0.95,
    ),
    'leafy_greens': NutrientProfile(
        crop_name='Leafy Greens (Spinach/Amaranth average)',
        # Average of USDA spinach raw (FDC 168462) and amaranth leaves
        # (FDC 169215): 23 kcal, 2.9g protein, 0.4g fat, 3.6g carbs,
        # 2.2g fiber, 2.7mg iron, 0.7mg zinc, 150mg Ca,
        # 300ug RAE vitA, 140ug folate, 35mg vitC
        energy_kcal=230_000,
        protein_kg=29.0,
        fat_kg=4.0,
        carbs_kg=36.0,
        fiber_kg=22.0,
        iron_g=27.0,
        zinc_g=7.0,
        calcium_g=1500.0,
        vitamin_a_mg_rae=3000.0,
        folate_mg=1400.0,
        vitamin_c_g=350.0,
        post_harvest_loss=0.35,
        food_use_fraction=0.95,
    ),
    'pepper': NutrientProfile(
        crop_name='Pepper (Red Bell, Raw)',
        # USDA, red bell pepper raw, FDC ID 170427:
        # 31 kcal, 0.99g protein, 0.3g fat, 6.0g carbs, 2.1g fiber,
        # 0.43mg iron, 0.25mg zinc, 7mg Ca, 157ug RAE vitA, 46ug folate,
        # 127.7mg vitC
        energy_kcal=310_000,
        protein_kg=10.0,
        fat_kg=3.0,
        carbs_kg=60.0,
        fiber_kg=21.0,
        iron_g=4.3,
        zinc_g=2.5,
        calcium_g=70.0,
        vitamin_a_mg_rae=1570.0,
        folate_mg=460.0,
        vitamin_c_g=1280.0,
        post_harvest_loss=0.25,
        food_use_fraction=0.95,
    ),
    'okra': NutrientProfile(
        crop_name='Okra (Raw)',
        # USDA, okra raw, FDC ID 169218:
        # 33 kcal, 1.9g protein, 0.2g fat, 7.5g carbs, 3.2g fiber,
        # 0.62mg iron, 0.58mg zinc, 82mg Ca, 36ug RAE vitA, 60ug folate,
        # 23mg vitC
        energy_kcal=330_000,
        protein_kg=19.0,
        fat_kg=2.0,
        carbs_kg=75.0,
        fiber_kg=32.0,
        iron_g=6.2,
        zinc_g=5.8,
        calcium_g=820.0,
        vitamin_a_mg_rae=360.0,
        folate_mg=600.0,
        vitamin_c_g=230.0,
        post_harvest_loss=0.28,
        food_use_fraction=0.95,
    ),

    # --- FRUITS ---
    'plantain': NutrientProfile(
        crop_name='Plantain (Yellow, Ripe, Raw)',
        # USDA, plantain raw yellow, FDC ID 169124:
        # 122 kcal, 1.3g protein, 0.37g fat, 31.9g carbs, 2.3g fiber,
        # 0.6mg iron, 0.14mg zinc, 3mg Ca, 56ug RAE vitA, 22ug folate,
        # 18.4mg vitC
        energy_kcal=1_220_000,
        protein_kg=13.0,
        fat_kg=4.0,
        carbs_kg=319.0,
        fiber_kg=23.0,
        iron_g=6.0,
        zinc_g=1.4,
        calcium_g=30.0,
        vitamin_a_mg_rae=560.0,
        folate_mg=220.0,
        vitamin_c_g=184.0,
        post_harvest_loss=0.30,
        food_use_fraction=0.90,
    ),
}


class NutrientConverter:
    """
    Converts crop production data into nutritional availability.

    Takes production in tonnes for each crop and calculates total
    nutrient availability after accounting for:
    1. Post-harvest losses
    2. Food vs non-food use allocation
    3. Nutrient content per tonne

    Usage:
        converter = NutrientConverter()
        converter.add_crop('maize_grain', production_tonnes=15_000_000)
        converter.add_crop('cassava', production_tonnes=60_000_000)
        nutrients = converter.get_total_nutrients()
    """

    TRACKED_NUTRIENTS = [
        'energy_kcal', 'protein_kg', 'fat_kg', 'carbs_kg', 'fiber_kg',
        'iron_g', 'zinc_g', 'calcium_g', 'vitamin_a_mg_rae', 'folate_mg',
        'vitamin_c_g',
    ]

    def __init__(self):
        self.crop_contributions: Dict[str, Dict[str, float]] = {}
        self.profiles = CROP_NUTRIENT_PROFILES.copy()

    def add_custom_profile(self, key: str, profile: NutrientProfile):
        """Add or override a nutrient profile for a crop."""
        self.profiles[key] = profile

    def convert_crop(
        self,
        crop_key: str,
        production_tonnes: float,
        food_fraction_override: Optional[float] = None,
        loss_fraction_override: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Convert crop production to nutrients available for human consumption.

        Args:
            crop_key: Key into CROP_NUTRIENT_PROFILES
            production_tonnes: Total production in tonnes
            food_fraction_override: Override the default food use fraction
            loss_fraction_override: Override post-harvest loss fraction

        Returns:
            Dict of nutrient name → total amount available
        """
        if crop_key not in self.profiles:
            raise ValueError(f"Unknown crop: {crop_key}. "
                           f"Available: {list(self.profiles.keys())}")

        profile = self.profiles[crop_key]
        loss = loss_fraction_override if loss_fraction_override is not None else profile.post_harvest_loss
        food_frac = food_fraction_override if food_fraction_override is not None else profile.food_use_fraction

        # Effective tonnes for human food
        effective_tonnes = production_tonnes * (1 - loss) * food_frac

        nutrients = {}
        for nutrient in self.TRACKED_NUTRIENTS:
            per_tonne = getattr(profile, nutrient, 0.0)
            nutrients[nutrient] = effective_tonnes * per_tonne

        nutrients['effective_food_tonnes'] = effective_tonnes
        nutrients['total_production_tonnes'] = production_tonnes
        nutrients['crop_name'] = profile.crop_name

        self.crop_contributions[crop_key] = nutrients
        return nutrients

    def convert_production_timeseries(
        self,
        crop_key: str,
        production_series: pd.Series,
        years: pd.Series,
    ) -> pd.DataFrame:
        """
        Convert a time series of crop production to nutrient availability.

        Args:
            crop_key: Key into CROP_NUTRIENT_PROFILES
            production_series: Annual production in tonnes
            years: Corresponding years

        Returns:
            DataFrame with Year and all nutrient columns
        """
        if crop_key not in self.profiles:
            raise ValueError(f"Unknown crop: {crop_key}")

        profile = self.profiles[crop_key]
        effective = production_series * (1 - profile.post_harvest_loss) * profile.food_use_fraction

        result = pd.DataFrame({'Year': years})
        result['Effective_Food_Tonnes'] = effective.values

        for nutrient in self.TRACKED_NUTRIENTS:
            per_tonne = getattr(profile, nutrient, 0.0)
            result[nutrient] = effective.values * per_tonne

        result['Crop'] = crop_key
        return result

    def get_total_nutrients(self) -> Dict[str, float]:
        """Get total nutrients from all crops added so far."""
        totals = {n: 0.0 for n in self.TRACKED_NUTRIENTS}
        totals['total_food_tonnes'] = 0.0

        for crop_key, nutrients in self.crop_contributions.items():
            for n in self.TRACKED_NUTRIENTS:
                totals[n] += nutrients.get(n, 0.0)
            totals['total_food_tonnes'] += nutrients.get('effective_food_tonnes', 0.0)

        return totals

    def get_contribution_table(self) -> pd.DataFrame:
        """Get a breakdown table showing each crop's contribution."""
        rows = []
        for crop_key, nutrients in self.crop_contributions.items():
            row = {'Crop': nutrients.get('crop_name', crop_key)}
            row['Production_tonnes'] = nutrients.get('total_production_tonnes', 0)
            row['Food_tonnes'] = nutrients.get('effective_food_tonnes', 0)
            for n in self.TRACKED_NUTRIENTS:
                row[n] = nutrients.get(n, 0)
            rows.append(row)

        return pd.DataFrame(rows)
