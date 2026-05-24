"""
World3 Country-Level Food System Dashboard
==========================================

Interactive Streamlit dashboard for the 5-sector coupled World3 model
calibrated for Canada and Nigeria. Includes country-specific crop mixes
and per-nutrient gap analysis.

Run:
    streamlit run climate_nutrition_world3/dashboard_v2.py

Model architecture: Meadows et al. (1972) World3, Python implementation
based on PyWorld3 (Vanwynsberghe 2021). Country calibrations from
Statistics Canada, UN World Population Prospects 2024, FAO FAOSTAT,
World Bank WDI, and WHO. See in-tab citations for specific sources.
"""

# ============================================================
# IMPORTS
# ============================================================

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from climate_nutrition_world3.world3_integrator import World3Integrator
from climate_nutrition_world3.sectors.population_sector import (
    CANADA_POPULATION_PARAMS, NIGERIA_POPULATION_PARAMS,
)
from climate_nutrition_world3.sectors.capital_sector import (
    CANADA_CAPITAL_PARAMS, NIGERIA_CAPITAL_PARAMS,
)
from climate_nutrition_world3.sectors.agriculture_sector import (
    CANADA_AGRICULTURE_PARAMS, NIGERIA_AGRICULTURE_PARAMS,
)
from climate_nutrition_world3.sectors.pollution_sector import (
    CANADA_POLLUTION_PARAMS, NIGERIA_POLLUTION_PARAMS,
)
from climate_nutrition_modelling.models.nutrient_converter import (
    NutrientConverter, CROP_NUTRIENT_PROFILES,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="World3 Country Food System Model",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS - COUNTRY DATA AND CITATIONS
# ============================================================

# Crop mixes by country - share of total food crop production by mass.
# Source for Canada: Statistics Canada Table 32-10-0359-01 (Production
#   of principal field crops, annual) and Table 32-10-0365-01 (Vegetable
#   production), 2020-2023 averages, restricted to crops used directly
#   for human food (excludes oilseed/feed crops such as canola, barley
#   for malting/feed where the food-use fraction is small).
# Source for Nigeria: FAO FAOSTAT Production_Crops_Livestock_E_Africa,
#   2020-2023 averages, and Nigeria Bureau of Statistics Annual Abstract.

COUNTRY_CROP_MIXES = {
    "canada": {
        "wheat":         0.50,  # ~32 Mt/yr, primary food grain
        "maize_grain":   0.20,  # ~14 Mt/yr (corn; portion used as food)
        "soybean":       0.10,  # ~6.5 Mt/yr (food-grade share)
        "tomato":        0.07,  # ~0.5 Mt/yr greenhouse + field
        "leafy_greens":  0.05,  # lettuce, spinach, kale combined
        "sweet_potato":  0.05,
        "groundnut":     0.03,  # peanuts (imported share allocated for nutrition)
    },
    "nigeria": {
        "cassava":       0.32,  # ~60 Mt/yr - largest staple
        "yam":           0.25,  # ~50 Mt/yr
        "sorghum":       0.12,  # ~7 Mt/yr
        "maize_grain":   0.10,  # ~12 Mt/yr
        "rice_paddy":    0.08,  # ~8 Mt/yr
        "plantain":      0.04,  # ~3 Mt/yr
        "millet":        0.03,  # ~2 Mt/yr
        "cowpea":        0.03,  # ~2.5 Mt/yr
        "groundnut":     0.02,  # ~3 Mt/yr
        "leafy_greens":  0.01,  # amaranth, ugu, ewedu
    },
}

# Daily per-capita nutrient requirements for adults.
# Sources:
#   - Energy, protein, fat: FAO/WHO/UNU (2004) Human Energy Requirements
#   - Iron, zinc, vit A, folate, vit C, calcium: WHO/FAO (2004) Vitamin
#     and Mineral Requirements in Human Nutrition, 2nd ed.
#   - Health Canada Dietary Reference Intakes (2010) — calcium, fiber

DAILY_REQUIREMENTS = {
    "energy_kcal":      2100.0,   # kcal/day - FAO/WHO/UNU minimum
    "protein_kg":       0.050,    # 50 g/day - FAO/WHO/UNU
    "fat_kg":           0.065,    # ~65 g/day (lower bound, 25% energy)
    "fiber_kg":         0.025,    # 25 g/day - Health Canada DRI women
    "iron_g":           0.012,    # 12 mg/day - WHO adult average
    "zinc_g":           0.010,    # 10 mg/day - WHO adult average
    "calcium_g":        1.000,    # 1000 mg/day - Health Canada DRI
    "vitamin_a_mg_rae": 0.700,    # 700 ug RAE/day - WHO
    "folate_mg":        0.400,    # 400 ug DFE/day - WHO
    "vitamin_c_g":      0.090,    # 90 mg/day - Health Canada DRI
}

# Display labels and units for nutrients
NUTRIENT_DISPLAY = {
    "energy_kcal":      ("Calories",     "kcal/day"),
    "protein_kg":       ("Protein",      "g/day"),
    "fat_kg":           ("Fat",          "g/day"),
    "fiber_kg":         ("Fiber",        "g/day"),
    "iron_g":           ("Iron",         "mg/day"),
    "zinc_g":           ("Zinc",         "mg/day"),
    "calcium_g":        ("Calcium",      "mg/day"),
    "vitamin_a_mg_rae": ("Vitamin A",    "ug RAE/day"),
    "folate_mg":        ("Folate",       "ug/day"),
    "vitamin_c_g":      ("Vitamin C",    "mg/day"),
}

# Unit conversion factors: from-storage-units to display-units per person per day
# (storage units are: kcal, kg, g, mg per total production over a year)
NUTRIENT_DISPLAY_SCALE = {
    "energy_kcal":      1.0,        # kcal -> kcal
    "protein_kg":       1000.0,     # kg -> g
    "fat_kg":           1000.0,
    "fiber_kg":         1000.0,
    "iron_g":           1000.0,     # g -> mg
    "zinc_g":           1000.0,
    "calcium_g":        1000.0,
    "vitamin_a_mg_rae": 1000.0,     # mg -> ug
    "folate_mg":        1000.0,
    "vitamin_c_g":      1000.0,
}

# Display labels for crops
CROP_DISPLAY_NAMES = {key: prof.crop_name for key, prof in CROP_NUTRIENT_PROFILES.items()}

# Color palette - clean institutional, no emoji vibe
COLORS = {
    "primary":      "#2E5984",   # deep blue
    "secondary":    "#C44536",   # rust
    "accent":       "#6A994E",   # sage green
    "neutral":      "#6B6B6B",   # medium gray
    "warning":      "#BC6C25",   # amber
    "success":      "#386641",   # forest green
    "muted":        "#BDBDBD",   # light gray
    "p1":           "#A8DADC",   # 0-14
    "p2":           "#457B9D",   # 15-44
    "p3":           "#1D3557",   # 45-64
    "p4":           "#06402B",   # 65+
}

# Adequacy classification thresholds
def adequacy_label(value: float) -> str:
    if value >= 1.0:
        return "Adequate"
    elif value >= 0.7:
        return "Below target"
    elif value >= 0.4:
        return "Deficit"
    else:
        return "Severe deficit"

def adequacy_color(value: float) -> str:
    if value >= 1.0:
        return COLORS["success"]
    elif value >= 0.7:
        return COLORS["warning"]
    elif value >= 0.4:
        return COLORS["secondary"]
    else:
        return "#7E1F1F"


# ============================================================
# SIMULATION RUNNER (CACHED)
# ============================================================

@st.cache_data(show_spinner=False)
def run_baseline(country: str, year_start: int, year_end: int,
                 climate_scenario: str = None) -> dict:
    """Run a baseline simulation for the country with default parameters.

    If climate_scenario is one of 'ssp126', 'ssp245', 'ssp370', 'ssp585',
    the agriculture sector uses the IPCC climate bridge instead of its
    simple linear climate model.
    """
    model = World3Integrator.from_country(
        country, year_start, year_end,
        climate_scenario=climate_scenario,
    )
    model.run()
    return _extract_results(model)


@st.cache_data(show_spinner=False)
def run_custom(
    country: str, year_start: int, year_end: int,
    tfr_init: float, tfr_target: float, tfr_decline: float,
    immigration_rate: float, mortality_improve: float,
    yield_growth: float, fioaa_base: float,
    pollution_decline: float, climate_sens: float,
    climate_scenario: str = None,
) -> dict:
    """Run a simulation with user-modified parameters and optional IPCC SSP."""
    model = World3Integrator.from_country(
        country, year_start, year_end,
        climate_scenario=climate_scenario,
    )
    # Override parameters
    p = model.population.params
    p.total_fertility_rate = tfr_init
    p.tfr_target = tfr_target
    p.tfr_decline_rate = tfr_decline
    p.immigration_rate = immigration_rate
    p.mortality_improvement_rate = mortality_improve
    model.population._init_stocks()
    model.population.tfr[0] = tfr_init

    model.agriculture.params.tech_yield_growth_rate = yield_growth
    # Only honour the simple climate sensitivity when no IPCC scenario active.
    if climate_scenario is None:
        model.agriculture.params.climate_sensitivity = climate_sens

    model.capital.params.fioaa_base = fioaa_base
    model.capital.fioaa[0] = fioaa_base

    model.pollution.params.pollution_intensity_decline = pollution_decline

    model.run()
    return _extract_results(model)


def _extract_results(model: World3Integrator) -> dict:
    """Pull arrays out of a completed model into a plain dict."""
    result = {
        "years": np.array(model.time),
        # Population
        "pop":           np.array(model.population.pop),
        "p1":            np.array(model.population.p1),
        "p2":            np.array(model.population.p2),
        "p3":            np.array(model.population.p3),
        "p4":            np.array(model.population.p4),
        "births":        np.array(model.population.births),
        "deaths":        np.array(model.population.deaths),
        "mat1":          np.array(model.population.mat1),
        "mat2":          np.array(model.population.mat2),
        "mat3":          np.array(model.population.mat3),
        "immigration":   np.array(model.population.immigration),
        "tfr":           np.array(model.population.tfr),
        "life_exp":      np.array(model.population.life_exp),
        "cbr":           np.array(model.population.cbr),
        "cdr":           np.array(model.population.cdr),
        "labor_force":   np.array(model.population.labor_force),
        # Capital
        "ic":            np.array(model.capital.ic),
        "sc":            np.array(model.capital.sc),
        "io":            np.array(model.capital.io),
        "so":            np.array(model.capital.so),
        "iopc":          np.array(model.capital.iopc),
        "hsapc":         np.array(model.capital.hsapc),
        "ag_investment": np.array(model.capital.ag_investment),
        "fioaa":         np.array(model.capital.fioaa),
        "fioai":         np.array(model.capital.fioai),
        "fioas":         np.array(model.capital.fioas),
        "fioac":         np.array(model.capital.fioac),
        # Agriculture
        "al":               np.array(model.agriculture.al),
        "lfert":            np.array(model.agriculture.lfert),
        "food_production":  np.array(model.agriculture.food_production),
        "food_per_capita":  np.array(model.agriculture.food_per_capita),
        "food_ratio":       np.array(model.agriculture.food_ratio),
        "land_yield":       np.array(model.agriculture.land_yield),
        "input_multiplier": np.array(model.agriculture.input_multiplier),
        "climate_factor":   np.array(model.agriculture.climate_factor),
        "land_development": np.array(model.agriculture.land_development),
        "land_erosion":     np.array(model.agriculture.land_erosion),
        "fert_regen":       np.array(model.agriculture.fert_regen),
        "fert_degrade":     np.array(model.agriculture.fert_degrade),
        # Pollution
        "pp":                np.array(model.pollution.pp),
        "ppolx":             np.array(model.pollution.ppolx),
        "pp_gen":            np.array(model.pollution.pp_gen),
        "pp_abs":            np.array(model.pollution.pp_abs),
        "pp_gen_industry":   np.array(model.pollution.pp_gen_industry),
        "pp_gen_agriculture":np.array(model.pollution.pp_gen_agriculture),
        "pp_gen_waste":      np.array(model.pollution.pp_gen_waste),
        "absorption_time":   np.array(model.pollution.absorption_time),
        # Nutrition (basic)
        "calorie_supply":      np.array(model.nutrition.calorie_supply),
        "protein_supply":      np.array(model.nutrition.protein_supply),
        "calorie_adequacy":    np.array(model.nutrition.calorie_adequacy),
        "protein_adequacy":    np.array(model.nutrition.protein_adequacy),
        "stunting_risk":       np.array(model.nutrition.stunting_risk),
        "food_security_index": np.array(model.nutrition.food_security_index),
        "nutrition_gap":       np.array(model.nutrition.nutrition_gap),
    }
    # If an IPCC climate bridge is attached, also extract its trajectories.
    if model.climate_bridge is not None:
        bridge = model.climate_bridge
        result["climate_scenario_name"] = bridge.get_scenario_label()
        result["climate_temperature_c"] = np.array(bridge.temperature)
        result["climate_precipitation_mm"] = np.array(bridge.precipitation)
        result["climate_co2_ppm"] = np.array(bridge.co2_ppm)
        result["climate_stress_factor"] = np.array(bridge.climate_stress)
        result["climate_protein_degradation"] = np.array(bridge.protein_degradation)
        result["climate_iron_degradation"] = np.array(bridge.iron_degradation)
        result["climate_zinc_degradation"] = np.array(bridge.zinc_degradation)
    else:
        result["climate_scenario_name"] = "Simple linear (no IPCC scenario)"
    return result


# ============================================================
# CROP-LEVEL NUTRITION ANALYSIS
# ============================================================

def compute_crop_nutrients(
    food_production_kg: float,
    crop_mix: dict,
    pop: float,
) -> dict:
    """
    Split total food production into crops and compute per-capita
    daily nutrient supply and adequacy ratios.

    Returns dict with:
      - per_crop: dict of crop_key -> {nutrient: daily_supply_per_capita}
      - totals:   dict of nutrient -> total daily supply per capita
      - adequacy: dict of nutrient -> ratio to daily requirement
    """
    food_tonnes = food_production_kg / 1000.0
    converter = NutrientConverter()

    per_crop_breakdown = {}
    for crop_key, share in crop_mix.items():
        crop_tonnes = food_tonnes * share
        nutrients = converter.convert_crop(crop_key, crop_tonnes)
        per_crop_breakdown[crop_key] = nutrients

    totals = converter.get_total_nutrients()

    # Convert totals (annual, country-wide) to per-capita daily values
    pop_safe = max(1.0, pop)
    per_capita_daily = {}
    adequacy = {}
    for nutrient_key in DAILY_REQUIREMENTS:
        annual_total = totals.get(nutrient_key, 0.0)
        per_capita_annual = annual_total / pop_safe
        per_capita_per_day = per_capita_annual / 365.0
        per_capita_daily[nutrient_key] = per_capita_per_day
        adequacy[nutrient_key] = per_capita_per_day / DAILY_REQUIREMENTS[nutrient_key]

    # Per-crop daily contributions per capita
    per_crop_per_capita_daily = {}
    for crop_key, nutrients in per_crop_breakdown.items():
        crop_daily = {}
        for nutrient_key in DAILY_REQUIREMENTS:
            annual = nutrients.get(nutrient_key, 0.0)
            crop_daily[nutrient_key] = annual / pop_safe / 365.0
        crop_daily["effective_food_tonnes"] = nutrients.get("effective_food_tonnes", 0.0)
        crop_daily["total_production_tonnes"] = nutrients.get("total_production_tonnes", 0.0)
        per_crop_per_capita_daily[crop_key] = crop_daily

    return {
        "per_crop": per_crop_per_capita_daily,
        "totals_per_capita_daily": per_capita_daily,
        "adequacy": adequacy,
    }


# ============================================================
# CHART HELPERS
# ============================================================

def base_layout(title: str, ylabel: str, height: int = 360) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="Year",
        yaxis_title=ylabel,
        height=height,
        template="plotly_white",
        margin=dict(l=60, r=20, t=50, b=40),
        hovermode="x unified",
    )

def line_chart(years, series_dict, title, ylabel, height=360,
               hline=None, hlabel=None, vline_year=2025):
    fig = go.Figure()
    palette = [COLORS["primary"], COLORS["secondary"], COLORS["accent"],
               COLORS["warning"], COLORS["neutral"], COLORS["success"]]
    for i, (name, y) in enumerate(series_dict.items()):
        fig.add_trace(go.Scatter(
            x=years, y=y, mode="lines", name=name,
            line=dict(width=2.4, color=palette[i % len(palette)]),
        ))
    if hline is not None:
        fig.add_hline(y=hline, line_dash="dot", line_color=COLORS["neutral"],
                      annotation_text=hlabel or "", annotation_position="top right")
    if vline_year is not None:
        fig.add_vline(x=vline_year, line_dash="dash",
                      line_color=COLORS["neutral"], opacity=0.4,
                      annotation_text="Historical / Projection", annotation_position="top")
    fig.update_layout(**base_layout(title, ylabel, height))
    fig.update_layout(legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"))
    return fig


def stacked_area_chart(years, series_dict, title, ylabel, height=360, colors=None):
    fig = go.Figure()
    palette = colors or [COLORS["p1"], COLORS["p2"], COLORS["p3"], COLORS["p4"],
                         COLORS["warning"], COLORS["accent"]]
    for i, (name, y) in enumerate(series_dict.items()):
        fig.add_trace(go.Scatter(
            x=years, y=y, mode="lines", name=name,
            stackgroup="one",
            line=dict(width=0.5, color=palette[i % len(palette)]),
            fillcolor=palette[i % len(palette)],
        ))
    fig.add_vline(x=2025, line_dash="dash", line_color=COLORS["neutral"], opacity=0.4)
    fig.update_layout(**base_layout(title, ylabel, height))
    fig.update_layout(legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"))
    return fig


def dual_axis_chart(years, left_data, right_data,
                    left_label, right_label, title, height=360):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=years, y=left_data["y"], name=left_data["name"],
        line=dict(color=COLORS["primary"], width=2.4),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=years, y=right_data["y"], name=right_data["name"],
        line=dict(color=COLORS["secondary"], width=2.4),
    ), secondary_y=True)
    fig.add_vline(x=2025, line_dash="dash", line_color=COLORS["neutral"], opacity=0.4)
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=height, template="plotly_white",
        margin=dict(l=60, r=60, t=50, b=40),
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text=left_label, secondary_y=False)
    fig.update_yaxes(title_text=right_label, secondary_y=True)
    return fig


def render_io_panel(sector_name: str, inputs: list, outputs: list,
                    loops: list, citation: str):
    """Render the inputs/outputs/loops information panel for a sector."""
    st.markdown(f"### How {sector_name} connects to other sectors")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Receives from other sectors**")
        for arrow in inputs:
            st.markdown(f"- {arrow}")
    with c2:
        st.markdown("**Sends to other sectors**")
        for arrow in outputs:
            st.markdown(f"- {arrow}")
    if loops:
        st.markdown("**Feedback loops this sector is part of**")
        for loop in loops:
            st.markdown(f"- {loop}")
    if citation:
        st.caption(f"Data sources: {citation}")


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("Model Configuration")
st.sidebar.markdown(
    "Five coupled sectors calibrated for the selected country using "
    "real published government and international data. Adjust parameters "
    "below to see how changes propagate through the system."
)

country_display = st.sidebar.selectbox(
    "Country", ["Canada", "Nigeria"], index=0,
)
country = country_display.lower()

st.sidebar.markdown("---")
st.sidebar.subheader("Simulation Range")
year_start = st.sidebar.slider("Start year", 1971, 2000, 1971, step=1)
year_end = st.sidebar.slider("End year", 2030, 2150, 2100, step=10)

st.sidebar.markdown("---")
st.sidebar.subheader("Climate scenario")
SSP_OPTIONS = {
    "None (simple linear model)": None,
    "SSP1-2.6 (Sustainability, +1.8C by 2100)": "ssp126",
    "SSP2-4.5 (Middle of Road, +2.7C)": "ssp245",
    "SSP3-7.0 (Regional Rivalry, +3.6C)": "ssp370",
    "SSP5-8.5 (Fossil Fuel Dev, +4.4C)": "ssp585",
}
climate_choice_label = st.sidebar.selectbox(
    "IPCC SSP scenario",
    list(SSP_OPTIONS.keys()),
    index=0,
    help=(
        "When set to None, agriculture uses a simple linear climate "
        "sensitivity. When an SSP is selected, the model uses IPCC AR6 "
        "temperature, precipitation, and CO2 trajectories downscaled to "
        "the country's region (Southern Ontario for Canada, Northern "
        "Nigeria for Nigeria). See the Climate tab for details."
    ),
)
climate_scenario = SSP_OPTIONS[climate_choice_label]

st.sidebar.markdown("---")
st.sidebar.subheader("Parameter Adjustments")
st.sidebar.caption(
    "These override the baseline calibrated values. Reset by reloading the page."
)

# Get baseline params for the selected country to set slider defaults
if country == "canada":
    base_pop = CANADA_POPULATION_PARAMS
    base_cap = CANADA_CAPITAL_PARAMS
    base_ag = CANADA_AGRICULTURE_PARAMS
    base_pol = CANADA_POLLUTION_PARAMS
else:
    base_pop = NIGERIA_POPULATION_PARAMS
    base_cap = NIGERIA_CAPITAL_PARAMS
    base_ag = NIGERIA_AGRICULTURE_PARAMS
    base_pol = NIGERIA_POLLUTION_PARAMS

st.sidebar.markdown("**Population**")
slider_tfr = st.sidebar.slider(
    "Initial fertility rate (children per woman)",
    1.0, 8.0, float(base_pop.total_fertility_rate), 0.1,
    key=f"slider_tfr_{country}",
    help="Total fertility rate in the starting year",
)
slider_tfr_target = st.sidebar.slider(
    "Long-run fertility target",
    1.0, 6.0, float(base_pop.tfr_target), 0.1,
    key=f"slider_tfr_target_{country}",
)
slider_tfr_decline = st.sidebar.slider(
    "Fertility decline rate per year",
    0.001, 0.030, float(base_pop.tfr_decline_rate), 0.001, format="%.3f",
    key=f"slider_tfr_decline_{country}",
)
# Immigration slider only shown for Canada (Nigeria has immigration_enabled=False
# in the population sector, so the slider would have no effect there).
if base_pop.immigration_enabled:
    slider_immig = st.sidebar.slider(
        "Immigration rate (fraction of population per year)",
        0.000, 0.020, float(base_pop.immigration_rate), 0.001, format="%.3f",
        key=f"slider_immig_{country}",
    )
else:
    slider_immig = float(base_pop.immigration_rate)
    st.sidebar.caption(
        "Immigration is not modelled for this country "
        "(immigration_enabled=False in the population sector)."
    )
slider_mort_imp = st.sidebar.slider(
    "Mortality improvement per year",
    0.000, 0.030, float(base_pop.mortality_improvement_rate), 0.001, format="%.3f",
    key=f"slider_mort_imp_{country}",
)

st.sidebar.markdown("**Agriculture**")
slider_yield = st.sidebar.slider(
    "Yield technology growth per year",
    0.000, 0.030, float(base_ag.tech_yield_growth_rate), 0.001, format="%.3f",
    key=f"slider_yield_{country}",
)
slider_climate = st.sidebar.slider(
    "Climate damage sensitivity",
    0.000, 0.010, float(base_ag.climate_sensitivity), 0.0005, format="%.4f",
    key=f"slider_climate_{country}",
)

st.sidebar.markdown("**Capital and Pollution**")
slider_fioaa = st.sidebar.slider(
    "Baseline capital allocation to agriculture",
    0.02, 0.40, float(base_cap.fioaa_base), 0.01,
    key=f"slider_fioaa_{country}",
)
slider_pol_decline = st.sidebar.slider(
    "Pollution intensity decline per year (clean tech)",
    0.000, 0.025, float(base_pol.pollution_intensity_decline), 0.001, format="%.3f",
    key=f"slider_pol_decline_{country}",
)

# ============================================================
# RUN SIMULATIONS
# ============================================================

with st.spinner(f"Running {country_display} simulation..."):
    baseline = run_baseline(country, year_start, year_end,
                            climate_scenario=climate_scenario)
    custom = run_custom(
        country, year_start, year_end,
        slider_tfr, slider_tfr_target, slider_tfr_decline,
        slider_immig, slider_mort_imp,
        slider_yield, slider_fioaa,
        slider_pol_decline, slider_climate,
        climate_scenario=climate_scenario,
    )

years = custom["years"]

# ============================================================
# HEADER
# ============================================================

st.title(f"World3 Country Food System Model: {country_display}")
st.markdown(
    f"Five-sector coupled system dynamics simulation, {year_start}-{year_end}. "
    "Population, Capital, Agriculture, Pollution, and Nutrition sectors "
    "exchange variables each year through bidirectional feedback. The active "
    "scenario reflects the sidebar slider settings; the baseline reflects the "
    "country's calibrated published values."
)

# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "Overview",
    "Population",
    "Capital",
    "Agriculture",
    "Pollution",
    "Climate",
    "Nutrition and Crops",
    "Cascade Lab",
    "Feedback Loops",
])

# ------------------------------------------------------------
# TAB 1: OVERVIEW
# ------------------------------------------------------------
with tabs[0]:
    st.header(f"Overview: {country_display}, {year_end}")
    st.caption(
        "Key headline metrics at the end of the simulation period "
        "for the active scenario."
    )

    last = -1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Population", f"{custom['pop'][last]/1e6:.0f} M")
    with c2:
        fs = custom["food_security_index"][last]
        st.metric("Food security index", f"{fs:.2f}",
                  delta=f"{adequacy_label(fs)}")
    with c3:
        sr = custom["stunting_risk"][last] * 100
        st.metric("Stunting risk", f"{sr:.1f}%")
    with c4:
        st.metric("Life expectancy", f"{custom['life_exp'][last]:.1f} yr")

    st.markdown("### Trajectories of all five sectors")
    a1, a2, a3 = st.columns(3)
    with a1:
        st.plotly_chart(line_chart(
            years,
            {"Population": custom["pop"] / 1e6},
            "Population (millions)", "Millions of people", height=290,
        ), use_container_width=True)
    with a2:
        st.plotly_chart(line_chart(
            years,
            {"Industrial output": custom["io"] / 1e9},
            "Industrial output", "Billion USD/year", height=290,
        ), use_container_width=True)
    with a3:
        st.plotly_chart(line_chart(
            years,
            {"Food per capita": custom["food_per_capita"]},
            "Food per capita", "kg/person/year", height=290,
        ), use_container_width=True)

    b1, b2, b3 = st.columns(3)
    with b1:
        st.plotly_chart(line_chart(
            years,
            {"Pollution index": custom["ppolx"]},
            "Pollution index (relative to 1970)", "Index", height=290,
            hline=1.0, hlabel="1970 level",
        ), use_container_width=True)
    with b2:
        st.plotly_chart(line_chart(
            years,
            {"Food security": custom["food_security_index"]},
            "Food security index", "Score (0-1)", height=290,
            hline=1.0, hlabel="Full security",
        ), use_container_width=True)
    with b3:
        st.plotly_chart(line_chart(
            years,
            {"Stunting risk": custom["stunting_risk"]},
            "Stunting risk in children under 5", "Fraction", height=290,
        ), use_container_width=True)

    st.markdown("---")
    st.markdown("### What this model is")
    st.markdown(
        f"This is a five-sector coupled World3-style system dynamics model "
        f"calibrated for {country_display}. The model follows Meadows et al. "
        f"(1972) *The Limits to Growth* architecture, implemented in Python "
        f"based on PyWorld3 (Vanwynsberghe, 2021), with all country-specific "
        f"parameters drawn from published government and international data. "
        f"The five sectors exchange variables every year through 14 coupling "
        f"arrows and seven named feedback loops. Behavior is emergent: nothing "
        f"is scripted, all outcomes arise from the equations and parameter "
        f"values."
    )

# ------------------------------------------------------------
# TAB 2: POPULATION
# ------------------------------------------------------------
with tabs[1]:
    st.header("Population Sector")
    st.caption(
        "Four age cohorts (0-14, 15-44, 45-64, 65+). Tracks births, deaths, "
        "maturation between cohorts, and immigration. Output drives food "
        "demand in Agriculture and labour in Capital."
    )

    sub = st.tabs([
        "Total population", "Age structure", "Births and deaths",
        "Fertility and life expectancy", "Immigration", "Inputs and outputs",
    ])

    with sub[0]:
        st.plotly_chart(line_chart(
            years,
            {"Active scenario": custom["pop"] / 1e6,
             "Baseline": baseline["pop"] / 1e6},
            f"Total population: {country_display}",
            "Millions of people",
        ), use_container_width=True)
        st.caption(
            "Source: Statistics Canada Table 17-10-0005-01 (Canada); "
            "UN World Population Prospects 2024 (Nigeria). "
            "Calibrated to reproduce 1971-2023 historical trajectory."
        )

    with sub[1]:
        st.plotly_chart(stacked_area_chart(
            years,
            {"0-14 (P1)":   custom["p1"] / 1e6,
             "15-44 (P2)":  custom["p2"] / 1e6,
             "45-64 (P3)":  custom["p3"] / 1e6,
             "65+ (P4)":    custom["p4"] / 1e6},
            "Population by age cohort", "Millions",
        ), use_container_width=True)
        st.caption(
            "Age structure reveals demographic momentum: a large young cohort "
            "drives future births even after fertility falls."
        )

    with sub[2]:
        st.plotly_chart(line_chart(
            years,
            {"Births": custom["births"] / 1e6,
             "Deaths": custom["deaths"] / 1e6,
             "Immigration": custom["immigration"] / 1e6},
            "Annual flows", "Millions of people per year",
        ), use_container_width=True)
        st.plotly_chart(line_chart(
            years,
            {"Crude birth rate (per 1000)": custom["cbr"],
             "Crude death rate (per 1000)": custom["cdr"]},
            "Crude vital rates", "Per 1000 population",
        ), use_container_width=True)

    with sub[3]:
        st.plotly_chart(dual_axis_chart(
            years,
            {"y": custom["tfr"], "name": "Total fertility rate"},
            {"y": custom["life_exp"], "name": "Life expectancy"},
            "Children per woman", "Years",
            "Fertility and life expectancy over time",
        ), use_container_width=True)
        st.caption(
            "Source: Statistics Canada Vital Statistics (Canada); "
            "UN WPP 2024 (Nigeria). Life expectancy is computed endogenously "
            "from cohort mortality plus food and pollution stress."
        )

    with sub[4]:
        if country == "canada":
            st.plotly_chart(line_chart(
                years,
                {"Active scenario": custom["immigration"] / 1e3,
                 "Baseline": baseline["immigration"] / 1e3},
                "Annual immigration", "Thousands of people per year",
            ), use_container_width=True)
            st.caption(
                "Source: Immigration, Refugees and Citizenship Canada "
                "Annual Reports. Rate rises after 2015 reflecting policy shift."
            )
        else:
            st.info(
                "Nigeria is modelled with zero net international migration. "
                "Internal rural-urban migration is not separately tracked."
            )

    with sub[5]:
        render_io_panel(
            "Population",
            inputs=[
                "`food_ratio` from Agriculture (prior year): affects mortality "
                "if food becomes scarce",
                "`hsapc` (health services per capita) from Capital (prior year): "
                "affects life expectancy",
                "`ppolx` (pollution index) from Pollution (prior year): affects "
                "mortality multiplier",
            ],
            outputs=[
                "`pop` to Capital (current year): denominator for per-capita "
                "metrics, labour force input",
                "`pop` to Agriculture (current year): denominator for "
                "food_per_capita",
                "`pop` to Pollution (current year): driver of household waste",
                "`labor_force` (P2+P3) to Capital (current year): capital "
                "utilisation",
            ],
            loops=[
                "R1 Population growth (reinforcing): pop -> births -> pop",
                "B2 Food-mortality (balancing): food shortage -> deaths -> "
                "population decline",
                "B4 Fertility response (balancing): food shortage -> TFR "
                "reduction -> fewer births",
            ],
            citation=(
                "Statistics Canada Tables 17-10-0005-01 (population), Life Tables; "
                "UN World Population Prospects 2024; IRCC Annual Reports; "
                "WHO Global Health Observatory"
            ),
        )

# ------------------------------------------------------------
# TAB 3: CAPITAL
# ------------------------------------------------------------
with tabs[2]:
    st.header("Capital Sector")
    st.caption(
        "Industrial Capital (IC) and Service Capital (SC) accumulate from "
        "investment, depreciate over time. Industrial output is allocated "
        "across agriculture, industry, services, and consumption. "
        "Service output funds healthcare per capita."
    )

    sub = st.tabs([
        "Capital stocks", "Output flows", "Allocation",
        "Per-capita metrics", "Inputs and outputs",
    ])

    with sub[0]:
        st.plotly_chart(line_chart(
            years,
            {"Industrial capital (IC)": custom["ic"] / 1e9,
             "Service capital (SC)":    custom["sc"] / 1e9},
            "Capital stocks", "Billion USD",
        ), use_container_width=True)
        st.caption(
            "Source: Statistics Canada Table 36-10-0222-01; "
            "World Bank WDI; Penn World Table 10.01."
        )

    with sub[1]:
        st.plotly_chart(line_chart(
            years,
            {"Industrial output (IO)": custom["io"] / 1e9,
             "Service output (SO)":    custom["so"] / 1e9},
            "Annual output", "Billion USD per year",
        ), use_container_width=True)
        st.caption(
            "Industrial output drives pollution generation and is the source "
            "of agricultural investment."
        )

    with sub[2]:
        st.plotly_chart(stacked_area_chart(
            years,
            {"To agriculture":  custom["fioaa"] * 100,
             "To industry":     custom["fioai"] * 100,
             "To services":     custom["fioas"] * 100,
             "To consumption":  custom["fioac"] * 100},
            "Allocation of industrial output (percent)", "Percent",
            colors=[COLORS["accent"], COLORS["primary"],
                    COLORS["warning"], COLORS["secondary"]],
        ), use_container_width=True)
        st.caption(
            "When food_ratio drops below 1.0, the share allocated to agriculture "
            "automatically rises (feedback loop B1). Watch the agriculture stripe "
            "thicken under food stress."
        )

    with sub[3]:
        st.plotly_chart(line_chart(
            years,
            {"Industrial output per capita": custom["iopc"],
             "Health services per capita":   custom["hsapc"]},
            "Per-capita metrics", "USD per person per year",
        ), use_container_width=True)
        st.caption(
            "Health services per capita is sent to Population and modulates "
            "life expectancy. Source: WHO Global Health Expenditure Database."
        )

    with sub[4]:
        render_io_panel(
            "Capital",
            inputs=[
                "`pop`, `labor_force` from Population (current year): capital "
                "utilisation and per-capita denominators",
                "`food_ratio` from Agriculture (prior year): triggers allocation "
                "shift towards agriculture (B1)",
            ],
            outputs=[
                "`io` to Pollution (current year): industrial pollution source",
                "`ag_investment` (= io * fioaa) to Agriculture (current year): "
                "drives yield multiplier",
                "`hsapc` to Population (next year): life expectancy",
            ],
            loops=[
                "R2 Capital accumulation (reinforcing): IC -> io -> investment "
                "-> IC",
                "B1 Food-investment (balancing): food shortage -> fioaa rises "
                "-> ag investment -> food",
            ],
            citation=(
                "Statistics Canada Table 36-10-0222-01 (capital stock); "
                "World Bank World Development Indicators; "
                "Penn World Table 10.01 (capital-output ratios); "
                "WHO Global Health Expenditure Database"
            ),
        )

# ------------------------------------------------------------
# TAB 4: AGRICULTURE
# ------------------------------------------------------------
with tabs[3]:
    st.header("Agriculture Sector")
    st.caption(
        "Two stocks: arable land (AL) and land fertility (LFERT). Food "
        "production equals AL multiplied by effective yield. Effective yield "
        "is the product of technology growth, soil health, capital inputs, "
        "climate, and pollution factors."
    )

    sub = st.tabs([
        "Land dynamics", "Land fertility", "Yield decomposition",
        "Food production", "Inputs and outputs",
    ])

    with sub[0]:
        st.plotly_chart(line_chart(
            years,
            {"Arable land": custom["al"] / 1e6},
            "Arable land stock", "Million hectares",
        ), use_container_width=True)
        st.plotly_chart(line_chart(
            years,
            {"Land development": custom["land_development"] / 1e3,
             "Land erosion":     custom["land_erosion"] / 1e3},
            "Annual land flows", "Thousand hectares per year",
        ), use_container_width=True)
        st.caption(
            "Source: Statistics Canada Table 32-10-0359-01 (Canada cropland); "
            "FAO FAOSTAT Land Use Statistics (Nigeria)."
        )

    with sub[1]:
        st.plotly_chart(line_chart(
            years,
            {"Land fertility": custom["lfert"]},
            "Land fertility (potential yield)", "kg per hectare",
        ), use_container_width=True)
        st.plotly_chart(line_chart(
            years,
            {"Fertility regeneration": custom["fert_regen"],
             "Fertility degradation":  custom["fert_degrade"]},
            "Fertility flows", "kg/ha per year",
        ), use_container_width=True)
        st.caption(
            "Fertility degrades from pollution accumulation (IPCC AR6 WGII "
            "Ch.5 ozone-yield relationship) and over-use; regenerates naturally."
        )

    with sub[2]:
        # Show the multiplicative components of yield
        st.plotly_chart(line_chart(
            years,
            {"Climate factor":   custom["climate_factor"],
             "Input multiplier": custom["input_multiplier"],
             "Pollution factor": 1.0 - (1.0 - np.clip(
                  1 - base_ag.pollution_yield_sensitivity *
                  np.maximum(0, custom["ppolx"] - 1), 0.5, 1.0))},
            "Yield modifying factors over time", "Multiplier (1.0 = no effect)",
            hline=1.0, hlabel="Baseline",
        ), use_container_width=True)
        st.caption(
            "Effective yield = base * tech_growth * soil_factor * input_multiplier "
            "* climate_factor * pollution_factor. Watch which factor drives "
            "yield changes."
        )

    with sub[3]:
        st.plotly_chart(line_chart(
            years,
            {"Food production (total)": custom["food_production"] / 1e9},
            "Total food production", "Million tonnes per year",
        ), use_container_width=True)
        st.plotly_chart(line_chart(
            years,
            {"Food per capita": custom["food_per_capita"]},
            "Food per capita", "kg/person/year",
            hline=base_ag.subsistence_food_pc, hlabel="Subsistence requirement",
        ), use_container_width=True)
        st.plotly_chart(line_chart(
            years,
            {"Food ratio": custom["food_ratio"]},
            "Food ratio (food_per_capita / subsistence)", "Ratio",
            hline=1.0, hlabel="Adequacy threshold",
        ), use_container_width=True)
        st.caption(
            "Food ratio drives feedbacks B1 (capital allocation), B2 (mortality), "
            "B4 (fertility response). Above 1.0 = adequate; below 1.0 = stress."
        )

    with sub[4]:
        render_io_panel(
            "Agriculture",
            inputs=[
                "`pop` from Population (current year): denominator of "
                "food_per_capita",
                "`ag_investment` from Capital (current year): drives input "
                "multiplier and fertility investment",
                "`ppolx` from Pollution (prior year): reduces land yield "
                "via pollution_factor",
            ],
            outputs=[
                "`food_per_capita`, `food_ratio` to Nutrition (current year): "
                "calorie and protein supply",
                "`food_ratio` to Capital (next year): allocation shift B1",
                "`food_ratio` to Population (next year): mortality B2, fertility B4",
                "`ag_pollution` to Pollution (current year): fertilizer runoff",
            ],
            loops=[
                "B1 Food-investment (balancing) - closes via Capital",
                "R3 Pollution death-spiral (reinforcing) - closes via "
                "Pollution and Capital",
                "B2 and B4 originate here (food_ratio is the signal)",
            ],
            citation=(
                "Statistics Canada Table 32-10-0359-01 (Canada crop production); "
                "FAO FAOSTAT (Nigeria production, fertilizer); "
                "IPCC AR6 WGII Ch.5 (climate yield response); "
                "FAO Land Use Statistics"
            ),
        )

# ------------------------------------------------------------
# TAB 5: POLLUTION
# ------------------------------------------------------------
with tabs[4]:
    st.header("Pollution Sector")
    st.caption(
        "Single stock: persistent pollution (PP). Accumulates from industrial "
        "output, agricultural fertilizer use, and household waste. Absorbed "
        "by the environment, but absorption slows as PP rises (saturation). "
        "Index ppolx is normalised to the 1970 level."
    )

    sub = st.tabs([
        "Pollution stock", "Generation by source",
        "Absorption dynamics", "Inputs and outputs",
    ])

    with sub[0]:
        st.plotly_chart(line_chart(
            years,
            {"Active scenario": custom["ppolx"],
             "Baseline":        baseline["ppolx"]},
            "Pollution index (relative to 1970)", "Index (1.0 = 1970 level)",
            hline=1.0, hlabel="1970 baseline",
        ), use_container_width=True)
        st.caption(
            "Source: Environment Canada National Pollutant Release Inventory; "
            "WHO Ambient Air Quality Database; FAO Fertilizer Statistics."
        )

    with sub[1]:
        st.plotly_chart(stacked_area_chart(
            years,
            {"From industry":    custom["pp_gen_industry"],
             "From agriculture": custom["pp_gen_agriculture"],
             "From household waste": custom["pp_gen_waste"]},
            "Pollution generation by source", "Units per year",
            colors=[COLORS["secondary"], COLORS["accent"], COLORS["warning"]],
        ), use_container_width=True)
        st.caption(
            "Industrial pollution intensity declines with clean technology "
            "adoption. Agricultural pollution rises with fertilizer use. "
            "Household waste scales with population."
        )

    with sub[2]:
        st.plotly_chart(dual_axis_chart(
            years,
            {"y": custom["pp_abs"], "name": "Absorption rate"},
            {"y": custom["absorption_time"], "name": "Effective absorption time"},
            "Units per year", "Years",
            "Absorption rate and effective absorption time",
        ), use_container_width=True)
        st.caption(
            "As pollution accumulates, the environment's absorption time grows "
            "(saturation). This is the mechanism behind World3's overshoot "
            "behaviour: nature stops cleaning up fast enough."
        )

    with sub[3]:
        render_io_panel(
            "Pollution",
            inputs=[
                "`io` (industrial output) from Capital (current year): "
                "industrial pollution source",
                "`pop` from Population (current year): household waste",
                "`ag_pollution` from Agriculture (current year): fertilizer runoff",
            ],
            outputs=[
                "`ppolx` to Agriculture (next year): reduces land yield",
                "`ppolx` to Population (next year): raises mortality",
            ],
            loops=[
                "B3 Pollution absorption (balancing): environment absorbs "
                "until saturated",
                "R3 Pollution death-spiral (reinforcing): more pollution -> "
                "less food -> more intensive agriculture -> more pollution",
            ],
            citation=(
                "Environment Canada National Pollutant Release Inventory; "
                "WHO Ambient Air Quality Database; "
                "FAO FAOSTAT Fertilizer consumption; "
                "World Bank PM2.5 mean annual exposure"
            ),
        )

# ------------------------------------------------------------
# TAB 6: CLIMATE (IPCC SSP scenarios)
# ------------------------------------------------------------
with tabs[5]:
    st.header(f"Climate inputs to the model: {country_display}")
    st.caption(
        "Climate is an exogenous driver, not an endogenous sector. It affects "
        "agricultural yield through the climate_factor multiplier applied "
        "every year. Two modes are available, selected from the sidebar."
    )

    if climate_scenario is None:
        st.info(
            "**Current mode: Simple linear climate model.** "
            "The agriculture sector reduces yield by `climate_sensitivity` "
            "per year of warming after the year 2000. To use real IPCC AR6 "
            "trajectories instead, select an SSP scenario in the sidebar."
        )
        st.markdown("#### Climate factor over time (simple linear model)")
        st.plotly_chart(line_chart(
            years,
            {"Climate factor (custom)":  custom["climate_factor"],
             "Climate factor (baseline)": baseline["climate_factor"]},
            "Climate factor (1.0 = no damage; below 1.0 = yield reduction)",
            "Multiplier",
            hline=1.0, hlabel="No climate damage",
        ), use_container_width=True)
        st.caption(
            "The simple model: climate_factor = max(0.6, 1 - climate_sensitivity "
            "* years_since_2000). Calibrated values: Canada 0.001/yr, "
            "Nigeria 0.002/yr. Source: IPCC AR6 WGII Ch.5."
        )
    else:
        st.success(
            f"**Current mode: {custom.get('climate_scenario_name', climate_scenario)}.** "
            "Agriculture yield is driven by IPCC AR6 temperature, precipitation, "
            "and CO2 trajectories downscaled to the country's region."
        )

        region_label = ("Southern Ontario" if country == "canada"
                        else "Northern Nigeria (Savanna)")
        st.markdown(f"Regional baseline: **{region_label}**.")

        st.markdown("#### Temperature and CO2 trajectories")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(line_chart(
                years,
                {"Temperature (C)": custom["climate_temperature_c"]},
                "Regional growing-season temperature",
                "degrees Celsius",
            ), use_container_width=True)
        with c2:
            st.plotly_chart(line_chart(
                years,
                {"CO2 (ppm)": custom["climate_co2_ppm"]},
                "Atmospheric CO2 concentration",
                "parts per million",
                hline=420, hlabel="2024 level",
            ), use_container_width=True)

        st.markdown("#### Precipitation and combined climate stress on agriculture")
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(line_chart(
                years,
                {"Precipitation (mm)": custom["climate_precipitation_mm"]},
                "Annual growing-season precipitation",
                "millimetres",
            ), use_container_width=True)
        with c4:
            st.plotly_chart(line_chart(
                years,
                {"Climate stress factor": custom["climate_stress_factor"]},
                "Climate stress factor applied to yield "
                "(temp x precip x CO2 fertilisation)",
                "Multiplier (1.0 = no stress)",
                hline=1.0, hlabel="No stress",
            ), use_container_width=True)

        st.markdown("#### CO2 nutrient dilution factors (Zhu et al. 2018, Nature Plants)")
        st.caption(
            "Elevated CO2 reduces protein, iron, and zinc per unit weight of "
            "edible crop. These factors are applied to per-tonne nutrient values "
            "when computing per-capita supply."
        )
        st.plotly_chart(line_chart(
            years,
            {"Protein retention": custom["climate_protein_degradation"],
             "Iron retention":    custom["climate_iron_degradation"],
             "Zinc retention":    custom["climate_zinc_degradation"]},
            "CO2 nutrient retention factors",
            "Fraction of original nutrient content",
            hline=1.0, hlabel="No dilution",
        ), use_container_width=True)

        st.caption(
            "Sources: IPCC AR6 WGI 2021 Table SPM.1 (SSP warming trajectories); "
            "Zhu et al. 2018 Nature Plants (CO2 nutrient dilution); "
            "regional baselines from CMIP6 ensemble averages."
        )

    st.markdown("---")
    st.markdown("### How climate connects to other sectors")
    st.markdown(
        "- **Climate -> Agriculture**: climate_factor multiplies effective yield "
        "in the food production calculation.  \n"
        "- **CO2 -> Nutrition** (if SSP active): protein, iron, zinc per-tonne "
        "values are degraded by CO2 fertilisation effects, propagating to the "
        "per-crop nutrient analysis in the Nutrition tab.  \n"
        "- Climate does NOT directly affect Population, Capital, or Pollution "
        "in this model; its effects flow through Agriculture and Nutrition."
    )

# ------------------------------------------------------------
# TAB 7: NUTRITION AND CROPS
# ------------------------------------------------------------
with tabs[6]:
    st.header(f"Nutrition and Crop-Level Analysis: {country_display}")
    st.caption(
        "Total food production is broken down by the country's actual crop mix, "
        "and per-capita nutrient supply is computed for each macronutrient and "
        "micronutrient. Adequacy ratios are relative to WHO/Health Canada daily "
        "requirements for an average adult."
    )

    sub_n = st.tabs([
        "Macronutrient adequacy",
        "Crop mix editor",
        "Per-crop contributions",
        "Nutrition gap heatmap",
        "Policy insight",
    ])

    # --- Macronutrient adequacy ---
    with sub_n[0]:
        st.markdown(f"#### Snapshot at year {year_end} (responds to crop mix changes)")
        st.markdown(
            "The four tiles below recompute from the **current crop mix** "
            "(set in the next sub-tab). Edit the mix and the numbers here "
            "update immediately. The delta shows the difference vs the World3 "
            "aggregate value, which uses a country-average kcal/kg and "
            "protein/kg derived from the country's typical diet composition."
        )

        active_mix_summary = st.session_state.get(
            "custom_mix", COUNTRY_CROP_MIXES[country]
        )
        snapshot = compute_crop_nutrients(
            food_production_kg=custom["food_production"][-1],
            crop_mix=active_mix_summary,
            pop=custom["pop"][-1],
        )

        last = -1
        per_crop_cal = snapshot["adequacy"]["energy_kcal"]
        per_crop_prot = snapshot["adequacy"]["protein_kg"]
        per_crop_vita = snapshot["adequacy"]["vitamin_a_mg_rae"]
        per_crop_iron = snapshot["adequacy"]["iron_g"]

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                "Calorie adequacy",
                f"{per_crop_cal:.2f}",
                delta=f"{per_crop_cal - custom['calorie_adequacy'][last]:+.2f} vs World3",
                delta_color="normal",
            )
            st.caption(adequacy_label(per_crop_cal))
        with m2:
            st.metric(
                "Protein adequacy",
                f"{per_crop_prot:.2f}",
                delta=f"{per_crop_prot - custom['protein_adequacy'][last]:+.2f} vs World3",
                delta_color="normal",
            )
            st.caption(adequacy_label(per_crop_prot))
        with m3:
            st.metric(
                "Vitamin A adequacy",
                f"{per_crop_vita:.2f}",
            )
            st.caption(adequacy_label(per_crop_vita))
        with m4:
            st.metric(
                "Iron adequacy",
                f"{per_crop_iron:.2f}",
            )
            st.caption(adequacy_label(per_crop_iron))

        # Show which crops are contributing most to each headline nutrient
        st.markdown("##### Top contributing crops for each headline nutrient")
        cc1, cc2, cc3, cc4 = st.columns(4)
        nutrient_top = [
            ("energy_kcal",      "Calories",   cc1),
            ("protein_kg",       "Protein",    cc2),
            ("vitamin_a_mg_rae", "Vitamin A",  cc3),
            ("iron_g",           "Iron",       cc4),
        ]
        for nut_key, nut_label, col in nutrient_top:
            with col:
                st.markdown(f"**{nut_label}**")
                contribs = [
                    (CROP_DISPLAY_NAMES.get(ck, ck), v[nut_key])
                    for ck, v in snapshot["per_crop"].items()
                ]
                contribs.sort(key=lambda x: -x[1])
                top = contribs[:3]
                tot = sum(c[1] for c in contribs)
                for crop_name, val in top:
                    pct = (val / tot * 100) if tot > 0 else 0
                    st.markdown(f"- {crop_name}: {pct:.0f}%")

        st.markdown("---")
        st.markdown("#### World3 simulation aggregate trajectories")
        st.markdown(
            "These time-series come from the basic Nutrition sector using "
            "the country-average kcal/kg and protein/kg values "
            "(Canada 3500 kcal/kg, 110 g protein/kg; Nigeria 3200 kcal/kg, "
            "80 g protein/kg). They reflect the World3 model's headline "
            "trajectory and do **not** change when you edit the crop mix. "
            "Use them to track the simulated trajectory over time; use the "
            "snapshot tiles above and the next three sub-tabs to explore "
            "how specific crops affect outcomes."
        )
        st.plotly_chart(line_chart(
            years,
            {"Calorie adequacy": custom["calorie_adequacy"],
             "Protein adequacy": custom["protein_adequacy"]},
            "Calorie and protein adequacy", "Ratio to daily requirement",
            hline=1.0, hlabel="Adequate",
        ), use_container_width=True)
        st.plotly_chart(line_chart(
            years,
            {"Stunting risk (under 5)": custom["stunting_risk"],
             "Food security index":     custom["food_security_index"]},
            "Stunting risk and food security index", "Ratio / Score",
        ), use_container_width=True)
        st.caption(
            "Sources: FAO/WHO/UNU (2004) Human Energy Requirements; "
            "Black et al. (2013) Lancet 382:427-451 stunting model; "
            "UNICEF/WHO/World Bank Joint Child Malnutrition Estimates."
        )

    # --- Crop mix editor ---
    with sub_n[1]:
        # Display any pending notification from a previous action (add/remove)
        # before it gets overwritten by the next interaction.
        if "_crop_msg" in st.session_state:
            msg_type, msg_text = st.session_state["_crop_msg"]
            if msg_type == "success":
                st.success(msg_text)
            elif msg_type == "info":
                st.info(msg_text)
            del st.session_state["_crop_msg"]

        st.markdown(f"### {country_display} crop mix (share of food production by mass)")
        st.markdown(
            "Adjust the slider for each crop to change its share of food "
            "production. To introduce a new crop into the mix, use the "
            "'Add a new crop' control further down. Shares are automatically "
            "renormalised to 100 percent. The 'Per-crop contributions', "
            "'Nutrition gap heatmap', and 'Policy insight' sub-tabs update "
            "to reflect any changes you make here."
        )

        default_mix = COUNTRY_CROP_MIXES[country].copy()

        # Track user-added crops in session state, keyed by country so that
        # Canada and Nigeria each maintain their own customisations.
        added_key = f"added_crops_{country}"
        if added_key not in st.session_state:
            st.session_state[added_key] = {}

        # The mix the user is editing = country baseline + any crops they've added
        editable_mix = {**default_mix, **st.session_state[added_key]}

        st.markdown("#### Edit crop shares")
        col1, col2 = st.columns(2)
        custom_mix = {}
        items = list(editable_mix.items())
        midpoint = (len(items) + 1) // 2

        def _render_crop_slider(crop_key, default_value):
            display_name = CROP_DISPLAY_NAMES.get(crop_key, crop_key)
            is_added = crop_key in st.session_state[added_key]
            label = display_name + ("   [added]" if is_added else "")
            return st.slider(
                label, 0.0, 0.6, float(default_value), 0.01,
                key=f"mix_{country}_{crop_key}",
                format="%.2f",
            )

        with col1:
            for crop_key, default_share in items[:midpoint]:
                custom_mix[crop_key] = _render_crop_slider(crop_key, default_share)
        with col2:
            for crop_key, default_share in items[midpoint:]:
                custom_mix[crop_key] = _render_crop_slider(crop_key, default_share)

        st.markdown("---")

        # Add new crop section
        st.markdown("#### Add a new crop to the mix")
        st.markdown(
            "Pick any crop from the FAO/INFOODS profile set that is not already "
            "in the mix. Set its initial share and click **Add to mix**. The new "
            "crop will appear as a slider above, and the next sub-tabs will "
            "include it in the analysis."
        )
        existing = set(custom_mix.keys())
        available_new = sorted(
            [k for k in CROP_NUTRIENT_PROFILES.keys() if k not in existing],
            key=lambda k: CROP_DISPLAY_NAMES.get(k, k),
        )

        if available_new:
            ac1, ac2, ac3 = st.columns([3, 1, 1])
            with ac1:
                picked_crop = st.selectbox(
                    "Crop to add",
                    available_new,
                    format_func=lambda k: CROP_DISPLAY_NAMES.get(k, k),
                    key=f"pick_new_{country}",
                )
            with ac2:
                initial_share = st.number_input(
                    "Initial share",
                    min_value=0.01, max_value=0.30,
                    value=0.05, step=0.01,
                    key=f"new_share_{country}",
                    format="%.2f",
                    help="The new crop's starting fraction of food production. "
                         "You can adjust it with its slider after adding.",
                )
            with ac3:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("Add to mix", key=f"add_btn_{country}",
                             type="primary", use_container_width=True):
                    st.session_state[added_key][picked_crop] = initial_share
                    st.session_state["_crop_msg"] = (
                        "success",
                        f"Added {CROP_DISPLAY_NAMES.get(picked_crop, picked_crop)} "
                        f"at {initial_share*100:.0f} percent. Adjust its slider above.",
                    )
                    st.rerun()
        else:
            st.info("All available crops are already in the mix.")

        # Remove added crops
        if st.session_state[added_key]:
            st.markdown("#### Remove a previously added crop")
            add_list = list(st.session_state[added_key].keys())
            n_buttons = min(4, len(add_list))
            rm_cols = st.columns(n_buttons)
            for i, ck in enumerate(add_list):
                with rm_cols[i % n_buttons]:
                    if st.button(
                        f"Remove {CROP_DISPLAY_NAMES.get(ck, ck)}",
                        key=f"rm_btn_{country}_{ck}",
                        use_container_width=True,
                    ):
                        del st.session_state[added_key][ck]
                        slider_state_key = f"mix_{country}_{ck}"
                        if slider_state_key in st.session_state:
                            del st.session_state[slider_state_key]
                        st.session_state["_crop_msg"] = (
                            "info",
                            f"Removed {CROP_DISPLAY_NAMES.get(ck, ck)} from the mix.",
                        )
                        st.rerun()

        # Normalise so shares sum to 100 percent
        total = sum(custom_mix.values())
        if total > 0:
            normalised_mix = {k: v / total for k, v in custom_mix.items()}
        else:
            normalised_mix = dict(custom_mix)

        st.session_state["custom_mix"] = normalised_mix

        st.markdown("---")
        st.markdown("#### Resulting crop mix (after renormalisation to 100 percent)")
        mix_rows = []
        for k in sorted(normalised_mix.keys(), key=lambda x: -normalised_mix[x]):
            mix_rows.append({
                "Crop": CROP_DISPLAY_NAMES.get(k, k),
                "Share": f"{normalised_mix[k]*100:.1f}%",
                "Source": "Country baseline" if k in default_mix else "User added",
            })
        st.dataframe(pd.DataFrame(mix_rows), hide_index=True,
                     use_container_width=True)
        st.caption(
            "Default mix sources: Statistics Canada Table 32-10-0359-01 and "
            "Table 32-10-0365-01 for Canada; FAO FAOSTAT and Nigeria Bureau of "
            "Statistics for Nigeria (2020-2023 averages)."
        )

    # --- Per-crop contributions ---
    with sub_n[2]:
        st.markdown(f"### Per-crop nutrient contribution at year {year_end}")

        active_mix = st.session_state.get("custom_mix", COUNTRY_CROP_MIXES[country])

        crop_analysis = compute_crop_nutrients(
            food_production_kg=custom["food_production"][-1],
            crop_mix=active_mix,
            pop=custom["pop"][-1],
        )

        st.markdown(
            "Each card shows what fraction of the daily per-person requirement "
            "for each nutrient comes from that specific crop. Cards are sorted "
            "by share of the crop mix."
        )

        crops_sorted = sorted(active_mix.items(), key=lambda kv: -kv[1])
        n_cols = 3
        for i in range(0, len(crops_sorted), n_cols):
            row = crops_sorted[i:i + n_cols]
            cols = st.columns(n_cols)
            for col, (crop_key, share) in zip(cols, row):
                with col:
                    display_name = CROP_DISPLAY_NAMES.get(crop_key, crop_key)
                    contrib = crop_analysis["per_crop"][crop_key]
                    prod_t = contrib["total_production_tonnes"]
                    food_t = contrib["effective_food_tonnes"]
                    st.markdown(f"**{display_name}** ({share*100:.1f}%)")
                    st.markdown(
                        f"Production: {prod_t/1e6:.2f} Mt/year  \n"
                        f"To food (after losses, non-food use): "
                        f"{food_t/1e6:.2f} Mt/year"
                    )
                    # Show the headline nutrients contributed
                    for nutrient_key in ["energy_kcal", "protein_kg",
                                          "vitamin_a_mg_rae"]:
                        label, unit = NUTRIENT_DISPLAY[nutrient_key]
                        per_cap = contrib[nutrient_key] * NUTRIENT_DISPLAY_SCALE[nutrient_key]
                        req = DAILY_REQUIREMENTS[nutrient_key] * NUTRIENT_DISPLAY_SCALE[nutrient_key]
                        pct = (per_cap / req * 100) if req > 0 else 0
                        st.markdown(
                            f"- {label}: {per_cap:.1f} {unit} "
                            f"({pct:.1f}% of need)"
                        )

        st.caption(
            "Per-crop nutrient profiles: FAO/INFOODS Food Composition Tables "
            "(2022), USDA FoodData Central, FAO West African Food Composition "
            "Table (FAO 2019). Post-harvest losses and food-use fractions from "
            "FAO methodology."
        )

    # --- Nutrition gap heatmap ---
    with sub_n[3]:
        st.markdown(f"### Per-nutrient adequacy: baseline vs current mix, year {year_end}")

        active_mix = st.session_state.get("custom_mix", COUNTRY_CROP_MIXES[country])

        baseline_analysis = compute_crop_nutrients(
            food_production_kg=custom["food_production"][-1],
            crop_mix=COUNTRY_CROP_MIXES[country],
            pop=custom["pop"][-1],
        )
        current_analysis = compute_crop_nutrients(
            food_production_kg=custom["food_production"][-1],
            crop_mix=active_mix,
            pop=custom["pop"][-1],
        )

        # Build comparison table
        nutrient_keys = list(DAILY_REQUIREMENTS.keys())
        rows = []
        for nut in nutrient_keys:
            label, unit = NUTRIENT_DISPLAY[nut]
            base_adq = baseline_analysis["adequacy"][nut]
            curr_adq = current_analysis["adequacy"][nut]
            rows.append({
                "Nutrient": label,
                "Daily requirement": (
                    f"{DAILY_REQUIREMENTS[nut] * NUTRIENT_DISPLAY_SCALE[nut]:.1f} {unit}"
                ),
                "Baseline adequacy": f"{base_adq:.2f}",
                "Baseline status": adequacy_label(base_adq),
                "Custom mix adequacy": f"{curr_adq:.2f}",
                "Custom mix status": adequacy_label(curr_adq),
                "Change": f"{curr_adq - base_adq:+.2f}",
            })
        df_gap = pd.DataFrame(rows)
        st.dataframe(df_gap, hide_index=True, use_container_width=True)

        # Bar chart comparison
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[NUTRIENT_DISPLAY[k][0] for k in nutrient_keys],
            y=[baseline_analysis["adequacy"][k] for k in nutrient_keys],
            name="Baseline mix",
            marker_color=COLORS["primary"],
        ))
        fig.add_trace(go.Bar(
            x=[NUTRIENT_DISPLAY[k][0] for k in nutrient_keys],
            y=[current_analysis["adequacy"][k] for k in nutrient_keys],
            name="Custom mix",
            marker_color=COLORS["accent"],
        ))
        fig.add_hline(y=1.0, line_dash="dot", line_color=COLORS["secondary"],
                      annotation_text="Daily requirement met", annotation_position="top right")
        fig.update_layout(
            title=dict(text="Adequacy ratio by nutrient (1.0 = daily requirement met)",
                       font=dict(size=14)),
            yaxis_title="Adequacy ratio",
            height=420, template="plotly_white",
            barmode="group",
            margin=dict(l=60, r=20, t=50, b=40),
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Nutrient profile values verified against USDA FoodData Central "
            "(Standard Reference Legacy) and FAO West African Food Composition "
            "Table (FAO 2019), per-100g composition converted to per-tonne "
            "using consistent unit rules documented in nutrient_converter.py. "
            "Adequacy ratios are capped at 1.5 for display."
        )

    # --- Policy insight ---
    with sub_n[4]:
        active_mix = st.session_state.get("custom_mix", COUNTRY_CROP_MIXES[country])

        baseline_analysis = compute_crop_nutrients(
            food_production_kg=custom["food_production"][-1],
            crop_mix=COUNTRY_CROP_MIXES[country],
            pop=custom["pop"][-1],
        )
        current_analysis = compute_crop_nutrients(
            food_production_kg=custom["food_production"][-1],
            crop_mix=active_mix,
            pop=custom["pop"][-1],
        )

        st.markdown("### Identified nutrition gaps (year " + str(year_end) + ")")
        gaps = [(NUTRIENT_DISPLAY[k][0], v) for k, v in current_analysis["adequacy"].items() if v < 1.0]
        gaps.sort(key=lambda t: t[1])

        if not gaps:
            st.success("All tracked nutrient adequacy ratios are at or above 1.0 in the current scenario.")
        else:
            for label, val in gaps:
                st.markdown(f"- **{label}**: adequacy {val:.2f} ({adequacy_label(val)})")

        # Suggested crops to address gaps
        st.markdown("### Crop options for closing identified gaps")
        # Rank crops by nutrient content
        for crit_nut_key in ["vitamin_a_mg_rae", "protein_kg", "iron_g", "zinc_g"]:
            if current_analysis["adequacy"][crit_nut_key] < 1.0:
                label, unit = NUTRIENT_DISPLAY[crit_nut_key]
                st.markdown(f"**To increase {label}** consider crops rich in this nutrient:")
                ranked = sorted(
                    [(k, getattr(p, crit_nut_key, 0))
                     for k, p in CROP_NUTRIENT_PROFILES.items()],
                    key=lambda kv: -kv[1],
                )[:5]
                for ck, val in ranked:
                    display_name = CROP_DISPLAY_NAMES.get(ck, ck)
                    in_mix = " (already in mix)" if ck in active_mix else ""
                    st.markdown(f"  - {display_name}: {val:.0f} per tonne{in_mix}")

        st.caption(
            "Policy interventions can include crop diversification, "
            "biofortification programmes, agricultural extension, and dietary "
            "guidelines. Sources for crop rankings: FAO/INFOODS (2022); USDA FoodData Central."
        )

# ------------------------------------------------------------
# TAB 8: CASCADE LAB
# ------------------------------------------------------------
with tabs[7]:
    st.header("Cascade Lab: trace one change through the entire system")
    st.markdown(
        "Pick a single parameter to change relative to the baseline, then "
        "see how the change propagates through every sector. The blue line is "
        "the country's calibrated baseline; the orange line is the modified "
        "scenario. The chain of consequence is explained below."
    )

    # The cascade lab uses the existing custom vs baseline runs from the sidebar
    casc_metric_options = {
        "Population": ("pop", "Millions", 1e-6),
        "Industrial output": ("io", "Billion USD/year", 1e-9),
        "Capital allocation to agriculture": ("fioaa", "Percent", 100),
        "Food per capita": ("food_per_capita", "kg/person/year", 1.0),
        "Food ratio": ("food_ratio", "Ratio", 1.0),
        "Pollution index": ("ppolx", "Relative to 1970", 1.0),
        "Calorie adequacy": ("calorie_adequacy", "Ratio to req", 1.0),
        "Stunting risk": ("stunting_risk", "Fraction", 1.0),
    }

    st.markdown("### Side-by-side: baseline vs modified scenario")

    cas_cols = st.columns(2)
    selected_metrics = list(casc_metric_options.items())
    for i, (label, (key, ylabel, scale)) in enumerate(selected_metrics):
        target_col = cas_cols[i % 2]
        with target_col:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=years, y=baseline[key] * scale, name="Baseline (calibrated)",
                line=dict(color=COLORS["primary"], width=2.4),
            ))
            fig.add_trace(go.Scatter(
                x=years, y=custom[key] * scale, name="Modified scenario",
                line=dict(color=COLORS["secondary"], width=2.4),
            ))
            fig.add_vline(x=2025, line_dash="dash", line_color=COLORS["neutral"],
                          opacity=0.4)
            fig.update_layout(
                title=dict(text=label, font=dict(size=13)),
                yaxis_title=ylabel, height=290, template="plotly_white",
                margin=dict(l=50, r=20, t=40, b=30),
                legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center",
                            font=dict(size=10)),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### What changed, and how the cascade flowed")

    diffs = []
    delta_tfr = slider_tfr - base_pop.total_fertility_rate
    delta_yield = slider_yield - base_ag.tech_yield_growth_rate
    delta_fioaa = slider_fioaa - base_cap.fioaa_base
    delta_pol = slider_pol_decline - base_pol.pollution_intensity_decline
    delta_immig = slider_immig - base_pop.immigration_rate
    delta_climate = slider_climate - base_ag.climate_sensitivity
    delta_mort = slider_mort_imp - base_pop.mortality_improvement_rate

    if abs(delta_tfr) > 0.01:
        diffs.append(f"Initial TFR changed by {delta_tfr:+.2f} children/woman")
    if abs(delta_yield) > 0.0001:
        diffs.append(f"Yield technology growth changed by {delta_yield*100:+.2f}%/yr")
    if abs(delta_fioaa) > 0.001:
        diffs.append(f"Baseline agricultural allocation changed by {delta_fioaa*100:+.1f}%")
    if abs(delta_pol) > 0.0001:
        diffs.append(f"Pollution intensity decline changed by {delta_pol*100:+.2f}%/yr")
    if abs(delta_immig) > 0.0001:
        diffs.append(f"Immigration rate changed by {delta_immig*100:+.2f}% of population/yr")
    if abs(delta_climate) > 0.00001:
        diffs.append(f"Climate sensitivity changed by {delta_climate:+.4f}")
    if abs(delta_mort) > 0.0001:
        diffs.append(f"Mortality improvement rate changed by {delta_mort*100:+.2f}%/yr")

    if not diffs:
        st.info(
            "No parameters have been changed from the baseline yet. "
            "Move sliders in the sidebar to see a cascade."
        )
    else:
        st.markdown("**Parameter changes from baseline:**")
        for d in diffs:
            st.markdown(f"- {d}")

        # Final-year deltas across sectors
        last = -1
        st.markdown("**Resulting changes at year " + str(year_end) + ":**")
        outcome_metrics = [
            ("Population (millions)", "pop", 1e-6),
            ("Industrial output (billion USD)", "io", 1e-9),
            ("Food per capita (kg/yr)", "food_per_capita", 1.0),
            ("Pollution index", "ppolx", 1.0),
            ("Calorie adequacy", "calorie_adequacy", 1.0),
            ("Stunting risk (fraction)", "stunting_risk", 1.0),
            ("Life expectancy (years)", "life_exp", 1.0),
            ("Food security index", "food_security_index", 1.0),
        ]
        outcome_rows = []
        for lbl, key, scale in outcome_metrics:
            b = baseline[key][last] * scale
            c = custom[key][last] * scale
            delta = c - b
            outcome_rows.append({
                "Metric": lbl,
                "Baseline": f"{b:,.2f}",
                "Modified": f"{c:,.2f}",
                "Delta": f"{delta:+,.2f}",
                "Percent change": (f"{(delta/b)*100:+.1f}%" if abs(b) > 1e-9 else "n/a"),
            })
        st.dataframe(pd.DataFrame(outcome_rows), hide_index=True,
                     use_container_width=True)

# ------------------------------------------------------------
# TAB 9: FEEDBACK LOOPS
# ------------------------------------------------------------
with tabs[8]:
    st.header("Feedback loops in this model")
    st.markdown(
        "The model contains seven named feedback loops. Each is a closed "
        "chain of cause and effect. Balancing loops (B) counter disturbances; "
        "reinforcing loops (R) amplify them. Behaviour over time depends on "
        "which loops dominate."
    )

    loop_options = {
        "B1: Food-Investment (balancing)": "b1",
        "B2: Food-Mortality (balancing)": "b2",
        "B3: Pollution Absorption (balancing)": "b3",
        "B4: Food-Fertility (balancing)": "b4",
        "R1: Population Growth (reinforcing)": "r1",
        "R2: Capital Accumulation (reinforcing)": "r2",
        "R3: Pollution Spiral (reinforcing)": "r3",
    }
    loop_choice = st.radio(
        "Select a loop to inspect",
        list(loop_options.keys()),
        horizontal=False,
    )
    loop_code = loop_options[loop_choice]

    col_diag, col_chart = st.columns([1, 1.4])

    with col_diag:
        if loop_code == "b1":
            st.markdown("**Loop chain**")
            st.markdown(
                "```\n"
                "food_ratio decreases\n"
                "      ↓  (negative link)\n"
                "fioaa (capital allocation to ag) increases\n"
                "      ↓  (positive link)\n"
                "agricultural investment increases\n"
                "      ↓  (positive link)\n"
                "input multiplier and yield increase\n"
                "      ↓  (positive link)\n"
                "food ratio recovers (loop closes)\n"
                "```"
            )
            st.markdown(
                "**Type:** Balancing.  \n"
                "**Meaning:** When food becomes scarce, the country "
                "automatically directs more of its economy toward farming. "
                "Yields rise, partially compensating for the original shortage."
            )
        elif loop_code == "b2":
            st.markdown("**Loop chain**")
            st.markdown(
                "```\n"
                "food_ratio decreases\n"
                "      ↓\n"
                "mortality multiplier increases\n"
                "      ↓\n"
                "deaths in each cohort increase\n"
                "      ↓\n"
                "population decreases\n"
                "      ↓\n"
                "food per capita (= food / population) rises (closes)\n"
                "```"
            )
            st.markdown(
                "**Type:** Balancing.  \n"
                "**Meaning:** Starvation itself relieves food pressure by "
                "reducing the population that needs to be fed. Severe but real."
            )
        elif loop_code == "b3":
            st.markdown("**Loop chain**")
            st.markdown(
                "```\n"
                "PP (pollution stock) increases\n"
                "      ↓\n"
                "effective absorption time grows (saturation)\n"
                "      ↓\n"
                "absorption rate eventually exceeds generation\n"
                "      ↓\n"
                "PP stabilises or declines (loop closes)\n"
                "```"
            )
            st.markdown(
                "**Type:** Balancing.  \n"
                "**Meaning:** The environment absorbs pollution, but the "
                "absorption rate slows as the stock rises. The loop weakens "
                "as pollution accumulates."
            )
        elif loop_code == "b4":
            st.markdown("**Loop chain**")
            st.markdown(
                "```\n"
                "food_ratio decreases\n"
                "      ↓\n"
                "current TFR is reduced by food stress\n"
                "      ↓\n"
                "annual births decrease\n"
                "      ↓\n"
                "population growth slows (closes)\n"
                "```"
            )
            st.markdown(
                "**Type:** Balancing.  \n"
                "**Meaning:** Fertility responds to food stress; "
                "people delay or avoid births during shortages."
            )
        elif loop_code == "r1":
            st.markdown("**Loop chain**")
            st.markdown(
                "```\n"
                "population increases\n"
                "      ↓\n"
                "the prime-age cohort (P2) grows over time via maturation\n"
                "      ↓\n"
                "annual births rise (births = P2 * 0.5 * TFR / 30)\n"
                "      ↓\n"
                "population grows further (loop reinforces)\n"
                "```"
            )
            st.markdown(
                "**Type:** Reinforcing.  \n"
                "**Meaning:** Demographic momentum. Even after fertility "
                "drops, a young population keeps growing for decades."
            )
        elif loop_code == "r2":
            st.markdown("**Loop chain**")
            st.markdown(
                "```\n"
                "Industrial capital (IC) grows\n"
                "      ↓\n"
                "Industrial output IO = IC / icor increases\n"
                "      ↓\n"
                "Investment in IC (= IO * fioai) rises\n"
                "      ↓\n"
                "IC grows further (loop reinforces)\n"
                "```"
            )
            st.markdown(
                "**Type:** Reinforcing.  \n"
                "**Meaning:** Capital begets capital. Wealth and industrial "
                "capacity compound over time."
            )
        elif loop_code == "r3":
            st.markdown("**Loop chain**")
            st.markdown(
                "```\n"
                "Industrial output rises\n"
                "      ↓\n"
                "Pollution generation rises -> PP -> ppolx increases\n"
                "      ↓\n"
                "Land yield falls (pollution factor < 1)\n"
                "      ↓\n"
                "Food ratio falls -> ag investment rises (via B1)\n"
                "      ↓\n"
                "More fertilizer used -> agricultural pollution rises\n"
                "      ↓\n"
                "Pollution accelerates further (loop reinforces)\n"
                "```"
            )
            st.markdown(
                "**Type:** Reinforcing (vicious cycle).  \n"
                "**Meaning:** The harder we farm to compensate for damaged "
                "yields, the more we pollute, the worse yields get. Drives "
                "land fertility collapse."
            )

    with col_chart:
        if loop_code == "b1":
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=custom["food_ratio"],
                                     name="Food ratio", line=dict(color=COLORS["primary"])))
            fig.add_trace(go.Scatter(x=years, y=custom["fioaa"] * 100,
                                     name="Allocation to ag (%)", yaxis="y2",
                                     line=dict(color=COLORS["secondary"])))
            fig.update_layout(
                title="B1 in action: food ratio vs allocation to agriculture",
                template="plotly_white", height=420,
                yaxis=dict(title="Food ratio"),
                yaxis2=dict(title="Percent to agriculture", overlaying="y", side="right"),
                margin=dict(l=60, r=60, t=50, b=40),
                legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig, use_container_width=True)

        elif loop_code == "b2":
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=custom["food_ratio"],
                                     name="Food ratio", line=dict(color=COLORS["primary"])))
            fig.add_trace(go.Scatter(x=years, y=custom["cdr"], name="Death rate per 1000",
                                     yaxis="y2", line=dict(color=COLORS["secondary"])))
            fig.update_layout(
                title="B2 in action: food ratio vs death rate",
                template="plotly_white", height=420,
                yaxis=dict(title="Food ratio"),
                yaxis2=dict(title="Deaths per 1000", overlaying="y", side="right"),
                margin=dict(l=60, r=60, t=50, b=40),
                legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig, use_container_width=True)

        elif loop_code == "b3":
            st.plotly_chart(line_chart(
                years,
                {"Pollution generation": custom["pp_gen"],
                 "Pollution absorption": custom["pp_abs"]},
                "B3 in action: generation vs absorption", "Units per year",
                height=420,
            ), use_container_width=True)

        elif loop_code == "b4":
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=custom["food_ratio"],
                                     name="Food ratio", line=dict(color=COLORS["primary"])))
            fig.add_trace(go.Scatter(x=years, y=custom["tfr"],
                                     name="TFR", yaxis="y2",
                                     line=dict(color=COLORS["secondary"])))
            fig.update_layout(
                title="B4 in action: food ratio vs TFR",
                template="plotly_white", height=420,
                yaxis=dict(title="Food ratio"),
                yaxis2=dict(title="Children per woman", overlaying="y", side="right"),
                margin=dict(l=60, r=60, t=50, b=40),
                legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig, use_container_width=True)

        elif loop_code == "r1":
            st.plotly_chart(line_chart(
                years,
                {"Total population (M)": custom["pop"] / 1e6,
                 "P2 (15-44, M)":        custom["p2"] / 1e6,
                 "Annual births (M)":    custom["births"] / 1e6 * 50},
                "R1: population reinforcing growth",
                "Millions (births scaled x50 for visibility)",
                height=420,
            ), use_container_width=True)

        elif loop_code == "r2":
            st.plotly_chart(line_chart(
                years,
                {"Industrial capital (B USD)": custom["ic"] / 1e9,
                 "Industrial output (B USD/yr)": custom["io"] / 1e9},
                "R2: capital and output growth", "Billion USD",
                height=420,
            ), use_container_width=True)

        elif loop_code == "r3":
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=custom["ppolx"],
                                     name="Pollution index", line=dict(color=COLORS["secondary"])))
            fig.add_trace(go.Scatter(x=years, y=custom["lfert"],
                                     name="Land fertility (kg/ha)", yaxis="y2",
                                     line=dict(color=COLORS["accent"])))
            fig.update_layout(
                title="R3 in action: pollution index vs land fertility",
                template="plotly_white", height=420,
                yaxis=dict(title="Pollution index"),
                yaxis2=dict(title="Land fertility (kg/ha)",
                            overlaying="y", side="right"),
                margin=dict(l=60, r=60, t=50, b=40),
                legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown(
    f"**Model:** 5-sector coupled World3-style system dynamics, "
    f"dt = 1 year, explicit Euler integration. "
    f"**Implementation:** Built on PyWorld3 (Vanwynsberghe, 2021), itself "
    f"based on Meadows et al. (1972) *The Limits to Growth*. "
    f"**Calibration:** Statistics Canada, UN World Population Prospects 2024, "
    f"FAO FAOSTAT, World Bank WDI, WHO, IRCC, Environment Canada, "
    f"Penn World Table 10.01, FAO/INFOODS 2022, USDA FoodData Central."
)
