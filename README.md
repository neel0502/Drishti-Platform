# Drishti — Crime Intelligence Platform

Drishti is a working, Catalyst-deployed decision-support platform for **AI-driven crime analytics and visualization**. It connects FIR intelligence, evidence workflows, case progress, link analysis, and district patrol planning in one explainable officer workspace.

It turns synthetic SCRB-style records into a state-level command dashboard, geographic crime view, cross-case search, offender profiles, criminal-network analysis, and actionable situation alerts.

> All repository data is synthetic. Drishti is decision support for authorized officers; it does not make automated accusations or operational decisions.

## Live prototype

[Open the Catalyst development deployment](https://drishti-50044068191.development.catalystappsail.in/)

The live prototype runs on **Zoho Catalyst AppSail** and reads its connected relational development subset from **Catalyst Data Store** through ZCQL. The demonstration data is synthetic and consists of 2,000 FIR records plus linked relational tables.

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
- Development CCTV, image, video, and document intake with file-type validation, SHA-256 evidence records, and temporary non-production storage
- Missing-link reporting for absent identifiers, routes, CCTV, arrests, victims, and chargesheets
- Human-reviewed operational recommendations with a prototype action audit trail
- Pattern-discovery laboratory that clusters a selected FIR slice at request time and links every result to representative cases
- Case lifecycle intelligence with FIR-to-arrest and FIR-to-chargesheet timing, exception counts, and station bottlenecks
- Patrol resource plans for selected districts, with Bangalore Urban boundary validation and out-of-district coordinate exclusion
- Data Quality Command Centre for completeness, duplicate narratives, geography, chronology, and referential-integrity checks
- Investigation Hypothesis Board for testable theories, linked FIRs, supporting evidence, and explicit evidence gaps
- Downloadable evidence-based PDF case briefs with timelines, linked FIR signals, missing evidence, and responsible-use notices
- Retrospective forecast backtesting with actual-vs-predicted charts and comparison to a naive baseline
- Responsive desktop, tablet, and mobile layouts with collapsible navigation and touch-friendly maps and tables

## Architecture

```text
Catalyst Data Store (linked synthetic FIR tables)
          |
          v
FastAPI intelligence and workflow service
  |-- aggregate indicators
  |-- TF-IDF case similarity
  |-- interactive narrative clustering
  |-- lifecycle joins and delay analysis
  |-- explainable patrol demand allocation
  |-- schema and data-quality observability
  |-- historical forecast validation
  |-- PDF case-brief generation
  |-- NetworkX link analysis
          |
          v
REST API + responsive web application
          |
          v
Zoho Catalyst AppSail
```

The application is Catalyst-first in AppSail. It hydrates the relational analytics layer from Catalyst Data Store through ZCQL. Local CSV files are retained only for explicit local-development fallback; the deployed configuration requests Catalyst Data Store and does not use the CSV fallback.

## Run locally

Python 3.10+ is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API health endpoint is [`/api/health`](http://127.0.0.1:8000/api/health).

Run the analytics regression suite with `pytest -q` after installing `requirements-dev.txt`.

For a production-style local start:

```bash
HOST=0.0.0.0 PORT=9000 DRISHTI_RELOAD=false python run.py
```

## Run with Docker

```bash
docker build --platform linux/amd64 -t drishti .
docker run --rm -p 9000:9000 drishti
```

Open [http://127.0.0.1:9000](http://127.0.0.1:9000).

## Zoho Catalyst deployment

Deployment instructions and the required AppSail configuration are in [deployment/catalyst/README.md](deployment/catalyst/README.md). From a Catalyst CLI-authenticated machine:

```bash
./scripts/build_appsail.sh
catalyst -p 50733000000039003 deploy appsail --name Drishti
```

The deployed AppSail service must use the Catalyst-supplied `X_ZOHO_CATALYST_LISTEN_PORT`; this is already handled by `app-config.json`.

## Repository guide

- `backend/app.py` — FastAPI service and analytics
- `frontend/` — dashboard web application
- `output/` — synthetic SCRB-style data
- `submission/` — prototype brief, architecture notes, presentation HTML, and demo run-through
- `DESIGN_BRIEF.md` — product and user-experience specification
- `FEATURES_FROM_ERD.md` — features derived from the source schema
- `DATA_GENERATION_ANTIGRAVITY.md` — synthetic-data notes

## Data and responsible-use principles

- No production police records or real PII are included.
- Identity fields displayed in a future production version must be masked by default.
- Predictions must show supporting evidence, confidence, and limitations.
- Human officers remain responsible for investigation and deployment decisions.
- Production access requires role-based authorization and audit logs.

## Evaluation materials

- [Prototype Brief](submission/PROTOTYPE_BRIEF.md)
- [Prototype Brief presentation (HTML)](submission/Drishti_Prototype_Brief.html)
- [Demo presentation and screen-by-screen run-through (HTML)](submission/Drishti_Full_Demo_Runthrough.html)
- [Design and production architecture (HTML)](submission/Drishti_Design_and_Production_Architecture.html)

Live deployment credentials, personal access tokens, and the final public demo-video URL are intentionally not stored in Git.
