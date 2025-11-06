from __future__ import annotations

from flask import Blueprint, request, jsonify, make_response
from flask_login import login_required, current_user
# I use Blueprint to group ops routes, and Flask-Login to protect them so only
# authenticated users can hit these endpoints during the onboarding flow.

from .models import Organisation
from .services.vendor_ops import (
    request_vendor_check,
    complete_vendor_check,
    issue_composite_passport,
    create_verification_request,
)


ops_bp = Blueprint("ops", __name__, url_prefix="/ops")
# I prefix all operational endpoints with /ops to keep the API surface tidy.


@ops_bp.post("/vendor-checks")
@login_required
def api_request_vendor_check():
    # I accept org_id + vendor and create a VendorCheck row so the UI can show
    # progress and the audit log can reflect what happened.
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
    # I mark a vendor check as completed and issue an Attestation that mirrors
    # the outcome so we can model revocation and evidence over time.
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
    # I issue a Composite Passport record for an organisation to simulate the
    # final output of successful onboarding.
    data = request.get_json(silent=True) or {}
    org_id = data.get("org_id") or getattr(current_user, "org_id", None)
    if not org_id:
        return jsonify({"error": "org_id is required"}), 400
    cp = issue_composite_passport(org_id, status=data.get("status", "valid"), chain_anchor=data.get("chain_anchor"))
    return jsonify({"passport_id": cp.id, "org_id": cp.org_id, "status": cp.status}), 201


@ops_bp.post("/verify")
@login_required
def api_create_verification_request():
    # I record that a bank asked to verify a passport; this feeds the audit UI
    # and demonstrates how an external relying party would interact.
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


@ops_bp.get("/passport.pdf")
@login_required
def passport_pdf():
    """Generate a minimal Composite Passport PDF with an embedded QR value.

    This demo uses reportlab to render a single-page PDF containing the
    organisation name, user email, a passport ID placeholder, and a QR code.
    """
    try:
        # Lazy import so reportlab is only required when used
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        from reportlab.graphics.barcode import qr
        from reportlab.graphics.shapes import Drawing
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"PDF generation dependency missing: {exc}"}), 500

    # Demo values – could be replaced by real CompositePassport and Org data
    qr_value = "SBX-QR-VALID-01"
    passport_id = "PASS-00019"
    org_name = getattr(current_user, "org_id", None) or "ACME Manufacturing Ltd"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Header
    c.setFillColorRGB(0.74, 0.07, 0.12)  # brand red
    c.setFont("Helvetica-Bold", 18)
    c.drawString(25 * mm, (height - 25 * mm), "Composite Passport")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 11)
    c.drawString(25 * mm, (height - 35 * mm), f"Organisation: {org_name}")
    c.drawString(25 * mm, (height - 42 * mm), f"Issued to: {current_user.email}")
    c.drawString(25 * mm, (height - 49 * mm), f"Passport ID: {passport_id}")

    # QR code block
    qr_code = qr.QrCodeWidget(qr_value)
    bounds = qr_code.getBounds()
    size = 40 * mm
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(qr_code)
    render_x = width - 25 * mm - size
    render_y = height - 70 * mm - size
    from reportlab.graphics import renderPDF

    renderPDF.draw(d, c, render_x, render_y)
    c.setFont("Helvetica", 10)
    c.drawString(render_x, render_y - 5 * mm, f"QR: {qr_value}")

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(25 * mm, 20 * mm, "This is a demo document – not legally binding.")

    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()

    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = "attachment; filename=Composite_Passport.pdf"
    return resp
