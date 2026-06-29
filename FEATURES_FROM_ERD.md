# All Features Buildable from KSP FIR ER Diagram

---

## TABLE SOURCE MAP

| Table | What it unlocks |
|---|---|
| CaseMaster | Everything — central hub |
| Accused | Repeat offenders, network graph nodes |
| Victim | Victim profiling, demographic analysis |
| ComplainantDetails | Socio-economic analysis, religion/caste/occupation patterns |
| ArrestSurrender | Arrest rate, IO performance, co-arrest gang detection |
| ChargesheetDetails | Case resolution, conviction rate, false case detection |
| ActSectionAssociation | Legal pattern analysis, IPC section clustering |
| Act + Section | MO legal fingerprint matching |
| CrimeHead + CrimeSubHead | Crime category breakdown, trend by type |
| Unit (Police Station) | Station performance, jurisdiction analysis |
| District | Geographic clustering, district comparison |
| State | State-level rollup |
| Employee | Officer workload, IO performance |
| Rank + Designation | Hierarchy-level analysis |
| Court | Court pendency, bail/chargesheet tracking |
| CaseCategory | FIR vs UDR vs Zero FIR vs PAR breakdown |
| GravityOffence | Heinous vs Non-Heinous split |
| CaseStatusMaster | Case lifecycle tracking |
| ReligionMaster | Complainant/victim religion breakdown |
| CasteMaster | SC/ST/OBC/General vulnerability analysis |
| OccupationMaster | Victim occupation patterns (farmer, retired = cyber fraud targets) |

---

## FEATURE LIST — GROUPED BY DOMAIN

---

### 1. COMMAND CENTRE / EXECUTIVE DASHBOARD

From: CaseMaster + District + CrimeHead + CaseStatusMaster + GravityOffence

| # | Feature | Tables Used |
|---|---|---|
| 1.1 | Total FIRs this month with delta vs last month | CaseMaster.CrimeRegisteredDate |
| 1.2 | Heinous vs Non-Heinous crime split | CaseMaster.GravityOffenceID → GravityOffence |
| 1.3 | Case resolution rate (% closed vs open) | CaseMaster.CaseStatusID → CaseStatusMaster |
| 1.4 | Arrest rate (% cases with an arrest) | ArrestSurrender linked to CaseMaster |
| 1.5 | FIR category breakdown (FIR / UDR / PAR / Zero FIR) | CaseMaster.CaseCategoryID → CaseCategory |
| 1.6 | Top crime types this month (bar chart) | CaseMaster → CrimeHead → CrimeSubHead |
| 1.7 | Monthly crime trend — 3 years (line chart) | CaseMaster.CrimeRegisteredDate grouped by month |
| 1.8 | Districts needing attention (top 3 by volume spike) | CaseMaster + District |
| 1.9 | Chargesheet conversion rate (FIR → CS) | CaseMaster + ChargesheetDetails |
| 1.10 | False case rate (cstype = B) | ChargesheetDetails.cstype |
| 1.11 | Undetected case rate (cstype = C) | ChargesheetDetails.cstype |
| 1.12 | Cases pending over 90 days (SLA breach) | CaseMaster.CrimeRegisteredDate + CaseStatusID |
| 1.13 | Week-on-week crime delta | CaseMaster.CrimeRegisteredDate |
| 1.14 | Festive season spike detection (Oct/Nov annual) | CaseMaster.CrimeRegisteredDate month grouping |
| 1.15 | Zero FIR tracking (cross-jurisdiction cases) | CaseMaster.CaseCategoryID = 8 (Zero FIR) |

---

### 2. CRIME MAP & GEOSPATIAL

From: CaseMaster.latitude + CaseMaster.longitude + District + Unit

| # | Feature | Tables Used |
|---|---|---|
| 2.1 | District choropleth map (crime density) | CaseMaster lat/lng + District |
| 2.2 | Heatmap layer (raw GPS density) | CaseMaster.latitude + longitude |
| 2.3 | Crime cluster map (DBSCAN hotspot detection) | CaseMaster lat/lng |
| 2.4 | Time-of-day animation (hour slider 0–23) | CaseMaster.IncidentFromDate extract(hour) |
| 2.5 | Day-of-week pattern map | CaseMaster.IncidentFromDate extract(dayofweek) |
| 2.6 | Crime type filter on map (e.g. only burglaries) | CaseMaster + CrimeSubHead |
| 2.7 | Police station jurisdiction boundary overlay | Unit + District GeoJSON |
| 2.8 | Incident duration overlay (IncidentFrom → IncidentTo) | CaseMaster.IncidentFromDate + IncidentToDate |
| 2.9 | Zero FIR origin vs registration district map | CaseMaster (ZeroFIR category) + Unit.DistrictID |
| 2.10 | Crime-free zones (districts with low/declining crime) | CaseMaster + District |
| 2.11 | GPS point click → case detail popup | CaseMaster.latitude + longitude |
| 2.12 | Radius search: all crimes within X km of a point | CaseMaster lat/lng + haversine formula |
| 2.13 | Police station workload map (cases per station) | CaseMaster.PoliceStationID → Unit |
| 2.14 | Arrest location vs crime location comparison | ArrestSurrender district vs CaseMaster district |

---

### 3. SPATIOTEMPORAL / PATTERN ANALYSIS

From: CaseMaster (dates + lat/lng + crime type)

| # | Feature | Tables Used |
|---|---|---|
| 3.1 | Peak crime hour per crime type | CaseMaster.IncidentFromDate + CrimeSubHead |
| 3.2 | Crime by day of week (Mon–Sun) | CaseMaster.IncidentFromDate |
| 3.3 | Monthly seasonality chart | CaseMaster.CrimeRegisteredDate |
| 3.4 | Crime duration analysis (IncidentFrom to IncidentTo gap) | CaseMaster date fields |
| 3.5 | Incident report delay (IncidentFrom to InfoReceivedPS) | CaseMaster.InfoReceivedPSDate |
| 3.6 | Reporting lag analysis (incident date vs FIR date) | CaseMaster.IncidentFromDate vs CrimeRegisteredDate |
| 3.7 | Night crime vs day crime split by district | CaseMaster hour extraction + DistrictID |
| 3.8 | Hotspot drift over time (do hotspots move?) | CaseMaster lat/lng grouped by month |
| 3.9 | Weekend vs weekday crime comparison | CaseMaster.IncidentFromDate |
| 3.10 | Crime velocity: how quickly does a spike develop? | CaseMaster daily rolling count |

---

### 4. CRIME CATEGORY INTELLIGENCE

From: CrimeHead + CrimeSubHead + CaseMaster + ActSectionAssociation

| # | Feature | Tables Used |
|---|---|---|
| 4.1 | Crime category breakdown (pie/bar) | CaseMaster → CrimeHead |
| 4.2 | Crime sub-category breakdown | CaseMaster → CrimeSubHead |
| 4.3 | Rising vs falling crime categories (trend) | CaseMaster + CrimeHead grouped by month |
| 4.4 | Heinous crime sub-type breakdown | CaseMaster.GravityOffenceID=1 + CrimeSubHead |
| 4.5 | Most common IPC sections invoked | ActSectionAssociation + Section |
| 4.6 | Section co-occurrence matrix (which sections appear together) | ActSectionAssociation grouped by CaseMasterID |
| 4.7 | District-wise crime type heatmap (district × crime type matrix) | CaseMaster + District + CrimeHead |
| 4.8 | Crime type migration (which types are growing in new districts) | CaseMaster + CrimeHead + District over time |
| 4.9 | Rare crime spike detection (unusual crime type appearing) | CaseMaster + CrimeSubHead rolling baseline |
| 4.10 | NDPS offence tracking (drug cases by district) | CaseMaster.CrimeMajorHeadID=7 + District |
| 4.11 | Cyber crime trend (growing category) | CaseMaster.CrimeMajorHeadID=6 grouped by month |
| 4.12 | SC/ST atrocity case tracking | CaseMaster.CrimeMajorHeadID=5 + District |

---

### 5. CASE LIFECYCLE ANALYSIS

From: CaseMaster + ArrestSurrender + ChargesheetDetails + CaseStatusMaster + Court

| # | Feature | Tables Used |
|---|---|---|
| 5.1 | Case lifecycle funnel (FIR → Arrest → Chargesheet → Court) | All 4 tables |
| 5.2 | Average days FIR → first arrest | CaseMaster + ArrestSurrender date diff |
| 5.3 | Average days arrest → chargesheet | ArrestSurrender + ChargesheetDetails date diff |
| 5.4 | Cases with arrest but no chargesheet | ArrestSurrender LEFT JOIN ChargesheetDetails |
| 5.5 | Cases with chargesheet but no prior arrest | ChargesheetDetails LEFT JOIN ArrestSurrender |
| 5.6 | Chargesheet type distribution (A/B/C) by crime type | ChargesheetDetails.cstype + CaseMaster crime |
| 5.7 | False case rate by district | ChargesheetDetails.cstype=B + District |
| 5.8 | Undetected case rate by district | ChargesheetDetails.cstype=C + District |
| 5.9 | Court-wise case load | CaseMaster.CourtID → Court |
| 5.10 | Case pendency at court level | CaseMaster.CaseStatusID + CourtID |
| 5.11 | Surrender vs arrest ratio | ArrestSurrender.ArrestSurrenderTypeID |
| 5.12 | Multiple arrests per case (complex/gang cases) | ArrestSurrender grouped by CaseMasterID |
| 5.13 | Complainant = Accused flag analysis | ArrestSurrender.IsComplainantAccused |

---

### 6. ACCUSED / REPEAT OFFENDER INTELLIGENCE

From: Accused + CaseMaster + ArrestSurrender

| # | Feature | Tables Used |
|---|---|---|
| 6.1 | Repeat offender detection (accused in 3+ cases) | Accused.AccusedName grouped by CaseMasterID |
| 6.2 | Repeat offender profile page (full case history) | Accused + CaseMaster + CrimeSubHead + ArrestSurrender |
| 6.3 | Accused age distribution (by crime type) | Accused.AgeYear + CaseMaster.CrimeMajorHeadID |
| 6.4 | Gender breakdown of accused (by crime type) | Accused.GenderID + CaseMaster.CrimeMajorHeadID |
| 6.5 | Multi-accused case detection (PersonID A1/A2/A3+) | Accused.PersonID count per CaseMasterID |
| 6.6 | Co-accused network (who appears together) | Accused grouped by CaseMasterID — pairs |
| 6.7 | Accused operating across districts (travel crime) | Accused + CaseMaster.PoliceStationID → District |
| 6.8 | Accused age at first offence | Accused.AgeYear at earliest CaseMaster date |
| 6.9 | Time between offences (recidivism interval) | Accused + CaseMaster dates sorted |
| 6.10 | Post-arrest reoffending rate | ArrestSurrender date vs subsequent CaseMaster dates |
| 6.11 | Accused with no arrest (at large tracking) | Accused + CaseMaster LEFT JOIN ArrestSurrender |
| 6.12 | ML risk score per repeat offender | Accused features → Random Forest model |

---

### 7. VICTIM INTELLIGENCE

From: Victim + CaseMaster + CrimeHead

| # | Feature | Tables Used |
|---|---|---|
| 7.1 | Victim age distribution by crime type | Victim.AgeYear + CaseMaster.CrimeMajorHeadID |
| 7.2 | Victim gender breakdown by crime type | Victim.GenderID + CaseMaster.CrimeMajorHeadID |
| 7.3 | Repeat victimisation detection | Victim.VictimName appearing in multiple CaseMaster |
| 7.4 | Police officer as victim tracking | Victim.VictimPolice = 1 |
| 7.5 | Vulnerable age group identification | Victim.AgeYear < 18 or > 60 by crime type |
| 7.6 | Multiple victims per case analysis | Victim count per CaseMasterID |
| 7.7 | Victim–accused relationship proximity | Victim location vs Accused location via CaseMaster GPS |

---

### 8. SOCIO-DEMOGRAPHIC ANALYSIS (SOCIOLOGICAL LAYER)

From: ComplainantDetails + ReligionMaster + CasteMaster + OccupationMaster + Victim

| # | Feature | Tables Used |
|---|---|---|
| 8.1 | Complainant occupation breakdown by crime type | ComplainantDetails.OccupationID + CaseMaster |
| 8.2 | Cyber fraud victims by occupation (retired/farmer targeting) | ComplainantDetails + CaseMaster.CrimeMajorHeadID=6 |
| 8.3 | Religion distribution of complainants | ComplainantDetails.ReligionID → ReligionMaster |
| 8.4 | Caste-based crime vulnerability mapping | ComplainantDetails.CasteID + CaseMaster + District |
| 8.5 | SC/ST complainant cases vs SC/ST atrocity cases | CasteMaster + CaseMaster.CrimeMajorHeadID=5 |
| 8.6 | Complainant age breakdown by crime type | ComplainantDetails.AgeYear + CaseMaster |
| 8.7 | Gender of complainant vs victim comparison | ComplainantDetails.GenderID vs Victim.GenderID |
| 8.8 | Complainant = Victim analysis (self-reporting) | ComplainantDetails.ComplainantName ~ Victim.VictimName |
| 8.9 | Farmer/labourer crime vulnerability by district | ComplainantDetails.OccupationID + District |
| 8.10 | Women complainant rate by district | ComplainantDetails.GenderID=F by DistrictID |

---

### 9. NETWORK & LINK ANALYSIS

From: Accused + Victim + CaseMaster + Unit + ArrestSurrender + ComplainantDetails

| # | Feature | Tables Used |
|---|---|---|
| 9.1 | Accused–Victim network graph | Accused ↔ CaseMaster ↔ Victim |
| 9.2 | Co-accused graph (who commits crimes together) | Accused.PersonID pairs per CaseMasterID |
| 9.3 | Gang/group detection (Louvain community detection) | Co-accused graph → NetworkX |
| 9.4 | Criminal cluster sizing (how large is each group) | Community detection node count |
| 9.5 | Cross-district gang detection | Co-accused + CaseMaster.DistrictID variance |
| 9.6 | Accused ↔ Location network (recurring crime spots) | Accused + CaseMaster lat/lng clusters |
| 9.7 | Accused ↔ Police Station patterns | Accused + CaseMaster.PoliceStationID |
| 9.8 | Shared IPC section fingerprint (same legal MO) | ActSectionAssociation patterns per accused |
| 9.9 | Hidden link: same victim targeted by different accused | Victim.VictimName across cases |
| 9.10 | Complainant network (same complainant, multiple FIRs) | ComplainantDetails.ComplainantName |
| 9.11 | Node centrality scoring (who is the gang leader) | NetworkX degree centrality on accused graph |
| 9.12 | Bridge nodes (accused connecting two separate groups) | NetworkX betweenness centrality |

---

### 10. NLP / TEXT INTELLIGENCE

From: CaseMaster.BriefFacts (free text field)

| # | Feature | Tables Used |
|---|---|---|
| 10.1 | MO extraction from BriefFacts (SpaCy NLP) | CaseMaster.BriefFacts |
| 10.2 | MO similarity matching across cases (TF-IDF cosine) | CaseMaster.BriefFacts pairwise |
| 10.3 | Cross-district MO linking ("same drill entry method") | BriefFacts similarity + District |
| 10.4 | Weapon extraction from BriefFacts ("knife", "rod", "acid") | NLP entity extraction |
| 10.5 | Vehicle number extraction from BriefFacts | Regex on BriefFacts |
| 10.6 | Phone number extraction from BriefFacts | Regex on BriefFacts |
| 10.7 | Location name extraction ("near X metro", "Y market") | NLP on BriefFacts |
| 10.8 | Victim description extraction ("lone woman", "elderly man") | NLP entity on BriefFacts |
| 10.9 | Time phrase extraction ("around midnight", "evening hours") | NLP on BriefFacts |
| 10.10 | Automatic case summary generation | LLM summarisation of BriefFacts |
| 10.11 | MO cluster labelling ("Drill Entry Group", "Metro Chain Snatch") | TF-IDF clusters → label |
| 10.12 | Unusual BriefFacts detection (outlier text patterns) | TF-IDF + IsolationForest |

---

### 11. OFFICER & STATION PERFORMANCE

From: Employee + CaseMaster + ArrestSurrender + Unit + Rank + Designation

| # | Feature | Tables Used |
|---|---|---|
| 11.1 | Cases assigned per IO | CaseMaster.PolicePersonID → Employee |
| 11.2 | Cases resolved per IO (chargesheet or closed) | CaseMaster + ChargesheetDetails + Employee |
| 11.3 | Arrest rate per IO | ArrestSurrender.IOID → Employee |
| 11.4 | Average resolution time per IO | CaseMaster dates + CaseStatusID per Employee |
| 11.5 | IO overload detection (>50 open cases) | CaseMaster open cases per Employee |
| 11.6 | Station case load vs district average | CaseMaster per Unit vs district average |
| 11.7 | Station resolution rate ranking | CaseMaster + CaseStatusMaster per Unit |
| 11.8 | Station arrest rate ranking | ArrestSurrender per PoliceStationID |
| 11.9 | Rank-wise performance comparison | Employee.RankID + case metrics |
| 11.10 | Understaffed station detection | Cases per station vs employee count per Unit |
| 11.11 | Officer posting history (unit transfers via UnitID) | Employee.UnitID + District |
| 11.12 | Cross-district arrest officer (IO making arrests outside home unit) | ArrestSurrender.IOID + PoliceStationID vs Unit.DistrictID |

---

### 12. ANOMALY DETECTION (AI/ML)

From: CaseMaster + all linked tables → ML models

| # | Feature | Tables Used |
|---|---|---|
| 12.1 | District crime spike detection (Z-score on rolling baseline) | CaseMaster per district per day |
| 12.2 | Crime type spike (unusual category surge) | CaseMaster + CrimeHead rolling mean |
| 12.3 | Isolation Forest: unusual case detection | CaseMaster features (time, location, type, gravity) |
| 12.4 | Time anomaly: crime at atypical hours for that type | CaseMaster + HOUR_WEIGHTS baseline |
| 12.5 | Reporting delay anomaly (very late FIR for incident) | CaseMaster.IncidentFromDate vs CrimeRegisteredDate |
| 12.6 | FIR volume anomaly at a single station | CaseMaster per PoliceStationID daily count |
| 12.7 | UDR spike (unnatural deaths rising) | CaseMaster.CaseCategoryID=3 per district |
| 12.8 | False case cluster detection (high cstype=B station) | ChargesheetDetails.cstype per Unit |
| 12.9 | Same accused arrested 3+ times in 30 days | ArrestSurrender + Accused date analysis |
| 12.10 | Same victim in multiple FIRs within 60 days | Victim.VictimName + CaseMaster date |

---

### 13. PREDICTIVE INTELLIGENCE (FORECASTING)

From: CaseMaster historical data → ML models

| # | Feature | Tables Used |
|---|---|---|
| 13.1 | 7-day crime risk score per district | Random Forest on CaseMaster history + District |
| 13.2 | Crime type forecast (which type will rise next week) | Prophet time series per CrimeHead |
| 13.3 | High-risk period prediction (festive, elections) | CaseMaster seasonal patterns |
| 13.4 | Reoffending prediction (will this accused reoffend) | Accused history + ML model |
| 13.5 | Station resource demand forecast | CaseMaster per Unit → future demand |
| 13.6 | Case resolution probability prediction | Case features → will this get chargesheeted? |
| 13.7 | Repeat victimisation risk (will this victim be targeted again) | Victim history + location + crime type |

---

### 14. LEGAL / COURT INTELLIGENCE

From: ActSectionAssociation + Act + Section + Court + ChargesheetDetails

| # | Feature | Tables Used |
|---|---|---|
| 14.1 | Top IPC sections used this year | ActSectionAssociation + Section |
| 14.2 | Section co-occurrence (which sections always appear together) | ActSectionAssociation per CaseMasterID |
| 14.3 | District-wise section distribution | ActSectionAssociation + CaseMaster + District |
| 14.4 | Court-wise case pendency | CaseMaster.CourtID + CaseStatusID |
| 14.5 | Cases with multiple acts invoked (complex crimes) | ActSectionAssociation.ActID count per CaseMasterID |
| 14.6 | NDPS vs IPC case ratio by district | Act.ActCode + District |
| 14.7 | Court production rate (arrestees produced in court) | ArrestSurrender.CourtID linkage |

---

### 15. ZERO FIR & JURISDICTIONAL INTELLIGENCE

From: CaseMaster.CaseCategoryID=8 + Unit + District

| # | Feature | Tables Used |
|---|---|---|
| 15.1 | Zero FIR volume by district | CaseMaster.CaseCategoryID=8 + District |
| 15.2 | Zero FIR origin vs transfer station | CaseMaster + Unit.DistrictID comparison |
| 15.3 | Inter-district crime flow (where crimes happen vs where registered) | CaseMaster GPS vs PoliceStationID district |
| 15.4 | PAR case tracking (Police Aided Reconciliation) | CaseMaster.CaseCategoryID=4 |
| 15.5 | UDR tracking (Unnatural Death Reports) | CaseMaster.CaseCategoryID=3 + District |

---

## SUMMARY COUNT

| Domain | Features |
|---|---|
| Command Centre / Executive Dashboard | 15 |
| Crime Map & Geospatial | 14 |
| Spatiotemporal / Pattern Analysis | 10 |
| Crime Category Intelligence | 12 |
| Case Lifecycle Analysis | 13 |
| Accused / Repeat Offender Intelligence | 12 |
| Victim Intelligence | 7 |
| Socio-Demographic Analysis | 10 |
| Network & Link Analysis | 12 |
| NLP / Text Intelligence | 12 |
| Officer & Station Performance | 12 |
| Anomaly Detection | 10 |
| Predictive Intelligence | 7 |
| Legal / Court Intelligence | 7 |
| Zero FIR & Jurisdictional | 5 |
| **TOTAL** | **158 features** |

---

## TOP 20 TO BUILD FOR THE DATATHON

Ranked by judge impact × build feasibility:

| Rank | Feature | Why |
|---|---|---|
| 1 | District choropleth + time slider (2.1 + 2.4) | Immediate visual wow |
| 2 | Red zone alert — district spike detection (12.1) | Directly answers the brief |
| 3 | Repeat offender profile (6.1 + 6.2) | Actionable detective intelligence |
| 4 | Co-accused network graph (9.2 + 9.3) | The cinematic screen |
| 5 | MO similarity matching (10.2 + 10.3) | Unique — no other team has this |
| 6 | Case lifecycle funnel (5.1) | Shows system-level insight |
| 7 | Crime category trend by month (4.1 + 4.3) | Standard but essential |
| 8 | BriefFacts vehicle/phone extraction (10.5 + 10.6) | Powers network graph |
| 9 | Station performance ranking (11.6 + 11.7) | Operational value |
| 10 | Predictive risk map 7-day (13.1) | Forward-looking intelligence |
| 11 | Socio-economic overlay — occupation of victims (8.1 + 8.2) | Sociological layer |
| 12 | Cross-district accused tracking (6.7) | Organised crime detection |
| 13 | Chargesheet type analysis (5.6 + 5.7 + 5.8) | System accountability |
| 14 | IPC section co-occurrence (4.6 + 14.2) | Legal MO fingerprinting |
| 15 | Festive season pattern (3.3 + 1.14) | Predictive storytelling |
| 16 | Zero FIR inter-district flow (15.2 + 15.3) | Unique jurisdictional insight |
| 17 | IO overload detection (11.5) | Resource deployment value |
| 18 | Gang centrality scoring — who is the leader (9.11) | Intelligence depth |
| 19 | Reoffending prediction (13.4) | AI credibility |
| 20 | Victim repeat targeting (7.3 + 13.7) | Human impact story |

---

*KSP Drishti · Feature Map from ER Diagram · Datathon 2026*
