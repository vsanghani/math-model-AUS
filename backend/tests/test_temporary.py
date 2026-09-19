"""Temporary visa stock identities and policy rundowns."""

from __future__ import annotations

from models.calibration import Calibration
from models.demographics import CohortComponentModel
from models.engine import SimulationEngine
from models.temporary import TemporaryModel, initial_temporary_stock, policy_for


def test_headline_stock_is_three_million():
    cal = Calibration()
    stock = initial_temporary_stock(cal)
    assert abs(stock.headline() - 3_000_000) < 1_000
    assert stock.resident() > 1.5e6
    assert abs(stock.overstayer - 77_000) < 1.0


def test_current_policy_keeps_resident_stock_in_a_band():
    cal = Calibration()
    model = TemporaryModel(cal)
    stock = initial_temporary_stock(cal)
    policy = policy_for("current", cal)
    start = stock.resident()
    for _ in range(8):
        stock, _ = model.step(stock, nom=cal.current_nom, student_share=0.34, policy=policy)
    # Steady-ish: not a collapse and not a doubling
    assert 0.75 * start < stock.resident() < 1.35 * start


def test_home_affairs_whm_ballot_shrinks_third_year_stock():
    cal = Calibration()
    model = TemporaryModel(cal)
    stock = initial_temporary_stock(cal)
    policy = policy_for("home_affairs", cal)
    for _ in range(4):
        stock, _ = model.step(stock, nom=225_000, student_share=0.27, policy=policy)
    assert stock.whm_y3 <= cal.ha_whm_y3_cap + 1.0
    assert stock.whm_y2 <= cal.ha_whm_y2_cap + 1.0
    assert stock.overstayer < 0.55 * cal.overstayer_0


def test_one_nation_forced_cut_removes_three_quarters_of_a_million():
    cal = Calibration()
    demo = CohortComponentModel(cal)
    state = demo.initial_state()
    start = state.temp.headline()
    annual = cal.one_nation_temp_cut / cal.one_nation_temp_cut_years
    policy = policy_for("one_nation", cal, forced_cut=annual)
    for _ in range(3):
        state, _ = demo.step(state, nom=130_000, student_share=0.16, temp_policy=policy)
    # Headline stock down by roughly the 750k rundown (plus duration effects)
    assert start - state.temp.headline() > 600_000
    assert state.temp.resident() < initial_temporary_stock(cal).resident() - 400_000


def test_one_nation_stock_cut_makes_effective_nom_negative():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    # 2026 is index 1: first announcement year
    row = raw["one_nation"][1]
    assert row.temp_forced_exits > 200_000
    assert row.nom < 0
    # After three years the stock gap vs current is material
    assert raw["one_nation"][4].temp_headline < raw["current"][4].temp_headline - 500_000
