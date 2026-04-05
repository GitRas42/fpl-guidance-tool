#!/usr/bin/env bash
# Render.com build script — installs deps and builds React frontend
set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Building React frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Copying build to static/ ==="
rm -rf static
cp -r frontend/build static

echo "=== Build complete ==="
