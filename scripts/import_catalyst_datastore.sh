#!/bin/sh
set -eu

ENVIRONMENT="${1:-development}"
STAGE_DIR="${2:-.catalyst-migration}"
PRODUCTION_FLAG=""
if [ "$ENVIRONMENT" = "production" ]; then
  PRODUCTION_FLAG="--production"
fi

for config in "$STAGE_DIR"/*.import.json; do
  table="$(basename "$config" .import.json)"
  csv="$STAGE_DIR/$table.csv"
  if [ ! -f "$csv" ]; then
    echo "Skipping $table: staged CSV not found"
    continue
  fi
  catalyst ds:import "$csv" --config "$config" $PRODUCTION_FLAG
done
