"""An assessment (CAT, assignment, quiz or exam) tied to a student's course."""

from datetime import datetime, timezone

from stem.extensions import db


class Assessment(db.Model):
    """A single graded assessment belonging to one of the student's courses.

    Ownership is enforced through the parent course: an assessment can only be
    created for, or accessed through, a course that belongs to the current user.
    """

    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(120), nullable=False)
    assessment_type = db.Column(db.String(20), nullable=False)
    assessment_date = db.Column(db.DateTime(timezone=True), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    course = db.relationship("Course", backref=db.backref("assessments", cascade="all, delete-orphan"))
    grade = db.relationship(
        "Grade",
        uselist=False,
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint("max_marks > 0", name="ck_assessments_max_marks_positive"),
    )

    @property
    def is_upcoming(self):
        """True when the assessment date is in the future."""
        now = datetime.now(timezone.utc)
        date = self.assessment_date
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date >= now

    def __repr__(self):
        return f"<Assessment {self.title} ({self.assessment_type})>"
