# app/models.py

from flask_sqlalchemy import SQLAlchemy          # table definitions and session
from flask_login import UserMixin                # login helpers for the User model
from datetime import datetime                    # creation timestamp

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

    def __repr__(self):
        # helpful label when logging a user instance
        return f"<User id={self.id} email={self.email}>"


# I define a simple Submission model to represent one upload 'flight record'.
# I keep columns minimal so it's easy to reason about and migrate.
class Submission(db.Model):
    __tablename__ = 'submissions'                                     # I map to the submissions table

    id = db.Column(db.Integer, primary_key=True)                      # I use an integer ID so URLs are simple
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # I tie the submission to its owner
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # I timestamp when I was created

    # I expose a relationship back to the User so I can say submission.user
    user = db.relationship('User', backref=db.backref('submissions', lazy=True))

    def __repr__(self):
        # I print a friendly label that helps me debug in the shell or logs
        return f"<Submission id={self.id} user_id={self.user_id}>"


# I define a Document model to represent each uploaded file (each 'bag').
# I store original name, where I saved it, what type I inferred, and when it arrived.
class Document(db.Model):
    __tablename__ = 'documents'                                       # I map to the documents table

    id = db.Column(db.Integer, primary_key=True)                      # I use an integer ID for simplicity
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)  # I reference my submission
    filename = db.Column(db.String(512), nullable=False)              # I keep the original filename the user picked
    stored_path = db.Column(db.String(1024), nullable=False)          # I record the path I saved to on disk
    document_type = db.Column(db.String(64), nullable=False)          # I record my inferred type (passport, etc.)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # I timestamp when I was saved

    # I expose a relationship to the parent submission so I can say doc.submission
    submission = db.relationship('Submission', backref=db.backref('documents', lazy=True))

    def __repr__(self):
        # I print a friendly label that helps me debug in the shell or logs
        return f"<Document id={self.id} sub_id={self.submission_id} type={self.document_type}>"
