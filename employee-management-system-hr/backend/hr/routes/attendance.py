from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Attendance, Employee
from ..utils import (err, admin_required, signed_in, current_user, employee_for_user, clean_string, parse_int,
                     parse_date, parse_time, log_activity, ValidationError)

bp = Blueprint("attendance", __name__, url_prefix="/api")
STATUSES = ("Present", "Absent", "Late", "Half-day", "Leave")


def _check_times(check_in, check_out):
    if check_in and check_out and check_out <= check_in:
        raise ValidationError("Check-out must be later than check-in")


@bp.get("/attendance")
@signed_in
def list_attendance():
    user = current_user()
    q = Attendance.query.join(Employee)
    if user.role != "admin":
        emp = employee_for_user(user)
        q = q.filter(Attendance.employee_id == (emp.id if emp else -1))
    try:
        date_from, date_to = parse_date(request.args.get("from"), "from"), parse_date(request.args.get("to"), "to")
        if date_from:
            q = q.filter(Attendance.attendance_date >= date_from)
        if date_to:
            q = q.filter(Attendance.attendance_date <= date_to)
        if request.args.get("employee_id") and user.role == "admin":
            q = q.filter(Attendance.employee_id == parse_int(request.args["employee_id"], "employee_id"))
    except ValidationError as e:
        return err(str(e))
    q = q.order_by(Attendance.attendance_date.desc(), Attendance.id.desc())
    return jsonify({"items": [a.to_dict() for a in q.limit(500).all()]})


@bp.post("/attendance")
@admin_required
def create_attendance():
    data = request.get_json(silent=True) or {}
    try:
        employee_id = parse_int(data.get("employee_id"), "Employee")
        attendance_date = parse_date(data.get("attendance_date"), "Date", required=True)
        status = data.get("status", "Present")
        if status not in STATUSES:
            return err("Invalid attendance status")
        check_in, check_out = parse_time(data.get("check_in"), "Check-in"), parse_time(data.get("check_out"), "Check-out")
        _check_times(check_in, check_out)
        if not db.session.get(Employee, employee_id):
            return err("Employee not found", 404)
        if Attendance.query.filter_by(employee_id=employee_id, attendance_date=attendance_date).first():
            return err("Attendance already exists for this employee and date", 409)
        a = Attendance(employee_id=employee_id, attendance_date=attendance_date, status=status,
                       check_in=check_in, check_out=check_out, notes=clean_string(data, "notes", False, 500))
        db.session.add(a)
        log_activity(current_user(), "attendance.create", f"employee {employee_id} on {attendance_date}")
        db.session.commit()
        return jsonify({"message": "Attendance saved", "attendance": a.to_dict()}), 201
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))
    except IntegrityError:
        db.session.rollback()
        return err("Attendance already exists for this employee and date", 409)


@bp.put("/attendance/<int:attendance_id>")
@admin_required
def update_attendance(attendance_id):
    a = db.session.get(Attendance, attendance_id)
    if not a:
        return err("Attendance record not found", 404)
    data = request.get_json(silent=True) or {}
    try:
        if "employee_id" in data:
            emp_id = parse_int(data["employee_id"], "Employee")
            if not db.session.get(Employee, emp_id):
                return err("Employee not found", 404)
            a.employee_id = emp_id
        if "attendance_date" in data:
            a.attendance_date = parse_date(data["attendance_date"], "Date", required=True)
        if "status" in data:
            if data["status"] not in STATUSES:
                return err("Invalid attendance status")
            a.status = data["status"]
        if "check_in" in data:
            a.check_in = parse_time(data["check_in"], "Check-in")
        if "check_out" in data:
            a.check_out = parse_time(data["check_out"], "Check-out")
        _check_times(a.check_in, a.check_out)
        if "notes" in data:
            a.notes = clean_string(data, "notes", False, 500)
        log_activity(current_user(), "attendance.update", f"record {a.id}")
        db.session.commit()
        return jsonify({"message": "Attendance updated", "attendance": a.to_dict()})
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))
    except IntegrityError:
        db.session.rollback()
        return err("Attendance already exists for this employee and date", 409)


@bp.delete("/attendance/<int:attendance_id>")
@admin_required
def delete_attendance(attendance_id):
    a = db.session.get(Attendance, attendance_id)
    if not a:
        return err("Attendance record not found", 404)
    log_activity(current_user(), "attendance.delete", f"record {a.id}")
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "Attendance deleted"})
