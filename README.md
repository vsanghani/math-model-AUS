# Australia 2025–2050 migration-shock simulator

Cohort-component demography, nested CES production, a four-sector labour/housing block, and a Commonwealth/State fiscal module. The policy scenario caps net overseas migration (default 130,000) and scales down the student/temporary share relative to a Treasury-style NOM glide.

## Run

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The Next.js app proxies `POST /api/simulate` to FastAPI.

## API

`POST /api/simulate` accepts Pydantic overrides (`nom_cap`, `sigma_L`, `tfp_growth`, `housing_supply_elasticity`, …) and returns paired baseline/policy year-by-year series plus 10- and 25-year deltas.

`GET /api/health` and `GET /api/defaults` are available on port 8000.

## Math

- Demography: \(N_{a,s,t+1}=N_{a-1,s,t}(1-q_{a-1,s,t})+M_{a,s,t}\) with an open-ended age-100 cohort, TFR-scaled fertility, and an 8-year migrant vintage ladder.
- Production: CES in \(K,L\) nested with CES in domestic vs migrant labour; capital partial-adjusts toward the rental FOC (capital deepening when labour growth slows).
- Housing: \(H^d_t=(N_t/\bar h_t)(1+\varepsilon_h\Delta w_t)\) against an inelastic completion curve.
- Fiscal: PIT, company tax, GST; Age Pension and other transfers exclude migrants with fewer than eight years’ residence.
