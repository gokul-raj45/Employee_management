"""Shared helpers: validation, error responses, auth decorators, activity logging."""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_

from .extensions import db
from .models import User, Employee, ActivityLog

MAX_MONEY = Decimal("9999999999.99")  # fits Numeric(12, 2)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def err(message, code=400):
    return jsonify({"error": message}), code


def current_user():
    try:
        return db.session.get(User, int(get_jwt_identity()))
    except (TypeError, ValueError):
        return None


def _guard(fn, admin_only):
    @wraps(fn)
    @jwt_required()
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user.is_active:
            return err("Account not found or disabled", 401)
        if admin_only and user.role != "admin":
            return err("Administrator access required", 403)
        return fn(*args, **kwargs)
    return wrapped


def admin_required(fn):
    return _guard(fn, True)


def signed_in(fn):
    return _guard(fn, False)


def employee_for_user(user):
    """The employee record linked to this login (by explicit user_id link only)."""
    if not user:
        return None
    return Employee.query.filter(Employee.user_id == user.id).first()


def log_activity(user, action, detail=""):
    db.session.add(ActivityLog(user_id=user.id, actor=user.username, action=action, detail=(detail or "")[:255]))


# ---------- validation ----------
class ValidationError(ValueError):
    pass


def clean_string(data, key, required=False, max_len=None):
    label = key.replace("_", " ").title()
    value = data.get(key)
    if value is None:
        if required:
            raise ValidationError(f"{label} is required")
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be text")
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{label} is required")
    if max_len and len(value) > max_len:
        raise ValidationError(f"{label} is too long (max {max_len})")
    return value or None


def clean_email(data, key="email", required=True):
    value = clean_string(data, key, required, 120)
    if value is None:
        return None
    value = value.lower()
    if not EMAIL_RE.match(value):
        raise ValidationError("Enter a valid email address")
    return value


def parse_int(value, label):
    if isinstance(value, bool) or value in (None, ""):
        raise ValidationError(f"{label} is required")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} must be a whole number")


def parse_date(value, label, required=False):
    if value in (None, ""):
        if required:
            raise ValidationError(f"{label} is required")
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{label} must use YYYY-MM-DD")


def parse_time(value, label):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        raise ValidationError(f"{label} must use HH:MM")


def parse_money(data, field):
    value = data.get(field)
    if value in (None, ""):
        return Decimal("0")
    label = field.replace("_", " ").title()
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError(f"{label} must be a number")
    if not amount.is_finite() or amount < 0 or amount > MAX_MONEY:
        raise ValidationError(f"{label} must be between 0 and {MAX_MONEY}")
    return amount.quantize(Decimal("0.01"))


def validate_password(password):
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("Password must contain at least 8 characters")
    if len(password) > 72:  # bcrypt ignores bytes beyond 72
        raise ValidationError("Password must be at most 72 characters")
    return password


def escape_like(term):
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def csv_safe(value):
    """Neutralise spreadsheet formula injection in exported CSV cells."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text
