#!/bin/sh
set -eu

ENVIRONMENT="${1:-development}"
STAGE_DIR="${2:-.catalyst-migration}"
PROJECT_ID="${3:-}"
PRODUCTION_FLAG=""
PROJECT_FLAG=""
if [ "$ENVIRONMENT" = "production" ]; then
  PRODUCTION_FLAG="--production"
fi
if [ -n "$PROJECT_ID" ]; then
  PROJECT_FLAG="-p $PROJECT_ID"
fi

TABLES="
State
District
UnitType
Unit
Rank
Designation
Employee
Court
CaseCategory
GravityOffence
CrimeHead
CrimeSubHead
CaseStatusMaster
OccupationMaster
ReligionMaster
CasteMaster
Act
Section
CaseMaster
Accused
Victim
ComplainantDetails
ActSectionAssociation
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
  catalyst $PROJECT_FLAG ds:import "$csv" --config "$config" $PRODUCTION_FLAG
done
