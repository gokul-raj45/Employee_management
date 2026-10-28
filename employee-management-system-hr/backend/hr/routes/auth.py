import os
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from ..extensions import db, bcrypt
from ..models import User
from ..utils import (err, signed_in, current_user, employee_for_user, clean_string, clean_email,
                     validate_password, ValidationError)

bp = Blueprint("auth", __name__, url_prefix="/api")


def _registration_enabled():
    return os.getenv("ALLOW_SELF_REGISTRATION", "false").lower() == "true"


@bp.get("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        db.session.rollback()
        return err("Database connection failed", 503)


@bp.get("/auth/config")
def auth_config():
    return jsonify({"self_registration": _registration_enabled()})


@bp.post("/register")
def register():
    """Disabled by default: an unverified self-registered email could otherwise be used
    to claim someone else's HR record. Admins create employee logins instead."""
    if not _registration_enabled():
        return err("Self-registration is disabled. Ask an administrator to create your account.", 403)
    data = request.get_json(silent=True) or {}
    try:
        username = clean_string(data, "username", True, 80)
        email = clean_email(data)
        validate_password(data.get("password"))
        if User.query.filter((User.username == username) | (User.email == email)).first():
            return err("Username or email already exists", 409)
        user = User(username=username, email=email, role="employee",
                    password_hash=bcrypt.generate_password_hash(data["password"]).decode("utf-8"))
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "Account created. An administrator must link it to your employee record.",
                        "user": user.to_dict()}), 201
    except ValidationError as e:
        return err(str(e))
    except IntegrityError:
        db.session.rollback()
        return err("Username or email already exists", 409)


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email, password = data.get("email"), data.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password:
        return err("Email and password are required")
    user = User.query.filter_by(email=email.strip().lower()).first()
    # Same message for unknown email and wrong password (no account enumeration).
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return err("Invalid email or password", 401)
    if not user.is_active:
        return err("This account has been deactivated. Contact an administrator.", 403)
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.get("/me")
@signed_in
def me():
    user = current_user()
    emp = employee_for_user(user)
    return jsonify({**user.to_dict(), "employee": emp.to_dict() if emp else None})


@bp.put("/me/profile")
@signed_in
def update_profile():
    """Employees may edit only these contact fields; everything else is admin-controlled."""
    emp = employee_for_user(current_user())
    if not emp:
        return err("No employee record is linked to your account", 404)
    data = request.get_json(silent=True) or {}
    try:
        if "phone" in data:
            emp.phone = clean_string(data, "phone", False, 30)
        if "location" in data:
            emp.location = clean_string(data, "location", False, 100)
        db.session.commit()
        return jsonify({"message": "Profile updated", "employee": emp.to_dict()})
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))


@bp.post("/change-password")
@signed_in
def change_password():
    user = current_user()
    data = request.get_json(silent=True) or {}
    current, new = data.get("current_password"), data.get("new_password")
    if not isinstance(current, str) or not bcrypt.check_password_hash(user.password_hash, current):
        return err("Current password is incorrect", 400)
    try:
        validate_password(new)
    except ValidationError as e:
        return err(str(e))
    if new == current:
        return err("New password must be different from the current password")
    user.password_hash = bcrypt.generate_password_hash(new).decode("utf-8")
    user.must_change_password = False
    db.session.commit()
    return jsonify({"message": "Password changed", "user": user.to_dict()})
