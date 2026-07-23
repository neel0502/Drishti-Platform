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
from sklearn.ensemble import IsolationForest, RandomForestRegressor, RandomForestClassifier
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
df_employee = None
df_court = None

# NLP & Network Variables
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = None
case_ids_list = []
G = nx.Graph()
link_prediction_model = None
link_prediction_features = []
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
    global df_district, df_unit, df_crime_head, df_crime_subhead, df_status, df_occupation, df_employee, df_court
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
    df_employee = frames["Employee"]
    df_court = frames["Court"]

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

def build_link_prediction_model():
    """Train a small supervised FIR-pair model from known relational links."""
    global link_prediction_model, link_prediction_features
    if tfidf_matrix is None or not case_ids_list:
        return
    by_id = df_case.set_index('CaseMasterID')
    positives = set()
    for column in ('phone', 'vehicle'):
        for _, group in df_case.dropna(subset=[column]).groupby(column):
            ids = group['CaseMasterID'].astype(int).tolist()[:12]
            for index, left in enumerate(ids):
                for right in ids[index + 1:]: positives.add(tuple(sorted((left, right))))
    for _, group in df_accused.groupby('AccusedName'):
        ids = group['CaseMasterID'].astype(int).unique().tolist()[:12]
        for index, left in enumerate(ids):
            for right in ids[index + 1:]: positives.add(tuple(sorted((left, right))))
    positives = list(positives)[:1000]
    rng = np.random.default_rng(42); ids = np.asarray(case_ids_list); negatives = []
    positive_set = set(positives)
    while len(negatives) < len(positives):
        pair = tuple(sorted(rng.choice(ids, size=2, replace=False).astype(int).tolist()))
        if pair not in positive_set: negatives.append(pair)
    index_map = {int(case_id): index for index, case_id in enumerate(case_ids_list)}
    def vector(pair):
        left, right = pair; a, b = by_id.loc[left], by_id.loc[right]
        sim = float(cosine_similarity(tfidf_matrix[index_map[left]], tfidf_matrix[index_map[right]])[0][0])
        dist = haversine_km(a['latitude'], a['longitude'], b['latitude'], b['longitude'])
        ah, bh = pd.to_datetime(a['IncidentFromDate']).hour, pd.to_datetime(b['IncidentFromDate']).hour
        hour = min(abs(ah-bh), 24-abs(ah-bh))
        return [sim, int(a['_SubheadName']==b['_SubheadName']), int(a['_DistrictID']==b['_DistrictID']), max(0,1-dist/50), max(0,1-hour/12)]
    rows = [vector(pair) for pair in positives + negatives]
    link_prediction_model = RandomForestClassifier(n_estimators=160, max_depth=7, min_samples_leaf=2, random_state=42, n_jobs=1).fit(rows, [1]*len(positives)+[0]*len(negatives))
    link_prediction_features = ['narrative similarity','same offence','same district','geographic proximity','time-of-day similarity']

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

    if link_prediction_model is None:
        build_link_prediction_model()
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
        ml_confidence = None
        if link_prediction_model is not None:
            features = [[candidate['similarity'], int(source['_SubheadName'] == candidate_row['_SubheadName']), int(source['_DistrictID'] == candidate_row['_DistrictID']), max(0, 1 - distance_km / 50), max(0, 1 - hour_difference / 12)]]
            ml_confidence = round(float(link_prediction_model.predict_proba(features)[0][1]) * 100, 1)

        # Keep the ML result explainable for the investigating officer.  These are
        # the same input signals used by the FIR-pair classifier, not a second
        # opaque score.
        similarity_signals = [
            {
                "label": "FIR narrative / MO",
                "value": f"{candidate['similarity'] * 100:.1f}% similarity",
                "score": round(candidate['similarity'] * 100, 1),
            },
            {
                "label": "Offence classification",
                "value": "Same offence type" if source['_SubheadName'] == candidate_row['_SubheadName'] else "Different offence type",
                "score": 100 if source['_SubheadName'] == candidate_row['_SubheadName'] else 0,
            },
            {
                "label": "Geographic proximity",
                "value": f"{distance_km:.1f} km between incidents",
                "score": round(max(0, 1 - distance_km / 50) * 100, 1),
            },
            {
                "label": "Time-of-day pattern",
                "value": f"{hour_difference} hour(s) apart",
                "score": round(max(0, 1 - hour_difference / 12) * 100, 1),
            },
        ]

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
            "mlConfidence": ml_confidence,
            "similarityConfidence": ml_confidence,
            "similaritySignals": similarity_signals,
            "evidence": evidence,
            "missingSignals": missing_signals,
            "distanceKm": round(distance_km, 1),
            "hourDifference": hour_difference,
        })

    links.sort(key=lambda item: (item['similarityConfidence'] or 0, item['connectionScore'], item['similarity']), reverse=True)
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
            "name": "Explainable ML Case Similarity",
            "threshold": "TF-IDF cosine similarity >= 35%",
            "model": "Random Forest FIR-pair classifier",
            "scoring": "Narrative / MO, offence classification, geographic proximity, time-of-day pattern, and known cross-case links. Results are investigative leads, not proof.",
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


def compute_ml_monthly_anomalies(limit=5):
    """Identify unusual current FIR-volume patterns with an unsupervised model.

    One Isolation Forest is trained per district/offence time series.  It learns
    the normal relationship between monthly volume, its recent lags, rolling
    average, and seasonality, then scores the most recent complete month.
    """
    latest_period, _ = get_complete_analysis_periods()
    working = df_case.copy()
    working['_period'] = pd.to_datetime(working['CrimeRegisteredDate']).dt.to_period('M')
    period_range = pd.period_range(latest_period - 24, latest_period, freq='M')
    anomalies = []

    for (district_id, crime_type), series in working.groupby(['_DistrictID', '_SubheadName', '_period']).size().groupby(level=[0, 1]):
        monthly = series.droplevel([0, 1]).reindex(period_range, fill_value=0).astype(float)
        if monthly.nunique() < 3 or monthly.iloc[-1] < 4:
            continue
        frame = pd.DataFrame({'count': monthly})
        frame['lag1'] = frame['count'].shift(1)
        frame['rolling3'] = frame['count'].shift(1).rolling(3, min_periods=3).mean()
        frame['month_sin'] = np.sin(2 * np.pi * np.array([period.month for period in frame.index]) / 12)
        frame['month_cos'] = np.cos(2 * np.pi * np.array([period.month for period in frame.index]) / 12)
        frame = frame.dropna()
        if len(frame) < 16:
            continue

        features = frame[['count', 'lag1', 'rolling3', 'month_sin', 'month_cos']]
        model = IsolationForest(n_estimators=160, contamination=0.12, random_state=42)
        model.fit(features)
        current_features = features.iloc[[-1]]
        decision = float(model.decision_function(current_features)[0])
        predicted_label = int(model.predict(current_features)[0])
        current_count = int(frame['count'].iloc[-1])
        baseline = monthly.iloc[-13:-1]
        baseline_mean = float(baseline.mean())
        ratio = current_count / baseline_mean if baseline_mean else 0

        # A negative Isolation Forest decision is anomalous. Keep material rises
        # only, avoiding low-volume data artefacts from incomplete reporting.
        if predicted_label != -1 or ratio < 1.35:
            continue
        matching = working[
            (working['_DistrictID'] == district_id)
            & (working['_SubheadName'] == crime_type)
            & (working['_period'] == latest_period)
        ].sort_values('CrimeRegisteredDate', ascending=False).head(3)
        anomalies.append({
            'districtId': int(district_id),
            'district': get_district_name(district_id),
            'crimeType': str(crime_type),
            'period': str(latest_period),
            'count': current_count,
            'baselineMean': round(baseline_mean, 1),
            'ratio': round(ratio, 2),
            'anomalyScore': round(max(0, -decision) * 100, 1),
            'model': 'Isolation Forest monthly-volume anomaly model',
            'features': 'FIR volume, 1-month lag, 3-month rolling mean, month-of-year seasonality',
            'cases': [{
                'id': int(row['CaseMasterID']), 'crimeNo': str(row['CrimeNo']),
                'date': str(row['CrimeRegisteredDate']), 'facts': str(row['BriefFacts']),
                'lat': float(row['latitude']), 'lng': float(row['longitude']),
            } for _, row in matching.iterrows()],
        })
    anomalies.sort(key=lambda item: (item['anomalyScore'], item['ratio']), reverse=True)
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

@app.get("/api/hotspots/forecast")
def hotspot_forecast(districtId: int = Query(default=1), crimeHeadId: Optional[int] = Query(default=None)):
    """Forecast next-month grid demand from historical, geocoded FIR volume."""
    cases = filtered_cases(district_id=districtId, crime_head_id=crimeHeadId).dropna(subset=["latitude", "longitude"]).copy()
    cases["_cell"] = cases["latitude"].round(2).astype(str) + "," + cases["longitude"].round(2).astype(str)
    cases["_month"] = cases["_registered"].dt.to_period("M")
    top_cells = cases["_cell"].value_counts().head(60).index.tolist()
    cases = cases[cases["_cell"].isin(top_cells)]
    months = pd.period_range(cases["_month"].min(), cases["_month"].max(), freq="M")
    if len(months) < 16 or not top_cells:
        raise HTTPException(status_code=400, detail="Not enough geocoded FIR history for an ML hotspot forecast")
    grid = cases.groupby(["_cell", "_month"]).size().unstack(fill_value=0).reindex(index=top_cells, columns=months, fill_value=0)

    def features(cell, index):
        period = months[index]
        values = grid.loc[cell].values.astype(float)
        return [values[index-1], values[index-2], values[index-3], values[max(0, index-3):index].mean(), math.sin(2*math.pi*period.month/12), math.cos(2*math.pi*period.month/12)]

    train_x, train_y = [], []
    for cell in top_cells:
        for index in range(3, len(months)):
            train_x.append(features(cell, index)); train_y.append(float(grid.loc[cell].iloc[index]))
    model = RandomForestRegressor(n_estimators=180, max_depth=7, min_samples_leaf=2, random_state=42, n_jobs=1)
    model.fit(train_x, train_y)
    next_month = months[-1] + 1
    zones = []
    for cell in top_cells:
        # Next-period features are computed from observed history; seasonality changes to next month.
        values = grid.loc[cell].values.astype(float)
        next_features = [values[-1], values[-2], values[-3], values[-3:].mean(), math.sin(2*math.pi*next_month.month/12), math.cos(2*math.pi*next_month.month/12)]
        prediction = max(0.0, float(model.predict([next_features])[0]))
        lat, lng = [float(value) for value in cell.split(",")]
        zones.append({"lat":lat,"lng":lng,"predictedIncidents":round(prediction,1),"recentIncidents":int(values[-3:].sum()),"cell":cell})
    zones.sort(key=lambda item: item["predictedIncidents"], reverse=True)
    return {"district":get_district_name(districtId),"forecastMonth":str(next_month),"zones":zones[:10],"model":"Random Forest hotspot-demand model","method":"Grid-cell FIR volume with 1–3 month lags, rolling 3-month volume, and month-of-year seasonality.","caveat":"Planning forecast only. It predicts aggregate historical demand by map cell, not an individual's behaviour or certainty of crime."}

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


@app.get("/api/command-query")
def command_query(q: str = Query(..., min_length=4)):
    """Interpret a small set of officer-style questions with visible filters.

    This is deliberately deterministic: the response states the FIR filters it
    used instead of presenting a black-box conclusion as intelligence.
    """
    query_text = q.strip()
    kannada_terms = {
        "ಬೆಂಗಳೂರು": "bengaluru", "ಮೈಸೂರು": "mysuru", "ರಾತ್ರಿ": "night",
        "ಕಳ್ಳತನ": "burglary", "ದರೋಡೆ": "robbery", "ಕಳ್ಳ": "theft",
        "ಪುನರಾವರ್ತಿತ": "repeat", "ಆರೋಪಿ": "accused", "ಪ್ರಕರಣ": "cases",
    }
    interpreted_query = query_text
    for kannada, english in kannada_terms.items():
        interpreted_query = interpreted_query.replace(kannada, english)
    lowered = interpreted_query.lower()
    working = df_case.copy()
    filters = []

    # Match known KSP districts by name, allowing officers to omit words such
    # as "district" or use a partial name in a spoken-style query.
    district_matches = []
    for _, district in df_district.iterrows():
        district_name = str(district["DistrictName"])
        tokens = [token for token in re.findall(r"[a-z]{4,}", district_name.lower())]
        bengaluru_alias = district_name == "Bangalore Urban" and "bengaluru" in lowered
        if district_name.lower() in lowered or bengaluru_alias or (tokens and all(token in lowered for token in tokens)):
            district_matches.append((int(district["DistrictID"]), district_name))
    if district_matches:
        district_ids = [item[0] for item in district_matches]
        working = working[working["_DistrictID"].isin(district_ids)]
        filters.append("District: " + ", ".join(item[1] for item in district_matches[:3]))

    # Match a supplied offence phrase against the KSP crime sub-head labels.
    offence_matches = []
    for value in df_case["_SubheadName"].dropna().astype(str).unique():
        words = [word for word in re.findall(r"[a-z]{4,}", value.lower())]
        if words and any(word in lowered for word in words):
            offence_matches.append(value)
    if offence_matches:
        working = working[working["_SubheadName"].isin(offence_matches)]
        filters.append("Offence: " + ", ".join(offence_matches[:3]))

    if any(phrase in lowered for phrase in ("night", "night-time", "nighttime", "evening", "after dark")):
        hours = pd.to_datetime(working["IncidentFromDate"], errors="coerce").dt.hour
        working = working[(hours >= 18) | (hours <= 5)]
        filters.append("Incident time: 18:00–05:59")

    linked_accused = df_accused[df_accused["CaseMasterID"].isin(working["CaseMasterID"])].copy()
    repeat_requested = any(term in lowered for term in ("repeat", "repeat offender", "repeat offenders", "recidiv"))
    suspect_rows = []
    if repeat_requested and not linked_accused.empty:
        counts = linked_accused["AccusedName"].value_counts()
        for name, count in counts[counts > 1].head(5).items():
            suspect_cases = linked_accused[linked_accused["AccusedName"] == name]["CaseMasterID"].unique()
            suspect_rows.append({
                "name": str(name),
                "caseCount": int(count),
                "districtCount": int(df_case[df_case["CaseMasterID"].isin(suspect_cases)]["_DistrictID"].nunique()),
            })
        filters.append("Entity condition: repeat accused (2+ linked FIRs)")

    working = working.sort_values("CrimeRegisteredDate", ascending=False)
    case_rows = []
    for _, row in working.head(12).iterrows():
        case_rows.append({
            "id": int(row["CaseMasterID"]),
            "crimeNo": str(row["CrimeNo"]),
            "date": str(row["CrimeRegisteredDate"]),
            "type": str(row["_SubheadName"]),
            "district": get_district_name(row["_DistrictID"]),
            "status": get_case_status_name(row["CaseStatusID"]),
            "facts": str(row["BriefFacts"]),
        })

    scope = "; ".join(filters) if filters else "No structured filter recognised; showing the most recent FIR records"
    answer = f"{len(working)} FIR record{'s' if len(working) != 1 else ''} match the stated intelligence query."
    if suspect_rows:
        answer += f" {len(suspect_rows)} repeat accused profile{'s' if len(suspect_rows) != 1 else ''} meet the selected scope."

    return {
        "query": query_text,
        "interpretedQuery": interpreted_query,
        "languageMode": "Kannada-assisted" if interpreted_query != query_text else "English",
        "answer": answer,
        "scope": scope,
        "filters": filters,
        "cases": case_rows,
        "suspects": suspect_rows,
        "recommendedAction": (
            "Validate the listed FIR narratives and identifiers before issuing operational directions."
            if case_rows else
            "No matching records were found. Broaden the offence, district, or time condition."
        ),
        "method": "Rule-based interpretation of the supplied question against Catalyst FIR fields; no external data or unstated inference is used.",
    }


@app.get("/api/demo-scenarios")
def get_demo_scenarios():
    """Return deploy-safe scenarios selected from records that actually exist."""
    scenarios = []

    scenarios.append({
        "label": "Operation Night Watch",
        "description": "Run the bilingual ML-led burglary investigation: repeat accused, night pattern, and Bengaluru FIR evidence.",
        "query": "Show repeat burglary accused in Bengaluru at night",
        "action": "command",
    })

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
        "scenarios": scenarios[:7],
        "notice": "Synthetic demonstration records. Validate every inference against source evidence.",
    }


class FIRCreateRequest(BaseModel):
    complainantName: str
    victimName: Optional[str] = None
    accusedName: Optional[str] = None
    crimeMinorHeadId: int
    policeStationId: int
    policePersonId: int
    incidentFromDate: datetime
    latitude: float
    longitude: float
    briefFacts: str


@app.get("/api/fir-intake-options")
def get_fir_intake_options():
    officers = df_employee[["EmployeeID", "UnitID", "FirstName"]].copy()
    return {
        "stations": [{"id": int(row.UnitID), "name": str(row.UnitName), "districtId": int(row.DistrictID)} for _, row in df_unit.head(120).iterrows()],
        "officers": [{"id": int(row.EmployeeID), "name": str(row.FirstName), "stationId": int(row.UnitID)} for _, row in officers.head(300).iterrows()],
        "offences": [{"id": int(row.CrimeSubHeadID), "name": str(row.CrimeHeadName)} for _, row in df_crime_subhead.iterrows()],
    }


@app.post("/api/firs")
def create_development_fir(fir: FIRCreateRequest):
    """Create a KSP-schema FIR graph in the Catalyst development datastore."""
    if data_source_status["active"] != "catalyst":
        raise HTTPException(status_code=503, detail="FIR creation requires Catalyst Data Store")
    station = df_unit[df_unit["UnitID"] == fir.policeStationId]
    officer = df_employee[df_employee["EmployeeID"] == fir.policePersonId]
    offence = df_crime_subhead[df_crime_subhead["CrimeSubHeadID"] == fir.crimeMinorHeadId]
    if station.empty or officer.empty or offence.empty:
        raise HTTPException(status_code=422, detail="Select a valid KSP station, officer, and offence")
    if not (11.5 <= fir.latitude <= 18.8 and 74.0 <= fir.longitude <= 78.8):
        raise HTTPException(status_code=422, detail="Coordinates must be within Karnataka")
    station_row, officer_row, offence_row = station.iloc[0], officer.iloc[0], offence.iloc[0]
    district_id = int(station_row["DistrictID"])
    courts = df_court[df_court["DistrictID"] == district_id]
    court_id = int((courts.iloc[0] if not courts.empty else df_court.iloc[0])["CourtID"])
    case_id = int(pd.to_numeric(df_case["CaseMasterID"]).max()) + 1
    complainant_id = int(pd.to_numeric(df_complainant["ComplainantID"]).max()) + 1
    serial = int((df_case["PoliceStationID"] == fir.policeStationId).sum()) + 1
    year = fir.incidentFromDate.year
    crime_no = f"1{district_id:04d}{int(fir.policeStationId):04d}{year}{serial:05d}"
    now = datetime.now(timezone.utc)
    case_row = {
        "CaseMasterID": case_id, "CrimeNo": crime_no, "CaseNo": f"{year}{serial:05d}",
        "CrimeRegisteredDate": now.date().isoformat(), "PolicePersonID": int(officer_row["EmployeeID"]),
        "PoliceStationID": int(station_row["UnitID"]), "CaseCategoryID": 1, "GravityOffenceID": 2,
        "CrimeMajorHeadID": int(offence_row["CrimeHeadID"]), "CrimeMinorHeadID": int(offence_row["CrimeSubHeadID"]),
        "CaseStatusID": 1, "CourtID": court_id, "IncidentFromDate": fir.incidentFromDate.isoformat(),
        "IncidentToDate": fir.incidentFromDate.isoformat(), "InfoReceivedPSDate": now.isoformat(),
        "latitude": fir.latitude, "longitude": fir.longitude, "BriefFacts": fir.briefFacts.strip(),
        "_DistrictID": district_id, "_SubheadName": str(offence_row["CrimeHeadName"]),
    }
    graph = {"CaseMaster": [case_row], "ComplainantDetails": [{
        "ComplainantID": complainant_id, "CaseMasterID": case_id,
        "ComplainantName": fir.complainantName.strip(), "GenderID": 2,
    }]}
    if fir.victimName and fir.victimName.strip():
        graph["Victim"] = [{"VictimMasterID": int(pd.to_numeric(df_victim["VictimMasterID"]).max()) + 1, "CaseMasterID": case_id, "VictimName": fir.victimName.strip(), "GenderID": 2, "VictimPolice": "0"}]
    if fir.accusedName and fir.accusedName.strip():
        graph["Accused"] = [{"AccusedMasterID": int(pd.to_numeric(df_accused["AccusedMasterID"]).max()) + 1, "CaseMasterID": case_id, "AccusedName": fir.accusedName.strip(), "GenderID": 1, "PersonID": "A1"}]
    try:
        catalyst_store.insert_schema_rows(graph)
        load_data(); build_network_graph(); build_nlp_index()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Catalyst development FIR write failed: {exc}")
    return {"caseId": case_id, "crimeNo": crime_no, "environment": "Catalyst Development", "createdTables": list(graph.keys())}


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


@app.get("/api/cases/{case_id}/ai-brief")
def get_case_ai_brief(case_id: int):
    """Create an extractive, source-linked officer briefing for one FIR."""
    rows = df_case[df_case['CaseMasterID'] == int(case_id)]
    if rows.empty:
        raise HTTPException(status_code=404, detail="Case not found")
    case = rows.iloc[0]
    narrative = str(case.get('BriefFacts') or '').strip()
    sentences = [item.strip() for item in re.split(r'(?<=[.!?])\s+', narrative) if item.strip()]
    if tfidf_matrix is None:
        build_nlp_index()
    if sentences:
        sentence_vectors = vectorizer.transform(sentences)
        ranked = sorted(range(len(sentences)), key=lambda index: float(sentence_vectors[index].sum()), reverse=True)
        summary = ' '.join(sentences[index] for index in sorted(ranked[:2]))
    else:
        summary = 'No recorded FIR narrative is available for NLP briefing.'
    narrative_vector = vectorizer.transform([narrative])
    term_scores = narrative_vector.toarray()[0]
    top_indices = np.argsort(term_scores)[::-1]
    keywords = [vectorizer.get_feature_names_out()[index] for index in top_indices if term_scores[index] > 0][:6]
    accused = df_accused[df_accused['CaseMasterID'] == int(case_id)]['AccusedName'].dropna().unique().tolist()
    victims = df_victim[df_victim['CaseMasterID'] == int(case_id)]['VictimName'].dropna().unique().tolist()
    entities = []
    def add_entity(kind, value, confidence, source):
        if value and str(value).strip():
            entities.append({'type': kind, 'value': str(value).strip(), 'confidence': confidence, 'source': source})
    for value in accused[:5]: add_entity('Accused record', value, 99, 'Accused.AccusedName')
    for value in victims[:5]: add_entity('Victim record', value, 99, 'Victim.VictimName')
    add_entity('Phone identifier', clean_val(case.get('phone')), 98, 'CaseMaster narrative identifier')
    add_entity('Vehicle identifier', clean_val(case.get('vehicle')), 98, 'CaseMaster narrative identifier')
    for match in re.findall(r'\b(?:\+91[- ]?)?[6-9]\d{4}[- ]?\d{5}\b', narrative):
        if not any(entity['value'] == match for entity in entities): add_entity('Phone identifier', match, 90, 'Matched in FIR narrative')
    for match in re.findall(r'\b[A-Z]{2}[- ]?\d{2}[- ]?[A-Z]{1,3}[- ]?\d{3,4}\b', narrative.upper()):
        if not any(entity['value'].upper() == match.upper() for entity in entities): add_entity('Vehicle identifier', match, 90, 'Matched in FIR narrative')
    add_entity('Incident time', pd.to_datetime(case['IncidentFromDate']).strftime('%d %b %Y %H:%M'), 99, 'CaseMaster.IncidentFromDate')
    add_entity('Recorded location', f"{float(case['latitude']):.5f}, {float(case['longitude']):.5f}", 99, 'CaseMaster latitude/longitude')
    return {
        'caseId': int(case_id), 'crimeNo': str(case['CrimeNo']), 'summary': summary,
        'keywords': keywords, 'entities': entities,
        'method': 'TF-IDF extractive FIR briefing with schema-linked and regex-verified entity extraction.',
        'caveat': 'The summary only condenses recorded FIR text. Extracted entities require officer verification against the source FIR and supporting evidence.',
    }


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
    
    age_value = pd.to_numeric(acc_rows['AgeYear'].iloc[0], errors='coerce')
    age = int(age_value) if pd.notna(age_value) else None
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
        lat = pd.to_numeric(r['latitude'], errors='coerce')
        lng = pd.to_numeric(r['longitude'], errors='coerce')
        if pd.notna(lat) and pd.notna(lng):
            movement_coordinates.append({
                "lat": float(lat),
                "lng": float(lng),
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

@app.get("/api/profile-options")
def get_profile_options(limit: int = Query(30, ge=5, le=100)):
    counts = df_accused['AccusedName'].dropna().astype(str).value_counts().head(limit)
    options = []
    for name, case_count in counts.items():
        rows = df_accused[df_accused['AccusedName'] == name]
        case_ids = rows['CaseMasterID'].dropna().astype(int).tolist()
        cases = df_case[df_case['CaseMasterID'].isin(case_ids)]
        options.append({
            "name": name,
            "caseCount": int(case_count),
            "districtCount": int(cases['_DistrictID'].nunique()),
            "latestDate": str(cases['CrimeRegisteredDate'].max()) if not cases.empty else None,
        })
    return {"profiles": options}

@app.get("/api/reconstruction-options")
def get_reconstruction_options(limit: int = Query(40, ge=5, le=100)):
    eligible = df_case[
        df_case['IncidentFromDate'].notna()
        & df_case['latitude'].notna()
        & df_case['longitude'].notna()
    ].sort_values('CrimeRegisteredDate', ascending=False).head(limit)
    return {"cases": [{
        "caseId": int(row['CaseMasterID']),
        "crimeNo": str(row['CrimeNo']),
        "crimeType": str(row['_SubheadName']),
        "district": get_district_name(row['_DistrictID']),
        "date": str(row['CrimeRegisteredDate']),
    } for _, row in eligible.iterrows()]}

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
    for index, anomaly in enumerate(compute_ml_monthly_anomalies(limit=5)):
        severity = "urgent" if anomaly['anomalyScore'] >= 8 else "watch"
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
                "label": "ML anomaly confidence signal",
                "value": f"Isolation Forest anomaly score {anomaly['anomalyScore']}/100",
            },
            {
                "label": "Model inputs",
                "value": anomaly['features'],
            },
        ]
        alerts.append({
            "id": f"computed-spike-{index}",
            "severity": severity,
            "title": f"{anomaly['crimeType']} spike — {anomaly['district']}",
            "timeText": f"ML-detected from {anomaly['period']} FIR records",
            "description": (
                f"{anomaly['count']} cases, {increase_percent}% above the preceding "
                f"12-month baseline of {anomaly['baselineMean']}."
            ),
            "whatHappened": (
                f"The Isolation Forest model marked {anomaly['district']} {anomaly['crimeType']} "
                f"volume for {anomaly['period']} as unusual after comparing FIR volume, recent "
                f"trend, and seasonality. The observed volume is {anomaly['ratio']}× the prior 12-month baseline."
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
        "method": "Isolation Forest monthly-volume anomaly detection; validation watches are labelled",
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


@app.get("/api/lifecycle/priority")
def lifecycle_priority(districtId: Optional[int] = Query(default=None), limit: int = Query(default=8, ge=1, le=20)):
    """Rank older open FIRs for supervisor review using a historical delay model.

    The target is a process outcome only: whether a historical FIR had no
    chargesheet within 180 days. It is not a risk score for a person.
    """
    cases = filtered_cases(district_id=districtId).copy()
    if cases.empty:
        raise HTTPException(status_code=404, detail="No cases found")
    analysis_date = cases['_registered'].max()
    cases['_ageDays'] = (analysis_date - cases['_registered']).dt.days
    arrests = df_arrest.copy()
    arrests['_date'] = pd.to_datetime(arrests['ArrestSurrenderDate'], errors='coerce')
    sheets = df_chargesheet.copy()
    sheets['_date'] = pd.to_datetime(sheets['csdate'], errors='coerce')
    first_arrest = arrests.groupby('CaseMasterID')['_date'].min()
    first_sheet = sheets.groupby('CaseMasterID')['_date'].min()
    accused_count = df_accused.groupby('CaseMasterID').size()
    victim_count = df_victim.groupby('CaseMasterID').size()

    cases['_arrestDays'] = cases['CaseMasterID'].map(first_arrest).sub(cases['_registered']).dt.days
    cases['_sheetDays'] = cases['CaseMasterID'].map(first_sheet).sub(cases['_registered']).dt.days
    cases['_hasArrest'] = cases['CaseMasterID'].isin(first_arrest.index).astype(int)
    cases['_accusedCount'] = cases['CaseMasterID'].map(accused_count).fillna(0)
    cases['_victimCount'] = cases['CaseMasterID'].map(victim_count).fillna(0)
    cases['_narrativeLength'] = cases['BriefFacts'].fillna('').astype(str).str.len()
    cases['_hour'] = pd.to_datetime(cases['IncidentFromDate'], errors='coerce').dt.hour.fillna(12)
    cases['_month'] = cases['_registered'].dt.month
    cases['_coordsPresent'] = (cases['latitude'].notna() & cases['longitude'].notna()).astype(int)

    training = cases[cases['_ageDays'] >= 180].copy()
    training['_delayed'] = ((training['_sheetDays'].isna()) | (training['_sheetDays'] > 180)).astype(int)
    feature_columns = ['CrimeMajorHeadID', 'GravityOffenceID', '_DistrictID', 'PoliceStationID', '_hour', '_month', '_narrativeLength', '_accusedCount', '_victimCount', '_coordsPresent', '_hasArrest']
    training_features = training[feature_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
    if len(training) < 50 or training['_delayed'].nunique() < 2:
        raise HTTPException(status_code=400, detail="Not enough historical lifecycle outcomes to train the delay model")
    model = RandomForestClassifier(n_estimators=180, max_depth=10, min_samples_leaf=8, class_weight='balanced', random_state=42, n_jobs=1)
    model.fit(training_features, training['_delayed'])

    candidates = cases[(~cases['CaseStatusID'].isin([2, 3])) & (cases['_ageDays'] >= 30)].copy()
    if candidates.empty:
        return {"district": get_district_name(districtId) if districtId else "Karnataka", "analysisDate": analysis_date.strftime('%Y-%m-%d'), "cases": [], "model": "Random Forest investigation-delay model", "caveat": "No open FIRs aged 30 days or more in this selection."}
    candidate_features = candidates[feature_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
    candidates['_delayProbability'] = model.predict_proba(candidate_features)[:, 1] * 100
    candidates = candidates.sort_values(['_delayProbability', '_ageDays'], ascending=False).head(limit)
    results = []
    for _, row in candidates.iterrows():
        signals = [f"FIR age {int(row['_ageDays'])} days"]
        signals.append("No chargesheet record" if pd.isna(row['_sheetDays']) else f"Chargesheet recorded after {int(row['_sheetDays'])} days")
        if not row['_hasArrest']:
            signals.append("No arrest record linked")
        if row['GravityOffenceID'] == 1:
            signals.append("Heinous-offence classification")
        if not row['_coordsPresent']:
            signals.append("Location field unavailable")
        results.append({
            "caseId": int(row['CaseMasterID']), "crimeNo": str(row['CrimeNo']),
            "district": get_district_name(row['_DistrictID']), "station": get_unit_name(row['PoliceStationID']),
            "crimeType": str(row['_SubheadName']), "ageDays": int(row['_ageDays']),
            "delayRisk": round(float(row['_delayProbability']), 1), "signals": signals,
        })
    return {
        "district": get_district_name(districtId) if districtId else "Karnataka",
        "analysisDate": analysis_date.strftime('%Y-%m-%d'), "cases": results,
        "model": "Random Forest investigation-delay model",
        "training": f"Trained on {len(training):,} FIRs at least 180 days old; target: no chargesheet within 180 days.",
        "features": "FIR category, gravity, jurisdiction, incident timing, narrative completeness, linked accused/victim count, geocode availability, and arrest linkage.",
        "caveat": "A process-priority recommendation only. It must not be used to judge a person or determine enforcement action; a supervisor must review the FIR and evidence record.",
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

    def monthly_features(values, index):
        """Lag and seasonality features available before the predicted month."""
        period = full_index[index]
        return [
            float(values[index - 1]), float(values[index - 2]), float(values[index - 3]),
            float(values[index - 6]), float(values[index - 12]),
            math.sin(2 * math.pi * period.month / 12), math.cos(2 * math.pi * period.month / 12),
        ]

    predictions = []
    training_sizes = []
    values = monthly.astype(float).tolist()
    holdout_start = len(monthly) - holdoutMonths
    for target_index in range(holdout_start, len(monthly)):
        # Train only on months preceding the evaluated month. This keeps the
        # backtest honest: future FIR volumes never enter the training rows.
        train_indices = list(range(12, target_index))
        if len(train_indices) < 8:
            prediction = float(np.mean(values[max(0, target_index - 6):target_index]))
            training_sizes.append(0)
        else:
            features = [monthly_features(values, index) for index in train_indices]
            targets = [values[index] for index in train_indices]
            model = RandomForestRegressor(
                n_estimators=160, max_depth=4, min_samples_leaf=2,
                random_state=42, n_jobs=1,
            )
            model.fit(features, targets)
            prediction = float(model.predict([monthly_features(values, target_index)])[0])
            training_sizes.append(len(train_indices))
        predictions.append(max(0.0, prediction))
    actual_values = actual.astype(float).values
    predicted_values = np.asarray(predictions)
    mae = float(np.mean(np.abs(actual_values - predicted_values)))
    mape_mask = actual_values > 0
    mape = float(np.mean(np.abs((actual_values[mape_mask] - predicted_values[mape_mask]) / actual_values[mape_mask])) * 100) if mape_mask.any() else None
    baseline = np.repeat(float(monthly.iloc[-holdoutMonths-1]), holdoutMonths)
    baseline_mae = float(np.mean(np.abs(actual_values - baseline)))
    return {
        "district": get_district_name(districtId), "crimeCategory": "All categories" if crimeHeadId is None else str(df_crime_head.loc[df_crime_head['CrimeHeadID'] == crimeHeadId, 'CrimeGroupName'].iloc[0]),
        "model": "Random Forest monthly-volume model", "holdoutMonths": holdoutMonths,
        "modelDetails": {
            "algorithm": "Random Forest regression",
            "features": ["1, 2, 3, 6 and 12-month FIR-volume lags", "month-of-year seasonality"],
            "trainingRows": training_sizes,
        },
        "metrics": {"mae": round(mae, 1), "mape": round(mape, 1) if mape is not None else None, "naiveMAE": round(baseline_mae, 1), "improvementVsNaive": round((baseline_mae - mae) / baseline_mae * 100, 1) if baseline_mae else 0},
        "series": [{"month": str(period), "actual": int(actual.loc[period]), "predicted": round(predictions[index], 1)} for index, period in enumerate(actual.index)],
        "caveat": "Retrospective ML backtest only: each predicted month is trained on earlier FIR volumes, then compared with the known holdout. It supports planning, not operational certainty or individual risk decisions.",
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
