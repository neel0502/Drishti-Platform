from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import os
import json
import random
from datetime import datetime, timedelta

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

def load_data():
    global df_case, df_accused, df_victim, df_complainant, df_arrest, df_chargesheet
    global df_district, df_unit, df_crime_head, df_crime_subhead, df_status, df_occupation
    global pattern_a_case_ids, pattern_b_case_ids, pattern_c_case_ids
    
    print("Loading data files...")
    df_case = pd.read_csv(os.path.join(OUTPUT_DIR, "CaseMaster.csv"), encoding="utf-8")
    df_accused = pd.read_csv(os.path.join(OUTPUT_DIR, "Accused.csv"), encoding="utf-8")
    df_victim = pd.read_csv(os.path.join(OUTPUT_DIR, "Victim.csv"), encoding="utf-8")
    df_complainant = pd.read_csv(os.path.join(OUTPUT_DIR, "ComplainantDetails.csv"), encoding="utf-8")
    df_arrest = pd.read_csv(os.path.join(OUTPUT_DIR, "ArrestSurrender.csv"), encoding="utf-8")
    df_chargesheet = pd.read_csv(os.path.join(OUTPUT_DIR, "ChargesheetDetails.csv"), encoding="utf-8")
    
    df_district = pd.read_csv(os.path.join(OUTPUT_DIR, "District.csv"), encoding="utf-8")
    df_unit = pd.read_csv(os.path.join(OUTPUT_DIR, "Unit.csv"), encoding="utf-8")
    df_crime_head = pd.read_csv(os.path.join(OUTPUT_DIR, "CrimeHead.csv"), encoding="utf-8")
    df_crime_subhead = pd.read_csv(os.path.join(OUTPUT_DIR, "CrimeSubHead.csv"), encoding="utf-8")
    df_status = pd.read_csv(os.path.join(OUTPUT_DIR, "CaseStatusMaster.csv"), encoding="utf-8")
    df_occupation = pd.read_csv(os.path.join(OUTPUT_DIR, "OccupationMaster.csv"), encoding="utf-8")
    
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

    # Enrich DataFrames with vehicle and phone columns
    df_case['phone'] = None
    df_case['vehicle'] = None
    
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

@app.on_event("startup")
def startup_event():
    load_data()
    build_network_graph()
    build_nlp_index()

# ─── API ENDPOINTS ────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard():
    # Since dataset is historical, set "current" simulation date to end of dataset
    max_date_str = df_case['CrimeRegisteredDate'].max()
    current_date = datetime.strptime(max_date_str, "%Y-%m-%d")
    
    # Crimes this month (Dec 2024)
    latest_ym = "2024-12"
    prev_ym = "2024-11"
    
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
    
    # Districts Needing Attention
    # Spikes: Bangalore Urban (Pattern A), Raichur (Kidnapping), Kolar
    attention_districts = {
        "value": 3,
        "districts": "Bangalore Urban · Raichur · Kolar",
        "label": "Action Required"
    }
    
    # Alerts Summary
    alerts = [
        {
            "id": "raichur-kidnap",
            "severity": "urgent",
            "title": "Unusual spike in Raichur",
            "description": "3 kidnappings in 2 days — 6× higher than normal",
            "link": "alerts"
        },
        {
            "id": "kiran-kumar-active",
            "severity": "watch",
            "title": "Repeat offender active — Bangalore",
            "description": "Kiran Kumar linked to 14 burglaries, last seen Belagavi",
            "link": "profiles"
        },
        {
            "id": "burglary-syndicate",
            "severity": "watch",
            "title": "Same break-in method — 3 districts",
            "description": "5 burglaries likely by same group — same drill MO",
            "link": "networks"
        }
    ]
    
    # Monthly counts for 24 months (2023-01 to 2024-12)
    df_case['ym'] = df_case['CrimeRegisteredDate'].astype(str).str.slice(0, 7)
    trend_data = df_case[df_case['ym'] >= "2023-01"].groupby('ym').size().sort_index()
    
    return {
        "morningBrief": f"Karnataka recorded 847 crimes yesterday. Bangalore Urban and Raichur require immediate attention today.",
        "kpi": {
            "crimesThisMonth": {
                "value": cases_this_month,
                "delta": delta_text,
                "deltaColor": delta_color,
                "sparkline": [11200, 11800, 11500, 12100, cases_prev_month, cases_this_month]
            },
            "casesSolved": {
                "value": resolved_count,
                "rate": f"{resolution_rate}% resolution rate",
                "comparison": "Better than last year (52%)",
                "comparisonColor": "green"
            },
            "arrestsMade": {
                "value": arrests_count,
                "subtext": f"{int(len(df_arrest[df_arrest['ArrestSurrenderDate'].astype(str).str.startswith('2024-12')]))} this month · 234 heinous crime arrests"
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
        props['crimeCount'] = int(c_count)
        props['districtId'] = int(matched_id) if matched_id else None
        props['districtName'] = district_names.get(matched_id, dist_name)
        props['trend'] = "+12% spike" if matched_id in [1, 12] else "Stable"
        props['pulsing'] = True if matched_id in [1, 12, 27] else False  # Bangalore, Raichur, Kolar
        
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
            "facts": str(r['BriefFacts']),
            "districtId": int(r['_DistrictID'])
        })
        
    # Hourly crime distribution
    hours = pd.to_datetime(df_case['IncidentFromDate']).dt.hour
    hourly_distribution = hours.value_counts().reindex(range(24), fill_value=0).tolist()
    
    return {
        "geojson": geojson_data,
        "incidents": incidents,
        "hourlyDistribution": hourly_distribution
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
        results["phones"].append({
            "number": "📱 +91 98450 12345",
            "caseCount": len(phone_cases),
            "owner": "Ramesh Naik (per FIR records)",
            "districts": "Bangalore Urban · Mysuru · Belagavi",
            "warning": "⚠️ Appears under 3 different names — possible shared gang phone",
            "cases": clean_list(phone_cases[['CaseMasterID', 'CrimeNo', 'CrimeRegisteredDate', '_SubheadName']].rename(columns={'_SubheadName': 'type'}).to_dict(orient='records'))
        })
        
    # 2. Search Vehicles
    if "ka-05" in q or "mx" in q or "1234" in q or "pulsar" in q:
        vehicle_cases = df_case[df_case['vehicle'] == "KA-05 MX 1234"]
        results["vehicles"].append({
            "plate": "🏍️ KA-05 MX 1234",
            "description": "Black Bajaj Pulsar",
            "caseCount": len(vehicle_cases),
            "crimeType": "Chain Snatching & House Burglary",
            "pattern": "Consistent pattern: Indiranagar area evening hours (6-9 PM) & Burglary Syndicate co-accused",
            "warning": "⚠️ Linked to 6 snatching incidents & 60 break-ins",
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
        acc_cases = df_accused[df_accused['AccusedName'] == name]['CaseMasterID'].tolist()
        case_rows = df_case[df_case['CaseMasterID'].isin(acc_cases)]
        
        is_high_risk = "Kiran Kumar" in name or "Ramesh Naik" in name or "Syed Ahmed" in name
        pills = ["HIGH RISK OFFENDER"] if is_high_risk else ["Suspect"]
        if len(acc_cases) > 3:
            pills.append("Repeat Offender")
            
        districts_seen = [get_district_name(d) for d in case_rows['_DistrictID'].unique()]
        
        associates = []
        if name in G:
            for neighbor in G.neighbors(name):
                weight = G[name][neighbor]['weight']
                if weight >= 2:
                    associates.append(neighbor)
                    
        results["people"].append({
            "name": name,
            "aliases": "Drill Kiran, Kiran Naik" if "Kiran Kumar" in name else "Night Ramesh" if "Ramesh" in name else "Tool Syed" if "Syed" in name else None,
            "age": int(matched_accused[matched_accused['AccusedName'] == name]['AgeYear'].iloc[0]),
            "gender": str(matched_accused[matched_accused['AccusedName'] == name]['GenderID'].iloc[0]),
            "status": "AT LARGE" if is_high_risk else "In Custody",
            "pills": pills,
            "caseCount": len(acc_cases),
            "districts": " · ".join(districts_seen),
            "crimeType": "House Burglary" if "Kiran" in name or "Ramesh" in name else "Chain Snatching" if "Raju" in name else "Assault",
            "associates": associates
        })

    # 4. Search Case / FIR Numbers
    matched_cases = df_case[
        df_case['CrimeNo'].astype(str).str.lower().str.contains(q, na=False) | 
        df_case['CaseNo'].astype(str).str.lower().str.contains(q, na=False)
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
    
    is_pattern_b = matched_name in ["Kiran Kumar alias Drill Kiran", "Ramesh Naik alias Night Ramesh", "Syed Ahmed alias Tool Syed"]
    
    age = int(acc_rows['AgeYear'].iloc[0])
    gender = str(acc_rows['GenderID'].iloc[0])
    
    phone = "98450-12345 (8 cases) · 76543-21098 (3 cases)" if is_pattern_b else "No phone records registered"
    vehicle = "KA-05 MX 1234 (Black Pulsar)" if is_pattern_b or "Raju" in matched_name else "No vehicle registered"
    aadhaar = "•••• •••• 3421" if is_pattern_b else "•••• •••• " + str(random.randint(1000, 9999))
    
    mo_desc = "Breaks into locked houses between midnight and 4 AM using a hand drill on front door locks. Targets homes when owners are travelling. Works in a group of 3." if is_pattern_b else "Snatches gold ornaments from lone walkers in evening hours, operating on a two-wheeler getaway vehicle."
    
    brother = "Suresh Naik — 2 NDPS cases" if is_pattern_b else "No direct criminal family records"
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
        "alias": "Drill Kiran" if "Kiran" in matched_name else "Night Ramesh" if "Ramesh" in matched_name else "Tool Syed" if "Syed" in matched_name else "Suspect Profile",
        "pills": ["HIGH RISK OFFENDER", "Repeat Offender"] if is_pattern_b else ["Repeat Offender"],
        "age": age,
        "gender": gender,
        "lastSeen": "Belagavi, November 2024" if is_pattern_b else "Bangalore Urban, December 2024",
        "status": "AT LARGE" if is_pattern_b else "In Custody",
        "contactInfo": {
            "aadhaar": aadhaar,
            "phone": phone,
            "vehicle": vehicle,
            "address": "Dharwad permanent address; active across Bangalore, Mysuru, Belagavi" if is_pattern_b else "Bangalore Urban"
        },
        "family": {
            "father": "Kumar Naik — No criminal record",
            "brother": brother,
            "associates": associates
        },
        "moDescription": mo_desc,
        "timeline": timeline,
        "movement": movement_coordinates
    }

@app.get("/api/networks")
def get_crime_networks(groupName: str = None):
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
    # Fetch some representative cases from Raichur (district 12) for the detail panel
    raichur_incidents = df_case[df_case['_DistrictID'] == 12].head(3)
    raichur_cases = []
    for _, r in raichur_incidents.iterrows():
        raichur_cases.append({
            "id": int(r['CaseMasterID']),
            "crimeNo": str(r['CrimeNo']),
            "date": str(r['CrimeRegisteredDate']),
            "facts": str(r['BriefFacts']),
            "lat": float(r['latitude']),
            "lng": float(r['longitude'])
        })
        
    return {
        "alerts": [
            {
                "id": "raichur-spike",
                "severity": "urgent",
                "title": "Kidnapping spike in Raichur",
                "timeText": "2 hours ago",
                "description": "3 kidnapping incidents registered within the last 48 hours. This is 6 times higher than the monthly average of 1 case.",
                "whatHappened": "Three kidnapping cases were registered in Raichur in the last 48 hours. Normally Raichur sees about 1 kidnapping per month. This week's count is 6 times higher than usual.",
                "cases": raichur_cases,
                "recommendedAction": "Suggested response: Deploy additional patrol units to Raichur North and Central zones. Issue lookout notice for suspects described in Case #RAI/26/0034."
            },
            {
                "id": "kiran-active",
                "severity": "watch",
                "title": "Known offender active again",
                "timeText": "1 day ago",
                "description": "Kiran Kumar was released on bail 3 months ago. 2 new burglaries matching his exact hand-drill method reported since.",
                "whatHappened": "Suspect Kiran Kumar alias Drill Kiran was released on bail in Mysuru. Within 90 days, two new burglaries using the silent wooden lock hand-drill method have been reported, suggesting re-offending activity.",
                "cases": [],
                "recommendedAction": "Suggested response: Issue alert to local beats in Bangalore and Mysuru. Coordinate with bail verification officer."
            },
            {
                "id": "cross-district-mo",
                "severity": "watch",
                "title": "Same break-in method — 5 cases, 3 districts",
                "timeText": "3 days ago",
                "description": "Burglaries matching the silent wooden hand-drill MO were logged in Bangalore and Belagavi. Highly likely a single group operating.",
                "whatHappened": "The NLP linkage engine grouped 5 burglaries across Bangalore and Belagavi with a cosine similarity > 92% based on BriefFacts descriptions. This confirms the movement of the burglary syndicate.",
                "cases": [],
                "recommendedAction": "Suggested response: Merge investigations under SCRB central task force. Track vehicles active near targeted coordinate locations."
            },
            {
                "id": "diwali-fraud",
                "severity": "watch",
                "title": "Diwali season — online fraud rising",
                "timeText": "Weekly update",
                "description": "Cyber utility bill frauds are rising in urban districts. Historically peaks during the October festival season.",
                "whatHappened": "A seasonal surge in cyber utility bill frauds has been detected, specifically targeting bank details of retired complainants via text links.",
                "cases": [],
                "recommendedAction": "Suggested response: Launch state-wide SMS awareness campaign targeting senior bank account holders. Monitor active IP gateways."
            },
            {
                "id": "mysuru-improving",
                "severity": "info",
                "title": "Mysuru improving — crime down 18%",
                "timeText": "Monthly summary",
                "description": "Violent crime declining for 3 months straight in Mysuru District.",
                "whatHappened": "Mysuru district has registered a steady 18% decline in violent body crimes over the last quarter, likely due to enhanced beat patrolling deployments.",
                "cases": [],
                "recommendedAction": "Suggested response: Maintain current beat officer deployments. Document best practices for translation to other districts."
            }
        ]
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
        is_at_large = name in ["Kiran Kumar alias Drill Kiran", "Ramesh Naik alias Night Ramesh", "Syed Ahmed alias Tool Syed", "Raju alias Splendor Raju", "Manoj Kumar", "Shiva alias Bike Shiva"]
        top_offenders.append({
            "name": name,
            "cases": int(count),
            "status": "AT LARGE" if is_at_large else "In Custody"
        })
        
    return {
        "districtName": dist_name,
        "casesCount": len(dist_cases),
        "percentageIncrease": "+12% vs last month" if district_id in [1, 12] else "-4% vs last month",
        "topCrimeType": "House Burglary" if district_id == 3 else "Vehicle Theft" if district_id == 1 else "Simple Assault",
        "stations": station_rows,
        "topOffenders": top_offenders
    }

# Serve Frontend static assets
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    print(f"Mounted frontend assets from: {FRONTEND_DIR}")
else:
    print(f"[WARN] Frontend directory not found at: {FRONTEND_DIR}. API server running stand-alone.")
