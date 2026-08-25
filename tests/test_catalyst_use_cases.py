import importlib.util
import json
from pathlib import Path

import pandas as pd
from fastapi import HTTPException
from starlette.requests import Request

from backend import app as analytics


ROOT = Path(__file__).resolve().parents[1]


def _generate(tmp_path):
    path = ROOT / "scripts" / "generate_catalyst_use_cases.py"
    spec = importlib.util.spec_from_file_location("catalyst_use_cases", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DESTINATION = tmp_path
    module.generate()
    return json.loads((tmp_path / "scenario-manifest.json").read_text())


def test_catalyst_use_case_seed_is_idempotent_and_relational(tmp_path):
    manifest = _generate(tmp_path)
    cases = pd.read_csv(tmp_path / "CaseMaster.csv")
    accused = pd.read_csv(tmp_path / "Accused.csv")
    victims = pd.read_csv(tmp_path / "Victim.csv")
    complainants = pd.read_csv(tmp_path / "ComplainantDetails.csv")
    arrests = pd.read_csv(tmp_path / "ArrestSurrender.csv")
    chargesheets = pd.read_csv(tmp_path / "ChargesheetDetails.csv")

    assert manifest["synthetic"] is True
    assert manifest["idempotent"] is True
    assert len(manifest["scenarios"]) == 8
    assert manifest["totalRows"] == 230
    assert len(cases) == 48
    assert cases["CaseMasterID"].is_unique
    assert accused["AccusedMasterID"].is_unique
    assert victims["VictimMasterID"].is_unique
    assert complainants["ComplainantID"].is_unique
    assert arrests["ArrestSurrenderID"].is_unique
    assert chargesheets["CSID"].is_unique
    assert cases["CaseMasterID"].min() >= 8_100_000
    assert cases["BriefFacts"].str.startswith("SYNTHETIC USE CASE").all()

    case_ids = set(cases["CaseMasterID"])
    assert set(accused["CaseMasterID"]) <= case_ids
    assert set(victims["CaseMasterID"]) <= case_ids
    assert set(complainants["CaseMasterID"]) <= case_ids
    assert set(arrests["CaseMasterID"]) <= case_ids
    assert set(chargesheets["CaseMasterID"]) <= case_ids
    assert set(arrests["AccusedMasterID"]) <= set(accused["AccusedMasterID"])


def test_positive_links_and_negative_controls_have_known_ground_truth(tmp_path):
    manifest = _generate(tmp_path)
    cases = pd.read_csv(tmp_path / "CaseMaster.csv")
    accused = pd.read_csv(tmp_path / "Accused.csv")

    for scenario in manifest["scenarios"]:
        scenario_cases = cases[cases["CaseMasterID"].isin(scenario["caseIds"])]
        scenario_accused = accused[accused["CaseMasterID"].isin(scenario["caseIds"])]
        assert len(scenario_cases) == 6
        if scenario["negativeControl"]:
            primary = scenario_accused[scenario_accused["PersonID"] == "A1"]
            assert primary["AccusedName"].nunique() == 6
            phones = scenario_cases["BriefFacts"].str.extract(r"(90000-\d{5})")[0]
            vehicles = scenario_cases["BriefFacts"].str.extract(r"(KA-00 NC \d{4})")[0]
            assert phones.nunique() == 6
            assert vehicles.nunique() == 6
        else:
            primary = scenario_accused[scenario_accused["PersonID"] == "A1"]
            assert primary["AccusedName"].nunique() == 1

    court_scenario = next(item for item in manifest["scenarios"] if item["code"] == "COURT_READINESS")
    chargesheets = pd.read_csv(tmp_path / "ChargesheetDetails.csv")
    assert len(chargesheets[chargesheets["CaseMasterID"].isin(court_scenario["caseIds"])]) == 3


def test_seed_endpoint_rejects_invalid_manifest_confirmation(tmp_path, monkeypatch):
    _generate(tmp_path)
    monkeypatch.setattr(analytics, "USE_CASE_SEED_DIR", str(tmp_path))
    monkeypatch.setitem(analytics.data_source_status, "active", "catalyst")
    request = Request({
        "type": "http", "method": "POST", "scheme": "http",
        "path": "/api/internal/seed-synthetic-use-cases", "query_string": b"",
        "headers": [(b"host", b"127.0.0.1"), (b"x-drishti-synthetic-seed", b"wrong")],
        "server": ("127.0.0.1", 8000),
    })

    try:
        analytics.seed_synthetic_use_cases(request)
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("The fixed seed package requires its exact manifest confirmation")
