from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from ..extensions import db
from ..models import LeaveRequest, Employee
from ..utils import (err, admin_required, signed_in, current_user, employee_for_user, clean_string, parse_int,
                     parse_date, log_activity, ValidationError)

bp = Blueprint("leaves", __name__, url_prefix="/api")
LEAVE_TYPES = ("Annual", "Sick", "Casual", "Unpaid", "Other")
MAX_DAYS = 365


@bp.get("/leaves")
@signed_in
def list_leaves():
    user = current_user()
    q = LeaveRequest.query.join(Employee)
    if user.role != "admin":
        emp = employee_for_user(user)
        q = q.filter(LeaveRequest.employee_id == (emp.id if emp else -1))
    elif request.args.get("employee_id"):
        try:
            q = q.filter(LeaveRequest.employee_id == parse_int(request.args["employee_id"], "employee_id"))
        except ValidationError as e:
            return err(str(e))
    status = request.args.get("status", "").strip()
    if status:
        q = q.filter(LeaveRequest.status == status)
    q = q.order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
    return jsonify({"items": [l.to_dict() for l in q.limit(500).all()]})


@bp.post("/leaves")
@signed_in
def create_leave():
    user = current_user()
    emp = employee_for_user(user)
    if not emp:
        return err("No employee record is linked to your account", 403)
    if emp.status == "Inactive":
        return err("Inactive employees cannot request leave", 403)
    data = request.get_json(silent=True) or {}
    try:
        leave_type = data.get("leave_type")
        if leave_type not in LEAVE_TYPES:
            return err(f"Leave type must be one of: {', '.join(LEAVE_TYPES)}")
        start = parse_date(data.get("start_date"), "Start date", required=True)
        end = parse_date(data.get("end_date"), "End date", required=True)
        if end < start:
            return err("End date cannot be before start date")
        if (end - start).days + 1 > MAX_DAYS:
            return err(f"A leave request cannot exceed {MAX_DAYS} days")
        reason = clean_string(data, "reason", True, 1000)
        overlap = LeaveRequest.query.filter(
            LeaveRequest.employee_id == emp.id, LeaveRequest.status.in_(("Pending", "Approved")),
            LeaveRequest.start_date <= end, LeaveRequest.end_date >= start).first()
        if overlap:
            return err("You already have a pending or approved leave overlapping these dates", 409)
        leave = LeaveRequest(employee_id=emp.id, leave_type=leave_type, start_date=start, end_date=end, reason=reason)
        db.session.add(leave)
        db.session.commit()
        return jsonify({"message": "Leave request submitted", "leave": leave.to_dict()}), 201
    except ValidationError as e:
        db.session.rollback()
        return err(str(e))


@bp.post("/leaves/<int:leave_id>/cancel")
@signed_in
def cancel_leave(leave_id):
    user = current_user()
    leave = db.session.get(LeaveRequest, leave_id)
    if not leave:
        return err("Leave request not found", 404)
    own = employee_for_user(user)
    if not own or own.id != leave.employee_id:
        return err("You can only cancel your own leave requests", 403)
    if leave.status != "Pending":
        return err("Only pending requests can be cancelled", 409)
    leave.status = "Cancelled"
    db.session.commit()
    return jsonify({"message": "Leave request cancelled", "leave": leave.to_dict()})


@bp.put("/leaves/<int:leave_id>/review")
@admin_required
def review_leave(leave_id):
    leave = db.session.get(LeaveRequest, leave_id)
    if not leave:
        return err("Leave request not found", 404)
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("Approved", "Rejected"):
        return err("Status must be Approved or Rejected")
    if leave.status != "Pending":
        return err(f"This request is already {leave.status.lower()}", 409)
    try:
        leave.review_note = clean_string(data, "review_note", False, 500)
    except ValidationError as e:
        return err(str(e))
    admin = current_user()
    leave.status = status
    leave.reviewed_by = admin.id
    leave.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    log_activity(admin, f"leave.{status.lower()}", f"{leave.employee.employee_code} {leave.start_date}..{leave.end_date}")
    db.session.commit()
    return jsonify({"message": f"Leave request {status.lower()}", "leave": leave.to_dict()})
