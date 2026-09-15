"""Fiscal identities: 8-year wait and revenue residual."""

from __future__ import annotations

from models.calibration import Calibration
from models.demographics import CohortComponentModel
from models.fiscal import FiscalModel


def test_fiscal_balance_equals_revenue_minus_outlays():
    cal = Calibration()
    demo = CohortComponentModel(cal)
    state = demo.initial_state()
    ld, lm, _ = demo.labour_supply(state)
    fiscal = FiscalModel(cal)
    y = cal.gdp_0
    # Rough average wages so labour income is about 62% of GDP
    w_d = 0.62 * y / max(ld + lm, 1.0)
    w_m = 0.94 * w_d
    s = fiscal.evaluate(2025, state, y, w_d, w_m, ld, lm)
    assert abs(s.revenue - (s.pit + s.cit + s.gst)) < 1.0
    assert abs(s.outlays - (s.age_pension + s.health + s.infrastructure
                            + s.other_transfers + s.gov_consumption)) < 1.0
    assert abs(s.balance - (s.revenue - s.outlays)) < 1.0
    assert s.health > 0 and s.age_pension > 0


def test_waiting_period_reduces_pension_outlays():
    cal = Calibration()
    demo = CohortComponentModel(cal)
    fiscal = FiscalModel(cal)
    state = demo.initial_state()
    ld, lm, _ = demo.labour_supply(state)
    y, w_d = cal.gdp_0, 90_000.0
    base = fiscal.evaluate(2025, state, y, w_d, 0.94 * w_d, ld, lm)

    # Force every foreign-born 67+ person into the recent (ineligible) ladder
    aged = state.settled[:, 67:].copy()
    state.settled[:, 67:] = 0.0
    state.recent[0, :, 67:] += aged
    shocked = FiscalModel(cal).evaluate(2025, state, y, w_d, 0.94 * w_d, ld, lm)
    assert shocked.age_pension < base.age_pension
    assert shocked.waiting_excluded_pensioners > base.waiting_excluded_pensioners
