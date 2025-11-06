from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from .models import db, Submission, Document, VendorCheck, Attestation, VerificationRequest


pages_bp = Blueprint("pages", __name__, template_folder="templates")
# I keep simple, user‑facing pages (audit/attestations/settings) in this blueprint
# so my core auth/upload code stays focused.


def _settings_path(user_id: int) -> str:
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, f"user_settings_{user_id}.json")


def _load_settings(user_id: int) -> dict[str, Any]:
    """I load per‑user settings from a JSON file so I can avoid a migration."""
    path = _settings_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_settings(user_id: int, data: dict[str, Any]) -> None:
    """I persist per‑user settings back to disk with a simple JSON file."""
    path = _settings_path(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@pages_bp.route("/attestations", methods=["GET"])
@login_required
def attestations():
    # I stub the attestations page with a clear "coming soon" message.
    return render_template("attestations.html")


@pages_bp.route("/audit", methods=["GET"])
@login_required
def audit():
    # I build a simple activity feed from recent actions so an auditor can see
    # who uploaded what and when, alongside check status.
    events: list[dict[str, Any]] = []

    def add(kind: str, when: datetime, summary: str):
        events.append({"kind": kind, "when": when, "summary": summary})

    # I list submissions by the user
    for s in (
        Submission.query.filter_by(user_id=current_user.id)
        .order_by(Submission.created_at.desc())
        .limit(25)
        .all()
    ):
        add("Submission", s.created_at, f"Created submission #{s.id}")

    # I include documents tied to the user's submissions
    doc_rows = (
        db.session.query(Document, Submission)
        .join(Submission, Submission.id == Document.submission_id)
        .filter(Submission.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .limit(50)
        .all()
    )
    for d, s in doc_rows:
        add("Document", d.uploaded_at, f"Uploaded {d.document_type} as '{d.filename}' in submission #{s.id}")

    # I include vendor checks/attestations for the user's organisation when set
    if getattr(current_user, "org_id", None):
        org = current_user.org_id
        for vc in (
            VendorCheck.query.filter_by(org_id=org)
            .order_by(VendorCheck.requested_at.desc())
            .limit(50)
            .all()
        ):
            add("VendorCheck", vc.requested_at, f"Vendor '{vc.vendor}' check {vc.status}")

        for at in (
            Attestation.query.join(VendorCheck, VendorCheck.id == Attestation.check_id)
            .filter(VendorCheck.org_id == org)
            .order_by(Attestation.issued_at.desc())
            .limit(50)
            .all()
        ):
            add("Attestation", at.issued_at, f"Attestation #{at.id} status {at.revocation_status}")

        for vr in (
            VerificationRequest.query
            .order_by(VerificationRequest.requested_at.desc())
            .limit(50)
            .all()
        ):
            add("Verification", vr.requested_at, f"Verification request #{vr.id} outcome: {vr.outcome or 'n/a'}")

    # I sort newest first to match typical audit expectations
    events.sort(key=lambda e: e["when"], reverse=True)
    return render_template("audit.html", events=events)


@pages_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    # I persist a couple of user preferences without a schema change so I can
    # demo working settings in the prototype.
    if request.method == "POST":
        data = _load_settings(current_user.id)
        data["display_name"] = request.form.get("display_name", "").strip()
        data["email_notifications"] = True if request.form.get("email_notifications") == "on" else False
        data["dark_mode"] = True if request.form.get("dark_mode") == "on" else False
        _save_settings(current_user.id, data)
        flash("Settings saved.", "success")
        return redirect(url_for("pages.settings"))

    data = _load_settings(current_user.id)
    return render_template("settings.html", settings=data)
