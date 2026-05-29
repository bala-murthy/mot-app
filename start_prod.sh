#!/bin/bash
# MOT Nexus – Production Start Script
# Run this on the hosting server.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR"

# Use absolute path for the database so it never moves regardless of cwd
export DATABASE_URL="sqlite:///$SCRIPT_DIR/mot_nexus.db"

echo "==================================================="
echo "  MOT Nexus – Enterprise Resourcing Portal"
echo "  Starting in PRODUCTION mode"
echo "  Database : $DATABASE_URL"
echo "  Port     : 8000"
echo "==================================================="

# Seed sample data only if the DB is brand new (no requirements table yet)
if [ ! -f "$SCRIPT_DIR/mot_nexus.db" ]; then
  echo "No database found — seeding sample data..."
  .venv/bin/python backend/seed_data.py
fi

# Production: no --reload, multiple workers for concurrency
# Adjust --workers based on CPU cores (rule of thumb: 2 × CPU + 1)
exec .venv/bin/uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --access-log
