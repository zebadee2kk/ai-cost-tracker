import os
import pytest

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("ENCRYPTION_KEY", "tXKK1nN-OlnqTmRHlHGGuwR3GwPFzjqfIQcvDHv6D0U=")


@pytest.fixture(scope="session")
def app():
    from app import create_app, db
    from config import TestingConfig

    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    from app import db as _db
    yield _db
    _db.session.rollback()
