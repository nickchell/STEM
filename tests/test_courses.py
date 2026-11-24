"""Courses management: access control, creation, duplication, scoping, and dashboard integration."""

from stem.extensions import db
from stem.models.course import Course


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


def test_courses_redirect_anonymous_users_to_login(client):
    response = client.get("/courses", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_authenticated_user_can_open_courses_page(client):
    register(client)
    login(client)
    response = client.get("/courses")
    assert response.status_code == 200
    assert b"My courses" in response.data


def test_user_can_add_course(client, app):
    register(client)
    login(client)
    response = add_course(client)
    assert response.status_code == 200
    assert b"added" in response.data.lower()

    with app.app_context():
        courses = Course.query.all()
        assert len(courses) == 1
        assert courses[0].course_code == "EEE 202"
        assert courses[0].course_name == "Engineering Mathematics"
        assert courses[0].created_at is not None


def test_course_is_saved_to_database(client, app):
    register(client)
    login(client)
    add_course(client)

    with app.app_context():
        course = Course.query.filter_by(course_code="EEE 202").one()
        assert course.course_name == "Engineering Mathematics"
        user = course.user
        assert user.email == "student@example.com"


def test_duplicate_course_code_is_rejected(client, app):
    register(client)
    login(client)
    add_course(client)
    response = add_course(client)

    assert response.status_code == 200
    assert b"already have a course" in response.data.lower()

    with app.app_context():
        assert Course.query.filter_by(course_code="EEE 202").count() == 1


def test_duplicate_course_code_is_case_insensitive(client):
    register(client)
    login(client)
    add_course(client, code="EEE 202", name="Engineering Mathematics")
    response = add_course(client, code="eee 202", name="Something else")

    assert response.status_code == 200
    assert b"already have a course" in response.data.lower()


def test_user_cannot_see_another_users_courses(client, app):
    register(client, email="alice@example.com", password="securepass")
    login(client, email="alice@example.com", password="securepass")
    add_course(client, code="EEE 202", name="Engineering Mathematics")

    client.post("/logout")
    register(client, email="bob@example.com", password="securepass")
    login(client, email="bob@example.com", password="securepass")
    add_course(client, code="PHY 101", name="Physics I")

    # Back to Alice: Bob's course must not appear.
    client.post("/logout")
    login(client, email="alice@example.com", password="securepass")
    response = client.get("/courses")
    assert b"EEE 202" in response.data
    assert b"PHY 101" not in response.data


def test_dashboard_shows_course_count(client, app):
    register(client)
    login(client)
    assert b"Total Courses: 0" in client.get("/dashboard").data

    add_course(client)
    response = client.get("/dashboard")
    assert b"Total Courses: 1" in response.data

    add_course(client, code="PHY 101", name="Physics I")
    response = client.get("/dashboard")
    assert b"Total Courses: 2" in response.data


def test_adding_course_creates_recent_activity(client):
    register(client)
    login(client)
    add_course(client)
    response = client.get("/dashboard")
    body = response.data.decode("utf-8")
    assert "Added EEE 202 — Engineering Mathematics" in body


def test_recent_activity_belongs_to_correct_user(client):
    register(client, email="alice@example.com", password="securepass")
    login(client, email="alice@example.com", password="securepass")
    add_course(client, code="EEE 202", name="Engineering Mathematics")

    client.post("/logout")
    register(client, email="bob@example.com", password="securepass")
    login(client, email="bob@example.com", password="securepass")
    add_course(client, code="PHY 101", name="Physics I")

    response = client.get("/dashboard")
    body = response.data.decode("utf-8")
    assert "Added PHY 101 — Physics I" in body
    assert "Added EEE 202 — Engineering Mathematics" not in body


def test_courses_survive_logout_and_login(client, app):
    register(client)
    login(client)
    add_course(client)

    client.post("/logout")
    login(client)

    response = client.get("/courses")
    assert b"EEE 202" in response.data
    assert b"Engineering Mathematics" in response.data

    with app.app_context():
        assert Course.query.filter_by(course_code="EEE 202").count() == 1

    dashboard = client.get("/dashboard")
    body = dashboard.data.decode("utf-8")
    assert "Total Courses: 1" in body
    assert "Added EEE 202 — Engineering Mathematics" in body
