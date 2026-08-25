"""Catalyst Data Store access with explicit, observable CSV fallback."""

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
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
    "agent_runs": "DrishtiAgentRun",
}

_app = None
_error = None


def _encode_value(value, data_type):
    if value is None or value == "":
        return None
    if data_type == "BIGINT":
        return int(value)
    if data_type == "DOUBLE":
        return float(value)
    if data_type == "BOOLEAN":
        return str(value).strip().lower() in {"1", "true", "yes"}
    return value


def _row_key(row, unique_columns):
    return tuple(str(row.get(column, "")) for column in unique_columns)


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


def initialize_from_request(request):
    """Initialize the server SDK with Catalyst's request-scoped credentials."""
    global _app, _error
    try:
        import zcatalyst_sdk

        _app = zcatalyst_sdk.initialize(req=request)
        _error = None
        return _app
    except Exception as exc:
        _error = str(exc)
        raise


def last_error():
    return _error


def _flatten_zcql_row(row, table_name):
    if isinstance(row, dict) and table_name in row and isinstance(row[table_name], dict):
        return row[table_name]
    return row


def fetch_table(table_name, page_size=300):
    """Read a complete Data Store table through Catalyst continuation tokens."""
    app = get_app()
    if app is None:
        raise RuntimeError(_error or "Catalyst SDK initialization failed")
    table = app.datastore().table(table_name)
    rows = []
    next_token = None
    while True:
        page = table.get_paged_rows(next_token=next_token, max_rows=page_size)
        rows.extend(page.get("data") or [])
        next_token = page.get("next_token")
        if not next_token:
            return rows


def load_relational_tables():
    return {table: fetch_table(table) for table in CATALYST_TABLE_FILES}


def bootstrap_datastore(data_dir, schema_path, batch_size=100, table_names=None):
    """Reconcile Data Store tables exactly to the validated staged CSV package."""
    app = get_app()
    if app is None:
        raise RuntimeError(_error or "Catalyst SDK initialization failed")

    data_dir = Path(data_dir)
    schema = json.loads(Path(schema_path).read_text())
    report = {"tables": [], "insertedRows": 0}

    for table_schema in schema["tables"]:
        table_name = table_schema["name"]
        if table_names and table_name not in table_names:
            continue
        csv_path = data_dir / f"{table_name}.csv"
        if not csv_path.exists():
            continue

        unique_columns = table_schema["unique"]
        if isinstance(unique_columns, str):
            unique_columns = [unique_columns]
        column_types = table_schema.get("columns", {})
        existing_rows = fetch_table(table_name)
        desired_rows = {}

        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            for raw_row in csv.DictReader(handle):
                key = _row_key(raw_row, unique_columns)
                encoded = {
                    column: converted
                    for column, value in raw_row.items()
                    if column in column_types
                    and (converted := _encode_value(value, column_types[column])) is not None
                }
                desired_rows[key] = encoded

        existing_by_key = {}
        for row in existing_rows:
            existing_by_key.setdefault(_row_key(row, unique_columns), []).append(row)

        catalyst_table = app.datastore().table(table_name)
        deleted = 0
        for key, rows in existing_by_key.items():
            keep_count = 1 if key in desired_rows else 0
            for row in rows[keep_count:]:
                catalyst_table.delete_row(row["ROWID"])
                deleted += 1

        pending = [
            row for key, row in desired_rows.items()
            if key not in existing_by_key
        ]
        inserted = 0
        for start in range(0, len(pending), batch_size):
            batch = pending[start:start + batch_size]
            catalyst_table.insert_rows(batch)
            inserted += len(batch)

        final_rows = len(fetch_table(table_name))
        report["tables"].append({
            "table": table_name,
            "existingRows": len(existing_rows),
            "insertedRows": inserted,
            "deletedRows": deleted,
            "expectedRows": len(desired_rows),
            "finalRows": final_rows,
            "matchesExpected": final_rows == len(desired_rows),
        })
        report["insertedRows"] += inserted
        print(
            f"[BOOTSTRAP] {table_name}: inserted {inserted}, deleted {deleted}, "
            f"final {final_rows}/{len(desired_rows)}"
        )

    return report


def insert_workflow_row(kind, row):
    app = get_app()
    if app is None:
        raise RuntimeError(_error or "Catalyst SDK initialization failed")
    table_name = WORKFLOW_TABLES[kind]
    encoded = {}
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            encoded[key] = json.dumps(value, ensure_ascii=False)
            continue
        if key.endswith("At") and isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                encoded[key] = parsed.strftime("%Y-%m-%d %H:%M:%S")
                continue
            except ValueError:
                pass
        encoded[key] = value
    return app.datastore().table(table_name).insert_row(encoded)


def insert_schema_rows(rows_by_table):
    """Insert a small schema-faithful FIR record graph into Catalyst."""
    app = get_app()
    if app is None:
        raise RuntimeError(_error or "Catalyst SDK initialization failed")
    created = {}
    for table_name, rows in rows_by_table.items():
        if rows:
            table = app.datastore().table(table_name)
            created[table_name] = [table.insert_row(row) for row in rows]
    return created


def fetch_workflow_rows(kind):
    table_name = WORKFLOW_TABLES[kind]
    rows = fetch_table(table_name)
    for row in rows:
        for key in ("CaseIDs", "Evidence", "Gaps", "Cases", "Tools", "TokenUsage"):
            if key in row and isinstance(row[key], str):
                try:
                    row[key] = json.loads(row[key])
                except json.JSONDecodeError:
                    pass
    return rows
