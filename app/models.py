# app/models.py

from flask_sqlalchemy import SQLAlchemy          # I use this to define tables
from flask_login import UserMixin                # I mix this into User for login helpers
from datetime import datetime                    # I time-stamp user creation

db = SQLAlchemy()                                # I create one shared DB handle

class User(UserMixin, db.Model):
    __tablename__ = 'users'                      # I map this class to the existing users table

    id = db.Column(db.Integer, primary_key=True) # I use an integer ID as the badge number
    email = db.Column(db.String(255), unique=True)     # I identify user by email
    password_hash = db.Column(db.String(255))          # I store the scrambled (hashed) password
    user_type = db.Column(db.String(50))               # I keep the existing role
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # I record when the badge was issued

    def __repr__(self):
        # I print a friendly label when I log a user
        return f"<User id={self.id} email={self.email}>"
