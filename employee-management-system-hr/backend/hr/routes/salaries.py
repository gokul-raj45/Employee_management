from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import SalaryRecord, Employee
from ..utils import (err, admin_required, signed_in, current_user, employee_for_user, clean_string, parse_int,
                     parse_date, parse_money, log_activity, MONTH_RE, ValidationError)

bp = Blueprint("salaries", __name__, url_prefix="/api")
PAYMENT_STATUSES = ("Pending", "Paid", "On Hold")


def _month(value):
    if not isinstance(value, str) or not MONTH_RE.match(value):
        raise ValidationError("Pay month must use YYYY-MM")
    return value


def _status(value):
    if value not in PAYMENT_STATUSES:
        raise ValidationError("Invalid payment status")
    return value


def _check_net(s):
    if s.basic_salary + s.allowances + s.bonus - s.deductions < 0:
        raise ValidationError("Deductions cannot exceed total earnings")


@bp.get("/salaries")
@signed_in
def list_salaries():
    user = current_user()
    q = SalaryRecord.query.join(Employee)
    if user.role != "admin":
        emp = employee_for_user(user)
        q = q.filter(SalaryRecord.employee_id == (emp.id if emp else -1))
    month = request.args.get("month", "").strip()
    if month:
        q = q.filter(SalaryRecord.pay_month == month)
    if request.args.get("employee_id") and user.role == "admin":
        try:
            q = q.filter(SalaryRecord.employee_id == parse_int(request.args["employee_id"], "employee_id"))
        except ValidationError as e:
            return err(str(e))
    q = q.order_by(SalaryRecord.pay_month.desc(), SalaryRecord.id.desc())
    return jsonify({"items": [s.to_dict() for s in q.limit(500).all()]})


@bp.get("/salaries/<int:salary_id>/payslip")
@signed_in
def payslip(salary_id):
    user = current_user()
    s = db.session.get(SalaryRecord, salary_id)
    if not s:
        return err("Salary record not found", 404)
    if user.role != "admin":
        own = employee_for_user(user)
        if not own or own.id != s.employee_id:
            return err("You can only view your own payslips", 403)
    emp = s.employee
    d = s.to_dict()
    return jsonify({"payslip": {**d, "department": emp.department, "designation": emp.designation,
                                "gross_earnings": d["basic_salary"] + d["allowances"] + d["bonus"]}})


@bp.post("/salaries")
@admin_required
def create_salary():
    data = request.get_json(silent=True) or {}
    try:
        employee_id = parse_int(data.get("employee_id"), "Employee")
        month = _month(data.get("pay_month", ""))
        if not db.session.get(Employee, employee_id):
            return err("Employee not found", 404)
        if SalaryRecord.query.filter_by(employee_id=employee_id, pay_month=month).first():
            return err("Salary record already exists for this employee and month", 409)
        s = SalaryRecord(employee_id=employee_id, pay_month=month,
                         basic_salary=parse_money(data, "basic_salary"), allowances=parse_money(data, "allowances"),
                         deductions=parse_money(data, "deductions"), bonus=parse_money(data, "bonus"),
                         payment_status=_status(data.get("payment_status", "Pending")),
                         paid_on=parse_date(data.get("paid_on"), "Paid date"),
                         notes=clean_string(data, "notes", False, 500))
        _check_net(s)
        db.session.add(s)
        log_activity(current_user(), "salary.create", f"employee {employee_id} {month}")
        db.session.commit()
        return jsonify({"message": "Salary record created", "salary": s.to_dict()}), 201
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))
    except IntegrityError:
        db.session.rollback()
        return err("Salary record already exists for this employee and month", 409)


@bp.put("/salaries/<int:salary_id>")
@admin_required
def update_salary(salary_id):
    s = db.session.get(SalaryRecord, salary_id)
    if not s:
        return err("Salary record not found", 404)
    data = request.get_json(silent=True) or {}
    try:
        if "employee_id" in data:
            emp_id = parse_int(data["employee_id"], "Employee")
            if not db.session.get(Employee, emp_id):
                return err("Employee not found", 404)
            s.employee_id = emp_id
        if "pay_month" in data:
            s.pay_month = _month(data["pay_month"])
        for field in ("basic_salary", "allowances", "deductions", "bonus"):
            if field in data:
                setattr(s, field, parse_money(data, field))
        if "payment_status" in data:
            s.payment_status = _status(data["payment_status"])
        if "paid_on" in data:
            s.paid_on = parse_date(data["paid_on"], "Paid date")
        if "notes" in data:
            s.notes = clean_string(data, "notes", False, 500)
        _check_net(s)
        log_activity(current_user(), "salary.update", f"record {s.id}")
        db.session.commit()
        return jsonify({"message": "Salary record updated", "salary": s.to_dict()})
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))
    except IntegrityError:
        db.session.rollback()
        return err("Salary record already exists for this employee and month", 409)


@bp.delete("/salaries/<int:salary_id>")
@admin_required
def delete_salary(salary_id):
    s = db.session.get(SalaryRecord, salary_id)
    if not s:
        return err("Salary record not found", 404)
    log_activity(current_user(), "salary.delete", f"record {s.id}")
    db.session.delete(s)
    db.session.commit()
    return jsonify({"message": "Salary record deleted"})
