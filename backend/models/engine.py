"""Orchestrator: current NOM vs Home Affairs (Burke Sep 2026) vs One Nation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from models.calibration import Calibration
from models.demographics import CohortComponentModel, DemographicState
from models.fiscal import FiscalModel
from models.macro import (
    MacroModel,
    calibrate_delta,
    infer_tfp,
    labour_headcount_scale,
    nested_labour,
    target_capital,
)
from models.sectors import SectoralModel
from models.temporary import policy_for


def scenario_nom(
    years: np.ndarray,
    scenario: str,
    *,
    current_nom: float,
    home_affairs_fy: float,
    home_affairs_long: float,
    one_nation_cap: float,
    announce_year: int = 2026,
) -> np.ndarray:
    """Calendar-year NOM flow applied between t and t+1.

    * ``current`` — ABS status quo (292.1k in the year to March 2026), held.
    * ``home_affairs`` — Burke NPC 17 Sep 2026: 245k in 2026, 225k from 2027.
    * ``one_nation`` — 130k cap from the announcement year.
    All scenarios share the observed current rate through the year before
    the announcement so the 2025 jump-off is identical.
    """
    out = np.zeros(len(years), dtype=float)
    for i, y in enumerate(years):
        year = int(y)
        if scenario == "current" or year < announce_year:
            out[i] = current_nom
        elif scenario == "home_affairs":
            out[i] = home_affairs_fy if year == announce_year else home_affairs_long
        elif scenario == "one_nation":
            out[i] = one_nation_cap
        else:
            raise ValueError(f"unknown NOM scenario: {scenario}")
    return out


def scenario_student_share(
    years: np.ndarray,
    scenario: str,
    *,
    current_share: float,
    home_affairs_share: float,
    one_nation_share: float,
    announce_year: int = 2026,
) -> np.ndarray:
    out = np.zeros(len(years), dtype=float)
    for i, y in enumerate(years):
        year = int(y)
        if scenario == "current" or year < announce_year:
            out[i] = current_share
        elif scenario == "home_affairs":
            out[i] = home_affairs_share
        elif scenario == "one_nation":
            out[i] = one_nation_share
        else:
            raise ValueError(f"unknown NOM scenario: {scenario}")
    return out


def forced_cut_path(
    years: np.ndarray,
    scenario: str,
    total_cut: float,
    n_years: int,
    announce_year: int = 2026,
) -> np.ndarray:
    """One Nation 750k temporary-stock rundown, allocated across n_years from the announcement."""
    out = np.zeros(len(years), dtype=float)
    if scenario != "one_nation" or n_years <= 0 or total_cut <= 0:
        return out
    annual = float(total_cut) / float(n_years)
    for i, y in enumerate(years):
        if announce_year <= int(y) < announce_year + n_years:
            out[i] = annual
    return out


def nom_path(years: np.ndarray, cap: float | None, cal: Calibration,
             near: float, long_run: float) -> np.ndarray:
    """Legacy helper used by older tests: glide or a hard cap."""
    if cap is not None:
        return scenario_nom(
            years, "one_nation",
            current_nom=near, home_affairs_fy=near, home_affairs_long=long_run,
            one_nation_cap=cap, announce_year=int(years[0]),
        )
    return np.full(len(years), long_run, dtype=float)


@dataclass
class YearRecord:
    year: int
    # demography
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
    temp_resident: float
    temp_headline: float
    temp_whm: float
    temp_skilled: float
    temp_overstayer: float
    temp_labour: float
    temp_forced_exits: float
    nom_applied: float
    # macro
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
    # housing / sectors
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
    # fiscal
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


def _record(
    demo_m,
    macro_s,
    sec_s,
    fis_s,
) -> YearRecord:
    return YearRecord(
        year=demo_m.year,
        population=demo_m.population,
        births=demo_m.births,
        deaths=demo_m.deaths,
        nom=demo_m.nom,
        student_inflow=demo_m.student_inflow,
        student_stock=demo_m.student_stock,
        working_age=demo_m.working_age,
        old_age=demo_m.old_age,
        prime_age=demo_m.prime_age,
        pension_age=demo_m.pension_age,
        dependency_ratio=demo_m.dependency_ratio,
        prime_working_age_share=demo_m.prime_working_age_share,
        participation_rate=demo_m.participation_rate,
        labour_native=demo_m.labour_native,
        labour_migrant=demo_m.labour_migrant,
        labour_total=demo_m.labour_total,
        native_pop=demo_m.native_pop,
        migrant_pop=demo_m.migrant_pop,
        recent_migrant_pop=demo_m.recent_migrant_pop,
        temp_resident=demo_m.temp_resident,
        temp_headline=demo_m.temp_headline,
        temp_whm=demo_m.temp_whm,
        temp_skilled=demo_m.temp_skilled,
        temp_overstayer=demo_m.temp_overstayer,
        temp_labour=demo_m.temp_labour,
        temp_forced_exits=demo_m.temp_forced_exits,
        nom_applied=demo_m.nom_applied,
        gdp=macro_s.y,
        gdp_per_capita=macro_s.gdp_per_capita,
        capital=macro_s.k,
        k_over_l=macro_s.k_over_l,
        tfp=macro_s.a,
        wage_domestic=macro_s.wage_domestic,
        wage_migrant=macro_s.wage_migrant,
        wage_index_d=macro_s.wage_index_d,
        wage_index_m=macro_s.wage_index_m,
        wage_index_avg=macro_s.wage_index_avg,
        investment=macro_s.investment,
        housing_demand=sec_s.housing_demand,
        housing_stock=sec_s.housing_stock,
        housing_shortfall=sec_s.housing_shortfall,
        shortfall_index=sec_s.shortfall_index,
        rent_index=sec_s.rent_index,
        household_size=sec_s.household_size,
        education_exports=sec_s.education_exports,
        completions=sec_s.completions,
        sector_shares=dict(sec_s.shares),
        sector_labour_gap=dict(sec_s.labour_gap),
        sector_wage_pressure=dict(sec_s.wage_pressure),
        pit=fis_s.pit,
        cit=fis_s.cit,
        gst=fis_s.gst,
        revenue=fis_s.revenue,
        age_pension=fis_s.age_pension,
        health=fis_s.health,
        infrastructure=fis_s.infrastructure,
        other_transfers=fis_s.other_transfers,
        gov_consumption=fis_s.gov_consumption,
        outlays=fis_s.outlays,
        fiscal_balance=fis_s.balance,
        fiscal_balance_to_gdp=fis_s.balance_to_gdp,
        consumption=fis_s.consumption,
        waiting_excluded_pensioners=fis_s.waiting_excluded_pensioners,
    )


class SimulationEngine:
    """Run a paired baseline / policy projection from a shared 2025 state."""

    def __init__(self, cal: Calibration):
        self.cal = cal
        self.demo = CohortComponentModel(cal)

    def _employment_scale(self, state: DemographicState) -> float:
        ld, lm, _ = self.demo.labour_supply(state)
        total = ld + lm
        if total <= 0:
            raise RuntimeError("zero labour supply at initialisation")
        return self.cal.employment_0 / total

    def run_scenario(
        self,
        *,
        noms: np.ndarray,
        student_shares: np.ndarray,
        sigma: float,
        sigma_L: float,
        alpha: float,
        tfp_growth: float,
        delta_k: float,
        real_rate: float,
        lam: float,
        housing_supply_elasticity: float,
        income_elasticity: float,
        skill_priority_tilt: float = 0.0,
        temp_scenario: str = "current",
        forced_cut_path: np.ndarray | None = None,
        start_state: DemographicState | None = None,
    ) -> list[YearRecord]:
        cal = self.cal
        years = np.arange(cal.start_year, cal.start_year + cal.horizon_years)
        if len(noms) != len(years) or len(student_shares) != len(years):
            raise ValueError("NOM and student-share paths must match the horizon")

        state = (start_state or self.demo.initial_state()).copy()
        emp_scale = self._employment_scale(state)

        ld0, lm0, _ = self.demo.labour_supply(state)
        ld0 *= emp_scale
        lm0 *= emp_scale
        delta = calibrate_delta(ld0, lm0, sigma_L, cal.migrant_wage_ratio)
        labour_scale = labour_headcount_scale(ld0, lm0, delta, sigma_L)
        labour0 = nested_labour(ld0, lm0, delta, sigma_L, labour_scale)
        k0 = cal.capital_output_ratio * cal.gdp_0
        a0 = infer_tfp(cal.gdp_0, k0, labour0, alpha, sigma)
        # Snap K onto the rental FOC so the first years are not a pure K* jump
        k_star0 = target_capital(a0, labour0, alpha, sigma, real_rate + delta_k)
        k0 = 0.85 * k0 + 0.15 * k_star0
        a0 = infer_tfp(cal.gdp_0, k0, labour0, alpha, sigma)

        macro = MacroModel(
            a0=a0, k0=k0, delta=delta, sigma=sigma, sigma_L=sigma_L,
            alpha=alpha, delta_k=delta_k, real_rate=real_rate, lam=lam,
            tfp_growth=tfp_growth,
        )
        macro.labour_scale = labour_scale
        sectors = SectoralModel(
            cal,
            housing_supply_elasticity=housing_supply_elasticity,
            income_elasticity=income_elasticity,
            skill_priority_tilt=skill_priority_tilt,
        )
        fiscal = FiscalModel(cal)

        records: list[YearRecord] = []
        prev_pop = float(state.total().sum())
        prev_wage_index = 1.0
        prev_metrics = self.demo.metrics(state, births=0.0, deaths=0.0, nom=0.0, student_inflow=0.0)
        prev_metrics.year = state.year
        cuts = forced_cut_path if forced_cut_path is not None else np.zeros(len(years))

        for i, year in enumerate(years):
            ld, lm, _pr = self.demo.labour_supply(state)
            ld *= emp_scale
            lm *= emp_scale
            m = prev_metrics
            m.labour_native = ld
            m.labour_migrant = lm
            m.labour_total = ld + lm
            pop = m.population
            old_share = m.old_age / max(pop, 1.0)
            pop_growth = pop - prev_pop if i > 0 else 0.0

            macro_s = macro.evaluate(int(year), ld, lm, pop)
            sec_s = sectors.evaluate(
                year=int(year),
                population=pop,
                old_share=old_share,
                pop_growth=pop_growth,
                wage_index=macro_s.wage_index_avg,
                labour_total=ld + lm,
                student_stock=state.temp.student,
                prev_wage_index=prev_wage_index,
                temp_resident=state.temp.resident(),
            )
            fis_s = fiscal.evaluate(int(year), state, macro_s.y, macro_s.wage_domestic,
                                    macro_s.wage_migrant, ld, lm)
            rec = _record(m, macro_s, sec_s, fis_s)
            rec.nom = float(noms[i]) - float(cuts[i])
            rec.student_inflow = max(rec.nom, 0.0) * float(student_shares[i])
            rec.student_stock = state.temp.student
            rec.temp_resident = state.temp.resident()
            rec.temp_headline = state.temp.headline()
            rec.temp_whm = state.temp.whm()
            rec.temp_skilled = state.temp.skilled
            rec.temp_overstayer = state.temp.overstayer
            rec.temp_labour = state.temp.labour_units()
            rec.nom_applied = rec.nom
            rec.temp_forced_exits = float(cuts[i])
            records.append(rec)

            prev_pop = pop
            prev_wage_index = macro_s.wage_index_avg
            macro.step_capital_and_tfp(macro_s)

            if i == len(years) - 1:
                break
            state, prev_metrics = self.demo.step(
                state,
                nom=float(noms[i]),
                student_share=float(student_shares[i]),
                temp_policy=policy_for(temp_scenario, cal, forced_cut=float(cuts[i])),
            )

        return records

    def run_pair(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run current NOM, Home Affairs (Burke), and One Nation from one jump-off."""
        o = overrides or {}
        cal = self.cal
        sigma = float(o.get("sigma", cal.sigma))
        sigma_L = float(o.get("sigma_L", cal.sigma_L))
        alpha = float(o.get("alpha", cal.alpha))
        tfp_growth = float(o.get("tfp_growth", cal.tfp_growth))
        delta_k = float(o.get("delta_k", cal.delta_k))
        real_rate = float(o.get("real_rate", cal.real_rate))
        lam = float(o.get("capital_adjust_lambda", cal.capital_adjust_lambda))
        hs = float(o.get("housing_supply_elasticity", cal.housing_supply_elasticity))
        eh = float(o.get("housing_demand_income_elasticity", cal.housing_demand_income_elasticity))
        current_nom = float(o.get("current_nom", cal.current_nom))
        ha_fy = float(o.get("home_affairs_fy_nom", cal.home_affairs_fy_nom))
        ha_long = float(o.get("home_affairs_long_run_nom", cal.home_affairs_long_run_nom))
        nom_cap = float(o.get("nom_cap", cal.policy_nom_cap))
        current_stu = float(o.get("current_student_share", cal.current_student_share))
        ha_stu = float(o.get("home_affairs_student_share", cal.home_affairs_student_share))
        on_stu = float(o.get("policy_student_share", cal.policy_student_share))
        on_cut = float(o.get("one_nation_temp_cut", cal.one_nation_temp_cut))
        on_cut_years = int(o.get("one_nation_temp_cut_years", cal.one_nation_temp_cut_years))
        ha_tilt = float(o.get("home_affairs_skill_tilt", 0.85))

        years = np.arange(cal.start_year, cal.start_year + cal.horizon_years)
        nom_kw = dict(
            current_nom=current_nom,
            home_affairs_fy=ha_fy,
            home_affairs_long=ha_long,
            one_nation_cap=nom_cap,
        )
        share_kw = dict(
            current_share=current_stu,
            home_affairs_share=ha_stu,
            one_nation_share=on_stu,
        )
        common = dict(
            sigma=sigma,
            sigma_L=sigma_L,
            alpha=alpha,
            tfp_growth=tfp_growth,
            delta_k=delta_k,
            real_rate=real_rate,
            lam=lam,
            housing_supply_elasticity=hs,
            income_elasticity=eh,
        )
        start = self.demo.initial_state()
        current = self.run_scenario(
            noms=scenario_nom(years, "current", **nom_kw),
            student_shares=scenario_student_share(years, "current", **share_kw),
            skill_priority_tilt=0.0,
            temp_scenario="current",
            start_state=start,
            **common,
        )
        home_affairs = self.run_scenario(
            noms=scenario_nom(years, "home_affairs", **nom_kw),
            student_shares=scenario_student_share(years, "home_affairs", **share_kw),
            skill_priority_tilt=ha_tilt,
            temp_scenario="home_affairs",
            start_state=start,
            **common,
        )
        one_nation = self.run_scenario(
            noms=scenario_nom(years, "one_nation", **nom_kw),
            student_shares=scenario_student_share(years, "one_nation", **share_kw),
            skill_priority_tilt=0.0,
            temp_scenario="one_nation",
            forced_cut_path=forced_cut_path(years, "one_nation", on_cut, on_cut_years),
            start_state=start,
            **common,
        )
        return {
            "current": current,
            "home_affairs": home_affairs,
            "one_nation": one_nation,
            "baseline": current,
            "policy": home_affairs,
            "parameters": {
                "sigma": sigma,
                "sigma_L": sigma_L,
                "alpha": alpha,
                "tfp_growth": tfp_growth,
                "delta_k": delta_k,
                "real_rate": real_rate,
                "capital_adjust_lambda": lam,
                "housing_supply_elasticity": hs,
                "housing_demand_income_elasticity": eh,
                "current_nom": current_nom,
                "home_affairs_fy_nom": ha_fy,
                "home_affairs_long_run_nom": ha_long,
                "nom_cap": nom_cap,
                "current_student_share": current_stu,
                "home_affairs_student_share": ha_stu,
                "policy_student_share": on_stu,
                "home_affairs_skill_tilt": ha_tilt,
                "one_nation_temp_cut": on_cut,
                "one_nation_temp_cut_years": on_cut_years,
                "start_year": cal.start_year,
                "end_year": cal.start_year + cal.horizon_years - 1,
            },
        }


def records_to_dicts(rows: list[YearRecord]) -> list[dict[str, Any]]:
    return [asdict(r) for r in rows]


def horizon_delta(baseline: list[YearRecord], policy: list[YearRecord],
                  years_ahead: int) -> dict[str, float]:
    """Differences at a horizon and cumulative sums over that window.

    `years_ahead=10` uses index 10 (2035 if start is 2025).  The 25-year
    window uses the last overlapping year (2050).
    """
    idx = min(years_ahead, len(baseline) - 1, len(policy) - 1)
    b, p = baseline[idx], policy[idx]
    window_b = baseline[: idx + 1]
    window_p = policy[: idx + 1]
    cum_gdp = sum(x.gdp for x in window_p) - sum(x.gdp for x in window_b)
    cum_fiscal = sum(x.fiscal_balance for x in window_p) - sum(
        x.fiscal_balance for x in window_b
    )
    avg_gdppc = (
        sum(x.gdp_per_capita for x in window_p) / (idx + 1)
        - sum(x.gdp_per_capita for x in window_b) / (idx + 1)
    )
    return {
        "year": p.year,
        "gdp_level": p.gdp - b.gdp,
        "gdp_pct": (p.gdp / b.gdp - 1.0) * 100.0,
        "gdp_per_capita_level": p.gdp_per_capita - b.gdp_per_capita,
        "gdp_per_capita_pct": (p.gdp_per_capita / b.gdp_per_capita - 1.0) * 100.0,
        "cumulative_gdp": cum_gdp,
        "avg_gdp_per_capita": avg_gdppc,
        "cumulative_fiscal": cum_fiscal,
        "fiscal_level": p.fiscal_balance - b.fiscal_balance,
        "rent_index_level": p.rent_index - b.rent_index,
        "rent_index_pct": (p.rent_index / b.rent_index - 1.0) * 100.0,
        "dependency_ratio_pp": (p.dependency_ratio - b.dependency_ratio) * 100.0,
        "population": p.population - b.population,
        "temp_resident": p.temp_resident - b.temp_resident,
        "temp_headline": p.temp_headline - b.temp_headline,
    }
