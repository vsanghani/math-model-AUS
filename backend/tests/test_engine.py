"""Paired-scenario engine and FastAPI contract."""

from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from main import app
from models.calibration import Calibration
from models.engine import SimulationEngine, horizon_delta, scenario_nom
from schemas import SimulationRequest


client = TestClient(app)


def test_home_affairs_nom_path_matches_burke_targets():
    years = np.arange(2025, 2051)
    path = scenario_nom(
        years,
        "home_affairs",
        current_nom=292_100,
        home_affairs_fy=245_000,
        home_affairs_long=225_000,
        one_nation_cap=130_000,
    )
    assert path[0] == 292_100  # 2025, pre-announcement
    assert path[1] == 245_000  # 2026–27 target
    assert path[2] == 225_000  # 2027–28 onward
    assert path[-1] == 225_000
    current = scenario_nom(
        years, "current",
        current_nom=292_100, home_affairs_fy=245_000,
        home_affairs_long=225_000, one_nation_cap=130_000,
    )
    assert np.all(current == 292_100)


def test_engine_returns_2025_to_2050():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    years_c = [r.year for r in raw["current"]]
    years_h = [r.year for r in raw["home_affairs"]]
    years_o = [r.year for r in raw["one_nation"]]
    assert years_c[0] == 2025 and years_c[-1] == 2050
    assert years_h == years_c == years_o
    assert len(years_c) == 26


def test_home_affairs_sits_between_current_and_one_nation():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    c, h, o = raw["current"][-1], raw["home_affairs"][-1], raw["one_nation"][-1]
    assert o.gdp < h.gdp < c.gdp
    assert o.population < h.population < c.population
    assert h.k_over_l > c.k_over_l
    assert h.dependency_ratio > c.dependency_ratio
    # Shared 2025 jump-off
    assert abs(raw["current"][0].gdp - raw["home_affairs"][0].gdp) < 1.0
    assert abs(raw["home_affairs"][1].nom - 245_000) < 1.0
    assert abs(raw["home_affairs"][2].nom - 225_000) < 1.0


def test_one_nation_lowers_gdp_level_but_deepens_capital():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair({"nom_cap": 130_000})
    c, o = raw["current"][-1], raw["one_nation"][-1]
    assert o.gdp < c.gdp
    assert o.population < c.population
    assert o.k_over_l > c.k_over_l
    assert o.dependency_ratio > c.dependency_ratio


def test_horizon_deltas_are_finite():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    d10 = horizon_delta(raw["current"], raw["home_affairs"], 10)
    d25 = horizon_delta(raw["current"], raw["home_affairs"], 25)
    assert d10["year"] == 2035
    assert d25["year"] == 2050
    for d in (d10, d25):
        for v in d.values():
            assert v == v  # not NaN


def test_waiting_period_excludes_recent_migrants_from_pension_base():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    for row in raw["home_affairs"]:
        assert row.waiting_excluded_pensioners >= 0


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_simulate_endpoint_three_scenarios():
    payload = SimulationRequest().model_dump()
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert "292k" in body["current"]["name"]
    assert "Home Affairs" in body["home_affairs"]["name"]
    assert "One Nation" in body["one_nation"]["name"]
    assert len(body["current"]["series"]) == 26
    assert body["ha_deltas_25y"]["year"] == 2050
    gdps = [pt["gdp"] for pt in body["current"]["series"]]
    assert all(g > 0 for g in gdps)
    ha_noms = [pt["nom"] for pt in body["home_affairs"]["series"]]
    assert ha_noms[0] == 292100
    assert ha_noms[1] == 245000
    assert ha_noms[5] == 225000


def test_simulate_rejects_invalid_payload():
    res = client.post("/api/simulate", json={"nom_cap": 10})
    assert res.status_code == 422


def test_defaults_endpoint():
    res = client.get("/api/defaults")
    assert res.status_code == 200
    body = res.json()
    assert body["nom_cap"] == 130000
    assert body["current_nom"] == 292100
    assert body["home_affairs_fy_nom"] == 245000
    assert body["home_affairs_long_run_nom"] == 225000
    assert body["sigma_L"] == 5.0
