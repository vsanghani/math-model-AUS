"""Temporary visa stock by class.

Resident temporaries (students, working-holiday, TSS, graduates, overstayers,
bridging) sit inside the usual-resident population.  Headline political stock
also includes NZ special-category and short-stay visitors (~3 million).

Law of motion for class :math:`c`:

.. math::

    S_{c,t+1} = (1 - \\delta_{c,t}) S_{c,t} + I_{c,t} - X_{c,t}

where :math:`\\delta` is the duration hazard, :math:`I` is inflow and
:math:`X` is a policy forced exit (One Nation rundown, denied WHM ballot).

Home Affairs WHM ballot and overstayer compliance change *composition and
duration* while the NOM *target* is still the population flow.  One Nation's
750,000 stock cut is additional net outflow for three years, so effective NOM
can go negative.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

import numpy as np

from models.calibration import Calibration

# Classes that are usual residents and can be forcibly run down
RESIDENT_CLASSES = (
    "student",
    "whm_y1",
    "whm_y2",
    "whm_y3",
    "skilled",
    "graduate",
    "overstayer",
    "other",
)

# Weight on each class when allocating a forced stock cut (skilled partly protected)
CUT_WEIGHT = {
    "student": 1.15,
    "whm_y1": 1.20,
    "whm_y2": 1.20,
    "whm_y3": 1.20,
    "skilled": 0.35,
    "graduate": 1.10,
    "overstayer": 1.40,
    "other": 1.00,
}

PARTICIPATION = {
    "student": 0.48,
    "whm_y1": 0.88,
    "whm_y2": 0.90,
    "whm_y3": 0.90,
    "skilled": 0.93,
    "graduate": 0.82,
    "overstayer": 0.70,
    "other": 0.65,
}


@dataclass
class TemporaryStock:
    student: float
    whm_y1: float
    whm_y2: float
    whm_y3: float
    skilled: float
    graduate: float
    overstayer: float
    other: float
    nz_sctv: float
    short_stay: float

    def copy(self) -> "TemporaryStock":
        return replace(self)

    def whm(self) -> float:
        return float(self.whm_y1 + self.whm_y2 + self.whm_y3)

    def resident(self) -> float:
        return float(
            self.student
            + self.whm()
            + self.skilled
            + self.graduate
            + self.overstayer
            + self.other
        )

    def headline(self) -> float:
        return float(self.resident() + self.nz_sctv + self.short_stay)

    def labour_units(self) -> float:
        total = 0.0
        for name, rate in PARTICIPATION.items():
            total += float(getattr(self, name)) * rate
        return total

    def as_dict(self) -> dict[str, float]:
        return {f.name: float(getattr(self, f.name)) for f in fields(self)}


@dataclass
class TemporaryPolicy:
    student_duration: float
    overstayer_removal: float
    graduate_duration: float = 2.4
    skilled_duration: float = 3.0
    other_duration: float = 3.0
    short_stay_duration: float = 0.45
    whm_y2_cap: float | None = None
    whm_y3_cap: float | None = None
    forced_cut: float = 0.0


@dataclass
class TemporaryReport:
    student_inflow: float
    whm_inflow: float
    skilled_inflow: float
    denied_whm: float
    overstayer_removals: float
    forced_exits: float
    delta_resident: float
    delta_headline: float


def initial_temporary_stock(cal: Calibration) -> TemporaryStock:
    return TemporaryStock(
        student=cal.student_stock_0,
        whm_y1=cal.whm_y1_0,
        whm_y2=cal.whm_y2_0,
        whm_y3=cal.whm_y3_0,
        skilled=cal.skilled_temp_0,
        graduate=cal.graduate_0,
        overstayer=cal.overstayer_0,
        other=cal.other_temp_0,
        nz_sctv=cal.nz_sctv_0,
        short_stay=cal.short_stay_0,
    )


def policy_for(scenario: str, cal: Calibration, forced_cut: float = 0.0) -> TemporaryPolicy:
    if scenario == "home_affairs":
        return TemporaryPolicy(
            student_duration=cal.ha_student_duration,
            overstayer_removal=cal.ha_overstayer_removal,
            graduate_duration=2.1,
            other_duration=2.4,
            short_stay_duration=0.32,
            whm_y2_cap=cal.ha_whm_y2_cap,
            whm_y3_cap=cal.ha_whm_y3_cap,
            forced_cut=0.0,
        )
    if scenario == "one_nation":
        return TemporaryPolicy(
            student_duration=1.8,
            overstayer_removal=0.55,
            graduate_duration=1.6,
            skilled_duration=2.4,
            other_duration=1.8,
            short_stay_duration=0.25,
            whm_y2_cap=20_000.0,
            whm_y3_cap=2_000.0,
            forced_cut=float(forced_cut),
        )
    return TemporaryPolicy(
        student_duration=cal.student_duration_years,
        overstayer_removal=0.08,
        forced_cut=0.0,
    )


def _inflow_scale(nom: float, current_nom: float) -> float:
    if current_nom <= 0:
        return 0.0
    return max(float(nom), 0.0) / float(current_nom)


def _apply_forced_cut(stock: TemporaryStock, cut: float) -> tuple[TemporaryStock, float]:
    cut = max(float(cut), 0.0)
    if cut <= 0:
        return stock, 0.0
    weights = np.array([CUT_WEIGHT[c] * max(float(getattr(stock, c)), 0.0) for c in RESIDENT_CLASSES])
    total_w = float(weights.sum())
    if total_w <= 0:
        return stock, 0.0
    available = stock.resident()
    take = min(cut, available)
    shares = weights / total_w
    data = stock.as_dict()
    removed = 0.0
    for i, name in enumerate(RESIDENT_CLASSES):
        slice_take = min(data[name], take * float(shares[i]))
        data[name] -= slice_take
        removed += slice_take
    # Residual if rounding left a gap
    leftover = take - removed
    if leftover > 1.0:
        for name in RESIDENT_CLASSES:
            extra = min(data[name], leftover)
            data[name] -= extra
            leftover -= extra
            removed += extra
            if leftover <= 0:
                break
    return TemporaryStock(**data), float(removed)


class TemporaryModel:
    def __init__(self, cal: Calibration):
        self.cal = cal

    def step(
        self,
        stock: TemporaryStock,
        nom: float,
        student_share: float,
        policy: TemporaryPolicy,
    ) -> tuple[TemporaryStock, TemporaryReport]:
        cal = self.cal
        scale = _inflow_scale(nom, cal.current_nom)
        share_rel = float(np.clip(student_share / max(cal.current_student_share, 1e-6), 0.05, 1.5))

        student_in = (cal.student_stock_0 / max(cal.student_duration_years, 0.5)) * scale * share_rel
        whm_in = cal.whm_y1_inflow_0 * scale
        skilled_in = cal.skilled_temp_inflow_0 * scale * (1.15 if policy.whm_y2_cap else 1.0)
        if policy.forced_cut > 0:
            skilled_in *= 0.70
        graduate_in = cal.graduate_inflow_0 * scale * share_rel
        other_in = cal.other_temp_inflow_0 * scale

        d_student = 1.0 / max(policy.student_duration, 0.5)
        d_grad = 1.0 / max(policy.graduate_duration, 0.5)
        d_skill = 1.0 / max(policy.skilled_duration, 0.5)
        d_other = 1.0 / max(policy.other_duration, 0.5)
        d_short = 1.0 / max(policy.short_stay_duration, 0.2)

        student_next = (1.0 - d_student) * stock.student + student_in
        skilled_next = (1.0 - d_skill) * stock.skilled + skilled_in
        graduate_next = (1.0 - d_grad) * stock.graduate + graduate_in
        other_next = (1.0 - d_other) * stock.other + other_in
        short_next = (1.0 - d_short) * stock.short_stay + 0.55 * other_in
        nz_next = stock.nz_sctv  # special-category stock is slow-moving

        # WHM ladder: year-1 always rolls; years 2–3 are ballot-capped
        y2_candidates = 0.82 * stock.whm_y1
        y2_cap = policy.whm_y2_cap
        y2_next = y2_candidates if y2_cap is None else min(y2_candidates, y2_cap)
        denied_y2 = max(y2_candidates - y2_next, 0.0)

        y3_candidates = 0.54 * stock.whm_y2
        y3_cap = policy.whm_y3_cap
        y3_next = y3_candidates if y3_cap is None else min(y3_candidates, y3_cap)
        denied_y3 = max(y3_candidates - y3_next, 0.0)

        y1_next = whm_in
        denied_whm = denied_y2 + denied_y3

        overstayer_removals = policy.overstayer_removal * stock.overstayer
        # A small inflow of new overstayers from the other-temp pool
        new_overstay = 0.04 * stock.other * (0.35 if policy.overstayer_removal > 0.2 else 1.0)
        overstayer_next = max(stock.overstayer - overstayer_removals + new_overstay, 0.0)

        nxt = TemporaryStock(
            student=max(student_next, 0.0),
            whm_y1=max(y1_next, 0.0),
            whm_y2=max(y2_next, 0.0),
            whm_y3=max(y3_next, 0.0),
            skilled=max(skilled_next, 0.0),
            graduate=max(graduate_next, 0.0),
            overstayer=overstayer_next,
            other=max(other_next, 0.0),
            nz_sctv=max(nz_next, 0.0),
            short_stay=max(short_next, 0.0),
        )
        nxt, forced = _apply_forced_cut(nxt, policy.forced_cut)
        delta_res = nxt.resident() - stock.resident()
        delta_head = nxt.headline() - stock.headline()
        return nxt, TemporaryReport(
            student_inflow=float(student_in),
            whm_inflow=float(whm_in),
            skilled_inflow=float(skilled_in),
            denied_whm=float(denied_whm),
            overstayer_removals=float(overstayer_removals),
            forced_exits=float(forced),
            delta_resident=float(delta_res),
            delta_headline=float(delta_head),
        )
