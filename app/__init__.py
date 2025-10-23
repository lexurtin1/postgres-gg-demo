from __future__ import annotations

"""
I keep this module tiny and focused: load .env, read secrets, build a SQLAlchemy
Engine, and expose a /health check that proves the backend can reach Postgres.
"""

import os
from typing import Tuple

from flask import Flask, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv


def _db_ping(engine: Engine) -> Tuple[bool, str]:
    """I open a short connection and run SELECT 1 to confirm DB is reachable.

    Returns (ok, message). I keep this separate so /health stays very small.
    """
    try:
        with engine.connect() as conn:
            # I use a trivial statement that works on PostgreSQL universally.
            conn.execute(text("SELECT 1"))
        return True, "up"
    except Exception as exc:  # I intentionally keep this broad for a health check
        return False, f"down: {type(exc).__name__}"


def create_app() -> Flask:
    """I create the Flask app, load .env, and prepare the DB Engine.

    - I load environment variables here so the app can read DB creds without
      hardcoding.
    - I read SECRET_KEY and DATABASE_URL from the environment.
    - I build a SQLAlchemy 2.x Engine and attach it to the app for reuse.
    - I register a /health route that pings the DB and returns JSON.
    """

    # I load environment variables first, so later config reads have values.
    load_dotenv()

    app = Flask(__name__)

    # I read the secret key from .env; good enough for local dev.
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-later")

    # I read the database URL from .env; this must be a full SQLAlchemy URL.
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")

    # I create a SQLAlchemy Engine (2.x style) instead of using Flask-SQLAlchemy.
    engine = create_engine(db_url, pool_pre_ping=True, future=True)

    # I store the engine on the app so other modules can reuse it later.
    app.engine = engine  # type: ignore[attr-defined]

    @app.get("/health")
    def health():  # I keep health lightweight and side-effect free.
        ok, db_status = _db_ping(app.engine)  # type: ignore[attr-defined]
        payload = {"status": "ok", "db": "up" if ok else "down"}
        # If DB is unreachable, I still return overall status ok for the app
        # process, but I use HTTP 500 to signal infra is unhealthy.
        return jsonify(payload), (200 if ok else 500)

    @app.get("/")
    def index():
        # I provide a simple landing endpoint to avoid confusion if I hit the
        # root URL; this tells me where the health check lives.
        return jsonify({
            "app": "Governance Gateway Demo",
            "hint": "Use /health to check DB connectivity"
        }), 200

    return app
