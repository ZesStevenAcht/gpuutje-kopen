"""Standalone admin web interface – runs on port 5001."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from flask import Flask
from gpuutje_kopen.routes.admin import admin


def create_admin_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["SECRET_KEY"] = os.environ.get("ADMIN_SECRET_KEY", os.urandom(32).hex())
    app.register_blueprint(admin)
    return app


app = create_admin_app()

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001, use_reloader=False)
