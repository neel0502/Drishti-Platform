#!/usr/bin/env python3
"""Generate deterministic, schema-faithful use-case records for Catalyst.

The output is intentionally small, idempotent, and unmistakably synthetic. It
uses reserved numeric identifiers and Catalyst ``upsert`` import configs, so a
second run updates the same rows instead of creating duplicates.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
DESTINATION = ROOT / ".catalyst-use-cases"
BASE_CASE_ID = 8_100_000


SCENARIOS = [
    {
        "code": "SERIAL_BURGLARY",
        "title": "Cross-district drill burglary series",
        "offence": "House Burglary",
        "districts": [1, 3, 9, 1, 3, 9],
        "shared_accused": "SYN PERSON BURGLARY ALPHA",
        "phone": "90000-11001",
        "vehicle": "KA-00 SY 1101",
        "facts": "A rear service door showed circular drill marks. A dark utility vehicle was reported near the scene. CCTV collection and tool-mark comparison remain pending.",
        "expected": ["shared accused", "shared phone", "shared vehicle", "similar drill modus operandi"],
        "negative_control": False,
    },
    {
        "code": "CYBER_MULE_RING",
        "title": "Multi-district payment-link fraud",
        "offence": "Cyber Fraud",
        "districts": [1, 3, 4, 9, 10, 1],
        "shared_accused": "SYN PERSON CYBER MULE ALPHA",
        "phone": "90000-22002",
        "vehicle": None,
        "facts": "The complainant received a false service-payment link referencing merchant handle SYN-UPI-2200. Device extraction, bank confirmation, and beneficiary ownership are not yet attached.",
        "expected": ["shared accused", "shared phone", "shared merchant handle", "missing bank/device evidence"],
        "negative_control": False,
    },
    {
        "code": "NDPS_CORRIDOR",
        "title": "NDPS courier and vehicle corridor",
        "offence": "NDPS Trafficking",
        "districts": [4, 9, 10, 4, 9, 10],
        "shared_accused": "SYN PERSON NDPS COURIER ALPHA",
        "phone": "90000-33003",
        "vehicle": "KA-00 SY 3303",
        "facts": "A sealed synthetic contraband packet was recorded during a vehicle check. Laboratory result, seal continuity, and route-camera records require verification.",
        "expected": ["shared accused", "shared courier vehicle", "custody verification gap", "cross-district coordination"],
        "negative_control": False,
    },
    {
        "code": "CONFLICTING_STATEMENTS",
        "title": "Conflicting witness chronology",
        "offence": "Attempt to Murder",
        "districts": [3, 3, 3, 3, 3, 3],
        "shared_accused": "SYN PERSON STATEMENT ALPHA",
        "phone": None,
        "vehicle": None,
        "facts": "Witness A recorded the event at 20:10 while Witness B recorded 21:05. Lighting, camera time drift, and original statement timestamps have not been reconciled.",
        "expected": ["statement time conflict", "camera-clock verification", "no unsupported resolution"],
        "negative_control": False,
    },
    {
        "code": "COURT_READINESS",
        "title": "Court-readiness documentation queue",
        "offence": "Commercial Robbery",
        "districts": [1, 2, 3, 4, 9, 10],
        "shared_accused": "SYN PERSON ROBBERY ALPHA",
        "phone": "90000-55005",
        "vehicle": "KA-00 SY 5505",
        "facts": "Recorded property seizure and witness statement are present. Forensic acknowledgement, exhibit index, and final document service require a court-readiness review.",
        "expected": ["mixed chargesheet status", "missing forensic acknowledgement", "document deadline tasks"],
        "negative_control": False,
    },
    {
        "code": "VICTIM_FOLLOWUP",
        "title": "Restricted victim follow-up series",
        "offence": "Domestic Violence",
        "districts": [1, 1, 1, 1, 1, 1],
        "shared_accused": "SYN PERSON RESPONDENT ALPHA",
        "phone": None,
        "vehicle": None,
        "facts": "A repeat safety concern was recorded for the same synthetic household. Contact preference, protection-order status, and welfare follow-up require restricted authorized review.",
        "expected": ["repeat household linkage", "victim follow-up task", "minimum-necessary access"],
        "negative_control": False,
    },
    {
        "code": "CHAIN_SNATCHING",
        "title": "Transport-corridor chain-snatching series",
        "offence": "Chain Snatching",
        "districts": [1, 2, 3, 1, 2, 3],
        "shared_accused": "SYN PERSON RIDER ALPHA",
        "phone": "90000-77007",
        "vehicle": "KA-00 SY 7707",
        "facts": "Two riders targeted a pedestrian near a transport corridor and left on the same recorded motorcycle. Helmet imagery and ownership verification remain pending.",
        "expected": ["shared accused", "shared phone", "shared motorcycle", "helmet/CCTV gap"],
        "negative_control": False,
    },
    {
        "code": "UNRELATED_BURGLARIES",
        "title": "Similar but deliberately unrelated burglaries",
        "offence": "House Burglary",
        "districts": [1, 2, 3, 4, 9, 10],
        "shared_accused": None,
        "phone": None,
        "vehicle": None,
        "facts": "A locked premises was entered at night and property was reported missing. No shared person, phone, vehicle, tool mark, or location evidence connects this FIR to the other control records.",
        "expected": ["narrative similarity only", "insufficient evidence for a common offender", "false-positive resistance"],
        "negative_control": True,
    },
]


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(OUTPUT / f"{name}.csv")


def _district_resources():
    units = _load("Unit")
    employees = _load("Employee")
    courts = _load("Court")
    cases = _load("CaseMaster")
    resources = {}
    for district_id in sorted({district for scenario in SCENARIOS for district in scenario["districts"]}):
        station = units[units["DistrictID"] == district_id].iloc[0]
        district_employees = employees[employees["DistrictID"] == district_id]
        officer = district_employees.iloc[0] if not district_employees.empty else employees.iloc[0]
        court_rows = courts[courts["DistrictID"] == district_id]
        court = court_rows.iloc[0] if not court_rows.empty else courts.iloc[0]
        district_cases = cases[cases["_DistrictID"] == district_id]
        resources[district_id] = {
            "station": int(station["UnitID"]),
            "officer": int(officer["EmployeeID"]),
            "court": int(court["CourtID"]),
            "lat": round(float(district_cases["latitude"].median()), 6),
            "lng": round(float(district_cases["longitude"].median()), 6),
        }
    return resources


def generate():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    offences = _load("CrimeSubHead").set_index("CrimeHeadName").to_dict("index")
    resources = _district_resources()
    rows = {name: [] for name in ("CaseMaster", "Accused", "Victim", "ComplainantDetails", "ArrestSurrender", "ChargesheetDetails")}
    manifest = {"synthetic": True, "idempotent": True, "baseCaseId": BASE_CASE_ID, "scenarios": []}
    base_time = datetime(2025, 1, 10, 19, 30)
    accused_id = 8_300_000
    victim_id = 8_400_000
    complainant_id = 8_500_000
    arrest_id = 8_600_000
    chargesheet_id = 8_700_000

    for scenario_index, scenario in enumerate(SCENARIOS):
        offence = offences[scenario["offence"]]
        case_ids = []
        crime_numbers = []
        for case_index, district_id in enumerate(scenario["districts"]):
            case_id = BASE_CASE_ID + scenario_index * 100 + case_index + 1
            case_ids.append(case_id)
            crime_no = f"SYN-{scenario['code'][:8]}-{case_index + 1:02d}"
            crime_numbers.append(crime_no)
            incident = base_time + timedelta(days=scenario_index * 24 + case_index * 3, minutes=case_index * 7)
            registered = incident + timedelta(hours=8 + case_index)
            resource = resources[district_id]
            identifiers = []
            if scenario["negative_control"]:
                identifiers.extend([f"phone 90000-{88010 + case_index:05d}", f"vehicle KA-00 NC {8800 + case_index}"])
            else:
                if scenario["phone"]:
                    identifiers.append(f"phone {scenario['phone']}")
                if scenario["vehicle"]:
                    identifiers.append(f"vehicle {scenario['vehicle']}")
            identifier_text = (" Recorded identifiers: " + ", ".join(identifiers) + ".") if identifiers else ""
            narrative = (
                f"SYNTHETIC USE CASE {scenario['code']}: {scenario['facts']}"
                f" This is scenario record {case_index + 1} of 6.{identifier_text}"
            )
            has_chargesheet = scenario["code"] == "COURT_READINESS" and case_index in {0, 2, 4}
            rows["CaseMaster"].append({
                "CaseMasterID": case_id,
                "CrimeNo": crime_no,
                "CaseNo": f"SYN25{scenario_index + 1:02d}{case_index + 1:02d}",
                "CrimeRegisteredDate": registered.date().isoformat(),
                "PolicePersonID": resource["officer"],
                "PoliceStationID": resource["station"],
                "CaseCategoryID": 1,
                "GravityOffenceID": 2,
                "CrimeMajorHeadID": int(offence["CrimeHeadID"]),
                "CrimeMinorHeadID": int(offence["CrimeSubHeadID"]),
                "CaseStatusID": 2 if has_chargesheet else 1,
                "CourtID": resource["court"],
                "IncidentFromDate": incident.strftime("%Y-%m-%d %H:%M:%S"),
                "IncidentToDate": (incident + timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M:%S"),
                "InfoReceivedPSDate": (incident + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "latitude": resource["lat"] + case_index * 0.0011,
                "longitude": resource["lng"] + case_index * 0.0011,
                "BriefFacts": narrative,
                "_DistrictID": district_id,
                "_SubheadName": scenario["offence"],
            })

            victim_id += 1
            complainant_id += 1
            victim_name = f"SYN VICTIM {scenario_index + 1:02d}-{case_index + 1:02d}"
            rows["Victim"].append({
                "VictimMasterID": victim_id, "CaseMasterID": case_id,
                "VictimName": victim_name, "AgeYear": 25 + case_index,
                "GenderID": 2, "VictimPolice": "0",
            })
            rows["ComplainantDetails"].append({
                "ComplainantID": complainant_id, "CaseMasterID": case_id,
                "ComplainantName": victim_name, "AgeYear": 25 + case_index,
                "OccupationID": 1, "ReligionID": 1, "CasteID": 1, "GenderID": 2,
            })

            accused_id += 1
            primary_name = scenario["shared_accused"] or f"SYN CONTROL PERSON {case_index + 1:02d}"
            rows["Accused"].append({
                "AccusedMasterID": accused_id, "CaseMasterID": case_id,
                "AccusedName": primary_name, "AgeYear": 28 + (case_index % 5),
                "GenderID": 1, "PersonID": "A1",
            })
            primary_accused_id = accused_id
            if not scenario["negative_control"] and case_index in {1, 3, 5}:
                accused_id += 1
                rows["Accused"].append({
                    "AccusedMasterID": accused_id, "CaseMasterID": case_id,
                    "AccusedName": f"SYN ASSOCIATE {scenario_index + 1:02d}",
                    "AgeYear": 24 + case_index, "GenderID": 1, "PersonID": "A2",
                })

            if case_index in {1, 4} and not scenario["negative_control"]:
                arrest_id += 1
                rows["ArrestSurrender"].append({
                    "ArrestSurrenderID": arrest_id, "CaseMasterID": case_id,
                    "ArrestSurrenderTypeID": 1,
                    "ArrestSurrenderDate": (registered + timedelta(days=4)).date().isoformat(),
                    "ArrestSurrenderStateId": 1, "ArrestSurrenderDistrictId": district_id,
                    "PoliceStationID": resource["station"], "IOID": resource["officer"],
                    "CourtID": resource["court"], "AccusedMasterID": primary_accused_id,
                    "IsAccused": True, "IsComplainantAccused": False,
                })
            if has_chargesheet:
                chargesheet_id += 1
                rows["ChargesheetDetails"].append({
                    "CSID": chargesheet_id, "CaseMasterID": case_id,
                    "csdate": (registered + timedelta(days=35)).strftime("%Y-%m-%d %H:%M:%S"),
                    "cstype": "A", "PolicePersonID": resource["officer"],
                })

        manifest["scenarios"].append({
            "code": scenario["code"], "title": scenario["title"],
            "caseIds": case_ids, "crimeNumbers": crime_numbers,
            "expectedSignals": scenario["expected"],
            "negativeControl": scenario["negative_control"],
        })

    unique_columns = {
        "CaseMaster": "CaseMasterID", "Accused": "AccusedMasterID",
        "Victim": "VictimMasterID", "ComplainantDetails": "ComplainantID",
        "ArrestSurrender": "ArrestSurrenderID", "ChargesheetDetails": "CSID",
    }
    manifest["rowCounts"] = {}
    for table, table_rows in rows.items():
        frame = pd.DataFrame(table_rows)
        unique = unique_columns[table]
        if frame.empty:
            raise RuntimeError(f"Scenario generator unexpectedly produced no {table} rows")
        if frame[unique].duplicated().any():
            raise RuntimeError(f"Duplicate {unique} in {table}")
        frame.to_csv(DESTINATION / f"{table}.csv", index=False)
        (DESTINATION / f"{table}.import.json").write_text(json.dumps({
            "table_identifier": table, "operation": "upsert", "find_by": unique,
        }, indent=2))
        manifest["rowCounts"][table] = len(frame)

    manifest["totalRows"] = sum(manifest["rowCounts"].values())
    (DESTINATION / "scenario-manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    generate()
