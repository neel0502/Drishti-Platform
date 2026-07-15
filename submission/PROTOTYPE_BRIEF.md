# Drishti Prototype Brief

## Challenge

Karnataka State Police Datathon 2026 — Challenge 2: AI-Driven Crime Analytics & Visualization Platform.

## Problem

Crime information spans cases, accused people, victims, arrests, chargesheets, courts, districts, and police units. Manual cross-referencing delays investigations and makes it difficult for senior officers to obtain a timely, statewide operational picture.

## Solution

Drishti converts SCRB-style data into two connected experiences:

1. A command-centre view that shows trends, geographic concentration, unusual situations, and districts needing attention.
2. An investigation workspace that searches across cases and people, identifies related cases, builds offender profiles, and explains criminal-network links.

## Users

- DGP/IGP/Commissioner: statewide situation and resource priorities
- SCRB analyst: cross-case investigation and network analysis
- SHO: station and district workload with local drill-down

## Current prototype

- FastAPI analytics service
- Responsive browser dashboard
- Synthetic data modeled on the supplied schema
- TF-IDF similarity for related-case discovery
- NetworkX graph analysis for connected offenders
- District, case, offender, map, and alert views
- Catalyst-ready health check and runtime-port support

## Differentiation

- One workflow connects command intelligence to case-level evidence.
- Technical scores are translated into plain-language operational explanations.
- Links are intended to show their supporting evidence, not merely draw a graph.
- The architecture has an explicit path from synthetic prototype to controlled production deployment.

## Responsible AI

Drishti is decision support. Predictions and associations must be explainable, confidence-bounded, auditable, and reviewed by authorized officers. The demo contains synthetic data only. A production version requires role-based access, station-level scoping, PII masking, retention controls, and immutable audit logs.

## Deployment and scalability path

The prototype is deployable on Zoho Catalyst AppSail. The next production iteration moves CSV ingestion into Catalyst Data Store or an indexed relational database, precomputes aggregates, introduces background pipelines and caching, and adds load tests and observability.

## Success measures

- Time required to find related cases
- Search and dashboard response latency
- Precision and false-alarm rate of alerts
- Analyst acceptance of suggested links
- Reduction in manual cross-referencing steps
- Successful completion rate for the core demo workflow
