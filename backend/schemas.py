"""Pydantic v2 request / response schemas for the simulation API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SimulationRequest(BaseModel):
    """User-tunable overrides.  Omitted fields keep the ABS/Treasury defaults."""

    model_config = ConfigDict(extra="forbid")

    nom_cap: float = Field(
        default=130_000,
        ge=50_000,
        le=400_000,
        description="One Nation net overseas migration cap (persons / year).",
    )
    current_nom: float = Field(
        default=292_100,
        ge=50_000,
        le=500_000,
        description="ABS current NOM, year to March 2026 (status quo).",
    )
    home_affairs_fy_nom: float = Field(
        default=245_000,
        ge=50_000,
        le=500_000,
        description="Home Affairs 2026–27 NOM target (Burke, 17 Sep 2026).",
    )
    home_affairs_long_run_nom: float = Field(
        default=225_000,
        ge=50_000,
        le=500_000,
        description="Home Affairs NOM target from 2027–28.",
    )
    home_affairs_student_share: float = Field(
        default=0.27,
        ge=0.0,
        le=0.80,
        description="Student/temporary share after visa-hopping and family limits.",
    )
    home_affairs_skill_tilt: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Skilled-list tilt toward construction, health and education.",
    )
    sigma: float = Field(default=0.90, gt=0.2, le=3.0, description="K-L CES elasticity.")
    sigma_L: float = Field(
        default=5.0,
        gt=0.4,
        le=20.0,
        description="Domestic–migrant labour substitution elasticity.",
    )
    alpha: float = Field(default=0.38, gt=0.05, lt=0.95, description="CES capital share.")
    tfp_growth: float = Field(
        default=0.010,
        ge=-0.02,
        le=0.05,
        description="Annual TFP growth rate.",
    )
    delta_k: float = Field(default=0.055, gt=0.01, lt=0.20, description="Capital depreciation.")
    real_rate: float = Field(default=0.045, ge=0.0, le=0.12)
    capital_adjust_lambda: float = Field(default=0.18, gt=0.0, le=1.0)
    housing_supply_elasticity: float = Field(
        default=0.30,
        ge=0.05,
        le=3.0,
        description="Flow elasticity of dwelling completions.",
    )
    housing_demand_income_elasticity: float = Field(default=0.35, ge=0.0, le=2.0)
    policy_student_share: float = Field(default=0.16, ge=0.0, le=0.80)
    one_nation_temp_cut: float = Field(
        default=750_000,
        ge=0.0,
        le=2_000_000,
        description="One Nation temporary-visa stock rundown (persons, over three years).",
    )

    @field_validator("nom_cap", "current_nom", "home_affairs_fy_nom", "home_affairs_long_run_nom")
    @classmethod
    def _finite(cls, v: float) -> float:
        if not (v == v) or v in (float("inf"), float("-inf")):
            raise ValueError("must be a finite number")
        return v


class YearPoint(BaseModel):
    year: int
    population: float
    births: float
    deaths: float
    nom: float
    student_inflow: float
    student_stock: float
    working_age: float
    old_age: float
    prime_age: float
    pension_age: float
    dependency_ratio: float
    prime_working_age_share: float
    participation_rate: float
    labour_native: float
    labour_migrant: float
    labour_total: float
    native_pop: float
    migrant_pop: float
    recent_migrant_pop: float
    gdp: float
    gdp_per_capita: float
    capital: float
    k_over_l: float
    tfp: float
    wage_domestic: float
    wage_migrant: float
    wage_index_d: float
    wage_index_m: float
    wage_index_avg: float
    investment: float
    housing_demand: float
    housing_stock: float
    housing_shortfall: float
    shortfall_index: float
    rent_index: float
    household_size: float
    education_exports: float
    completions: float
    sector_shares: dict[str, float]
    sector_labour_gap: dict[str, float]
    sector_wage_pressure: dict[str, float]
    pit: float
    cit: float
    gst: float
    revenue: float
    age_pension: float
    health: float
    infrastructure: float
    other_transfers: float
    gov_consumption: float
    outlays: float
    fiscal_balance: float
    fiscal_balance_to_gdp: float
    consumption: float
    waiting_excluded_pensioners: float
    temp_resident: float
    temp_headline: float
    temp_whm: float
    temp_skilled: float
    temp_overstayer: float
    temp_labour: float
    temp_forced_exits: float
    nom_applied: float


class HorizonDelta(BaseModel):
    year: int
    gdp_level: float
    gdp_pct: float
    gdp_per_capita_level: float
    gdp_per_capita_pct: float
    cumulative_gdp: float
    avg_gdp_per_capita: float
    cumulative_fiscal: float
    fiscal_level: float
    rent_index_level: float
    rent_index_pct: float
    dependency_ratio_pp: float
    population: float
    temp_resident: float
    temp_headline: float


class ScenarioSeries(BaseModel):
    name: str
    series: list[YearPoint]


class SimulationResponse(BaseModel):
    current: ScenarioSeries
    home_affairs: ScenarioSeries
    one_nation: ScenarioSeries
    ha_deltas_10y: HorizonDelta
    ha_deltas_25y: HorizonDelta
    on_deltas_10y: HorizonDelta
    on_deltas_25y: HorizonDelta
    parameters: dict[str, Any]
    notes: str
