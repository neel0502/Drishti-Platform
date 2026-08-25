#!/bin/sh
set -eu

PROJECT_ID="${1:-50733000000039003}"
STAGE_DIR="${2:-.catalyst-use-cases}"

if [ ! -f "$STAGE_DIR/scenario-manifest.json" ]; then
  echo "Missing $STAGE_DIR/scenario-manifest.json; run scripts/generate_catalyst_use_cases.py first." >&2
  exit 1
fi

# Parent rows must exist before relational children are imported. Every config
# uses an upsert against a reserved unique ID, making this safe to rerun.
for table in CaseMaster Accused Victim ComplainantDetails ArrestSurrender ChargesheetDetails; do
  csv="$STAGE_DIR/$table.csv"
  config="$STAGE_DIR/$table.import.json"
  if [ ! -f "$csv" ] || [ ! -f "$config" ]; then
    echo "Missing staged import artifacts for $table" >&2
    exit 1
  fi
  catalyst -p "$PROJECT_ID" ds:import "$csv" --config "$config"
done
