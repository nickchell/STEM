"""Course management rules, independent of HTTP.

Blueprints collect form data and call these functions. Validation lives here
so Pytest can exercise it without going through templates.
"""

import re

from sqlalchemy.exc import IntegrityError

from stem.extensions import db
from stem.models.course import Course

MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 100


class CourseError(Exception):
    """Raised when course input cannot be accepted."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def normalize_course_code(code):
    """Trim, collapse internal whitespace, and uppercase a course code."""
    if code is None or not str(code).strip():
        raise CourseError("Course code is required.", field="course_code")

    code = re.sub(r"\s+", " ", str(code).strip()).upper()
    if len(code) > MAX_CODE_LENGTH:
        raise CourseError(
            f"Course code must be at most {MAX_CODE_LENGTH} characters.",
            field="course_code",
        )
    return code


def normalize_course_name(name):
    """Trim and validate a course name."""
    if name is None or not str(name).strip():
        raise CourseError("Course name is required.", field="course_name")

    name = str(name).strip()
    if len(name) > MAX_NAME_LENGTH:
        raise CourseError(
            f"Course name must be at most {MAX_NAME_LENGTH} characters.",
            field="course_name",
        )
    return name


def add_course(user_id, course_code, course_name):
    """Save a course for the given user and return it.

    Raises CourseError for validation errors or a duplicate course code for
    that user. The database unique constraint is the final backstop.
    """
    code = normalize_course_code(course_code)
    name = normalize_course_name(course_name)

    existing = (
        Course.query.filter_by(user_id=user_id, course_code=code).first()
    )
    if existing is not None:
        raise CourseError(
            f"You already have a course with code {code}.", field="course_code"
        )

    course = Course(course_code=code, course_name=name, user_id=user_id)
    db.session.add(course)

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise CourseError(
            f"You already have a course with code {code}.", field="course_code"
        ) from exc

    return course


def get_user_courses(user_id):
    """Return the given user's courses, newest first."""
    return (
        Course.query.filter_by(user_id=user_id)
        .order_by(Course.created_at.desc())
        .all()
    )
