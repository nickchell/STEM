"""WTForms for adding a course, including CSRF via Flask-WTF."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

from stem.services.course_service import MAX_CODE_LENGTH, MAX_NAME_LENGTH


class CourseForm(FlaskForm):
    course_code = StringField(
        "Course code",
        validators=[
            DataRequired(message="Course code is required."),
            Length(max=MAX_CODE_LENGTH),
        ],
    )
    course_name = StringField(
        "Course name",
        validators=[
            DataRequired(message="Course name is required."),
            Length(max=MAX_NAME_LENGTH),
        ],
    )
    submit = SubmitField("Add course")
