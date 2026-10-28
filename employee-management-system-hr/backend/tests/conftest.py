import os
import secrets

import pytest

TEST_DB = os.getenv("TEST_DATABASE_URL", "sqlite://")
from sqlalchemy.engine import make_url  # noqa: E402

if not TEST_DB.startswith("sqlite") and "test" not in (make_url(TEST_DB).database or ""):
    raise RuntimeError("Refusing to run tests: TEST_DATABASE_URL database name must contain 'test' "
                       "(tests drop and recreate all tables).")
os.environ.setdefault("DATABASE_URL", TEST_DB)
os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))

from hr import create_app  # noqa: E402
from hr.extensions import db, bcrypt  # noqa: E402
from hr.models import User  # noqa: E402

PW = "Passw0rd!test"


@pytest.fixture()
def app():
    app = create_app({"SQLALCHEMY_DATABASE_URI": TEST_DB, "TESTING": True, "PROPAGATE_EXCEPTIONS": False,
                      "SQLALCHEMY_ENGINE_OPTIONS": {}, "BCRYPT_LOG_ROUNDS": 4})
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(User(username="admin", email="admin@test.local", role="admin",
                            password_hash=bcrypt.generate_password_hash(PW).decode()))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email, password=PW):
    r = client.post("/api/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": "Bearer " + r.get_json()["access_token"]}


@pytest.fixture()
def admin(client):
    return _login(client, "admin@test.local")


@pytest.fixture()
def make_employee(client, admin):
    """Create an employee WITH a login via the admin API; returns (employee_dict, auth_headers)."""
    def _make(name, email, **extra):
        body = {"name": name, "email": email, "department": "Engineering", "designation": "Developer",
                "initial_password": PW, **extra}
        r = client.post("/api/employees", json=body, headers=admin)
        assert r.status_code == 201, r.get_json()
        return r.get_json()["employee"], _login(client, email)
    return _make
