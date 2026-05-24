"""
Agriculture Sector — World3-style food production with climate feedback.

Integrates crop production modeling with World3 capital/pollution/population
feedback loops. Land fertility is a stock that degrades with pollution and
improves with agricultural investment.

STATE VARIABLES (Stocks):
    al[k]    — Arable land [hectares]
    lfert[k] — Land fertility [kg/ha potential yield]
    ai[k]    — Agricultural inputs (capital invested) [$/year]

FLOW VARIABLES (Rates):
    food_production[k] — Total food produced [kg/year]
    land_development[k] — New land brought into production [ha/year]
    land_erosion[k]     — Land lost to erosion/degradation [ha/year]
    fert_regen[k]       — Fertility regeneration [units/year]
    fert_degrade[k]     — Fertility degradation [units/year]

FEEDBACK FROM OTHER SECTORS:
    pop[k]          — from Population → food demand
    ag_investment[k] — from Capital → agricultural inputs
    ppolx[k]        — from Pollution → reduces land fertility

OUTPUTS TO OTHER SECTORS:
    food_per_capita[k] — food / pop → Population (mortality feedback)
    food_ratio[k]      — food_pc / subsistence → Capital (allocation shift)
    ag_pollution[k]    — fertilizer intensity → Pollution

References:
    - Meadows et al. (1972) Ch.6: Agriculture Sector
    - Meadows et al. (2004) Ch.3: Food system
    - Sterman (2000) Ch.11: Agricultural dynamics
    - IPCC AR6 WGII Ch.5 (2022): Food, Fibre, Ecosystem Products
    - FAO (2023): World Food and Agriculture Statistical Yearbook
    - PyWorld3 (Vanwynsberghe 2021): agriculture.py

Data Sources:
    - Canada: Statistics Canada Table 32-10-0359-01 (crop production)
    - Nigeria: NBS Annual Abstract, FAO FAOSTAT
    - Land area: FAO Land Use Statistics
    - Fertilizer: FAO Fertilizer consumption (kg/ha)
    - Yields: FAO crop yields by country
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class AgricultureParams:
    """
    Agriculture sector parameters.

    Combines World3 structure with real agricultural data.

    References:
        World3: Meadows (1972) Table 6-1
        FAO FAOSTAT: Production, Land Use, Inputs
        Statistics Canada / NBS Nigeria
    """
    # ── Land parameters ──
    al_init: float = 40e6          # Initial arable land [hectares]
    al_max: float = 60e6           # Maximum potential arable land [ha]
    land_development_rate: float = 0.005  # Fraction of remaining land developed/year
    land_erosion_rate: float = 0.002      # Fraction of arable land eroded/year

    # ── Land fertility ──
    # Source: FAO — typical yields and potential
    lfert_init: float = 3000.0     # Initial land fertility [kg/ha]
    lfert_max: float = 8000.0      # Maximum achievable fertility [kg/ha]

    # Fertility degradation from pollution
    # Reference: IPCC AR6 — pollution effects on soil
    lfert_pollution_sensitivity: float = 0.05  # fertility loss per unit ppolx above 1

    # Fertility improvement from investment
    # Reference: Meadows (1972) — land yield multiplier from capital
    lfert_investment_response: float = 0.0001  # fertility gain per $ invested/ha

    # Fertility natural regeneration
    lfert_regen_time: float = 30.0  # Years for natural fertility recovery

    # ── Food production ──
    # food = arable_land × land_fertility × climate_factor × input_intensity
    # Source: FAO yield data, climate projections
    subsistence_food_pc: float = 230.0  # kg/person/year (subsistence requirement)
    # Reference: FAO — minimum dietary requirement ~2100 kcal/day ≈ 230 kg cereal equiv.

    # Agricultural input (intensification) multiplier
    # More investment → higher yields (with diminishing returns)
    # Reference: Meadows (1972) — land yield multiplier from inputs
    input_intensity_max: float = 3.0   # Max multiplier from inputs
    input_half_saturation: float = 500.0  # $/ha where multiplier = 1.5

    # ── Technology/Green Revolution yield growth (exogenous) ──
    # Historical yield growth NOT explained by investment alone
    # Source: FAO — cereal yields grew 1-2%/year globally from green revolution
    # This captures genetics, agronomic practices, improved varieties
    tech_yield_growth_rate: float = 0.012  # 1.2%/year exogenous yield growth

    # ── Climate parameters ──
    # Base climate factor (modified by scenarios)
    climate_base: float = 1.0          # Normal climate = 1.0
    climate_sensitivity: float = 0.002  # Yield reduction per year from warming

    # ── Pollution effect on yield ──
    # Reference: IPCC AR6 Ch.5 — ozone/pollution damage to crops
    pollution_yield_sensitivity: float = 0.08  # yield loss per unit ppolx above 1


# ─── COUNTRY PRESETS ──────────────────────────────────────────────

CANADA_AGRICULTURE_PARAMS = AgricultureParams(
    # Statistics Canada Table 32-10-0359-01
    # Canada 1971: ~36.6M ha cropland, yield ~1960 kg/ha
    # Canada 2023: ~38.3M ha, yield ~4079 kg/ha (doubled!)
    al_init=36.6e6,
    al_max=42e6,               # Max potential ~42M ha (peaked at 41.5 in 1986)
    land_development_rate=0.002,   # Slow — already near max
    land_erosion_rate=0.0008,      # Low erosion

    # Yields: 1960 kg/ha (1971) → 4079 kg/ha (2023)
    # ~1.4%/year growth from technology, fertilizer, genetics
    lfert_init=1960.0,         # 1971 actual yield
    lfert_max=7000.0,          # Theoretical max with full technology

    lfert_pollution_sensitivity=0.02,
    lfert_investment_response=0.0002,
    lfert_regen_time=20.0,

    # Food requirements — Canada produces ~4x subsistence
    subsistence_food_pc=250.0,

    # Already high-input in 1971
    input_intensity_max=2.5,
    input_half_saturation=300.0,

    # Technology: Canada yields grew ~1.4%/year (1960→4079 over 52 years)
    tech_yield_growth_rate=0.014,

    # Climate — minimal damage through 2023
    climate_base=1.0,
    climate_sensitivity=0.001,

    pollution_yield_sensitivity=0.02,
)

NIGERIA_AGRICULTURE_PARAMS = AgricultureParams(
    # FAO FAOSTAT — Nigeria
    # Nigeria 1971: ~33M ha arable, yield ~1050 kg/ha
    # Nigeria 2023: ~37M ha arable, yield ~1656 kg/ha (modest growth)
    al_init=33e6,
    al_max=82e6,               # FAO: 82M ha potentially suitable
    land_development_rate=0.003,   # Slow expansion despite pressure
    land_erosion_rate=0.002,       # Moderate erosion

    # Yields: 1050 kg/ha (1971) → 1656 kg/ha (2023)
    # Only ~0.9%/year growth — low input agriculture
    lfert_init=1050.0,
    lfert_max=5000.0,          # Theoretical max with full intensification

    lfert_pollution_sensitivity=0.03,
    lfert_investment_response=0.0004,  # High response potential
    lfert_regen_time=30.0,

    # Food requirements — Nigeria is food-insecure
    # ~2100 kcal/day minimum ≈ 200 kg cereal equivalent
    subsistence_food_pc=200.0,

    # Low-input agriculture — enormous room for intensification
    input_intensity_max=4.0,
    input_half_saturation=150.0,  # Responds at low investment

    # Technology: Nigeria yields grew ~0.9%/year (1050→1656 over 52 years)
    tech_yield_growth_rate=0.009,

    # Climate — already impacting (Sahel desertification, rainfall)
    climate_base=1.0,
    climate_sensitivity=0.002,

    pollution_yield_sensitivity=0.03,
)


class AgricultureSector:
    """
    World3-style agriculture sector with land, fertility, and food dynamics.

    Architecture follows Meadows (1972) with extensions for climate feedback
    and country-specific calibration.

    Stock-Flow Structure:
        ┌──────────────┐           ┌──────────────────┐
        │  Arable Land │           │  Land Fertility  │
        │    (al)      │           │    (lfert)       │
        └──┬─────┬─────┘           └──┬──────────┬────┘
           ↑     ↓                    ↑          ↓
     land_dev  erosion          fert_regen   fert_degrade
           │     │                    │          │
           │     └── al×eros_rate     │          ├── ppolx × sensitivity
           │                          │          └── over-use degradation
           └── (al_max-al)×dev_rate   │
                                      └── natural + investment

        Food Production = al × lfert × climate × input_multiplier
        Food Per Capita = food_production / population
        Food Ratio = food_per_capita / subsistence_requirement

    Key Feedback Loops (World3):
        B1: food shortage → more capital to ag → more food (balancing)
        B2: more ag inputs → more pollution → lower fertility → less food
        R1: population growth → more demand → food shortage (reinforcing)
        B4: food shortage → higher mortality → less population → less demand
    """

    def __init__(self, params: AgricultureParams, year_start: int = 1971,
                 year_end: int = 2100, dt: float = 1.0):
        self.params = params
        self.year_start = year_start
        self.year_end = year_end
        self.dt = dt
        self.n = int((year_end - year_start) / dt) + 1
        self.time = np.linspace(year_start, year_end, self.n)

        # ── STATE VARIABLES (Stocks) ──
        self.al = np.zeros(self.n)              # Arable land [ha]
        self.lfert = np.zeros(self.n)           # Land fertility [kg/ha]
        self.ai = np.zeros(self.n)              # Agricultural inputs [$/year]

        # ── FLOW VARIABLES ──
        self.land_development = np.zeros(self.n)
        self.land_erosion = np.zeros(self.n)
        self.fert_regen = np.zeros(self.n)
        self.fert_degrade = np.zeros(self.n)

        # ── OUTPUT VARIABLES ──
        self.food_production = np.zeros(self.n)  # Total food [kg/year]
        self.food_per_capita = np.zeros(self.n)  # Food per person [kg/person/year]
        self.food_ratio = np.zeros(self.n)       # food_pc / subsistence
        self.land_yield = np.zeros(self.n)       # Effective yield [kg/ha]
        self.input_intensity = np.zeros(self.n)  # $/ha of agricultural input
        self.input_multiplier = np.zeros(self.n) # Yield multiplier from inputs
        self.climate_factor = np.zeros(self.n)   # Climate effect on yield
        self.ag_pollution_output = np.zeros(self.n)  # → Pollution sector

        # ── COUPLING INPUTS ──
        self.pop = np.zeros(self.n)              # Population (from Population)
        self.ag_investment = np.zeros(self.n)    # Investment (from Capital)
        self.ppolx = np.zeros(self.n)            # Pollution index (from Pollution)

        # Initialize
        self._init_stocks()

    def _init_stocks(self):
        """Set initial values from parameters."""
        p = self.params
        self.al[0] = p.al_init
        self.lfert[0] = p.lfert_init
        self.climate_factor[0] = p.climate_base
        self.food_ratio[0] = 1.0

    # ──────────────────────────────────────────────────────────────
    # SECTOR UPDATE — called each timestep by the integrator
    # ──────────────────────────────────────────────────────────────

    def step(self, k: int, pop: float, ag_investment: float,
             ppolx: float = 1.0,
             climate_factor_override: float = None):
        """
        Advance agriculture sector by one timestep.

        Called by World3Integrator at each k. Receives coupling inputs
        from Population, Capital, and Pollution sectors.

        Args:
            k: Current timestep index
            pop: Total population (from Population sector) → demand
            ag_investment: $ invested in agriculture (from Capital) → inputs
            ppolx: Pollution index (from Pollution) → fertility loss
            climate_factor_override: If supplied (e.g. from a
                ClimateAgricultureBridge running an IPCC SSP scenario),
                replaces the simple internal linear climate model with the
                externally supplied value for this timestep.

        Stock updates (Euler integration):
            dAL/dt = land_development - land_erosion
            dLFERT/dt = fert_regen - fert_degrade
        """
        if k == 0:
            # Initialise k=0 with the actual coupling inputs from Capital and
            # Pollution rather than zeros. This keeps food_production[0]
            # consistent with subsequent years where the same coupling applies.
            self.pop[0] = pop
            self.ag_investment[0] = ag_investment
            self.ppolx[0] = ppolx
            self._calc_food(0, pop if pop > 0 else 1.0, ag_investment, ppolx,
                            climate_factor_override)
            return

        p = self.params
        dt = self.dt

        # Store coupling inputs
        self.pop[k] = pop
        self.ag_investment[k] = ag_investment
        self.ppolx[k] = ppolx

        # ── 1. LAND DYNAMICS ──
        # Development: bring new land into production
        remaining_land = max(0, p.al_max - self.al[k-1])
        self.land_development[k] = remaining_land * p.land_development_rate

        # Erosion: lose land to degradation
        # Erosion increases with pollution (World3 coupling)
        erosion_factor = 1.0 + 0.2 * max(0, ppolx - 1.0)
        self.land_erosion[k] = self.al[k-1] * p.land_erosion_rate * erosion_factor

        # Stock update: arable land
        self.al[k] = max(0, self.al[k-1] + dt * (
            self.land_development[k] - self.land_erosion[k]))

        # ── 2. LAND FERTILITY DYNAMICS ──
        # Natural regeneration (biological recovery)
        fert_gap = p.lfert_max - self.lfert[k-1]
        self.fert_regen[k] = max(0, fert_gap) / p.lfert_regen_time

        # Investment-driven improvement
        input_per_ha = ag_investment / max(1, self.al[k-1])
        investment_boost = input_per_ha * p.lfert_investment_response

        # Degradation from pollution
        # Reference: IPCC AR6 — pollution damages soil biology
        pollution_damage = self.lfert[k-1] * p.lfert_pollution_sensitivity * max(0, ppolx - 1.0)

        # Over-use degradation (intensification without sustainability)
        overuse = 0.0
        if input_per_ha > p.input_half_saturation * 2:
            overuse = self.lfert[k-1] * 0.005  # 0.5% degradation from over-use

        self.fert_degrade[k] = pollution_damage + overuse

        # Stock update: land fertility
        self.lfert[k] = np.clip(
            self.lfert[k-1] + dt * (self.fert_regen[k] + investment_boost - self.fert_degrade[k]),
            100.0,  # Minimum fertility (land never fully dead)
            p.lfert_max
        )

        # ── 3. FOOD PRODUCTION ──
        self._calc_food(k, pop, ag_investment, ppolx, climate_factor_override)

    def _calc_food(self, k: int, pop: float, ag_investment: float, ppolx: float,
                   climate_factor_override: float = None):
        """
        Calculate food production and derived outputs.

        food = arable_land × effective_yield
        effective_yield = lfert × input_multiplier × climate_factor × pollution_factor

        If climate_factor_override is supplied (e.g. from an IPCC SSP scenario
        via ClimateAgricultureBridge), it replaces the simple internal linear
        climate model.
        """
        p = self.params

        # years_elapsed is used by both the climate model below and by the
        # technology multiplier later; compute it once.
        years_elapsed = self.time[k] - self.year_start

        # Climate factor: either externally supplied (e.g. from an IPCC
        # SSP scenario via ClimateAgricultureBridge) or derived from the
        # simple internal linear model.
        if climate_factor_override is not None:
            self.climate_factor[k] = climate_factor_override
        else:
            # Climate damage only kicks in after 2000 (historical warming was
            # minimal before).
            climate_years = max(0, years_elapsed - 29)
            self.climate_factor[k] = max(
                0.6, p.climate_base - p.climate_sensitivity * climate_years)

        # Input intensity multiplier (diminishing returns from investment)
        # Reference: Meadows (1972) — land yield multiplier from inputs
        # Starts at 1.0 (no additional boost), increases with investment
        input_per_ha = ag_investment / max(1, self.al[k])
        self.input_intensity[k] = input_per_ha
        # Michaelis-Menten curve: adds 0 to (max-1) on top of base yield
        self.input_multiplier[k] = 1.0 + (p.input_intensity_max - 1.0) * (
            input_per_ha / (input_per_ha + p.input_half_saturation))

        # Pollution effect on yield
        # Reference: IPCC AR6 Ch.5 — ozone/pollution crop damage
        pollution_factor = max(0.5, 1.0 - p.pollution_yield_sensitivity * max(0, ppolx - 1.0))

        # Technology-driven yield growth (calibrated to match historical yields)
        # Canada: 1960 → 4079 kg/ha (1971-2023), Nigeria: 1050 → 1656 kg/ha
        # This is THE primary growth driver — already captures investment effects
        tech_multiplier = (1.0 + p.tech_yield_growth_rate) ** years_elapsed

        # Soil health: can only DEGRADE (from pollution). At full health = 1.0
        soil_factor = min(1.0, self.lfert[k] / max(1, p.lfert_init))

        # Input multiplier: only adds EXTRA yield from ABOVE-baseline investment
        # At baseline, this should be ~1.0 (no additional boost)
        # Only policy-driven increases in ag_investment produce gains
        effective_input_mult = 1.0 + (self.input_multiplier[k] - 1.0) * 0.3  # Damped

        # Effective yield = base × tech × soil × inputs × climate × pollution
        self.land_yield[k] = (p.lfert_init * tech_multiplier * soil_factor *
                              effective_input_mult *
                              self.climate_factor[k] * pollution_factor)

        # Total food production
        self.food_production[k] = self.al[k] * self.land_yield[k]

        # Per-capita food and food ratio
        pop_safe = max(1.0, pop)
        self.food_per_capita[k] = self.food_production[k] / pop_safe
        self.food_ratio[k] = self.food_per_capita[k] / p.subsistence_food_pc

        # Agricultural pollution output (fertilizer intensity → Pollution sector)
        # More intensive agriculture generates more pollution
        self.ag_pollution_output[k] = ag_investment * self.input_multiplier[k]

    # ──────────────────────────────────────────────────────────────
    # OUTPUT INTERFACE (for other sectors)
    # ──────────────────────────────────────────────────────────────

    def get_food_ratio(self, k: int) -> float:
        """
        Food ratio at timestep k.
        food_per_capita / subsistence_requirement.
        Used by Population (mortality) and Capital (allocation shift).
        """
        return self.food_ratio[k]

    def get_food_per_capita(self, k: int) -> float:
        """Food per capita [kg/person/year]. Used by Nutrition sector."""
        return self.food_per_capita[k]

    def get_ag_pollution(self, k: int) -> float:
        """Agricultural pollution output. Used by Pollution sector."""
        return self.ag_pollution_output[k]

    def get_results_df(self):
        """Return full results as DataFrame for dashboard display."""
        import pandas as pd
        return pd.DataFrame({
            'Year': self.time,
            'Arable_Land_ha': self.al,
            'Land_Fertility': self.lfert,
            'Food_Production_kg': self.food_production,
            'Food_Per_Capita': self.food_per_capita,
            'Food_Ratio': self.food_ratio,
            'Land_Yield_kg_ha': self.land_yield,
            'Input_Multiplier': self.input_multiplier,
            'Climate_Factor': self.climate_factor,
            'Pollution_Index_Input': self.ppolx,
            'AG_Investment_Input': self.ag_investment,
            'Land_Development': self.land_development,
            'Land_Erosion': self.land_erosion,
        })
