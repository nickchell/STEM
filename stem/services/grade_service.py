"""Grade management rules, independent of HTTP.

Blueprints collect form data and call these functions. Validation lives here
so Pytest can exercise it without going through templates. Ownership is
enforced through the assessment's parent course.
"""

from stem.extensions import db
from stem.models.assessment import Assessment
from stem.models.course import Course
from stem.models.grade import Grade


class GradeError(Exception):
    """Raised when grade input cannot be accepted."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def normalize_marks(marks, max_marks):
    """Validate marks obtained: not negative and not greater than max marks."""
    if marks is None or str(marks).strip() == "":
        raise GradeError("Marks obtained is required.", field="marks_obtained")
    try:
        marks = float(marks)
    except (TypeError, ValueError) as exc:
        raise GradeError("Marks obtained must be a number.", field="marks_obtained") from exc
    if marks < 0:
        raise GradeError("Marks obtained cannot be negative.", field="marks_obtained")
    if marks > max_marks:
        raise GradeError(
            f"Marks obtained cannot be greater than maximum marks ({max_marks}).",
            field="marks_obtained",
        )
    return marks


def _get_owned_assessment(assessment_id, user_id):
    """Return the assessment if it belongs to the given user, else None."""
    return (
        Assessment.query.join(Course, Assessment.course_id == Course.id)
        .filter(Assessment.id == assessment_id, Course.user_id == user_id)
        .first()
    )


def record_grade(user_id, assessment_id, marks_obtained):
    """Record or update a grade for an owned assessment and return it.

    Percentage is calculated automatically: marks / max_marks * 100.
    Raises GradeError for validation errors or when the assessment is not owned.
    """
    assessment = _get_owned_assessment(assessment_id, user_id)
    if assessment is None:
        raise GradeError("Assessment not found or you do not own it.")

    marks = normalize_marks(marks_obtained, assessment.max_marks)
    percentage = round((marks / assessment.max_marks) * 100, 2)

    grade = Grade.query.filter_by(assessment_id=assessment.id).first()
    if grade is None:
        grade = Grade(
            assessment_id=assessment.id,
            marks_obtained=marks,
            percentage=percentage,
        )
        db.session.add(grade)
    else:
        grade.marks_obtained = marks
        grade.percentage = percentage

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise GradeError("Could not save the grade.") from exc

    return grade


def get_user_grades(user_id):
    """Return the given user's grades, newest recorded first, with assessments."""
    return (
        Grade.query.join(Assessment, Grade.assessment_id == Assessment.id)
        .join(Course, Assessment.course_id == Course.id)
        .filter(Course.user_id == user_id)
        .order_by(Grade.recorded_at.desc())
        .all()
    )


def get_grade(assessment_id, user_id):
    """Return a grade only if its assessment belongs to the given user, else None."""
    return (
        Grade.query.join(Assessment, Grade.assessment_id == Assessment.id)
        .join(Course, Assessment.course_id == Course.id)
        .filter(Grade.assessment_id == assessment_id, Course.user_id == user_id)
        .first()
    )
