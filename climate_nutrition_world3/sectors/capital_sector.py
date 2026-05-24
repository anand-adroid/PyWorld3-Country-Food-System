"""
Capital Sector — World3-style industrial & service capital dynamics.

Follows Meadows et al. (1972) capital structure with allocation logic that
directs industrial output toward agriculture when food is scarce.

STATE VARIABLES (Stocks):
    ic[k] — Industrial capital [dollars]
    sc[k] — Service capital [dollars]

FLOW VARIABLES (Rates):
    icir[k] — Industrial capital investment rate [$/year]
    icdr[k] — Industrial capital depreciation rate [$/year]
    scir[k] — Service capital investment rate [$/year]
    scdr[k] — Service capital depreciation rate [$/year]

FEEDBACK FROM OTHER SECTORS:
    pop[k]         — from Population → labor force, per-capita normalization
    labor_force[k] — from Population → capital utilization
    food_ratio[k]  — from Agriculture → shifts allocation toward agriculture

OUTPUTS TO OTHER SECTORS:
    io[k]           — Industrial output → Agriculture (investment), Pollution (generation)
    iopc[k]         — Industrial output per capita → general development proxy
    fioaa[k]        — Fraction of IO allocated to agriculture → Agriculture sector
    hsapc[k]        — Health services per capita → Population (life expectancy)
    ag_investment[k] — Agricultural investment = io × fioaa → Agriculture

References:
    - Meadows et al. (1972) Ch.4: Capital Sector, pp.253-270
    - Meadows et al. (2004) Limits to Growth: 30-Year Update, Ch.4
    - Sterman (2000) Ch.10: Capital investment and economic growth
    - Forrester (1961) Industrial Dynamics, Ch.14
    - PyWorld3 (Vanwynsberghe 2021): capital.py

Data Sources:
    - Canada GDP/capital: Statistics Canada Table 36-10-0222-01
    - Nigeria GDP/capital: World Bank WDI (NY.GDP.MKTP.CD)
    - Capital-output ratios: Penn World Table 10.01
    - Health expenditure: WHO Global Health Expenditure Database
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class CapitalParams:
    """
    Capital sector parameters.

    Reference values:
        World3 standard run: Meadows (1972) Table 4-1
        Canada: Statistics Canada, Penn World Table 10.01
        Nigeria: World Bank WDI, Penn World Table 10.01
    """
    # Initial capital stocks [dollars]
    ic_init: float = 2.1e11       # Industrial capital initial
    sc_init: float = 1.44e11      # Service capital initial

    # Capital-output ratios [years]
    # Ratio of capital stock to annual output (higher = less productive)
    # Source: Penn World Table — capital/output ratio
    icor: float = 3.0             # Industrial capital-output ratio
    scor: float = 1.0             # Service capital-output ratio

    # Capital lifetimes [years]
    # Average lifetime before depreciation
    # Source: Statistics Canada / World Bank depreciation schedules
    alic: float = 14.0            # Average lifetime of industrial capital
    alsc: float = 20.0            # Average lifetime of service capital

    # Allocation fractions (sum must be < 1.0)
    # Source: World3 standard run, adjusted for country
    fioaa_base: float = 0.12      # Fraction of IO allocated to agriculture (base)
    fioai_base: float = 0.43      # Fraction of IO allocated to industry (reinvestment)
    fioas_base: float = 0.22      # Fraction of IO allocated to services
    fioac_base: float = 0.23      # Fraction of IO allocated to consumption

    # Food scarcity response — increases ag allocation when food_ratio < 1
    # Reference: Meadows (1972) "fraction of IO to agriculture" table function
    fioaa_max: float = 0.40       # Maximum allocation to agriculture in crisis
    food_allocation_sensitivity: float = 2.0  # How fast ag allocation responds

    # Health services fraction (from service output)
    # Source: WHO — health expenditure as % of GDP
    health_fraction_of_services: float = 0.30  # 30% of service output → health

    # Labor productivity parameters
    # Source: Sterman (2000) eq. 10-15
    labor_participation_fraction: float = 0.75  # fraction of labor force employed
    labor_output_ratio: float = 1.0             # output per labor unit


# ─── COUNTRY PRESETS ──────────────────────────────────────────────

CANADA_CAPITAL_PARAMS = CapitalParams(
    # Statistics Canada / Penn World Table 10.01
    # Canada GDP 1971: ~$100B USD → 2023: ~$2.14T (21× growth in 52 years)
    # Capital stock ~3× GDP
    ic_init=200e9,            # Industrial capital 1971 ~$200B
    sc_init=100e9,            # Service capital 1971 ~$100B
    icor=3.0,                 # Penn World Table — Canada ICOR ~3
    scor=1.2,
    alic=14.0,
    alsc=20.0,
    fioaa_base=0.05,          # Canada: only 5% to agriculture
    fioai_base=0.45,
    fioas_base=0.27,
    fioac_base=0.23,
    fioaa_max=0.15,           # Even in crisis, max 15%
    food_allocation_sensitivity=1.0,
    health_fraction_of_services=0.35,
    labor_participation_fraction=0.78,
)

NIGERIA_CAPITAL_PARAMS = CapitalParams(
    # World Bank WDI — Nigeria 1971
    # Nigeria GDP 1971: ~$11.1B → 2023: ~$363B (33× growth, oil-driven)
    # Capital stock ~2× GDP
    ic_init=15e9,             # Industrial capital ~$15B (including oil infrastructure)
    sc_init=7e9,              # Service capital ~$7B
    icor=3.5,                 # Moderate efficiency (oil sector is efficient)
    scor=1.5,
    alic=12.0,
    alsc=18.0,
    fioaa_base=0.12,         # Nigeria: 12% to agriculture (declining — oil dominates)
    fioai_base=0.40,         # Oil reinvestment
    fioas_base=0.23,
    fioac_base=0.25,
    fioaa_max=0.35,          # In crisis, up to 35% to agriculture
    food_allocation_sensitivity=2.0,
    health_fraction_of_services=0.10,  # Nigeria: only ~4% of GDP on health
    labor_participation_fraction=0.55,  # Lower formal participation
)


class CapitalSector:
    """
    World3-style capital sector with industrial/service subsystems.

    Architecture follows Meadows (1972) with key feedback:
        - Food shortage → increases fraction allocated to agriculture
        - Industrial output → funds agricultural investment + pollution
        - Service output → provides health services → Population

    Stock-Flow Structure:
        ┌──────────────────┐                     ┌──────────────────┐
        │ Industrial Cap   │                     │ Service Capital  │
        │      (ic)        │                     │      (sc)        │
        └────┬────┬────────┘                     └────┬────┬────────┘
             │    │                                    │    │
        icir ↑    ↓ icdr                          scir ↑    ↓ scdr
             │    │                                    │    │
             │    └── ic / alic                        │    └── sc / alsc
             │                                        │
             └── io × fioai                           └── io × fioas

        Industrial Output:  io = ic / icor × capital_utilization
        Service Output:     so = sc / scor
        AG Investment:      ag_inv = io × fioaa(food_ratio)
        Health Services:    hsapc = so × health_fraction / pop

    Key Feedback Loop (B3 in World3):
        food_ratio ↓ → fioaa ↑ → more ag investment → more food → food_ratio ↑
    """

    def __init__(self, params: CapitalParams, year_start: int = 1971,
                 year_end: int = 2100, dt: float = 1.0):
        self.params = params
        self.year_start = year_start
        self.year_end = year_end
        self.dt = dt
        self.n = int((year_end - year_start) / dt) + 1
        self.time = np.linspace(year_start, year_end, self.n)

        # ── STATE VARIABLES (Stocks) ──
        self.ic = np.zeros(self.n)              # Industrial capital [$]
        self.sc = np.zeros(self.n)              # Service capital [$]

        # ── FLOW VARIABLES (Rates) ──
        self.icir = np.zeros(self.n)            # Industrial capital investment rate
        self.icdr = np.zeros(self.n)            # Industrial capital depreciation rate
        self.scir = np.zeros(self.n)            # Service capital investment rate
        self.scdr = np.zeros(self.n)            # Service capital depreciation rate

        # ── OUTPUT VARIABLES ──
        self.io = np.zeros(self.n)              # Industrial output [$/year]
        self.so = np.zeros(self.n)              # Service output [$/year]
        self.iopc = np.zeros(self.n)            # Industrial output per capita
        self.sopc = np.zeros(self.n)            # Service output per capita
        self.hsapc = np.zeros(self.n)           # Health services per capita
        self.ag_investment = np.zeros(self.n)   # Agricultural investment [$/year]

        # ── ALLOCATION FRACTIONS ──
        self.fioaa = np.zeros(self.n)           # Fraction to agriculture
        self.fioai = np.zeros(self.n)           # Fraction to industry
        self.fioas = np.zeros(self.n)           # Fraction to services
        self.fioac = np.zeros(self.n)           # Fraction to consumption

        # ── COUPLING INPUTS ──
        self.pop = np.zeros(self.n)             # Total population (from Population)
        self.labor_force = np.zeros(self.n)     # Working-age pop (from Population)
        self.food_ratio = np.ones(self.n)       # Food adequacy (from Agriculture)

        # Initialize
        self._init_stocks()

    def _init_stocks(self):
        """Set initial values from parameters."""
        p = self.params
        self.ic[0] = p.ic_init
        self.sc[0] = p.sc_init
        self.fioaa[0] = p.fioaa_base
        self.fioai[0] = p.fioai_base
        self.fioas[0] = p.fioas_base
        self.fioac[0] = p.fioac_base

    # ──────────────────────────────────────────────────────────────
    # SECTOR UPDATE — called each timestep by the integrator
    # ──────────────────────────────────────────────────────────────

    def step(self, k: int, pop: float, labor_force: float,
             food_ratio: float = 1.0):
        """
        Advance capital sector by one timestep.

        Called by World3Integrator at each k. Receives coupling inputs
        from Population and Agriculture sectors.

        Args:
            k: Current timestep index
            pop: Total population (from Population sector)
            labor_force: Working-age population (from Population sector)
            food_ratio: food_per_capita / subsistence (from Agriculture)
                       Controls allocation shift toward agriculture

        Stock updates (Euler integration):
            dIC/dt = icir - icdr = io × fioai - ic / alic
            dSC/dt = scir - scdr = io × fioas - sc / alsc
        """
        if k == 0:
            # Compute initial industrial output and outputs
            self.pop[0] = pop
            self.labor_force[0] = labor_force
            self.io[0] = self.ic[0] / self.params.icor
            self.so[0] = self.sc[0] / self.params.scor
            self.fioaa[0] = self.params.fioaa_base
            self._calc_outputs(0, pop if pop > 0 else 1.0)
            return

        p = self.params
        dt = self.dt

        # Store coupling inputs
        self.pop[k] = pop
        self.labor_force[k] = labor_force
        self.food_ratio[k] = food_ratio

        # ── 1. CAPITAL UTILIZATION ──
        # In World3, capital utilization depends on labor availability
        # capital_utilization = min(1.0, labor_force / required_labor)
        # Simplified: assume full utilization (World3 standard run)
        cap_util = min(1.0, labor_force * p.labor_participation_fraction /
                       max(1, self.ic[k-1] / 50000))  # ~50k capital per worker
        cap_util = max(0.5, cap_util)  # Floor at 50%

        # ── 2. INDUSTRIAL OUTPUT ──
        # io = ic / icor × capital_utilization
        # Reference: Meadows (1972) eq. 4-1
        self.io[k] = (self.ic[k-1] / p.icor) * cap_util

        # ── 3. ALLOCATION FRACTIONS ──
        # Food shortage shifts allocation toward agriculture
        # Reference: Meadows (1972) Table 4-3 "FIOAA vs food_ratio"
        self._calc_allocation(k, food_ratio)

        # ── 4. CAPITAL INVESTMENT AND DEPRECIATION ──
        # Industrial capital
        self.icir[k] = self.io[k] * self.fioai[k]
        self.icdr[k] = self.ic[k-1] / p.alic

        # Service capital
        self.scir[k] = self.io[k] * self.fioas[k]
        self.scdr[k] = self.sc[k-1] / p.alsc

        # ── 5. STOCK UPDATES (Euler integration) ──
        self.ic[k] = max(0, self.ic[k-1] + dt * (self.icir[k] - self.icdr[k]))
        self.sc[k] = max(0, self.sc[k-1] + dt * (self.scir[k] - self.scdr[k]))

        # ── 6. SERVICE OUTPUT ──
        self.so[k] = self.sc[k] / p.scor

        # ── 7. OUTPUTS FOR OTHER SECTORS ──
        self._calc_outputs(k, pop)

    def _calc_allocation(self, k: int, food_ratio: float):
        """
        Calculate allocation fractions based on food adequacy.

        World3 feedback loop B3: when food is scarce, society shifts
        more industrial output toward agriculture.

        Reference: Meadows (1972) Table 4-3 — FIOAA table function
        Shape: sigmoid response, fioaa rises as food_ratio falls below 1.0

        When food_ratio = 1.0: normal allocation (fioaa_base)
        When food_ratio = 0.5: emergency allocation (fioaa approaches fioaa_max)
        """
        p = self.params

        if food_ratio >= 1.0:
            # Adequate food — normal allocation
            self.fioaa[k] = p.fioaa_base
        else:
            # Food shortage — increase agricultural allocation
            # Nonlinear: more aggressive response as shortage worsens
            shortage = (1.0 - food_ratio)
            shift = (p.fioaa_max - p.fioaa_base) * min(1.0,
                    shortage * p.food_allocation_sensitivity)
            self.fioaa[k] = p.fioaa_base + shift

        # Remaining allocation (proportionally adjusted)
        remaining = 1.0 - self.fioaa[k]
        base_non_ag = p.fioai_base + p.fioas_base + p.fioac_base
        if base_non_ag > 0:
            self.fioai[k] = remaining * (p.fioai_base / base_non_ag)
            self.fioas[k] = remaining * (p.fioas_base / base_non_ag)
            self.fioac[k] = remaining * (p.fioac_base / base_non_ag)
        else:
            self.fioai[k] = remaining / 3
            self.fioas[k] = remaining / 3
            self.fioac[k] = remaining / 3

    def _calc_outputs(self, k: int, pop: float):
        """Calculate per-capita outputs and inter-sector deliverables."""
        p = self.params
        pop_safe = max(1.0, pop)

        # Per-capita metrics
        self.iopc[k] = self.io[k] / pop_safe
        self.sopc[k] = self.so[k] / pop_safe

        # Agricultural investment (→ Agriculture sector)
        self.ag_investment[k] = self.io[k] * self.fioaa[k]

        # Health services per capita (→ Population sector)
        # Health comes from service output
        self.hsapc[k] = (self.so[k] * p.health_fraction_of_services) / pop_safe

    # ──────────────────────────────────────────────────────────────
    # OUTPUT INTERFACE (for other sectors)
    # ──────────────────────────────────────────────────────────────

    def get_industrial_output(self, k: int) -> float:
        """Industrial output at timestep k. Used by Pollution sector."""
        return self.io[k]

    def get_ag_investment(self, k: int) -> float:
        """Agricultural investment at timestep k. Used by Agriculture sector."""
        return self.ag_investment[k]

    def get_health_services_pc(self, k: int) -> float:
        """Health services per capita at timestep k. Used by Population sector."""
        return self.hsapc[k]

    def get_iopc(self, k: int) -> float:
        """Industrial output per capita. Development proxy."""
        return self.iopc[k]

    def get_results_df(self):
        """Return full results as DataFrame for dashboard display."""
        import pandas as pd
        return pd.DataFrame({
            'Year': self.time,
            'Industrial_Capital': self.ic,
            'Service_Capital': self.sc,
            'Industrial_Output': self.io,
            'Service_Output': self.so,
            'IO_Per_Capita': self.iopc,
            'Health_Services_PC': self.hsapc,
            'AG_Investment': self.ag_investment,
            'Frac_to_Agriculture': self.fioaa,
            'Frac_to_Industry': self.fioai,
            'Frac_to_Services': self.fioas,
            'Food_Ratio_Input': self.food_ratio,
        })
