import pytest
from app import create_app
from app.extensions import db
from app.models.course import Course
from app.models.student import Student
from app.models.session import ClassSession
from app.models.settings import PrivacySetting

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_course(app):
    with app.app_context():
        course = Course(code="CS202", name="Computer Vision & Deep Learning")
        db.session.add(course)
        db.session.commit()
        return course.id

@pytest.fixture
def sample_session(app, sample_course):
    with app.app_context():
        sess = ClassSession(
            title="Introduction to Object Detection",
            course_id=sample_course,
            expected_duration_minutes=60,
            input_source_type="synthetic",
        )
        db.session.add(sess)
        db.session.commit()
        return sess.id
