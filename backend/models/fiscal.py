"""Commonwealth & State fiscal module.

Revenues
    * Personal income tax  — :math:`\\tau_y (w_d L_d + w_m L_m)`
    * Company tax          — :math:`\\tau_c (Y - w L)`  (capital residual)
    * GST                  — :math:`\\tau_g C_t`,  :math:`C_t = \\mathrm{mpc}\\, Y_t`

Outlays
    * Age Pension, scaled by the eligible population aged 67+
    * Health expenditure by single-year age cohort (AIHW gradient)
    * Infrastructure capex, scaled by population growth
    * Residual government consumption and working-age transfers

Policy rule
    New migrants face an **8-year waiting period** for social benefits /
    transfers (Age Pension and other personal transfers).  Health and
    infrastructure spending still follow the full resident population.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.calibration import Calibration, health_cost_by_age
from models.demographics import DemographicState


@dataclass
class FiscalState:
    year: int
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
    balance: float
    balance_to_gdp: float
    consumption: float
    labour_income: float
    capital_income: float
    waiting_excluded_pensioners: float


class FiscalModel:
    def __init__(self, cal: Calibration):
        self.cal = cal
        self.health_cost = health_cost_by_age()
        self._prev_pop: float | None = None

    def evaluate(
        self,
        year: int,
        state: DemographicState,
        y: float,
        w_d: float,
        w_m: float,
        ld: float,
        lm: float,
    ) -> FiscalState:
        tot = state.total()
        pop = float(tot.sum())
        labour_income = w_d * ld + w_m * lm
        capital_income = max(y - labour_income, 0.0)
        consumption = self.cal.mpc * y

        pit = self.cal.pit_rate * labour_income
        cit = self.cal.cit_rate * capital_income
        gst = self.cal.gst_effective * consumption
        revenue = pit + cit + gst

        # Eligible pensioners: 67+ excluding recent (waiting-period) migrants
        pension_age_stock = float(tot[:, 67:].sum())
        recent_pensioners = float(state.recent.sum(axis=0)[:, 67:].sum())
        eligible = max(pension_age_stock - recent_pensioners, 0.0)
        age_pension = self.cal.age_pension_avg * self.cal.pension_takeup * eligible

        health = float((tot * self.health_cost[np.newaxis, :]).sum())

        if self._prev_pop is None:
            dpop = 0.0
        else:
            dpop = pop - self._prev_pop
        self._prev_pop = pop
        infrastructure = self.cal.infrastructure_per_new_person * max(dpop, 0.0)
        # A floor of replacement / maintenance capex
        infrastructure += 0.012 * self.cal.gdp_0 * (pop / self.cal.population_0)

        # Working-age transfers: native + settled only (8-year wait)
        transfer_base = float(state.native.sum() + state.settled.sum())
        other_transfers = self.cal.other_transfer_per_capita * transfer_base

        gov_consumption = self.cal.gov_consumption_gdp * y

        outlays = age_pension + health + infrastructure + other_transfers + gov_consumption
        balance = revenue - outlays

        return FiscalState(
            year=year,
            pit=pit,
            cit=cit,
            gst=gst,
            revenue=revenue,
            age_pension=age_pension,
            health=health,
            infrastructure=infrastructure,
            other_transfers=other_transfers,
            gov_consumption=gov_consumption,
            outlays=outlays,
            balance=balance,
            balance_to_gdp=balance / max(y, 1.0),
            consumption=consumption,
            labour_income=labour_income,
            capital_income=capital_income,
            waiting_excluded_pensioners=recent_pensioners,
        )
