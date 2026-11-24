"""A recorded grade (marks obtained) for a single assessment."""

from datetime import datetime, timezone

from stem.extensions import db


class Grade(db.Model):
    """The marks obtained for one assessment.

    There is at most one grade per assessment. The percentage is derived from
    marks obtained versus maximum marks and stored for convenient display.
    """

    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    marks_obtained = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    assessment = db.relationship("Assessment", back_populates="grade")

    __table_args__ = (
        db.CheckConstraint("marks_obtained >= 0", name="ck_grades_marks_non_negative"),
    )

    def __repr__(self):
        return f"<Grade {self.marks_obtained}/{self.assessment.max_marks} ({self.percentage}%)>"
