# Round 2 — Governed Agentic Investigation Workflow

## Product position

Drishti is an accountable command-support platform. The agent does not determine guilt, order surveillance, dispatch personnel, or alter a case. It retrieves authorized intelligence, identifies evidence gaps, and drafts a cited plan for human review.

## Demo workflow

1. A supervisor selects an FIR in **Case Commander**.
2. Drishti composes a command plan from the recorded timeline, missing links, and explainable cross-FIR signals.
3. The **Proactive Sentinel** surfaces aggregate anomaly and case-delay review triggers without changing a case.
4. **Scout Agent** calls allowlisted reconstruction, FIR-brief, and cross-case-link tools to assemble candidate claims.
5. **Skeptic Agent** challenges every claim against missing evidence and district data-quality risks, records alternative explanations, and reduces confidence where appropriate.
6. **Commander Agent** returns an evidence-cited review draft with a fingerprinted agent-run record; it has no execution tools.
7. A supervisor explicitly records a review request; no operational action occurs automatically.

## Agent safety contract

| Capability | Agent access |
| --- | --- |
| Read case, FIR, and link context | Allowed through fixed internal tools |
| Identify evidence gaps and contradictions | Allowed |
| Draft a human-review action | Allowed |
| Approve, dispatch, message, or create a case | Denied |
| Declare guilt or treat a link as proof | Denied |
| Use arbitrary web, shell, or database tools | Denied |

Every generated recommendation includes evidence citations and requires human approval.

Generated narrative output masks phone, vehicle, and 12-digit identity values by default. Agent-run records form a tamper-evident hash chain: each entry contains the previous audit hash, run ID, case scope, role, plan fingerprint, status, and current audit hash.

## Production path

The complete deployment topology, security controls, service inventory, release checklist, operational targets, and phased rollout are documented in [`docs/SUBMISSION_ARCHITECTURE.md`](docs/SUBMISSION_ARCHITECTURE.md).

The deployed prototype is intentionally a development environment with synthetic data. A production deployment uses:

- Catalyst-authenticated identity claims; the server maps those claims to role, district, and case scope. Browser-provided roles are never trusted.
- A row-level policy layer that masks PII by default and logs justified reveals.
- A dedicated append-only agent-audit table/event stream containing run ID, tool calls, citations, plan hash, approver, and outcome.
- Object storage with hash verification and retention policies for evidence; temporary AppSail storage is not a production evidence vault.
- Event-driven ingestion: validate → normalize → deduplicate → quality-check → index → analytics refresh → auditable status event.
- Independent API, search/index, analytics worker, evidence, and audit services with queue retries, monitoring, backup, and retention controls.

## Judge framing

> The intelligence agent is not an autonomous policing system. It is a governed orchestration layer that makes data provenance, uncertainty, and human responsibility visible at the moment a command decision is made.
