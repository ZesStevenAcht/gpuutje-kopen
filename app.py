"""Flask web app for GPU price tracker."""

import atexit
import os
import signal
import sys
from pathlib import Path

# Add src to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from gpuutje_kopen.routes.public import public
from gpuutje_kopen.search_worker import start_worker_thread, stop_worker_thread


# ── App factory ───────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32).hex())

    # Trust X-Forwarded-For from 2 proxies (Cloudflare → nginx)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1, x_host=1)

    # Register blueprints
    app.register_blueprint(public)

    # Background search worker (idempotent start)
    _start_worker()

    return app


# ── Worker lifecycle ──────────────────────────────────────────────────

_worker_thread = None


def _start_worker():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_thread = start_worker_thread()


atexit.register(stop_worker_thread)


def _handle_shutdown(signum, frame):
    stop_worker_thread()
    sys.exit(0)


for _sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(_sig, _handle_shutdown)


# ── Entrypoint ────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
