"""A course owned by a registered student."""

from datetime import datetime, timezone

from stem.extensions import db


class Course(db.Model):
    """A single course (for example EEE 202 - Engineering Mathematics).

    Every course belongs to exactly one student. Course codes are normalized
    (trimmed, whitespace collapsed, upper-cased) so a user cannot register the
    same course twice under different casing.
    """

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(50), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("courses", cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "course_code", name="uq_courses_user_id_course_code"),
    )

    def __repr__(self):
        return f"<Course {self.course_code} - {self.course_name}>"
