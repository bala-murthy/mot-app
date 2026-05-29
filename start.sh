#!/bin/bash
# MOT Nexus – Startup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  uv venv .venv
fi

echo "Installing / verifying dependencies..."
uv pip install -r backend/requirements.txt --quiet

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  MOT Nexus – Enterprise Resourcing      │"
echo "│  Management Portal                      │"
echo "├─────────────────────────────────────────┤"
echo "│  Starting server on http://localhost:8000│"
echo "│  API docs: http://localhost:8000/api/docs│"
echo "└─────────────────────────────────────────┘"
echo ""

# Seed sample data if DB doesn't exist
if [ ! -f "mot_nexus.db" ]; then
  echo "No database found — seeding sample data..."
  PYTHONPATH="$SCRIPT_DIR" .venv/bin/python backend/seed_data.py
  echo ""
fi

PYTHONPATH="$SCRIPT_DIR" .venv/bin/uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
