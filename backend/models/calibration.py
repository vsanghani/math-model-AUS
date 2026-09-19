"""Default ABS / Treasury-style calibration for Australia, 2025.

Figures are stylised to official orders of magnitude (ABS demographic
structure, Treasury NOM baselines, AIHW health cost gradients, PBO-style
fiscal elasticities) rather than a full micro-data rebuild.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

N_AGES = 101  # ages 0..100 inclusive; 100 is an open-ended terminal cohort
SEXES = 2  # 0 = male, 1 = female
MALE, FEMALE = 0, 1
WAITING_YEARS = 8

# Age bands used throughout the engine
WORKING_AGE = slice(15, 65)
PRIME_AGE = slice(25, 55)
OLD_AGE = slice(65, 101)
PENSION_AGE = 67
FERTILE = slice(15, 50)


@dataclass(frozen=True)
class Calibration:
    """Immutable country-level starting point for 2025."""

    start_year: int = 2025
    horizon_years: int = 26  # 2025 through 2050 inclusive

    # --- National accounts (real 2025 AUD) ---
    gdp_0: float = 2.70e12
    capital_output_ratio: float = 3.15
    employment_0: float = 14.45e6
    population_0: float = 27.25e6
    foreign_born_share: float = 0.312
    migrant_wage_ratio: float = 0.94  # w_m / w_d at calibration

    # --- Production ---
    sigma: float = 0.90  # K-L substitution (complements if < 1)
    sigma_L: float = 5.0  # domestic-migrant substitution
    alpha: float = 0.38  # capital share parameter in CES
    tfp_growth: float = 0.010
    delta_k: float = 0.055
    real_rate: float = 0.045
    capital_adjust_lambda: float = 0.18

    # --- Demography ---
    tfr: float = 1.60
    mean_maternity_age: float = 31.2
    sex_ratio_at_birth: float = 1.055  # male / female
    e0_male: float = 81.2
    e0_female: float = 85.3
    # ABS NOM, year to March 2026 (status quo that overshot the Budget forecast)
    current_nom: float = 292_100.0
    # Home Affairs NPC, 17 Sep 2026: Budget NOM treated as a target
    home_affairs_fy_nom: float = 245_000.0  # 2026-27
    home_affairs_long_run_nom: float = 225_000.0  # 2027-28 onward
    policy_nom_cap: float = 130_000.0  # One Nation
    current_student_share: float = 0.34
    home_affairs_student_share: float = 0.27  # visa-hopping + student-family limits
    policy_student_share: float = 0.16
    # Backward-compatible aliases used by older call sites
    baseline_nom_long_run: float = 292_100.0
    baseline_nom_near_term: float = 292_100.0
    baseline_student_share: float = 0.34

    # --- Housing ---
    avg_household_size_0: float = 2.51
    hh_size_drift: float = -0.004  # annual change in household size
    housing_stock_0: float = 11.05e6
    housing_vacancy_target: float = 0.025
    housing_demand_income_elasticity: float = 0.35
    housing_supply_elasticity: float = 0.30
    rent_pass_through: float = 0.45

    # --- Education exports ---
    student_stock_0: float = 780_000.0
    student_duration_years: float = 2.8
    spend_per_student: float = 62_000.0  # tuition + living, AUD

    # --- Fiscal ---
    pit_rate: float = 0.225
    cit_rate: float = 0.30
    gst_effective: float = 0.052  # GST collections / consumption
    mpc: float = 0.61
    age_pension_avg: float = 18_400.0
    pension_takeup: float = 0.62
    other_transfer_per_capita: float = 4_800.0
    infrastructure_per_new_person: float = 28_000.0
    gov_consumption_gdp: float = 0.18
    health_other_gdp: float = 0.022

    # --- Labour force ---
    hours_index: float = 1.0

    rng_seed: int = 2025
    notes: str = field(
        default="Stylised 2025 ABS/Treasury/AIHW calibration",
        compare=False,
    )


def _normalise(x: np.ndarray) -> np.ndarray:
    total = float(x.sum())
    if total <= 0:
        raise ValueError("cannot normalise a zero vector")
    return x / total


def initial_population(cal: Calibration) -> np.ndarray:
    """Synthetic ABS-like pyramid: shape (2, 101), persons.

    Mixes a working-age plateau, a 1950s-60s baby-boom bulge, and a
    declining child cohort consistent with sub-replacement fertility.
    """
    ages = np.arange(N_AGES, dtype=float)

    # Base hazard producing median age ~38 and 65+ share ~17.5%
    base = np.exp(-ages / 48.0) * (1.0 + 0.22 * np.exp(-0.5 * ((ages - 32.0) / 14.0) ** 2))
    boom = 0.28 * np.exp(-0.5 * ((ages - 62.0) / 9.5) ** 2)
    young_dip = 1.0 - 0.12 * np.exp(-0.5 * ((ages - 8.0) / 7.0) ** 2)
    density = (base + boom) * young_dip
    density = np.clip(density, 1e-12, None)
    density = _normalise(density)

    # Sex ratio: 1.055 at birth, falling toward a female surplus at old ages
    male_frac = 0.513 - 0.00115 * ages - 0.000035 * np.maximum(ages - 55.0, 0.0) ** 1.4
    male_frac = np.clip(male_frac, 0.22, 0.54)

    pop = np.zeros((SEXES, N_AGES), dtype=float)
    pop[MALE] = cal.population_0 * density * male_frac
    pop[FEMALE] = cal.population_0 * density * (1.0 - male_frac)
    # Rescale to exact total after sex split
    pop *= cal.population_0 / pop.sum()
    return pop


def migrant_stock_share_by_age() -> np.ndarray:
    """Foreign-born share of each age cell. Peaks in prime working ages."""
    ages = np.arange(N_AGES, dtype=float)
    share = 0.10 + 0.34 * np.exp(-0.5 * ((ages - 38.0) / 16.0) ** 2)
    share[:5] = 0.06
    share = np.clip(share, 0.05, 0.48)
    return share


def split_native_migrant(pop: np.ndarray, cal: Calibration) -> tuple[np.ndarray, np.ndarray]:
    """Split total population into Australian-born vs foreign-born stocks."""
    age_share = migrant_stock_share_by_age()
    migrant = pop * age_share[np.newaxis, :]
    # Rescale so aggregate foreign-born share matches calibration
    target = cal.foreign_born_share * pop.sum()
    migrant *= target / migrant.sum()
    native = np.clip(pop - migrant, 0.0, None)
    # Preserve totals
    scale = pop / np.clip(native + migrant, 1e-12, None)
    native *= scale
    migrant *= scale
    return native, migrant


def mortality_qx(cal: Calibration | None = None) -> np.ndarray:
    """Gompertz-Makeham age-sex mortality probabilities, shape (2, 101).

    Calibrated so implied e0 is close to ABS 2022-24 life tables
    (male ~81, female ~85) without requiring an external file.
    """
    ages = np.arange(N_AGES, dtype=float)
    # Makeham A + Gompertz B exp(C a); infant extra mortality added separately
    # Males
    mu_m = 0.00055 + 0.000031 * np.exp(0.090 * ages)
    mu_f = 0.00042 + 0.000018 * np.exp(0.091 * ages)
    infant_m = 0.0032 * np.exp(-ages / 1.15)
    infant_f = 0.0026 * np.exp(-ages / 1.15)
    qx = np.vstack(
        [
            1.0 - np.exp(-(mu_m + infant_m)),
            1.0 - np.exp(-(mu_f + infant_f)),
        ]
    )
    qx = np.clip(qx, 0.0, 0.55)
    qx[:, 100] = np.clip(qx[:, 100] + 0.12, 0.0, 0.70)
    return qx


def fertility_asfr(cal: Calibration) -> np.ndarray:
    """Age-specific fertility rates for ages 0..100 (non-zero on 15-49).

    A Gamma-like schedule concentrated around the mean maternity age,
    scaled so the total fertility rate equals `cal.tfr`.
    """
    ages = np.arange(N_AGES, dtype=float)
    asfr = np.zeros(N_AGES, dtype=float)
    fertile_ages = ages[FERTILE]
    # Log-normal-ish maternity schedule
    loc = cal.mean_maternity_age
    sd = 5.4
    kernel = np.exp(-0.5 * ((fertile_ages - loc) / sd) ** 2)
    kernel *= np.clip((fertile_ages - 14.0) / 6.0, 0.0, 1.0)
    kernel *= np.clip((50.0 - fertile_ages) / 4.0, 0.0, 1.0)
    kernel = kernel / kernel.sum()
    asfr[FERTILE] = cal.tfr * kernel
    return asfr


def nom_age_sex_profile(kind: str = "permanent") -> np.ndarray:
    """Probability mass over (sex, age) for a net overseas migrant.

    `kind` is ``permanent`` (skilled/family) or ``student``.
    """
    ages = np.arange(N_AGES, dtype=float)
    profile = np.zeros((SEXES, N_AGES), dtype=float)
    if kind == "student":
        dens = np.exp(-0.5 * ((ages - 23.0) / 4.2) ** 2)
        dens[ages < 17] = 0.0
        dens[ages > 40] = 0.0
        male_frac = 0.49
    else:
        dens = (
            0.55 * np.exp(-0.5 * ((ages - 30.0) / 8.5) ** 2)
            + 0.22 * np.exp(-0.5 * ((ages - 8.0) / 5.0) ** 2)
            + 0.12 * np.exp(-0.5 * ((ages - 48.0) / 9.0) ** 2)
        )
        dens[ages > 80] *= 0.15
        male_frac = 0.51
    dens = np.clip(dens, 0.0, None)
    dens = _normalise(dens)
    profile[MALE] = dens * male_frac
    profile[FEMALE] = dens * (1.0 - male_frac)
    return profile


def participation_by_age_sex() -> np.ndarray:
    """Labour-force participation rates, shape (2, 101). ABS-like 2024."""
    ages = np.arange(N_AGES, dtype=float)
    p = np.zeros((SEXES, N_AGES), dtype=float)

    def _schedule(peak: float, senior: float, retire: float) -> np.ndarray:
        s = np.zeros_like(ages)
        # 15-19
        s = np.where((ages >= 15) & (ages < 20), 0.52 + 0.02 * (ages - 15), s)
        # 20-24
        s = np.where((ages >= 20) & (ages < 25), 0.74 + 0.02 * (ages - 20), s)
        # 25-54 plateau
        s = np.where((ages >= 25) & (ages < 55), peak, s)
        # 55-64
        s = np.where(
            (ages >= 55) & (ages < 65),
            peak - (peak - senior) * (ages - 55) / 10.0,
            s,
        )
        # 65-69
        s = np.where(
            (ages >= 65) & (ages < 70),
            senior - (senior - retire) * (ages - 65) / 5.0,
            s,
        )
        # 70-74
        s = np.where((ages >= 70) & (ages < 75), retire * 0.55, s)
        s = np.where(ages >= 75, retire * 0.18, s)
        return np.clip(s, 0.0, 0.97)

    p[MALE] = _schedule(peak=0.905, senior=0.70, retire=0.27)
    p[FEMALE] = _schedule(peak=0.835, senior=0.60, retire=0.18)
    return p


def health_cost_by_age() -> np.ndarray:
    """AIHW-style government health expenditure per person (AUD / year)."""
    ages = np.arange(N_AGES, dtype=float)
    cost = np.where(
        ages < 5,
        4_200 + 200 * ages,
        np.where(
            ages < 15,
            2_100,
            np.where(
                ages < 25,
                2_400,
                np.where(
                    ages < 45,
                    3_100 + 40 * (ages - 25),
                    np.where(
                        ages < 65,
                        4_800 + 180 * (ages - 45),
                        np.where(
                            ages < 75,
                            11_500 + 650 * (ages - 65),
                            np.where(
                                ages < 85,
                                18_000 + 1_100 * (ages - 75),
                                32_000 + 900 * np.minimum(ages - 85, 10),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    return cost.astype(float)


def sector_base_shares() -> dict[str, float]:
    """Initial employment shares across the four representative sectors."""
    return {
        "construction_housing": 0.11,
        "healthcare_aged_care": 0.15,
        "education_export_services": 0.09,
        "general_industry": 0.65,
    }
