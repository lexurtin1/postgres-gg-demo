# app/models.py

from flask_sqlalchemy import SQLAlchemy          # table definitions and session
from flask_login import UserMixin                # login helpers for the User model
from datetime import datetime                    # creation timestamp

"""I define my database schema here using SQLAlchemy models so I can keep
application logic clean and let the ORM handle persistence concerns."""

db = SQLAlchemy()                                # shared DB handle

class User(UserMixin, db.Model):
    __tablename__ = 'users'                      # users table

    id = db.Column(db.Integer, primary_key=True)       # integer primary key
    # I add username to match the existing DB schema created by early migrations.
    # In the DB it's unique and non-null; I mirror that here so inserts succeed.
    username = db.Column(db.String(50), unique=True, nullable=False)  # login handle (we derive from email on signup)
    email = db.Column(db.String(255), unique=True)     # user email
    password_hash = db.Column(db.String(255))          # hashed password
    user_type = db.Column(db.String(50))               # existing role
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # account creation time
    # New: link user to an organisation and active flag per ERD
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        # helpful label when logging a user instance
        return f"<User id={self.id} email={self.email}>"


# Submission model to represent a multi-file upload transaction.
# Columns are minimal to keep it easy to reason about and migrate.
class Submission(db.Model):
    __tablename__ = 'submissions'                                     # I map to the submissions table

    id = db.Column(db.Integer, primary_key=True)                      # I use an integer ID so URLs are simple
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # I tie the submission to its owner
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # I timestamp when I was created
    # New: organisation linkage and status string per ERD
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'))
    status = db.Column(db.String(32), default='pending', nullable=False)

    # I expose a relationship back to the User so I can say submission.user
    user = db.relationship('User', backref=db.backref('submissions', lazy=True))

    def __repr__(self):
        # I print a friendly label that helps me debug in the shell or logs
        return f"<Submission id={self.id} user_id={self.user_id}>"


# Document model for each uploaded file.
# Stores original name, storage path, inferred type, and timestamps.
class Document(db.Model):
    __tablename__ = 'documents'                                       # I map to the documents table

    id = db.Column(db.Integer, primary_key=True)                      # I use an integer ID for simplicity
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)  # I reference my submission
    filename = db.Column(db.String(512), nullable=False)              # I keep the original filename the user picked
    stored_path = db.Column(db.String(1024), nullable=False)          # I record the path I saved to on disk
    document_type = db.Column(db.String(64), nullable=False)          # I record my inferred type (passport, etc.)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # I timestamp when I was saved
    # New: ERD fields
    hash = db.Column(db.String(128))
    storage_ref = db.Column(db.String(1024))

    # I expose a relationship to the parent submission so I can say doc.submission
    submission = db.relationship('Submission', backref=db.backref('documents', lazy=True))

    def __repr__(self):
        # I print a friendly label that helps me debug in the shell or logs
        return f"<Document id={self.id} sub_id={self.submission_id} type={self.document_type}>"


# --- New models from ERD -----------------------------------------------------

class Organisation(db.Model):
    __tablename__ = 'organisations'

    id = db.Column(db.String(36), primary_key=True)  # UUID as string
    legal_name = db.Column(db.String(255), nullable=False)
    reg_number = db.Column(db.String(100))
    status = db.Column(db.String(16), default='active', nullable=False)  # active/inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Organisation id={self.id} legal_name={self.legal_name}>"


class VendorCheck(db.Model):
    __tablename__ = 'vendor_checks'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    vendor = db.Column(db.String(100), nullable=False)  # e.g., Refinitiv
    status = db.Column(db.String(16), default='pending', nullable=False)  # pending/pass/fail
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)

    organisation = db.relationship('Organisation', backref=db.backref('vendor_checks', lazy=True))


class Attestation(db.Model):
    __tablename__ = 'attestations'

    id = db.Column(db.Integer, primary_key=True)
    check_id = db.Column(db.Integer, db.ForeignKey('vendor_checks.id'), nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    valid_until = db.Column(db.DateTime)
    revocation_status = db.Column(db.String(16), default='Active', nullable=False)  # Active/Revoked
    signature = db.Column(db.String(512))

    vendor_check = db.relationship('VendorCheck', backref=db.backref('attestations', lazy=True))


class CompositePassport(db.Model):
    __tablename__ = 'composite_passports'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'), nullable=False)
    status = db.Column(db.String(16), default='draft', nullable=False)  # draft/valid/revoked
    issued_at = db.Column(db.DateTime)
    version = db.Column(db.Integer, default=1, nullable=False)
    chain_anchor = db.Column(db.String(255))

    organisation = db.relationship('Organisation', backref=db.backref('passports', lazy=True))


class Bank(db.Model):
    __tablename__ = 'banks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    bic = db.Column(db.String(20))
    country = db.Column(db.String(2))  # ISO 3166-1 alpha-2


class VerificationRequest(db.Model):
    __tablename__ = 'verification_requests'

    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey('banks.id'), nullable=False)
    passport_id = db.Column(db.Integer, db.ForeignKey('composite_passports.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    outcome = db.Column(db.String(16))  # valid/invalid
    reason = db.Column(db.String(255))
    audited_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    bank = db.relationship('Bank', backref=db.backref('verification_requests', lazy=True))
    passport = db.relationship('CompositePassport', backref=db.backref('verification_requests', lazy=True))


# --- Minimal additional models for cases/sandbox/audit ----------------------

class Case(db.Model):
    __tablename__ = 'cases'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'))
    status = db.Column(db.String(24), default='running', nullable=False)  # running/needs_info/pass/review/fail
    sla_due_at = db.Column(db.DateTime)
    risk_flags = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    organisation = db.relationship('Organisation', backref=db.backref('cases', lazy=True))


class CaseDecision(db.Model):
    __tablename__ = 'case_decisions'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    decision = db.Column(db.String(16), nullable=False)  # pass/review/fail
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    case = db.relationship('Case', backref=db.backref('decisions', lazy=True))
    actor = db.relationship('User')


class Request(db.Model):
    __tablename__ = 'requests'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'))
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'))
    type = db.Column(db.String(50))  # document/info
    reason_code = db.Column(db.String(50))
    message = db.Column(db.String(512))
    status = db.Column(db.String(24), default='open', nullable=False)  # open/closed
    due_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    case = db.relationship('Case', backref=db.backref('requests', lazy=True))


class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'))
    prefix = db.Column(db.String(16), unique=True, nullable=False)
    secret = db.Column(db.String(64), nullable=False)  # demo only; store plaintext for sandbox
    status = db.Column(db.String(16), default='active', nullable=False)  # active/revoked
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class WebhookEndpoint(db.Model):
    __tablename__ = 'webhook_endpoints'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.String(36), db.ForeignKey('organisations.id'))
    url = db.Column(db.String(512))
    signing_secret = db.Column(db.String(64))  # demo only
    status = db.Column(db.String(16), default='enabled', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AuditEvent(db.Model):
    __tablename__ = 'audit_events'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'))
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_type = db.Column(db.String(50), nullable=False)
    data_json = db.Column(db.Text)
    correlation_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    case = db.relationship('Case', backref=db.backref('audit_events', lazy=True))
