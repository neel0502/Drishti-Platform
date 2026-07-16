#!/usr/bin/env python3
"""Validate and stage schema-faithful CSVs for Catalyst Data Store import."""

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
MANIFEST = ROOT / "deployment" / "catalyst" / "datastore-schema.json"


def clean_frame(frame, table):
    cleaned = frame.copy()
    column_types = table.get("columns", {})
    for column, data_type in column_types.items():
        if column not in cleaned:
            continue
        if column == "GenderID" and data_type == "BIGINT":
            cleaned[column] = cleaned[column].map(
                lambda value: {"M": 1, "F": 2, "T": 3}.get(str(value).strip().upper(), value)
            )
        elif data_type == "DATE":
            parsed = pd.to_datetime(cleaned[column], errors="coerce")
            cleaned[column] = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), "")
        elif data_type == "DATETIME":
            parsed = pd.to_datetime(cleaned[column], errors="coerce")
            cleaned[column] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").where(parsed.notna(), "")
        elif data_type == "BOOLEAN":
            cleaned[column] = cleaned[column].map(
                lambda value: "" if pd.isna(value) or value == "" else
                "true" if str(value).strip().lower() in {"1", "true", "yes"} else "false"
            )
    return cleaned.replace({pd.NA: "", float("nan"): ""})


def add_derived_keys(frame, table):
    derived = table.get("derivedKeys", {})
    for target, source_columns in derived.items():
        frame[target] = frame[source_columns].fillna("").astype(str).agg("::".join, axis=1)
    return frame


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
                registered = pd.to_datetime(frame["CrimeRegisteredDate"], errors="coerce")
                frame = frame.assign(_sample_month=registered.dt.to_period("M"))
                months = sorted(frame["_sample_month"].dropna().unique())
                base_size, remainder = divmod(args.case_limit, len(months))
                sampled = []
                for index, month in enumerate(months):
                    group = frame[frame["_sample_month"] == month]
                    month_size = base_size + (1 if index >= len(months) - remainder else 0)
                    sampled.append(
                        group.sample(
                            n=min(month_size, len(group)),
                            random_state=2026 + index,
                        )
                    )
                frame = pd.concat(sampled).drop(columns="_sample_month")
                selected_case_ids = set(frame["CaseMasterID"].astype(int))
            elif "CaseMasterID" in frame.columns and selected_case_ids is not None:
                frame = frame[frame["CaseMasterID"].isin(selected_case_ids)]
        frame = add_derived_keys(frame, table)
        unique = table["unique"]
        duplicate_count = int(frame.duplicated(unique).sum())
        frame = frame.drop_duplicates(unique)
        staged = clean_frame(frame, table)
        staged.to_csv(destination / f"{table['name']}.csv", index=False)
        config = {
            "table_identifier": table["name"],
            "operation": "upsert",
            "find_by": unique
        }
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
