"""Assessment HTTP handlers: list, create, edit, delete, record grade.

All routes require authentication and scope data to the current user through
the owning course.
"""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from stem.blueprints.assessments import assessments_bp
from stem.blueprints.assessments.forms import AssessmentForm, GradeForm
from stem.models.course import Course
from stem.services.assessment_service import (
    AssessmentError,
    create_assessment,
    delete_assessment,
    get_assessment,
    get_user_assessments,
    update_assessment,
)
from stem.services.grade_service import GradeError, get_grade, record_grade


@assessments_bp.route("/assessments", methods=["GET"])
@login_required
def index():
    """List the student's assessments, grouped by course."""
    assessments = get_user_assessments(current_user.id)
    courses = (
        Course.query.filter_by(user_id=current_user.id)
        .order_by(Course.course_code)
        .all()
    )
    return render_template(
        "assessments/index.html",
        assessments=assessments,
        courses=courses,
    )


@assessments_bp.route("/assessments/new", methods=["GET", "POST"])
@login_required
def new():
    """Create a new assessment for one of the student's courses."""
    courses = (
        Course.query.filter_by(user_id=current_user.id)
        .order_by(Course.course_code)
        .all()
    )
    form = AssessmentForm()
    form.course_id.choices = [(c.id, f"{c.course_code} — {c.course_name}") for c in courses]
    if not courses:
        flash("Add a course before creating assessments.", "info")
        return redirect(url_for("courses.index"))

    if form.validate_on_submit():
        try:
            create_assessment(
                current_user.id,
                form.course_id.data,
                form.title.data,
                form.assessment_type.data,
                form.assessment_date.data,
                form.max_marks.data,
            )
        except AssessmentError as exc:
            field = getattr(form, exc.field, None) if exc.field else None
            if field is not None:
                field.errors.append(exc.message)
            else:
                flash(exc.message, "danger")
            return render_template("assessments/form.html", form=form, assessment=None)
        flash("Assessment added.", "success")
        return redirect(url_for("assessments.index"))

    return render_template("assessments/form.html", form=form, assessment=None)


@assessments_bp.route("/courses/<int:course_id>/assessments", methods=["GET"])
@login_required
def course_assessments(course_id):
    """Show assessments belonging to a single course (course performance)."""
    course = Course.query.filter_by(id=course_id, user_id=current_user.id).first()
    if course is None:
        flash("Course not found or you do not own it.", "danger")
        return redirect(url_for("courses.index"))

    assessments = sorted(course.assessments, key=lambda a: a.assessment_date, reverse=True)
    return render_template(
        "assessments/course.html",
        course=course,
        assessments=assessments,
    )


@assessments_bp.route("/assessments/<int:assessment_id>/edit", methods=["GET", "POST"])
@login_required
def edit(assessment_id):
    """Edit an owned assessment."""
    assessment = get_assessment(assessment_id, current_user.id)
    if assessment is None:
        flash("Assessment not found or you do not own it.", "danger")
        return redirect(url_for("assessments.index"))

    courses = (
        Course.query.filter_by(user_id=current_user.id)
        .order_by(Course.course_code)
        .all()
    )
    form = AssessmentForm(obj=assessment)
    form.course_id.choices = [(c.id, f"{c.course_code} — {c.course_name}") for c in courses]

    if request.method == "GET":
        form.assessment_date.data = assessment.assessment_date.strftime("%Y-%m-%dT%H:%M")

    if form.validate_on_submit():
        try:
            update_assessment(
                assessment_id,
                current_user.id,
                title=form.title.data,
                assessment_type=form.assessment_type.data,
                assessment_date=form.assessment_date.data,
                max_marks=form.max_marks.data,
            )
        except AssessmentError as exc:
            field = getattr(form, exc.field, None) if exc.field else None
            if field is not None:
                field.errors.append(exc.message)
            else:
                flash(exc.message, "danger")
            return render_template("assessments/form.html", form=form, assessment=assessment)
        flash("Assessment updated.", "success")
        return redirect(url_for("assessments.index"))

    return render_template("assessments/form.html", form=form, assessment=assessment)


@assessments_bp.route("/assessments/<int:assessment_id>/delete", methods=["POST"])
@login_required
def delete(assessment_id):
    """Delete an owned assessment."""
    if delete_assessment(assessment_id, current_user.id):
        flash("Assessment deleted.", "info")
    else:
        flash("Assessment not found or you do not own it.", "danger")
    return redirect(url_for("assessments.index"))


@assessments_bp.route("/assessments/<int:assessment_id>/grade", methods=["POST"])
@login_required
def grade(assessment_id):
    """Record or update a grade for an owned assessment."""
    assessment = get_assessment(assessment_id, current_user.id)
    if assessment is None:
        flash("Assessment not found or you do not own it.", "danger")
        return redirect(url_for("assessments.index"))

    form = GradeForm()
    if form.validate_on_submit():
        try:
            record_grade(
                current_user.id,
                assessment_id,
                form.marks_obtained.data,
            )
        except GradeError as exc:
            flash(exc.message, "danger")
        else:
            flash(
                f"Grade recorded: {form.marks_obtained.data} / {assessment.max_marks} "
                f"({assessment.grade.percentage if assessment.grade else ''}%).",
                "success",
            )
    return redirect(url_for("assessments.index"))
