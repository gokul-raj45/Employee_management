import os
from datetime import timedelta

import click
from dotenv import load_dotenv
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .extensions import db, migrate, bcrypt, jwt, cors

MIN_SECRET_LEN = 32


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "8")))
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    if config:
        app.config.update(config)

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("DATABASE_URL is not set. Copy backend/.env.example to backend/.env and edit it.")
    secret = app.config["JWT_SECRET_KEY"]
    if not secret or len(secret) < MIN_SECRET_LEN or secret.lower().startswith("replace"):
        raise RuntimeError(
            f"JWT_SECRET_KEY must be a random value of at least {MIN_SECRET_LEN} characters. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(64))"')

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    origins = [o.strip() for o in os.getenv(
        "FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
    cors.init_app(app, resources={r"/api/*": {"origins": origins}})  # explicit allow-list, never "*"

    from . import models  # noqa: F401
    from .routes import register_blueprints
    register_blueprints(app)
    _register_handlers(app)
    _register_cli(app)
    return app


def _register_handlers(app):
    @app.get("/")
    def home():
        return jsonify({"message": "PeopleDesk HR API running"})

    @jwt.unauthorized_loader
    def _missing(reason):
        return jsonify({"error": "Authentication required"}), 401

    @jwt.invalid_token_loader
    def _invalid(reason):
        return jsonify({"error": "Invalid token"}), 401

    @jwt.expired_token_loader
    def _expired(header, payload):
        return jsonify({"error": "Session expired. Please sign in again."}), 401

    @app.errorhandler(HTTPException)
    def _http(e):
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def _unexpected(e):
        db.session.rollback()
        app.logger.exception("Unhandled error")  # details go to the server log only
        return jsonify({"error": "Internal server error"}), 500


def _register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--username", default=lambda: os.getenv("ADMIN_USERNAME", "admin"), show_default="admin")
    @click.option("--email", default=lambda: os.getenv("ADMIN_EMAIL", ""), prompt=True)
    @click.password_option(help="Prompted securely; never stored in .env or shell history.")
    def create_admin(username, email, password):
        """Create the initial administrator (or reset a password with --force via the UI instead)."""
        from .models import User
        from .utils import validate_password, ValidationError
        email = email.strip().lower()
        try:
            validate_password(password)
        except ValidationError as e:
            raise click.ClickException(str(e))
        if User.query.filter((User.email == email) | (User.username == username)).first():
            raise click.ClickException("A user with that email or username already exists.")
        db.session.add(User(username=username, email=email, role="admin",
                            password_hash=bcrypt.generate_password_hash(password).decode("utf-8")))
        db.session.commit()
        click.echo(f"Administrator {email} created.")
