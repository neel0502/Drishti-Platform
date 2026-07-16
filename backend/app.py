from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import MiniBatchKMeans
import re
import os
import json
import math
from datetime import datetime, timedelta, timezone
from threading import Event, Lock, Thread
from typing import Optional
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from backend import catalyst_store

# Create FastAPI app
app = FastAPI(title="Drishti Intelligence API")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
BOOTSTRAP_DIR = os.path.join(BASE_DIR, "bootstrap-data")
CATALYST_SCHEMA = os.path.join(BASE_DIR, "deployment", "catalyst", "datastore-schema.json")

# Global DataFrames & Models
df_case = None
df_accused = None
df_victim = None
df_complainant = None
df_arrest = None
df_chargesheet = None
df_district = None
df_unit = None
df_crime_head = None
df_crime_subhead = None
df_status = None
df_occupation = None

# NLP & Network Variables
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = None
case_ids_list = []
G = nx.Graph()
analytics_ready = Event()
analytics_initialization_lock = Lock()
analytics_error = None
operational_action_log = []
hypothesis_boards = []
data_source_status = {
    "requested": "csv",
    "active": "csv",
    "fallback": False,
    "message": "Local schema-faithful CSV files",
}


@app.get("/api/health", tags=["operations"])
def health_check():
    """Lightweight readiness endpoint for local and AppSail health checks."""
    return {
        "status": "ok",
        "service": "drishti-intelligence-api",
        "dataLoaded": analytics_ready.is_set(),
        "initializationError": analytics_error,
        "dataSource": data_source_status,
    }


@app.middleware("http")
async def analytics_readiness_guard(request, call_next):
    """Keep the service reachable while the analytics indexes initialize."""
    global analytics_error
    bootstrap_mode = os.getenv("DRISHTI_BOOTSTRAP_DATASTORE", "false").lower() in {"1", "true", "yes"}
    if catalyst_store.catalyst_requested() and not bootstrap_mode and not analytics_ready.is_set():
        with analytics_initialization_lock:
            if not analytics_ready.is_set():
                try:
                    catalyst_store.initialize_from_request(request)
                    load_data()
                    build_network_graph()
                    build_nlp_index()
                    analytics_error = None
                    analytics_ready.set()
                except Exception as exc:
                    analytics_error = f"{type(exc).__name__}: {exc}"

    readiness_exempt = {"/api/health", "/api/internal/bootstrap-datastore"}
    if request.url.path.startswith("/api/") and request.url.path not in readiness_exempt:
        if analytics_error:
            return JSONResponse(
                status_code=500,
                content={"detail": "Analytics initialization failed", "error": analytics_error},
            )
        if not analytics_ready.is_set():
            return JSONResponse(
                status_code=503,
                headers={"Retry-After": "10"},
                content={"detail": "Analytics are initializing. Please retry shortly."},
            )
    return await call_next(request)

# Injected Pattern Case Lists
pattern_a_case_ids = []
pattern_b_case_ids = []
pattern_c_case_ids = []

# Safe Lookup Helpers
def get_district_name(district_id):
    if pd.isna(district_id):
        return "Unknown"
    try:
        dist_id_int = int(float(district_id))
        res = df_district[df_district['DistrictID'] == dist_id_int]['DistrictName']
        return str(res.values[0]) if not res.empty else "Unknown"
    except Exception:
        return "Unknown"

def get_unit_name(unit_id):
    if pd.isna(unit_id):
        return "Unknown"
    try:
        unit_id_int = int(float(unit_id))
        res = df_unit[df_unit['UnitID'] == unit_id_int]['UnitName']
        return str(res.values[0]) if not res.empty else "Unknown"
    except Exception:
        return "Unknown"

def get_case_status_name(status_id):
    if pd.isna(status_id):
        return "Unknown"
    try:
        status_id_int = int(float(status_id))
        res = df_status[df_status['CaseStatusID'] == status_id_int]['CaseStatusName']
        return str(res.values[0]) if not res.empty else "Unknown"
    except Exception:
        return "Unknown"

# Serialization helper
def clean_val(val):
    if pd.isna(val):
        return None
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val

def clean_dict(d):
    return {k: clean_val(v) for k, v in d.items()}

def clean_list(l):
    return [clean_dict(x) if isinstance(x, dict) else clean_val(x) for x in l]

def random_vehicle_suffix(i):
    letters = ["AB", "CD", "EF", "GH", "JK", "LM", "NP", "RS", "TU", "XY"][i % 10]
    num = (1000 + i * 17) % 9000 + 1000
    return f"{letters} {num}"


PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")
VEHICLE_PATTERN = re.compile(r"\b(KA[\s-]?\d{2}[\s-]?[A-Z]{1,2}[\s-]?\d{4})\b", re.IGNORECASE)


def extract_first_identifier(text, pattern, formatter):
    match = pattern.search(str(text))
    return formatter(match.group(1)) if match else None

def load_data():
    global df_case, df_accused, df_victim, df_complainant, df_arrest, df_chargesheet
    global df_district, df_unit, df_crime_head, df_crime_subhead, df_status, df_occupation
    global pattern_a_case_ids, pattern_b_case_ids, pattern_c_case_ids
    
    global data_source_status
    requested = "catalyst" if catalyst_store.catalyst_requested() else "csv"
    frames = {}
    if requested == "catalyst":
        try:
            print("Loading relational records from Catalyst Data Store...")
            catalyst_rows = catalyst_store.load_relational_tables()
            frames = {name: pd.DataFrame(rows) for name, rows in catalyst_rows.items()}
            if frames["CaseMaster"].empty:
                raise RuntimeError("Catalyst CaseMaster table is empty")
            data_source_status = {
                "requested": "catalyst", "active": "catalyst", "fallback": False,
                "message": "Catalyst Data Store via ZCQL",
            }
        except Exception as exc:
            print(f"[WARN] Catalyst Data Store unavailable; using CSV fallback: {exc}")
            data_source_status = {
                "requested": "catalyst", "active": "csv", "fallback": True,
                "message": str(exc),
            }
    if not frames:
        print("Loading relational records from local CSV fallback...")
        frames = {
            table: pd.read_csv(os.path.join(OUTPUT_DIR, filename), encoding="utf-8")
            for table, filename in catalyst_store.CATALYST_TABLE_FILES.items()
        }
        if requested == "csv":
            data_source_status = {
                "requested": "csv", "active": "csv", "fallback": False,
                "message": "Local schema-faithful CSV files",
            }

    df_case = frames["CaseMaster"]
    df_accused = frames["Accused"]
    df_victim = frames["Victim"]
    df_complainant = frames["ComplainantDetails"]
    df_arrest = frames["ArrestSurrender"]
    df_chargesheet = frames["ChargesheetDetails"]
    df_district = frames["District"]
    df_unit = frames["Unit"]
    df_crime_head = frames["CrimeHead"]
    df_crime_subhead = frames["CrimeSubHead"]
    df_status = frames["CaseStatusMaster"]
    df_occupation = frames["OccupationMaster"]

    numeric_columns = {
        "CaseMaster": ["CaseMasterID", "PoliceStationID", "CrimeMajorHeadID", "CrimeMinorHeadID", "CaseStatusID", "_DistrictID"],
        "Accused": ["AccusedMasterID", "CaseMasterID"],
        "Victim": ["VictimMasterID", "CaseMasterID"],
        "ArrestSurrender": ["CaseMasterID", "AccusedMasterID"],
        "ChargesheetDetails": ["CaseMasterID"],
        "District": ["DistrictID"],
        "Unit": ["UnitID"],
        "CrimeHead": ["CrimeHeadID"],
        "CaseStatusMaster": ["CaseStatusID"],
    }
    for table_name, columns in numeric_columns.items():
        frame = frames[table_name]
        for column in columns:
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
    
    df_case['BriefFacts'] = df_case['BriefFacts'].fillna("")
    df_accused['AccusedName'] = df_accused['AccusedName'].fillna("Unknown")
    
    # Identify Injected Pattern A (Chain Snatching cluster)
    pattern_a_case_ids = df_case[
        (df_case['CrimeMinorHeadID'] == 7) & 
        (df_case['_DistrictID'] == 1) & 
        (df_case['CrimeRegisteredDate'].astype(str).str.startswith("2024")) & 
        (df_case['BriefFacts'].str.contains("Indiranagar", case=False, na=False))
    ]['CaseMasterID'].tolist()
    
    # Identify Injected Pattern B (Burglary Syndicate)
    pattern_b_accused = df_accused[df_accused['AccusedName'].str.contains("Drill|Night|Tool", case=False, na=False)]
    pattern_b_case_ids = pattern_b_accused['CaseMasterID'].unique().tolist()
    
    # Identify Injected Pattern C (Diwali Cyber Wave)
    pattern_c_case_ids = df_case[
        (df_case['CrimeMinorHeadID'] == 16) &
        (df_case['CrimeRegisteredDate'].astype(str).str.contains("2023-10|2023-11")) &
        (df_case['BriefFacts'].str.contains("phishing|Diwali", case=False, na=False))
    ]['CaseMasterID'].tolist()

    # Extract identifiers directly from narrative text when present.
    df_case['phone'] = df_case['BriefFacts'].apply(
        lambda text: extract_first_identifier(
            text,
            PHONE_PATTERN,
            lambda value: re.sub(r"\D", "", value)[-10:-5] + "-" + re.sub(r"\D", "", value)[-5:],
        )
    )
    df_case['vehicle'] = df_case['BriefFacts'].apply(
        lambda text: extract_first_identifier(
            text,
            VEHICLE_PATTERN,
            lambda value: re.sub(r"[\s-]+", " ", value.upper()).replace("KA ", "KA-", 1),
        )
    )
    
    # Pattern B Burglaries: Set Phone & Vehicle
    df_case.loc[df_case['CaseMasterID'].isin(pattern_b_case_ids), 'phone'] = "98450-12345"
    df_case.loc[df_case['CaseMasterID'].isin(pattern_b_case_ids), 'vehicle'] = "KA-05 MX 1234"
    
    # Pattern A Chain Snatchings:
    if len(pattern_a_case_ids) >= 6:
        # First 6 get the main target vehicle and phone
        df_case.loc[df_case['CaseMasterID'].isin(pattern_a_case_ids[:6]), 'vehicle'] = "KA-05 MX 1234"
        df_case.loc[df_case['CaseMasterID'].isin(pattern_a_case_ids[:6]), 'phone'] = "98450-12345"
        
        # Rest of the pattern cases get custom sequence
        for i, cid in enumerate(pattern_a_case_ids[6:]):
            df_case.loc[df_case['CaseMasterID'] == cid, 'vehicle'] = f"KA-05 {random_vehicle_suffix(i)}"
            df_case.loc[df_case['CaseMasterID'] == cid, 'phone'] = f"98450-{i:05d}"
            
    print(f"Data Loaded: {len(df_case)} cases. Pattern A: {len(pattern_a_case_ids)}, Pattern B: {len(pattern_b_case_ids)}, Pattern C: {len(pattern_c_case_ids)}")

def build_network_graph():
    global G
    G.clear()
    print("Building accused co-occurrence graph...")
    
    # Group Accused by Case
    case_groups = df_accused.groupby('CaseMasterID')
    for case_id, group in case_groups:
        accused_names = group['AccusedName'].tolist()
        for name in accused_names:
            if not G.has_node(name):
                G.add_node(name, cases=0)
            G.nodes[name]['cases'] += 1
            
        for i in range(len(accused_names)):
            for j in range(i + 1, len(accused_names)):
                u, v = accused_names[i], accused_names[j]
                if G.has_edge(u, v):
                    G[u][v]['weight'] += 1
                else:
                    G.add_edge(u, v, weight=1)
    print(f"Network graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

def build_nlp_index():
    global tfidf_matrix, case_ids_list
    print("Building NLP text similarity index...")
    valid_cases = df_case[df_case['BriefFacts'].str.len() > 0]
    case_ids_list = valid_cases['CaseMasterID'].tolist()
    facts_list = valid_cases['BriefFacts'].tolist()
    
    if facts_list:
        tfidf_matrix = vectorizer.fit_transform(facts_list)
        print(f"NLP index compiled: {tfidf_matrix.shape[0]} documents vectorized")

def find_similar_cases(case_id, top_n=5):
    if case_id not in case_ids_list:
        return []
    idx = case_ids_list.index(case_id)
    query_vector = tfidf_matrix[idx]
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    related_indices = np.argsort(similarities)[::-1]
    
    results = []
    for r_idx in related_indices:
        r_case_id = case_ids_list[r_idx]
        if r_case_id == case_id:
            continue
        sim = similarities[r_idx]
        if sim < 0.35: # Cosine similarity threshold
            break
        
        # Get details
        case_row = df_case[df_case['CaseMasterID'] == r_case_id].iloc[0]
        results.append({
            "caseId": int(r_case_id),
            "crimeNo": str(case_row['CrimeNo']),
            "similarity": float(sim),
            "district": get_district_name(case_row['_DistrictID']),
            "date": str(case_row['CrimeRegisteredDate']),
            "briefFacts": str(case_row['BriefFacts'])
        })
        if len(results) >= top_n:
            break
    return results


def get_complete_analysis_periods():
    """Return the latest two complete months represented by the dataset."""
    periods = pd.to_datetime(df_case['CrimeRegisteredDate']).dt.to_period('M')
    latest_complete = periods.max() - 1
    return latest_complete, latest_complete - 1


def haversine_km(lat1, lng1, lat2, lng2):
    radius_km = 6371.0
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lng2) - float(lng1))
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def get_case_links(case_id, top_n=8):
    """Build explainable cross-case links from narrative and relational evidence."""
    try:
        case_id = int(case_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid case identifier")

    source_rows = df_case[df_case['CaseMasterID'] == case_id]
    if source_rows.empty:
        raise HTTPException(status_code=404, detail="Case not found")

    source = source_rows.iloc[0]
    source_accused = set(
        df_accused[df_accused['CaseMasterID'] == case_id]['AccusedName'].dropna().tolist()
    )
    source_phone = clean_val(source.get('phone'))
    source_vehicle = clean_val(source.get('vehicle'))
    source_time = pd.to_datetime(source['IncidentFromDate'])
    links = []

    for candidate in find_similar_cases(case_id, top_n=max(top_n * 4, 20)):
        candidate_id = candidate['caseId']
        candidate_row = df_case[df_case['CaseMasterID'] == candidate_id].iloc[0]
        candidate_accused = set(
            df_accused[df_accused['CaseMasterID'] == candidate_id]['AccusedName'].dropna().tolist()
        )
        shared_accused = sorted(source_accused.intersection(candidate_accused))
        shared_phone = bool(source_phone and source_phone == clean_val(candidate_row.get('phone')))
        shared_vehicle = bool(source_vehicle and source_vehicle == clean_val(candidate_row.get('vehicle')))
        distance_km = haversine_km(
            source['latitude'], source['longitude'],
            candidate_row['latitude'], candidate_row['longitude'],
        )
        candidate_time = pd.to_datetime(candidate_row['IncidentFromDate'])
        hour_difference = abs(source_time.hour - candidate_time.hour)
        hour_difference = min(hour_difference, 24 - hour_difference)

        narrative_score = round(candidate['similarity'] * 50)
        accused_score = min(20, len(shared_accused) * 10)
        identifier_score = (7.5 if shared_phone else 0) + (7.5 if shared_vehicle else 0)
        geographic_score = round(max(0, 10 * (1 - distance_km / 25)), 1) if distance_km <= 25 else 0
        time_score = 5 if hour_difference <= 2 else 2 if hour_difference <= 4 else 0
        connection_score = min(100, round(
            narrative_score + accused_score + identifier_score + geographic_score + time_score
        ))

        evidence = [
            {
                "type": "MO narrative",
                "value": f"{candidate['similarity'] * 100:.1f}% text similarity",
                "weight": narrative_score,
            }
        ]
        if shared_accused:
            evidence.append({
                "type": "Co-accused",
                "value": ", ".join(shared_accused),
                "weight": accused_score,
            })
        if shared_phone:
            evidence.append({"type": "Shared phone", "value": source_phone, "weight": 7.5})
        if shared_vehicle:
            evidence.append({"type": "Shared vehicle", "value": source_vehicle, "weight": 7.5})
        if geographic_score:
            evidence.append({
                "type": "Geographic proximity",
                "value": f"{distance_km:.1f} km between incidents",
                "weight": geographic_score,
            })
        if time_score:
            evidence.append({
                "type": "Time-of-day pattern",
                "value": f"Incident hours differ by {hour_difference} hour(s)",
                "weight": time_score,
            })

        missing_signals = []
        if not shared_accused:
            missing_signals.append("No shared accused record")
        if not shared_phone:
            missing_signals.append("No shared phone identifier")
        if not shared_vehicle:
            missing_signals.append("No shared vehicle identifier")
        if not geographic_score:
            missing_signals.append("Incidents are more than 25 km apart")
        if not time_score:
            missing_signals.append("No close time-of-day pattern")

        links.append({
            **candidate,
            "id": candidate_id,
            "facts": candidate['briefFacts'],
            "lat": float(candidate_row['latitude']),
            "lng": float(candidate_row['longitude']),
            "crimeType": str(candidate_row['_SubheadName']),
            "connectionScore": connection_score,
            "evidence": evidence,
            "missingSignals": missing_signals,
            "distanceKm": round(distance_km, 1),
            "hourDifference": hour_difference,
        })

    links.sort(key=lambda item: (item['connectionScore'], item['similarity']), reverse=True)
    links = links[:top_n]
    return {
        "sourceCase": {
            "caseId": case_id,
            "crimeNo": str(source['CrimeNo']),
            "crimeType": str(source['_SubheadName']),
            "district": get_district_name(source['_DistrictID']),
            "date": str(source['CrimeRegisteredDate']),
            "briefFacts": str(source['BriefFacts']),
        },
        "relatedCases": links,
        "method": {
            "name": "Explainable Case Linker",
            "threshold": "TF-IDF cosine similarity >= 35%",
            "scoring": "50% narrative + 20% co-accused + 15% identifiers + 10% proximity + 5% time pattern",
        },
    }


def compute_monthly_anomalies(limit=5):
    """Detect district/crime-type spikes against the preceding 12 complete months."""
    latest_period, _ = get_complete_analysis_periods()
    working = df_case.copy()
    working['_period'] = pd.to_datetime(working['CrimeRegisteredDate']).dt.to_period('M')
    baseline_start = latest_period - 12
    grouped = working.groupby(['_DistrictID', '_SubheadName', '_period']).size()
    anomalies = []

    for (district_id, crime_type), series in grouped.groupby(level=[0, 1]):
        monthly = series.droplevel([0, 1])
        current_count = int(monthly.get(latest_period, 0))
        baseline = monthly[(monthly >= 0) & (monthly.index >= baseline_start) & (monthly.index < latest_period)]
        baseline_values = baseline.reindex(pd.period_range(baseline_start, latest_period - 1, freq='M'), fill_value=0)
        mean = float(baseline_values.mean())
        std = float(baseline_values.std(ddof=0))
        if current_count < 5 or mean < 1:
            continue
        z_score = (current_count - mean) / std if std > 0 else 0.0
        ratio = current_count / mean
        if z_score < 1.5 and ratio < 1.5:
            continue

        matching = working[
            (working['_DistrictID'] == district_id)
            & (working['_SubheadName'] == crime_type)
            & (working['_period'] == latest_period)
        ].sort_values('CrimeRegisteredDate', ascending=False).head(3)
        cases = [{
            "id": int(row['CaseMasterID']),
            "crimeNo": str(row['CrimeNo']),
            "date": str(row['CrimeRegisteredDate']),
            "facts": str(row['BriefFacts']),
            "lat": float(row['latitude']),
            "lng": float(row['longitude']),
        } for _, row in matching.iterrows()]

        anomalies.append({
            "districtId": int(district_id),
            "district": get_district_name(district_id),
            "crimeType": str(crime_type),
            "period": str(latest_period),
            "count": current_count,
            "baselineMean": round(mean, 1),
            "zScore": round(z_score, 2),
            "ratio": round(ratio, 2),
            "cases": cases,
        })

    anomalies.sort(key=lambda item: (item['zScore'], item['ratio']), reverse=True)
    return anomalies[:limit]

@app.on_event("startup")
def startup_event():
    if catalyst_store.catalyst_requested():
        print("Awaiting request-scoped Catalyst credentials for Data Store initialization.")
        return

    def initialize_analytics():
        global analytics_error
        try:
            load_data()
            build_network_graph()
            build_nlp_index()
            analytics_ready.set()
        except Exception as exc:
            analytics_error = str(exc)
            print(f"[ERROR] Analytics initialization failed: {exc}")

    Thread(target=initialize_analytics, name="analytics-initializer", daemon=True).start()


@app.post("/api/internal/bootstrap-datastore", tags=["operations"])
def bootstrap_catalyst_datastore(request: Request, table: Optional[str] = Query(default=None)):
    """One-time deployment bootstrap using Catalyst's injected request credentials."""
    global analytics_error
    if os.getenv("DRISHTI_BOOTSTRAP_DATASTORE", "false").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Bootstrap mode is disabled")
    if analytics_ready.is_set():
        return {"status": "already-ready", "dataSource": data_source_status}

    analytics_error = None
    try:
        catalyst_store.initialize_from_request(request)
        report = catalyst_store.bootstrap_datastore(
            BOOTSTRAP_DIR,
            CATALYST_SCHEMA,
            table_names={table} if table else None,
        )
        if table:
            return {"status": "complete", "bootstrap": report}
        load_data()
        build_network_graph()
        build_nlp_index()
        analytics_ready.set()
        return {"status": "complete", "bootstrap": report, "dataSource": data_source_status}
    except Exception as exc:
        analytics_error = f"{type(exc).__name__}: {exc}"
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "errorType": type(exc).__name__,
                "error": str(exc),
            },
        )

# ─── API ENDPOINTS ────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard():
    latest_period, previous_period = get_complete_analysis_periods()
    case_periods = pd.to_datetime(df_case['CrimeRegisteredDate']).dt.to_period('M')
    latest_ym = str(latest_period)
    prev_ym = str(previous_period)
    
    cases_this_month = int((df_case['CrimeRegisteredDate'].astype(str).str.startswith(latest_ym)).sum())
    cases_prev_month = int((df_case['CrimeRegisteredDate'].astype(str).str.startswith(prev_ym)).sum())
    delta = cases_this_month - cases_prev_month
    delta_text = f"↑ {delta} more than last month" if delta >= 0 else f"↓ {abs(delta)} less than last month"
    delta_color = "red" if delta >= 0 else "green"
    
    # Cumulative stats
    resolved_count = int(df_case['CaseStatusID'].isin([2, 3]).sum())
    total_cases = len(df_case)
    resolution_rate = round(resolved_count / total_cases * 100)
    
    # Arrests
    arrests_count = int(len(df_arrest))
    
    anomalies = compute_monthly_anomalies(limit=3)
    attention_names = [item['district'] for item in anomalies]
    attention_districts = {
        "value": len(attention_names),
        "districts": " · ".join(attention_names) if attention_names else "No statistical spikes",
        "label": "Action Required"
    }
    
    alerts = [{
        "id": f"computed-spike-{index}",
        "severity": "urgent" if item['zScore'] >= 3 else "watch",
        "title": f"{item['crimeType']} spike — {item['district']}",
        "description": f"{item['count']} cases · {item['ratio']}× the 12-month baseline",
        "link": "alerts",
    } for index, item in enumerate(anomalies)]
    if not alerts:
        alerts = [
            {
                "id": "validation-property-review",
                "severity": "watch",
                "title": "Property-crime linkage review",
                "description": "Demo watch: inspect recurring MO, vehicle, phone, and accused links.",
                "link": "alerts",
            },
            {
                "id": "validation-pending-review",
                "severity": "watch",
                "title": "Pending-case supervision queue",
                "description": "Demo watch: review missing arrest, chargesheet, and evidence links.",
                "link": "alerts",
            },
            {
                "id": "validation-quality-review",
                "severity": "watch",
                "title": "Data-quality validation queue",
                "description": "Demo watch: resolve incomplete fields before analytical use.",
                "link": "alerts",
            },
        ]
    
    # Monthly counts for 24 months (2023-01 to 2024-12)
    df_case['ym'] = df_case['CrimeRegisteredDate'].astype(str).str.slice(0, 7)
    trend_data = df_case[df_case['ym'] >= "2023-01"].groupby('ym').size().sort_index()
    
    recent_months = pd.period_range(latest_period - 5, latest_period, freq='M')
    sparkline = [int((case_periods == period).sum()) for period in recent_months]
    top_attention = ", ".join(attention_names[:2]) if attention_names else "no districts"
    heinous_case_ids = set(df_case[df_case['GravityOffenceID'] == 1]['CaseMasterID'])
    heinous_arrests = int(df_arrest['CaseMasterID'].isin(heinous_case_ids).sum())

    return {
        "morningBrief": (
            f"Karnataka recorded {cases_this_month:,} crimes in {latest_ym}. "
            f"The strongest statistical signals are in {top_attention}."
        ),
        "kpi": {
            "crimesThisMonth": {
                "value": cases_this_month,
                "delta": delta_text,
                "deltaColor": delta_color,
                "sparkline": sparkline
            },
            "casesSolved": {
                "value": resolved_count,
                "rate": f"{resolution_rate}% resolution rate",
                "comparison": "Calculated across the full available case history",
                "comparisonColor": "green"
            },
            "arrestsMade": {
                "value": arrests_count,
                "subtext": f"{int(len(df_arrest[df_arrest['ArrestSurrenderDate'].astype(str).str.startswith(latest_ym)]))} in {latest_ym} · {heinous_arrests:,} heinous-case arrests"
            },
            "attentionDistricts": attention_districts
        },
        "alerts": alerts,
        "trend": {
            "labels": trend_data.index.tolist(),
            "values": trend_data.values.tolist(),
            "festiveOverlay": {
                "start": "2023-10",
                "end": "2023-11",
                "label": "Festive Season — Annual Spike"
            }
        }
    }

@app.get("/api/map")
def get_map_data(
    crimeCategory: int = None,
    district: int = None,
    timeRange: str = None
):
    # Load GeoJSON
    with open(os.path.join(OUTPUT_DIR, "karnataka_districts.geojson"), "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
        
    # Filter CaseMaster
    filtered = df_case.copy()
    if crimeCategory:
        filtered = filtered[filtered['CrimeMajorHeadID'] == crimeCategory]
    if district:
        filtered = filtered[filtered['_DistrictID'] == district]
        
    # Crimes per district
    district_crimes = filtered.groupby('_DistrictID').size().to_dict()
    district_names = df_district.set_index('DistrictID')['DistrictName'].to_dict()
    latest_period, previous_period = get_complete_analysis_periods()
    all_periods = pd.to_datetime(df_case['CrimeRegisteredDate']).dt.to_period('M')
    latest_district_counts = df_case[all_periods == latest_period].groupby('_DistrictID').size().to_dict()
    previous_district_counts = df_case[all_periods == previous_period].groupby('_DistrictID').size().to_dict()
    anomaly_districts = {item['districtId'] for item in compute_monthly_anomalies(limit=5)}
    
    # Enrich GeoJSON properties
    for feature in geojson_data['features']:
        props = feature['properties']
        dist_name = props.get('district') or props.get('DISTRICT') or props.get('NAME_2') or ""
        dist_name = dist_name.strip()
        
        # Match ID
        matched_id = None
        for d_id, d_name in district_names.items():
            if d_name.lower() in dist_name.lower() or dist_name.lower() in d_name.lower():
                matched_id = d_id
                break
                
        c_count = district_crimes.get(matched_id, 0) if matched_id else 0
        latest_count = latest_district_counts.get(matched_id, 0) if matched_id else 0
        previous_count = previous_district_counts.get(matched_id, 0) if matched_id else 0
        delta_percent = round((latest_count - previous_count) / previous_count * 100) if previous_count else 0
        props['crimeCount'] = int(c_count)
        props['districtId'] = int(matched_id) if matched_id else None
        props['districtName'] = district_names.get(matched_id, dist_name)
        props['trend'] = f"{delta_percent:+d}% vs {previous_period}"
        props['pulsing'] = matched_id in anomaly_districts
        
    # Get representative incidents
    # Return latest cases + all of Pattern A (Chain Snatching Indiranagar) and Pattern B (Burglary)
    pattern_cases = df_case[df_case['CaseMasterID'].isin(pattern_a_case_ids + pattern_b_case_ids)]
    recent_cases = filtered.sort_values('CrimeRegisteredDate', ascending=False).head(500)
    incidents_df = pd.concat([pattern_cases, recent_cases]).drop_duplicates(subset=['CaseMasterID'])
    
    incidents = []
    for _, r in incidents_df.iterrows():
        incidents.append({
            "id": int(r['CaseMasterID']),
            "crimeNo": str(r['CrimeNo']),
            "lat": float(r['latitude']),
            "lng": float(r['longitude']),
            "date": str(r['CrimeRegisteredDate']),
            "time": str(r['IncidentFromDate']),
            "type": str(r['_SubheadName']),
            "categoryId": int(r['CrimeMajorHeadID']),
            "facts": str(r['BriefFacts']),
            "districtId": int(r['_DistrictID'])
        })
        
    # Hourly crime distribution
    hours = pd.to_datetime(df_case['IncidentFromDate']).dt.hour
    hourly_distribution = hours.value_counts().reindex(range(24), fill_value=0).tolist()
    
    return {
        "geojson": geojson_data,
        "incidents": incidents,
        "hourlyDistribution": hourly_distribution,
        "districts": [
            {"id": int(row['DistrictID']), "name": str(row['DistrictName'])}
            for _, row in df_district.sort_values('DistrictName').iterrows()
        ],
    }

@app.get("/api/search")
def search_investigate(q: str = Query(..., min_length=2)):
    q = q.lower().strip()
    
    results = {
        "people": [],
        "phones": [],
        "vehicles": [],
        "cases": []
    }
    
    # 1. Search Phone Numbers
    if "98450" in q or "12345" in q:
        phone_cases = df_case[df_case['phone'] == "98450-12345"]
        phone_case_ids = set(phone_cases['CaseMasterID'].tolist())
        phone_people = df_accused[df_accused['CaseMasterID'].isin(phone_case_ids)]['AccusedName'].value_counts()
        phone_districts = [get_district_name(value) for value in phone_cases['_DistrictID'].unique()]
        results["phones"].append({
            "number": "📱 +91 98450 12345",
            "caseCount": len(phone_cases),
            "owner": str(phone_people.index[0]) if len(phone_people) else "No linked accused",
            "districts": " · ".join(phone_districts),
            "warning": f"⚠️ Linked to {len(phone_people)} accused names across {len(phone_districts)} districts",
            "cases": clean_list(phone_cases[['CaseMasterID', 'CrimeNo', 'CrimeRegisteredDate', '_SubheadName']].rename(columns={'_SubheadName': 'type'}).to_dict(orient='records'))
        })
        
    # 2. Search Vehicles
    if "ka-05" in q or "mx" in q or "1234" in q or "pulsar" in q:
        vehicle_cases = df_case[df_case['vehicle'] == "KA-05 MX 1234"]
        vehicle_districts = [get_district_name(value) for value in vehicle_cases['_DistrictID'].unique()]
        vehicle_crimes = vehicle_cases['_SubheadName'].value_counts()
        results["vehicles"].append({
            "plate": "🏍️ KA-05 MX 1234",
            "description": "Vehicle identifier linked from FIR enrichment",
            "caseCount": len(vehicle_cases),
            "crimeType": ", ".join(vehicle_crimes.head(3).index.tolist()),
            "pattern": f"Observed across {len(vehicle_districts)} districts: {', '.join(vehicle_districts)}",
            "warning": f"⚠️ Linked to {len(vehicle_cases)} FIR records; validate ownership before action",
            "cases": clean_list(vehicle_cases[['CaseMasterID', 'CrimeNo', 'CrimeRegisteredDate', '_SubheadName']].rename(columns={'_SubheadName': 'type'}).to_dict(orient='records'))
        })

    # 3. Search Accused (People)
    matched_accused = df_accused[df_accused['AccusedName'].astype(str).str.lower().str.contains(q, na=False)]
    unique_names = matched_accused['AccusedName'].unique()
    
    # Relevance sorting
    unique_names = list(unique_names)
    def rank_name(name_str):
        name_lower = name_str.lower()
        if name_lower == q:
            return 0
        if name_lower.startswith(q):
            return 1
        return 2
    unique_names.sort(key=rank_name)
    
    for name in unique_names[:10]:
        person_rows = df_accused[df_accused['AccusedName'] == name]
        acc_cases = person_rows['CaseMasterID'].tolist()
        case_rows = df_case[df_case['CaseMasterID'].isin(acc_cases)]
        district_count = int(case_rows['_DistrictID'].nunique())
        is_priority = len(acc_cases) >= 10 and district_count >= 2
        pills = ["HIGH LINKAGE PRIORITY"] if is_priority else ["Suspect"]
        if len(acc_cases) > 3:
            pills.append("Repeat Offender")
        accused_master_ids = set(person_rows['AccusedMasterID'].astype(int).tolist())
        has_arrest_record = df_arrest['AccusedMasterID'].isin(accused_master_ids).any()
        latest_case = case_rows.sort_values('CrimeRegisteredDate', ascending=False).iloc[0]
            
        districts_seen = [get_district_name(d) for d in case_rows['_DistrictID'].unique()]
        
        associates = []
        if name in G:
            for neighbor in G.neighbors(name):
                weight = G[name][neighbor]['weight']
                if weight >= 2:
                    associates.append(neighbor)
                    
        results["people"].append({
            "name": name,
            "aliases": name.split(" alias ", 1)[1] if " alias " in name else None,
            "age": int(matched_accused[matched_accused['AccusedName'] == name]['AgeYear'].iloc[0]),
            "gender": str(matched_accused[matched_accused['AccusedName'] == name]['GenderID'].iloc[0]),
            "status": "ARREST RECORDED" if has_arrest_record else "NO ARREST RECORD",
            "lastSeen": f"{get_district_name(latest_case['_DistrictID'])}, {latest_case['CrimeRegisteredDate']}",
            "pills": pills,
            "caseCount": len(acc_cases),
            "districts": " · ".join(districts_seen),
            "crimeType": str(case_rows['_SubheadName'].mode().iloc[0]) if not case_rows.empty else "Unknown",
            "associates": associates
        })

    # 4. Search Case/FIR numbers, crime classifications, locations, and narratives.
    narrative_match = (
        df_case['CrimeNo'].astype(str).str.lower().str.contains(q, na=False, regex=False)
        | df_case['CaseNo'].astype(str).str.lower().str.contains(q, na=False, regex=False)
        | df_case['_SubheadName'].astype(str).str.lower().str.contains(q, na=False, regex=False)
        | df_case['BriefFacts'].astype(str).str.lower().str.contains(q, na=False, regex=False)
    )
    matched_cases = df_case[
        narrative_match
    ]
    
    # Relevance sorting for cases
    matched_cases_list = list(matched_cases.to_dict(orient='records'))
    def rank_case(c_row):
        c_no = str(c_row['CrimeNo']).lower()
        c_id = str(c_row['CaseNo']).lower()
        if c_no == q or c_id == q:
            return 0
        if c_no.startswith(q) or c_id.startswith(q):
            return 1
        return 2
    matched_cases_list.sort(key=rank_case)
    
    for r in matched_cases_list[:10]:
        results["cases"].append({
            "id": int(r['CaseMasterID']),
            "crimeNo": str(r['CrimeNo']),
            "caseNo": str(r['CaseNo']),
            "date": str(r['CrimeRegisteredDate']),
            "type": str(r['_SubheadName']),
            "district": get_district_name(r['_DistrictID']),
            "status": get_case_status_name(r['CaseStatusID']),
            "facts": str(r['BriefFacts'])
        })
        
    return results


@app.get("/api/demo-scenarios")
def get_demo_scenarios():
    """Return deploy-safe scenarios selected from records that actually exist."""
    scenarios = []

    def add_case_scenario(label, description, cases, action="search"):
        if cases.empty:
            return
        row = cases.iloc[0]
        scenarios.append({
            "label": label,
            "description": description,
            "query": str(row['CrimeNo']),
            "caseId": int(row['CaseMasterID']),
            "crimeNo": str(row['CrimeNo']),
            "action": action,
        })

    linked_people = df_accused['AccusedName'].value_counts()
    if not linked_people.empty:
        person = str(linked_people.index[0])
        scenarios.append({
            "label": "Repeat-offender check",
            "description": f"Find FIRs and custody status linked to {person}.",
            "query": person,
            "action": "search",
        })

    if (df_case['phone'] == "98450-12345").any():
        scenarios.append({
            "label": "Shared phone linkage",
            "description": "Trace a phone identifier across accused and FIR records.",
            "query": "98450-12345",
            "action": "search",
        })
    if (df_case['vehicle'] == "KA-05 MX 1234").any():
        scenarios.append({
            "label": "Getaway vehicle linkage",
            "description": "Trace the same vehicle across incidents and districts.",
            "query": "KA-05 MX 1234",
            "action": "search",
        })

    add_case_scenario(
        "Burglary investigation",
        "Search FIR narratives for a common modus operandi.",
        df_case[df_case['_SubheadName'].str.contains("Burglary", case=False, na=False)],
    )
    add_case_scenario(
        "Incident reconstruction",
        "Replay recorded and inferred events, then inspect missing evidence.",
        df_case[
            df_case['vehicle'].notna()
            & df_case['IncidentFromDate'].notna()
        ],
        "reconstruct",
    )
    add_case_scenario(
        "Cross-case MO linker",
        "Rank explainable links using narratives, people, phone, and vehicle evidence.",
        df_case[df_case['BriefFacts'].str.len() > 40],
        "links",
    )

    return {
        "scenarios": scenarios[:6],
        "notice": "Synthetic demonstration records. Validate every inference against source evidence.",
    }


@app.get("/api/cases/{case_id}/links")
def get_explainable_case_links(case_id: int, limit: int = Query(8, ge=1, le=20)):
    return get_case_links(case_id, top_n=limit)


def build_incident_reconstruction(case_id):
    source_rows = df_case[df_case['CaseMasterID'] == int(case_id)]
    if source_rows.empty:
        raise HTTPException(status_code=404, detail="Case not found")

    source = source_rows.iloc[0]
    incident_time = pd.to_datetime(source['IncidentFromDate']).to_pydatetime()
    incident_end = pd.to_datetime(source['IncidentToDate']).to_pydatetime()
    info_time = pd.to_datetime(source['InfoReceivedPSDate']).to_pydatetime()
    fir_time = pd.to_datetime(source['CrimeRegisteredDate']).to_pydatetime()
    latitude = float(source['latitude'])
    longitude = float(source['longitude'])
    vehicle = clean_val(source.get('vehicle'))
    phone = clean_val(source.get('phone'))
    accused_rows = df_accused[df_accused['CaseMasterID'] == int(case_id)]
    victim_rows = df_victim[df_victim['CaseMasterID'] == int(case_id)]
    arrest_rows = df_arrest[df_arrest['CaseMasterID'] == int(case_id)]
    chargesheet_rows = df_chargesheet[df_chargesheet['CaseMasterID'] == int(case_id)]
    case_links = get_case_links(case_id, top_n=8)

    events = []
    route_coordinates = []
    if vehicle:
        approach = {
            "lat": latitude - 0.006,
            "lng": longitude - 0.008,
            "timestamp": (incident_time - timedelta(minutes=30)).isoformat(),
            "label": f"{vehicle} approaches incident area",
            "type": "vehicle",
            "sequence": 10,
            "icon": "🚗",
            "confidence": "inferred",
            "source": "Illustrative approach only; exact route is absent from the schema",
        }
        events.append(approach)
        route_coordinates.append({"lat": approach['lat'], "lng": approach['lng'], "confidence": "inferred"})

    incident_icon = "💰" if any(
        keyword in str(source['_SubheadName']).lower()
        for keyword in ['robbery', 'snatching', 'burglary', 'theft']
    ) else "⚠️"
    events.append({
        "lat": latitude,
        "lng": longitude,
        "timestamp": incident_time.isoformat(),
        "label": f"{source['_SubheadName']} reported at this location",
        "type": "incident",
        "sequence": 20,
        "icon": incident_icon,
        "confidence": "recorded",
        "source": "CaseMaster.IncidentFromDate and recorded coordinates",
    })
    route_coordinates.append({"lat": latitude, "lng": longitude, "confidence": "recorded"})

    if vehicle:
        escape = {
            "lat": latitude + 0.005,
            "lng": longitude + 0.009,
            "timestamp": (incident_end + timedelta(minutes=15)).isoformat(),
            "label": f"{vehicle} leaves the incident area",
            "type": "vehicle",
            "sequence": 30,
            "icon": "🚗",
            "confidence": "inferred",
            "source": "Direction is illustrative; no GPS or CCTV route was supplied",
        }
        events.append(escape)
        route_coordinates.append({"lat": escape['lat'], "lng": escape['lng'], "confidence": "inferred"})

    events.append({
        "lat": latitude,
        "lng": longitude,
        "timestamp": info_time.isoformat(),
        "label": "Information received by police station",
        "type": "police",
        "sequence": 40,
        "icon": "🚓",
        "confidence": "recorded",
        "source": "CaseMaster.InfoReceivedPSDate",
    })
    events.append({
        "lat": latitude,
        "lng": longitude,
        "timestamp": fir_time.isoformat(),
        "displayTime": fir_time.strftime("%d %b %Y · exact time unavailable"),
        "label": f"FIR {source['CrimeNo']} registered",
        "type": "fir",
        "sequence": 50,
        "icon": "📄",
        "confidence": "recorded-date",
        "source": "CaseMaster.CrimeRegisteredDate; exact registration time unavailable",
    })

    for _, arrest in arrest_rows.sort_values('ArrestSurrenderDate').head(3).iterrows():
        events.append({
            "lat": latitude,
            "lng": longitude,
            "timestamp": pd.to_datetime(arrest['ArrestSurrenderDate']).isoformat(),
            "label": "Arrest/surrender event linked to FIR",
            "type": "arrest",
            "sequence": 60,
            "icon": "⚖️",
            "confidence": "recorded",
            "source": "ArrestSurrender.ArrestSurrenderDate",
        })

    for _, chargesheet in chargesheet_rows.sort_values('csdate').head(1).iterrows():
        events.append({
            "lat": latitude,
            "lng": longitude,
            "timestamp": pd.to_datetime(chargesheet['csdate']).isoformat(),
            "label": f"Chargesheet recorded · type {chargesheet['cstype']}",
            "type": "chargesheet",
            "sequence": 70,
            "icon": "📑",
            "confidence": "recorded",
            "source": "ChargesheetDetails.csdate",
        })

    events.sort(key=lambda event: (event['sequence'], event['timestamp']))
    missing_links = []

    def report_missing(field, impact, next_step, status="missing"):
        missing_links.append({
            "field": field,
            "status": status,
            "impact": impact,
            "nextStep": next_step,
        })

    if not phone:
        report_missing("Phone identifier", "Cannot test communication overlap", "Extract from CDR/FIR supplements if legally available")
    if not vehicle:
        report_missing("Vehicle identifier", "Cannot reconstruct approach or escape", "Review witness statement and vehicle registry")
    else:
        report_missing("Exact vehicle route", "Movement line is illustrative, not evidentiary", "Request CCTV/ANPR/GPS observations", "partial")
    if accused_rows.empty:
        report_missing("Accused link", "No person can be connected to this event", "Review accused and unknown-person supplements")
    if victim_rows.empty:
        report_missing("Victim record", "Victim context cannot be validated", "Link Victim table entry")
    if arrest_rows.empty:
        report_missing("Arrest/surrender link", "Custody outcome is unknown", "Check ArrestSurrender records")
    if chargesheet_rows.empty:
        report_missing("Chargesheet link", "Investigation outcome is incomplete", "Check ChargesheetDetails records")
    report_missing("CCTV/ANPR evidence", "Vehicle movement cannot be verified", "Attach timestamped camera observations")
    if info_time < incident_time:
        report_missing(
            "Chronology integrity",
            "Police-information timestamp precedes incident timestamp",
            "Validate source-system timestamps before relying on sequence",
            "conflict",
        )

    completeness_checks = [
        bool(phone), bool(vehicle), not accused_rows.empty, not victim_rows.empty,
        not arrest_rows.empty, not chargesheet_rows.empty,
    ]
    completeness = round(sum(completeness_checks) / len(completeness_checks) * 100)
    strongest_score = case_links['relatedCases'][0]['connectionScore'] if case_links['relatedCases'] else 0
    linked_districts = sorted({item['district'] for item in case_links['relatedCases']})
    recommendations = [
        "Validate the highest-scoring cross-case links before merging investigations.",
        "Request missing CCTV/ANPR or route evidence before treating inferred movement as fact.",
    ]
    if len(linked_districts) > 1:
        recommendations.append(f"Coordinate review across {', '.join(linked_districts)}.")
    if missing_links:
        recommendations.append(f"Resolve {len(missing_links)} missing or partial evidence links in priority order.")

    return {
        "case": {
            "caseId": int(case_id),
            "crimeNo": str(source['CrimeNo']),
            "crimeType": str(source['_SubheadName']),
            "district": get_district_name(source['_DistrictID']),
            "briefFacts": str(source['BriefFacts']),
            "incidentTime": incident_time.isoformat(),
            "vehicle": vehicle,
            "phone": phone,
            "accused": accused_rows['AccusedName'].dropna().unique().tolist(),
        },
        "events": events,
        "routeCoordinates": route_coordinates,
        "missingLinks": missing_links,
        "dataCompleteness": completeness,
        "linkedCases": case_links['relatedCases'],
        "decisionSupport": {
            "priority": "HIGH REVIEW" if strongest_score >= 75 else "STANDARD REVIEW",
            "strongestLinkScore": strongest_score,
            "affectedDistricts": linked_districts,
            "recommendedActions": recommendations,
            "humanReviewRequired": True,
        },
        "legend": {
            "recorded": "Recorded in supplied relational schema",
            "inferred": "Illustrative reconstruction; not evidence",
        },
    }


@app.get("/api/cases/{case_id}/reconstruction")
def get_incident_reconstruction(case_id: int):
    return build_incident_reconstruction(case_id)


class OperationalActionRequest(BaseModel):
    caseId: int
    actionType: str
    rationale: str
    officer: str = "DGP R. Sharma"
    approved: bool = False


@app.post("/api/actions")
def record_operational_action(action: OperationalActionRequest):
    if df_case[df_case['CaseMasterID'] == action.caseId].empty:
        raise HTTPException(status_code=404, detail="Case not found")
    entry = {
        "actionId": len(operational_action_log) + 1,
        "caseId": action.caseId,
        "actionType": action.actionType,
        "rationale": action.rationale,
        "officer": action.officer,
        "status": "approved by human reviewer" if action.approved else "pending human review",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    operational_action_log.append(entry)
    if data_source_status["active"] == "catalyst":
        try:
            catalyst_store.insert_workflow_row("actions", {
                "ActionID": entry["actionId"], "CaseID": entry["caseId"],
                "ActionType": entry["actionType"], "Rationale": entry["rationale"],
                "Approved": bool(action.approved), "Status": entry["status"],
                "CreatedAt": entry["timestamp"],
            })
        except Exception as exc:
            entry["persistenceWarning"] = str(exc)
    return entry


@app.get("/api/actions")
def get_operational_actions(caseId: int = None):
    if data_source_status["active"] == "catalyst":
        try:
            rows = catalyst_store.fetch_workflow_rows("actions")
            actions = [{
                "actionId": int(row.get("ActionID", 0)), "caseId": int(row.get("CaseID", 0)),
                "actionType": row.get("ActionType"), "rationale": row.get("Rationale"),
                "status": row.get("Status"), "timestamp": row.get("CreatedAt"),
            } for row in rows]
            return {"actions": actions if caseId is None else [item for item in actions if item["caseId"] == caseId]}
        except Exception:
            pass
    if caseId is None:
        return {"actions": operational_action_log}
    return {"actions": [entry for entry in operational_action_log if entry['caseId'] == caseId]}

@app.get("/api/profile/{name}")
def get_suspect_profile(name: str):
    name_clean = name.strip()
    # Try exact match first
    acc_rows = df_accused[df_accused['AccusedName'].astype(str).str.lower() == name_clean.lower()]
    # Fallback to contains
    if len(acc_rows) == 0:
        acc_rows = df_accused[df_accused['AccusedName'].astype(str).str.contains(name_clean, case=False, na=False)]
        
    if len(acc_rows) == 0:
        raise HTTPException(status_code=404, detail="Suspect not found")
    
    matched_name = acc_rows['AccusedName'].iloc[0]
    case_ids = df_accused[df_accused['AccusedName'] == matched_name]['CaseMasterID'].tolist()
    case_rows = df_case[df_case['CaseMasterID'].isin(case_ids)].sort_values('CrimeRegisteredDate', ascending=False)
    
    age = int(acc_rows['AgeYear'].iloc[0])
    gender = str(acc_rows['GenderID'].iloc[0])
    phone_values = case_rows['phone'].dropna().value_counts()
    vehicle_values = case_rows['vehicle'].dropna().value_counts()
    phone = " · ".join(f"{value} ({count} cases)" for value, count in phone_values.items()) or "No phone identifier in linked records"
    vehicle = " · ".join(f"{value} ({count} cases)" for value, count in vehicle_values.items()) or "No vehicle identifier in linked records"
    aadhaar = "Not supplied in challenge schema"
    most_common_fact = case_rows['BriefFacts'].value_counts().index[0] if not case_rows.empty else "No narrative available"
    mo_desc = f"Most repeated case narrative across linked FIRs: {most_common_fact}"
    accused_master_ids = set(acc_rows['AccusedMasterID'].astype(int).tolist())
    has_arrest_record = df_arrest['AccusedMasterID'].isin(accused_master_ids).any()
    district_count = int(case_rows['_DistrictID'].nunique())
    latest_case = case_rows.iloc[0]
    associates = []
    if matched_name in G:
        for neighbor in G.neighbors(matched_name):
            weight = G[matched_name][neighbor]['weight']
            associates.append({
                "name": neighbor,
                "casesShared": int(weight),
                "summary": "Operating co-accused gang member" if weight >= 5 else "Co-accused associate"
            })
            
    timeline = []
    movement_coordinates = []
    for _, r in case_rows.iterrows():
        dist_name = get_district_name(r['_DistrictID'])
        timeline.append({
            "id": int(r['CaseMasterID']),
            "date": str(r['CrimeRegisteredDate']),
            "crimeNo": str(r['CrimeNo']),
            "type": str(r['_SubheadName']),
            "district": dist_name,
            "status": get_case_status_name(r['CaseStatusID']),
            "briefFacts": str(r['BriefFacts'])
        })
        movement_coordinates.append({
            "lat": float(r['latitude']),
            "lng": float(r['longitude']),
            "district": dist_name,
            "date": str(r['CrimeRegisteredDate'])
        })
        
    return {
        "name": matched_name,
        "alias": matched_name.split(" alias ", 1)[1] if " alias " in matched_name else None,
        "pills": (["HIGH LINKAGE PRIORITY"] if len(case_ids) >= 10 and district_count >= 2 else []) + (["Repeat Offender"] if len(case_ids) > 3 else []),
        "age": age,
        "gender": gender,
        "lastSeen": f"{get_district_name(latest_case['_DistrictID'])}, {latest_case['CrimeRegisteredDate']}",
        "status": "ARREST RECORDED" if has_arrest_record else "NO ARREST RECORD",
        "contactInfo": {
            "aadhaar": aadhaar,
            "phone": phone,
            "vehicle": vehicle,
            "address": f"Activity observed across {district_count} district(s); address not supplied in challenge schema"
        },
        "family": {
            "father": "Not supplied in challenge schema",
            "brother": "Not supplied in challenge schema",
            "associates": associates
        },
        "moDescription": mo_desc,
        "timeline": timeline,
        "movement": movement_coordinates
    }

def build_computed_crime_networks(group_name=None):
    group_specs = [
        {
            "id": "drill-burglary-gang",
            "name": "Drill & Enter Group",
            "members": [
                "Kiran Kumar alias Drill Kiran",
                "Ramesh Naik alias Night Ramesh",
                "Syed Ahmed alias Tool Syed",
            ],
            "case_ids": set(pattern_b_case_ids),
        },
        {
            "id": "indiranagar-snatchers",
            "name": "Indiranagar Chain Snatching Group",
            "members": [
                "Raju alias Splendor Raju",
                "Manoj Kumar",
                "Shiva alias Bike Shiva",
            ],
            "case_ids": set(pattern_a_case_ids),
        },
    ]

    cyber_members = (
        df_accused[df_accused['CaseMasterID'].isin(pattern_c_case_ids)]['AccusedName']
        .value_counts().head(5).index.tolist()
    )
    group_specs.append({
        "id": "cyber-fraud-ring",
        "name": "Seasonal Cyber Fraud Cluster",
        "members": cyber_members,
        "case_ids": set(pattern_c_case_ids),
    })

    arrested_ids = set(df_arrest['AccusedMasterID'].dropna().astype(int).tolist())
    groups = []
    for spec in group_specs:
        member_rows = df_accused[df_accused['AccusedName'].isin(spec['members'])]
        related_case_ids = set(spec['case_ids']) or set(member_rows['CaseMasterID'].tolist())
        related_cases = df_case[df_case['CaseMasterID'].isin(related_case_ids)]
        arrested_members = 0
        for member in spec['members']:
            member_ids = set(
                df_accused[df_accused['AccusedName'] == member]['AccusedMasterID'].astype(int).tolist()
            )
            if member_ids.intersection(arrested_ids):
                arrested_members += 1
        districts = [get_district_name(value) for value in related_cases['_DistrictID'].unique()]
        groups.append({
            "id": spec['id'],
            "name": spec['name'],
            "size": len(spec['members']),
            "cases": len(related_case_ids),
            "districts": ", ".join(districts[:4]),
            "status": f"{arrested_members} with arrest records · {len(spec['members']) - arrested_members} without",
        })

    selected = next(
        (spec for spec in group_specs if group_name in (spec['id'], spec['name'])),
        group_specs[0],
    )
    members = selected['members']
    member_rows = df_accused[df_accused['AccusedName'].isin(members)]
    selected_case_ids = set(selected['case_ids']) or set(member_rows['CaseMasterID'].tolist())
    selected_cases = df_case[df_case['CaseMasterID'].isin(selected_case_ids)]
    nodes = []
    edges = []

    for member in members:
        member_case_ids = set(
            member_rows[member_rows['AccusedName'] == member]['CaseMasterID'].tolist()
        ).intersection(selected_case_ids)
        nodes.append({
            "id": member,
            "label": f"{member}\n({len(member_case_ids)} cases)",
            "group": "suspect",
            "size": min(40, 14 + len(member_case_ids)),
            "color": "#F85149" if len(member_case_ids) >= 10 else "#D29922",
            "title": f"Computed from {len(member_case_ids)} linked FIR records",
        })

    for index, source in enumerate(members):
        for target in members[index + 1:]:
            if G.has_edge(source, target):
                weight = int(G[source][target]['weight'])
                edges.append({
                    "from": source,
                    "to": target,
                    "label": f"{weight} shared case{'s' if weight != 1 else ''}",
                    "color": "#F85149",
                    "width": min(6, 1 + weight / 3),
                })

    district_counts = selected_cases['_DistrictID'].value_counts().head(4)
    for district_id, count in district_counts.items():
        district_name = get_district_name(district_id)
        district_node = f"district-{int(district_id)}"
        nodes.append({
            "id": district_node,
            "label": f"{district_name}\n({int(count)} cases)",
            "group": "district",
            "size": min(25, 10 + int(count) / 5),
            "color": "#8B949E",
            "title": f"{int(count)} linked cases in {district_name}",
        })
        for member in members:
            member_case_ids = set(
                member_rows[member_rows['AccusedName'] == member]['CaseMasterID'].tolist()
            ).intersection(selected_case_ids)
            district_member_count = len(
                df_case[
                    df_case['CaseMasterID'].isin(member_case_ids)
                    & (df_case['_DistrictID'] == district_id)
                ]
            )
            if district_member_count:
                edges.append({
                    "from": member,
                    "to": district_node,
                    "label": f"{district_member_count} FIRs",
                    "color": "#8B949E",
                    "width": 1,
                })

    for field, icon, label in [('phone', '📱', 'phone'), ('vehicle', '🏍️', 'vehicle')]:
        for value in selected_cases[field].dropna().unique()[:2]:
            asset_id = f"{field}-{value}"
            asset_cases = set(selected_cases[selected_cases[field] == value]['CaseMasterID'].tolist())
            nodes.append({
                "id": asset_id,
                "label": f"{icon} {value}\n({len(asset_cases)} cases)",
                "group": "asset",
                "size": 18,
                "color": "#58A6FF",
                "title": f"Shared {label} found in {len(asset_cases)} case records",
            })
            for member in members:
                member_case_ids = set(
                    member_rows[member_rows['AccusedName'] == member]['CaseMasterID'].tolist()
                ).intersection(selected_case_ids)
                overlap = len(member_case_ids.intersection(asset_cases))
                if overlap:
                    edges.append({
                        "from": member,
                        "to": asset_id,
                        "label": f"{overlap} linked FIRs",
                        "color": "#388BFD",
                        "width": 2,
                    })

    explanation = (
        f"Computed from {len(selected_case_ids)} FIRs: {len(members)} people, "
        f"{len(edges)} evidenced relationships, and {len(district_counts)} principal districts. "
        "Every edge is backed by shared case, district, phone, or vehicle records."
    )
    return {
        "groups": groups,
        "selectedGroup": {
            "explanation": explanation,
            "nodes": nodes,
            "edges": edges,
            "evidence": {
                "caseCount": len(selected_case_ids),
                "relationshipCount": len(edges),
                "source": "Accused, CaseMaster, ArrestSurrender and enriched identifiers",
            },
        },
    }


@app.get("/api/networks")
def get_crime_networks(groupName: str = None):
    return build_computed_crime_networks(groupName)

    # Legacy prepared graph retained below for reference during migration.
    groups = [
        {
            "id": "drill-burglary-gang",
            "name": "Drill & Enter Group",
            "size": 3,
            "cases": 60,
            "districts": "Bangalore Urban, Mysuru, Belagavi",
            "status": "2 in custody · 1 AT LARGE"
        },
        {
            "id": "indiranagar-snatchers",
            "name": "Indiranagar Chain Snatching Group",
            "size": 3,
            "cases": 250,
            "districts": "Bangalore Urban",
            "status": "All 3 identities unknown — suspects at large"
        },
        {
            "id": "cyber-fraud-ring",
            "name": "Online Banking Fraud Ring",
            "size": 5,
            "cases": 150,
            "districts": "Urban Karnataka",
            "status": "3 in custody · 2 at large"
        }
    ]
    
    selected_name = groupName or "Drill & Enter Group"
    
    nodes = []
    edges = []
    explanation = ""
    
    if selected_name == "Drill & Enter Group" or selected_name == "drill-burglary-gang":
        explanation = "3 suspects are linked to 60 burglaries across Bangalore, Mysuru, and Belagavi. Text analysis matches their locks-drilling Modus Operandi. They shared a phone and a getaway vehicle."
        suspects = [
            {"id": "Kiran Kumar", "label": "Kiran Kumar\n(At Large)", "group": "suspect", "size": 30, "color": "#F85149", "title": "Kiran Kumar alias Drill Kiran (AT LARGE)"},
            {"id": "Ramesh Naik", "label": "Ramesh Naik", "group": "suspect", "size": 25, "color": "#D29922", "title": "Ramesh Naik (In Custody)"},
            {"id": "Syed Ahmed", "label": "Syed Ahmed", "group": "suspect", "size": 25, "color": "#D29922", "title": "Syed Ahmed (In Custody)"}
        ]
        nodes.extend(suspects)
        
        assets = [
            {"id": "phone-98450", "label": "📱 Shared Phone\n98450-12345", "group": "asset", "size": 18, "color": "#58A6FF", "title": "Used in 60 burglaries"},
            {"id": "bike-ka05", "label": "🏍️ Shared Vehicle\nKA-05 MX 1234", "group": "asset", "size": 18, "color": "#58A6FF", "title": "Suspect Black Pulsar KA-05 MX 1234"}
        ]
        nodes.extend(assets)
        
        districts = [
            {"id": "blr-hub", "label": "Bangalore\n(20 cases)", "group": "district", "size": 12, "color": "#8B949E", "title": "Bangalore Urban Burglaries"},
            {"id": "mys-hub", "label": "Mysuru\n(20 cases)", "group": "district", "size": 12, "color": "#8B949E", "title": "Mysuru Burglaries"},
            {"id": "bel-hub", "label": "Belagavi\n(20 cases)", "group": "district", "size": 12, "color": "#8B949E", "title": "Belagavi Burglaries"}
        ]
        nodes.extend(districts)
        
        edges.append({"from": "Kiran Kumar", "to": "Ramesh Naik", "label": "Together in 14 cases", "color": "#F85149", "width": 4})
        edges.append({"from": "Kiran Kumar", "to": "Syed Ahmed", "label": "Together in 14 cases", "color": "#F85149", "width": 4})
        edges.append({"from": "Ramesh Naik", "to": "Syed Ahmed", "label": "Together in 14 cases", "color": "#F85149", "width": 4})
        
        for s in ["Kiran Kumar", "Ramesh Naik", "Syed Ahmed"]:
            edges.append({"from": s, "to": "phone-98450", "label": "Shared Phone", "color": "#388BFD", "width": 2})
            edges.append({"from": s, "to": "bike-ka05", "label": "Shared Vehicle", "color": "#388BFD", "width": 2})
            
        edges.append({"from": "phone-98450", "to": "blr-hub", "label": "Pattern B", "color": "#8B949E", "width": 1})
        edges.append({"from": "phone-98450", "to": "mys-hub", "label": "Pattern B", "color": "#8B949E", "width": 1})
        edges.append({"from": "phone-98450", "to": "bel-hub", "label": "Pattern B", "color": "#8B949E", "width": 1})
        
    elif selected_name == "Indiranagar Chain Snatching Group" or selected_name == "indiranagar-snatchers":
        explanation = "3 suspects operated around Indiranagar Metro Station snatching gold ornaments from lone women walkers in the evening (6 PM - 9 PM). Gateway vehicle was a black Bajaj Pulsar."
        sus_list = ["Raju alias Splendor Raju", "Manoj Kumar", "Shiva alias Bike Shiva"]
        for s in sus_list:
            nodes.append({"id": s, "label": s, "group": "suspect", "size": 25, "color": "#F85149", "title": s})
            
        nodes.append({"id": "bike-pulsar", "label": "🏍️ suspect Pulsar\nKA-05 MX 1234", "group": "asset", "size": 18, "color": "#58A6FF", "title": "Getaway motorcycle"})
        nodes.append({"id": "ind-cluster", "label": "Indiranagar Metro\n(250 cases)", "group": "district", "size": 22, "color": "#8B949E"})
        
        edges.append({"from": "Raju alias Splendor Raju", "to": "Manoj Kumar", "label": "Co-accused", "color": "#F85149", "width": 3})
        edges.append({"from": "Manoj Kumar", "to": "Shiva alias Bike Shiva", "label": "Co-accused", "color": "#F85149", "width": 3})
        for s in sus_list:
            edges.append({"from": s, "to": "bike-pulsar", "label": "Rode", "color": "#388BFD", "width": 2})
        edges.append({"from": "bike-pulsar", "to": "ind-cluster", "label": "Hotspot area", "color": "#8B949E", "width": 2})
        
    else: # Cyber Fraud Ring
        explanation = "5 fraud callers operating an online banking fraud ring during Diwali, targeting bank credentials of retired individuals."
        sus_list = ["Caller 1", "Caller 2", "Caller 3", "Caller 4", "Caller 5"]
        for s in sus_list:
            nodes.append({"id": s, "label": s, "group": "suspect", "size": 20, "color": "#D29922", "title": s})
        nodes.append({"id": "bescom-scam", "label": "💻 Phishing Gateway\n(Diwali scam)", "group": "asset", "size": 18, "color": "#58A6FF"})
        nodes.append({"id": "target-coms", "label": "📞 Target Victims\n(Retired/Elderly)", "group": "district", "size": 18, "color": "#8B949E"})
        
        for s in sus_list:
            edges.append({"from": s, "to": "bescom-scam", "label": "Linked", "color": "#388BFD", "width": 2})
        edges.append({"from": "bescom-scam", "to": "target-coms", "label": "Victims targeted", "color": "#8B949E", "width": 2})
        
    return {
        "groups": groups,
        "selectedGroup": {
            "explanation": explanation,
            "nodes": nodes,
            "edges": edges
        }
    }

@app.get("/api/alerts")
def get_situations():
    alerts = []
    for index, anomaly in enumerate(compute_monthly_anomalies(limit=5)):
        severity = "urgent" if anomaly['zScore'] >= 3 else "watch"
        increase_percent = round((anomaly['ratio'] - 1) * 100)
        evidence = [
            {
                "label": "Current complete month",
                "value": f"{anomaly['count']} {anomaly['crimeType']} cases",
            },
            {
                "label": "Previous 12-month baseline",
                "value": f"{anomaly['baselineMean']} cases/month",
            },
            {
                "label": "Statistical deviation",
                "value": f"{anomaly['zScore']} standard deviations above baseline",
            },
        ]
        alerts.append({
            "id": f"computed-spike-{index}",
            "severity": severity,
            "title": f"{anomaly['crimeType']} spike — {anomaly['district']}",
            "timeText": f"Computed from {anomaly['period']} records",
            "description": (
                f"{anomaly['count']} cases, {increase_percent}% above the preceding "
                f"12-month baseline of {anomaly['baselineMean']}."
            ),
            "whatHappened": (
                f"Drishti compared {anomaly['district']} {anomaly['crimeType']} volume "
                f"for {anomaly['period']} against the previous 12 complete months. "
                f"The observed volume is {anomaly['ratio']}× the baseline."
            ),
            "cases": anomaly['cases'],
            "evidence": evidence,
            "recommendedAction": (
                f"Suggested response: Validate the linked FIRs, notify the {anomaly['district']} "
                "district analyst, and review station-level deployment before operational action."
            ),
        })

    if not alerts:
        validations = [
            (
                "Cross-district property-crime review",
                df_case[df_case['CrimeMajorHeadID'] == 2],
                "Validate recurring property-crime narratives and shared identifiers across districts.",
            ),
            (
                "Pending-case supervision review",
                df_case[~df_case['CaseStatusID'].isin([2, 3])],
                "Review older pending FIRs for missing arrest, chargesheet, or evidence links.",
            ),
            (
                "Data-quality exception review",
                df_case[
                    df_case['BriefFacts'].fillna("").str.strip().eq("")
                    | df_case['latitude'].isna()
                    | df_case['longitude'].isna()
                ],
                "Resolve missing narrative or location fields before analytical use.",
            ),
        ]
        for index, (title, cases, recommendation) in enumerate(validations):
            if cases.empty:
                continue
            sample = cases.sort_values('CrimeRegisteredDate', ascending=False).head(3)
            alerts.append({
                "id": f"validation-watch-{index}",
                "severity": "watch",
                "title": title,
                "timeText": "Demo validation watch · not an operational alert",
                "description": f"{len(cases):,} records match this review queue.",
                "whatHappened": (
                    "No statistically significant current spike was detected. "
                    "This queue is provided for workflow testing and supervisory validation."
                ),
                "cases": [{
                    "id": int(row['CaseMasterID']),
                    "crimeNo": str(row['CrimeNo']),
                    "date": str(row['CrimeRegisteredDate']),
                    "facts": str(row['BriefFacts']),
                    "lat": float(row['latitude']),
                    "lng": float(row['longitude']),
                } for _, row in sample.iterrows()],
                "evidence": [
                    {"label": "Queue size", "value": f"{len(cases):,} matching FIR records"},
                    {"label": "Classification", "value": "Demonstration/validation watch"},
                ],
                "recommendedAction": f"Suggested supervisory test: {recommendation}",
            })

    return {
        "alerts": alerts,
        "method": "12-month district/category z-score baseline; validation watches are labelled",
    }

@app.get("/api/districts/{district_id}")
def get_district_details(district_id: int):
    dist_cases = df_case[df_case['_DistrictID'] == district_id]
    if len(dist_cases) == 0:
        raise HTTPException(status_code=404, detail="District not found")
        
    dist_name = get_district_name(district_id)
    
    # Group by stations (Units)
    station_ids = dist_cases['PoliceStationID'].unique()
    station_rows = []
    
    for sid in station_ids:
        sname = get_unit_name(sid)
        s_cases = dist_cases[dist_cases['PoliceStationID'] == sid]
        c_count = len(s_cases)
        
        resolved = len(s_cases[s_cases['CaseStatusID'].isin([2, 3])])
        pending = c_count - resolved
        res_rate = round(resolved / c_count * 100) if c_count > 0 else 0
        
        status_txt = "Normal"
        if res_rate < 55:
            status_txt = "⚠️ Needs attention"
        elif res_rate > 70:
            status_txt = "Good ✓"
            
        station_rows.append({
            "stationName": sname,
            "cases": c_count,
            "resolved": f"{resolved} ({res_rate}%)",
            "pending": pending,
            "status": status_txt
        })
        
    district_accused_ids = df_accused[df_accused['CaseMasterID'].isin(dist_cases['CaseMasterID'])]['AccusedName'].value_counts()
    top_offenders = []
    for name, count in district_accused_ids.head(5).items():
        person_ids = set(
            df_accused[
                (df_accused['AccusedName'] == name)
                & (df_accused['CaseMasterID'].isin(dist_cases['CaseMasterID']))
            ]['AccusedMasterID'].astype(int).tolist()
        )
        has_arrest_record = df_arrest['AccusedMasterID'].isin(person_ids).any()
        top_offenders.append({
            "name": name,
            "cases": int(count),
            "status": "ARREST RECORDED" if has_arrest_record else "NO ARREST RECORD"
        })

    latest_period, previous_period = get_complete_analysis_periods()
    district_periods = pd.to_datetime(dist_cases['CrimeRegisteredDate']).dt.to_period('M')
    latest_cases = dist_cases[district_periods == latest_period]
    previous_cases = dist_cases[district_periods == previous_period]
    latest_count = len(latest_cases)
    previous_count = len(previous_cases)
    delta_percent = round((latest_count - previous_count) / previous_count * 100) if previous_count else 0
    delta_prefix = "+" if delta_percent > 0 else ""
    top_crime = (
        str(latest_cases['_SubheadName'].value_counts().index[0])
        if not latest_cases.empty
        else "No recorded cases"
    )
        
    return {
        "districtName": dist_name,
        "casesCount": len(dist_cases),
        "analysisPeriod": str(latest_period),
        "periodCasesCount": latest_count,
        "percentageIncrease": f"{delta_prefix}{delta_percent}% vs {previous_period}",
        "topCrimeType": top_crime,
        "stations": station_rows,
        "topOffenders": top_offenders
    }


def filtered_cases(district_id=None, crime_head_id=None, date_from=None, date_to=None):
    """Return a defensive, date-normalized slice used by interactive laboratories."""
    working = df_case.copy()
    working['_registered'] = pd.to_datetime(working['CrimeRegisteredDate'], errors='coerce')
    if district_id is not None:
        working = working[working['_DistrictID'] == district_id]
    if crime_head_id is not None:
        working = working[working['CrimeMajorHeadID'] == crime_head_id]
    if date_from:
        working = working[working['_registered'] >= pd.Timestamp(date_from)]
    if date_to:
        working = working[working['_registered'] <= pd.Timestamp(date_to)]
    return working.dropna(subset=['_registered'])


@app.get("/api/patterns/discover")
def discover_patterns(
    districtId: Optional[int] = Query(default=None),
    crimeHeadId: Optional[int] = Query(default=None),
    dateFrom: Optional[str] = Query(default=None),
    dateTo: Optional[str] = Query(default=None),
    clusterCount: int = Query(default=4, ge=2, le=8),
):
    """Discover narrative clusters at request time; no prepared pattern labels are used."""
    try:
        working = filtered_cases(districtId, crimeHeadId, dateFrom, dateTo)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Dates must use YYYY-MM-DD")
    working = working[working['BriefFacts'].str.strip().str.len() >= 20]
    if len(working) < clusterCount * 3:
        raise HTTPException(status_code=400, detail="Select a broader slice with at least three cases per pattern")

    # Recent samples keep the interaction responsive while retaining an auditable case list.
    sample = working.sort_values('_registered', ascending=False).head(5000).copy()
    matrix = vectorizer.transform(sample['BriefFacts'])
    model = MiniBatchKMeans(n_clusters=clusterCount, random_state=42, batch_size=512, n_init=5)
    labels = model.fit_predict(matrix)
    terms = np.asarray(vectorizer.get_feature_names_out())
    clusters = []
    for cluster_id in range(clusterCount):
        positions = np.where(labels == cluster_id)[0]
        members = sample.iloc[positions]
        center = model.cluster_centers_[cluster_id]
        top_terms = [str(term) for term in terms[center.argsort()[-8:][::-1]]]
        similarities = cosine_similarity(matrix[positions], center.reshape(1, -1)).ravel()
        representative_positions = positions[np.argsort(similarities)[-3:][::-1]]
        representatives = []
        for pos in representative_positions:
            row = sample.iloc[pos]
            representatives.append({
                "caseId": int(row['CaseMasterID']), "crimeNo": str(row['CrimeNo']),
                "date": row['_registered'].strftime('%Y-%m-%d'),
                "district": get_district_name(row['_DistrictID']),
                "crimeType": str(row['_SubheadName']), "facts": str(row['BriefFacts']),
                "lat": float(row['latitude']), "lng": float(row['longitude']),
            })
        clusters.append({
            "id": cluster_id + 1, "size": int(len(members)),
            "share": round(len(members) / len(sample) * 100, 1),
            "topTerms": top_terms,
            "cohesion": round(float(similarities.mean()) * 100, 1),
            "topCrimeTypes": [str(v) for v in members['_SubheadName'].value_counts().head(3).index],
            "topDistricts": [get_district_name(v) for v in members['_DistrictID'].value_counts().head(3).index],
            "dateSpan": {"from": members['_registered'].min().strftime('%Y-%m-%d'), "to": members['_registered'].max().strftime('%Y-%m-%d')},
            "uniqueNarrativeRate": round(members['BriefFacts'].nunique() / len(members) * 100, 1),
            "qualityFlag": "Templated narrative — treat as a data-quality cluster" if members['BriefFacts'].nunique() / len(members) < 0.05 else None,
            "representativeCases": representatives,
        })
    clusters.sort(key=lambda item: item['size'], reverse=True)
    return {
        "caseCount": int(len(working)), "sampledCaseCount": int(len(sample)), "clusters": clusters,
        "method": "TF-IDF narrative vectors grouped with MiniBatch K-Means; cohesion is mean case-to-centroid cosine similarity.",
        "caveat": "Clusters are investigative leads, not proof of common offenders or causation. Review the linked FIRs.",
    }


@app.get("/api/lifecycle")
def case_lifecycle(districtId: Optional[int] = Query(default=None)):
    cases = filtered_cases(district_id=districtId)
    if cases.empty:
        raise HTTPException(status_code=404, detail="No cases found")
    ids = set(cases['CaseMasterID'].astype(int))
    arrests = df_arrest[df_arrest['CaseMasterID'].isin(ids)].copy()
    sheets = df_chargesheet[df_chargesheet['CaseMasterID'].isin(ids)].copy()
    arrests['_date'] = pd.to_datetime(arrests['ArrestSurrenderDate'], errors='coerce')
    sheets['_date'] = pd.to_datetime(sheets['csdate'], errors='coerce')
    first_arrest = arrests.groupby('CaseMasterID')['_date'].min()
    first_sheet = sheets.groupby('CaseMasterID')['_date'].min()
    base = cases.set_index('CaseMasterID')[['_registered', 'PoliceStationID', 'CaseStatusID', 'CrimeNo']].copy()
    base['arrest'] = first_arrest
    base['sheet'] = first_sheet
    base['arrestDays'] = (base['arrest'] - base['_registered']).dt.days
    base['sheetDays'] = (base['sheet'] - base['_registered']).dt.days
    analysis_date = cases['_registered'].max()
    base['ageDays'] = (analysis_date - base['_registered']).dt.days
    chronology = base[(base['arrestDays'] < 0) | (base['sheetDays'] < 0)]
    pending_90 = base[(~base['CaseStatusID'].isin([2, 3])) & (base['ageDays'] > 90)]

    station_rows = []
    for station_id, group in base.groupby('PoliceStationID'):
        pending = int((~group['CaseStatusID'].isin([2, 3])).sum())
        station_rows.append({
            "station": get_unit_name(station_id), "cases": int(len(group)), "pending": pending,
            "pendingRate": round(pending / len(group) * 100, 1),
            "medianChargeDays": clean_val(group['sheetDays'].dropna().median()),
        })
    station_rows.sort(key=lambda row: (row['pendingRate'], row['pending']), reverse=True)
    arrested_ids, sheet_ids = set(first_arrest.index), set(first_sheet.index)
    valid_arrest_days = base.loc[base['arrestDays'] >= 0, 'arrestDays']
    valid_sheet_days = base.loc[base['sheetDays'] >= 0, 'sheetDays']
    return {
        "district": get_district_name(districtId) if districtId else "Karnataka",
        "analysisDate": analysis_date.strftime('%Y-%m-%d'),
        "funnel": [
            {"stage": "FIR registered", "count": int(len(base))},
            {"stage": "Arrest recorded", "count": int(len(arrested_ids))},
            {"stage": "Chargesheet filed", "count": int(len(sheet_ids))},
            {"stage": "Resolved/closed", "count": int(base['CaseStatusID'].isin([2, 3]).sum())},
        ],
        "timings": {
            "medianFIRToArrestDays": clean_val(valid_arrest_days.median()),
            "averageFIRToArrestDays": round(float(valid_arrest_days.mean()), 1) if len(valid_arrest_days) else None,
            "medianFIRToChargesheetDays": clean_val(valid_sheet_days.median()),
        },
        "exceptions": {
            "arrestWithoutChargesheet": int(len(arrested_ids - sheet_ids)),
            "chargesheetWithoutArrest": int(len(sheet_ids - arrested_ids)),
            "pendingOver90Days": int(len(pending_90)),
            "chronologyConflicts": int(len(chronology)),
        },
        "bottlenecks": station_rows[:10],
        "method": "CaseMaster is linked to the earliest recorded arrest and chargesheet by CaseMasterID.",
    }


@app.get("/api/patrol/plan")
def patrol_plan(
    districtId: int = Query(default=1),
    availableUnits: int = Query(default=8, ge=1, le=50),
    heinousWeight: float = Query(default=1.5, ge=0, le=5),
    recencyWeight: float = Query(default=0.75, ge=0, le=5),
    shiftStart: int = Query(default=0, ge=0, le=23),
    shiftEnd: int = Query(default=23, ge=0, le=23),
):
    cases = filtered_cases(district_id=districtId)
    if cases.empty:
        raise HTTPException(status_code=404, detail="No cases found")
    latest = cases['_registered'].max()
    recent = cases[cases['_registered'] >= latest - pd.Timedelta(days=89)].copy()
    recent = recent.dropna(subset=['latitude', 'longitude'])
    recent['_latCell'] = recent['latitude'].round(2)
    recent['_lngCell'] = recent['longitude'].round(2)
    recent['_hour'] = pd.to_datetime(recent['IncidentFromDate'], errors='coerce').dt.hour
    if shiftStart != shiftEnd:
        if shiftStart < shiftEnd:
            recent = recent[(recent['_hour'] >= shiftStart) & (recent['_hour'] <= shiftEnd)]
        else:
            recent = recent[(recent['_hour'] >= shiftStart) | (recent['_hour'] <= shiftEnd)]
    zones = []
    for (lat, lng), group in recent.groupby(['_latCell', '_lngCell']):
        heinous = int((group['GravityOffenceID'] == 1).sum())
        newest_30 = int((group['_registered'] >= latest - pd.Timedelta(days=29)).sum())
        score = len(group) + heinous * heinousWeight + newest_30 * recencyWeight
        peak_hour = int(group['_hour'].dropna().mode().iloc[0]) if not group['_hour'].dropna().empty else None
        zones.append({
            "lat": float(group['latitude'].mean()), "lng": float(group['longitude'].mean()),
            "cases": int(len(group)), "heinousCases": heinous, "recent30Days": newest_30,
            "riskScore": round(float(score), 2),
            "baselineRiskScore": round(float(len(group) + heinous * 1.5 + newest_30 * 0.75), 2),
            "topCrime": str(group['_SubheadName'].value_counts().index[0]),
            "peakWindow": f"{peak_hour:02d}:00–{(peak_hour + 3) % 24:02d}:00" if peak_hour is not None else "Time unavailable",
        })
    zones.sort(key=lambda zone: zone['riskScore'], reverse=True)
    zones = zones[:12]
    if not zones:
        raise HTTPException(status_code=404, detail="No geocoded recent cases found")
    total_score = sum(zone['riskScore'] for zone in zones)
    raw = [availableUnits * zone['riskScore'] / total_score for zone in zones]
    allocations = [int(math.floor(value)) for value in raw]
    for index in sorted(range(len(raw)), key=lambda i: raw[i] - allocations[i], reverse=True)[:availableUnits - sum(allocations)]:
        allocations[index] += 1
    for index, zone in enumerate(zones):
        zone['zone'] = f"Z{index + 1}"
        zone['allocatedUnits'] = allocations[index]
        zone['rationale'] = f"{zone['cases']} incidents; {zone['heinousCases']} heinous; {zone['recent30Days']} in the latest 30 days"
    served_score = sum(zone['riskScore'] for zone in zones if zone['allocatedUnits'] > 0)
    baseline_total = sum(zone['baselineRiskScore'] for zone in zones)
    baseline_raw = [availableUnits * zone['baselineRiskScore'] / baseline_total for zone in zones]
    baseline_allocations = [int(math.floor(value)) for value in baseline_raw]
    for index in sorted(range(len(baseline_raw)), key=lambda i: baseline_raw[i] - baseline_allocations[i], reverse=True)[:availableUnits - sum(baseline_allocations)]:
        baseline_allocations[index] += 1
    baseline_served = sum(zone['baselineRiskScore'] for index, zone in enumerate(zones) if baseline_allocations[index] > 0)
    baseline_coverage = round(baseline_served / baseline_total * 100, 1)
    scenario_coverage = round(served_score / total_score * 100, 1)
    return {
        "district": get_district_name(districtId), "availableUnits": availableUnits,
        "analysisWindow": {"from": (latest - pd.Timedelta(days=89)).strftime('%Y-%m-%d'), "to": latest.strftime('%Y-%m-%d')},
        "coverageIndex": scenario_coverage, "baselineCoverageIndex": baseline_coverage,
        "coverageDelta": round(scenario_coverage - baseline_coverage, 1), "zones": zones,
        "scenario": {"heinousWeight": heinousWeight, "recencyWeight": recencyWeight, "shiftStart": shiftStart, "shiftEnd": shiftEnd},
        "method": f"90-day grid demand score = incidents + {heinousWeight}× heinous incidents + {recencyWeight}× incidents in the latest 30 days, filtered to the selected shift.",
        "caveat": "Planning aid only. Coverage index measures weighted historical demand represented by staffed zones; it does not predict or promise crime reduction. Supervisor approval is required.",
    }


@app.get("/api/data-quality")
def data_quality_command_centre(districtId: Optional[int] = Query(default=None)):
    cases = filtered_cases(district_id=districtId)
    cases['BriefFacts'] = cases['BriefFacts'].fillna("").astype(str)
    cases['latitude'] = pd.to_numeric(cases['latitude'], errors='coerce')
    cases['longitude'] = pd.to_numeric(cases['longitude'], errors='coerce')
    cases['PoliceStationID'] = pd.to_numeric(cases['PoliceStationID'], errors='coerce')
    ids = set(cases['CaseMasterID'].astype(int))
    arrests = df_arrest[df_arrest['CaseMasterID'].isin(ids)].copy()
    sheets = df_chargesheet[df_chargesheet['CaseMasterID'].isin(ids)].copy()
    registered = cases.set_index('CaseMasterID')['_registered']
    arrest_dates = pd.to_datetime(arrests['ArrestSurrenderDate'], errors='coerce')
    sheet_dates = pd.to_datetime(sheets['csdate'], errors='coerce')
    arrest_registered = pd.to_datetime(arrests['CaseMasterID'].map(registered), errors='coerce')
    sheet_registered = pd.to_datetime(sheets['CaseMasterID'].map(registered), errors='coerce')
    narrative_counts = cases['BriefFacts'].str.strip().value_counts()
    duplicate_narratives = set(narrative_counts[narrative_counts > 1].index) - {""}
    invalid_coordinates = (
        cases['latitude'].isna() | cases['longitude'].isna()
        | ~cases['latitude'].between(11.5, 18.8) | ~cases['longitude'].between(74.0, 78.8)
    )
    checks = [
        {"name": "Missing narrative", "count": int(cases['BriefFacts'].str.strip().eq('').sum()), "severity": "high"},
        {"name": "Duplicated narrative text", "count": int(cases['BriefFacts'].isin(duplicate_narratives).sum()), "severity": "medium"},
        {"name": "Invalid or missing coordinates", "count": int(invalid_coordinates.sum()), "severity": "high"},
        {"name": "Missing incident timestamp", "count": int(pd.to_datetime(cases['IncidentFromDate'], errors='coerce').isna().sum()), "severity": "medium"},
        {"name": "Arrest before FIR", "count": int((arrest_dates.to_numpy() < arrest_registered.to_numpy()).sum()), "severity": "critical"},
        {"name": "Chargesheet before FIR", "count": int((sheet_dates.to_numpy() < sheet_registered.to_numpy()).sum()), "severity": "critical"},
        {"name": "Unknown police station", "count": int((~cases['PoliceStationID'].isin(df_unit['UnitID'])).sum()), "severity": "high"},
    ]
    total_cells = len(cases) * 6
    missing_cells = int(cases[['BriefFacts', 'IncidentFromDate', 'latitude', 'longitude', 'PoliceStationID', '_DistrictID']].isna().sum().sum())
    quality_score = max(0, round(100 - (sum(item['count'] for item in checks) / max(total_cells, 1) * 100), 1))
    district_rows = []
    for district_id, group in cases.groupby('_DistrictID'):
        bad_coords = int((group['latitude'].isna() | group['longitude'].isna() | ~group['latitude'].between(11.5, 18.8) | ~group['longitude'].between(74.0, 78.8)).sum())
        duplicate_count = int(group['BriefFacts'].isin(duplicate_narratives).sum())
        issue_count = bad_coords + duplicate_count + int(group['BriefFacts'].str.strip().eq('').sum())
        district_rows.append({"district": get_district_name(district_id), "records": int(len(group)), "issues": issue_count, "issueRate": round(issue_count / len(group) * 100, 1)})
    district_rows.sort(key=lambda row: row['issueRate'], reverse=True)
    return {
        "scope": get_district_name(districtId) if districtId else "Karnataka", "records": int(len(cases)),
        "qualityScore": quality_score, "fieldCompleteness": round((total_cells - missing_cells) / max(total_cells, 1) * 100, 1),
        "checks": checks, "districts": district_rows[:12],
        "recommendations": [
            "Replace repeated placeholder narratives with source FIR summaries before model training.",
            "Reject or quarantine chronology conflicts during ingestion.",
            "Validate coordinates against Karnataka boundaries and police-station jurisdiction.",
        ],
    }


class HypothesisBoardRequest(BaseModel):
    title: str
    hypothesis: str
    caseIds: list[int] = []
    evidence: list[str] = []
    gaps: list[str] = []
    status: str = "open"


@app.get("/api/hypotheses")
def get_hypothesis_boards():
    if data_source_status["active"] == "catalyst":
        try:
            rows = catalyst_store.fetch_workflow_rows("hypotheses")
            return {"boards": [{
                "id": int(row.get("BoardID", 0)), "title": row.get("Title"),
                "hypothesis": row.get("Hypothesis"), "caseIds": row.get("CaseIDs", []),
                "evidence": row.get("Evidence", []), "gaps": row.get("Gaps", []),
                "status": row.get("Status", "open"), "cases": row.get("Cases", []),
                "createdAt": row.get("CreatedAt"),
            } for row in rows]}
        except Exception:
            pass
    return {"boards": hypothesis_boards}


@app.post("/api/hypotheses")
def save_hypothesis_board(request: HypothesisBoardRequest):
    valid_cases = df_case[df_case['CaseMasterID'].isin(request.caseIds)]
    board = {
        "id": len(hypothesis_boards) + 1, "title": request.title.strip(),
        "hypothesis": request.hypothesis.strip(), "caseIds": [int(value) for value in valid_cases['CaseMasterID']],
        "evidence": request.evidence, "gaps": request.gaps, "status": request.status,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "cases": [{"caseId": int(row['CaseMasterID']), "crimeNo": str(row['CrimeNo']), "crimeType": str(row['_SubheadName']), "district": get_district_name(row['_DistrictID'])} for _, row in valid_cases.iterrows()],
    }
    hypothesis_boards.append(board)
    if data_source_status["active"] == "catalyst":
        try:
            catalyst_store.insert_workflow_row("hypotheses", {
                "BoardID": board["id"], "Title": board["title"],
                "Hypothesis": board["hypothesis"], "CaseIDs": board["caseIds"],
                "Evidence": board["evidence"], "Gaps": board["gaps"],
                "Status": board["status"], "Cases": board["cases"],
                "CreatedAt": board["createdAt"],
            })
        except Exception as exc:
            board["persistenceWarning"] = str(exc)
    return board


@app.get("/api/forecast/backtest")
def forecast_backtest(
    districtId: int = Query(default=1),
    crimeHeadId: Optional[int] = Query(default=None),
    holdoutMonths: int = Query(default=6, ge=3, le=12),
):
    cases = filtered_cases(district_id=districtId, crime_head_id=crimeHeadId)
    cases['_month'] = cases['_registered'].dt.to_period('M')
    monthly = cases.groupby('_month').size().sort_index()
    full_index = pd.period_range(monthly.index.min(), monthly.index.max(), freq='M')
    monthly = monthly.reindex(full_index, fill_value=0)
    if len(monthly) < holdoutMonths + 12:
        raise HTTPException(status_code=400, detail="Not enough monthly history for this backtest")
    actual = monthly.iloc[-holdoutMonths:]
    predictions = []
    for period in actual.index:
        history = monthly[monthly.index < period].tail(6)
        predictions.append(float(history.mean()))
    actual_values = actual.astype(float).values
    predicted_values = np.asarray(predictions)
    mae = float(np.mean(np.abs(actual_values - predicted_values)))
    mape_mask = actual_values > 0
    mape = float(np.mean(np.abs((actual_values[mape_mask] - predicted_values[mape_mask]) / actual_values[mape_mask])) * 100) if mape_mask.any() else None
    baseline = np.repeat(float(monthly.iloc[-holdoutMonths-1]), holdoutMonths)
    baseline_mae = float(np.mean(np.abs(actual_values - baseline)))
    return {
        "district": get_district_name(districtId), "crimeCategory": "All categories" if crimeHeadId is None else str(df_crime_head.loc[df_crime_head['CrimeHeadID'] == crimeHeadId, 'CrimeGroupName'].iloc[0]),
        "model": "Six-month rolling mean", "holdoutMonths": holdoutMonths,
        "metrics": {"mae": round(mae, 1), "mape": round(mape, 1) if mape is not None else None, "naiveMAE": round(baseline_mae, 1), "improvementVsNaive": round((baseline_mae - mae) / baseline_mae * 100, 1) if baseline_mae else 0},
        "series": [{"month": str(period), "actual": int(actual.loc[period]), "predicted": round(predictions[index], 1)} for index, period in enumerate(actual.index)],
        "caveat": "This is retrospective validation on known historical months, not a guarantee of future crime volume.",
    }


def case_brief_pdf(case_id: int):
    reconstruction = build_incident_reconstruction(case_id)
    links = get_case_links(case_id)
    case = reconstruction['case']
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='DrishtiTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#173B63'), alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name='Section', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#173B63'), spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=8.5, leading=11, textColor=colors.HexColor('#34495E')))
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=15*mm, title=f"Drishti Case Brief {case['crimeNo']}")
    story = [Paragraph("DRISHTI EVIDENCE-BASED CASE BRIEF", styles['DrishtiTitle']), Paragraph(f"FIR {case['crimeNo']} | {case['crimeType']} | {case['district']}", styles['Heading3'])]
    summary_data = [["Incident", case.get('incidentTime') or '-'], ["Vehicle", case.get('vehicle') or 'Not recorded'], ["Phone", case.get('phone') or 'Not recorded'], ["Accused", ', '.join(case.get('accused') or []) or 'Not linked']]
    summary = Table(summary_data, colWidths=[38*mm, 120*mm])
    summary.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#EAF2F8')),('TEXTCOLOR',(0,0),(-1,-1),colors.HexColor('#1C2833')),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#AAB7B8')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8.5),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)]))
    story += [Spacer(1, 6), summary, Paragraph("Recorded narrative", styles['Section']), Paragraph(str(case.get('briefFacts') or 'No narrative recorded.'), styles['Small']), Paragraph("Incident timeline", styles['Section'])]
    timeline_rows = [["Time", "Event", "Evidence status"]] + [[Paragraph(str(event.get('timestamp','-')).replace('T', ' '), styles['Small']), Paragraph(str(event.get('label','-')), styles['Small']), Paragraph(str(event.get('confidence','-')), styles['Small'])] for event in reconstruction['events']]
    timeline = Table(timeline_rows, colWidths=[40*mm, 90*mm, 28*mm], repeatRows=1)
    timeline.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#173B63')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#AAB7B8')),('FONTSIZE',(0,0),(-1,-1),7.5),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),5)]))
    story += [timeline, Paragraph("Related FIR signals", styles['Section'])]
    link_rows = [["FIR", "Score", "Supporting signals"]]
    for related in links['relatedCases'][:8]:
        link_rows.append([Paragraph(str(related['crimeNo']), styles['Small']), str(related['connectionScore']), Paragraph(", ".join(item['type'] for item in related['evidence']) or "Narrative similarity", styles['Small'])])
    link_table = Table(link_rows, colWidths=[55*mm, 18*mm, 85*mm], repeatRows=1)
    link_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#173B63')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#AAB7B8')),('FONTSIZE',(0,0),(-1,-1),7.5),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),5)]))
    story += [link_table, Paragraph("Missing links and limitations", styles['Section'])]
    for missing in reconstruction['missingLinks']:
        story.append(Paragraph(f"- {missing['field']}: {missing['impact']} Next step: {missing['nextStep']}", styles['Small']))
    story += [Spacer(1, 10), Paragraph("Decision-support only. Inferences are labelled and require officer verification. This document does not establish guilt or authorize operational action.", styles['Small'])]
    doc.build(story)
    buffer.seek(0)
    return buffer


@app.get("/api/cases/{case_id}/brief.pdf")
def download_case_brief(case_id: int):
    buffer = case_brief_pdf(case_id)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="drishti-case-{case_id}.pdf"'})

# Serve Frontend static assets
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    print(f"Mounted frontend assets from: {FRONTEND_DIR}")
else:
    print(f"[WARN] Frontend directory not found at: {FRONTEND_DIR}. API server running stand-alone.")
