#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/.appsail-build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

python3 -m pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 311 \
  --ignore-requires-python \
  --only-binary=:all: \
  --upgrade \
  --requirement "$ROOT_DIR/requirements.txt" \
  --target "$BUILD_DIR"

cp -R "$ROOT_DIR/backend" "$BUILD_DIR/backend"
cp -R "$ROOT_DIR/frontend" "$BUILD_DIR/frontend"
cp -R "$ROOT_DIR/output" "$BUILD_DIR/output"
cp "$ROOT_DIR/launcher.py" "$BUILD_DIR/launcher.py"
python3 "$ROOT_DIR/scripts/generate_catalyst_use_cases.py" >/dev/null
cp -R "$ROOT_DIR/.catalyst-use-cases" "$BUILD_DIR/use-case-data"
mkdir -p "$BUILD_DIR/deployment/catalyst"
cp "$ROOT_DIR/deployment/catalyst/datastore-schema.json" "$BUILD_DIR/deployment/catalyst/datastore-schema.json"

python3 "$ROOT_DIR/scripts/prepare_catalyst_import.py" \
  --environment development \
  --case-limit "${DRISHTI_BOOTSTRAP_CASE_LIMIT:-2000}" \
  --destination .catalyst-migration
cp -R "$ROOT_DIR/.catalyst-migration" "$BUILD_DIR/bootstrap-data"

echo "AppSail bundle created at $BUILD_DIR"
