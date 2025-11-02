# app/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash  # render pages and navigate
from flask_login import login_user, logout_user, login_required                  # manage sessions
from werkzeug.security import generate_password_hash, check_password_hash        # hash + verify passwords
from .models import db, User                                                     # read/write user records

auth_bp = Blueprint('auth', __name__, template_folder='templates')               # group auth routes

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # Create a new user account
    if request.method == "POST":
        email = request.form.get("email")                # I read email
        password = request.form.get("password")          # I read password

        if not email or not password:                    # basic input validation
            flash("Please provide both email and password.", "warning")
            return render_template("signup.html")

        if User.query.filter_by(email=email).first():    # prevent duplicate accounts
            flash("Account already exists. Please log in.", "info")
            return redirect(url_for("auth.login"))

        # I derive a simple username from the part before '@'.
        # This satisfies the existing NOT NULL + UNIQUE constraint on users.username.
        base_username = (email.split("@", 1)[0] or "user").lower()  # I pick something stable and readable
        candidate = base_username                                   # I start with the base
        # I ensure the username is unique by appending a number if needed.
        suffix = 1
        while User.query.filter_by(username=candidate).first() is not None:  # I check for collisions
            suffix += 1                                                      # I increment until it's unique
            candidate = f"{base_username}{suffix}"                           # I try the next candidate

        user = User(                                     # create the user record
            username=candidate,                           # I set a unique username
            email=email,                                  # I store the email used for login
            password_hash=generate_password_hash(password),  # I hash the password for safety
            user_type="user"                              # I keep a simple default role
        )
        db.session.add(user)                             # stage the insert
        db.session.commit()                              # commit to the database

        login_user(user)                                 # log in the new user
        flash("Welcome! Your account is active.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("signup.html")                # show the form

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Handle user login
    if request.method == "POST":
        email = request.form.get("email", "").strip()              # read email
        password = request.form.get("password", "").strip()          # read password attempt

        user = User.query.filter_by(email=email).first() # look up the user

        if user and user.password_hash and check_password_hash(user.password_hash, password):  # verify password if hash exists
            login_user(user, remember=True)              # log them in
            flash("Logged in successfully.", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")   # block access
            return render_template("login.html")

    return render_template("login.html")                 # show the form

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()                                        # end the session
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/dashboard")
@login_required
def dashboard():
    # Show the user dashboard
    return render_template("dashboard.html")
