"""Catalyst Data Store access with explicit, observable CSV fallback."""

import json
import os
from typing import Iterable


CATALYST_TABLE_FILES = {
    "CaseMaster": "CaseMaster.csv",
    "Accused": "Accused.csv",
    "Victim": "Victim.csv",
    "ComplainantDetails": "ComplainantDetails.csv",
    "ArrestSurrender": "ArrestSurrender.csv",
    "ChargesheetDetails": "ChargesheetDetails.csv",
    "District": "District.csv",
    "Unit": "Unit.csv",
    "CrimeHead": "CrimeHead.csv",
    "CrimeSubHead": "CrimeSubHead.csv",
    "CaseStatusMaster": "CaseStatusMaster.csv",
    "OccupationMaster": "OccupationMaster.csv",
    "State": "State.csv",
    "UnitType": "UnitType.csv",
    "Rank": "Rank.csv",
    "Designation": "Designation.csv",
    "Employee": "Employee.csv",
    "Court": "Court.csv",
    "CaseCategory": "CaseCategory.csv",
    "GravityOffence": "GravityOffence.csv",
    "ReligionMaster": "ReligionMaster.csv",
    "CasteMaster": "CasteMaster.csv",
    "Act": "Act.csv",
    "Section": "Section.csv",
    "ActSectionAssociation": "ActSectionAssociation.csv",
}

WORKFLOW_TABLES = {
    "hypotheses": "DrishtiHypothesisBoard",
    "actions": "DrishtiOperationalAction",
    "imports": "DrishtiImportJob",
}

_app = None
_error = None


def catalyst_requested():
    configured = os.getenv("DRISHTI_DATA_SOURCE", "auto").lower()
    if configured == "csv":
        return False
    if configured == "catalyst":
        return True
    return bool(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT"))


def get_app():
    global _app, _error
    if _app is not None:
        return _app
    try:
        import zcatalyst_sdk

        _app = zcatalyst_sdk.initialize()
        _error = None
        return _app
    except Exception as exc:
        _error = str(exc)
        return None


def last_error():
    return _error


def _flatten_zcql_row(row, table_name):
    if isinstance(row, dict) and table_name in row and isinstance(row[table_name], dict):
        return row[table_name]
    return row


def fetch_table(table_name, page_size=2000):
    """Read a complete Data Store table through bounded ZCQL pages."""
    app = get_app()
    if app is None:
        raise RuntimeError(_error or "Catalyst SDK initialization failed")
    service = app.zcql()
    rows = []
    offset = 0
    while True:
        query = f"SELECT * FROM {table_name} LIMIT {page_size} OFFSET {offset}"
        page = service.execute_query(query) or []
        normalized = [_flatten_zcql_row(row, table_name) for row in page]
        rows.extend(normalized)
        if len(normalized) < page_size:
            break
        offset += page_size
    return rows


def load_relational_tables():
    return {table: fetch_table(table) for table in CATALYST_TABLE_FILES}


def insert_workflow_row(kind, row):
    app = get_app()
    if app is None:
        raise RuntimeError(_error or "Catalyst SDK initialization failed")
    table_name = WORKFLOW_TABLES[kind]
    encoded = {
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        for key, value in row.items()
        if value is not None
    }
    return app.datastore().table(table_name).insert_row(encoded)


def fetch_workflow_rows(kind):
    table_name = WORKFLOW_TABLES[kind]
    rows = fetch_table(table_name)
    for row in rows:
        for key in ("CaseIDs", "Evidence", "Gaps", "Cases"):
            if key in row and isinstance(row[key], str):
                try:
                    row[key] = json.loads(row[key])
                except json.JSONDecodeError:
                    pass
    return rows
