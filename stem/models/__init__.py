"""SQLAlchemy models.

Importing this package registers models with Flask-Migrate's metadata.
"""

from stem.models.assessment import Assessment
from stem.models.course import Course
from stem.models.grade import Grade
from stem.models.user import User

__all__ = ["Assessment", "Course", "Grade", "User"]
