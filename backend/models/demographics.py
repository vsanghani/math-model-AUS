"""Cohort-component demographic engine.

Tracks population :math:`N_{a,s,t}` by single-year age
:math:`a \\in [0, 100]`, sex :math:`s \\in \\{M, F\\}`, and year :math:`t`.

Transition (closed interval, with an open-ended terminal cohort at 100):

.. math::

    N_{a,s,t+1} = N_{a-1,s,t}(1 - q_{a-1,s,t}) + M_{a,s,t}
        \\quad a = 1,\\ldots,99

    N_{100,s,t+1} = N_{99,s,t}(1-q_{99,s,t}) + N_{100,s,t}(1-q_{100,s,t})
        + M_{100,s,t}

Births replenish age 0.  Net overseas migration :math:`M` is allocated by
an age-sex profile that mixes permanent and student/temporary cohorts.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.calibration import (
    FEMALE,
    FERTILE,
    MALE,
    N_AGES,
    OLD_AGE,
    PENSION_AGE,
    PRIME_AGE,
    SEXES,
    WAITING_YEARS,
    WORKING_AGE,
    Calibration,
    fertility_asfr,
    initial_population,
    mortality_qx,
    nom_age_sex_profile,
    participation_by_age_sex,
    split_native_migrant,
)


@dataclass
class DemographicState:
    """Full age-sex stocks plus an 8-year migrant vintage ladder."""

    year: int
    native: np.ndarray  # (2, 101) Australian-born
    settled: np.ndarray  # (2, 101) foreign-born, resident >= 8 years
    recent: np.ndarray  # (8, 2, 101) vintages 0..7 years since arrival
    student_stock: float

    def total(self) -> np.ndarray:
        return self.native + self.settled + self.recent.sum(axis=0)

    def foreign_born(self) -> np.ndarray:
        return self.settled + self.recent.sum(axis=0)

    def copy(self) -> "DemographicState":
        return DemographicState(
            year=self.year,
            native=self.native.copy(),
            settled=self.settled.copy(),
            recent=self.recent.copy(),
            student_stock=float(self.student_stock),
        )


@dataclass
class DemographicMetrics:
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
    recent_pension_age: float


def _survive(stock: np.ndarray, surv: np.ndarray) -> np.ndarray:
    """Advance a (2, 101) stock one year by survival only (no births, no NOM)."""
    out = np.zeros_like(stock)
    out[:, 1:100] = stock[:, 0:99] * surv[:, 0:99]
    out[:, 100] = stock[:, 99] * surv[:, 99] + stock[:, 100] * surv[:, 100]
    return out


class CohortComponentModel:
    """Vectorised cohort-component projector."""

    def __init__(self, cal: Calibration):
        self.cal = cal
        self.qx = mortality_qx(cal)
        self.surv = 1.0 - self.qx
        self.asfr = fertility_asfr(cal)
        self.part = participation_by_age_sex()
        self.perm_profile = nom_age_sex_profile("permanent")
        self.student_profile = nom_age_sex_profile("student")
        self.male_birth_frac = cal.sex_ratio_at_birth / (1.0 + cal.sex_ratio_at_birth)

    def initial_state(self) -> DemographicState:
        pop = initial_population(self.cal)
        native, migrant = split_native_migrant(pop, self.cal)
        # Allocate vintages: most foreign-born are long-settled
        recent = np.zeros((WAITING_YEARS, SEXES, N_AGES), dtype=float)
        # ~18% of the migrant stock arrived in the last 8 years
        recent_share = 0.18
        recent_total = migrant * recent_share
        # More recent vintages are slightly smaller (COVID trough + rebound)
        weights = np.array([1.35, 1.25, 1.10, 1.00, 0.90, 0.85, 0.80, 0.75], dtype=float)
        weights = weights / weights.sum()
        for k in range(WAITING_YEARS):
            recent[k] = recent_total * weights[k]
        settled = migrant - recent_total
        settled = np.clip(settled, 0.0, None)
        return DemographicState(
            year=self.cal.start_year,
            native=native,
            settled=settled,
            recent=recent,
            student_stock=self.cal.student_stock_0,
        )

    def nom_profile(self, student_share: float) -> np.ndarray:
        student_share = float(np.clip(student_share, 0.0, 1.0))
        mix = (1.0 - student_share) * self.perm_profile + student_share * self.student_profile
        return mix / mix.sum()

    def births_from(self, females: np.ndarray) -> np.ndarray:
        """Return age-0 births by sex from a female age vector (length 101)."""
        n_births = float((females[FERTILE] * self.asfr[FERTILE]).sum())
        out = np.zeros((SEXES, N_AGES), dtype=float)
        out[MALE, 0] = n_births * self.male_birth_frac
        out[FEMALE, 0] = n_births * (1.0 - self.male_birth_frac)
        return out, n_births

    def labour_supply(self, state: DemographicState) -> tuple[float, float, float]:
        """Return (L_domestic, L_migrant, participation rate among 15+)."""
        native = state.native
        migrant = state.foreign_born()
        ld = float((native * self.part).sum())
        lm = float((migrant * self.part).sum())
        pop_15plus = float(state.total()[:, 15:].sum())
        lf = ld + lm
        pr = lf / pop_15plus if pop_15plus > 0 else 0.0
        return ld, lm, pr

    def metrics(self, state: DemographicState, births: float, deaths: float, nom: float,
                student_inflow: float) -> DemographicMetrics:
        tot = state.total()
        n = float(tot.sum())
        wa = float(tot[:, WORKING_AGE].sum())
        old = float(tot[:, OLD_AGE].sum())
        prime = float(tot[:, PRIME_AGE].sum())
        pension = float(tot[:, PENSION_AGE:].sum())
        recent_tot = state.recent.sum(axis=0)
        ld, lm, pr = self.labour_supply(state)
        return DemographicMetrics(
            year=state.year,
            population=n,
            births=births,
            deaths=deaths,
            nom=nom,
            student_inflow=student_inflow,
            student_stock=state.student_stock,
            working_age=wa,
            old_age=old,
            prime_age=prime,
            pension_age=pension,
            dependency_ratio=(old / wa) if wa > 0 else np.nan,
            prime_working_age_share=prime / n if n > 0 else np.nan,
            participation_rate=pr,
            labour_native=ld,
            labour_migrant=lm,
            labour_total=ld + lm,
            native_pop=float(state.native.sum()),
            migrant_pop=float(state.foreign_born().sum()),
            recent_migrant_pop=float(recent_tot.sum()),
            recent_pension_age=float(recent_tot[:, PENSION_AGE:].sum()),
        )

    def step(
        self,
        state: DemographicState,
        nom: float,
        student_share: float,
        qx: np.ndarray | None = None,
        asfr: np.ndarray | None = None,
        apply_births: bool = True,
    ) -> tuple[DemographicState, DemographicMetrics]:
        """Advance one year.  Births are Australian-born; NOM enters vintage 0."""
        surv = (1.0 - qx) if qx is not None else self.surv
        asfr_use = asfr if asfr is not None else self.asfr

        pre = state.total()
        native_s = _survive(state.native, surv)
        settled_s = _survive(state.settled, surv)
        recent_s = np.stack([_survive(state.recent[k], surv) for k in range(WAITING_YEARS)])

        deaths = float(pre.sum() - (native_s + settled_s + recent_s.sum(axis=0)).sum())

        n_births = 0.0
        if apply_births:
            # Fertility uses beginning-of-interval females (pre-migration)
            females_pre = pre[FEMALE]
            n_births = float((females_pre[FERTILE] * asfr_use[FERTILE]).sum())
            births_arr = np.zeros((SEXES, N_AGES), dtype=float)
            births_arr[MALE, 0] = n_births * self.male_birth_frac
            births_arr[FEMALE, 0] = n_births * (1.0 - self.male_birth_frac)
            native_s = native_s + births_arr

        # Vintage ladder: 7 -> settled, k -> k+1, 0 filled by this year's NOM
        new_settled = settled_s + recent_s[WAITING_YEARS - 1]
        new_recent = np.zeros_like(recent_s)
        new_recent[1:] = recent_s[:-1]

        profile = self.nom_profile(student_share)
        migrants = nom * profile
        new_recent[0] = migrants

        # Student stock: inflow plus geometric duration decay
        student_inflow = max(0.0, float(nom) * float(np.clip(student_share, 0.0, 1.0)))
        decay = 1.0 / max(self.cal.student_duration_years, 0.5)
        new_students = (1.0 - decay) * state.student_stock + student_inflow

        nxt = DemographicState(
            year=state.year + 1,
            native=native_s,
            settled=new_settled,
            recent=new_recent,
            student_stock=new_students,
        )
        # Metrics for the *new* year after the transition
        metrics = self.metrics(nxt, n_births, deaths, float(nom), student_inflow)
        metrics.year = nxt.year
        return nxt, metrics


def conservation_residual(pop_before: np.ndarray, pop_after: np.ndarray,
                          births: float, deaths: float, nom: float) -> float:
    """Identity: ΔN = births - deaths + NOM.  Returns residual (should be ~0)."""
    return float(pop_after.sum() - pop_before.sum() - births + deaths - nom)
