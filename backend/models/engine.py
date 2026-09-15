"""Orchestrator: run baseline Treasury NOM vs One Nation policy shock."""

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


def nom_path(years: np.ndarray, cap: float | None, cal: Calibration,
             near: float, long_run: float) -> np.ndarray:
    """Return the NOM *flow applied between t and t+1* for each year in `years`.

    The last year has no subsequent step; its path value is unused.
    Baseline: linear glide from `near` to `long_run` over three years.
    Policy: a hard cap for every year.
    """
    out = np.zeros(len(years), dtype=float)
    for i, y in enumerate(years):
        if cap is not None:
            out[i] = cap
            continue
        t = int(y) - cal.start_year
        if t <= 0:
            out[i] = near
        elif t >= 3:
            out[i] = long_run
        else:
            out[i] = near + (long_run - near) * (t / 3.0)
    return out


def student_share_path(years: np.ndarray, policy: bool, cal: Calibration,
                       policy_student_share: float) -> np.ndarray:
    if policy:
        return np.full(len(years), policy_student_share, dtype=float)
    # Baseline: student share eases slightly as NOM normalises
    out = np.zeros(len(years), dtype=float)
    for i, y in enumerate(years):
        t = int(y) - cal.start_year
        out[i] = cal.baseline_student_share * (1.0 - 0.04 * min(t, 5) / 5.0)
    return out


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
        nom_cap: float | None,
        student_share_policy: float,
        sigma: float,
        sigma_L: float,
        alpha: float,
        tfp_growth: float,
        delta_k: float,
        real_rate: float,
        lam: float,
        housing_supply_elasticity: float,
        income_elasticity: float,
        baseline_nom_near: float,
        baseline_nom_long: float,
        start_state: DemographicState | None = None,
    ) -> list[YearRecord]:
        cal = self.cal
        years = np.arange(cal.start_year, cal.start_year + cal.horizon_years)
        noms = nom_path(years, nom_cap, cal, baseline_nom_near, baseline_nom_long)
        shares = student_share_path(
            years, policy=nom_cap is not None, cal=cal,
            policy_student_share=student_share_policy,
        )

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
        )
        fiscal = FiscalModel(cal)

        records: list[YearRecord] = []
        prev_pop = float(state.total().sum())
        prev_wage_index = 1.0
        prev_metrics = self.demo.metrics(state, births=0.0, deaths=0.0, nom=0.0, student_inflow=0.0)
        prev_metrics.year = state.year

        for i, year in enumerate(years):
            ld, lm, _pr = self.demo.labour_supply(state)
            ld *= emp_scale
            lm *= emp_scale
            # Overlay the employment-scaled labour onto metrics for reporting
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
                student_stock=state.student_stock,
                prev_wage_index=prev_wage_index,
            )
            fis_s = fiscal.evaluate(int(year), state, macro_s.y, macro_s.wage_domestic,
                                    macro_s.wage_migrant, ld, lm)
            rec = _record(m, macro_s, sec_s, fis_s)
            # NOM reported on a year is the flow that will arrive over the year
            rec.nom = float(noms[i]) if i < len(years) - 1 else float(noms[i])
            rec.student_inflow = rec.nom * float(shares[i])
            records.append(rec)

            prev_pop = pop
            prev_wage_index = macro_s.wage_index_avg
            macro.step_capital_and_tfp(macro_s)

            if i == len(years) - 1:
                break
            state, prev_metrics = self.demo.step(
                state, nom=float(noms[i]), student_share=float(shares[i])
            )

        return records

    def run_pair(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run Treasury baseline and One Nation shock with shared parameters."""
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
        near = float(o.get("baseline_nom_near", cal.baseline_nom_near_term))
        long_run = float(o.get("baseline_nom", cal.baseline_nom_long_run))
        nom_cap = float(o.get("nom_cap", cal.policy_nom_cap))
        pol_stu = float(o.get("policy_student_share", cal.policy_student_share))

        common = dict(
            student_share_policy=pol_stu,
            sigma=sigma,
            sigma_L=sigma_L,
            alpha=alpha,
            tfp_growth=tfp_growth,
            delta_k=delta_k,
            real_rate=real_rate,
            lam=lam,
            housing_supply_elasticity=hs,
            income_elasticity=eh,
            baseline_nom_near=near,
            baseline_nom_long=long_run,
        )
        start = self.demo.initial_state()
        baseline = self.run_scenario(nom_cap=None, start_state=start, **common)
        policy = self.run_scenario(nom_cap=nom_cap, start_state=start, **common)
        return {
            "baseline": baseline,
            "policy": policy,
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
                "baseline_nom_near": near,
                "baseline_nom_long": long_run,
                "nom_cap": nom_cap,
                "policy_student_share": pol_stu,
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
    }
