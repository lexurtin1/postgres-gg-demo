from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from .models import db, Submission, Document, VendorCheck, Attestation, VerificationRequest, Case, CaseDecision, Request, ApiKey, WebhookEndpoint, AuditEvent, Organisation


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


# --- Cases (Analyst demo) ---------------------------------------------------

@pages_bp.route('/cases', methods=['GET'])
@login_required
def cases_index():
    if getattr(current_user, 'user_type', None) != 'vendor':
        flash('Access restricted to vendor users.', 'warning')
        return redirect(url_for('auth.dashboard'))
    # Determine which external vendor this user represents (simple demo map).
    VENDOR_USER_MAP = {
        'vendor@example.com': 'Refinitiv',
        'vendor2@example.com': 'KYBService',
    }
    vendor_name = VENDOR_USER_MAP.get((current_user.email or '').lower())

    # List cases relevant to this vendor; if none in DB, seed a demo case.
    q = Case.query.order_by(Case.created_at.desc())
    cases = q.limit(200).all()
    if not cases:
        c = Case(org_id=getattr(current_user, 'org_id', None), status='running')
        db.session.add(c)
        db.session.commit()
        cases = [c]
    # Filter to only cases where a VendorCheck exists for this vendor (if mapped)
    if vendor_name:
        org_ids_with_checks = {
            vc.org_id for vc in VendorCheck.query.filter_by(vendor=vendor_name).all()
        }
        if org_ids_with_checks:
            cases = [c for c in cases if c.org_id in org_ids_with_checks]
    orgs = {o.id: o for o in Organisation.query.filter(Organisation.id.in_([c.org_id for c in cases if c.org_id])).all()}
    # Compute simple doc counts per case org for context
    doc_counts = {}
    if orgs:
        rows = (
            db.session.query(Submission.org_id, db.func.count(Document.id))
            .join(Document, Document.submission_id == Submission.id)
            .filter(Submission.org_id.in_(list(orgs.keys())))
            .group_by(Submission.org_id)
            .all()
        )
        doc_counts = {org_id: count for org_id, count in rows}
    return render_template('cases.html', cases=cases, orgs=orgs, doc_counts=doc_counts)


@pages_bp.route('/vendor/dashboard', methods=['GET'])
@login_required
def vendor_dashboard():
    if getattr(current_user, 'user_type', None) != 'vendor':
        return redirect(url_for('auth.dashboard'))
    # Reuse the same vendor mapping to pick a relevant case, then deep-link to detail.
    VENDOR_USER_MAP = {
        'vendor@example.com': 'Refinitiv',
        'vendor2@example.com': 'KYBService',
    }
    vendor_name = VENDOR_USER_MAP.get((current_user.email or '').lower())
    q = Case.query.order_by(Case.created_at.desc())
    cases = q.limit(200).all()
    if vendor_name:
        org_ids_with_checks = {vc.org_id for vc in VendorCheck.query.filter_by(vendor=vendor_name).all()}
        cases = [c for c in cases if c.org_id in org_ids_with_checks] or cases
    if cases:
        return redirect(url_for('pages.case_detail', case_id=cases[0].id))
    return redirect(url_for('pages.cases_index'))


@pages_bp.route('/cases/<int:case_id>', methods=['GET'])
@login_required
def case_detail(case_id: int):
    if getattr(current_user, 'user_type', None) != 'vendor':
        flash('Access restricted to vendor users.', 'warning')
        return redirect(url_for('auth.dashboard'))
    c = Case.query.get_or_404(case_id)
    org = Organisation.query.filter_by(id=c.org_id).first()
    # Pull recent attestations and requests
    reqs = Request.query.filter_by(case_id=case_id).order_by(Request.created_at.desc()).all()
    atts = Attestation.query.order_by(Attestation.issued_at.desc()).limit(10).all()
    events = AuditEvent.query.filter_by(case_id=case_id).order_by(AuditEvent.created_at.desc()).limit(20).all()
    # Documents for the applicant org
    from .models import Submission
    docs = (
        db.session.query(Document)
        .join(Submission, Submission.id == Document.submission_id)
        .filter(Submission.org_id == c.org_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return render_template('case.html', case=c, org=org, requests=reqs, attestations=atts, events=events, documents=docs)


@pages_bp.route('/cases/<int:case_id>/decision', methods=['POST'])
@login_required
def case_decide(case_id: int):
    if getattr(current_user, 'user_type', None) != 'vendor':
        flash('Access restricted to vendor users.', 'warning')
        return redirect(url_for('auth.dashboard'))
    decision = (request.form.get('decision') or '').lower()
    reason = request.form.get('reason')
    if decision not in {'pass', 'review', 'fail'}:
        flash('Invalid decision.', 'danger')
        return redirect(url_for('pages.case_detail', case_id=case_id))
    c = Case.query.get_or_404(case_id)
    c.status = decision
    d = CaseDecision(case_id=case_id, actor_user_id=current_user.id, decision=decision, reason=reason)
    db.session.add(d)
    ae = AuditEvent(case_id=case_id, actor_user_id=current_user.id, event_type='case_decision', data_json=decision)
    db.session.add(ae)
    # If PASS and applicant org set, mint a Composite Passport (demo flow)
    if decision == 'pass' and c.org_id:
        try:
            from .services.vendor_ops import issue_composite_passport
            from .models import CompositePassport
            existing = CompositePassport.query.filter_by(org_id=c.org_id, status='valid').first()
            if not existing:
                issue_composite_passport(c.org_id, status='valid')
                db.session.add(AuditEvent(case_id=case_id, actor_user_id=current_user.id, event_type='passport_issued'))
        except Exception:
            pass
    db.session.commit()
    flash('Decision recorded.', 'success')
    return redirect(url_for('pages.case_detail', case_id=case_id))


@pages_bp.route('/requests', methods=['POST'])
@login_required
def create_request():
    if getattr(current_user, 'user_type', None) != 'vendor':
        flash('Access restricted to vendor users.', 'warning')
        return redirect(url_for('auth.dashboard'))
    case_id = request.form.get('case_id', type=int)
    reason_code = request.form.get('reason_code') or 'INFO'
    message = request.form.get('message') or 'Please provide more information.'
    r = Request(case_id=case_id, org_id=getattr(current_user, 'org_id', None), type='document', reason_code=reason_code, message=message)
    db.session.add(r)
    db.session.add(AuditEvent(case_id=case_id, actor_user_id=current_user.id, event_type='request_created', data_json=reason_code))
    db.session.commit()
    flash('Request sent to applicant (demo).', 'success')
    return redirect(url_for('pages.case_detail', case_id=case_id))


@pages_bp.post('/cases/<int:case_id>/documents/<int:doc_id>/decision')
@login_required
def case_doc_decision(case_id: int, doc_id: int):
    """Vendor marks an individual document as approved/rejected, creating an attestation."""
    if getattr(current_user, 'user_type', None) != 'vendor':
        flash('Access restricted to vendor users.', 'warning')
        return redirect(url_for('auth.dashboard'))
    action = (request.form.get('action') or '').lower()
    if action not in {'approve', 'reject'}:
        flash('Invalid action.', 'danger')
        return redirect(url_for('pages.case_detail', case_id=case_id))
    # Lookup document and its org via submission
    doc = Document.query.get_or_404(doc_id)
    sub = Submission.query.filter_by(id=doc.submission_id).first()
    org_id = getattr(sub, 'org_id', None)
    if not org_id:
        flash('Document has no organisation link.', 'warning')
        return redirect(url_for('pages.case_detail', case_id=case_id))
    # Create/complete vendor check + attestation for this document type
    vendor = {
        'passport': 'Refinitiv',
        'proof_of_address': 'Refinitiv',
        'kyb': 'KYBService',
        'ubo_declaration': 'KYBService',
    }.get(doc.document_type, 'Refinitiv')
    # Reuse latest existing check or create a new one
    vc = VendorCheck.query.filter_by(org_id=org_id, vendor=vendor).order_by(VendorCheck.requested_at.desc()).first()
    if not vc or vc.status == 'fail':
        vc = VendorCheck(org_id=org_id, vendor=vendor, status='pending')
        db.session.add(vc)
        db.session.flush()
    # Complete
    from .services.vendor_ops import complete_vendor_check
    att = complete_vendor_check(vc.id, 'pass' if action == 'approve' else 'fail', signature=None, valid_until=None)
    db.session.add(AuditEvent(case_id=case_id, actor_user_id=current_user.id, event_type='doc_decision', data_json=f"{doc.document_type}:{action}"))
    db.session.commit()
    flash(f"Document {doc.document_type} marked {action}.", 'success')
    return redirect(url_for('pages.case_detail', case_id=case_id))


# --- Developer Sandbox ------------------------------------------------------

@pages_bp.route('/developer', methods=['GET', 'POST'])
@login_required
def developer():
    if getattr(current_user, 'user_type', None) != 'vendor':
        flash('Access restricted to vendor users.', 'warning')
        return redirect(url_for('auth.dashboard'))
    # Manage webhook endpoint
    wh = WebhookEndpoint.query.order_by(WebhookEndpoint.created_at.desc()).first()
    if request.method == 'POST':
        url = request.form.get('callback_url')
        secret = request.form.get('signing_secret')
        status = 'enabled'
        if wh:
            wh.url = url
            wh.signing_secret = secret
            wh.status = status
        else:
            wh = WebhookEndpoint(url=url, signing_secret=secret, status=status)
            db.session.add(wh)
        db.session.commit()
        flash('Webhook settings saved.', 'success')
        return redirect(url_for('pages.developer'))

    recent = AuditEvent.query.filter(AuditEvent.event_type.in_(['sandbox_verify'])).order_by(AuditEvent.created_at.desc()).limit(10).all()
    return render_template('developer.html', webhook=wh, events=recent)


@pages_bp.route('/sandbox/verify', methods=['POST'])
def sandbox_verify():
    import json as _json
    from datetime import timedelta
    data = request.get_json(silent=True) or {}
    qr = (data.get('passport_qr') or '').upper()
    corr = f"CORR-{_json.__name__[:3]}"  # cheap deterministic token just for demo
    if 'VALID' in qr:
        decision = 'pass'
        status = 'verified'
    elif 'REVIEW' in qr:
        decision = 'review'
        status = 'needs_more_info'
    else:
        decision = 'fail'
        status = 'failed'
    # Log audit
    ae = AuditEvent(event_type='sandbox_verify', data_json=_json.dumps(data), correlation_id=corr)
    db.session.add(ae)
    db.session.commit()
    resp = {
        'verification_id': f'ver_{ae.id:06d}',
        'decision': decision,
        'status': status,
        'expires_at': (datetime.utcnow().replace(microsecond=0) + timedelta(days=365)).isoformat()+"Z",
        'correlation_id': corr,
    }
    return resp, 200
