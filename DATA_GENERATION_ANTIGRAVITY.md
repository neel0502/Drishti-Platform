# KSP Drishti — Synthetic Data Generation
### Run entirely in Antigravity (Python notebook) · No setup needed

> **Schema:** Karnataka Police FIR ER Diagram  
> **Output:** 18 CSV files · ~50,000 FIR records · 3 injected criminal patterns  
> **Time to run:** ~3 minutes total

---

## How to Use This

Copy each code block into a **new Antigravity cell** in order.  
Run them top to bottom. That's it.

---

## Cell 1 — Install Dependencies

```python
!pip install faker pandas numpy tqdm -q
```

---

## Cell 2 — Imports & Seeds

```python
import pandas as pd
import numpy as np
import random
import os
from datetime import datetime, timedelta
from faker import Faker
from tqdm import tqdm

# Reproducible output — same data every run
fake = Faker('en_IN')
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Output folder
os.makedirs("output", exist_ok=True)
print("✅ Imports done")
```

---

## Cell 3 — Master Config

```python
# ─── DATE RANGE ───────────────────────────────────────────────
START_DATE = datetime(2022, 1, 1)
END_DATE   = datetime(2024, 12, 31)

# ─── VOLUME ───────────────────────────────────────────────────
N_CASES      = 50_000
N_EMPLOYEES  = 2_000
N_UNITS      = 180    # police stations

# ─── KARNATAKA DISTRICTS (all 31, real coords + population weight) ──
DISTRICTS = [
    {"id":  1, "name": "Bangalore Urban",   "lat": 12.9716, "lng": 77.5946, "w": 0.18},
    {"id":  2, "name": "Bangalore Rural",   "lat": 13.1070, "lng": 77.5970, "w": 0.04},
    {"id":  3, "name": "Mysuru",            "lat": 12.2958, "lng": 76.6394, "w": 0.07},
    {"id":  4, "name": "Belagavi",          "lat": 15.8497, "lng": 74.4977, "w": 0.06},
    {"id":  5, "name": "Kalaburagi",        "lat": 17.3297, "lng": 76.8343, "w": 0.05},
    {"id":  6, "name": "Dakshina Kannada",  "lat": 12.9141, "lng": 74.8560, "w": 0.05},
    {"id":  7, "name": "Tumakuru",          "lat": 13.3379, "lng": 77.1010, "w": 0.04},
    {"id":  8, "name": "Shivamogga",        "lat": 13.9299, "lng": 75.5681, "w": 0.04},
    {"id":  9, "name": "Dharwad",           "lat": 15.4589, "lng": 75.0078, "w": 0.04},
    {"id": 10, "name": "Vijayapura",        "lat": 16.8302, "lng": 75.7100, "w": 0.04},
    {"id": 11, "name": "Ballari",           "lat": 15.1394, "lng": 76.9214, "w": 0.04},
    {"id": 12, "name": "Raichur",           "lat": 16.2120, "lng": 77.3439, "w": 0.03},
    {"id": 13, "name": "Hassan",            "lat": 13.0033, "lng": 76.1004, "w": 0.03},
    {"id": 14, "name": "Mandya",            "lat": 12.5218, "lng": 76.8951, "w": 0.03},
    {"id": 15, "name": "Udupi",             "lat": 13.3409, "lng": 74.7421, "w": 0.03},
    {"id": 16, "name": "Uttara Kannada",    "lat": 14.7937, "lng": 74.6865, "w": 0.02},
    {"id": 17, "name": "Chikkamagaluru",    "lat": 13.3161, "lng": 75.7720, "w": 0.02},
    {"id": 18, "name": "Kodagu",            "lat": 12.3375, "lng": 75.8069, "w": 0.02},
    {"id": 19, "name": "Chitradurga",       "lat": 14.2251, "lng": 76.3980, "w": 0.02},
    {"id": 20, "name": "Davangere",         "lat": 14.4644, "lng": 75.9218, "w": 0.03},
    {"id": 21, "name": "Gadag",             "lat": 15.4166, "lng": 75.6309, "w": 0.02},
    {"id": 22, "name": "Haveri",            "lat": 14.7939, "lng": 75.4041, "w": 0.02},
    {"id": 23, "name": "Koppal",            "lat": 15.3478, "lng": 76.1547, "w": 0.02},
    {"id": 24, "name": "Bagalkote",         "lat": 16.1765, "lng": 75.6965, "w": 0.02},
    {"id": 25, "name": "Chamarajanagara",   "lat": 11.9261, "lng": 76.9432, "w": 0.02},
    {"id": 26, "name": "Chikkaballapura",   "lat": 13.4355, "lng": 77.7315, "w": 0.02},
    {"id": 27, "name": "Kolar",             "lat": 13.1369, "lng": 78.1294, "w": 0.02},
    {"id": 28, "name": "Ramanagara",        "lat": 12.7157, "lng": 77.2819, "w": 0.02},
    {"id": 29, "name": "Yadgir",            "lat": 16.7710, "lng": 77.1383, "w": 0.02},
    {"id": 30, "name": "Vijayanagara",      "lat": 15.3562, "lng": 76.5224, "w": 0.02},
    {"id": 31, "name": "Bidar",             "lat": 17.9104, "lng": 77.5199, "w": 0.02},
]
DISTRICT_IDS     = [d["id"]   for d in DISTRICTS]
DISTRICT_WEIGHTS = [d["w"]    for d in DISTRICTS]
DISTRICT_MAP     = {d["id"]: d for d in DISTRICTS}

# ─── CRIME HEADS ──────────────────────────────────────────────
CRIME_HEADS = [
    {"id": 1, "name": "Crimes Against Body",     "w": 0.22},
    {"id": 2, "name": "Crimes Against Property", "w": 0.31},
    {"id": 3, "name": "Crimes Against Women",    "w": 0.14},
    {"id": 4, "name": "Economic Offences",       "w": 0.08},
    {"id": 5, "name": "Crimes Against SC/ST",    "w": 0.05},
    {"id": 6, "name": "Cyber Crimes",            "w": 0.07},
    {"id": 7, "name": "Drug Offences (NDPS)",    "w": 0.06},
    {"id": 8, "name": "Other IPC",               "w": 0.07},
]
CRIME_HEAD_IDS     = [c["id"] for c in CRIME_HEADS]
CRIME_HEAD_WEIGHTS = [c["w"]  for c in CRIME_HEADS]

# ─── CRIME SUB-HEADS ──────────────────────────────────────────
CRIME_SUBHEADS = [
    {"id":  1, "head_id": 1, "name": "Murder"},
    {"id":  2, "head_id": 1, "name": "Attempt to Murder"},
    {"id":  3, "head_id": 1, "name": "Grievous Hurt"},
    {"id":  4, "head_id": 1, "name": "Simple Assault"},
    {"id":  5, "head_id": 2, "name": "Vehicle Theft"},
    {"id":  6, "head_id": 2, "name": "House Burglary"},
    {"id":  7, "head_id": 2, "name": "Chain Snatching"},
    {"id":  8, "head_id": 2, "name": "Commercial Robbery"},
    {"id":  9, "head_id": 2, "name": "Pickpocketing"},
    {"id": 10, "head_id": 3, "name": "Eve Teasing"},
    {"id": 11, "head_id": 3, "name": "Domestic Violence"},
    {"id": 12, "head_id": 3, "name": "Sexual Assault"},
    {"id": 13, "head_id": 4, "name": "Cheating"},
    {"id": 14, "head_id": 4, "name": "Fraud"},
    {"id": 15, "head_id": 5, "name": "Atrocity (SC/ST Act)"},
    {"id": 16, "head_id": 6, "name": "Cyber Fraud"},
    {"id": 17, "head_id": 6, "name": "Online Harassment"},
    {"id": 18, "head_id": 7, "name": "NDPS Possession"},
    {"id": 19, "head_id": 7, "name": "NDPS Trafficking"},
    {"id": 20, "head_id": 8, "name": "Other IPC Offence"},
]
# Map head_id → list of subhead ids
SUBHEAD_BY_HEAD = {}
for s in CRIME_SUBHEADS:
    SUBHEAD_BY_HEAD.setdefault(s["head_id"], []).append(s["id"])

# ─── HOUR WEIGHTS (crime by time of day) ─────────────────────
HOUR_WEIGHTS = [
    0.02, 0.02, 0.01, 0.01, 0.01, 0.01,   # 0–5
    0.02, 0.03, 0.04, 0.04, 0.04, 0.04,   # 6–11
    0.04, 0.04, 0.04, 0.04, 0.05, 0.06,   # 12–17
    0.07, 0.08, 0.09, 0.08, 0.06, 0.05,   # 18–23 (evening spike)
]

# ─── MONTHLY MULTIPLIER (seasonality) ────────────────────────
MONTH_MULT = {1:0.9, 2:0.85, 3:0.95, 4:1.0, 5:1.1, 6:0.95,
              7:0.9, 8:0.9,  9:1.0, 10:1.1, 11:1.2, 12:1.05}

# ─── BriefFacts MO TEMPLATES (key for NLP feature) ───────────
MO_TEMPLATES = {
    "Chain Snatching":    [
        "Two suspects on a {color} {bike} motorcycle targeted lone {gender} walkers near {area}, snatched gold chain from behind and fled.",
        "Accused on two-wheeler approached victim near {area} signal, grabbed gold chain and sped away towards {direction}.",
    ],
    "House Burglary":     [
        "Drilled hole near the front door wooden lock using a manual hand drill. Stole cash and valuables during midnight hours.",
        "Suspects gained entry through rear window by breaking iron grills. House was locked, owners were outstation.",
        "Drilled hole near the front door wooden lock using a manual hand drill silencer setup. Gold ornaments and cash stolen.",
    ],
    "Vehicle Theft":      [
        "Two-wheeler was parked near {area}. Ignition bypassed using duplicate key. Vehicle stolen between {time1} and {time2}.",
        "Four-wheeler stolen from apartment parking. CCTV footage shows suspect using master key device.",
    ],
    "Cyber Fraud":        [
        "Victim received WhatsApp message posing as electricity board. Clicked phishing link and lost Rs {amount} from bank account.",
        "Caller posed as KYC officer of {bank} bank. Victim shared OTP and Rs {amount} was debited.",
        "Victim received call claiming to be from TRAI. Threatened mobile disconnection. Rs {amount} transferred.",
    ],
    "Murder":             [
        "Deceased was found with stab wounds near {area}. Old enmity suspected. Accused identified as {relationship} of victim.",
        "Victim attacked with sharp weapon during altercation over land dispute. Succumbed to injuries at hospital.",
    ],
    "Domestic Violence":  [
        "Complainant reported repeated assault by husband and in-laws over dowry demands. Injuries documented.",
        "Victim assaulted by husband under influence of alcohol. Neighbours informed police station.",
    ],
    "NDPS Possession":    [
        "Accused was intercepted near {area} bus stand. Search revealed {drug} concealed in {item}. Quantity: {qty} grams.",
        "During routine vehicle check accused found with {drug} packets. No valid permit produced.",
    ],
    "Default":            [
        "Complainant reported {crime} at {area} on {date}. Statement recorded. Investigation initiated.",
        "FIR registered based on complaint. Accused identified. Further investigation in progress.",
    ],
}

def get_brief_facts(subhead_name, district_name, incident_date):
    templates = MO_TEMPLATES.get(subhead_name, MO_TEMPLATES["Default"])
    t = random.choice(templates)
    return t.format(
        color=random.choice(["black","red","white","blue"]),
        bike=random.choice(["Pulsar","Splendor","Apache","Activa"]),
        gender=random.choice(["female","elderly female","woman"]),
        area=f"{district_name} {random.choice(['Main Road','Market','Bus Stand','Circle','Layout'])}",
        direction=random.choice(["north","south","east","west"]),
        time1=f"{random.randint(6,20):02d}:00",
        time2=f"{random.randint(21,23):02d}:00",
        amount=f"{random.randint(5,500)*1000:,}",
        bank=random.choice(["SBI","Canara","HDFC","ICICI","Karnataka"]),
        relationship=random.choice(["neighbour","relative","acquaintance","co-worker"]),
        drug=random.choice(["Ganja","Brown Sugar","Heroin","MDMA"]),
        item=random.choice(["bag","undergarment","vehicle seat","food parcel"]),
        qty=random.randint(10, 5000),
        crime=subhead_name,
        date=incident_date.strftime("%d/%m/%Y"),
    )

print("✅ Config loaded —", len(DISTRICTS), "districts,", len(CRIME_SUBHEADS), "crime types")
```

---

## Cell 4 — Lookup / Reference Tables

```python
# ── State ──────────────────────────────────────────────────────
df_state = pd.DataFrame([
    {"StateID": 1, "StateName": "Karnataka", "NationalityID": 1, "Active": 1}
])
df_state.to_csv("output/State.csv", index=False)

# ── District ───────────────────────────────────────────────────
df_district = pd.DataFrame([
    {"DistrictID": d["id"], "DistrictName": d["name"], "StateID": 1, "Active": 1}
    for d in DISTRICTS
])
df_district.to_csv("output/District.csv", index=False)

# ── UnitType ───────────────────────────────────────────────────
df_unittype = pd.DataFrame([
    {"UnitTypeID": 1, "UnitTypeName": "Police Station", "CityDistState": "District", "Hierarchy": 3, "Active": 1},
    {"UnitTypeID": 2, "UnitTypeName": "Circle Office",  "CityDistState": "District", "Hierarchy": 2, "Active": 1},
    {"UnitTypeID": 3, "UnitTypeName": "District HQ",    "CityDistState": "District", "Hierarchy": 1, "Active": 1},
])
df_unittype.to_csv("output/UnitType.csv", index=False)

# ── Unit (Police Stations) ─────────────────────────────────────
units = []
uid = 1
station_suffixes = ["PS", "Town PS", "Rural PS", "North PS", "South PS", "East PS", "West PS"]
for d in DISTRICTS:
    n_stations = max(3, int(N_UNITS * d["w"]))
    for i in range(n_stations):
        units.append({
            "UnitID":    uid,
            "UnitName":  f"{d['name']} {station_suffixes[i % len(station_suffixes)]}",
            "TypeID":    1,
            "ParentUnit": None,
            "StateID":   1,
            "DistrictID": d["id"],
            "Active":    1,
        })
        uid += 1
df_unit = pd.DataFrame(units)
df_unit.to_csv("output/Unit.csv", index=False)

# ── Rank ───────────────────────────────────────────────────────
df_rank = pd.DataFrame([
    {"RankID": 1, "RankName": "Constable",        "Hierarchy": 7, "Active": 1},
    {"RankID": 2, "RankName": "Head Constable",   "Hierarchy": 6, "Active": 1},
    {"RankID": 3, "RankName": "ASI",              "Hierarchy": 5, "Active": 1},
    {"RankID": 4, "RankName": "SI",               "Hierarchy": 4, "Active": 1},
    {"RankID": 5, "RankName": "Inspector",        "Hierarchy": 3, "Active": 1},
    {"RankID": 6, "RankName": "DSP",              "Hierarchy": 2, "Active": 1},
    {"RankID": 7, "RankName": "SP",               "Hierarchy": 1, "Active": 1},
])
df_rank.to_csv("output/Rank.csv", index=False)

# ── Designation ────────────────────────────────────────────────
df_designation = pd.DataFrame([
    {"DesignationID": 1, "DesignationName": "Investigating Officer", "Active": 1, "SortOrder": 1},
    {"DesignationID": 2, "DesignationName": "SHO",                   "Active": 1, "SortOrder": 2},
    {"DesignationID": 3, "DesignationName": "Writer",                "Active": 1, "SortOrder": 3},
    {"DesignationID": 4, "DesignationName": "Beat Officer",          "Active": 1, "SortOrder": 4},
])
df_designation.to_csv("output/Designation.csv", index=False)

# ── CaseCategory ───────────────────────────────────────────────
df_casecat = pd.DataFrame([
    {"CaseCategoryID": 1, "LookupValue": "FIR"},
    {"CaseCategoryID": 3, "LookupValue": "UDR"},
    {"CaseCategoryID": 4, "LookupValue": "PAR"},
    {"CaseCategoryID": 8, "LookupValue": "Zero FIR"},
])
df_casecat.to_csv("output/CaseCategory.csv", index=False)

# ── GravityOffence ─────────────────────────────────────────────
df_gravity = pd.DataFrame([
    {"GravityOffenceID": 1, "LookupValue": "Heinous"},
    {"GravityOffenceID": 2, "LookupValue": "Non-Heinous"},
])
df_gravity.to_csv("output/GravityOffence.csv", index=False)

# ── CaseStatusMaster ───────────────────────────────────────────
df_status = pd.DataFrame([
    {"CaseStatusID": 1, "CaseStatusName": "Under Investigation"},
    {"CaseStatusID": 2, "CaseStatusName": "Charge Sheeted"},
    {"CaseStatusID": 3, "CaseStatusName": "Closed / Final Report"},
    {"CaseStatusID": 4, "CaseStatusName": "Referred to Court"},
])
df_status.to_csv("output/CaseStatusMaster.csv", index=False)

# ── ReligionMaster ─────────────────────────────────────────────
df_religion = pd.DataFrame([
    {"ReligionID": 1, "ReligionName": "Hindu"},
    {"ReligionID": 2, "ReligionName": "Muslim"},
    {"ReligionID": 3, "ReligionName": "Christian"},
    {"ReligionID": 4, "ReligionName": "Other"},
])
df_religion.to_csv("output/ReligionMaster.csv", index=False)

# ── CasteMaster ────────────────────────────────────────────────
castes = ["General", "OBC", "SC", "ST", "Vokkaliga", "Lingayat",
          "Kuruba", "Idiga", "Bovi", "Scheduled Caste (Other)"]
df_caste = pd.DataFrame([
    {"caste_master_id": i+1, "caste_master_name": c} for i, c in enumerate(castes)
])
df_caste.to_csv("output/CasteMaster.csv", index=False)

# ── OccupationMaster ───────────────────────────────────────────
occupations = ["Farmer", "Daily Labourer", "Business", "Government Employee",
               "Private Employee", "Student", "Housewife", "Retired",
               "Auto/Cab Driver", "Unemployed"]
df_occ = pd.DataFrame([
    {"OccupationID": i+1, "OccupationName": o} for i, o in enumerate(occupations)
])
df_occ.to_csv("output/OccupationMaster.csv", index=False)

# ── CrimeHead ──────────────────────────────────────────────────
df_crimehead = pd.DataFrame([
    {"CrimeHeadID": c["id"], "CrimeGroupName": c["name"], "Active": 1}
    for c in CRIME_HEADS
])
df_crimehead.to_csv("output/CrimeHead.csv", index=False)

# ── CrimeSubHead ───────────────────────────────────────────────
df_crimesubhead = pd.DataFrame([
    {"CrimeSubHeadID": s["id"], "CrimeHeadID": s["head_id"],
     "CrimeHeadName": s["name"], "SeqID": i+1}
    for i, s in enumerate(CRIME_SUBHEADS)
])
df_crimesubhead.to_csv("output/CrimeSubHead.csv", index=False)

# ── Act & Section ──────────────────────────────────────────────
df_act = pd.DataFrame([
    {"ActCode": "IPC",  "ActDescription": "Indian Penal Code",                       "ShortName": "IPC",  "Active": 1},
    {"ActCode": "NDPS", "ActDescription": "Narcotic Drugs and Psychotropic Substances Act", "ShortName": "NDPS", "Active": 1},
    {"ActCode": "SCST", "ActDescription": "SC/ST (Prevention of Atrocities) Act",    "ShortName": "SCST", "Active": 1},
    {"ActCode": "IT",   "ActDescription": "Information Technology Act",               "ShortName": "IT",   "Active": 1},
    {"ActCode": "DV",   "ActDescription": "Protection of Women from Domestic Violence Act", "ShortName": "DV", "Active": 1},
])
df_act.to_csv("output/Act.csv", index=False)

sections_data = [
    ("IPC", "302",  "Murder"),
    ("IPC", "307",  "Attempt to Murder"),
    ("IPC", "326",  "Voluntarily Causing Grievous Hurt"),
    ("IPC", "323",  "Voluntarily Causing Hurt"),
    ("IPC", "379",  "Theft"),
    ("IPC", "380",  "Theft in Dwelling House"),
    ("IPC", "392",  "Robbery"),
    ("IPC", "420",  "Cheating"),
    ("IPC", "354",  "Assault on Woman"),
    ("IPC", "498A", "Husband Cruelty"),
    ("IPC", "376",  "Rape"),
    ("NDPS","20",   "Possession of Cannabis"),
    ("NDPS","21",   "Possession of Manufactured Drugs"),
    ("SCST","3",    "Atrocities Against SC/ST"),
    ("IT",  "66C",  "Identity Theft"),
    ("IT",  "66D",  "Cheating by Personation"),
    ("DV",  "3",    "Domestic Violence"),
]
df_section = pd.DataFrame([
    {"ActCode": a, "SectionCode": s, "SectionDescription": d, "Active": 1}
    for a, s, d in sections_data
])
df_section.to_csv("output/Section.csv", index=False)

# ── Court ──────────────────────────────────────────────────────
courts = []
for i, d in enumerate(DISTRICTS[:10]):  # major districts have courts
    courts.append({
        "CourtID":    i+1,
        "CourtName":  f"{d['name']} District & Sessions Court",
        "DistrictID": d["id"],
        "StateID":    1,
        "Active":     1,
    })
df_court = pd.DataFrame(courts)
df_court.to_csv("output/Court.csv", index=False)

print(f"✅ Lookup tables saved — {len(df_unit)} police stations, {len(df_court)} courts")
```

---

## Cell 5 — Employees (Police Officers)

```python
RANK_DIST = [1,1,1,1,1,2,2,2,3,3,4,4,5,6,7]   # weighted rank draw pool

first_names_m = ["Rajesh","Suresh","Mahesh","Ganesh","Ramesh","Naresh","Dinesh",
                 "Venkatesh","Girish","Harish","Santosh","Prakash","Ravi","Kumar",
                 "Srinivas","Basavaraj","Manjunath","Shivaraj","Praveen","Naveen"]
first_names_f = ["Anitha","Suma","Kavitha","Lakshmi","Savitha","Rekha","Usha",
                 "Meena","Geetha","Mamatha","Pushpa","Vinitha","Shobha","Asha"]
last_names    = ["Naik","Gowda","Reddy","Kumar","Rao","Patil","Hegde","Shetty",
                 "Murthy","Swamy","Raju","Bhat","Nair","Pillai","Sharma"]

employees = []
unit_ids = df_unit["UnitID"].tolist()

for i in tqdm(range(N_EMPLOYEES), desc="Employees"):
    gender = "M" if random.random() < 0.88 else "F"
    fname  = random.choice(first_names_m if gender == "M" else first_names_f)
    lname  = random.choice(last_names)
    rank   = random.choice(RANK_DIST)
    unit   = random.choice(unit_ids)
    dist   = df_unit[df_unit["UnitID"] == unit]["DistrictID"].values[0]
    dob    = START_DATE - timedelta(days=random.randint(25*365, 55*365))
    appt   = dob + timedelta(days=random.randint(22*365, 27*365))

    employees.append({
        "EmployeeID":          i + 1,
        "DistrictID":          dist,
        "UnitID":              unit,
        "RankID":              rank,
        "DesignationID":       1 if rank >= 3 else random.randint(1, 4),
        "KGID":                f"KA{random.randint(1000000, 9999999)}",
        "FirstName":           f"{fname} {lname}",
        "EmployeeDOB":         dob.date(),
        "GenderID":            gender,
        "BloodGroupID":        random.randint(1, 8),
        "PhysicallyChallenged": 0,
        "AppointmentDate":     appt.date(),
    })

df_employee = pd.DataFrame(employees)
df_employee.to_csv("output/Employee.csv", index=False)

# Build lookup: unit_id → list of employee_ids (for FK assignment)
UNIT_TO_EMPLOYEES = df_employee.groupby("UnitID")["EmployeeID"].apply(list).to_dict()
print(f"✅ {len(df_employee)} employees across {df_employee['UnitID'].nunique()} stations")
```

---

## Cell 6 — CaseMaster (Core FIR Records)

```python
CASE_CAT_IDS     = [1, 3, 4, 8]
CASE_CAT_WEIGHTS = [0.70, 0.15, 0.10, 0.05]
GRAVITY_IDS      = [1, 2]
GRAVITY_WEIGHTS  = [0.25, 0.75]
STATUS_IDS       = [1, 2, 3, 4]
STATUS_WEIGHTS   = [0.50, 0.30, 0.12, 0.08]
CAT_CODE_MAP     = {1: 1, 3: 3, 4: 4, 8: 8}
COURT_IDS        = df_court["CourtID"].tolist()
SUBHEAD_MAP      = {s["id"]: s for s in CRIME_SUBHEADS}

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def gps_for_district(d):
    lat = np.clip(np.random.normal(d["lat"], 0.25), 11.5, 18.5)
    lng = np.clip(np.random.normal(d["lng"], 0.25), 74.0, 78.6)
    return round(lat, 6), round(lng, 6)

cases = []
station_serials = {}   # (station_id, cat_id, year) → serial

for i in tqdm(range(N_CASES), desc="CaseMaster"):
    dist_id  = random.choices(DISTRICT_IDS, weights=DISTRICT_WEIGHTS)[0]
    dist     = DISTRICT_MAP[dist_id]

    # Pick a unit in this district
    dist_units = df_unit[df_unit["DistrictID"] == dist_id]["UnitID"].tolist()
    unit_id    = random.choice(dist_units)

    # Pick an employee in this unit (or district if unit empty)
    emp_list   = UNIT_TO_EMPLOYEES.get(unit_id, df_employee[df_employee["DistrictID"] == dist_id]["EmployeeID"].tolist())
    officer_id = random.choice(emp_list) if emp_list else 1

    # Dates — apply month multiplier via rejection sampling
    reg_date   = random_date(START_DATE, END_DATE)
    if random.random() > MONTH_MULT[reg_date.month] / 1.2:
        reg_date = random_date(START_DATE, END_DATE)  # resample once

    inc_hour   = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
    inc_from   = reg_date - timedelta(days=random.randint(0, 30))
    inc_from   = inc_from.replace(hour=inc_hour, minute=random.randint(0, 59))
    inc_to     = inc_from + timedelta(minutes=random.randint(5, 180))

    # Crime classification
    head_id    = random.choices(CRIME_HEAD_IDS, weights=CRIME_HEAD_WEIGHTS)[0]
    subhead_id = random.choice(SUBHEAD_BY_HEAD[head_id])
    subhead    = SUBHEAD_MAP[subhead_id]

    cat_id     = random.choices(CASE_CAT_IDS, weights=CASE_CAT_WEIGHTS)[0]
    grav_id    = random.choices(GRAVITY_IDS, weights=GRAVITY_WEIGHTS)[0]
    status_id  = random.choices(STATUS_IDS,  weights=STATUS_WEIGHTS)[0]

    # CrimeNo: {cat_code}{dist_id:04d}{unit_id:04d}{year:04d}{serial:05d}
    year       = reg_date.year
    key        = (unit_id, cat_id, year)
    station_serials[key] = station_serials.get(key, 0) + 1
    serial     = station_serials[key]
    crime_no   = f"{CAT_CODE_MAP[cat_id]}{dist_id:04d}{unit_id:04d}{year}{serial:05d}"
    case_no    = f"{year}{serial:05d}"

    lat, lng   = gps_for_district(dist)

    cases.append({
        "CaseMasterID":        i + 1,
        "CrimeNo":             crime_no,
        "CaseNo":              case_no,
        "CrimeRegisteredDate": reg_date.date(),
        "PolicePersonID":      officer_id,
        "PoliceStationID":     unit_id,
        "CaseCategoryID":      cat_id,
        "GravityOffenceID":    grav_id,
        "CrimeMajorHeadID":    head_id,
        "CrimeMinorHeadID":    subhead_id,
        "CaseStatusID":        status_id,
        "CourtID":             random.choice(COURT_IDS),
        "IncidentFromDate":    inc_from,
        "IncidentToDate":      inc_to,
        "InfoReceivedPSDate":  reg_date,
        "latitude":            lat,
        "longitude":           lng,
        "BriefFacts":          get_brief_facts(subhead["name"], dist["name"], inc_from),
        "_DistrictID":         dist_id,   # helper col — remove before prod
        "_SubheadName":        subhead["name"],
    })

df_case = pd.DataFrame(cases)
df_case.to_csv("output/CaseMaster.csv", index=False)
print(f"✅ {len(df_case)} FIR records | Districts: {df_case['_DistrictID'].nunique()} | Date range: {df_case['CrimeRegisteredDate'].min()} → {df_case['CrimeRegisteredDate'].max()}")
```

---

## Cell 7 — Inject Criminal Patterns ⚠️ Critical for Demo

```python
# ══════════════════════════════════════════════════════════════════
# These 3 patterns are what the AI will "discover" on demo day.
# They must be injected BEFORE generating Accused/Victim tables.
# ══════════════════════════════════════════════════════════════════

# ── PATTERN A: Chain Snatching Cluster (Spatiotemporal) ────────
# 250 cases, Bangalore Urban, 6–9PM only, tight GPS around Indiranagar metro
# ML will find this as a spatiotemporal hotspot
print("Injecting Pattern A: Chain Snatching Cluster (Indiranagar)...")
pattern_a_ids = []
pattern_a_suspects = ["Raju alias Splendor Raju", "Manoj Kumar", "Shiva alias Bike Shiva"]
base_case_id = len(df_case) + 1

pa_rows = []
for i in range(250):
    d = DISTRICT_MAP[1]  # Bangalore Urban
    ts = datetime(2024, random.randint(6, 11), random.randint(1, 28),
                  random.randint(18, 20), random.randint(0, 59))
    lat = round(random.uniform(12.9770, 12.9810), 6)   # tight Indiranagar cluster
    lng = round(random.uniform(77.6390, 77.6450), 6)
    cid = base_case_id + i
    pattern_a_ids.append(cid)
    pa_rows.append({
        "CaseMasterID": cid, "CrimeNo": f"1000100012024{50000+i:05d}",
        "CaseNo": f"2024{50000+i:05d}", "CrimeRegisteredDate": ts.date(),
        "PolicePersonID": random.randint(1, N_EMPLOYEES),
        "PoliceStationID": df_unit[df_unit["DistrictID"]==1]["UnitID"].iloc[0],
        "CaseCategoryID": 1, "GravityOffenceID": 2,
        "CrimeMajorHeadID": 2, "CrimeMinorHeadID": 7,  # Chain Snatching
        "CaseStatusID": random.choices([1,2,3],[0.4,0.4,0.2])[0],
        "CourtID": 1,
        "IncidentFromDate": ts, "IncidentToDate": ts + timedelta(minutes=5),
        "InfoReceivedPSDate": ts + timedelta(hours=1),
        "latitude": lat, "longitude": lng,
        "BriefFacts": f"Two suspects on a black Pulsar motorcycle targeted lone female walker near Indiranagar Metro Station, snatched gold chain from behind and fled towards Domlur.",
        "_DistrictID": 1, "_SubheadName": "Chain Snatching",
    })

# ── PATTERN B: House Burglary Syndicate (Network / MO Link) ───
# 3 suspects, 60 cases across 3 districts, identical MO text
# NetworkX will cluster these as a gang; NLP will find MO match
print("Injecting Pattern B: Burglary Syndicate (Cross-District Gang)...")
pattern_b_suspects = [
    "Kiran Kumar alias Drill Kiran",
    "Ramesh Naik alias Night Ramesh",
    "Syed Ahmed alias Tool Syed",
]
SHARED_MO = "Drilled hole near the front door wooden lock using a manual hand drill silencer setup. Entry gained silently during midnight. Gold ornaments and cash stolen."
pattern_b_ids = []
pb_rows = []
target_districts = [1, 3, 4]  # Bangalore, Mysuru, Belagavi

for j, dist_id in enumerate(target_districts):
    d = DISTRICT_MAP[dist_id]
    for k in range(20):  # 20 cases per district = 60 total
        ts = datetime(2023, random.randint(1, 12), random.randint(1, 28),
                      random.randint(1, 4), random.randint(0, 59))
        lat, lng = gps_for_district(d)
        cid = base_case_id + 250 + j*20 + k
        pattern_b_ids.append(cid)
        pb_rows.append({
            "CaseMasterID": cid, "CrimeNo": f"1{dist_id:04d}00012023{60000+j*20+k:05d}",
            "CaseNo": f"2023{60000+j*20+k:05d}", "CrimeRegisteredDate": ts.date(),
            "PolicePersonID": random.randint(1, N_EMPLOYEES),
            "PoliceStationID": df_unit[df_unit["DistrictID"]==dist_id]["UnitID"].iloc[0],
            "CaseCategoryID": 1, "GravityOffenceID": 1,  # Heinous
            "CrimeMajorHeadID": 2, "CrimeMinorHeadID": 6,  # House Burglary
            "CaseStatusID": random.choices([1,2],[0.5,0.5])[0],
            "CourtID": min(j+1, len(df_court)),
            "IncidentFromDate": ts, "IncidentToDate": ts + timedelta(hours=2),
            "InfoReceivedPSDate": ts + timedelta(hours=6),
            "latitude": lat, "longitude": lng,
            "BriefFacts": SHARED_MO,
            "_DistrictID": dist_id, "_SubheadName": "House Burglary",
        })

# ── PATTERN C: Cyber Fraud Wave (Seasonal Anomaly) ────────────
# 150 cases, Oct–Nov 2023 (Diwali), urban districts only, retired/farmer victims
# Anomaly detection will flag the Diwali spike
print("Injecting Pattern C: Diwali Cyber Fraud Wave...")
pattern_c_ids = []
pc_rows = []
urban_districts = [1, 3, 6, 9]
for m in range(150):
    dist_id = random.choice(urban_districts)
    d = DISTRICT_MAP[dist_id]
    ts = datetime(2023, random.choice([10, 11]), random.randint(1, 30),
                  random.randint(9, 21), random.randint(0, 59))
    lat, lng = gps_for_district(d)
    cid = base_case_id + 310 + m
    pattern_c_ids.append(cid)
    pc_rows.append({
        "CaseMasterID": cid, "CrimeNo": f"1{dist_id:04d}00012023{70000+m:05d}",
        "CaseNo": f"2023{70000+m:05d}", "CrimeRegisteredDate": ts.date(),
        "PolicePersonID": random.randint(1, N_EMPLOYEES),
        "PoliceStationID": df_unit[df_unit["DistrictID"]==dist_id]["UnitID"].iloc[0],
        "CaseCategoryID": 1, "GravityOffenceID": 2,
        "CrimeMajorHeadID": 6, "CrimeMinorHeadID": 16,  # Cyber Fraud
        "CaseStatusID": 1,
        "CourtID": 1,
        "IncidentFromDate": ts, "IncidentToDate": ts + timedelta(minutes=30),
        "InfoReceivedPSDate": ts + timedelta(days=random.randint(1,5)),
        "latitude": lat, "longitude": lng,
        "BriefFacts": f"Victim received WhatsApp message posing as {random.choice(['BESCOM','BWSSB','SBI'])} during Diwali festival period. Clicked phishing link and lost Rs {random.randint(10,200)*1000:,} from bank account. KYC fraud suspected.",
        "_DistrictID": dist_id, "_SubheadName": "Cyber Fraud",
    })

# ── Append all patterns to CaseMaster ─────────────────────────
df_patterns = pd.DataFrame(pa_rows + pb_rows + pc_rows)
df_case = pd.concat([df_case, df_patterns], ignore_index=True)
df_case.to_csv("output/CaseMaster.csv", index=False)
print(f"✅ CaseMaster updated: {len(df_case)} total records ({len(pa_rows)} PatA + {len(pb_rows)} PatB + {len(pc_rows)} PatC injected)")
```

---

## Cell 8 — Accused

```python
# ── Repeat offender pool (500 people appearing in 3–8 cases each) ──
repeat_offenders = []
for _ in range(500):
    gender = "M" if random.random() < 0.85 else "F"
    fname  = random.choice(first_names_m if gender == "M" else first_names_f)
    lname  = random.choice(last_names)
    repeat_offenders.append({
        "name":   f"{fname} {lname}",
        "age":    int(np.clip(np.random.normal(28, 7), 18, 55)),
        "gender": gender,
    })

accused_rows = []
acc_id = 1
case_to_accused = {}   # caseID → list of accused_ids (for ArrestSurrender)

case_ids = df_case["CaseMasterID"].tolist()

for cid in tqdm(case_ids, desc="Accused"):
    n_accused = random.choices([1, 2, 3, 4], weights=[0.60, 0.25, 0.10, 0.05])[0]
    case_to_accused[cid] = []

    for person_num in range(n_accused):
        # 15% chance this slot is a repeat offender
        if random.random() < 0.15 and repeat_offenders:
            ro = random.choice(repeat_offenders)
            name   = ro["name"]
            age    = ro["age"] + random.randint(-1, 2)
            gender = ro["gender"]
        else:
            gender = random.choices(["M","F","T"], weights=[0.80,0.18,0.02])[0]
            fname  = random.choice(first_names_m if gender == "M" else first_names_f)
            name   = f"{fname} {random.choice(last_names)}"
            age    = int(np.clip(np.random.normal(28, 8), 18, 65))

        accused_rows.append({
            "AccusedMasterID": acc_id,
            "CaseMasterID":    cid,
            "AccusedName":     name,
            "AgeYear":         age,
            "GenderID":        gender,
            "PersonID":        f"A{person_num+1}",
        })
        case_to_accused[cid].append(acc_id)
        acc_id += 1

# ── Inject Pattern B suspects into their cases ─────────────────
pb_suspect_map = {}
for idx, cid in enumerate(pattern_b_ids):
    suspect = pattern_b_suspects[idx % 3]
    existing = [r for r in accused_rows if r["CaseMasterID"] == cid]
    if not existing:
        accused_rows.append({
            "AccusedMasterID": acc_id,
            "CaseMasterID":    cid,
            "AccusedName":     suspect,
            "AgeYear":         random.randint(25, 38),
            "GenderID":        "M",
            "PersonID":        "A1",
        })
        case_to_accused.setdefault(cid, []).append(acc_id)
        pb_suspect_map[suspect] = pb_suspect_map.get(suspect, []) + [acc_id]
        acc_id += 1
    else:
        # Overwrite A1 with pattern suspect name
        for r in accused_rows:
            if r["CaseMasterID"] == cid and r["PersonID"] == "A1":
                r["AccusedName"] = suspect
                break

# ── Inject Pattern A suspects ──────────────────────────────────
for idx, cid in enumerate(pattern_a_ids):
    for r in accused_rows:
        if r["CaseMasterID"] == cid and r["PersonID"] == "A1":
            r["AccusedName"] = pattern_a_suspects[idx % 3]
            break

df_accused = pd.DataFrame(accused_rows)
df_accused.to_csv("output/Accused.csv", index=False)
print(f"✅ {len(df_accused)} accused records | Unique names: {df_accused['AccusedName'].nunique()}")
```

---

## Cell 9 — Victim

```python
VICTIM_GENDER_BY_HEAD = {
    3: {"F": 0.95, "M": 0.04, "T": 0.01},   # Crimes Against Women
    1: {"M": 0.65, "F": 0.33, "T": 0.02},   # Body
    2: {"M": 0.55, "F": 0.43, "T": 0.02},   # Property
    6: {"M": 0.50, "F": 0.48, "T": 0.02},   # Cyber (equal)
}

victim_rows = []
vic_id = 1

for _, row in tqdm(df_case.iterrows(), total=len(df_case), desc="Victim"):
    head_id = row["CrimeMajorHeadID"]
    gdist   = VICTIM_GENDER_BY_HEAD.get(head_id, {"M": 0.55, "F": 0.43, "T": 0.02})
    gender  = random.choices(list(gdist.keys()), weights=list(gdist.values()))[0]
    fname   = random.choice(first_names_f if gender == "F" else first_names_m)

    # Age varies by crime type
    if head_id == 1:   age = int(np.clip(np.random.normal(30, 10), 18, 65))
    elif head_id == 6: age = int(np.clip(np.random.normal(50, 12), 20, 80))  # cyber: older victims
    else:              age = int(np.clip(np.random.normal(35, 15), 5, 80))

    victim_rows.append({
        "VictimMasterID": vic_id,
        "CaseMasterID":   row["CaseMasterID"],
        "VictimName":     f"{fname} {random.choice(last_names)}",
        "AgeYear":        age,
        "GenderID":       gender,
        "VictimPolice":   1 if random.random() < 0.03 else 0,
    })
    vic_id += 1

    # 10% cases have 2 victims
    if random.random() < 0.10:
        gender2 = random.choices(list(gdist.keys()), weights=list(gdist.values()))[0]
        fname2  = random.choice(first_names_f if gender2 == "F" else first_names_m)
        victim_rows.append({
            "VictimMasterID": vic_id,
            "CaseMasterID":   row["CaseMasterID"],
            "VictimName":     f"{fname2} {random.choice(last_names)}",
            "AgeYear":        int(np.clip(np.random.normal(35, 15), 5, 80)),
            "GenderID":       gender2,
            "VictimPolice":   0,
        })
        vic_id += 1

# Pattern C (cyber fraud): victims are retired/elderly
for cid in pattern_c_ids:
    for r in victim_rows:
        if r["CaseMasterID"] == cid:
            r["AgeYear"] = random.randint(52, 75)
            break

df_victim = pd.DataFrame(victim_rows)
df_victim.to_csv("output/Victim.csv", index=False)
print(f"✅ {len(df_victim)} victim records")
```

---

## Cell 10 — ComplainantDetails

```python
# Karnataka religion & caste proportions (Census data)
RELIGION_WEIGHTS  = [0.84, 0.13, 0.02, 0.01]   # Hindu, Muslim, Christian, Other
CASTE_IDS         = [1,2,3,4,5,6,7,8,9,10]
CASTE_WEIGHTS     = [0.20,0.25,0.15,0.08,0.12,0.10,0.04,0.03,0.02,0.01]
OCC_IDS           = list(range(1, 11))
OCC_WEIGHTS       = [0.25,0.20,0.15,0.12,0.10,0.06,0.05,0.04,0.02,0.01]

complainant_rows = []
comp_id = 1
df_victim_map = df_victim.groupby("CaseMasterID").first().reset_index()
victim_name_map = df_victim_map.set_index("CaseMasterID")["VictimName"].to_dict()

for _, row in tqdm(df_case.iterrows(), total=len(df_case), desc="Complainant"):
    cid = row["CaseMasterID"]
    # 60% of the time complainant = victim
    use_victim_name = random.random() < 0.60
    name = victim_name_map.get(cid, fake.name()) if use_victim_name else fake.name()
    gender = random.choices(["M","F","T"], weights=[0.55, 0.44, 0.01])[0]
    occ_id = random.choices(OCC_IDS, weights=OCC_WEIGHTS)[0]

    # Cyber fraud complainants are more likely to be retired
    if row["_SubheadName"] == "Cyber Fraud" and random.random() < 0.50:
        occ_id = 8  # Retired

    complainant_rows.append({
        "ComplainantID":   comp_id,
        "CaseMasterID":    cid,
        "ComplainantName": name,
        "AgeYear":         int(np.clip(np.random.normal(38, 14), 18, 80)),
        "OccupationID":    occ_id,
        "ReligionID":      random.choices([1,2,3,4], weights=RELIGION_WEIGHTS)[0],
        "CasteID":         random.choices(CASTE_IDS, weights=CASTE_WEIGHTS)[0],
        "GenderID":        gender,
    })
    comp_id += 1

df_complainant = pd.DataFrame(complainant_rows)
df_complainant.to_csv("output/ComplainantDetails.csv", index=False)
print(f"✅ {len(df_complainant)} complainant records")
```

---

## Cell 11 — ArrestSurrender

```python
# Only 60% of cases have arrests
arrest_case_ids = random.sample(
    df_case["CaseMasterID"].tolist(),
    int(len(df_case) * 0.60)
)
# Cases with Pattern B suspects always arrested (gang cases)
arrest_case_ids = list(set(arrest_case_ids + pattern_b_ids))

arrest_rows = []
arr_id = 1

for cid in tqdm(arrest_case_ids, desc="ArrestSurrender"):
    case_row = df_case[df_case["CaseMasterID"] == cid].iloc[0]
    reg_date = pd.to_datetime(case_row["CrimeRegisteredDate"])
    unit_id  = case_row["PoliceStationID"]
    dist_id  = case_row["_DistrictID"]
    court_id = case_row["CourtID"]

    acc_ids  = case_to_accused.get(cid, [1])
    # Usually first accused is arrested; 25% chance second also arrested
    arrest_these = [acc_ids[0]]
    if len(acc_ids) > 1 and random.random() < 0.25:
        arrest_these.append(acc_ids[1])

    io_list = UNIT_TO_EMPLOYEES.get(unit_id, [1])
    io_id   = random.choice(io_list)

    for accused_id in arrest_these:
        arr_date = reg_date + timedelta(days=random.randint(1, 90))
        arrest_rows.append({
            "ArrestSurrenderID":          arr_id,
            "CaseMasterID":               cid,
            "ArrestSurrenderTypeID":      1 if random.random() < 0.85 else 2,
            "ArrestSurrenderDate":        arr_date.date(),
            "ArrestSurrenderStateId":     1,
            "ArrestSurrenderDistrictId":  dist_id,
            "PoliceStationID":            unit_id,
            "IOID":                       io_id,
            "CourtID":                    court_id,
            "AccusedMasterID":            accused_id,
            "IsAccused":                  1,
            "IsComplainantAccused":       1 if random.random() < 0.02 else 0,
        })
        arr_id += 1

df_arrest = pd.DataFrame(arrest_rows)
df_arrest.to_csv("output/ArrestSurrender.csv", index=False)
print(f"✅ {len(df_arrest)} arrest/surrender records across {df_arrest['CaseMasterID'].nunique()} cases")
```

---

## Cell 12 — ChargesheetDetails

```python
# Only charge-sheeted cases (CaseStatusID = 2)
cs_cases = df_case[df_case["CaseStatusID"] == 2]["CaseMasterID"].tolist()

cs_rows = []
cs_id = 1

for cid in tqdm(cs_cases, desc="Chargesheet"):
    case_row  = df_case[df_case["CaseMasterID"] == cid].iloc[0]
    reg_date  = pd.to_datetime(case_row["CrimeRegisteredDate"])

    arr_row   = df_arrest[df_arrest["CaseMasterID"] == cid]
    if len(arr_row) > 0:
        arr_date = pd.to_datetime(arr_row.iloc[0]["ArrestSurrenderDate"])
        cs_date  = arr_date + timedelta(days=random.randint(30, 180))
    else:
        cs_date  = reg_date + timedelta(days=random.randint(60, 365))

    officer_id = case_row["PolicePersonID"]
    cs_type    = random.choices(["A","B","C"], weights=[0.70, 0.10, 0.20])[0]

    cs_rows.append({
        "CSID":            cs_id,
        "CaseMasterID":    cid,
        "csdate":          cs_date.date(),
        "cstype":          cs_type,
        "PolicePersonID":  officer_id,
    })
    cs_id += 1

df_cs = pd.DataFrame(cs_rows)
df_cs.to_csv("output/ChargesheetDetails.csv", index=False)
print(f"✅ {len(df_cs)} chargesheet records")
```

---

## Cell 13 — ActSectionAssociation

```python
# Map crime subhead → most likely act+section combos
SUBHEAD_TO_SECTIONS = {
    1:  [("IPC","302")],                        # Murder
    2:  [("IPC","307")],                        # Attempt to Murder
    3:  [("IPC","326")],                        # Grievous Hurt
    4:  [("IPC","323")],                        # Simple Assault
    5:  [("IPC","379")],                        # Vehicle Theft
    6:  [("IPC","380"), ("IPC","454")],         # House Burglary
    7:  [("IPC","392")],                        # Chain Snatching / Robbery
    8:  [("IPC","392")],                        # Commercial Robbery
    9:  [("IPC","379")],                        # Pickpocketing
    10: [("IPC","354")],                        # Eve Teasing
    11: [("IPC","498A"), ("DV","3")],           # Domestic Violence
    12: [("IPC","376")],                        # Sexual Assault
    13: [("IPC","420")],                        # Cheating
    14: [("IPC","420"), ("IPC","468")],         # Fraud
    15: [("SCST","3")],                         # SC/ST Atrocity
    16: [("IT","66C"), ("IT","66D")],           # Cyber Fraud
    17: [("IT","66D")],                         # Online Harassment
    18: [("NDPS","20")],                        # NDPS Possession
    19: [("NDPS","21")],                        # NDPS Trafficking
    20: [("IPC","323")],                        # Other IPC
}

asa_rows = []
for _, row in tqdm(df_case.iterrows(), total=len(df_case), desc="ActSection"):
    subhead_id = row["CrimeMinorHeadID"]
    sections   = SUBHEAD_TO_SECTIONS.get(subhead_id, [("IPC","323")])
    for order, (act_code, sec_code) in enumerate(sections):
        asa_rows.append({
            "CaseMasterID":  row["CaseMasterID"],
            "ActID":         act_code,
            "SectionID":     sec_code,
            "ActOrderID":    1,
            "SectionOrderID": order + 1,
        })

df_asa = pd.DataFrame(asa_rows)
df_asa.to_csv("output/ActSectionAssociation.csv", index=False)
print(f"✅ {len(df_asa)} act-section associations")
```

---

## Cell 14 — Validate Everything

```python
print("\n" + "="*60)
print("  VALIDATION REPORT")
print("="*60)

checks_passed = 0
checks_total  = 0

def check(label, condition, detail=""):
    global checks_passed, checks_total
    checks_total += 1
    status = "✅ PASS" if condition else "❌ FAIL"
    if condition: checks_passed += 1
    print(f"  {status}  {label}")
    if not condition and detail:
        print(f"         → {detail}")

# Load all outputs
df_c  = pd.read_csv("output/CaseMaster.csv")
df_a  = pd.read_csv("output/Accused.csv")
df_v  = pd.read_csv("output/Victim.csv")
df_cp = pd.read_csv("output/ComplainantDetails.csv")
df_ar = pd.read_csv("output/ArrestSurrender.csv")
df_cs2= pd.read_csv("output/ChargesheetDetails.csv")

case_ids_set = set(df_c["CaseMasterID"])

check("CaseMaster has 50k+ records",            len(df_c) >= 50_000, f"got {len(df_c)}")
check("No null CaseMasterID in CaseMaster",     df_c["CaseMasterID"].isnull().sum() == 0)
check("All Accused.CaseMasterID valid FK",      df_a["CaseMasterID"].isin(case_ids_set).all())
check("All Victim.CaseMasterID valid FK",       df_v["CaseMasterID"].isin(case_ids_set).all())
check("All Complainant.CaseMasterID valid FK",  df_cp["CaseMasterID"].isin(case_ids_set).all())
check("All ArrestSurrender.CaseMasterID valid", df_ar["CaseMasterID"].isin(case_ids_set).all())
check("GPS within Karnataka lat bounds",
      df_c["latitude"].between(11.5, 18.5).all(),
      f"outliers: {(~df_c['latitude'].between(11.5,18.5)).sum()}")
check("GPS within Karnataka lng bounds",
      df_c["longitude"].between(74.0, 78.6).all())
check("ArrestDate > RegisteredDate",
      (pd.to_datetime(df_ar["ArrestSurrenderDate"]) >=
       pd.to_datetime(df_ar["CaseMasterID"].map(
           df_c.set_index("CaseMasterID")["CrimeRegisteredDate"]))).all())
check("Bangalore Urban has highest crime share",
      df_c["_DistrictID"].value_counts().idxmax() == 1)
check("Pattern A: 250 Chain Snatching in Bangalore",
      len(df_c[(df_c["CrimeMinorHeadID"]==7) & (df_c["_DistrictID"]==1)]) >= 200)
check("Pattern B: Burglary syndicate present",
      df_a[df_a["AccusedName"].str.contains("Drill|Night|Tool", na=False)]["CaseMasterID"].nunique() >= 50)
check("Pattern C: Oct-Nov 2023 cyber spike present",
      len(df_c[(df_c["CrimeMinorHeadID"]==16) &
               (pd.to_datetime(df_c["CrimeRegisteredDate"]).dt.month.isin([10,11])) &
               (pd.to_datetime(df_c["CrimeRegisteredDate"]).dt.year==2023)]) >= 100)
check("Repeat offenders exist (name in 3+ cases)",
      (df_a.groupby("AccusedName")["CaseMasterID"].nunique() >= 3).sum() >= 300)
check("BriefFacts not empty",
      df_c["BriefFacts"].isnull().sum() == 0)

print("="*60)
print(f"  RESULT: {checks_passed}/{checks_total} checks passed")
if checks_passed == checks_total:
    print("  🎉 All good! Data is ready for handoff.")
else:
    print("  ⚠️  Fix failing checks before handoff.")
print("="*60)
```

---

## Cell 15 — Summary & File Sizes

```python
import os

print("\n📁 OUTPUT FILES\n")
files = [f for f in os.listdir("output") if f.endswith(".csv")]
total_rows = 0
for f in sorted(files):
    path  = f"output/{f}"
    df_   = pd.read_csv(path)
    size  = os.path.getsize(path) / 1024
    total_rows += len(df_)
    print(f"  {f:<35} {len(df_):>8,} rows   {size:>8.1f} KB")

print(f"\n  {'TOTAL':35} {total_rows:>8,} rows")

print("\n\n🎯 INJECTED PATTERNS SUMMARY")
print(f"  Pattern A  Chain Snatching Cluster   {len(pattern_a_ids):>5} cases  (Indiranagar, 6-9PM)")
print(f"  Pattern B  Burglary Syndicate Gang    {len(pattern_b_ids):>5} cases  (3 suspects, 3 districts)")
print(f"  Pattern C  Diwali Cyber Fraud Wave    {len(pattern_c_ids):>5} cases  (Oct-Nov 2023 spike)")

print("\n\n📦 HANDOFF GUIDE")
print("  → Dashboard team:  CaseMaster, District, Unit, CrimeHead, CrimeSubHead, CaseStatusMaster")
print("  → ML team:         CaseMaster, Accused, ArrestSurrender, District")
print("  → Network team:    CaseMaster, Accused, Victim, Unit, ArrestSurrender")
print("  → All teams:       karnataka_districts.geojson (download from github.com/datameet/india-maps)")
```

---

## What the 3 Patterns Enable on Demo Day

| Pattern | What AI finds | Feature demo'd |
|---|---|---|
| **A — Chain Snatching Cluster** | Tight GPS cluster + 6–9PM hour = hotspot | Spatiotemporal heatmap time slider |
| **B — Burglary Syndicate** | 3 accused share 60 cases + identical MO text | Network graph gang detection + NLP MO match |
| **C — Diwali Cyber Wave** | Oct-Nov spike >2σ above baseline | Red Zone Alert + Anomaly Detection feed |

---

## GeoJSON (Download Separately — 1 command)

```python
# Run this in a separate cell to download Karnataka district boundaries for the map
import urllib.request, json

url = "https://raw.githubusercontent.com/datameet/india-maps/master/Districts/Karnataka.geojson"
urllib.request.urlretrieve(url, "output/karnataka_districts.geojson")
print("✅ GeoJSON saved to output/karnataka_districts.geojson")
```

---

*KSP Drishti Platform · Datathon 2026 · Data Generation v2.0*
