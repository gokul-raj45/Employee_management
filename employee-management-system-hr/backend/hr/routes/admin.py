from datetime import date

from flask import Blueprint, request, jsonify
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (Employee, Attendance, SalaryRecord, LeaveRequest, ActivityLog, Department, Designation)
from ..utils import (err, admin_required, signed_in, current_user, employee_for_user, clean_string,
                     log_activity, MONTH_RE, ValidationError)

bp = Blueprint("admin", __name__, url_prefix="/api")


@bp.get("/dashboard")
@signed_in
def dashboard():
    user = current_user()
    if user.role == "admin":
        total = Employee.query.count()
        by_department = (db.session.query(Employee.department, func.count(Employee.id))
                         .group_by(Employee.department).order_by(Employee.department).all())
        today = date.today()
        att_today = dict(db.session.query(Attendance.status, func.count(Attendance.id))
                         .filter(Attendance.attendance_date == today).group_by(Attendance.status).all())
        recent = ActivityLog.query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(8).all()
        return jsonify({"role": "admin", "total": total,
                        "active": Employee.query.filter_by(status="Active").count(),
                        "on_leave": Employee.query.filter_by(status="On Leave").count(),
                        "inactive": Employee.query.filter_by(status="Inactive").count(),
                        "pending_leaves": LeaveRequest.query.filter_by(status="Pending").count(),
                        "attendance_today": att_today,
                        "by_department": [{"department": d, "count": n} for d, n in by_department],
                        "recent_activity": [a.to_dict() for a in recent]})
    emp = employee_for_user(user)
    if not emp:
        return jsonify({"role": "employee", "employee": None, "attendance_count": 0, "salary_count": 0,
                        "leave_pending": 0})
    return jsonify({"role": "employee", "employee": emp.to_dict(),
                    "attendance_count": Attendance.query.filter_by(employee_id=emp.id).count(),
                    "salary_count": SalaryRecord.query.filter_by(employee_id=emp.id).count(),
                    "leave_pending": LeaveRequest.query.filter_by(employee_id=emp.id, status="Pending").count()})


@bp.get("/reports/summary")
@admin_required
def report_summary():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    if not MONTH_RE.match(month):
        return err("month must use YYYY-MM")
    first = date.fromisoformat(month + "-01")
    nxt = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
    att = dict(db.session.query(Attendance.status, func.count(Attendance.id))
               .filter(Attendance.attendance_date >= first, Attendance.attendance_date < nxt)
               .group_by(Attendance.status).all())
    pay = db.session.query(
        func.coalesce(func.sum(SalaryRecord.basic_salary + SalaryRecord.allowances + SalaryRecord.bonus
                               - SalaryRecord.deductions), 0),
        func.count(SalaryRecord.id)).filter(SalaryRecord.pay_month == month).one()
    paid = db.session.query(SalaryRecord.payment_status, func.count(SalaryRecord.id)) \
        .filter(SalaryRecord.pay_month == month).group_by(SalaryRecord.payment_status).all()
    leaves = dict(db.session.query(LeaveRequest.status, func.count(LeaveRequest.id))
                  .filter(LeaveRequest.start_date >= first, LeaveRequest.start_date < nxt)
                  .group_by(LeaveRequest.status).all())
    return jsonify({"month": month, "attendance": att, "leaves": leaves,
                    "payroll": {"total_net": float(pay[0]), "records": pay[1], "by_status": dict(paid)}})


@bp.get("/activity")
@admin_required
def activity():
    limit = min(100, max(1, request.args.get("limit", 25, type=int)))
    rows = ActivityLog.query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit).all()
    return jsonify({"items": [a.to_dict() for a in rows]})


# ---------- departments & designations (simple lookup CRUD) ----------
def _lookup_routes(model, path, field, label, in_use):
    def listing():
        return jsonify({"items": [r.to_dict() for r in model.query.order_by(getattr(model, field)).all()]})

    def create():
        data = request.get_json(silent=True) or {}
        try:
            value = clean_string(data, field, True, 100)
            if model.query.filter(func.lower(getattr(model, field)) == value.lower()).first():
                return err(f"{label} already exists", 409)
            row = model(**{field: value})
            if model is Department:
                row.description = clean_string(data, "description", False, 255)
            else:
                row.department = clean_string(data, "department", False, 100)
            db.session.add(row)
            log_activity(current_user(), f"{path}.create", value)
            db.session.commit()
            return jsonify({"message": f"{label} created", "item": row.to_dict()}), 201
        except ValidationError as e:
            db.session.rollback()
            return err(str(e))
        except IntegrityError:
            db.session.rollback()
            return err(f"{label} already exists", 409)

    def update(item_id):
        row = db.session.get(model, item_id)
        if not row:
            return err(f"{label} not found", 404)
        data = request.get_json(silent=True) or {}
        try:
            if field in data:
                value = clean_string(data, field, True, 100)
                dup = model.query.filter(func.lower(getattr(model, field)) == value.lower(), model.id != row.id).first()
                if dup:
                    return err(f"{label} already exists", 409)
                old = getattr(row, field)
                if old != value and in_use(old):
                    return err(f"{label} is used by employees; it cannot be renamed", 409)
                setattr(row, field, value)
            if model is Department and "description" in data:
                row.description = clean_string(data, "description", False, 255)
            if model is Designation and "department" in data:
                row.department = clean_string(data, "department", False, 100)
            log_activity(current_user(), f"{path}.update", getattr(row, field))
            db.session.commit()
            return jsonify({"message": f"{label} updated", "item": row.to_dict()})
        except ValidationError as e:
            db.session.rollback()
            return err(str(e))

    def delete(item_id):
        row = db.session.get(model, item_id)
        if not row:
            return err(f"{label} not found", 404)
        if in_use(getattr(row, field)):
            return err(f"{label} is assigned to employees and cannot be deleted", 409)
        log_activity(current_user(), f"{path}.delete", getattr(row, field))
        db.session.delete(row)
        db.session.commit()
        return jsonify({"message": f"{label} deleted"})

    bp.add_url_rule(f"/{path}", f"list_{path}", admin_required(listing), methods=["GET"])
    bp.add_url_rule(f"/{path}", f"create_{path}", admin_required(create), methods=["POST"])
    bp.add_url_rule(f"/{path}/<int:item_id>", f"update_{path}", admin_required(update), methods=["PUT"])
    bp.add_url_rule(f"/{path}/<int:item_id>", f"delete_{path}", admin_required(delete), methods=["DELETE"])


_lookup_routes(Department, "departments", "name", "Department",
               lambda v: Employee.query.filter_by(department=v).first() is not None)
_lookup_routes(Designation, "designations", "title", "Designation",
               lambda v: Employee.query.filter_by(designation=v).first() is not None)
