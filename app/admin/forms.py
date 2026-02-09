from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

from app.constants import UserRole, CLASSIFICATION_CHOICES


class UserEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=UserRole.CHOICES, validators=[DataRequired()])
    clearance_level = SelectField('Clearance Level',
                                   choices=CLASSIFICATION_CHOICES,
                                   coerce=int,
                                   validators=[DataRequired()])
    new_password = PasswordField('New Password (leave blank to keep current)',
                                  validators=[Optional(), Length(min=8)])
    submit = SubmitField('Save Changes')
