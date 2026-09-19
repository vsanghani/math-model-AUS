"""Demographic accounting identities and conservation properties."""

from __future__ import annotations

import numpy as np

from models.calibration import Calibration, initial_population, mortality_qx
from models.demographics import CohortComponentModel, conservation_residual


def test_initial_population_matches_calibration_total():
    cal = Calibration()
    pop = initial_population(cal)
    assert pop.shape == (2, 101)
    assert abs(pop.sum() - cal.population_0) / cal.population_0 < 1e-9
    assert np.all(pop >= 0)


def test_aging_conserves_mass_without_vital_events():
    model = CohortComponentModel(Calibration())
    state = model.initial_state()
    n0 = float(state.total().sum())
    qx = np.zeros_like(model.qx)
    asfr = np.zeros_like(model.asfr)
    nxt, metrics = model.step(
        state, nom=0.0, student_share=0.0, qx=qx, asfr=asfr, apply_births=True
    )
    assert abs(float(nxt.total().sum()) - n0) < 1e-4
    assert metrics.births == 0.0
    assert abs(metrics.deaths) < 1e-4
    # Everyone except the terminal cohort should have shifted up one age
    before = state.total()
    after = nxt.total()
    np.testing.assert_allclose(after[:, 1:100], before[:, 0:99], atol=1e-6)
    np.testing.assert_allclose(
        after[:, 100], before[:, 99] + before[:, 100], atol=1e-6
    )


def test_cohort_identity_with_mortality_births_and_nom():
    model = CohortComponentModel(Calibration())
    state = model.initial_state()
    before = state.total().copy()
    nom = 130_000.0
    nxt, metrics = model.step(state, nom=nom, student_share=0.20)
    residual = conservation_residual(
        before, nxt.total(), metrics.births, metrics.deaths, metrics.nom_applied
    )
    assert abs(residual) < 1.0  # within one person (float drift)
    assert metrics.deaths > 0
    assert metrics.births > 0
    assert abs(metrics.nom - nom) < 1e-6


def test_qx_in_unit_interval():
    qx = mortality_qx()
    assert qx.shape == (2, 101)
    assert np.all(qx >= 0.0) and np.all(qx < 1.0)
    # Female mortality should be lower at adult ages
    assert qx[1, 70] < qx[0, 70]


def test_dependency_ratio_and_participation_are_well_defined():
    model = CohortComponentModel(Calibration())
    state = model.initial_state()
    m = model.metrics(state, births=0, deaths=0, nom=0, student_inflow=0)
    assert 0.15 < m.dependency_ratio < 0.40  # ABS 65+/15-64 ~ 0.25-0.30
    assert 0.12 < m.prime_working_age_share < 0.50
    assert 0.50 < m.participation_rate < 0.80
    assert m.labour_total > 10e6


def test_policy_nom_reduces_population_relative_to_baseline():
    model = CohortComponentModel(Calibration())
    base = model.initial_state()
    pol = model.initial_state()
    for _ in range(10):
        base, _ = model.step(base, nom=235_000.0, student_share=0.34)
        pol, _ = model.step(pol, nom=130_000.0, student_share=0.16)
    assert pol.total().sum() < base.total().sum()
    # Student stock should be materially lower under the shock
    assert pol.student_stock < 0.85 * base.student_stock


def test_waiting_period_vintage_ladder_rolls_into_settled():
    model = CohortComponentModel(Calibration())
    state = model.initial_state()
    qx = np.zeros_like(model.qx)
    asfr = np.zeros_like(model.asfr)
    settled0 = float(state.settled.sum())
    # Feed a unit cohort for 8 years with no deaths
    for _ in range(8):
        state, _ = model.step(
            state, nom=1_000.0, student_share=0.0, qx=qx, asfr=asfr
        )
    # The first 1,000 should now have rolled into settled
    assert float(state.settled.sum()) > settled0 + 900
