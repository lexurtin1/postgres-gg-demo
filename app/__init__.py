# app/__init__.py
from __future__ import annotations
import os

from flask import Flask, jsonify, redirect, url_for
from flask_login import LoginManager, current_user          # session manager helpers
# I use Flask-Login for sessions and CSRF for form safety; I keep everything
# in one place so I can reason about app configuration during the audit.
from sqlalchemy import text                                  # health check query
from dotenv import load_dotenv
from flask_wtf import CSRFProtect

from .models import db, User                                # ORM handle + User model


def create_app() -> Flask:
    # Load environment so DATABASE_URL / SECRET_KEY work locally.
    # Load .env and allow it to override any stale values from a parent
    # reloader process so config changes take effect without a full shell reset.
    load_dotenv(override=True)

    # Create the Flask application instance.
    app = Flask(__name__)

    # Basic configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    # I keep a default dev secret so the app boots for demos; real deployments
    # must override this via environment.

    # Read the database URL; fail fast if missing.
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set. Add it to .env")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # I disable SQLAlchemy event overhead to keep the app snappy and simple.

    # I set where uploaded files are stored and a simple upload size guard.
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
    # I constrain upload size to protect the server and simplify demos.

    # I ensure the uploads folder exists so the first save doesn't fail.
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize the ORM so models can talk to Postgres.
    db.init_app(app)
    # I initialize the ORM here so models can create sessions against Postgres.

    # Enable CSRF protection across the app.
    CSRFProtect(app)

    # Install Flask-Login for session management.
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)
    # I specify where unauthenticated users get sent so flows are predictable.

    @app.get("/__routes")
    def __routes():
        # I list every registered route so I can quickly sanity‑check the app map.
        return {"routes": sorted([f"{r.endpoint} -> {r.rule}" for r in app.url_map.iter_rules()])}

    @login_manager.user_loader
    def load_user(user_id: str):
        # I tell Flask-Login how to fetch a user by primary key.
        return User.query.get(int(user_id))

    # ---- Routes -------------------------------------------------------------

    @app.get("/health")
    def health():
        # I ping the database; 200 = up, 500 = down. This helps ops verify state.
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "db": "up"}), 200
        except Exception as exc:
            return jsonify({"status": "ok", "db": f"down: {type(exc).__name__}"}), 500

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("auth.dashboard"))
        return redirect(url_for("auth.login"))

    # Register the auth blueprint (signup/login/logout/dashboard).
    from .auth import auth_bp
    app.register_blueprint(auth_bp)
    # I register auth routes (signup/login/logout/dashboard) under their blueprint.

    # Register the uploads blueprint (check-in desk + submissions views).
    from .uploads import uploads_bp
    app.register_blueprint(uploads_bp)
    # I register document upload/check‑in routes for the applicant journey.

    # Register ops blueprint for vendor checks/passports API.
    from .ops import ops_bp
    app.register_blueprint(ops_bp)
    # I expose operational APIs (vendor checks, passport issuance, verification).

    # Register pages blueprint for audit/attestations/settings.
    from .pages import pages_bp
    app.register_blueprint(pages_bp)
    # I wire audit/attestations/settings pages for the prototype navigation.

    return app
