from __future__ import annotations

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from .models import Organisation
from .services.vendor_ops import (
    request_vendor_check,
    complete_vendor_check,
    issue_composite_passport,
    create_verification_request,
)


ops_bp = Blueprint("ops", __name__, url_prefix="/ops")


@ops_bp.post("/vendor-checks")
@login_required
def api_request_vendor_check():
    data = request.get_json(silent=True) or {}
    org_id = data.get("org_id") or getattr(current_user, "org_id", None)
    vendor = data.get("vendor")
    if not org_id or not vendor:
        return jsonify({"error": "org_id and vendor are required"}), 400
    check = request_vendor_check(org_id, vendor)
    return jsonify({"id": check.id, "org_id": check.org_id, "vendor": check.vendor, "status": check.status}), 201


@ops_bp.post("/vendor-checks/<int:check_id>/complete")
@login_required
def api_complete_vendor_check(check_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in {"pending", "pass", "fail"}:
        return jsonify({"error": "status must be one of: pending, pass, fail"}), 400
    att = complete_vendor_check(
        check_id,
        status,
        signature=data.get("signature"),
        valid_until=None,
    )
    return jsonify({"attestation_id": att.id, "check_id": att.check_id, "revocation_status": att.revocation_status}), 200


@ops_bp.post("/passports")
@login_required
def api_issue_passport():
    data = request.get_json(silent=True) or {}
    org_id = data.get("org_id") or getattr(current_user, "org_id", None)
    if not org_id:
        return jsonify({"error": "org_id is required"}), 400
    cp = issue_composite_passport(org_id, status=data.get("status", "valid"), chain_anchor=data.get("chain_anchor"))
    return jsonify({"passport_id": cp.id, "org_id": cp.org_id, "status": cp.status}), 201


@ops_bp.post("/verify")
@login_required
def api_create_verification_request():
    data = request.get_json(silent=True) or {}
    bank_id = data.get("bank_id")
    passport_id = data.get("passport_id")
    if not bank_id or not passport_id:
        return jsonify({"error": "bank_id and passport_id are required"}), 400
    vr = create_verification_request(
        bank_id=int(bank_id),
        passport_id=int(passport_id),
        audited_by=getattr(current_user, "id", None),
        outcome=data.get("outcome"),
        reason=data.get("reason"),
    )
    return jsonify({"request_id": vr.id, "bank_id": vr.bank_id, "passport_id": vr.passport_id}), 201

