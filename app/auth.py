# app/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash  # I render pages and navigate
from flask_login import login_user, logout_user, login_required                  # I manage sessions
from werkzeug.security import generate_password_hash, check_password_hash        # I hash + verify passwords
from .models import db, User                                                     # I read/write staff records

auth_bp = Blueprint('auth', __name__, template_folder='templates')               # I group auth routes

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # I issue a new staff badge
    if request.method == "POST":
        email = request.form.get("email")                # I read email
        password = request.form.get("password")          # I read password

        if not email or not password:                    # I sanity check inputs
            flash("Please provide both email and password.", "warning")
            return render_template("signup.html")

        if User.query.filter_by(email=email).first():    # I prevent duplicate badges
            flash("Account already exists. Please log in.", "info")
            return redirect(url_for("auth.login"))

        user = User(                                     # I create the staff record
            email=email,
            password_hash=generate_password_hash(password),
            user_type="user"
        )
        db.session.add(user)                             # I stage the insert
        db.session.commit()                              # I write it to the hangar

        login_user(user)                                 # I let them through the gate
        flash("Welcome! Your badge is active.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("signup.html")                # I show the form

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # I scan a staff badge
    if request.method == "POST":
        email = request.form.get("email", "").strip()              # I read email
        password = request.form.get("password", "").strip()          # I read password attempt

        user = User.query.filter_by(email=email).first() # I look up the staff record

        if user and check_password_hash(user.password_hash, password):  # I verify the badge
            login_user(user, remember=True)              # I let them in
            flash("Logged in successfully.", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")   # I block access
            return render_template("login.html")

    return render_template("login.html")                 # I show the form

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()                                        # I revoke the badge for this session
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/dashboard")
@login_required
def dashboard():
    # I show the control room you reach after the gate
    return render_template("dashboard.html")
