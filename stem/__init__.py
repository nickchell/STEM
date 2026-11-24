"""S.T.E.M. Flask application factory."""

import os

from dotenv import load_dotenv
from flask import Flask

from stem.config import get_config_class
from stem.extensions import csrf, db, login_manager, migrate


def create_app(config_class=None):
    """Build and return a Flask app.

    Pass a config class in tests (TestingConfig). Otherwise STEM_CONFIG
    selects development or production settings.
    """
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    resolved = config_class or get_config_class()
    app.config.from_object(resolved)

    if not app.config.get("TESTING"):
        app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or app.config.get(
            "SECRET_KEY"
        )
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URL"
        ) or app.config.get("SQLALCHEMY_DATABASE_URI")

    _validate_runtime_config(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import models so Flask-Migrate sees them on metadata.
    from stem import models  # noqa: F401
    from stem.blueprints.auth import auth_bp
    from stem.blueprints.assessments import assessments_bp
    from stem.blueprints.courses import courses_bp
    from stem.blueprints.dashboard import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(assessments_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(dashboard_bp)

    return app


def _validate_runtime_config(app):
    """Fail fast when required secrets or database URLs are missing."""
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is not set. Copy .env.example to .env and set a value."
        )

    if app.testing:
        return

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
            "DATABASE_URL is not set. PostgreSQL is required for development "
            "and production. Tests use SQLite automatically."
        )
