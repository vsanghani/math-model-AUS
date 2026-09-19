"""Sectoral labour allocation and housing / education-export demand.

Four representative sectors:

* Construction & Housing
* Healthcare & Aged Care
* Education & Export Services
* General Industry

Housing demand

.. math::

    H^{d}_{t} = \\frac{N_t}{\\bar h_t} \\, (1 + \\varepsilon_h \\, \\Delta w_t)

is confronted with a near-term inelastic supply curve whose flow
elasticity is :math:`\\varepsilon_s`.  Rent pressure is a partial
pass-through of the proportional shortfall.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.calibration import Calibration, sector_base_shares


SECTOR_KEYS = (
    "construction_housing",
    "healthcare_aged_care",
    "education_export_services",
    "general_industry",
)

SECTOR_LABELS = {
    "construction_housing": "Construction & Housing",
    "healthcare_aged_care": "Healthcare & Aged Care",
    "education_export_services": "Education & Export Services",
    "general_industry": "General Industry",
}


@dataclass
class SectorState:
    year: int
    shares: dict[str, float]
    labour_demand: dict[str, float]
    labour_gap: dict[str, float]
    wage_pressure: dict[str, float]
    housing_demand: float
    housing_stock: float
    housing_shortfall: float
    shortfall_index: float
    rent_index: float
    household_size: float
    education_exports: float
    student_stock: float
    completions: float


class SectoralModel:
    def __init__(self, cal: Calibration, housing_supply_elasticity: float | None = None,
                 income_elasticity: float | None = None, skill_priority_tilt: float = 0.0):
        self.cal = cal
        self.eps_s = float(
            housing_supply_elasticity
            if housing_supply_elasticity is not None
            else cal.housing_supply_elasticity
        )
        self.eps_h = float(
            income_elasticity
            if income_elasticity is not None
            else cal.housing_demand_income_elasticity
        )
        # 0–1: Home Affairs skilled-list tilt toward construction, health, education
        self.skill_priority_tilt = float(np.clip(skill_priority_tilt, 0.0, 1.0))
        self.stock = float(cal.housing_stock_0)
        self.rent_index = 1.0
        self.hh_size = float(cal.avg_household_size_0)
        self.base_shares = sector_base_shares()
        self._pop0 = float(cal.population_0)
        self._old_share0: float | None = None
        self._student0 = float(cal.student_stock_0)

    def evaluate(
        self,
        year: int,
        population: float,
        old_share: float,
        pop_growth: float,
        wage_index: float,
        labour_total: float,
        student_stock: float,
        prev_wage_index: float,
    ) -> SectorState:
        if self._old_share0 is None:
            self._old_share0 = max(old_share, 1e-6)

        # Household size drifts slowly (ABS long-run decline)
        self.hh_size = max(self.hh_size + self.cal.hh_size_drift, 1.8)
        dw = wage_index / max(prev_wage_index, 1e-8) - 1.0
        h_demand = (population / self.hh_size) * (1.0 + self.eps_h * dw)

        # Completions respond to last period's rent gap and population growth.
        # Near-term supply is inelastic: ε_s << 1.
        natural_replacement = 0.012 * self.stock  # demolitions / replacement
        demand_pressure = (h_demand - self.stock * (1.0 - self.cal.housing_vacancy_target)) / max(
            self.stock, 1.0
        )
        completions = natural_replacement + self.eps_s * 0.04 * self.stock * np.tanh(
            3.0 * demand_pressure
        )
        # Population-driven baseline starts (pipeline)
        completions += 0.35 * max(pop_growth, 0.0) / max(self.hh_size, 1.0)
        completions = max(float(completions), 0.0)
        self.stock = max(self.stock + completions - 0.004 * self.stock, 0.5 * self.cal.housing_stock_0)

        shortfall = h_demand - self.stock * (1.0 - self.cal.housing_vacancy_target)
        shortfall_index = shortfall / max(h_demand, 1.0)
        # Rent: partial adjustment to proportional excess demand
        self.rent_index *= 1.0 + self.cal.rent_pass_through * np.clip(shortfall_index, -0.05, 0.20)
        self.rent_index = float(np.clip(self.rent_index, 0.6, 4.0))

        # --- Sectoral labour demand shares (renormalised) ---
        pop_g_term = np.clip(pop_growth / max(self._pop0, 1.0), -0.02, 0.04)
        old_rel = old_share / self._old_share0
        student_rel = student_stock / max(self._student0, 1.0)

        tilt = self.skill_priority_tilt
        raw = {
            "construction_housing": self.base_shares["construction_housing"]
            * (1.0 + 1.8 * max(shortfall_index, 0.0) + 4.0 * max(pop_g_term, 0.0))
            * (1.0 + 0.28 * tilt),
            "healthcare_aged_care": self.base_shares["healthcare_aged_care"]
            * (0.55 + 0.45 * old_rel)
            * (1.0 + 0.22 * tilt),
            "education_export_services": self.base_shares["education_export_services"]
            * (0.40 + 0.60 * student_rel)
            * (1.0 - 0.12 * tilt),
            "general_industry": self.base_shares["general_industry"] * (1.0 - 0.08 * tilt),
        }
        total_raw = sum(raw.values())
        shares = {k: v / total_raw for k, v in raw.items()}

        # Supply is assumed to start at the base mix and only slowly reallocate
        # (occupational friction).  Gap = demand − frictional supply.
        friction = 0.35  # share of workers who cannot switch this year
        labour_demand = {k: shares[k] * labour_total for k in SECTOR_KEYS}
        labour_supply = {
            k: (friction * self.base_shares[k] + (1.0 - friction) * shares[k]) * labour_total
            for k in SECTOR_KEYS
        }
        labour_gap = {k: labour_demand[k] - labour_supply[k] for k in SECTOR_KEYS}
        wage_pressure = {
            k: labour_gap[k] / max(labour_supply[k], 1.0) for k in SECTOR_KEYS
        }

        education_exports = float(student_stock * self.cal.spend_per_student)

        return SectorState(
            year=year,
            shares=shares,
            labour_demand=labour_demand,
            labour_gap=labour_gap,
            wage_pressure=wage_pressure,
            housing_demand=float(h_demand),
            housing_stock=float(self.stock),
            housing_shortfall=float(shortfall),
            shortfall_index=float(shortfall_index),
            rent_index=float(self.rent_index),
            household_size=float(self.hh_size),
            education_exports=education_exports,
            student_stock=float(student_stock),
            completions=float(completions),
        )
