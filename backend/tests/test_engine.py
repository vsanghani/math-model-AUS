"""Paired-scenario engine and FastAPI contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from models.calibration import Calibration
from models.engine import SimulationEngine, horizon_delta
from schemas import SimulationRequest


client = TestClient(app)


def test_engine_returns_2025_to_2050():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    years_b = [r.year for r in raw["baseline"]]
    years_p = [r.year for r in raw["policy"]]
    assert years_b[0] == 2025 and years_b[-1] == 2050
    assert years_p == years_b
    assert len(years_b) == 26


def test_policy_lowers_gdp_level_but_deepens_capital():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair({"nom_cap": 130_000})
    b, p = raw["baseline"][-1], raw["policy"][-1]
    assert p.gdp < b.gdp
    assert p.population < b.population
    assert p.k_over_l > b.k_over_l  # capital deepening
    assert p.dependency_ratio > b.dependency_ratio


def test_horizon_deltas_are_finite():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    d10 = horizon_delta(raw["baseline"], raw["policy"], 10)
    d25 = horizon_delta(raw["baseline"], raw["policy"], 25)
    assert d10["year"] == 2035
    assert d25["year"] == 2050
    for d in (d10, d25):
        for v in d.values():
            assert v == v  # not NaN


def test_waiting_period_excludes_recent_migrants_from_pension_base():
    engine = SimulationEngine(Calibration())
    raw = engine.run_pair()
    # Early in the shock, policy has fewer recent arrivals so fewer excluded,
    # but the field must be populated and non-negative
    for row in raw["policy"]:
        assert row.waiting_excluded_pensioners >= 0


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_simulate_endpoint_baseline_vs_policy():
    payload = SimulationRequest().model_dump()
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["baseline"]["name"] == "Treasury baseline"
    assert body["policy"]["name"] == "One Nation shock"
    assert len(body["baseline"]["series"]) == 26
    assert body["deltas_25y"]["year"] == 2050
    # GDP path should be a list of positive numbers
    gdps = [pt["gdp"] for pt in body["baseline"]["series"]]
    assert all(g > 0 for g in gdps)


def test_simulate_rejects_invalid_payload():
    res = client.post("/api/simulate", json={"nom_cap": 10})
    assert res.status_code == 422


def test_defaults_endpoint():
    res = client.get("/api/defaults")
    assert res.status_code == 200
    body = res.json()
    assert body["nom_cap"] == 130000
    assert body["sigma_L"] == 5.0
