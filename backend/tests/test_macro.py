"""CES production, nested labour, and capital-deepening convergence."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from models.calibration import Calibration
from models.macro import (
    MacroModel,
    calibrate_delta,
    ces_combine,
    infer_tfp,
    labour_headcount_scale,
    mpk,
    nested_labour,
    target_capital,
)
from schemas import SimulationRequest


def test_cobb_douglas_limit_matches_closed_form():
    k, ell, a, alpha = 3.0, 1.5, 1.2, 0.4
    y_cd = a * (k**alpha) * (ell ** (1.0 - alpha))
    y_ces = a * ces_combine(k, ell, alpha, sigma=1.0)
    assert abs(y_ces - y_cd) / y_cd < 1e-10


def test_ces_homogeneous_of_degree_one():
    k, ell, alpha, sigma = 8.0, 3.0, 0.38, 0.9
    y = ces_combine(k, ell, alpha, sigma)
    y2 = ces_combine(2 * k, 2 * ell, alpha, sigma)
    assert abs(y2 / y - 2.0) < 1e-8


def test_tfp_inversion_roundtrip():
    y, k, ell, alpha, sigma = 2.7e12, 8.5e12, 14.45e6, 0.38, 0.9
    a = infer_tfp(y, k, ell, alpha, sigma)
    y_hat = a * ces_combine(k, ell, alpha, sigma)
    assert abs(y_hat / y - 1.0) < 1e-10


def test_target_capital_sets_mpk_to_rental():
    a, ell, alpha, sigma, rental = 1.0, 14.45e6, 0.38, 0.9, 0.10
    # Use a TFP consistent with Australian scale
    a = infer_tfp(2.7e12, 8.5e12, ell, alpha, sigma)
    k_star = target_capital(a, ell, alpha, sigma, rental)
    assert abs(mpk(a, k_star, ell, alpha, sigma) / rental - 1.0) < 1e-5


def test_capital_converges_to_k_star_with_fixed_labour():
    cal = Calibration()
    ld, lm = 9.8e6, 4.65e6
    delta = calibrate_delta(ld, lm, cal.sigma_L, cal.migrant_wage_ratio)
    scale = labour_headcount_scale(ld, lm, delta, cal.sigma_L)
    labour = nested_labour(ld, lm, delta, cal.sigma_L, scale)
    k0 = cal.capital_output_ratio * cal.gdp_0
    a0 = infer_tfp(cal.gdp_0, k0, labour, cal.alpha, cal.sigma)
    # Start K 20% below target, freeze TFP and labour
    k_star = target_capital(a0, labour, cal.alpha, cal.sigma, cal.real_rate + cal.delta_k)
    macro = MacroModel(
        a0=a0,
        k0=0.80 * k_star,
        delta=delta,
        sigma=cal.sigma,
        sigma_L=cal.sigma_L,
        alpha=cal.alpha,
        delta_k=cal.delta_k,
        real_rate=cal.real_rate,
        lam=0.25,
        tfp_growth=0.0,
    )
    macro.labour_scale = scale
    pop = cal.population_0
    for t in range(80):
        s = macro.evaluate(2025 + t, ld, lm, pop)
        macro.step_capital_and_tfp(s)
    assert abs(macro.k / k_star - 1.0) < 0.01


def test_lower_migrant_labour_raises_domestic_wage_when_substitutes():
    cal = Calibration()
    ld, lm = 9.8e6, 4.65e6
    delta = calibrate_delta(ld, lm, sigma_L=5.0, wage_ratio=0.94)
    scale = labour_headcount_scale(ld, lm, delta, 5.0)
    labour = nested_labour(ld, lm, delta, 5.0, scale)
    k = cal.capital_output_ratio * cal.gdp_0
    a = infer_tfp(cal.gdp_0, k, labour, cal.alpha, cal.sigma)
    m = MacroModel(
        a0=a, k0=k, delta=delta, sigma=cal.sigma, sigma_L=5.0,
        alpha=cal.alpha, delta_k=cal.delta_k, real_rate=cal.real_rate,
        lam=0.18, tfp_growth=0.0,
    )
    m.labour_scale = scale
    base = m.evaluate(2025, ld, lm, cal.population_0)
    shock = m.evaluate(2025, ld, 0.70 * lm, cal.population_0)
    assert shock.y < base.y
    assert shock.wage_migrant > base.wage_migrant
    assert shock.wage_migrant / shock.wage_domestic > base.wage_migrant / base.wage_domestic


def test_request_rejects_out_of_range_parameters():
    with pytest.raises(ValidationError):
        SimulationRequest(nom_cap=1_000)
    with pytest.raises(ValidationError):
        SimulationRequest(sigma_L=0.1)
    with pytest.raises(ValidationError):
        SimulationRequest(tfp_growth=0.5)
    with pytest.raises(ValidationError):
        SimulationRequest(housing_supply_elasticity=0.0)
    ok = SimulationRequest(nom_cap=130_000, sigma_L=6.5, tfp_growth=0.012)
    assert ok.nom_cap == 130_000
