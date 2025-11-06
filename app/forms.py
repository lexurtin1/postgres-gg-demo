from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, MultipleFileField
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Sign in")


class SignupForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Create account")


class UploadForm(FlaskForm):
    files = MultipleFileField("Files")
    submit = SubmitField("Upload")

