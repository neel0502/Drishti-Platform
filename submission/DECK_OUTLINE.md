# Prototype Deck Outline

## 1. Title

Drishti — From Crime Records to Actionable Intelligence

## 2. The operational problem

- Fragmented records and manual cross-referencing
- Slow statewide situational awareness
- Charts without a clear recommended next action

## 3. Users and jobs to be done

- Senior officer morning briefing
- SCRB analyst investigation
- SHO district and station review

## 4. Solution

Show the command dashboard and the investigation workspace as one connected system.

## 5. Live investigation story

Crime spike → hotspot → linked cases → offender network → operational response → intelligence brief.

## 6. Technical architecture

Synthetic SCRB schema → ingestion/validation → analytics and link engine → API → dashboard → Catalyst AppSail.

## 7. AI and analytics

- Similar-case retrieval
- Network/community analysis
- Alert generation
- Planned temporal hotspot model with measured accuracy

## 8. Responsible and secure deployment

Synthetic demo data, explainability, RBAC, audit logging, masking, human review.

## 9. Scale

Indexed production store, cached aggregates, background processing, monitoring, capacity testing for 1,100+ police stations.

## 10. Impact and roadmap

Investigation-time reduction, faster situational decisions, measured alert quality, Catalyst deployment milestones.
