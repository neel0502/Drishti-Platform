#!/usr/bin/env python3
"""Build Catalyst IaC templates from an authentic exported project template."""

import argparse
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "deployment" / "catalyst" / "datastore-schema.json"

TYPE_PROPERTIES = {
    "BIGINT": {"data_type": "bigint", "max_length": 19, "decimal_digits": 2},
    "VARCHAR": {"data_type": "varchar", "max_length": 255, "decimal_digits": 2},
    "BOOLEAN": {"data_type": "boolean", "max_length": 5, "decimal_digits": 2},
    "DATE": {"data_type": "date", "max_length": 20, "decimal_digits": 2},
    "DATETIME": {"data_type": "datetime", "max_length": 20, "decimal_digits": 2},
    "DOUBLE": {"data_type": "double", "max_length": 20, "decimal_digits": 6},
    "TEXT": {"data_type": "text", "max_length": 0, "decimal_digits": 2},
}


def table_resource(name):
    return {
        "type": "table",
        "name": name,
        "properties": {"table_name": name},
        "dependsOn": [],
    }


def column_resource(table, column, data_type, unique, indexed):
    properties = {
        "audit_consent": False,
        "column_name": column,
        "is_unique": column == unique,
        "is_mandatory": column == unique,
        "search_index_enabled": column in indexed,
        "table_id": table,
        "table_name": table,
        **TYPE_PROPERTIES[data_type],
    }
    return {
        "type": "column",
        "name": f"{table}-{column}",
        "properties": properties,
        "dependsOn": [f"Datastore.table.{table}"],
    }


def access_resources(table):
    dependency = [f"Datastore.table.{table}"]
    return [
        {
            "type": "tableScope",
            "name": f"{table}-App Administrator",
            "properties": {
                "role_name": "App Administrator",
                "table_scope": "GLOBAL",
                "type": "App Administrator",
                "table_name": table,
            },
            "dependsOn": dependency,
        },
        {
            "type": "tableScope",
            "name": f"{table}-App User",
            "properties": {
                "role_name": "App User",
                "table_scope": "GLOBAL",
                "type": "App User",
                "table_name": table,
            },
            "dependsOn": dependency,
        },
        {
            "type": "tablePermission",
            "name": f"{table}-App Administrator",
            "properties": {
                "role_name": "App Administrator",
                "type": "App Administrator",
                "table_permissions": ["SELECT", "UPDATE", "INSERT", "DELETE"],
                "table_name": table,
            },
            "dependsOn": dependency,
        },
        {
            "type": "tablePermission",
            "name": f"{table}-App User",
            "properties": {
                "role_name": "App User",
                "type": "App User",
                "table_permissions": ["SELECT"],
                "table_name": table,
            },
            "dependsOn": dependency,
        },
    ]


def load_export_template(export_zip):
    with zipfile.ZipFile(export_zip) as archive:
        template_name = next(
            name for name in archive.namelist()
            if name.startswith("project-template") and name.endswith(".json")
        )
        return json.loads(archive.read(template_name))


def build_datastore(schema, selected_names):
    resources = []
    for table in schema["tables"]:
        if selected_names and table["name"] not in selected_names:
            continue
        name = table["name"]
        resources.append(table_resource(name))
        indexes = set(table.get("indexes", []))
        for column, data_type in table["columns"].items():
            resources.append(
                column_resource(name, column, data_type, table["unique"], indexes)
            )
        resources.extend(access_resources(name))
    return resources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-zip", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--tables", nargs="*")
    parser.add_argument("--include-appsail", action="store_true")
    args = parser.parse_args()

    export_zip = Path(args.export_zip).resolve()
    destination = Path(args.destination).resolve()
    work = destination.with_suffix("")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    template = load_export_template(export_zip)
    schema = json.loads(SCHEMA.read_text())
    template["components"]["Datastore"] = build_datastore(
        schema, set(args.tables or [])
    )
    if not args.include_appsail:
        template["components"]["AppSail"] = []

    template_path = work / "project-template-1.0.0.json"
    template_path.write_text(json.dumps(template, indent=2))

    if args.include_appsail:
        with zipfile.ZipFile(export_zip) as source:
            for name in source.namelist():
                if name.startswith("appsail/"):
                    source.extract(name, work)

    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in work.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(work))

    print(json.dumps({
        "zip": str(destination),
        "tables": [
            table["name"] for table in schema["tables"]
            if not args.tables or table["name"] in set(args.tables)
        ],
        "includeAppSail": args.include_appsail,
    }, indent=2))


if __name__ == "__main__":
    main()
