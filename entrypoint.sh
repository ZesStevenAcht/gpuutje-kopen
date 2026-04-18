#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# Docker entrypoint for GPUutje Kopen
#
# Ensures the database exists and schema is up to date, then starts
# the application.
# ──────────────────────────────────────────────────────────────────────

set -e

# Ensure the data directory exists (in case no volume is mounted)
mkdir -p /app/data

echo "[entrypoint] Initialising database..."
python -c "
import sys
sys.path.insert(0, '/app/src')
import gpuutje_kopen.db as db
db.init_db()
gpus = db._conn().execute('SELECT COUNT(*) FROM gpus').fetchone()[0]
print(f'[entrypoint] Database ready — {gpus} GPUs')
"

echo "[entrypoint] Starting application..."
exec "$@"
