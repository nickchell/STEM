"""Assessment management rules, independent of HTTP.

Blueprints collect form data and call these functions. Validation lives here
so Pytest can exercise it without going through templates. Ownership is always
enforced through the parent course: an assessment belongs to the user who owns
its course.
"""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from stem.extensions import db
from stem.models.assessment import Assessment
from stem.models.course import Course

ASSESSMENT_TYPES = ["CAT", "assignment", "quiz", "exam"]
MAX_TITLE_LENGTH = 120


class AssessmentError(Exception):
    """Raised when assessment input cannot be accepted."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def normalize_assessment_type(assessment_type):
    """Validate and normalize an assessment type."""
    if assessment_type is None or not str(assessment_type).strip():
        raise AssessmentError("Assessment type is required.", field="assessment_type")

    assessment_type = str(assessment_type).strip()
    if assessment_type not in ASSESSMENT_TYPES:
        raise AssessmentError(
            "Assessment type must be one of: " + ", ".join(ASSESSMENT_TYPES),
            field="assessment_type",
        )
    return assessment_type


def normalize_title(title):
    """Trim and validate an assessment title."""
    if title is None or not str(title).strip():
        raise AssessmentError("Title is required.", field="title")
    title = str(title).strip()
    if len(title) > MAX_TITLE_LENGTH:
        raise AssessmentError(
            f"Title must be at most {MAX_TITLE_LENGTH} characters.", field="title"
        )
    return title


def normalize_max_marks(max_marks):
    """Validate maximum marks is a positive number."""
    if max_marks is None or str(max_marks).strip() == "":
        raise AssessmentError("Maximum marks is required.", field="max_marks")
    try:
        max_marks = float(max_marks)
    except (TypeError, ValueError) as exc:
        raise AssessmentError("Maximum marks must be a number.", field="max_marks") from exc
    if max_marks <= 0:
        raise AssessmentError("Maximum marks must be greater than zero.", field="max_marks")
    return max_marks


def normalize_assessment_date(assessment_date):
    """Validate an assessment date/time."""
    if assessment_date is None:
        raise AssessmentError("Assessment date is required.", field="assessment_date")
    if isinstance(assessment_date, str):
        try:
            assessment_date = datetime.fromisoformat(assessment_date)
        except ValueError as exc:
            raise AssessmentError("Enter a valid date and time.", field="assessment_date") from exc
    if not isinstance(assessment_date, datetime):
        raise AssessmentError("Enter a valid date and time.", field="assessment_date")
    return assessment_date


def _get_owned_course(course_id, user_id):
    """Return the course if it belongs to the given user, else None."""
    return Course.query.filter_by(id=course_id, user_id=user_id).first()


def create_assessment(user_id, course_id, title, assessment_type, assessment_date, max_marks):
    """Save an assessment for one of the user's courses and return it.

    Raises AssessmentError for validation errors or when the course does not
    belong to the user.
    """
    course = _get_owned_course(course_id, user_id)
    if course is None:
        raise AssessmentError("Course not found or you do not own it.")

    title = normalize_title(title)
    assessment_type = normalize_assessment_type(assessment_type)
    assessment_date = normalize_assessment_date(assessment_date)
    max_marks = normalize_max_marks(max_marks)

    assessment = Assessment(
        course_id=course.id,
        title=title,
        assessment_type=assessment_type,
        assessment_date=assessment_date,
        max_marks=max_marks,
    )
    db.session.add(assessment)

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise AssessmentError("Could not save the assessment.") from exc

    return assessment


def get_user_assessments(user_id):
    """Return the given user's assessments, newest date first, with grades."""
    return (
        Assessment.query.join(Course, Assessment.course_id == Course.id)
        .filter(Course.user_id == user_id)
        .order_by(Assessment.assessment_date.desc())
        .all()
    )


def get_assessment(assessment_id, user_id):
    """Return an assessment only if it belongs to the given user, else None."""
    return (
        Assessment.query.join(Course, Assessment.course_id == Course.id)
        .filter(Assessment.id == assessment_id, Course.user_id == user_id)
        .first()
    )


def update_assessment(assessment_id, user_id, title=None, assessment_type=None,
                      assessment_date=None, max_marks=None):
    """Update an owned assessment's fields and return it."""
    assessment = get_assessment(assessment_id, user_id)
    if assessment is None:
        raise AssessmentError("Assessment not found or you do not own it.")

    if title is not None:
        assessment.title = normalize_title(title)
    if assessment_type is not None:
        assessment.assessment_type = normalize_assessment_type(assessment_type)
    if assessment_date is not None:
        assessment.assessment_date = normalize_assessment_date(assessment_date)
    if max_marks is not None:
        assessment.max_marks = normalize_max_marks(max_marks)

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise AssessmentError("Could not update the assessment.") from exc

    return assessment


def delete_assessment(assessment_id, user_id):
    """Delete an owned assessment (and its grade). Returns True if deleted."""
    assessment = get_assessment(assessment_id, user_id)
    if assessment is None:
        return False
    db.session.delete(assessment)
    db.session.commit()
    return True

