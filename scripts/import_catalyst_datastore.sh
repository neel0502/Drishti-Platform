#!/bin/sh
set -eu

ENVIRONMENT="${1:-development}"
STAGE_DIR="${2:-.catalyst-migration}"
PRODUCTION_FLAG=""
if [ "$ENVIRONMENT" = "production" ]; then
  PRODUCTION_FLAG="--production"
fi

TABLES="
District
Unit
CrimeHead
CrimeSubHead
CaseStatusMaster
OccupationMaster
CaseMaster
Accused
Victim
ComplainantDetails
ArrestSurrender
ChargesheetDetails
"

for table in $TABLES; do
  config="$STAGE_DIR/$table.import.json"
  csv="$STAGE_DIR/$table.csv"
  if [ ! -f "$config" ]; then
    echo "Missing import configuration: $config" >&2
    exit 1
  fi
  if [ ! -f "$csv" ]; then
    echo "Missing staged CSV: $csv" >&2
    exit 1
  fi
  catalyst ds:import "$csv" --config "$config" $PRODUCTION_FLAG
done
