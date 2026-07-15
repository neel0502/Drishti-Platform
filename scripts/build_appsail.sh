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
  --only-binary=:all: \
  --upgrade \
  --requirement "$ROOT_DIR/requirements.txt" \
  --target "$BUILD_DIR"

cp -R "$ROOT_DIR/backend" "$BUILD_DIR/backend"
cp -R "$ROOT_DIR/frontend" "$BUILD_DIR/frontend"
cp -R "$ROOT_DIR/output" "$BUILD_DIR/output"

echo "AppSail bundle created at $BUILD_DIR"
