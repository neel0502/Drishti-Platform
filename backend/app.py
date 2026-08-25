from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
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
from sklearn.linear_model import LogisticRegression
import re
import os
import json
import math
import hashlib
import hmac
import mimetypes
import tempfile
import uuid
from urllib.parse import unquote
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
from backend import ai_agent
from backend import agent_catalog

# Create FastAPI app
app = FastAPI(title="Drishti Intelligence API")

# Same-origin is the secure default. Explicit cross-origin access can be enabled
# only for known deployment surfaces through DRISHTI_ALLOWED_ORIGINS.
allowed_origins = [
    origin.strip() for origin in os.getenv("DRISHTI_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=bool(allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prevent_stale_application_shell(request: Request, call_next):
    """Force browsers to revalidate the HTML shell after AppSail deployments."""
    response = await call_next(request)
    if request.url.path in {"/", "/index.html"}:
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response

# Resolve directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
BOOTSTRAP_DIR = os.path.join(BASE_DIR, "bootstrap-data")
CATALYST_SCHEMA = os.path.join(BASE_DIR, "deployment", "catalyst", "datastore-schema.json")
USE_CASE_SEED_DIR = os.path.join(BASE_DIR, "use-case-data")

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
district_geometry_cache = {}

# NLP & Network Variables
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = None
case_ids_list = []
G = nx.Graph()
link_prediction_model = None
link_prediction_features = []
offence_classifier = None
offence_classifier_labels = []
analytics_ready = Event()
analytics_initialization_lock = Lock()
synthetic_seed_lock = Lock()
analytics_error = None
operational_action_log = []
hypothesis_boards = []
agent_run_log = []
development_evidence_registry = []
EVIDENCE_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "drishti-development-evidence")
MAX_EVIDENCE_UPLOAD_BYTES = 25 * 1024 * 1024
EVIDENCE_CATEGORIES = {
    "cctv_export": "CCTV export",
    "scene_image": "Scene image",
    "body_camera": "Body-camera clip",
    "document": "Document or statement",
    "digital_artifact": "Digital artifact",
}
ALLOWED_EVIDENCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov", ".pdf", ".txt", ".doc", ".docx"}
ALLOWED_EVIDENCE_MIME_PREFIXES = ("image/", "video/")
ALLOWED_EVIDENCE_MIME_TYPES = {"application/pdf", "text/plain", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"}
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
        "ai": ai_agent.model_configuration(),
        "security": {
            "corsMode": "explicit allowlist" if allowed_origins else "same-origin only",
            "agentMode": "constrained allowlisted tools with human review",
            "authenticationMode": os.getenv("DRISHTI_AUTH_MODE", "demo").lower(),
            "authorizationBoundary": (
                "Catalyst-authenticated identity and server-side role scope"
                if os.getenv("DRISHTI_AUTH_MODE", "demo").lower() == "catalyst"
                else "Explicit prototype role simulation; not production authentication"
            ),
        },
    }


@app.get("/api/ai/model-registry")
def ai_model_registry():
    """Transparent registry of deployed analytical models and their safeguards."""
    return {
        "dataNotice": "Demonstration dataset based on a policing-data schema. It is not operational data.",
        "models": [
            {"name":"Narrative pattern discovery", "algorithm":"TF-IDF + MiniBatch K-Means", "uses":"FIR narrative, offence, district", "doesNotUse":"Identity, biometrics, or external surveillance", "guardrail":"Clusters are leads only; inspect representative FIRs."},
            {"name":"Case-link confidence", "algorithm":"Random Forest FIR-pair classifier", "uses":"Narrative similarity, offence, district, location, incident time, recorded links", "doesNotUse":"Unverified associations as proof", "guardrail":"Validate source FIRs before coordinating or merging investigations."},
            {"name":"Offence suggestion", "algorithm":"TF-IDF + Logistic Regression", "uses":"FIR narrative and existing offence labels", "doesNotUse":"Legal judgement or statutory interpretation", "guardrail":"Station officer confirms the official classification."},
            {"name":"Crime-demand forecast", "algorithm":"Random Forest regressor", "uses":"Aggregate FIR volume, lags, seasonality, map cells", "doesNotUse":"Individual behaviour prediction", "guardrail":"Planning aid only; supervisor approval required."},
            {"name":"Investigation-delay review", "algorithm":"Random Forest classifier", "uses":"FIR lifecycle and record-completeness features", "doesNotUse":"Guilt, risk of a person, sentencing, or enforcement eligibility", "guardrail":"Ranks files for supervisory review only."},
            {"name":"Volume anomaly watch", "algorithm":"Isolation Forest", "uses":"Aggregate monthly volume, trend, and seasonality", "doesNotUse":"Certainty that crime will occur", "guardrail":"Validate linked FIRs before issuing an operational alert."},
        ],
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


@app.post("/api/internal/seed-synthetic-use-cases", tags=["operations"])
def seed_synthetic_use_cases(request: Request):
    """Idempotently insert the fixed, validated synthetic use-case package.

    Callers cannot supply records. The endpoint is restricted to Catalyst's
    development hostname, reserved IDs, a small row cap, and a confirmation
    derived from the exact bundled manifest.
    """
    host = request.url.hostname or ""
    if host not in {"127.0.0.1", "localhost"} and not host.endswith(".development.catalystappsail.in"):
        raise HTTPException(status_code=403, detail="Synthetic seeding is restricted to Catalyst development")
    if data_source_status["active"] != "catalyst":
        raise HTTPException(status_code=503, detail="Synthetic seeding requires Catalyst Data Store")
    manifest_path = os.path.join(USE_CASE_SEED_DIR, "scenario-manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=503, detail="Synthetic use-case package is not bundled")
    with open(manifest_path, "rb") as stream:
        manifest_bytes = stream.read()
    expected_confirmation = hashlib.sha256(manifest_bytes).hexdigest()[:24]
    provided_confirmation = request.headers.get("x-drishti-synthetic-seed", "")
    if not hmac.compare_digest(provided_confirmation, expected_confirmation):
        raise HTTPException(status_code=403, detail="Synthetic seed confirmation is invalid")
    manifest = json.loads(manifest_bytes)
    if manifest.get("synthetic") is not True or manifest.get("totalRows", 0) > 500:
        raise HTTPException(status_code=422, detail="Synthetic seed package failed its safety contract")
    if int(manifest.get("baseCaseId", 0)) < 8_000_000:
        raise HTTPException(status_code=422, detail="Synthetic seed IDs are outside the reserved range")

    unique_columns = {
        "CaseMaster": "CaseMasterID", "Accused": "AccusedMasterID",
        "Victim": "VictimMasterID", "ComplainantDetails": "ComplainantID",
        "ArrestSurrender": "ArrestSurrenderID", "ChargesheetDetails": "CSID",
    }
    inserted, existing = {}, {}
    with synthetic_seed_lock:
        for table, unique_column in unique_columns.items():
            csv_path = os.path.join(USE_CASE_SEED_DIR, f"{table}.csv")
            if not os.path.exists(csv_path):
                raise HTTPException(status_code=503, detail=f"Synthetic package is missing {table}")
            frame = pd.read_csv(csv_path)
            if unique_column not in frame or frame[unique_column].duplicated().any():
                raise HTTPException(status_code=422, detail=f"Synthetic {table} keys are invalid")
            current_rows = catalyst_store.fetch_table(table)
            current_ids = {str(row.get(unique_column)) for row in current_rows}
            missing_frame = frame[~frame[unique_column].astype(str).isin(current_ids)]
            records = missing_frame.where(pd.notna(missing_frame), None).to_dict(orient="records")
            try:
                if records:
                    catalyst_store.insert_schema_rows({table: records})
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Synthetic {table} insert failed: {exc}") from exc
            inserted[table] = len(records)
            existing[table] = len(frame) - len(records)
        load_data()
        build_network_graph()
        build_nlp_index()

    return {
        "status": "seeded" if sum(inserted.values()) else "already-seeded",
        "synthetic": True, "insertedRows": inserted, "existingRows": existing,
        "totalInserted": sum(inserted.values()),
        "scenarios": [{
            "code": item["code"], "title": item["title"],
            "caseIds": item["caseIds"], "expectedSignals": item["expectedSignals"],
            "negativeControl": item["negativeControl"],
        } for item in manifest["scenarios"]],
        "notice": "Synthetic development records only. Existing FIR rows were not modified.",
    }

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
    trend_values = trend_data.values.tolist()
    trend_is_stable = bool(trend_values) and (max(trend_values) - min(trend_values) < max(3, round(max(trend_values) * 0.10)))
    trend_note = (
        "Stable monthly volume in the current synthetic test dataset"
        if trend_is_stable
        else "Monthly FIR volume; review peaks before drawing operational conclusions"
    )

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
            "values": trend_values,
            "note": trend_note,
            "festiveOverlay": None if trend_is_stable else {
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

@app.get("/api/semantic-search")
def semantic_fir_search(q: str = Query(..., min_length=4), limit: int = 8):
    """Retrieve FIRs by narrative meaning using the deployed TF-IDF index."""
    if tfidf_matrix is None:
        build_nlp_index()
    query_vector = vectorizer.transform([q.strip()])
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    ranked = np.argsort(similarities)[::-1][:limit]
    cases = []
    for index in ranked:
        row = df_case[df_case['CaseMasterID'] == case_ids_list[index]].iloc[0]
        cases.append({
            'id': int(row['CaseMasterID']), 'crimeNo': str(row['CrimeNo']),
            'date': str(row['CrimeRegisteredDate']), 'type': str(row['_SubheadName']),
            'district': get_district_name(row['_DistrictID']),
            'status': get_case_status_name(row['CaseStatusID']), 'facts': str(row['BriefFacts']),
            'semanticConfidence': round(float(similarities[index]) * 100, 1),
        })
    return {
        'query': q, 'cases': cases, 'people': [], 'phones': [], 'vehicles': [],
        'model': 'TF-IDF semantic FIR narrative retrieval with cosine similarity',
        'caveat': 'Similarity ranks narrative language, not proof of a common offender, event, or legal linkage. Open and validate each FIR before action.',
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

    # Match known districts by name, allowing officers to omit words such
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

    # Match a supplied offence phrase against the crime sub-head labels.
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


class FIRClassificationRequest(BaseModel):
    narrative: str


class SyntheticScenarioRequest(BaseModel):
    scenario: str = "night_burglary"
    caseCount: int = 4


@app.post("/api/synthetic-scenarios/generate")
def generate_synthetic_scenario(request: SyntheticScenarioRequest):
    """Create schema-compatible, in-memory demo records; never writes police data."""
    templates = {
        "night_burglary": {
            "title": "Operation Night Watch",
            "offence": "House Burglary",
            "districts": ["Bengaluru Urban", "Mysuru", "Belagavi"],
            "narrative": "SYNTHETIC DEMO: Unknown persons entered a locked residence at night using a drill on the front-door lock. Gold ornaments and cash reported stolen. Witness observed a dark motorcycle nearby.",
            "vehicle": "SYN-KA-05-DEMO", "phone": "90000-00001",
            "test": "Run semantic MO search, cross-case link prediction, reconstruction, and missing CCTV/ANPR evidence checks.",
        },
        "chain_snatching": {
            "title": "Metro Corridor Chain Snatching",
            "offence": "Chain Snatching",
            "districts": ["Bengaluru Urban", "Bengaluru Urban", "Mysuru"],
            "narrative": "SYNTHETIC DEMO: Two riders on a motorcycle targeted a lone pedestrian near a transport corridor in the evening and snatched a gold chain before leaving the area.",
            "vehicle": "SYN-KA-05-DEMO", "phone": "90000-00002",
            "test": "Run MO similarity, map hotspot view, linked-vehicle investigation, and patrol planning scenario.",
        },
        "cyber_fraud": {
            "title": "Festival Phishing Fraud Cluster",
            "offence": "Cyber Fraud",
            "districts": ["Mysuru", "Dharwad", "Bengaluru Urban"],
            "narrative": "SYNTHETIC DEMO: Victim received a fraudulent service-payment message and disclosed a one-time password. Funds were transferred through an unknown digital channel.",
            "vehicle": "Not applicable", "phone": "90000-00003",
            "test": "Run narrative classification, semantic search, anomaly watch, and evidence-gap review.",
        },
        "evidence_gap": {
            "title": "Incomplete Evidence Review Queue",
            "offence": "Robbery",
            "districts": ["Belagavi", "Dharwad", "Mysuru"],
            "narrative": "SYNTHETIC DEMO: Robbery reported near a commercial area. Witness account is available, but CCTV reference, vehicle number, and suspect identity are not yet recorded.",
            "vehicle": "Not recorded", "phone": "Not recorded",
            "test": "Open reconstruction to demonstrate explicit missing-evidence links and the supervisory review workflow.",
        },
    }
    template = templates.get(request.scenario)
    if not template:
        raise HTTPException(status_code=422, detail="Choose a supported synthetic scenario")
    count = max(2, min(int(request.caseCount), 10))
    base_date = datetime(2024, 11, 18, 20, 0, tzinfo=timezone.utc)
    cases = []
    for index in range(count):
        district = template['districts'][index % len(template['districts'])]
        timestamp = base_date + timedelta(days=index * 3, hours=index % 3)
        cases.append({
            "caseId": f"SYN-{request.scenario.upper()}-{index + 1:02d}",
            "crimeNo": f"SYN-2024-{index + 1:04d}", "district": district,
            "offence": template['offence'], "incidentTime": timestamp.isoformat(),
            "narrative": template['narrative'], "vehicle": template['vehicle'], "phone": template['phone'],
            "status": "Synthetic demo record",
        })
    return {
        "synthetic": True, "title": template['title'], "cases": cases,
        "schemaTables": ["CaseMaster", "Accused", "Victim", "ComplainantDetails", "ArrestSurrender", "ChargesheetDetails"],
        "testPlan": template['test'],
        "notice": "Synthetic test data only. It is generated in memory for the demo sandbox, is not written to Catalyst Data Store, and must never be represented as production data.",
    }


def build_offence_classifier():
    """Train a transparent narrative-to-offence classifier from labelled FIRs."""
    global offence_classifier, offence_classifier_labels
    if tfidf_matrix is None:
        build_nlp_index()
    labels = df_case.set_index('CaseMasterID').loc[case_ids_list, '_SubheadName'].fillna('').astype(str)
    eligible = labels.value_counts()
    eligible = eligible[eligible >= 25].index
    mask = labels.isin(eligible)
    indices = np.flatnonzero(mask.to_numpy())
    if len(indices) > 12000:
        indices = np.random.default_rng(42).choice(indices, size=12000, replace=False)
    offence_classifier = LogisticRegression(max_iter=250, class_weight='balanced', multi_class='auto', n_jobs=1)
    offence_classifier.fit(tfidf_matrix[indices], labels.iloc[indices])
    offence_classifier_labels = offence_classifier.classes_.tolist()


@app.post("/api/fir-classification")
def classify_fir_narrative(request: FIRClassificationRequest):
    narrative = request.narrative.strip()
    if len(narrative) < 20:
        raise HTTPException(status_code=422, detail="Enter at least 20 characters of FIR narrative for a classification suggestion")
    if offence_classifier is None:
        build_offence_classifier()
    probabilities = offence_classifier.predict_proba(vectorizer.transform([narrative]))[0]
    top = np.argsort(probabilities)[::-1][:3]
    suggestions = [{
        'offence': str(offence_classifier.classes_[index]),
        'confidence': round(float(probabilities[index]) * 100, 1),
    } for index in top]
    return {
        'suggestions': suggestions,
        'model': 'TF-IDF FIR narrative vectors + multinomial Logistic Regression',
        'training': f'Trained on {len(offence_classifier_labels)} official offence labels represented in historic FIRs.',
        'caveat': 'Classification assistance only. The officer must confirm the statutory/offence classification from the FIR facts and applicable law.',
    }


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
    """Create a schema-mapped FIR graph in the Catalyst development datastore."""
    if data_source_status["active"] != "catalyst":
        raise HTTPException(status_code=503, detail="FIR creation requires Catalyst Data Store")
    station = df_unit[df_unit["UnitID"] == fir.policeStationId]
    officer = df_employee[df_employee["EmployeeID"] == fir.policePersonId]
    offence = df_crime_subhead[df_crime_subhead["CrimeSubHeadID"] == fir.crimeMinorHeadId]
    if station.empty or officer.empty or offence.empty:
        raise HTTPException(status_code=422, detail="Select a valid station, officer, and offence")
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


def valid_evidence_upload(filename: str, mime_type: str) -> bool:
    extension = os.path.splitext(filename.lower())[1]
    return extension in ALLOWED_EVIDENCE_EXTENSIONS and (
        mime_type.startswith(ALLOWED_EVIDENCE_MIME_PREFIXES) or mime_type in ALLOWED_EVIDENCE_MIME_TYPES
    )


@app.post("/api/evidence")
async def upload_development_evidence(
    request: Request,
    caseId: Optional[int] = Query(None, ge=1),
    category: str = Query("document"),
    source: str = Query("station_intake"),
    note: str = Query("", max_length=2000),
    collectedBy: str = Query("Authorized officer", max_length=120),
    collectedAt: Optional[str] = Query(None, max_length=50),
    collectionLocation: str = Query("", max_length=240),
    sealNumber: str = Query("", max_length=80),
    receivedBy: str = Query("Evidence officer", max_length=120),
):
    """Store a bounded development evidence file with immutable metadata and checksum.

    Files are deliberately written only to temporary AppSail/local storage. They are
    never exposed through a public download endpoint and are not production evidence.
    """
    if category not in EVIDENCE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Choose a valid evidence type")
    if caseId is not None and df_case[df_case["CaseMasterID"] == caseId].empty:
        raise HTTPException(status_code=404, detail="Case not found")
    if collectedAt:
        try:
            collected_at = datetime.fromisoformat(collectedAt.replace("Z", "+00:00")).isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Provide the collection time in ISO format") from exc
    else:
        collected_at = datetime.now(timezone.utc).isoformat()
    encoded_filename = request.headers.get("x-evidence-filename", "")
    filename = os.path.basename(unquote(encoded_filename)).strip() or "uploaded-evidence"
    mime_type = request.headers.get("content-type", "application/octet-stream").split(";", 1)[0].strip().lower()
    if not valid_evidence_upload(filename, mime_type):
        raise HTTPException(status_code=415, detail="Supported uploads are images, MP4/WebM/MOV video, PDF, text, DOC, and DOCX files")
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_EVIDENCE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Evidence files are limited to 25 MB in the development prototype")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="Evidence upload is empty")
    if len(content) > MAX_EVIDENCE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Evidence files are limited to 25 MB in the development prototype")
    evidence_id = f"DEV-EV-{uuid.uuid4().hex[:10].upper()}"
    os.makedirs(EVIDENCE_UPLOAD_DIR, exist_ok=True)
    stored_name = f"{evidence_id}{os.path.splitext(filename)[1].lower()}"
    stored_path = os.path.join(EVIDENCE_UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as stream:
        stream.write(content)
    checksum = hashlib.sha256(content).hexdigest()
    received_at = datetime.now(timezone.utc).isoformat()
    record = {
        "id": evidence_id,
        "caseId": caseId,
        "fileName": filename,
        "mimeType": mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "sizeBytes": len(content),
        "sha256": checksum,
        "sha256Short": checksum[:16],
        "category": category,
        "categoryLabel": EVIDENCE_CATEGORIES[category],
        "source": source[:80],
        "noteRecorded": bool(note.strip()),
        "note": redact_agent_text(note.strip())[:2000],
        "collectedBy": redact_agent_text(collectedBy.strip())[:120],
        "collectedAt": collected_at,
        "collectionLocation": redact_agent_text(collectionLocation.strip())[:240],
        "sealNumber": redact_agent_text(sealNumber.strip())[:80],
        "receivedBy": redact_agent_text(receivedBy.strip())[:120],
        "receivedAt": received_at,
        "custodyStatus": "received",
        "humanVerified": False,
        "storageNotice": "Stored only in temporary development application storage; not a production evidence vault.",
    }
    development_evidence_registry.insert(0, record)
    del development_evidence_registry[100:]
    if caseId is not None:
        event = _append_workflow_event("evidence-created", caseId, record, "received")
        record["auditEventId"] = event["actionId"]
        if event.get("persistenceWarning"):
            record["persistenceWarning"] = event["persistenceWarning"]
    return record


@app.get("/api/evidence")
def list_development_evidence(caseId: Optional[int] = Query(None, ge=1)):
    """Return development evidence metadata only; file content is intentionally not served."""
    if not isinstance(caseId, (int, type(None))):
        caseId = None
    records_by_id = {record["id"]: dict(record) for record in development_evidence_registry}
    for event in _read_workflow_events("evidence-", caseId):
        payload = event["eventPayload"]
        evidence_id = str(payload.get("evidenceId") or payload.get("id") or "")
        if not evidence_id:
            continue
        if event["actionType"] == "evidence-created":
            records_by_id.setdefault(evidence_id, {**payload, "caseId": event["caseId"]})
        elif evidence_id in records_by_id:
            records_by_id[evidence_id]["custodyStatus"] = payload.get("status", event["status"])
            records_by_id[evidence_id]["humanVerified"] = payload.get("status") == "verified"
            records_by_id[evidence_id]["verifiedBy"] = payload.get("officer")
            records_by_id[evidence_id]["verifiedAt"] = event["timestamp"]
    records = sorted(records_by_id.values(), key=lambda item: str(item.get("receivedAt") or ""), reverse=True)
    if caseId is not None:
        records = [record for record in records if record["caseId"] == caseId]
    return {"records": records, "notice": "Custody metadata is append-only and persisted when Catalyst is active. Uploaded binary files remain temporary development artifacts and are never exposed through a download endpoint."}


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


@app.get("/api/cases/{case_id}/command-plan")
def get_case_command_plan(case_id: int):
    """Return an evidence-led, human-approved command plan for one FIR.

    This intentionally packages existing recorded case links and evidence gaps
    into an officer workflow; it never makes an autonomous operational decision.
    """
    reconstruction = build_incident_reconstruction(case_id)
    case = reconstruction["case"]
    decision = reconstruction["decisionSupport"]
    top_link = reconstruction["linkedCases"][0] if reconstruction["linkedCases"] else None
    steps = []
    for index, missing in enumerate(reconstruction["missingLinks"][:3], start=1):
        steps.append({
            "id": f"evidence-{index}",
            "stage": "Evidence verification",
            "priority": "urgent" if missing["status"] == "conflict" else "review",
            "title": f"Resolve {missing['field']}",
            "rationale": missing["impact"],
            "nextStep": missing["nextStep"],
        })
    if top_link:
        steps.append({
            "id": "link-review",
            "stage": "Cross-case review",
            "priority": "review",
            "title": f"Validate linked FIR {top_link['crimeNo']}",
            "rationale": f"Connection score {top_link['connectionScore']}/100 is based on recorded signals, not proof.",
            "nextStep": "Compare source FIRs and verify every listed signal before coordinating or merging investigations.",
        })
    if len(decision["affectedDistricts"]) > 1:
        steps.append({
            "id": "coordination",
            "stage": "Supervisor decision",
            "priority": "approval",
            "title": "Consider cross-district coordination",
            "rationale": f"Related FIRs span {', '.join(decision['affectedDistricts'])}.",
            "nextStep": "A designated supervisor must review the evidence and explicitly approve any coordination request.",
        })
    return {
        "case": case,
        "priority": decision["priority"],
        "evidenceCompleteness": reconstruction["dataCompleteness"],
        "strongestLinkScore": decision["strongestLinkScore"],
        "linkedCases": reconstruction["linkedCases"][:3],
        "steps": steps,
        "guardrail": "Decision support only. Every cross-case link, evidence gap, and operational action requires human verification and approval.",
    }


AGENT_ROLE_POLICIES = {
    "command": {"case_review", "cross_district", "patrol_context"},
    "district": {"case_review", "cross_district"},
    "analyst": {"case_review"},
    "station": {"case_review"},
    "patrol": {"patrol_context"},
}


class InvestigationAgentRequest(BaseModel):
    caseId: int
    role: str = "district"
    query: str = "What evidence must be verified before a review decision?"
    language: str = "en"


class AgentWorkflowRequest(BaseModel):
    agentId: str
    caseId: Optional[int] = None
    role: str = "station"
    query: Optional[str] = None
    language: str = "en"
    context: Optional[dict] = None


def redact_agent_text(value):
    """Apply output minimisation before agent-generated text reaches the UI."""
    text = str(value or "")
    def mask_last_four(match, label):
        digits = re.sub("[^0-9]", "", match.group(0))
        return f"{label}-••••{digits[-4:]}"
    text = re.sub(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)", lambda match: mask_last_four(match, "PHONE"), text)
    text = re.sub(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)", lambda match: mask_last_four(match, "ID"), text)
    text = VEHICLE_PATTERN.sub("VEHICLE-••••", text)
    return text


def _bounded_confidence(value, default=50):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return default


def validate_model_agent_draft(payload, allowed_source_ids, allowed_action_types=None):
    """Turn untrusted model JSON into the existing safe UI response contract."""
    if not isinstance(payload, dict):
        raise ValueError("Model draft is not an object")
    allowed_claim_types = {"recorded_context", "evidence_gap", "candidate_link"}
    allowed_action_types = set(allowed_action_types or {"verify_evidence", "validate_case_link", "draft_coordination_review"})
    allowed_source_ids = set(allowed_source_ids)
    claims = []
    for raw in (payload.get("claims") or [])[:5]:
        if not isinstance(raw, dict) or raw.get("claimType") not in allowed_claim_types:
            continue
        sources = [str(item) for item in (raw.get("sourceIds") or []) if str(item) in allowed_source_ids]
        statement = redact_agent_text(str(raw.get("statement") or "").strip())[:800]
        if not statement or not sources:
            continue
        claims.append({
            "id": f"CL{len(claims) + 1}",
            "statement": statement,
            "claimType": raw["claimType"],
            "supportingSourceIds": sources,
            "confidenceBeforeReview": _bounded_confidence(raw.get("confidence")),
            "recordStatus": {
                "recorded_context": "recorded FIR context—underlying assertions require verification",
                "evidence_gap": "computed from current record presence",
                "candidate_link": "analytical lead—not proof",
            }[raw["claimType"]],
        })
    if not claims:
        raise ValueError("Model draft did not contain a source-linked claim")

    reviews_by_index = {}
    for raw in (payload.get("skepticReviews") or [])[:5]:
        if not isinstance(raw, dict):
            continue
        try:
            index = int(raw.get("claimIndex"))
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(claims):
            reviews_by_index[index] = raw
    reviews = []
    for index, claim in enumerate(claims):
        raw = reviews_by_index.get(index, {})
        sources = [str(item) for item in (raw.get("sourceIds") or []) if str(item) in allowed_source_ids]
        after = min(claim["confidenceBeforeReview"], _bounded_confidence(raw.get("confidenceAfterReview"), claim["confidenceBeforeReview"] - 10))
        reviews.append({
            "claimId": claim["id"],
            "verdict": redact_agent_text(str(raw.get("verdict") or "retain with verification"))[:120],
            "challenge": redact_agent_text(str(raw.get("challenge") or "Verify the cited source records and seek independent corroboration."))[:800],
            "contradictingSourceIds": sources,
            "confidenceAfterReview": max(0, after),
        })

    actions = []
    for raw in (payload.get("actions") or [])[:5]:
        if not isinstance(raw, dict) or raw.get("type") not in allowed_action_types:
            continue
        sources = [str(item) for item in (raw.get("sourceIds") or []) if str(item) in allowed_source_ids]
        title = redact_agent_text(str(raw.get("title") or "").strip())[:180]
        reason = redact_agent_text(str(raw.get("reason") or "").strip())[:800]
        if title and reason and sources:
            actions.append({
                "type": raw["type"], "title": title, "reason": reason,
                "sourceIds": sources, "requiresHumanApproval": True,
            })
    if not actions:
        raise ValueError("Model draft did not contain a source-linked review action")
    summary = redact_agent_text(str(payload.get("summary") or "Investigation review draft generated from cited records."))[:1200]
    return summary, claims, reviews, actions


def run_investigation_agent(request: InvestigationAgentRequest, workflow_spec=None):
    """A constrained, evidence-cited orchestration layer over internal tools.

    The agent intentionally has no free-form network, messaging, enforcement, or
    dispatch tools. It may only retrieve case context, identify gaps, and create
    a human-review draft. This is the production safety boundary for the demo.
    """
    role = request.role.strip().lower()
    allowed_tools = AGENT_ROLE_POLICIES.get(role)
    if allowed_tools is None or (workflow_spec is not None and role not in workflow_spec.roles):
        raise HTTPException(status_code=403, detail="This role is not permitted to run the investigation agent")
    if len(request.query.strip()) < 8 or len(request.query) > 1200:
        raise HTTPException(status_code=422, detail="Provide an investigation question between 8 and 1200 characters")

    source_map = {
        "case_reconstruction": {"C1", "C2"}, "case_brief": {"C4"},
        "case_link_review": {"C3"}, "data_quality_review": {"C5"},
        "shift_context": {"C6"},
    }
    workflow_tool_names = set(workflow_spec.tools) if workflow_spec else {
        "case_reconstruction", "case_brief", "case_link_review", "data_quality_review"
    }
    case_rows = df_case[df_case["CaseMasterID"] == request.caseId]
    if case_rows.empty:
        raise HTTPException(status_code=404, detail="Case not found")
    case_row = case_rows.iloc[0]
    private_names = set()
    for frame, column in (
        (df_accused, "AccusedName"), (df_victim, "VictimName"), (df_complainant, "ComplainantName")
    ):
        if frame is None or column not in frame.columns:
            continue
        values = frame[frame["CaseMasterID"] == request.caseId][column].dropna().astype(str)
        private_names.update(value.strip() for value in values if len(value.strip()) >= 4 and value.strip().lower() != "unknown")

    def minimize_agent_value(value):
        text = redact_agent_text(value)
        for name in sorted(private_names, key=len, reverse=True):
            text = re.sub(re.escape(name), "PERSON-REDACTED", text, flags=re.IGNORECASE)
        return text
    if "case_reconstruction" in workflow_tool_names:
        reconstruction = build_incident_reconstruction(request.caseId)
        case = reconstruction["case"]
    else:
        case = {
            "caseId": int(request.caseId), "crimeNo": str(case_row["CrimeNo"]),
            "crimeType": str(case_row["_SubheadName"]),
            "district": get_district_name(case_row["_DistrictID"]),
            "briefFacts": str(case_row.get("BriefFacts") or ""),
        }
        reconstruction = {"case": case, "missingLinks": [], "decisionSupport": {"affectedDistricts": []}}
    brief = get_case_ai_brief(request.caseId) if "case_brief" in workflow_tool_names else {"summary": "Case narrative was not requested by this workflow."}
    links = get_case_links(request.caseId, top_n=3) if "case_link_review" in workflow_tool_names else {"relatedCases": []}
    quality = data_quality_command_centre(districtId=int(case_row["_DistrictID"])) if "data_quality_review" in workflow_tool_names else {"scope": case["district"]}
    priority_context = lifecycle_priority(districtId=None, limit=8).get("cases", [])[:8] if "shift_context" in workflow_tool_names else []
    sentinel_context = get_agent_sentinel(limit=6).get("triggers", [])[:6] if "shift_context" in workflow_tool_names else []
    all_fallback_tools = [
        {"name": "case_reconstruction", "purpose": "Retrieve recorded timeline and evidence gaps", "status": "completed"},
        {"name": "case_brief", "purpose": "Extract recorded FIR narrative signals", "status": "completed"},
        {"name": "case_link_review", "purpose": "Retrieve explainable cross-FIR signals", "status": "completed"},
        {"name": "data_quality_review", "purpose": "Challenge leads against district data-quality risks", "status": "completed"},
        {"name": "shift_context", "purpose": "Retrieve priority work, pending reviews, and recorded handoffs", "status": "completed"},
    ]
    citations = [
        {"id": "C1", "label": f"FIR {case['crimeNo']} timeline", "source": "CaseMaster.IncidentFromDate, CrimeRegisteredDate, coordinates", "confidence": "recorded"},
        {"id": "C2", "label": "Evidence-gap assessment", "source": "CaseMaster, Accused, Victim, ArrestSurrender, ChargesheetDetails", "confidence": "recorded schema presence"},
        {"id": "C3", "label": "Cross-case link assessment", "source": "Explainable FIR link signals", "confidence": "review required"},
        {"id": "C4", "label": "Extractive FIR brief", "source": "CaseMaster.BriefFacts", "confidence": "recorded narrative"},
        {"id": "C5", "label": f"{quality['scope']} data-quality audit", "source": "Schema completeness, chronology, geography, and duplicate checks", "confidence": "computed audit"},
        {"id": "C6", "label": "Current shift review context", "source": "Lifecycle priority queue, sentinel triggers, and recorded human actions", "confidence": "computed from recorded workflow state"},
    ]
    model_result = None
    model_warning = None

    tool_payloads = {
        "case_reconstruction": {
            "citations": citations[:2], "case": reconstruction["case"],
            "timeline": reconstruction.get("timeline", []),
            "missingLinks": reconstruction["missingLinks"],
            "decisionSupport": reconstruction.get("decisionSupport", {}),
        },
        "case_brief": {"citations": [citations[3]], "brief": brief},
        "case_link_review": {"citations": [citations[2]], "relatedCases": links["relatedCases"]},
        "data_quality_review": {"citations": [citations[4]], "audit": quality},
        "shift_context": {
            "citations": [citations[5]],
            "priorityCases": priority_context,
            "reviewTriggers": sentinel_context,
            "recordedActions": operational_action_log[:12],
        },
    }
    workflow_source_ids = set().union(*(source_map[name] for name in workflow_tool_names))
    fallback_tools_used = [item for item in all_fallback_tools if item["name"] in workflow_tool_names]
    visible_citations = [item for item in citations if item["id"] in workflow_source_ids]

    def execute_agent_tool(name):
        if name not in tool_payloads:
            raise ValueError(f"Tool is not allowlisted: {name}")
        # Identifiers are minimized before any content leaves the application.
        return json.loads(minimize_agent_value(json.dumps(tool_payloads[name], default=str)))

    try:
        model_result = ai_agent.run_model_agent(
            case_id=request.caseId, role=role, query=request.query.strip(),
            execute_tool=execute_agent_tool,
            agent_name=workflow_spec.name if workflow_spec else None,
            focus=workflow_spec.focus if workflow_spec else None,
            allowed_tool_names=set(workflow_spec.tools) if workflow_spec else None,
            allowed_action_types=set(workflow_spec.action_types) if workflow_spec else None,
        )
    except Exception as exc:
        model_warning = (
            "The live model did not complete within the officer response window; "
            f"the validated source-linked evidence workflow was returned instead ({type(exc).__name__})."
        )

    scout_claims = []
    if {"C1", "C4"} & workflow_source_ids:
        scout_claims.append({
            "id": f"CL{len(scout_claims) + 1}",
            "statement": redact_agent_text(brief["summary"]),
            "claimType": "recorded_context",
            "supportingSourceIds": [source_id for source_id in ("C1", "C4") if source_id in workflow_source_ids],
            "confidenceBeforeReview": 95,
            "recordStatus": "recorded FIR context",
        })
    if "C2" in workflow_source_ids:
        scout_claims.append({
            "id": f"CL{len(scout_claims) + 1}",
            "statement": f"The case has {len(reconstruction['missingLinks'])} missing, partial, or conflicting evidence links.",
            "claimType": "evidence_gap",
            "supportingSourceIds": ["C2"],
            "confidenceBeforeReview": 99,
            "recordStatus": "computed from record presence",
        })
    if "C5" in workflow_source_ids:
        scout_claims.append({
            "id": f"CL{len(scout_claims) + 1}",
            "statement": f"The {quality['scope']} data-quality audit must be reviewed before relying on incomplete or conflicting records.",
            "claimType": "evidence_gap",
            "supportingSourceIds": ["C5"],
            "confidenceBeforeReview": 90,
            "recordStatus": "computed data-quality finding",
        })
    if "C6" in workflow_source_ids:
        shift_payload = tool_payloads["shift_context"]
        scout_claims.append({
            "id": f"CL{len(scout_claims) + 1}",
            "statement": f"Current workflow context contains {len(shift_payload['priorityCases'])} priority cases and {len(shift_payload['reviewTriggers'])} review triggers.",
            "claimType": "recorded_context",
            "supportingSourceIds": ["C6"],
            "confidenceBeforeReview": 90,
            "recordStatus": "computed workflow context",
        })
    if links["relatedCases"] and "C3" in workflow_source_ids:
        strongest = links["relatedCases"][0]
        scout_claims.append({
            "id": f"CL{len(scout_claims) + 1}",
            "statement": f"FIR {strongest['crimeNo']} is a candidate related case with connection score {strongest['connectionScore']}/100.",
            "claimType": "candidate_link",
            "supportingSourceIds": ["C3"],
            "confidenceBeforeReview": int(strongest["connectionScore"]),
            "recordStatus": "analytical lead—not proof",
        })

    skeptic_reviews = []
    for claim in scout_claims:
        if claim["claimType"] == "candidate_link":
            weak_link = claim["confidenceBeforeReview"] < 65
            skeptic_reviews.append({
                "claimId": claim["id"],
                "verdict": "challenged" if weak_link else "retain with verification",
                "challenge": "The connection may reflect a common offence, district, or narrative pattern rather than a shared offender. Validate the source FIRs and independent identifiers.",
                "contradictingSourceIds": [source_id for source_id in ("C2", "C5") if source_id in workflow_source_ids] or claim["supportingSourceIds"],
                "confidenceAfterReview": max(10, claim["confidenceBeforeReview"] - (15 if weak_link else 5)),
            })
        elif claim["claimType"] == "recorded_context":
            skeptic_reviews.append({
                "claimId": claim["id"],
                "verdict": "retained as recorded context",
                "challenge": "The narrative is recorded but may contain unverified complainant or witness assertions; consult the source FIR and supporting evidence.",
                "contradictingSourceIds": ["C2"] if "C2" in workflow_source_ids else claim["supportingSourceIds"],
                "confidenceAfterReview": 85,
            })
        else:
            skeptic_reviews.append({
                "claimId": claim["id"],
                "verdict": "retained",
                "challenge": "Record absence is confirmed, but absence does not establish that the evidence does not exist outside the current dataset.",
                "contradictingSourceIds": ["C5"] if "C5" in workflow_source_ids else claim["supportingSourceIds"],
                "confidenceAfterReview": 90,
            })
    actions = []
    fallback_action_type = "verify_evidence"
    if workflow_spec is not None:
        fallback_action_type = workflow_spec.action_types[0]
    if "C2" in workflow_source_ids:
        for missing in reconstruction["missingLinks"][:3]:
            actions.append({
                "type": fallback_action_type,
                "title": f"Verify {missing['field']}",
                "reason": missing["impact"],
                "sourceIds": ["C2"],
                "requiresHumanApproval": True,
            })
    else:
        primary_source_id = next(source_id for source_id in ("C6", "C5", "C2", "C3", "C4", "C1") if source_id in workflow_source_ids)
        action_title = {
            "verify_record": "Verify cited record",
            "add_task_draft": "Draft officer follow-up task",
            "request_review": "Request human review",
            "prepare_document_draft": "Prepare editable document draft",
            "validate_case_link": "Validate candidate case link",
            "draft_coordination_review": "Draft coordination review",
        }.get(fallback_action_type, "Prepare human-review draft")
        actions.append({
            "type": fallback_action_type,
            "title": action_title,
            "reason": workflow_spec.focus if workflow_spec else "Verify the source records before taking any operational action.",
            "sourceIds": [primary_source_id],
            "requiresHumanApproval": True,
        })
    if links["relatedCases"] and (workflow_spec is None or "validate_case_link" in workflow_spec.action_types):
        strongest = links["relatedCases"][0]
        actions.append({
            "type": "validate_case_link",
            "title": f"Review linked FIR {strongest['crimeNo']}",
            "reason": f"The link has score {strongest['connectionScore']}/100 and must be corroborated before any investigative coordination.",
            "sourceIds": ["C3"],
            "requiresHumanApproval": True,
        })
    affected = reconstruction["decisionSupport"]["affectedDistricts"]
    if "cross_district" in allowed_tools and len(affected) > 1 and (workflow_spec is None or "draft_coordination_review" in workflow_spec.action_types):
        actions.append({
            "type": "draft_coordination_review",
            "title": "Draft cross-district review request",
            "reason": f"Related FIR signals span {', '.join(affected)}.",
            "sourceIds": ["C1", "C3"],
            "requiresHumanApproval": True,
        })
    workflow_name = workflow_spec.name if workflow_spec else "Drishti Case Investigator"
    if request.language.strip().lower() == "kn":
        answer = (
            f"{workflow_name} ಎಫ್‌ಐಆರ್ {case['crimeNo']}ಗಾಗಿ {len(scout_claims)} ಮೂಲ-ಸಂಬಂಧಿತ ಕಂಡುಹಿಡಿಕೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿದೆ. "
            f"ಸಂದೇಹ ಪರಿಶೀಲನೆ {len(skeptic_reviews)} ಕಂಡುಹಿಡಿಕೆಗಳ ಅನಿಶ್ಚಿತತೆಯನ್ನು ದಾಖಲಿಸಿದೆ. ಇದು ಪರಿಶೀಲನಾ ಕರಡು ಮಾತ್ರ; "
            "ಅಧಿಕಾರಿ ಉಲ್ಲೇಖಿತ ಮೂಲಗಳನ್ನು ಪರಿಶೀಲಿಸಿ ಅನುಮೋದಿಸುವವರೆಗೆ ಯಾವುದೇ ಕಾರ್ಯಾಚರಣೆಗೆ ಅನುಮತಿ ಇಲ್ಲ."
        )
    else:
        answer = (
            f"{workflow_name} reviewed {len(scout_claims)} source-linked findings for FIR {case['crimeNo']}. "
            f"The skeptic check recorded uncertainty for {len(skeptic_reviews)} findings. This is a review draft only; "
            "no operational action is authorized until an officer verifies the cited sources and approves it."
        )
    tools_used = fallback_tools_used
    if model_result is not None:
        called_source_ids = set()
        for tool in model_result.tools_used:
            called_source_ids.update(source_map.get(tool["name"], set()))
        try:
            answer, scout_claims, skeptic_reviews, actions = validate_model_agent_draft(
                model_result.output, called_source_ids,
                set(workflow_spec.action_types) if workflow_spec else None,
            )
            tools_used = model_result.tools_used
        except ValueError as exc:
            model_warning = f"Model draft failed evidence validation; deterministic evidence workflow used ({type(exc).__name__})."
            model_result = None
    answer = minimize_agent_value(answer)
    for claim in scout_claims:
        claim["statement"] = minimize_agent_value(claim["statement"])
    for review in skeptic_reviews:
        review["verdict"] = minimize_agent_value(review["verdict"])
        review["challenge"] = minimize_agent_value(review["challenge"])
    for action in actions:
        action["title"] = minimize_agent_value(action["title"])
        action["reason"] = minimize_agent_value(action["reason"])
    is_patrol_brief = bool(workflow_spec and workflow_spec.id == "patrol-shift-briefing")
    if is_patrol_brief:
        answer = (
            "The patrol shift briefing reviewed recorded location priorities and current review triggers. "
            "Confirm recency, operational relevance, unit availability, and supervisor authorization before deployment."
        )
        for review in skeptic_reviews:
            review["challenge"] = (
                "A recorded location priority may be historical or analytical. Verify current conditions and command authorization before deployment."
            )
    plan_fingerprint = hashlib.sha256(json.dumps({
        "caseId": request.caseId, "role": role, "query": request.query.strip(),
        "claims": scout_claims, "reviews": skeptic_reviews, "actions": actions,
    }, sort_keys=True).encode()).hexdigest()[:16]
    used_tool_names = [item["name"] for item in tools_used]
    stages = [{
        "id": "scout", "name": "Scout Agent", "status": "completed",
        "summary": f"Assembled {len(scout_claims)} source-linked candidate claims.",
        "toolNames": [name for name in used_tool_names if name != "data_quality_review"],
    }, {
        "id": "skeptic", "name": "Skeptic Agent", "status": "completed",
        "summary": f"Reviewed {len(skeptic_reviews)} claims and attached challenges or alternative explanations.",
        "toolNames": [name for name in used_tool_names if name in {"data_quality_review", "case_link_review"}],
    }, {
        "id": "commander", "name": "Commander Agent", "status": "awaiting human review",
        "summary": f"Drafted {len(actions)} bounded review actions; execution is unavailable to the agent.",
        "toolNames": [],
    }]
    run = {
        "runId": f"AGT-{uuid.uuid4().hex[:10].upper()}",
        "agentId": workflow_spec.id if workflow_spec else "case-investigator",
        "agentName": workflow_spec.name if workflow_spec else "Drishti Case Investigator",
        "caseId": request.caseId,
        "role": role,
        "query": request.query.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "planFingerprint": plan_fingerprint,
        "toolsUsed": tools_used,
        "citationCount": len(visible_citations),
        "status": "awaiting human review",
        "stages": stages,
        "aiProvider": model_result.provider if model_result else "deterministic-fallback",
        "aiModel": model_result.model if model_result else "deterministic-fallback",
        "modelResponseId": model_result.response_id if model_result else None,
        "tokenUsage": model_result.usage if model_result else {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
    }
    previous_audit_hash = agent_run_log[0]["auditHash"] if agent_run_log else "GENESIS"
    if previous_audit_hash == "GENESIS" and data_source_status["active"] == "catalyst":
        try:
            persisted_runs = catalyst_store.fetch_workflow_rows("agent_runs")
            if persisted_runs:
                latest_run = max(persisted_runs, key=lambda row: str(row.get("CreatedAt", "")))
                previous_audit_hash = str(latest_run.get("AuditHash") or "GENESIS")
        except Exception:
            pass
    run["previousAuditHash"] = previous_audit_hash
    run["auditHash"] = hashlib.sha256(json.dumps({
        "previousAuditHash": previous_audit_hash,
        "runId": run["runId"],
        "caseId": run["caseId"],
        "role": run["role"],
        "timestamp": run["timestamp"],
        "planFingerprint": run["planFingerprint"],
        "status": run["status"],
    }, sort_keys=True).encode()).hexdigest()
    if data_source_status["active"] == "catalyst":
        try:
            catalyst_store.insert_workflow_row("agent_runs", {
                "RunID": run["runId"], "CaseID": run["caseId"], "Role": run["role"],
                "QueryHash": hashlib.sha256(run["query"].encode()).hexdigest(),
                "PlanFingerprint": run["planFingerprint"],
                "PreviousAuditHash": run["previousAuditHash"], "AuditHash": run["auditHash"],
                "Tools": [f"agent:{run['agentId']}"] + [item["name"] for item in tools_used],
                "CitationCount": run["citationCount"], "Status": run["status"],
                "AIProvider": run["aiProvider"], "AIModel": run["aiModel"],
                "ModelResponseID": run["modelResponseId"], "TokenUsage": run["tokenUsage"],
                "CreatedAt": run["timestamp"],
            })
            run["auditPersistence"] = "Catalyst append-only workflow table"
        except Exception as exc:
            run["auditPersistenceWarning"] = str(exc)
    else:
        run["auditPersistence"] = "development in-memory ledger"
    agent_run_log.insert(0, run)
    del agent_run_log[200:]
    return {
        "run": run,
        "agent": workflow_spec.public_dict() if workflow_spec else {
            "id": "case-investigator", "name": "Drishti Case Investigator",
            "surface": "case-workspace", "requiresCase": True,
        },
        "answer": answer,
        "case": {
            "caseId": case["caseId"],
            "crimeNo": "Restricted shift context" if is_patrol_brief else case["crimeNo"],
            "district": case["district"],
            "crimeType": "Recorded incident priority" if is_patrol_brief else case["crimeType"],
        },
        "toolsUsed": tools_used,
        "citations": visible_citations,
        "stages": stages,
        "claims": scout_claims,
        "skepticReviews": skeptic_reviews,
        "recommendedActions": actions,
        "actionDraft": {
            "caseId": request.caseId,
            "actionType": f"agent-{workflow_spec.id if workflow_spec else 'investigation'}-review",
            "rationale": f"Agent review draft {plan_fingerprint}: verify cited evidence before any coordination.",
            "approved": False,
        },
        "guardrails": [
            "The agent uses only allowlisted Drishti case-analysis tools.",
            "Links and summaries are decision support, not proof of involvement or guilt.",
            "The agent cannot dispatch personnel, send messages, create an FIR, or approve an action.",
            "A named human officer must verify cited source records and approve every operational action.",
        ],
        "environmentNotice": "Generated narrative masks direct phone, vehicle, and 12-digit identity values. The prototype enforces its declared demo role server-side; production derives role and scope from authenticated Catalyst identity claims, never from a browser-supplied value.",
        "privacy": {
            "mode": "minimum necessary output",
            "masked": ["phone identifiers", "vehicle identifiers", "12-digit identity numbers"],
            "notice": "The agent reasons over authorized source records but masks direct identifiers in generated narrative output by default.",
        },
        "model": {
            "provider": run["aiProvider"], "name": run["aiModel"],
            "responseId": run["modelResponseId"], "tokenUsage": run["tokenUsage"],
            "warning": model_warning,
        },
    }


@app.post("/api/agent/investigate")
def investigate_with_agent(request: InvestigationAgentRequest):
    return run_investigation_agent(request)


@app.get("/api/agents")
def get_agent_catalog(role: Optional[str] = Query(default=None)):
    """Return the bounded agent catalog, optionally filtered to one demo role."""
    agents = agent_catalog.AGENTS if not role else agent_catalog.agents_for_role(role)
    return {
        "agents": [agent.public_dict() for agent in agents],
        "count": len(agents),
        "guardrail": "Agents prepare source-linked drafts only. They cannot contact anyone, modify a record, dispatch personnel, or approve an action.",
        "model": ai_agent.model_configuration(),
    }


def _default_agent_case_id() -> int:
    priority = lifecycle_priority(districtId=None, limit=1).get("cases", [])
    if priority:
        return int(priority[0]["caseId"])
    if df_case is None or df_case.empty:
        raise HTTPException(status_code=503, detail="No case records are available for agent context")
    return int(df_case.sort_values("CrimeRegisteredDate", ascending=False).iloc[0]["CaseMasterID"])


@app.post("/api/agents/run")
def run_agent_workflow(request: AgentWorkflowRequest):
    """Run one catalog agent inside the shared citation, privacy, and approval boundary."""
    spec = agent_catalog.get_agent(request.agentId)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown Drishti agent workflow")
    role = request.role.strip().lower()
    if role not in spec.roles:
        raise HTTPException(status_code=403, detail="This role is not permitted to run the selected agent")
    if spec.requires_case and request.caseId is None:
        raise HTTPException(status_code=422, detail="Select a case before running this agent")
    case_id = int(request.caseId or _default_agent_case_id())
    query = (request.query or spec.default_prompt).strip()
    if request.context:
        minimized_context = redact_agent_text(json.dumps(request.context, ensure_ascii=False, default=str))[:2000]
        query = f"{query}\nOfficer-provided context (unverified until checked): {minimized_context}"
    language = request.language.strip().lower()
    if language not in {"en", "kn"}:
        language = "en"
    if language == "kn":
        query = f"Respond in Kannada, keeping record identifiers unchanged. {query}"
    result = run_investigation_agent(
        InvestigationAgentRequest(caseId=case_id, role=role, query=query, language=language),
        workflow_spec=spec,
    )
    result["contextSelection"] = {
        "requestedCaseId": request.caseId,
        "resolvedCaseId": case_id,
        "automatic": request.caseId is None,
        "notice": "A priority case supplies source context for this shift-level workflow." if request.caseId is None else "Officer-selected case context.",
    }
    result["agentUx"] = {
        "beforeRun": f"{spec.name} may read: {', '.join(spec.tools)}.",
        "progressSteps": ["Reading authorized records", "Checking source quality", "Challenging weak findings", "Preparing human-review draft"],
        "controls": ["add_to_checklist", "edit_draft", "request_review", "reject_suggestion", "view_sources"],
        "executionAvailable": False,
    }
    return result


@app.get("/api/agent/runs")
def get_agent_runs(caseId: Optional[int] = Query(None, ge=1)):
    """Read-only audit ledger of generated agent review drafts in this environment."""
    # FastAPI replaces ``Query`` when this endpoint is invoked over HTTP, but
    # internal command-centre/history calls invoke the function directly.
    # Treat the descriptor as the endpoint's intended ``None`` default.
    if not isinstance(caseId, (int, type(None))):
        caseId = None
    if data_source_status["active"] == "catalyst":
        try:
            rows = catalyst_store.fetch_workflow_rows("agent_runs")
            runs = [{
                "runId": row.get("RunID"), "caseId": int(row.get("CaseID", 0)),
                "role": row.get("Role"), "queryHash": row.get("QueryHash"),
                "planFingerprint": row.get("PlanFingerprint"),
                "previousAuditHash": row.get("PreviousAuditHash"), "auditHash": row.get("AuditHash"),
                "tools": row.get("Tools", []), "citationCount": int(row.get("CitationCount", 0)),
                "aiProvider": row.get("AIProvider") or "deterministic-fallback",
                "aiModel": row.get("AIModel"), "modelResponseId": row.get("ModelResponseID"),
                "tokenUsage": row.get("TokenUsage") or {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
                "status": row.get("Status"), "timestamp": row.get("CreatedAt"),
            } for row in rows]
            for run in runs:
                raw_tools = run.get("tools")
                if isinstance(raw_tools, str):
                    try:
                        raw_tools = json.loads(raw_tools)
                    except Exception:
                        raw_tools = [raw_tools]
                raw_tools = list(raw_tools or [])
                marker = next((item for item in raw_tools if str(item).startswith("agent:")), None)
                run["agentId"] = str(marker).split(":", 1)[1] if marker else "case-investigator"
                run["tools"] = [item for item in raw_tools if not str(item).startswith("agent:")]
            return {"runs": runs if caseId is None else [run for run in runs if run["caseId"] == caseId], "notice": "Catalyst append-only agent audit ledger."}
        except Exception:
            pass
    runs = agent_run_log if caseId is None else [run for run in agent_run_log if run["caseId"] == caseId]
    return {"runs": runs, "notice": "Development audit ledger. Production deployments persist this immutable event stream in a governed audit store."}


@app.get("/api/agent/sentinel")
def get_agent_sentinel(
    districtId: Optional[int] = Query(default=None),
    limit: int = Query(default=6, ge=1, le=12),
):
    """Surface proactive, evidence-backed review triggers without taking action."""
    # Keep the function directly testable outside FastAPI's dependency parser.
    if not isinstance(districtId, (int, type(None))):
        districtId = None
    if not isinstance(limit, int):
        limit = 6
    anomaly_rows = compute_monthly_anomalies(limit=8)
    if districtId is not None:
        anomaly_rows = [row for row in anomaly_rows if row["districtId"] == districtId]
    delay_rows = lifecycle_priority(districtId=districtId, limit=min(limit, 8))["cases"]
    triggers = []
    for row in anomaly_rows[:3]:
        lead_case = row["cases"][0] if row["cases"] else None
        triggers.append({
            "id": f"SENT-ANOM-{row['districtId']}-{re.sub(r'[^A-Z0-9]', '', row['crimeType'].upper())[:12]}",
            "category": "volume anomaly",
            "severity": "high review" if row["ratio"] >= 3 else "review",
            "title": f"{row['crimeType']} change in {row['district']}",
            "rationale": f"{row['count']} FIRs in {row['period']} versus a 12-month mean of {row['baselineMean']} ({row['ratio']}×).",
            "caseId": lead_case["id"] if lead_case else None,
            "source": "12-month district/offence baseline and current complete-month FIR volume",
            "humanReviewRequired": True,
        })
    for row in delay_rows[:3]:
        triggers.append({
            "id": f"SENT-DELAY-{row['caseId']}",
            "category": "case-delay prevention",
            "severity": "high review" if row["delayRisk"] >= 70 else "review",
            "title": f"FIR {row['crimeNo']} needs lifecycle review",
            "rationale": f"Process-delay score {row['delayRisk']}% · {' · '.join(row['signals'])}.",
            "caseId": row["caseId"],
            "source": "Historical FIR lifecycle model and recorded case-stage links",
            "humanReviewRequired": True,
        })
    triggers.sort(key=lambda item: (item["severity"] == "high review", item["category"] == "case-delay prevention"), reverse=True)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": get_district_name(districtId) if districtId else "Karnataka",
        "status": "monitoring synthetic development records",
        "triggers": triggers[:limit],
        "guardrail": "Sentinel creates review triggers only. It does not predict individual behaviour, accuse a person, dispatch personnel, or alter a case.",
    }


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


TASK_STATUSES = {"open", "in_progress", "awaiting_supervisor", "completed", "returned"}
TASK_PRIORITIES = {"urgent", "high", "normal", "low"}


class InvestigationTaskRequest(BaseModel):
    caseId: int
    title: str
    detail: str
    owner: str
    dueDate: str
    priority: str = "normal"
    sourceIds: list[str] = Field(default_factory=list)
    agentId: Optional[str] = None
    agentRunId: Optional[str] = None
    createdBy: str = "Authorized officer"


class TaskStatusRequest(BaseModel):
    status: str
    officer: str = "Authorized officer"
    note: str = ""
    role: str = "station"


class EvidenceVerificationRequest(BaseModel):
    officer: str
    role: str = "station"
    status: str = "verified"
    note: str = ""


def _append_workflow_event(action_type, case_id, payload, status):
    timestamp = datetime.now(timezone.utc).isoformat()
    event_id = f"EVT-{uuid.uuid4().hex[:14].upper()}"
    entry = {
        "actionId": event_id, "caseId": int(case_id), "actionType": action_type,
        "rationale": json.dumps(payload, ensure_ascii=False), "eventPayload": payload,
        "status": status, "timestamp": timestamp,
    }
    operational_action_log.append(entry)
    if data_source_status["active"] == "catalyst":
        try:
            catalyst_store.insert_workflow_row("actions", {
                "ActionID": event_id, "CaseID": int(case_id), "ActionType": action_type,
                "Rationale": payload, "Approved": status in {"completed", "verified", "approved"},
                "Status": status, "CreatedAt": timestamp,
            })
            entry["auditPersistence"] = "Catalyst append-only workflow table"
        except Exception as exc:
            entry["persistenceWarning"] = str(exc)
    return entry


def _read_workflow_events(prefix=None, case_id=None):
    rows = []
    if data_source_status["active"] == "catalyst":
        try:
            rows = catalyst_store.fetch_workflow_rows("actions")
            rows = [{
                "actionId": str(row.get("ActionID", "")), "caseId": int(row.get("CaseID", 0)),
                "actionType": str(row.get("ActionType") or ""), "rationale": row.get("Rationale"),
                "status": str(row.get("Status") or ""), "timestamp": str(row.get("CreatedAt") or ""),
            } for row in rows]
        except Exception:
            rows = list(operational_action_log)
    else:
        rows = list(operational_action_log)
    normalized = []
    for row in rows:
        action_type = str(row.get("actionType") or "")
        if prefix and not action_type.startswith(prefix):
            continue
        if case_id is not None and int(row.get("caseId", 0)) != int(case_id):
            continue
        payload = row.get("eventPayload")
        if payload is None:
            raw = row.get("rationale")
            if isinstance(raw, dict):
                payload = raw
            elif isinstance(raw, str):
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = {"note": raw}
        item = dict(row)
        item["eventPayload"] = payload or {}
        normalized.append(item)
    return sorted(normalized, key=lambda item: str(item.get("timestamp") or ""))


@app.post("/api/tasks")
def create_investigation_task(request: InvestigationTaskRequest):
    if df_case[df_case["CaseMasterID"] == request.caseId].empty:
        raise HTTPException(status_code=404, detail="Case not found")
    if request.priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=422, detail="Choose a valid task priority")
    if not (4 <= len(request.title.strip()) <= 180 and 8 <= len(request.detail.strip()) <= 1200):
        raise HTTPException(status_code=422, detail="Provide a clear task title and detail")
    if not request.owner.strip():
        raise HTTPException(status_code=422, detail="Assign an accountable task owner")
    if request.agentId and not request.sourceIds:
        raise HTTPException(status_code=422, detail="Agent-suggested tasks require at least one cited source")
    try:
        due_date = datetime.fromisoformat(request.dueDate.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Provide the due date in ISO format") from exc
    task_id = f"TSK-{uuid.uuid4().hex[:10].upper()}"
    payload = {
        "taskId": task_id, "title": redact_agent_text(request.title.strip()),
        "detail": redact_agent_text(request.detail.strip()), "owner": redact_agent_text(request.owner.strip())[:120],
        "dueDate": due_date, "priority": request.priority, "sourceIds": request.sourceIds[:8],
        "agentId": request.agentId, "agentRunId": request.agentRunId,
        "createdBy": redact_agent_text(request.createdBy.strip())[:120],
    }
    event = _append_workflow_event("task-created", request.caseId, payload, "open")
    return {**payload, "caseId": request.caseId, "status": "open", "createdAt": event["timestamp"], "auditEventId": event["actionId"]}


@app.post("/api/tasks/{task_id}/status")
def update_investigation_task(task_id: str, request: TaskStatusRequest):
    tasks = {task["taskId"]: task for task in get_investigation_tasks()["tasks"]}
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Investigation task not found")
    if request.status not in TASK_STATUSES:
        raise HTTPException(status_code=422, detail="Choose a valid task status")
    if request.status in {"completed", "returned"} and request.role not in {"command", "district"}:
        raise HTTPException(status_code=403, detail="A supervisor role must record this decision")
    allowed_transitions = {
        "open": {"in_progress"}, "returned": {"in_progress"},
        "in_progress": {"awaiting_supervisor"},
        "awaiting_supervisor": {"completed", "returned"},
        "completed": set(),
    }
    if request.status not in allowed_transitions.get(task["status"], set()):
        raise HTTPException(
            status_code=409,
            detail=f"Task cannot move from {task['status']} to {request.status}",
        )
    payload = {
        "taskId": task_id, "status": request.status,
        "officer": redact_agent_text(request.officer.strip())[:120],
        "role": request.role, "note": redact_agent_text(request.note.strip())[:800],
    }
    event = _append_workflow_event("task-status", task["caseId"], payload, request.status)
    return {**payload, "caseId": task["caseId"], "timestamp": event["timestamp"], "auditEventId": event["actionId"]}


@app.get("/api/tasks")
def get_investigation_tasks(caseId: Optional[int] = Query(default=None), status: Optional[str] = Query(default=None)):
    if not isinstance(caseId, (int, type(None))):
        caseId = None
    if not isinstance(status, (str, type(None))):
        status = None
    events = _read_workflow_events("task-", caseId)
    tasks = {}
    for event in events:
        payload = event["eventPayload"]
        task_id = str(payload.get("taskId") or "")
        if not task_id:
            continue
        if event["actionType"] == "task-created":
            tasks[task_id] = {**payload, "caseId": event["caseId"], "status": "open", "createdAt": event["timestamp"], "history": []}
        elif task_id in tasks:
            tasks[task_id]["status"] = payload.get("status", event["status"])
            tasks[task_id]["updatedAt"] = event["timestamp"]
            tasks[task_id]["history"].append({**payload, "timestamp": event["timestamp"], "auditEventId": event["actionId"]})
    values = sorted(tasks.values(), key=lambda item: (item.get("dueDate", ""), item.get("createdAt", "")))
    if status:
        values = [item for item in values if item["status"] == status]
    return {"tasks": values, "count": len(values), "notice": "Task state is reconstructed from append-only workflow events."}


@app.post("/api/evidence/{evidence_id}/verify")
def verify_evidence_custody(evidence_id: str, request: EvidenceVerificationRequest):
    records = {record["id"]: record for record in list_development_evidence()["records"]}
    record = records.get(evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Evidence metadata record not found")
    if request.status not in {"verified", "returned"}:
        raise HTTPException(status_code=422, detail="Choose verified or returned")
    if request.role not in {"command", "district"}:
        raise HTTPException(status_code=403, detail="A supervisor role must record the custody decision")
    payload = {
        "evidenceId": evidence_id, "status": request.status,
        "officer": redact_agent_text(request.officer.strip())[:120],
        "role": request.role, "note": redact_agent_text(request.note.strip())[:800],
    }
    event = _append_workflow_event("evidence-status", record["caseId"], payload, request.status)
    return {**payload, "caseId": record["caseId"], "timestamp": event["timestamp"], "auditEventId": event["actionId"]}


@app.get("/api/cases/{case_id}/agent-history")
def get_case_agent_history(case_id: int):
    if df_case[df_case["CaseMasterID"] == case_id].empty:
        raise HTTPException(status_code=404, detail="Case not found")
    runs = sorted(get_agent_runs(caseId=case_id)["runs"], key=lambda item: str(item.get("timestamp") or ""), reverse=True)
    events = _read_workflow_events(case_id=case_id)
    last_run_at = str(runs[0].get("timestamp") or "") if runs else None
    changes = [event for event in events if not last_run_at or str(event.get("timestamp") or "") > last_run_at]
    change_types = {
        "tasks": sum(event["actionType"].startswith("task-") for event in changes),
        "evidence": sum(event["actionType"].startswith("evidence-") for event in changes),
        "reviews": sum(not event["actionType"].startswith(("task-", "evidence-")) for event in changes),
    }
    return {
        "caseId": case_id, "runs": runs[:20], "lastRunAt": last_run_at,
        "changesSinceLastRun": {"total": len(changes), **change_types},
        "recentChanges": [{
            "eventId": event["actionId"], "type": event["actionType"], "status": event["status"],
            "timestamp": event["timestamp"], "summary": event["eventPayload"].get("title") or event["eventPayload"].get("note") or event["actionType"],
        } for event in changes[-12:][::-1]],
        "notice": "Changes are derived from append-only task, evidence, and review events recorded after the latest agent run.",
    }


@app.get("/api/supervisor/command-centre")
def get_supervisor_command_centre(role: str = Query("district")):
    if role not in {"command", "district"}:
        raise HTTPException(status_code=403, detail="Supervisor access is required")
    tasks = get_investigation_tasks()["tasks"]
    today = datetime.now(timezone.utc).date().isoformat()
    overdue = [task for task in tasks if task["status"] not in {"completed"} and task.get("dueDate", "9999-12-31") < today]
    awaiting = [task for task in tasks if task["status"] == "awaiting_supervisor"]
    coordination = [task for task in tasks if task.get("agentId") == "district-coordination" and task["status"] != "completed"]
    priority = lifecycle_priority(districtId=None, limit=8).get("cases", [])
    weak_links = []
    for case_row in priority[:5]:
        link_result = get_case_links(int(case_row["caseId"]), top_n=1)
        if not link_result["relatedCases"]:
            continue
        link = link_result["relatedCases"][0]
        weak_links.append({
            "caseId": int(case_row["caseId"]), "crimeNo": case_row["crimeNo"],
            "linkedCrimeNo": link["crimeNo"], "connectionScore": link["connectionScore"],
            "verificationRequired": True,
        })
    quality = data_quality_command_centre(districtId=None)
    recent_runs = sorted(get_agent_runs()["runs"], key=lambda item: str(item.get("timestamp") or ""), reverse=True)[:10]
    return {
        "summary": {
            "awaitingDecision": len(awaiting), "overdueTasks": len(overdue),
            "coordinationDrafts": len(coordination), "weakLinks": len(weak_links),
            "qualityScore": quality["qualityScore"], "recentAgentRuns": len(recent_runs),
        },
        "awaitingTasks": awaiting[:12], "overdueTasks": overdue[:12],
        "coordinationDrafts": coordination[:8], "weakLinks": weak_links,
        "dataQuality": {"score": quality["qualityScore"], "checks": quality["checks"], "recommendations": quality["recommendations"]},
        "recentAgentRuns": recent_runs,
        "guardrail": "Supervisor decisions are recorded human actions. Agents cannot complete tasks, verify custody, or authorize coordination.",
    }


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
                "actionId": str(row.get("ActionID", "")), "caseId": int(row.get("CaseID", 0)),
                "actionType": row.get("ActionType"), "rationale": row.get("Rationale"),
                "status": row.get("Status"), "timestamp": row.get("CreatedAt"),
            } for row in rows if not str(row.get("ActionType") or "").startswith(("task-", "evidence-"))]
            return {"actions": actions if caseId is None else [item for item in actions if item["caseId"] == caseId]}
        except Exception:
            pass
    if caseId is None:
        return {"actions": [entry for entry in operational_action_log if not str(entry.get("actionType") or "").startswith(("task-", "evidence-"))]}
    return {"actions": [entry for entry in operational_action_log if entry['caseId'] == caseId and not str(entry.get("actionType") or "").startswith(("task-", "evidence-"))]}

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


def _point_on_segment(lng, lat, start, end, epsilon=1e-9):
    """Return True when a point lies on a GeoJSON line segment."""
    x1, y1 = start[0], start[1]
    x2, y2 = end[0], end[1]
    cross_product = (lng - x1) * (y2 - y1) - (lat - y1) * (x2 - x1)
    if abs(cross_product) > epsilon:
        return False
    return min(x1, x2) - epsilon <= lng <= max(x1, x2) + epsilon and min(y1, y2) - epsilon <= lat <= max(y1, y2) + epsilon


def _point_in_ring(lng, lat, ring):
    """Ray-casting point-in-polygon check for one GeoJSON linear ring."""
    inside = False
    for index in range(len(ring) - 1):
        start, end = ring[index], ring[index + 1]
        if _point_on_segment(lng, lat, start, end):
            return True
        x1, y1 = start[0], start[1]
        x2, y2 = end[0], end[1]
        if (y1 > lat) != (y2 > lat):
            intersection_lng = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lng < intersection_lng:
                inside = not inside
    return inside


def _point_in_geojson_geometry(lng, lat, geometry):
    """Check a point against Polygon or MultiPolygon GeoJSON, including holes."""
    if not geometry:
        return False
    polygons = [geometry.get("coordinates", [])] if geometry.get("type") == "Polygon" else geometry.get("coordinates", [])
    for polygon in polygons:
        if not polygon or not _point_in_ring(lng, lat, polygon[0]):
            continue
        if not any(_point_in_ring(lng, lat, hole) for hole in polygon[1:]):
            return True
    return False


def point_is_within_selected_district(latitude, longitude, district_id):
    """Accept only coordinates inside the selected district's official map boundary."""
    try:
        lat, lng = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return False
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return False
    district_name = get_district_name(district_id)
    geometry = district_geometry_cache.get(district_name)
    if geometry is None:
        with open(os.path.join(OUTPUT_DIR, "karnataka_districts.geojson"), "r", encoding="utf-8") as source:
            features = json.load(source).get("features", [])
        feature = next((item for item in features if str(item.get("properties", {}).get("NAME_2", "")).lower() == district_name.lower()), None)
        geometry = feature.get("geometry") if feature else False
        district_geometry_cache[district_name] = geometry
    return bool(geometry) and _point_in_geojson_geometry(lng, lat, geometry)


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
    geocoded_case_count = int(len(recent))
    within_district = [
        point_is_within_selected_district(latitude, longitude, districtId)
        for latitude, longitude in zip(recent['latitude'], recent['longitude'])
    ]
    recent = recent.loc[within_district].copy()
    excluded_coordinate_count = geocoded_case_count - int(len(recent))
    if recent.empty:
        raise HTTPException(status_code=404, detail="No recent FIR coordinates fall inside the selected district boundary")
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
        "coordinateScope": {
            "label": f"{get_district_name(districtId)} only",
            "accepted": int(len(recent)),
            "excludedOutsideBoundary": excluded_coordinate_count,
        },
        "coverageIndex": scenario_coverage, "baselineCoverageIndex": baseline_coverage,
        "coverageDelta": round(scenario_coverage - baseline_coverage, 1), "zones": zones,
        "scenario": {"heinousWeight": heinousWeight, "recencyWeight": recencyWeight, "shiftStart": shiftStart, "shiftEnd": shiftEnd},
        "method": "Uses only FIR coordinates inside the selected district boundary from the last 90 days for the selected shift. Coordinates outside that boundary are excluded. The deployment focus gives more attention to either recent activity or serious offences; the balanced plan considers both.",
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
