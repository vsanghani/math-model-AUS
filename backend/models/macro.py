"""CES aggregate production core.

Headline output

.. math::

    Y_t = A_t \\left[ \\alpha K_t^{\\rho} + (1-\\alpha) L_t^{\\rho} \\right]^{1/\\rho},
    \\qquad \\rho = (\\sigma-1)/\\sigma

with nested labour

.. math::

    L_t = \\left[ \\delta L_{d,t}^{\\rho_L} + (1-\\delta) L_{m,t}^{\\rho_L}
        \\right]^{1/\\rho_L},
    \\qquad \\rho_L = (\\sigma_L-1)/\\sigma_L

Capital evolves by partial adjustment toward the competitive demand
:math:`K^\\star(L,A)` defined by :math:`\\mathrm{MPK} = r + \\delta_k`:

.. math::

    K_{t+1} = (1-\\lambda) K_t + \\lambda K^\\star_t

which is equivalent to replacement plus net investment
:math:`I_t = \\delta_k K_t + \\lambda (K^\\star_t - K_t)` inside
:math:`K_{t+1} = (1-\\delta_k)K_t + I_t`.  When labour growth slows,
:math:`K` is predetermined so :math:`K/L` rises (capital deepening).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

_RHO_EPS = 1e-6  # switch to Cobb-Douglas when |σ - 1| is this small


def _rho(sigma: float) -> float | None:
    if abs(sigma - 1.0) < 1e-4:
        return None
    return (sigma - 1.0) / sigma


def ces_combine(x: float, y: float, share: float, sigma: float) -> float:
    """Two-input CES aggregator with share parameter on `x`.

    Returns :math:`\\big[ s x^\\rho + (1-s) y^\\rho \\big]^{1/\\rho}`,
    or the Cobb-Douglas limit :math:`x^s y^{1-s}` when σ → 1.
    """
    x = max(float(x), 1e-12)
    y = max(float(y), 1e-12)
    share = float(np.clip(share, 1e-8, 1.0 - 1e-8))
    rho = _rho(sigma)
    if rho is None or abs(rho) < _RHO_EPS:
        return (x**share) * (y ** (1.0 - share))
    inner = share * x**rho + (1.0 - share) * y**rho
    inner = max(inner, 1e-18)
    return float(inner ** (1.0 / rho))


def infer_tfp(y: float, k: float, labour: float, alpha: float, sigma: float) -> float:
    """Invert the CES production function for :math:`A` given (Y, K, L)."""
    bundle = ces_combine(k, labour, alpha, sigma)
    if bundle <= 0:
        raise ValueError("non-positive CES bundle")
    return float(y / bundle)


def mpk(a: float, k: float, labour: float, alpha: float, sigma: float) -> float:
    """Marginal product of capital."""
    k = max(float(k), 1e-12)
    labour = max(float(labour), 1e-12)
    rho = _rho(sigma)
    if rho is None or abs(rho) < _RHO_EPS:
        return alpha * a * (labour / k) ** (1.0 - alpha)
    ces = ces_combine(k, labour, alpha, sigma)
    # ∂Y/∂K = A * α * K^{ρ-1} * CES^{1-ρ}
    return float(a * alpha * (k ** (rho - 1.0)) * (ces ** (1.0 - rho)))


def mpl(a: float, k: float, labour: float, alpha: float, sigma: float) -> float:
    """Marginal product of the labour aggregate."""
    k = max(float(k), 1e-12)
    labour = max(float(labour), 1e-12)
    rho = _rho(sigma)
    if rho is None or abs(rho) < _RHO_EPS:
        return (1.0 - alpha) * a * (k / labour) ** alpha
    ces = ces_combine(k, labour, alpha, sigma)
    return float(a * (1.0 - alpha) * (labour ** (rho - 1.0)) * (ces ** (1.0 - rho)))


def nested_labour(ld: float, lm: float, delta: float, sigma_L: float,
                  scale: float = 1.0) -> float:
    """Efficiency-unit labour index, optionally scaled to headcount at calibration."""
    return float(scale) * ces_combine(ld, lm, delta, sigma_L)


def nested_labour_weights(ld: float, lm: float, delta: float, sigma_L: float,
                          scale: float = 1.0) -> tuple[float, float]:
    """∂L/∂Ld and ∂L/∂Lm for the nested CES labour aggregator."""
    ld = max(float(ld), 1e-12)
    lm = max(float(lm), 1e-12)
    raw = ces_combine(ld, lm, delta, sigma_L)
    rho = _rho(sigma_L)
    if rho is None or abs(rho) < _RHO_EPS:
        d_ld = scale * delta * (raw / ld)
        d_lm = scale * (1.0 - delta) * (raw / lm)
        return float(d_ld), float(d_lm)
    d_ld = scale * delta * (ld ** (rho - 1.0)) * (raw ** (1.0 - rho))
    d_lm = scale * (1.0 - delta) * (lm ** (rho - 1.0)) * (raw ** (1.0 - rho))
    return float(d_ld), float(d_lm)


def labour_headcount_scale(ld: float, lm: float, delta: float, sigma_L: float) -> float:
    """Factor that makes the CES labour index equal Ld+Lm at the jump-off split."""
    raw = ces_combine(ld, lm, delta, sigma_L)
    return float((ld + lm) / raw)


def calibrate_delta(ld: float, lm: float, sigma_L: float, wage_ratio: float) -> float:
    """Choose δ so that w_m / w_d equals `wage_ratio` at the initial split.

    From :math:`w_d / w_m = [δ/(1-δ)] (L_m / L_d)^{1/σ_L}` in the CES case
    (and the analogous Cobb-Douglas limit).
    """
    ld = max(float(ld), 1e-12)
    lm = max(float(lm), 1e-12)
    target = max(float(wage_ratio), 1e-6)  # w_m / w_d
    # w_m / w_d = ((1-δ)/δ) * (ld/lm)^{1/σ_L}
    # (1-δ)/δ = target * (lm/ld)^{1/σ_L}
    ratio = target * (lm / ld) ** (1.0 / sigma_L)
    # (1-δ)/δ = ratio  =>  1/δ - 1 = ratio  =>  δ = 1/(1+ratio)
    delta = 1.0 / (1.0 + ratio)
    return float(np.clip(delta, 0.05, 0.95))


def target_capital(a: float, labour: float, alpha: float, sigma: float,
                   rental: float) -> float:
    """Invert MPK(K, L) = rental for K* > 0."""
    labour = max(float(labour), 1e-8)
    rental = max(float(rental), 1e-8)

    def _gap(k: float) -> float:
        return mpk(a, k, labour, alpha, sigma) - rental

    # Bracket: very small K has huge MPK, large K has tiny MPK
    lo, hi = labour * 1e-6, labour * 1e8
    g_lo, g_hi = _gap(lo), _gap(hi)
    if g_lo < 0:
        # MPK already below rental even at tiny K — return a floor
        return lo
    if g_hi > 0:
        return hi
    return float(brentq(_gap, lo, hi, xtol=1e-8, maxiter=80))


@dataclass
class MacroState:
    year: int
    a: float
    k: float
    ld: float
    lm: float
    labour: float
    y: float
    gdp_per_capita: float
    k_over_l: float
    wage_domestic: float
    wage_migrant: float
    mpl_agg: float
    mpk: float
    k_star: float
    investment: float
    wage_index_d: float
    wage_index_m: float
    wage_index_avg: float


class MacroModel:
    """CES production, nested labour, and endogenous capital deepening."""

    def __init__(self, a0: float, k0: float, delta: float, sigma: float, sigma_L: float,
                 alpha: float, delta_k: float, real_rate: float, lam: float,
                 tfp_growth: float):
        self.a = float(a0)
        self.k = float(k0)
        self.delta = float(delta)
        self.sigma = float(sigma)
        self.sigma_L = float(sigma_L)
        self.alpha = float(alpha)
        self.delta_k = float(delta_k)
        self.real_rate = float(real_rate)
        self.lam = float(np.clip(lam, 0.0, 1.0))
        self.tfp_growth = float(tfp_growth)
        self.rental = self.real_rate + self.delta_k
        self.labour_scale = 1.0
        self._w0_d: float | None = None
        self._w0_m: float | None = None
        self._w0_avg: float | None = None

    def set_labour_scale_from(self, ld: float, lm: float) -> None:
        self.labour_scale = labour_headcount_scale(ld, lm, self.delta, self.sigma_L)

    def evaluate(self, year: int, ld: float, lm: float, population: float) -> MacroState:
        labour = nested_labour(ld, lm, self.delta, self.sigma_L, self.labour_scale)
        y = self.a * ces_combine(self.k, labour, self.alpha, self.sigma)
        k_star = target_capital(self.a, labour, self.alpha, self.sigma, self.rental)
        mpl_agg = mpl(self.a, self.k, labour, self.alpha, self.sigma)
        mpk_t = mpk(self.a, self.k, labour, self.alpha, self.sigma)
        d_ld, d_lm = nested_labour_weights(
            ld, lm, self.delta, self.sigma_L, self.labour_scale
        )
        w_d = mpl_agg * d_ld
        w_m = mpl_agg * d_lm
        if self._w0_d is None:
            self._w0_d = w_d
            self._w0_m = w_m
            self._w0_avg = (w_d * ld + w_m * lm) / max(ld + lm, 1e-12)
        avg_w = (w_d * ld + w_m * lm) / max(ld + lm, 1e-12)
        # Implied gross investment consistent with the K law of motion
        k_next = (1.0 - self.lam) * self.k + self.lam * k_star
        investment = k_next - (1.0 - self.delta_k) * self.k
        return MacroState(
            year=year,
            a=self.a,
            k=self.k,
            ld=ld,
            lm=lm,
            labour=labour,
            y=y,
            gdp_per_capita=y / max(population, 1.0),
            k_over_l=self.k / labour,
            wage_domestic=w_d,
            wage_migrant=w_m,
            mpl_agg=mpl_agg,
            mpk=mpk_t,
            k_star=k_star,
            investment=investment,
            wage_index_d=w_d / self._w0_d,
            wage_index_m=w_m / self._w0_m,
            wage_index_avg=avg_w / self._w0_avg,
        )

    def step_capital_and_tfp(self, state: MacroState) -> None:
        """Apply K_{t+1} = (1-λ)K + λK* and A_{t+1} = A (1+g)."""
        self.k = max((1.0 - self.lam) * self.k + self.lam * state.k_star, 1.0)
        self.a *= 1.0 + self.tfp_growth
