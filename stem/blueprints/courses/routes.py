"""Courses HTTP handlers: list courses, add a course. Protected with Flask-Login."""

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from stem.blueprints.courses import courses_bp
from stem.blueprints.courses.forms import CourseForm
from stem.services.course_service import CourseError, add_course, get_user_courses


@courses_bp.route("/courses", methods=["GET", "POST"])
@login_required
def index():
    """Show the student's courses and handle adding a new one."""
    form = CourseForm()
    if form.validate_on_submit():
        try:
            course = add_course(
                current_user.id, form.course_code.data, form.course_name.data
            )
        except CourseError as exc:
            form_field = getattr(form, exc.field, None) if exc.field else None
            if form_field is not None:
                form_field.errors.append(exc.message)
            else:
                flash(exc.message, "danger")
        else:
            flash(
                f"Course {course.course_code} — {course.course_name} added.",
                "success",
            )
            return redirect(url_for("courses.index"))

    courses = get_user_courses(current_user.id)
    return render_template("courses/index.html", form=form, courses=courses)
