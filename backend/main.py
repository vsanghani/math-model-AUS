"""FastAPI entry-point for the Australia migration-shock simulator."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.calibration import Calibration
from models.engine import SimulationEngine, horizon_delta, records_to_dicts
from schemas import (
    HorizonDelta,
    ScenarioSeries,
    SimulationRequest,
    SimulationResponse,
    YearPoint,
)

NOTES = (
    "Stylised 2025–2050 projection using a cohort-component demographic "
    "engine, nested CES production, a four-sector labour block, and a "
    "Commonwealth/State fiscal module.  Calibration matches ABS / Treasury / "
    "AIHW orders of magnitude.  Baseline NOM follows a Treasury-style glide "
    "from ~255k to a 235k long run; the policy scenario caps net overseas "
    "migration and scales down the student/temporary share.  New migrants "
    "face an 8-year wait for Age Pension and other personal transfers."
)

app = FastAPI(
    title="Australia migration-shock simulator",
    version="1.0.0",
    description=NOTES,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run(req: SimulationRequest) -> SimulationResponse:
    cal = Calibration()
    engine = SimulationEngine(cal)
    raw = engine.run_pair(req.model_dump())
    b_dicts = records_to_dicts(raw["baseline"])
    p_dicts = records_to_dicts(raw["policy"])
    d10 = horizon_delta(raw["baseline"], raw["policy"], 10)
    d25 = horizon_delta(raw["baseline"], raw["policy"], 25)
    return SimulationResponse(
        baseline=ScenarioSeries(
            name="Treasury baseline",
            series=[YearPoint.model_validate(row) for row in b_dicts],
        ),
        policy=ScenarioSeries(
            name="One Nation shock",
            series=[YearPoint.model_validate(row) for row in p_dicts],
        ),
        deltas_10y=HorizonDelta.model_validate(d10),
        deltas_25y=HorizonDelta.model_validate(d25),
        parameters=raw["parameters"],
        notes=NOTES,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/defaults", response_model=SimulationRequest)
def defaults() -> SimulationRequest:
    return SimulationRequest()


@app.post("/api/simulate", response_model=SimulationResponse)
def simulate(req: SimulationRequest) -> SimulationResponse:
    return _run(req)
