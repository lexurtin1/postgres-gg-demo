from __future__ import annotations

from datetime import datetime
from typing import Optional, Iterable, Tuple, List

# I keep DB‑touching operations in this service module so my route handlers
# stay thin and I can test or reuse these behaviors in isolation.
from ..models import (
    db,
    Organisation,
    VendorCheck,
    Attestation,
    CompositePassport,
    VerificationRequest,
    Submission,
)


def request_vendor_check(org_id: str, vendor: str) -> VendorCheck:
    """I create a pending vendor check for an organisation and persist it."""
    check = VendorCheck(org_id=org_id, vendor=vendor, status="pending")
    db.session.add(check)
    db.session.commit()
    return check


def complete_vendor_check(check_id: int, status: str, *, signature: Optional[str] = None, valid_until: Optional[datetime] = None) -> Attestation:
    """I mark the vendor check complete and create an attestation summarizing it."""
    check = VendorCheck.query.get(check_id)
    if not check:
        raise ValueError("vendor check not found")
    check.status = status
    check.completed_at = datetime.utcnow()

    att = Attestation(
        check_id=check.id,
        issued_at=datetime.utcnow(),
        valid_until=valid_until,
        revocation_status="Active" if status == "pass" else "Revoked",
        signature=signature,
    )
    db.session.add(att)
    db.session.commit()
    return att


def issue_composite_passport(org_id: str, *, status: str = "valid", chain_anchor: Optional[str] = None) -> CompositePassport:
    """I issue a CompositePassport row to represent the applicant's credential."""
    cp = CompositePassport(
        org_id=org_id,
        status=status,
        issued_at=datetime.utcnow(),
        version=1,
        chain_anchor=chain_anchor,
    )
    db.session.add(cp)
    db.session.commit()
    return cp


def create_verification_request(bank_id: int, passport_id: int, *, audited_by: Optional[int] = None, outcome: Optional[str] = None, reason: Optional[str] = None) -> VerificationRequest:
    """I log that a bank asked to verify a passport so we have an audit trail."""
    vr = VerificationRequest(
        bank_id=bank_id,
        passport_id=passport_id,
        requested_at=datetime.utcnow(),
        outcome=outcome,
        reason=reason,
        audited_by=audited_by,
    )
    db.session.add(vr)
    db.session.commit()
    return vr


# --- Submission routing helpers ---------------------------------------------

VENDOR_MAP = {
    "passport": "Refinitiv",
    "proof_of_address": "Refinitiv",
    "kyb": "KYBService",
    "ubo_declaration": "KYBService",
}
"""I map document types to external vendors so I can auto‑route checks
based on which files were uploaded in a submission."""


def get_vendor_checks_for_org(org_id: str) -> list[VendorCheck]:
    """I return recent checks for an organisation to show status to the user."""
    return VendorCheck.query.filter_by(org_id=org_id).order_by(VendorCheck.requested_at.desc()).all()


def route_submission_for_checks(submission: Submission) -> Tuple[int, int]:
    """Create vendor checks for the submission's organisation based on its documents.

    I determine which vendors are required from the submission's document types
    and create checks unless a relevant pending/pass check already exists.
    I return (created_count, skipped_existing_count) for easy UI feedback.
    """
    if not submission.org_id:
        raise ValueError("submission.org_id is required to route vendor checks")

    # Determine required vendors based on present document types
    present_types = {d.document_type for d in submission.documents}
    required_vendors = {VENDOR_MAP[t] for t in present_types if t in VENDOR_MAP}

    created = 0
    skipped = 0
    for vendor in required_vendors:
        existing = VendorCheck.query.filter_by(org_id=submission.org_id, vendor=vendor).order_by(VendorCheck.requested_at.desc()).first()
        if existing and existing.status in {"pending", "pass"}:
            skipped += 1
            continue
        check = VendorCheck(org_id=submission.org_id, vendor=vendor, status="pending")
        db.session.add(check)
        created += 1
    db.session.commit()
    return created, skipped
