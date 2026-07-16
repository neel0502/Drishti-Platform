# Drishti — KSP Crime Intelligence Platform

Drishti is a decision-support and investigation platform built for the Karnataka State Police Datathon 2026, Challenge 2: **AI-Driven Crime Analytics & Visualization Platform**.

It turns synthetic SCRB-style records into a state-level command dashboard, geographic crime view, cross-case search, offender profiles, criminal-network analysis, and actionable situation alerts.

> All repository data is synthetic. Drishti is decision support for authorized officers; it does not make automated accusations or operational decisions.

## Demonstrated workflows

- State command dashboard with trends and district attention indicators
- District map with crime, category, and time filters
- Investigation search across cases and accused people
- Suspect profiles with repeat-offender and related-case context
- Network and link analysis for connected offenders and cases
- Situation alerts for unusual activity
- District drill-down for station and offender summaries
- Explainable FIR-to-FIR links with narrative, co-accused, phone, and vehicle evidence
- Computed 12-month district/category anomaly baselines
- Evidence-aware incident reconstruction with a map timeline and explicit inferred steps
- Missing-link reporting for absent identifiers, routes, CCTV, arrests, victims, and chargesheets
- Human-reviewed operational recommendations with a prototype action audit trail
- Pattern-discovery laboratory that clusters a selected FIR slice at request time and links every result to representative cases
- Case lifecycle intelligence with FIR-to-arrest and FIR-to-chargesheet timing, exception counts, and station bottlenecks
- Patrol resource scenarios that allocate a fixed unit pool against explainable 90-day historical demand

## Architecture

```text
Synthetic SCRB CSV/GeoJSON
          |
          v
FastAPI ingestion and analytics
  |-- aggregate indicators
  |-- TF-IDF case similarity
  |-- interactive narrative clustering
  |-- lifecycle joins and delay analysis
  |-- explainable patrol demand allocation
  |-- NetworkX link analysis
          |
          v
REST API + static web application
          |
          v
Zoho Catalyst AppSail
```

The current prototype intentionally uses local synthetic files for portability. The production path replaces them with Catalyst Data Store or an indexed relational store, background ingestion, cached aggregates, and station-level access controls.

## Run locally

Python 3.10+ is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API health endpoint is `/api/health`.

Run the analytics regression suite with `pytest -q` after installing `requirements-dev.txt`.

For a production-style local start:

```bash
HOST=0.0.0.0 PORT=9000 DRISHTI_RELOAD=false python run.py
```

## Run with Docker

```bash
docker build --platform linux/amd64 -t drishti-ksp .
docker run --rm -p 9000:9000 drishti-ksp
```

Open [http://127.0.0.1:9000](http://127.0.0.1:9000).

## Zoho Catalyst deployment

Deployment instructions and the required AppSail configuration are in [deployment/catalyst/README.md](deployment/catalyst/README.md).

Live development deployment: https://drishtiksp-50044050051.development.catalystappsail.in

## Repository guide

- `backend/app.py` — FastAPI service and analytics
- `frontend/` — dashboard web application
- `output/` — synthetic SCRB-style data
- `submission/` — prototype brief, pitch outline, and demo script
- `DESIGN_BRIEF.md` — product and user-experience specification
- `FEATURES_FROM_ERD.md` — features derived from the source schema
- `DATA_GENERATION_ANTIGRAVITY.md` — synthetic-data notes

## Data and responsible-use principles

- No production police records or real PII are included.
- Identity fields displayed in a future production version must be masked by default.
- Predictions must show supporting evidence, confidence, and limitations.
- Human officers remain responsible for investigation and deployment decisions.
- Production access requires role-based authorization and audit logs.

## Submission status

The current branch prepares the working feature implementation for review against `main`, adds reproducible dependencies, Catalyst deployment scaffolding, and the initial submission package. Live deployment credentials and the final public video URL are intentionally not stored in Git.
