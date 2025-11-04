"""
Document upload blueprint.

This module provides a simple multi-file upload flow:
- Display an upload form where a user can select multiple files
- Create a Submission row when the form is posted
- Save each file to the configured uploads folder with a safe unique name
- Infer a basic document type from the filename
- Create a Document row for each saved file
- Show a summary page per submission
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


# Allowed file extensions for document uploads
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}


def _ensure_upload_folder_exists() -> str:
    """Ensure the uploads folder exists and return its path."""
    folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    return folder


def _allowed_file(filename: str) -> bool:
    """Check the file extension against the allow-list."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@uploads_bp.route('/upload', methods=['GET'])
@login_required
def upload_form():
    return render_template('upload.html')


@uploads_bp.route('/upload', methods=['POST'])
@login_required
def upload_post():
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
