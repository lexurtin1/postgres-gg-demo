"""
I implement the 'Check-in & Baggage Sorting' feature using a small blueprint.

I keep the logic straightforward and heavily commented so it's easy to follow:
- I show an upload form (the check-in desk) where the user can select many files.
- I create a Submission row (the flight record) when the form is posted.
- I save each file (each bag) to an uploads/ folder with a safe unique name.
- I infer a simple document type from the filename (the routing sticker).
- I create a Document row for each file so the DB mirrors what is on disk.
- I show a simple summary page per submission so I can verify everything worked.
"""

from __future__ import annotations  # I allow future annotations for type hints

import os  # I use this to build paths and create the uploads folder
from typing import List  # I document a few types for readability

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash  # I use Flask helpers
from flask_login import login_required, current_user  # I protect routes so only logged-in users can upload
from werkzeug.utils import secure_filename  # I sanitize file names so they are safe for the filesystem

from .models import db, Submission, Document  # I create DB rows that reflect the upload
from .services.naming import infer_document_type  # I tag files based on their names


# I create a blueprint dedicated to uploads so routes are neatly grouped.
uploads_bp = Blueprint('uploads', __name__, template_folder='templates')


# I define which extensions I will accept; I keep this small and explicit.
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}  # I accept common KYC file types


def _ensure_upload_folder_exists() -> str:
    """I make sure the uploads folder exists and return its absolute path.

    I use the configured UPLOAD_FOLDER, and if it's missing I create it so the
    first upload doesn't fail. This is idempotent and safe to call on every POST.
    """
    # I read the target folder from app config so tests and dev can override it.
    folder = current_app.config['UPLOAD_FOLDER']  # I rely on __init__.py to set this
    # I create the folder if it doesn't exist so save() has a destination.
    os.makedirs(folder, exist_ok=True)  # I avoid errors by ensuring the directory exists
    return folder  # I return the absolute path so callers can join filenames


def _allowed_file(filename: str) -> bool:
    """I check the file extension against the allow-list.

    I use os.path.splitext to read the extension and compare lower-cased values
    so 'IMAGE.JPG' is fine.
    """
    # I split the extension so I can compare it to the allow-list.
    ext = os.path.splitext(filename)[1].lower()  # I normalize to lower case
    return ext in ALLOWED_EXTENSIONS  # I return True only for allowed types


@uploads_bp.route('/upload', methods=['GET'])
@login_required  # I require the user to be logged in to see the form
def upload_form():
    # I simply render the form template; the heavy lifting happens on POST.
    return render_template('upload.html')  # I keep the template minimal and readable


@uploads_bp.route('/upload', methods=['POST'])
@login_required  # I protect the endpoint so uploads are linked to an authenticated user
def upload_post():
    # I make sure there's at least one file in the request; otherwise I guide the user.
    files = request.files.getlist('files')  # I read a list of files under the 'files' field name
    files = [f for f in files if f and f.filename]  # I filter out empty items browsers sometimes include
    if not files:  # I handle the edge case where nothing was selected
        flash('Please choose at least one file to upload.', 'warning')  # I help the user understand the issue
        return redirect(url_for('uploads.upload_form'))  # I send them back to try again

    # I create the flight record (submission) tied to the current user.
    submission = Submission(user_id=current_user.id)  # I record who owns this batch
    db.session.add(submission)  # I stage the insert so I can get an ID after commit
    db.session.commit()  # I commit so submission.id is populated for filenames and FK rows

    # I make sure the uploads folder exists so saving files does not fail.
    upload_folder = _ensure_upload_folder_exists()  # I get the path where I will save files

    # I iterate over every selected file and save it to disk + database.
    for idx, file in enumerate(files, start=1):  # I number files so stored names are unique and ordered
        original_name = file.filename  # I keep the original name for display later

        # I enforce a simple, clear allow-list on file types.
        if not _allowed_file(original_name):  # I guard against unsupported file types early
            flash(f"Skipping unsupported file type: {original_name}", 'warning')  # I notify but continue with others
            continue  # I process the remaining files rather than failing the whole batch

        # I sanitize the original name to remove risky characters.
        safe_original = secure_filename(original_name)  # I ensure the name is safe for the filesystem

        # I build a unique stored filename using the submission id and a counter.
        stored_name = f"{submission.id}_{idx}_{safe_original}"  # I prefix so files don't collide across submissions
        stored_path = os.path.join(upload_folder, stored_name)  # I compute where on disk I will save the file

        # I save the file contents to disk now that I have a safe destination.
        file.save(stored_path)  # I write the uploaded bytes to the uploads folder

        # I infer a simple document type based on the original filename.
        doc_type = infer_document_type(original_name)  # I tag this bag for later routing to vendors

        # I create a Document row so the DB mirrors the file I just saved.
        doc = Document(
            submission_id=submission.id,  # I link to the flight record
            filename=original_name,        # I store the original name for display
            stored_path=stored_path,       # I store the absolute path where I saved it
            document_type=doc_type,        # I store the inferred document type
        )
        db.session.add(doc)  # I stage the insert so I can commit once per request

    # I write all Document rows to the database in one commit for simplicity.
    db.session.commit()  # I persist the documents so the detail page can load them

    # I send the user to a detail page where they can see what I processed.
    return redirect(url_for('uploads.submission_detail', submission_id=submission.id))  # I navigate to the summary


@uploads_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@login_required  # I ensure only the logged-in owner can view the submission
def submission_detail(submission_id: int):
    # I fetch the submission that belongs to the current user or return 404 if missing.
    submission = Submission.query.filter_by(id=submission_id, user_id=current_user.id).first()  # I scope by owner
    if not submission:  # I handle cases where the id is invalid or not owned by this user
        flash('Submission not found.', 'danger')  # I inform the user without leaking existence
        return redirect(url_for('uploads.upload_form'))  # I send them back to the upload page

    # I render a simple table of documents so I can verify what was saved.
    return render_template('submission_detail.html', submission=submission)  # I pass the submission with its documents

