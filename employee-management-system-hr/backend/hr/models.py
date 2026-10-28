"""Database models."""
from decimal import Decimal
from sqlalchemy import func
from .extensions import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    must_change_password = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)

    def to_dict(self):
        """Public representation. Never includes password_hash."""
        return {"id": self.id, "username": self.username, "email": self.email, "role": self.role,
                "must_change_password": self.must_change_password}


class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    employee_code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    department = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100), nullable=False)
    employment_type = db.Column(db.String(30), nullable=False, default="Full-time")
    status = db.Column(db.String(20), nullable=False, default="Active")
    joining_date = db.Column(db.Date)
    location = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id, "employee_code": self.employee_code,
            "name": self.name, "email": self.email, "phone": self.phone,
            "department": self.department, "designation": self.designation,
            "employment_type": self.employment_type, "status": self.status,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
            "location": self.location, "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="Present")
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    employee = db.relationship("Employee", backref=db.backref("attendance_records", lazy=True, cascade="all, delete-orphan"))
    __table_args__ = (db.UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),)

    def to_dict(self):
        return {
            "id": self.id, "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else "",
            "employee_code": self.employee.employee_code if self.employee else "",
            "attendance_date": self.attendance_date.isoformat(),
            "status": self.status,
            "check_in": self.check_in.strftime("%H:%M") if self.check_in else "",
            "check_out": self.check_out.strftime("%H:%M") if self.check_out else "",
            "notes": self.notes or ""
        }


class SalaryRecord(db.Model):
    __tablename__ = "salary_records"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    pay_month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    basic_salary = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    allowances = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    deductions = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    bonus = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    payment_status = db.Column(db.String(20), nullable=False, default="Pending")
    paid_on = db.Column(db.Date)
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    employee = db.relationship("Employee", backref=db.backref("salary_records", lazy=True, cascade="all, delete-orphan"))
    __table_args__ = (db.UniqueConstraint("employee_id", "pay_month", name="uq_salary_employee_month"),)

    def to_dict(self):
        basic = Decimal(self.basic_salary or 0)
        allowances = Decimal(self.allowances or 0)
        deductions = Decimal(self.deductions or 0)
        bonus = Decimal(self.bonus or 0)
        return {
            "id": self.id, "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else "",
            "employee_code": self.employee.employee_code if self.employee else "",
            "pay_month": self.pay_month, "basic_salary": float(basic),
            "allowances": float(allowances), "deductions": float(deductions),
            "bonus": float(bonus), "net_salary": float(basic + allowances + bonus - deductions),
            "payment_status": self.payment_status,
            "paid_on": self.paid_on.isoformat() if self.paid_on else None,
            "notes": self.notes or ""
        }



class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description or ""}


class Designation(db.Model):
    __tablename__ = "designations"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100))  # optional hint, matches Department.name
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "department": self.department or ""}


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type = db.Column(db.String(30), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending", server_default="Pending", index=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = db.Column(db.DateTime)
    review_note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    employee = db.relationship("Employee", backref=db.backref("leave_requests", lazy=True, cascade="all, delete-orphan"))

    def to_dict(self):
        return {"id": self.id, "employee_id": self.employee_id,
                "employee_name": self.employee.name if self.employee else "",
                "employee_code": self.employee.employee_code if self.employee else "",
                "leave_type": self.leave_type, "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "days": (self.end_date - self.start_date).days + 1,
                "reason": self.reason, "status": self.status, "review_note": self.review_note or "",
                "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class ActivityLog(db.Model):
    """Audit trail of administrative actions (never stores passwords or secrets)."""
    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    actor = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False, index=True)

    def to_dict(self):
        return {"id": self.id, "actor": self.actor, "action": self.action, "detail": self.detail or "",
                "created_at": self.created_at.isoformat() if self.created_at else None}
