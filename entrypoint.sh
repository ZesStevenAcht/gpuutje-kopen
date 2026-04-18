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

if [ ! -f /app/data/gpuutje.db ]; then
    echo "[entrypoint] No database found — copying built-in DB to /app/data/"
    cp /app/data_builtin/gpuutje.db /app/data/gpuutje.db
fi

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
