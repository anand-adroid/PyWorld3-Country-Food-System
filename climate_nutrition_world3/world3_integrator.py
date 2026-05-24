"""
World3 Integrator — Master coupling class for all five sectors.

This is the heart of the multi-level systems model. It instantiates all
five sectors and runs them in a coordinated timestep loop where each
sector's outputs feed into other sectors' inputs, creating the
bidirectional feedback loops that define World3-style system dynamics.

SECTOR COUPLING DIAGRAM:
    ┌───────────────────────────────────────────────────────────────────┐
    │                     World3 Integrator                            │
    │                                                                   │
    │  ┌────────────┐    pop, labor    ┌────────────┐                  │
    │  │ Population │ ──────────────→  │  Capital   │                  │
    │  │ (4 cohorts)│ ←────────────── │ (ic, sc)   │                  │
    │  └─────┬──────┘   hsapc          └─────┬──────┘                  │
    │        │ pop                           │ io, ag_inv               │
    │        │ food_ratio                    │ fioaa                    │
    │        ↓                              ↓                          │
    │  ┌────────────┐                ┌────────────┐                    │
    │  │ Pollution  │ ←── ag_poll ── │Agriculture │                    │
    │  │   (pp)     │ ──────────────→│ (al,lfert) │                    │
    │  └─────┬──────┘   ppolx        └─────┬──────┘                    │
    │        │                              │                          │
    │        │ ppolx                        │ food_pc, food_ratio       │
    │        ↓                              ↓                          │
    │  ┌────────────┐                ┌────────────┐                    │
    │  │ Population │                │ Nutrition  │                    │
    │  │ (mortality)│                │ (analysis) │                    │
    │  └────────────┘                └────────────┘                    │
    └───────────────────────────────────────────────────────────────────┘

FEEDBACK LOOPS (World3 style):
    B1 (Balancing — Food Investment):
        food_ratio ↓ → fioaa ↑ → ag_investment ↑ → food ↑ → food_ratio ↑
    B2 (Balancing — Population-Food):
        food_ratio ↓ → mortality ↑ → pop ↓ → demand ↓ → food_ratio ↑
    B3 (Balancing — Pollution Cleanup):
        pollution ↑ → absorption ↑ → pollution ↓
    B4 (Balancing — Fertility Response):
        food_ratio ↓ → fertility ↓ → births ↓ → pop ↓ → demand ↓
    R1 (Reinforcing — Population Growth):
        pop ↑ → births ↑ → pop ↑ (positive feedback)
    R2 (Reinforcing — Industrial Growth):
        ic ↑ → io ↑ → icir ↑ → ic ↑ (capital accumulation)
    R3 (Reinforcing — Pollution Accumulation):
        io ↑ → pollution ↑ → yield ↓ → food ↓ → more ag → more pollution

INTEGRATION METHOD:
    Euler integration with dt=1.0 year (World3 standard).
    Each timestep: all sectors update sequentially, using outputs
    from the previous timestep for coupling (explicit scheme).

References:
    - Meadows et al. (1972) Ch.7: The Complete World3 Model
    - Meadows et al. (2004) Ch.4: Model structure
    - Forrester (1961) Ch.6: System dynamics integration
    - Sterman (2000) Ch.13: Coupling subsystems
    - PyWorld3 (Vanwynsberghe 2021): world3.py master class
"""

import numpy as np
import pandas as pd

from .sectors.population_sector import (
    PopulationSector, PopulationParams,
    CANADA_POPULATION_PARAMS, NIGERIA_POPULATION_PARAMS
)
from .sectors.capital_sector import (
    CapitalSector, CapitalParams,
    CANADA_CAPITAL_PARAMS, NIGERIA_CAPITAL_PARAMS
)
from .sectors.agriculture_sector import (
    AgricultureSector, AgricultureParams,
    CANADA_AGRICULTURE_PARAMS, NIGERIA_AGRICULTURE_PARAMS
)
from .sectors.pollution_sector import (
    PollutionSector, PollutionParams,
    CANADA_POLLUTION_PARAMS, NIGERIA_POLLUTION_PARAMS
)
from .sectors.nutrition_sector import (
    NutritionSector, NutritionParams,
    CANADA_NUTRITION_PARAMS, NIGERIA_NUTRITION_PARAMS
)


# ─── COUNTRY PRESETS ──────────────────────────────────────────────

COUNTRY_PRESETS = {
    'canada': {
        'population': CANADA_POPULATION_PARAMS,
        'capital': CANADA_CAPITAL_PARAMS,
        'agriculture': CANADA_AGRICULTURE_PARAMS,
        'pollution': CANADA_POLLUTION_PARAMS,
        'nutrition': CANADA_NUTRITION_PARAMS,
    },
    'nigeria': {
        'population': NIGERIA_POPULATION_PARAMS,
        'capital': NIGERIA_CAPITAL_PARAMS,
        'agriculture': NIGERIA_AGRICULTURE_PARAMS,
        'pollution': NIGERIA_POLLUTION_PARAMS,
        'nutrition': NIGERIA_NUTRITION_PARAMS,
    },
}


class World3Integrator:
    """
    Master integrator that couples all five sectors per timestep.

    This class implements the World3-style multi-level system dynamics
    model following Meadows et al. (1972). Each sector is an independent
    module with its own stocks, flows, and parameters. The integrator
    connects them by passing outputs between sectors at each timestep.

    Usage:
        >>> model = World3Integrator.from_country('canada')
        >>> model.run()
        >>> results = model.get_all_results()
        >>> model.plot_overview()

    Or with custom parameters:
        >>> model = World3Integrator(
        ...     pop_params=my_pop_params,
        ...     cap_params=my_cap_params,
        ...     ag_params=my_ag_params,
        ...     pol_params=my_pol_params,
        ...     nut_params=my_nut_params,
        ... )
    """

    def __init__(self,
                 pop_params: PopulationParams = None,
                 cap_params: CapitalParams = None,
                 ag_params: AgricultureParams = None,
                 pol_params: PollutionParams = None,
                 nut_params: NutritionParams = None,
                 year_start: int = 1971,
                 year_end: int = 2100,
                 dt: float = 1.0,
                 climate_bridge=None):
        """
        Initialize the integrated World3 model.

        Args:
            pop_params: Population sector parameters
            cap_params: Capital sector parameters
            ag_params: Agriculture sector parameters
            pol_params: Pollution sector parameters
            nut_params: Nutrition sector parameters
            year_start: Simulation start year
            year_end: Simulation end year
            dt: Timestep [years] (default 1.0, World3 standard)
            climate_bridge: Optional ClimateAgricultureBridge. When supplied,
                the agriculture sector's simple linear climate model is
                replaced each year by the bridge's IPCC SSP-derived climate
                stress factor. Build with ClimateAgricultureBridge.for_canada
                or ClimateAgricultureBridge.for_nigeria with scenario in
                {'ssp126', 'ssp245', 'ssp370', 'ssp585'}.
        """
        self.year_start = year_start
        self.year_end = year_end
        self.dt = dt
        self.n = int((year_end - year_start) / dt) + 1
        self.time = np.linspace(year_start, year_end, self.n)
        self.climate_bridge = climate_bridge

        # Use defaults if not provided
        if pop_params is None:
            pop_params = PopulationParams()
        if cap_params is None:
            cap_params = CapitalParams()
        if ag_params is None:
            ag_params = AgricultureParams()
        if pol_params is None:
            pol_params = PollutionParams()
        if nut_params is None:
            nut_params = NutritionParams()

        # ── INSTANTIATE ALL FIVE SECTORS ──
        # Deep copy params to avoid shared-state bugs between model instances
        import copy
        self.population = PopulationSector(copy.deepcopy(pop_params), year_start, year_end, dt)
        self.capital = CapitalSector(copy.deepcopy(cap_params), year_start, year_end, dt)
        self.agriculture = AgricultureSector(copy.deepcopy(ag_params), year_start, year_end, dt)
        self.pollution = PollutionSector(copy.deepcopy(pol_params), year_start, year_end, dt)
        self.nutrition = NutritionSector(copy.deepcopy(nut_params), year_start, year_end, dt)

        self._has_run = False

    @classmethod
    def from_country(cls, country: str, year_start: int = 1971,
                     year_end: int = 2100, dt: float = 1.0,
                     climate_scenario: str = None):
        """
        Create a World3 model pre-calibrated for a specific country.

        Args:
            country: 'canada' or 'nigeria'
            year_start: Simulation start year
            year_end: Simulation end year
            dt: Timestep
            climate_scenario: Optional IPCC SSP scenario name. One of
                'ssp126', 'ssp245', 'ssp370', 'ssp585'. When supplied, the
                simulation uses a ClimateAgricultureBridge with the country's
                regional climate baseline and the chosen SSP trajectory. When
                None (default), the agriculture sector uses its simple
                linear climate model instead.

        Returns:
            World3Integrator instance with country-specific parameters

        Available countries and their data sources:
            canada — Statistics Canada, IRCC, Environment Canada
            nigeria — UN WPP, FAO FAOSTAT, NBS Nigeria, WHO
        """
        country = country.lower()
        if country not in COUNTRY_PRESETS:
            raise ValueError(f"Unknown country: {country}. "
                           f"Available: {list(COUNTRY_PRESETS.keys())}")

        preset = COUNTRY_PRESETS[country]

        bridge = None
        if climate_scenario:
            # Lazy import to avoid hard dependency when climate not used
            from .sectors.climate_agriculture_bridge import ClimateAgricultureBridge
            if country == 'canada':
                bridge = ClimateAgricultureBridge.for_canada(
                    scenario=climate_scenario,
                    year_start=year_start, year_end=year_end,
                )
            elif country == 'nigeria':
                bridge = ClimateAgricultureBridge.for_nigeria(
                    scenario=climate_scenario,
                    year_start=year_start, year_end=year_end,
                )

        return cls(
            pop_params=preset['population'],
            cap_params=preset['capital'],
            ag_params=preset['agriculture'],
            pol_params=preset['pollution'],
            nut_params=preset['nutrition'],
            year_start=year_start,
            year_end=year_end,
            dt=dt,
            climate_bridge=bridge,
        )

    # ──────────────────────────────────────────────────────────────
    # MAIN SIMULATION LOOP
    # ──────────────────────────────────────────────────────────────

    def run(self):
        """
        Run the coupled multi-level simulation.

        Integration scheme (explicit Euler, World3 standard):
        For each timestep k = 0, 1, ..., n-1:
            1. Population.step(k) — uses food_ratio[k-1], hsapc[k-1], ppolx[k-1]
            2. Capital.step(k)    — uses pop[k], labor[k], food_ratio[k-1]
            3. Agriculture.step(k) — uses pop[k], ag_inv[k], ppolx[k-1]
            4. Pollution.step(k)  — uses io[k], pop[k], ag_poll[k]
            5. Nutrition.step(k)  — uses food_pc[k], food_ratio[k]

        Coupling is one-timestep lagged (explicit scheme) to avoid
        algebraic loops. This is the standard World3 approach.

        Reference: Meadows (1972) Appendix A — Integration scheme
        """
        pop = self.population
        cap = self.capital
        ag = self.agriculture
        pol = self.pollution
        nut = self.nutrition

        for k in range(self.n):
            # Get coupling values from previous timestep (k-1)
            # At k=0, use initial/default values
            if k == 0:
                food_ratio_prev = 1.0
                hsapc_prev = 0.0
                ppolx_prev = pol.ppolx[0]
                io_prev = cap.ic[0] / cap.params.icor
                ag_inv_prev = io_prev * cap.params.fioaa_base
            else:
                food_ratio_prev = ag.get_food_ratio(k-1)
                hsapc_prev = cap.get_health_services_pc(k-1)
                ppolx_prev = pol.get_pollution_index(k-1)
                io_prev = cap.get_industrial_output(k-1)
                ag_inv_prev = cap.get_ag_investment(k-1)

            # ── STEP 1: POPULATION ──
            # Receives: food_ratio (Agriculture), hsapc (Capital), ppolx (Pollution)
            pop.step(k, food_ratio=food_ratio_prev,
                     health_services_pc=hsapc_prev,
                     pollution_index=ppolx_prev)

            # Get current population outputs
            current_pop = pop.get_population(k)
            current_labor = pop.get_labor_force(k)

            # ── STEP 2: CAPITAL ──
            # Receives: pop (Population), labor_force (Population), food_ratio (Agriculture)
            cap.step(k, pop=current_pop, labor_force=current_labor,
                     food_ratio=food_ratio_prev)

            # Get current capital outputs
            current_io = cap.get_industrial_output(k)
            current_ag_inv = cap.get_ag_investment(k)

            # ── STEP 3: AGRICULTURE ──
            # Receives: pop (Population), ag_investment (Capital), ppolx
            # (Pollution). If an IPCC climate bridge is attached, override
            # the simple linear climate model with the bridge's per-year
            # climate stress factor.
            climate_override = None
            if self.climate_bridge is not None:
                climate_override = self.climate_bridge.get_climate_factor(k)

            ag.step(k, pop=current_pop, ag_investment=current_ag_inv,
                    ppolx=ppolx_prev,
                    climate_factor_override=climate_override)

            # Get current agriculture outputs
            current_food_pc = ag.get_food_per_capita(k)
            current_food_ratio = ag.get_food_ratio(k)
            current_ag_poll = ag.get_ag_pollution(k)

            # ── STEP 4: POLLUTION ──
            # Receives: io (Capital), pop (Population), ag_pollution (Agriculture)
            pol.step(k, io=current_io, pop=current_pop,
                     ag_input=current_ag_poll)

            # ── STEP 5: NUTRITION ──
            # Receives: food_per_capita (Agriculture), food_ratio (Agriculture)
            nut.step(k, food_per_capita=current_food_pc,
                     food_ratio=current_food_ratio)

        self._has_run = True
        return self

    # ──────────────────────────────────────────────────────────────
    # RESULTS AND ANALYSIS
    # ──────────────────────────────────────────────────────────────

    def get_all_results(self) -> pd.DataFrame:
        """
        Get combined results from all sectors in a single DataFrame.

        Returns a wide-format DataFrame with all sector variables,
        prefixed by sector name for clarity.
        """
        if not self._has_run:
            raise RuntimeError("Must call run() before getting results")

        # Combine all sector DataFrames
        pop_df = self.population.get_results_df()
        cap_df = self.capital.get_results_df()
        ag_df = self.agriculture.get_results_df()
        pol_df = self.pollution.get_results_df()
        nut_df = self.nutrition.get_results_df()

        # Use Year as the merge key
        result = pop_df.copy()
        for df, prefix in [(cap_df, 'Cap'), (ag_df, 'Ag'),
                           (pol_df, 'Pol'), (nut_df, 'Nut')]:
            # Rename columns (except Year) to add prefix
            renamed = {}
            for col in df.columns:
                if col != 'Year':
                    renamed[col] = f"{prefix}_{col}"
            df_renamed = df.rename(columns=renamed)
            result = result.merge(df_renamed, on='Year', how='left')

        return result

    def get_summary(self) -> dict:
        """
        Get a summary of key model outputs at selected years.

        Returns dict with key metrics at start, 2000, 2025, 2050, 2100.
        """
        if not self._has_run:
            raise RuntimeError("Must call run() before getting summary")

        summary = {}
        for year in [self.year_start, 2000, 2025, 2050, 2100]:
            if year < self.year_start or year > self.year_end:
                continue
            k = int((year - self.year_start) / self.dt)
            if k >= self.n:
                continue
            summary[year] = {
                'population': self.population.pop[k],
                'industrial_output': self.capital.io[k],
                'food_ratio': self.agriculture.food_ratio[k],
                'pollution_index': self.pollution.ppolx[k],
                'life_expectancy': self.population.life_exp[k],
                'food_security': self.nutrition.food_security_index[k],
                'stunting_risk': self.nutrition.stunting_risk[k],
                'arable_land': self.agriculture.al[k],
                'land_fertility': self.agriculture.lfert[k],
            }
        return summary

    def print_summary(self):
        """Print formatted summary of model results."""
        if not self._has_run:
            raise RuntimeError("Must call run() before printing summary")

        summary = self.get_summary()
        print("\n" + "="*70)
        print("WORLD3 INTEGRATED MODEL — SIMULATION RESULTS")
        print("="*70)

        header = f"{'Metric':<25}"
        for year in sorted(summary.keys()):
            header += f"{year:>12}"
        print(header)
        print("-"*70)

        metrics = [
            ('Population (M)', 'population', 1e-6, '{:>12.1f}'),
            ('Ind. Output ($B/yr)', 'industrial_output', 1e-9, '{:>12.1f}'),
            ('Food Ratio', 'food_ratio', 1, '{:>12.2f}'),
            ('Pollution Index', 'pollution_index', 1, '{:>12.2f}'),
            ('Life Expect. (yr)', 'life_expectancy', 1, '{:>12.1f}'),
            ('Food Security', 'food_security', 1, '{:>12.2f}'),
            ('Stunting Risk', 'stunting_risk', 1, '{:>12.2f}'),
            ('Arable Land (Mha)', 'arable_land', 1e-6, '{:>12.1f}'),
            ('Land Fertility', 'land_fertility', 1, '{:>12.0f}'),
        ]

        for label, key, scale, fmt in metrics:
            row = f"{label:<25}"
            for year in sorted(summary.keys()):
                val = summary[year][key] * scale
                row += fmt.format(val)
            print(row)

        print("="*70)

    # ──────────────────────────────────────────────────────────────
    # VISUALIZATION
    # ──────────────────────────────────────────────────────────────

    def plot_overview(self, save_path: str = None):
        """
        Plot 6-panel overview of all sectors.

        Panels:
            1. Population (4 cohorts stacked)
            2. Capital (IC, SC)
            3. Food Production & Food Ratio
            4. Pollution Index
            5. Nutrition (calorie/protein adequacy)
            6. Key feedback variables
        """
        import matplotlib.pyplot as plt

        if not self._has_run:
            raise RuntimeError("Must call run() before plotting")

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        time = self.time

        # Panel 1: Population
        ax = axes[0, 0]
        ax.stackplot(time,
                     self.population.p1 / 1e6,
                     self.population.p2 / 1e6,
                     self.population.p3 / 1e6,
                     self.population.p4 / 1e6,
                     labels=['0-14', '15-44', '45-64', '65+'],
                     alpha=0.7)
        ax.set_title('Population by Age Cohort')
        ax.set_ylabel('Millions')
        ax.legend(loc='upper left', fontsize=8)

        # Panel 2: Capital
        ax = axes[0, 1]
        ax.plot(time, self.capital.ic / 1e9, label='Industrial Capital', linewidth=2)
        ax.plot(time, self.capital.sc / 1e9, label='Service Capital', linewidth=2)
        ax.plot(time, self.capital.io / 1e9, '--', label='Industrial Output', alpha=0.7)
        ax.set_title('Capital & Output')
        ax.set_ylabel('Billion $')
        ax.legend(fontsize=8)

        # Panel 3: Food
        ax = axes[0, 2]
        ax.plot(time, self.agriculture.food_ratio, 'g-', linewidth=2, label='Food Ratio')
        ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Subsistence')
        ax.set_title('Food Adequacy')
        ax.set_ylabel('Food Ratio (1.0 = adequate)')
        ax.legend(fontsize=8)

        # Panel 4: Pollution
        ax = axes[1, 0]
        ax.plot(time, self.pollution.ppolx, 'r-', linewidth=2)
        ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='1970 Level')
        ax.set_title('Pollution Index')
        ax.set_ylabel('Relative to 1970')
        ax.legend(fontsize=8)

        # Panel 5: Nutrition
        ax = axes[1, 1]
        ax.plot(time, self.nutrition.calorie_adequacy, label='Calorie Adequacy', linewidth=2)
        ax.plot(time, self.nutrition.protein_adequacy, label='Protein Adequacy', linewidth=2)
        ax.plot(time, self.nutrition.food_security_index, '--', label='Food Security', alpha=0.7)
        ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.3)
        ax.set_title('Nutrition Outcomes')
        ax.set_ylabel('Adequacy Ratio')
        ax.legend(fontsize=8)

        # Panel 6: Feedback Loop Indicators
        ax = axes[1, 2]
        ax.plot(time, self.capital.fioaa * 100, label='% to Agriculture', linewidth=2)
        ax.plot(time, self.population.life_exp, label='Life Expectancy', linewidth=2)
        ax.plot(time, self.agriculture.lfert / 100, '--', label='Fertility/100', alpha=0.7)
        ax.set_title('Feedback Indicators')
        ax.legend(fontsize=8)

        for ax_row in axes:
            for ax in ax_row:
                ax.set_xlabel('Year')
                ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        return fig


# ──────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ──────────────────────────────────────────────────────────────────

def run_scenario(country: str = 'canada',
                 year_start: int = 1971,
                 year_end: int = 2100,
                 climate_scenario: str = None,
                 **param_overrides) -> World3Integrator:
    """
    Quick-run a country scenario with optional parameter overrides.

    Args:
        country: 'canada' or 'nigeria'
        year_start: Start year
        year_end: End year
        climate_scenario: Optional IPCC SSP scenario ('ssp126', 'ssp245',
            'ssp370', 'ssp585'). When supplied, agriculture uses the IPCC
            climate bridge instead of the simple linear climate model.
        **param_overrides: Override any sector parameter, e.g.:
            total_fertility_rate=3.0 (overrides Population params)
            icor=4.0 (overrides Capital params)

    Returns:
        World3Integrator instance (already run)

    Example:
        >>> model = run_scenario('nigeria', year_end=2050,
        ...                     total_fertility_rate=4.0,
        ...                     climate_scenario='ssp585')
        >>> model.print_summary()
    """
    model = World3Integrator.from_country(country, year_start, year_end,
                                          climate_scenario=climate_scenario)

    # Apply parameter overrides to relevant sectors
    pop_attrs = vars(model.population.params)
    cap_attrs = vars(model.capital.params)
    ag_attrs = vars(model.agriculture.params)
    pol_attrs = vars(model.pollution.params)
    nut_attrs = vars(model.nutrition.params)

    for key, val in param_overrides.items():
        if key in pop_attrs:
            setattr(model.population.params, key, val)
        elif key in cap_attrs:
            setattr(model.capital.params, key, val)
        elif key in ag_attrs:
            setattr(model.agriculture.params, key, val)
        elif key in pol_attrs:
            setattr(model.pollution.params, key, val)
        elif key in nut_attrs:
            setattr(model.nutrition.params, key, val)
        else:
            print(f"Warning: Unknown parameter '{key}' — ignored")

    model.run()
    return model
