#!/usr/bin/env python3
"""Validate and stage schema-faithful CSVs for Catalyst Data Store import."""

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
MANIFEST = ROOT / "deployment" / "catalyst" / "datastore-schema.json"


def clean_frame(frame):
    cleaned = frame.copy()
    for column in cleaned.columns:
        if "Date" in column or column.lower().endswith("date"):
            parsed = pd.to_datetime(cleaned[column], errors="coerce")
            cleaned[column] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").where(parsed.notna(), "")
    return cleaned.replace({pd.NA: "", float("nan"): ""})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=("development", "production"), default="development")
    parser.add_argument("--case-limit", type=int, default=3000)
    parser.add_argument("--destination", default=".catalyst-migration")
    args = parser.parse_args()
    destination = ROOT / args.destination
    destination.mkdir(parents=True, exist_ok=True)
    schema = json.loads(MANIFEST.read_text())
    selected_case_ids = None
    report = {"environment": args.environment, "tables": []}

    for table in schema["tables"]:
        source = table.get("source")
        if not source:
            continue
        frame = pd.read_csv(OUTPUT / source)
        original = len(frame)
        if args.environment == "development":
            if table["name"] == "CaseMaster":
                frame = frame.sort_values("CrimeRegisteredDate", ascending=False).head(args.case_limit)
                selected_case_ids = set(frame["CaseMasterID"].astype(int))
            elif "CaseMasterID" in frame.columns and selected_case_ids is not None:
                frame = frame[frame["CaseMasterID"].isin(selected_case_ids)]
        unique = table["unique"]
        duplicate_count = int(frame.duplicated(unique).sum())
        frame = frame.drop_duplicates(unique)
        staged = clean_frame(frame)
        staged.to_csv(destination / f"{table['name']}.csv", index=False)
        config = {
            "table_identifier": table["name"],
            "operation": "upsert",
            "find_by": unique
        }
        if table.get("foreignKeys"):
            config["fk_mapping"] = [
                {"local_column": item["local"], "reference_column": item["reference"]}
                for item in table["foreignKeys"]
            ]
        (destination / f"{table['name']}.import.json").write_text(json.dumps(config, indent=2))
        report["tables"].append({
            "table": table["name"], "sourceRows": original, "stagedRows": len(staged),
            "duplicatesRejected": duplicate_count
        })

    total = sum(item["stagedRows"] for item in report["tables"])
    report["totalStagedRows"] = total
    if args.environment == "development" and total > 24000:
        raise SystemExit(f"Development package has {total} rows; reduce --case-limit to remain below 25,000.")
    (destination / "validation-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
