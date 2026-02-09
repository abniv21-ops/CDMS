from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from wtforms.widgets import ListWidget, CheckboxInput

from app.constants import CLASSIFICATION_CHOICES, DISSEMINATION_CONTROLS


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class DocumentUploadForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    classification_level = SelectField('Classification Level',
                                       choices=CLASSIFICATION_CHOICES,
                                       coerce=int,
                                       validators=[DataRequired()])
    compartments = MultiCheckboxField('Compartments', coerce=int)
    dissemination_controls = MultiCheckboxField('Dissemination Controls',
                                                 choices=DISSEMINATION_CONTROLS)
    file = FileField('Document File', validators=[FileRequired()])
    submit = SubmitField('Upload Document')


class DocumentEditForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    classification_level = SelectField('Classification Level',
                                       choices=CLASSIFICATION_CHOICES,
                                       coerce=int,
                                       validators=[DataRequired()])
    compartments = MultiCheckboxField('Compartments', coerce=int)
    dissemination_controls = MultiCheckboxField('Dissemination Controls',
                                                 choices=DISSEMINATION_CONTROLS)
    file = FileField('Replace File (optional)')
    change_summary = TextAreaField('Change Summary', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Changes')


class DocumentSearchForm(FlaskForm):
    query = StringField('Search', validators=[Optional(), Length(max=255)])
    classification = SelectField('Classification',
                                  choices=[('', 'All Levels')] + CLASSIFICATION_CHOICES,
                                  validators=[Optional()])
    submit = SubmitField('Search')
