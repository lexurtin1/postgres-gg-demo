"""
Document upload blueprint.

I implement a simple, auditable multi-file upload flow so an applicant can
check in their KYC pack and I can route follow‑up checks:
- I render an upload form that accepts multiple files
- I create a Submission row to group the files and tie it to the user
- I save each file to disk with a safe unique name under UPLOAD_FOLDER
- I infer a coarse document_type from the filename prefix to drive checks
- I create a Document row per file to keep a durable index
- I render a submission detail page that can trigger vendor checks
"""

from __future__ import annotations

import os
from typing import List

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from .models import db, Submission, Document
from .services.vendor_ops import route_submission_for_checks, get_vendor_checks_for_org
from .services.naming import infer_document_type


uploads_bp = Blueprint('uploads', __name__, template_folder='templates')
# I keep uploads on their own blueprint to make wiring and tests cleaner.


# Allowed file extensions for document uploads
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
# I restrict extensions to common document/image types to avoid surprises.


def _ensure_upload_folder_exists() -> str:
    """I ensure the uploads folder exists and return its path to save files."""
    folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    return folder


def _allowed_file(filename: str) -> bool:
    """I check the file extension against the allow‑list for a quick guard."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@uploads_bp.route('/upload', methods=['GET'])
@login_required
def upload_form():
    # I render the upload UI with drag‑and‑drop so the flow feels modern.
    return render_template('upload.html')


@uploads_bp.route('/upload', methods=['POST'])
@login_required
def upload_post():
    # I accept multiple files, validate extensions, and persist them atomically
    # under a Submission so the user has a single reference for the batch.
    files = request.files.getlist('files')
    files = [f for f in files if f and f.filename]
    if not files:
        flash('Please choose at least one file to upload.', 'warning')
        return redirect(url_for('uploads.upload_form'))

    submission = Submission(user_id=current_user.id, org_id=getattr(current_user, "org_id", None))
    db.session.add(submission)
    db.session.commit()

    upload_folder = _ensure_upload_folder_exists()

    for idx, file in enumerate(files, start=1):
        original_name = file.filename

        if not _allowed_file(original_name):
            flash(f"Skipping unsupported file type: {original_name}", 'warning')
            continue

        safe_original = secure_filename(original_name)
        stored_name = f"{submission.id}_{idx}_{safe_original}"
        stored_path = os.path.join(upload_folder, stored_name)
        file.save(stored_path)

        doc_type = infer_document_type(original_name)

        doc = Document(
            submission_id=submission.id,
            filename=original_name,
            stored_path=stored_path,
            document_type=doc_type,
        )
        db.session.add(doc)

    db.session.commit()

    return redirect(url_for('uploads.submission_detail', submission_id=submission.id))


@uploads_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@login_required
def submission_detail(submission_id: int):
    # I show the uploaded files and any vendor checks already associated with
    # the user’s organisation so the applicant can see progress.
    submission = Submission.query.filter_by(id=submission_id, user_id=current_user.id).first()
    if not submission:
        flash('Submission not found.', 'danger')
        return redirect(url_for('uploads.upload_form'))

    checks = []
    if submission.org_id:
        checks = get_vendor_checks_for_org(submission.org_id)
    return render_template('submission_detail.html', submission=submission, vendor_checks=checks)


@uploads_bp.route('/submissions/<int:submission_id>/route', methods=['POST'])
@login_required
def route_submission(submission_id: int):
    # I create vendor checks based on the types present in this submission so
    # the pipeline can move forward without manual back‑office work.
    submission = Submission.query.filter_by(id=submission_id, user_id=current_user.id).first()
    if not submission:
        flash('Submission not found.', 'danger')
        return redirect(url_for('uploads.upload_form'))
    if not (submission.org_id or getattr(current_user, "org_id", None)):
        flash('Organisation not set for this user or submission.', 'warning')
        return redirect(url_for('uploads.submission_detail', submission_id=submission.id))
    if not submission.org_id and getattr(current_user, "org_id", None):
        submission.org_id = current_user.org_id
        db.session.commit()
    created, skipped = route_submission_for_checks(submission)
    flash(f'Requested {created} vendor check(s); {skipped} existing.', 'success')
    return redirect(url_for('uploads.submission_detail', submission_id=submission.id))
