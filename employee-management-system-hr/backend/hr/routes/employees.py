import csv
import io
import os

from flask import Blueprint, request, jsonify, make_response
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..extensions import db, bcrypt
from ..models import User, Employee, Department
from ..utils import (err, admin_required, signed_in, current_user, employee_for_user, clean_string,
                     clean_email, parse_date, validate_password, log_activity, escape_like, csv_safe,
                     ValidationError)

bp = Blueprint("employees", __name__, url_prefix="/api")
STATUSES = ("Active", "On Leave", "Inactive")
EMPLOYMENT_TYPES = ("Full-time", "Part-time", "Contract", "Intern")


def _sync_login(emp):
    """Keep the linked login's is_active in step with the employee status."""
    if emp.user_id:
        user = db.session.get(User, emp.user_id)
        if user and user.role != "admin":
            user.is_active = emp.status != "Inactive"


def _unique_username(email):
    base = email.split("@")[0][:70] or "user"
    name, n = base, 1
    while User.query.filter_by(username=name).first():
        n += 1
        name = f"{base}{n}"
    return name


def _enum(data, key, allowed, default):
    value = clean_string(data, key, False, 30) or default
    if value not in allowed:
        raise ValidationError(f"{key.replace('_', ' ').title()} must be one of: {', '.join(allowed)}")
    return value


@bp.get("/employees")
@signed_in
def list_employees():
    user = current_user()
    q = Employee.query
    if user.role != "admin":
        emp = employee_for_user(user)
        q = q.filter(Employee.id == (emp.id if emp else -1))
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    status = request.args.get("status", "").strip()
    if search:
        like = f"%{escape_like(search)}%"
        q = q.filter(or_(*[c.ilike(like, escape="\\") for c in
                           (Employee.name, Employee.email, Employee.employee_code, Employee.department, Employee.designation)]))
    if department:
        q = q.filter(Employee.department == department)
    if status:
        q = q.filter(Employee.status == status)
    sort_fields = {"name": Employee.name, "department": Employee.department,
                   "joining_date": Employee.joining_date, "created_at": Employee.created_at}
    column = sort_fields.get(request.args.get("sort", "name"), Employee.name)
    q = q.order_by(column.desc() if request.args.get("direction") == "desc" else column.asc(), Employee.id)
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 10))))
    except ValueError:
        return err("page and per_page must be integers")
    p = q.paginate(page=page, per_page=per_page, error_out=False)
    departments = []
    if user.role == "admin":
        names = {r[0] for r in db.session.query(Employee.department).distinct()}
        names |= {r[0] for r in db.session.query(Department.name)}
        departments = sorted(names)
    return jsonify({"items": [e.to_dict() for e in p.items], "total": p.total, "page": page,
                    "per_page": per_page, "pages": p.pages, "departments": departments})


@bp.post("/employees")
@admin_required
def create_employee():
    data = request.get_json(silent=True) or {}
    admin = current_user()
    try:
        name = clean_string(data, "name", True, 100)
        email = clean_email(data)
        department = clean_string(data, "department", True, 100)
        designation = clean_string(data, "designation", True, 100)
        if Employee.query.filter_by(email=email).first():
            return err("Employee email already exists", 409)
        code = clean_string(data, "employee_code", False, 30) or "EMP-" + os.urandom(3).hex().upper()
        if Employee.query.filter_by(employee_code=code).first():
            return err("Employee code already exists", 409)
        emp = Employee(employee_code=code, name=name, email=email, department=department, designation=designation,
                       phone=clean_string(data, "phone", False, 30),
                       employment_type=_enum(data, "employment_type", EMPLOYMENT_TYPES, "Full-time"),
                       status=_enum(data, "status", STATUSES, "Active"),
                       location=clean_string(data, "location", False, 100),
                       notes=clean_string(data, "notes", False, 2000),
                       joining_date=parse_date(data.get("joining_date"), "Joining date"))
        initial_password = data.get("initial_password")
        user = User.query.filter_by(email=email).first()
        if user and Employee.query.filter_by(user_id=user.id).first():
            return err("A login with this email is already linked to another employee", 409)
        if initial_password:
            validate_password(initial_password)
            if user:
                return err("A login with this email already exists; leave the password blank to link it", 409)
            user = User(username=_unique_username(email), email=email, role="employee", must_change_password=True,
                        password_hash=bcrypt.generate_password_hash(initial_password).decode("utf-8"))
            db.session.add(user)
            db.session.flush()
        db.session.add(emp)
        if user:
            emp.user_id = user.id
        db.session.flush()
        _sync_login(emp)
        log_activity(admin, "employee.create", f"{emp.employee_code} {emp.name}")
        db.session.commit()
        return jsonify({"message": "Employee created", "employee": emp.to_dict(), "login_created": bool(initial_password)}), 201
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))
    except IntegrityError:
        db.session.rollback()
        return err("Employee email, code or login already exists", 409)


@bp.get("/employees/<int:employee_id>")
@signed_in
def get_employee(employee_id):
    user = current_user()
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return err("Employee not found", 404)
    if user.role != "admin":
        own = employee_for_user(user)
        if not own or own.id != emp.id:
            return err("You can only view your own employee details", 403)
    return jsonify(emp.to_dict())


@bp.put("/employees/<int:employee_id>")
@admin_required
def update_employee(employee_id):
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return err("Employee not found", 404)
    data = request.get_json(silent=True) or {}
    try:
        if "name" in data:
            emp.name = clean_string(data, "name", True, 100)
        if "email" in data:
            email = clean_email(data)
            if Employee.query.filter(Employee.email == email, Employee.id != emp.id).first():
                return err("Employee email already exists", 409)
            emp.email = email  # the explicit user_id link is NOT changed when the email changes
        if "department" in data:
            emp.department = clean_string(data, "department", True, 100)
        if "designation" in data:
            emp.designation = clean_string(data, "designation", True, 100)
        if data.get("employee_code"):
            code = clean_string(data, "employee_code", True, 30)
            if Employee.query.filter(Employee.employee_code == code, Employee.id != emp.id).first():
                return err("Employee code already exists", 409)
            emp.employee_code = code
        for field, limit in (("phone", 30), ("location", 100), ("notes", 2000)):
            if field in data:
                setattr(emp, field, clean_string(data, field, False, limit))
        if "employment_type" in data:
            emp.employment_type = _enum(data, "employment_type", EMPLOYMENT_TYPES, "Full-time")
        if "status" in data:
            emp.status = _enum(data, "status", STATUSES, "Active")
            _sync_login(emp)
        if "joining_date" in data:
            emp.joining_date = parse_date(data["joining_date"], "Joining date")
        log_activity(current_user(), "employee.update", f"{emp.employee_code} {emp.name}")
        db.session.commit()
        return jsonify({"message": "Employee updated", "employee": emp.to_dict()})
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))
    except IntegrityError:
        db.session.rollback()
        return err("Duplicate employee details", 409)


@bp.post("/employees/<int:employee_id>/deactivate")
@admin_required
def deactivate_employee(employee_id):
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return err("Employee not found", 404)
    emp.status = "Inactive"
    _sync_login(emp)
    log_activity(current_user(), "employee.deactivate", f"{emp.employee_code} {emp.name}")
    db.session.commit()
    return jsonify({"message": "Employee deactivated; login disabled", "employee": emp.to_dict()})


@bp.post("/employees/<int:employee_id>/activate")
@admin_required
def activate_employee(employee_id):
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return err("Employee not found", 404)
    emp.status = "Active"
    _sync_login(emp)
    log_activity(current_user(), "employee.activate", f"{emp.employee_code} {emp.name}")
    db.session.commit()
    return jsonify({"message": "Employee reactivated", "employee": emp.to_dict()})


@bp.delete("/employees/<int:employee_id>")
@admin_required
def delete_employee(employee_id):
    """Permanent delete (also removes that employee's attendance, salary and leave rows).
    Prefer /deactivate to keep history."""
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return err("Employee not found", 404)
    log_activity(current_user(), "employee.delete", f"{emp.employee_code} {emp.name}")
    db.session.delete(emp)
    db.session.commit()
    return jsonify({"message": "Employee deleted"})


@bp.get("/employees/export.csv")
@admin_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    cols = ["id", "employee_code", "name", "email", "phone", "department", "designation",
            "employment_type", "status", "joining_date", "location"]
    writer.writerow(cols)
    for e in Employee.query.order_by(Employee.name).all():
        d = e.to_dict()
        writer.writerow([csv_safe(d.get(k)) for k in cols])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=employees.csv"
    return response
