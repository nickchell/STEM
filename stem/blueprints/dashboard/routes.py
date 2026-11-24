"""Student dashboard HTTP handlers. Protected with Flask-Login."""

from datetime import datetime, timezone

from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from stem.blueprints.dashboard import dashboard_bp
from stem.models.assessment import Assessment
from stem.models.course import Course
from stem.models.grade import Grade


@dashboard_bp.route("/")
def home():
    """Send visitors to the dashboard or the login page."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    course_count = Course.query.filter_by(user_id=current_user.id).count()
    recent_courses = (
        Course.query.filter_by(user_id=current_user.id)
        .order_by(Course.created_at.desc())
        .limit(5)
        .all()
    )

    total_assessments = (
        Assessment.query.join(Course, Assessment.course_id == Course.id)
        .filter(Course.user_id == current_user.id)
        .count()
    )

    upcoming_assessments = (
        Assessment.query.join(Course, Assessment.course_id == Course.id)
        .filter(Course.user_id == current_user.id)
        .filter(Assessment.assessment_date >= datetime.now(timezone.utc))
        .order_by(Assessment.assessment_date.asc())
        .limit(5)
        .all()
    )

    recent_grades = (
        Grade.query.join(Assessment, Grade.assessment_id == Assessment.id)
        .join(Course, Assessment.course_id == Course.id)
        .filter(Course.user_id == current_user.id)
        .order_by(Grade.recorded_at.desc())
        .limit(5)
        .all()
    )

    graded = [g for g in recent_grades if g.percentage is not None]
    overall_performance = (
        round(sum(g.percentage for g in graded) / len(graded), 2) if graded else None
    )

    return render_template(
        "dashboard/index.html",
        course_count=course_count,
        recent_courses=recent_courses,
        total_assessments=total_assessments,
        upcoming_assessments=upcoming_assessments,
        recent_grades=recent_grades,
        overall_performance=overall_performance,
    )
