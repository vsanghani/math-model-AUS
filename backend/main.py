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
    "Stylised 2025–2050 projection.  Current NOM holds the ABS print of 292,100 "
    "(year to March 2026).  The Home Affairs scenario implements Tony Burke’s "
    "17 September 2026 National Press Club package: Budget NOM treated as a "
    "target (245,000 in 2026–27, 225,000 from 2027–28), a working-holiday "
    "ballot (45,000 second-year / 5,000 third-year places), limits on student "
    "dependants and visa-hopping, overstayer compliance, and a skilled-list "
    "tilt toward construction, healthcare, education, enforcement and primary "
    "industries.  One Nation remains a 130,000 net cap with a deeper student "
    "cut.  New migrants face an 8-year wait for Age Pension and other personal "
    "transfers."
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
    current = records_to_dicts(raw["current"])
    home_affairs = records_to_dicts(raw["home_affairs"])
    one_nation = records_to_dicts(raw["one_nation"])
    return SimulationResponse(
        current=ScenarioSeries(
            name="Current NOM (ABS 292k)",
            series=[YearPoint.model_validate(row) for row in current],
        ),
        home_affairs=ScenarioSeries(
            name="Home Affairs (Burke Sep 2026)",
            series=[YearPoint.model_validate(row) for row in home_affairs],
        ),
        one_nation=ScenarioSeries(
            name="One Nation 130k cap",
            series=[YearPoint.model_validate(row) for row in one_nation],
        ),
        ha_deltas_10y=HorizonDelta.model_validate(
            horizon_delta(raw["current"], raw["home_affairs"], 10)
        ),
        ha_deltas_25y=HorizonDelta.model_validate(
            horizon_delta(raw["current"], raw["home_affairs"], 25)
        ),
        on_deltas_10y=HorizonDelta.model_validate(
            horizon_delta(raw["current"], raw["one_nation"], 10)
        ),
        on_deltas_25y=HorizonDelta.model_validate(
            horizon_delta(raw["current"], raw["one_nation"], 25)
        ),
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
