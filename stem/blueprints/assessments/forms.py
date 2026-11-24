"""WTForms for assessments and grades, including CSRF via Flask-WTF."""

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    FloatField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange

from stem.services.assessment_service import ASSESSMENT_TYPES


class AssessmentForm(FlaskForm):
    course_id = SelectField(
        "Course",
        coerce=int,
        validators=[DataRequired(message="Please select a course.")],
    )
    title = StringField(
        "Title",
        validators=[
            DataRequired(message="Title is required."),
            Length(max=120),
        ],
    )
    assessment_type = SelectField(
        "Assessment type",
        choices=[(t, t.title()) for t in ASSESSMENT_TYPES],
        validators=[DataRequired(message="Assessment type is required.")],
    )
    assessment_date = DateTimeLocalField(
        "Assessment date & time",
        validators=[DataRequired(message="Assessment date is required.")],
        format="%Y-%m-%dT%H:%M",
    )
    max_marks = FloatField(
        "Maximum marks",
        validators=[
            NumberRange(min=0.01, message="Maximum marks must be greater than zero."),
        ],
    )
    submit = SubmitField("Save assessment")


class GradeForm(FlaskForm):
    marks_obtained = FloatField(
        "Marks obtained",
    )
    submit = SubmitField("Record grade")
