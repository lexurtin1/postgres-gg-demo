# app/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash  # render pages and navigate
from flask_login import login_user, logout_user, login_required, current_user    # manage sessions
from werkzeug.security import generate_password_hash, check_password_hash        # hash + verify passwords
from sqlalchemy import func
from datetime import datetime, timedelta
from .models import db, User, Submission, Document                               # read/write user records
"""I group all authentication and applicant dashboard routes here so I can
keep identity, session management, and onboarding status in one clear module."""
from .forms import LoginForm, SignupForm

auth_bp = Blueprint('auth', __name__, template_folder='templates')               # group auth routes
# I mount auth views on their own blueprint to keep imports minimal in create_app.

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # I show a signup form and create a user with a unique username derived
    # from email so the DB constraints are always satisfied in demos.
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        if User.query.filter(func.lower(User.email) == email).first():
            flash("Account already exists. Please log in.", "info")
            return redirect(url_for("auth.login"))

        base_username = (email.split("@", 1)[0] or "user").lower()
        candidate = base_username
        suffix = 1
        while User.query.filter_by(username=candidate).first() is not None:
            suffix += 1
            candidate = f"{base_username}{suffix}"

        user = User(
            username=candidate,
            email=email,
            password_hash=generate_password_hash(password),
            user_type=form.role.data or "applicant",  # set role from form (applicant/vendor)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome! Your account is active.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("signup.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # I authenticate a user by email/password and start a session with remember
    # turned on to make the demo feel seamless across reloads.
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        user = User.query.filter(func.lower(User.email) == email).first()
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            flash("Logged in successfully.", "success")
            # If the account is vendor, land on Cases; otherwise dashboard.
            desired = (form.role.data or '').lower()
            if user.user_type == 'vendor':
                return redirect(url_for("pages.cases_index"))
            # If user asked for vendor but account is applicant, warn and send to applicant dashboard.
            if desired == 'vendor' and user.user_type != 'vendor':
                flash("This account is not a vendor. Showing applicant dashboard.", "warning")
            return redirect(url_for("auth.dashboard"))
        flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()                                        # I end the session on logout.
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/dashboard")
@login_required
def dashboard():
    # Redirect vendors to their cases workspace instead of applicant dashboard.
    if getattr(current_user, 'user_type', None) == 'vendor':
        return redirect(url_for('pages.cases_index'))
    # I compute live document status for the current user so the UI can show
    # progress and what's missing (Company certificate, UBO, Proof of address).
    required_types = ["kyb", "ubo_declaration", "proof_of_address"]
    labels = {
        "kyb": "Company certificate",
        "ubo_declaration": "UBO declaration",
        "proof_of_address": "Proof of address",
    }

    docs = (
        db.session.query(Document)
        .join(Submission, Submission.id == Document.submission_id)
        .filter(Submission.user_id == current_user.id)
        .order_by(Document.document_type, Document.uploaded_at.desc())
        .all()
    )
    latest_by_type: dict[str, Document] = {}
    for d in docs:
        latest_by_type.setdefault(d.document_type, d)

    status = {}
    now = datetime.utcnow()
    for t in required_types:
        doc = latest_by_type.get(t)
        if not doc:
            status[t] = {"label": labels[t], "state": "Missing"}
        else:
            if t == "proof_of_address" and doc.uploaded_at and (now - doc.uploaded_at) > timedelta(days=90):
                status[t] = {"label": labels[t], "state": "Expired"}
            else:
                status[t] = {"label": labels[t], "state": "Uploaded"}

    completed = sum(1 for v in status.values() if v["state"] == "Uploaded")
    total = len(required_types)
    progress_percent = int(round(100 * completed / total)) if total else 0
    outstanding = sum(1 for v in status.values() if v["state"] != "Uploaded")

    return render_template(
        "dashboard.html",
        status=status,
        progress_percent=progress_percent,
        outstanding=outstanding,
    )
