"""
Nutrition Sector — Converts food production to nutritional outcomes.

This is the final downstream sector that translates agricultural output
into human nutritional status, performing gap analysis between production
and population requirements.

STATE VARIABLES:
    (None — this is a pure computational/analysis sector)

OUTPUT VARIABLES:
    calorie_supply[k]    — Total calories available [kcal/day/person]
    protein_supply[k]    — Protein available [g/day/person]
    nutrition_gap[k]     — Fractional gap (1.0 = fully met, <1 = deficit)
    stunting_risk[k]     — Estimated stunting prevalence (children <5)
    food_security_index[k] — Composite food security score

FEEDBACK FROM OTHER SECTORS:
    food_per_capita[k]  — from Agriculture → raw food availability
    food_ratio[k]       — from Agriculture → adequacy ratio
    pop[k]              — from Population → demand denominator

OUTPUTS TO OTHER SECTORS:
    (Nutrition is a terminal sector — outputs are for analysis/display only)

References:
    - FAO (2023): The State of Food Security and Nutrition in the World
    - WHO (2021): Global Nutrition Targets 2025
    - UNICEF/WHO/World Bank (2023): Joint Child Malnutrition Estimates
    - Black et al. (2013): Maternal and child undernutrition, Lancet 382
    - IPCC AR6 WGII Ch.5 (2022): Food security projections

Data Sources:
    - Canada: Health Canada Dietary Reference Intakes
    - Nigeria: Nigeria Food Consumption and Nutrition Survey 2018
    - Global: FAO Food Balance Sheets (FAOSTAT)
    - Conversion factors: FAO/WHO/UNU (2004) energy requirements
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class NutritionParams:
    """
    Nutrition sector parameters.

    Conversion factors from food mass to nutritional content.

    References:
        FAO/WHO/UNU (2004): Human energy requirements
        FAO Food Balance Sheets methodology
        Health Canada: Dietary Reference Intakes
    """
    # ── Conversion factors (cereal-equivalent basis) ──
    # 1 kg cereal ≈ 3500 kcal (FAO)
    kcal_per_kg_food: float = 3500.0

    # 1 kg cereal ≈ 100g protein (FAO — average including legumes/meat)
    protein_per_kg_food: float = 100.0

    # ── Daily requirements ──
    # Source: FAO/WHO/UNU (2004)
    daily_calorie_requirement: float = 2100.0   # kcal/day minimum
    daily_protein_requirement: float = 50.0     # g/day minimum

    # ── Stunting model ──
    # Simplified model: stunting prevalence as function of food adequacy
    # Reference: Black et al. (2013) — undernutrition-stunting relationship
    # UNICEF/WHO/World Bank Joint Child Malnutrition Estimates
    stunting_baseline: float = 0.05     # Baseline stunting rate at full food
    stunting_max: float = 0.50          # Maximum stunting at severe shortage
    stunting_sensitivity: float = 2.0   # How fast stunting responds to shortage

    # ── Food security composite ──
    # Weighted composite of caloric adequacy, protein, and stability
    weight_calorie: float = 0.5
    weight_protein: float = 0.3
    weight_stability: float = 0.2   # Year-over-year consistency


# ─── COUNTRY PRESETS ──────────────────────────────────────────────

CANADA_NUTRITION_PARAMS = NutritionParams(
    # Health Canada — Dietary Reference Intakes
    kcal_per_kg_food=3500.0,
    protein_per_kg_food=110.0,     # More diverse diet → more protein per kg
    daily_calorie_requirement=2250.0,  # Higher standard (cold climate)
    daily_protein_requirement=56.0,
    # Canada: very low stunting
    stunting_baseline=0.01,
    stunting_max=0.15,
    stunting_sensitivity=1.5,
)

NIGERIA_NUTRITION_PARAMS = NutritionParams(
    # Nigeria Food Consumption and Nutrition Survey 2018
    kcal_per_kg_food=3200.0,       # Less diverse diet
    protein_per_kg_food=80.0,      # Lower protein content (cereal-heavy)
    daily_calorie_requirement=2100.0,
    daily_protein_requirement=46.0,
    # Nigeria: significant stunting prevalence
    stunting_baseline=0.10,        # 10% even at adequate food
    stunting_max=0.55,             # Up to 55% in severe shortage
    stunting_sensitivity=3.0,      # Rapid response to food deficit
)


class NutritionSector:
    """
    Nutrition analysis sector — terminal sector in the World3 coupling.

    Converts food production from the Agriculture sector into nutritional
    metrics for analysis and dashboard display. This sector has no stocks
    (no Euler integration) — it performs instantaneous conversion.

    Computation Flow:
        food_per_capita [kg/yr]
            │
            ├── ÷ 365 × kcal_per_kg → daily calorie supply
            ├── ÷ 365 × protein_per_kg → daily protein supply
            │
            ├── calorie_adequacy = supply / requirement
            ├── protein_adequacy = supply / requirement
            │
            ├── stunting_risk = f(calorie_adequacy)
            └── food_security_index = weighted composite

    This sector exists to:
        1. Convert raw food output to meaningful nutritional metrics
        2. Enable gap analysis (what nutrients are lacking)
        3. Compute health outcomes (stunting, malnutrition)
        4. Provide the final dashboard metrics
    """

    def __init__(self, params: NutritionParams, year_start: int = 1971,
                 year_end: int = 2100, dt: float = 1.0):
        self.params = params
        self.year_start = year_start
        self.year_end = year_end
        self.dt = dt
        self.n = int((year_end - year_start) / dt) + 1
        self.time = np.linspace(year_start, year_end, self.n)

        # ── OUTPUT VARIABLES ──
        self.calorie_supply = np.zeros(self.n)      # kcal/day/person
        self.protein_supply = np.zeros(self.n)       # g/day/person
        self.calorie_adequacy = np.zeros(self.n)     # ratio (1.0 = meets requirement)
        self.protein_adequacy = np.zeros(self.n)     # ratio
        self.nutrition_gap = np.zeros(self.n)         # composite gap (1.0 = no gap)
        self.stunting_risk = np.zeros(self.n)         # fraction of children <5
        self.food_security_index = np.zeros(self.n)  # 0-1 composite score

        # ── COUPLING INPUTS ──
        self.food_per_capita = np.zeros(self.n)
        self.food_ratio = np.zeros(self.n)

    # ──────────────────────────────────────────────────────────────
    # SECTOR UPDATE
    # ──────────────────────────────────────────────────────────────

    def step(self, k: int, food_per_capita: float, food_ratio: float):
        """
        Compute nutritional outcomes for timestep k.

        Args:
            k: Current timestep index
            food_per_capita: kg food / person / year (from Agriculture)
            food_ratio: food_pc / subsistence (from Agriculture)
        """
        p = self.params

        # Store inputs
        self.food_per_capita[k] = food_per_capita
        self.food_ratio[k] = food_ratio

        # ── 1. CALORIC ANALYSIS ──
        # Convert kg/year to kcal/day
        daily_food_kg = food_per_capita / 365.0
        self.calorie_supply[k] = daily_food_kg * p.kcal_per_kg_food
        self.calorie_adequacy[k] = min(1.5, self.calorie_supply[k] / p.daily_calorie_requirement)

        # ── 2. PROTEIN ANALYSIS ──
        self.protein_supply[k] = daily_food_kg * p.protein_per_kg_food
        self.protein_adequacy[k] = min(1.5, self.protein_supply[k] / p.daily_protein_requirement)

        # ── 3. STUNTING RISK ──
        # Reference: Black et al. (2013) — nonlinear relationship
        if self.calorie_adequacy[k] >= 1.0:
            self.stunting_risk[k] = p.stunting_baseline
        else:
            deficit = 1.0 - self.calorie_adequacy[k]
            self.stunting_risk[k] = p.stunting_baseline + (
                p.stunting_max - p.stunting_baseline) * min(1.0,
                deficit * p.stunting_sensitivity)

        # ── 4. FOOD SECURITY INDEX ──
        # Composite: caloric adequacy + protein adequacy + stability
        cal_score = min(1.0, self.calorie_adequacy[k])
        prot_score = min(1.0, self.protein_adequacy[k])

        # Stability: how much food_ratio changed year-over-year
        if k > 0:
            stability = max(0, 1.0 - abs(self.food_ratio[k] - self.food_ratio[k-1]))
        else:
            stability = 1.0

        self.food_security_index[k] = (
            p.weight_calorie * cal_score +
            p.weight_protein * prot_score +
            p.weight_stability * stability
        )

        # ── 5. OVERALL NUTRITION GAP ──
        # 1.0 = all needs met, <1.0 = deficit
        self.nutrition_gap[k] = min(cal_score, prot_score)

    # ──────────────────────────────────────────────────────────────
    # OUTPUT INTERFACE
    # ──────────────────────────────────────────────────────────────

    def get_results_df(self):
        """Return full results as DataFrame for dashboard display."""
        import pandas as pd
        return pd.DataFrame({
            'Year': self.time,
            'Calorie_Supply_kcal_day': self.calorie_supply,
            'Protein_Supply_g_day': self.protein_supply,
            'Calorie_Adequacy': self.calorie_adequacy,
            'Protein_Adequacy': self.protein_adequacy,
            'Nutrition_Gap': self.nutrition_gap,
            'Stunting_Risk': self.stunting_risk,
            'Food_Security_Index': self.food_security_index,
            'Food_Per_Capita_Input': self.food_per_capita,
            'Food_Ratio_Input': self.food_ratio,
        })
