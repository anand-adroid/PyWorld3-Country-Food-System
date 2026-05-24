"""
Pollution Sector — World3-style persistent pollution dynamics.

Models the accumulation of persistent pollution from industrial activity
and agricultural fertilizer runoff, with absorption by the environment.

STATE VARIABLES (Stocks):
    pp[k] — Persistent pollution [pollution units]

FLOW VARIABLES (Rates):
    pp_gen[k]  — Pollution generation rate [units/year]
    pp_abs[k]  — Pollution absorption rate [units/year]

FEEDBACK FROM OTHER SECTORS:
    io[k]       — from Capital → industrial pollution generation
    pop[k]      — from Population → per-capita normalization
    ag_input[k] — from Agriculture → fertilizer/chemical runoff

OUTPUTS TO OTHER SECTORS:
    ppolx[k] — Persistent pollution index (ratio to 1970 level)
               → Agriculture (yield reduction)
               → Population (life expectancy reduction)

References:
    - Meadows et al. (1972) Ch.5: Pollution Sector, pp.478-502
    - Meadows et al. (2004) Limits to Growth: 30-Year Update
    - Sterman (2000) Ch.12: Environmental systems
    - IPCC AR6 WGII Ch.5 (2022): Food systems and pollution
    - PyWorld3 (Vanwynsberghe 2021): pollution.py

Data Sources:
    - Canada pollution: Environment Canada — National Pollutant Release Inventory
    - Nigeria pollution: WHO Ambient Air Quality Database
    - Fertilizer use: FAO FAOSTAT Inputs/Fertilizers
    - Pollution indices: World Bank — PM2.5 mean annual exposure
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class PollutionParams:
    """
    Pollution sector parameters.

    Reference values:
        World3: Meadows (1972) Table 5-1
        Country-specific: WHO, FAO, Environment Canada
    """
    # Initial persistent pollution [pollution units]
    pp_init: float = 2.5e7

    # Pollution generation from industry
    # pp_gen_industrial = (io / io_reference) × ppgio_norm × pp_reference
    # Normalized: when io = io_reference, industrial pollution = ppgio_norm × pp_reference
    # Source: Meadows (1972) eq. 5-1
    ppgio_norm: float = 0.03      # Fraction of reference pollution from industry at base IO
    io_reference: float = 67e9    # Reference industrial output [$/year] for normalization

    # Pollution generation from agriculture (fertilizer runoff)
    # Normalized similarly: ag_poll / ag_ref × ppgao_norm × pp_reference
    # Source: FAO — nitrogen surplus, IPCC AR6 Ch5
    ppgao_norm: float = 0.02      # Fraction of reference pollution from agriculture at base
    ag_reference: float = 5e9     # Reference agricultural pollution output

    # Pollution absorption parameters
    # Environment absorbs pollution at a rate that decreases as pp accumulates
    # Reference: Meadows (1972) eq. 5-3
    pp_absorption_time: float = 20.0    # Years to absorb at normal level
    pp_absorption_saturation: float = 2.0  # Multiplier of pp_reference where absorption halves

    # Reference pollution level (1970)
    # Used to compute ppolx = pp / pp_reference
    pp_reference_1970: float = 2.5e7

    # Technology improvement — reduces pollution intensity over time
    # Reference: Meadows (2004) — technology scenario
    pollution_intensity_decline: float = 0.005  # 0.5%/year reduction in ppgio

    # Agricultural pollution fraction (how much of ag input becomes pollution)
    # Source: IPCC AR6 — nitrogen use efficiency ~50%, rest is runoff
    ag_pollution_fraction: float = 0.20   # 20% of fertilizer input → pollution

    # Population-related waste
    # Source: World Bank — solid waste per capita
    # Normalized: small relative to industrial/ag pollution
    waste_per_capita: float = 0.01        # pollution units per person per year


# ─── COUNTRY PRESETS ──────────────────────────────────────────────

CANADA_POLLUTION_PARAMS = PollutionParams(
    # Environment Canada — NPRI
    # Canada 1971: moderate pollution, strong environmental regulation post-1990
    pp_init=1.0e7,                # Normalized pollution units (baseline = 1.0)
    ppgio_norm=0.02,
    io_reference=67e9,            # 1971 IO
    ppgao_norm=0.01,
    ag_reference=3.3e9,
    pp_absorption_time=12.0,      # Good environmental capacity
    pp_absorption_saturation=3.0,
    pp_reference_1970=1.0e7,
    pollution_intensity_decline=0.012,  # Strong: Canada adopted cleaner tech
    ag_pollution_fraction=0.12,
    waste_per_capita=0.01,
)

NIGERIA_POLLUTION_PARAMS = PollutionParams(
    # WHO / FAO — Nigeria
    # Nigeria 1971: low industrial pollution, but growing (oil flaring, industry)
    pp_init=3.0e6,                # Low initial (pre-oil boom)
    ppgio_norm=0.008,             # Moderate — most industry is oil (localized)
    io_reference=4.3e9,           # 1971 IO
    ppgao_norm=0.005,             # Low fertilizer use = low ag pollution
    ag_reference=0.5e9,
    pp_absorption_time=15.0,      # Tropical: faster biological decomposition
    pp_absorption_saturation=3.0,
    pp_reference_1970=3.0e6,
    pollution_intensity_decline=0.003,  # Slow adoption of clean tech
    ag_pollution_fraction=0.15,
    waste_per_capita=0.001,
)


class PollutionSector:
    """
    World3-style persistent pollution sector.

    Models pollution as a stock that accumulates from industrial and
    agricultural sources and is absorbed by the environment. When
    pollution exceeds the environment's capacity, absorption slows
    and the pollution index rises — affecting agriculture (yield) and
    population (health).

    Stock-Flow Structure:
        ┌────────────────────────────────┐
        │    Persistent Pollution (pp)   │
        └────────┬───────────────┬───────┘
                 ↑               ↓
            pp_gen[k]       pp_abs[k]
                 │               │
                 │               └── pp / absorption_time(pp)
                 │
                 ├── io × ppgio × technology_factor
                 ├── ag_input × ag_pollution_fraction
                 └── pop × waste_per_capita

        Output: ppolx = pp / pp_reference_1970
        (Normalized index: 1.0 = 1970 level)

    Key Feedback Loops:
        R1 (reinforcing): More industry → more pollution → reduced ag yield
            → food shortage → more industrial allocation to agriculture
        B2 (balancing): High pollution → reduced population → less industry
            → less pollution
    """

    def __init__(self, params: PollutionParams, year_start: int = 1971,
                 year_end: int = 2100, dt: float = 1.0):
        self.params = params
        self.year_start = year_start
        self.year_end = year_end
        self.dt = dt
        self.n = int((year_end - year_start) / dt) + 1
        self.time = np.linspace(year_start, year_end, self.n)

        # ── STATE VARIABLE (Stock) ──
        self.pp = np.zeros(self.n)              # Persistent pollution

        # ── FLOW VARIABLES ──
        self.pp_gen = np.zeros(self.n)          # Generation rate
        self.pp_abs = np.zeros(self.n)          # Absorption rate
        self.pp_gen_industry = np.zeros(self.n) # From industry
        self.pp_gen_agriculture = np.zeros(self.n)  # From agriculture
        self.pp_gen_waste = np.zeros(self.n)    # From population waste

        # ── OUTPUT VARIABLES ──
        self.ppolx = np.zeros(self.n)           # Pollution index (norm to 1970)
        self.absorption_time = np.zeros(self.n) # Effective absorption time

        # ── COUPLING INPUTS ──
        self.io = np.zeros(self.n)              # Industrial output (from Capital)
        self.pop = np.zeros(self.n)             # Population (from Population)
        self.ag_input = np.zeros(self.n)        # Agricultural input intensity

        # Initialize
        self._init_stocks()

    def _init_stocks(self):
        """Set initial values from parameters."""
        p = self.params
        self.pp[0] = p.pp_init
        self.ppolx[0] = p.pp_init / p.pp_reference_1970

    # ──────────────────────────────────────────────────────────────
    # SECTOR UPDATE — called each timestep by the integrator
    # ──────────────────────────────────────────────────────────────

    def step(self, k: int, io: float, pop: float,
             ag_input: float = 0.0):
        """
        Advance pollution by one timestep.

        Called by World3Integrator at each k. Receives coupling inputs
        from Capital, Population, and Agriculture sectors.

        Args:
            k: Current timestep index
            io: Industrial output [$/year] (from Capital sector)
            pop: Total population (from Population sector)
            ag_input: Agricultural input intensity (from Agriculture)
                     Represents fertilizer/chemical use level

        Stock update (Euler integration):
            dPP/dt = pp_gen - pp_abs
            pp_gen = industrial + agricultural + waste
            pp_abs = pp / effective_absorption_time
        """
        if k == 0:
            return

        p = self.params
        dt = self.dt

        # Store coupling inputs
        self.io[k] = io
        self.pop[k] = pop
        self.ag_input[k] = ag_input

        # ── 1. TECHNOLOGY FACTOR ──
        # Pollution intensity declines over time as technology improves
        years_elapsed = self.time[k] - self.year_start
        tech_factor = max(0.3, 1.0 - p.pollution_intensity_decline * years_elapsed)

        # ── 2. POLLUTION GENERATION (normalized to reference levels) ──
        # Industrial pollution: normalized so that at io=io_reference,
        # generation = ppgio_norm × pp_reference
        io_ratio = io / max(1, p.io_reference)
        self.pp_gen_industry[k] = io_ratio * p.ppgio_norm * p.pp_reference_1970 * tech_factor

        # Agricultural pollution (fertilizer runoff)
        ag_ratio = ag_input / max(1, p.ag_reference)
        self.pp_gen_agriculture[k] = ag_ratio * p.ppgao_norm * p.pp_reference_1970

        # Population waste (small contribution, normalized)
        self.pp_gen_waste[k] = pop * p.waste_per_capita * tech_factor

        # Total generation
        self.pp_gen[k] = (self.pp_gen_industry[k] +
                          self.pp_gen_agriculture[k] +
                          self.pp_gen_waste[k])

        # ── 3. POLLUTION ABSORPTION ──
        # Absorption slows as pollution accumulates (environment saturates)
        # Reference: Meadows (1972) — absorption time increases with pp level
        # saturation_level = pp_reference × pp_absorption_saturation
        saturation_level = p.pp_reference_1970 * p.pp_absorption_saturation
        pp_ratio = self.pp[k-1] / max(1, saturation_level)
        effective_abs_time = p.pp_absorption_time * (1.0 + pp_ratio)
        self.absorption_time[k] = effective_abs_time

        self.pp_abs[k] = self.pp[k-1] / effective_abs_time

        # ── 4. STOCK UPDATE (Euler integration) ──
        self.pp[k] = max(0, self.pp[k-1] + dt * (self.pp_gen[k] - self.pp_abs[k]))

        # ── 5. POLLUTION INDEX ──
        # Normalized to 1970 reference level
        self.ppolx[k] = self.pp[k] / max(1, p.pp_reference_1970)

    # ──────────────────────────────────────────────────────────────
    # OUTPUT INTERFACE (for other sectors)
    # ──────────────────────────────────────────────────────────────

    def get_pollution_index(self, k: int) -> float:
        """
        Persistent pollution index at timestep k.
        Used by Agriculture (yield reduction) and Population (health).
        Value of 1.0 = 1970 level, >1 means worse than 1970.
        """
        return self.ppolx[k]

    def get_results_df(self):
        """Return full results as DataFrame for dashboard display."""
        import pandas as pd
        return pd.DataFrame({
            'Year': self.time,
            'Persistent_Pollution': self.pp,
            'Pollution_Index': self.ppolx,
            'PP_Generation': self.pp_gen,
            'PP_Absorption': self.pp_abs,
            'PP_From_Industry': self.pp_gen_industry,
            'PP_From_Agriculture': self.pp_gen_agriculture,
            'PP_From_Waste': self.pp_gen_waste,
            'Absorption_Time': self.absorption_time,
        })
