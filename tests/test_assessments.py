"""Assessments and grades: creation, validation, ownership, grading, and dashboard integration."""

from datetime import datetime, timezone, timedelta

from stem.extensions import db
from stem.models.assessment import Assessment
from stem.models.course import Course
from stem.models.grade import Grade


def register(client, email="student@example.com", password="securepass"):
    return client.post(
        "/register",
        data={
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, email="student@example.com", password="securepass"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def add_course(client, code="EEE 202", name="Engineering Mathematics"):
    return client.post(
        "/courses",
        data={"course_code": code, "course_name": name},
        follow_redirects=True,
    )


def add_assessment(client, course_id=1, title="CAT 1", assessment_type="CAT",
                   date_offset_days=7, max_marks="100"):
    assessment_date = (datetime.now(timezone.utc) + timedelta(days=date_offset_days))
    return client.post(
        "/assessments/new",
        data={
            "course_id": course_id,
            "title": title,
            "assessment_type": assessment_type,
            "assessment_date": assessment_date.strftime("%Y-%m-%dT%H:%M"),
            "max_marks": max_marks,
        },
        follow_redirects=True,
    )


def test_assessments_redirect_anonymous_users_to_login(client):
    response = client.get("/assessments", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_authenticated_user_can_open_assessments_page(client):
    register(client)
    login(client)
    response = client.get("/assessments")
    assert response.status_code == 200
    assert b"My assessments" in response.data


def test_user_can_create_assessment(client, app):
    register(client)
    login(client)
    add_course(client)
    response = add_assessment(client)
    assert response.status_code == 200
    assert b"Assessment added" in response.data

    with app.app_context():
        assessments = Assessment.query.all()
        assert len(assessments) == 1
        a = assessments[0]
        assert a.title == "CAT 1"
        assert a.assessment_type == "CAT"
        assert a.max_marks == 100.0
        assert a.course.course_code == "EEE 202"
        assert a.assessment_date is not None


def test_assessment_saved_to_database(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client, title="Final Exam", assessment_type="exam", max_marks="200")

    with app.app_context():
        assessment = Assessment.query.filter_by(title="Final Exam").one()
        assert assessment.assessment_type == "exam"
        assert assessment.max_marks == 200.0
        assert assessment.course.user.email == "student@example.com"


def test_assessment_title_is_required(client):
    register(client)
    login(client)
    add_course(client)
    future = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    response = client.post(
        "/assessments/new",
        data={
            "course_id": 1,
            "title": "",
            "assessment_type": "CAT",
            "assessment_date": future,
            "max_marks": "100",
        },
        follow_redirects=True,
    )
    assert b"Title is required" in response.data


def test_invalid_assessment_type_is_rejected(client):
    register(client)
    login(client)
    add_course(client)
    future = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    response = client.post(
        "/assessments/new",
        data={
            "course_id": 1,
            "title": "Test",
            "assessment_type": "midterm",
            "assessment_date": future,
            "max_marks": "100",
        },
        follow_redirects=True,
    )
    assert b"Not a valid choice" in response.data


def test_non_positive_max_marks_is_rejected(client):
    register(client)
    login(client)
    add_course(client)
    response = add_assessment(client, max_marks="0")
    assert b"Maximum marks must be greater than zero" in response.data


def test_assessment_types_include_cat_assignment_quiz_exam(client):
    register(client)
    login(client)
    add_course(client)
    response = client.get("/assessments/new")
    assert b"CAT" in response.data
    assert b"Assignment" in response.data
    assert b"Quiz" in response.data
    assert b"Exam" in response.data


# ---------- Edit and delete ----------

def test_user_can_edit_assessment(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client, title="Old Title")

    with app.app_context():
        assessment_id = Assessment.query.first().id

    future = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    response = client.post(
        f"/assessments/{assessment_id}/edit",
        data={
            "course_id": 1,
            "title": "Updated Title",
            "assessment_type": "assignment",
            "assessment_date": future,
            "max_marks": "50",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Assessment updated" in response.data

    with app.app_context():
        assessment = Assessment.query.get(assessment_id)
        assert assessment.title == "Updated Title"
        assert assessment.assessment_type == "assignment"
        assert assessment.max_marks == 50.0


def test_user_can_delete_assessment(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client)

    with app.app_context():
        assessment_id = Assessment.query.first().id

    response = client.post(
        f"/assessments/{assessment_id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Assessment deleted" in response.data

    with app.app_context():
        assert Assessment.query.count() == 0


# ---------- Ownership ----------

def test_user_cannot_access_another_users_assessments(client, app):
    register(client, email="alice@example.com", password="securepass")
    login(client, email="alice@example.com", password="securepass")
    add_course(client, code="EEE 202", name="Engineering Mathematics")
    add_assessment(client, title="Alice's CAT")

    client.post("/logout")
    register(client, email="bob@example.com", password="securepass")
    login(client, email="bob@example.com", password="securepass")
    add_course(client, code="PHY 101", name="Physics I")
    add_assessment(client, course_id=2, title="Bob's CAT")

    response = client.get("/assessments")
    body = response.data.decode("utf-8")
    assert "Alice&#39;s CAT" not in body
    assert "Bob&#39;s CAT" in body

    with app.app_context():
        alice_assessment = Assessment.query.filter_by(title="Alice's CAT").first()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    response = client.post(
        f"/assessments/{alice_assessment.id}/edit",
        data={
            "course_id": 2,
            "title": "Hacked",
            "assessment_type": "CAT",
            "assessment_date": future,
            "max_marks": "100",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert Assessment.query.get(alice_assessment.id).title == "Alice's CAT"


# ---------- Grades ----------

def test_user_can_record_grade(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client)

    with app.app_context():
        assessment_id = Assessment.query.first().id

    response = client.post(
        f"/assessments/{assessment_id}/grade",
        data={"marks_obtained": "85"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Grade recorded" in response.data

    with app.app_context():
        grade = Grade.query.filter_by(assessment_id=assessment_id).one()
        assert grade.marks_obtained == 85.0
        assert grade.percentage == 85.0  # 85/100 * 100


def test_percentage_is_calculated_automatically(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client, max_marks="200")

    with app.app_context():
        assessment_id = Assessment.query.first().id

    client.post(f"/assessments/{assessment_id}/grade", data={"marks_obtained": "150"}, follow_redirects=True)
    with app.app_context():
        grade = Grade.query.filter_by(assessment_id=assessment_id).one()
        assert grade.percentage == 75.0  # 150/200 * 100


def test_negative_marks_are_rejected(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client)

    with app.app_context():
        assessment_id = Assessment.query.first().id

    response = client.post(
        f"/assessments/{assessment_id}/grade",
        data={"marks_obtained": "-10"},
        follow_redirects=True,
    )
    assert b"Marks obtained cannot be negative" in response.data


def test_marks_above_max_are_rejected(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client, max_marks="100")

    with app.app_context():
        assessment_id = Assessment.query.first().id

    response = client.post(
        f"/assessments/{assessment_id}/grade",
        data={"marks_obtained": "120"},
        follow_redirects=True,
    )
    assert b"cannot be greater than maximum marks" in response.data


def test_user_can_update_grade(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client)

    with app.app_context():
        assessment_id = Assessment.query.first().id

    client.post(f"/assessments/{assessment_id}/grade", data={"marks_obtained": "70"}, follow_redirects=True)
    client.post(f"/assessments/{assessment_id}/grade", data={"marks_obtained": "90"}, follow_redirects=True)

    with app.app_context():
        grade = Grade.query.filter_by(assessment_id=assessment_id).one()
        assert grade.marks_obtained == 90.0
        assert Grade.query.filter_by(assessment_id=assessment_id).count() == 1


def test_grade_belongs_to_correct_user(client, app):
    register(client, email="alice@example.com", password="securepass")
    login(client, email="alice@example.com", password="securepass")
    add_course(client, code="EEE 202", name="Engineering Mathematics")
    add_assessment(client, title="Alice's CAT")

    client.post("/logout")
    register(client, email="bob@example.com", password="securepass")
    login(client, email="bob@example.com", password="securepass")
    add_course(client, code="PHY 101", name="Physics I")
    add_assessment(client, course_id=2, title="Bob's CAT")

    with app.app_context():
        bob_assessment = Assessment.query.filter_by(title="Bob's CAT").first()
    client.post(f"/assessments/{bob_assessment.id}/grade", data={"marks_obtained": "88"}, follow_redirects=True)

    response = client.get("/assessments")
    body = response.data.decode("utf-8")
    assert "88" in body


# ---------- Dashboard integration ----------

def test_dashboard_shows_total_assessments(client, app):
    register(client)
    login(client)
    assert b"Total Assessments: 0" in client.get("/dashboard").data

    add_course(client)
    add_assessment(client)
    response = client.get("/dashboard")
    assert b"Total Assessments: 1" in response.data

    add_assessment(client, title="Second CAT", date_offset_days=2)
    response = client.get("/dashboard")
    assert b"Total Assessments: 2" in response.data


def test_dashboard_shows_upcoming_assessments(client):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client, title="Upcoming CAT")

    response = client.get("/dashboard")
    body = response.data.decode("utf-8")
    assert "Upcoming CAT" in body


def test_dashboard_shows_recent_grades(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client)

    with app.app_context():
        assessment_id = Assessment.query.first().id

    client.post(f"/assessments/{assessment_id}/grade", data={"marks_obtained": "92"}, follow_redirects=True)
    response = client.get("/dashboard")
    body = response.data.decode("utf-8")
    assert "CAT 1" in body
    assert "92" in body


def test_dashboard_shows_overall_performance(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client, max_marks="100")

    with app.app_context():
        assessment_id = Assessment.query.first().id

    client.post(f"/assessments/{assessment_id}/grade", data={"marks_obtained": "80"}, follow_redirects=True)
    response = client.get("/dashboard")
    body = response.data.decode("utf-8")
    assert "Overall academic performance" in body
    assert "80.00%" in body


# ---------- Persistence ----------

def test_assessments_persist_after_logout_and_login(client, app):
    register(client)
    login(client)
    add_course(client)
    add_assessment(client, title="Persistent CAT")
    with app.app_context():
        assessment_id = Assessment.query.first().id
    client.post(f"/assessments/{assessment_id}/grade", data={"marks_obtained": "77"}, follow_redirects=True)

    client.post("/logout")
    login(client)

    response = client.get("/assessments")
    assert b"Persistent CAT" in response.data
    assert b"77" in response.data

    dashboard = client.get("/dashboard")
    body = dashboard.data.decode("utf-8")
    assert "Total Assessments: 1" in body
    assert "Persistent CAT" in body

    with app.app_context():
        assert Assessment.query.filter_by(title="Persistent CAT").count() == 1
        assert Grade.query.count() == 1

