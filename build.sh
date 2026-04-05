#!/usr/bin/env bash
# Build script: compiles React frontend and copies to /static for Flask to serve.
set -e

echo "=== Building FPL Guidance Tool ==="

# 1. Install and build React frontend
echo "Installing frontend dependencies..."
cd frontend
npm install
echo "Building React app..."
npm run build
cd ..

# 2. Copy build output to /static (Flask serves from here)
echo "Copying build to static/..."
rm -rf static
cp -r frontend/build static

echo "=== Build complete ==="
echo "Run with: python app.py"
echo "Or production: gunicorn app:app --bind 0.0.0.0:5000"
