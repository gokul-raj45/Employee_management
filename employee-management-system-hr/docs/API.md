# API reference

Base URL `http://127.0.0.1:5000`. JSON in / JSON out. Protected endpoints need `Authorization: Bearer <access_token>`.

**Errors** are always `{"error": "message"}`: `400` validation · `401` missing/invalid/expired token or disabled account · `403` role/ownership · `404` not found · `409` duplicate / state conflict · `500` server error (details only in the server log).

Responses never contain password hashes.

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/api/health` | public | DB connectivity check |
| GET | `/api/auth/config` | public | Tells the UI whether self-registration is enabled |
| POST | `/api/login` | public | Returns `access_token` + `user` |
| POST | `/api/register` | public (disabled by default) | Creates an *unlinked* employee login. 403 unless `ALLOW_SELF_REGISTRATION=true` |
| GET | `/api/me` | any user | Current user + linked employee (or null) |
| PUT | `/api/me/profile` | employee | Edit only `phone`, `location` of own record |
| POST | `/api/change-password` | any user | Needs `current_password`; new password 8–72 chars |
| GET | `/api/dashboard` | any user | Admin: totals, attendance today, pending leave, recent activity. Employee: own counts + profile |
| GET | `/api/employees` | any user | Query: `search, department, status, sort, direction, page, per_page(≤100)`. Employees only ever receive their own record |
| POST | `/api/employees` | admin | Required: `name,email,department,designation`. Optional `initial_password` creates a login (forced change at first sign-in) |
| GET | `/api/employees/{id}` | admin or owner | 403 for another employee's id |
| PUT | `/api/employees/{id}` | admin | Partial update |
| POST | `/api/employees/{id}/deactivate` | admin | Status → Inactive and disables the login (history kept) |
| POST | `/api/employees/{id}/activate` | admin | Status → Active and re-enables the login |
| DELETE | `/api/employees/{id}` | admin | Permanent; also removes the employee's attendance, salary and leave rows |
| GET | `/api/employees/export.csv` | admin | CSV download (formula-injection safe) |
| GET | `/api/attendance` | any user | Query: `from,to` (YYYY-MM-DD), `employee_id` (admin only). Employees: own rows only |
| POST | `/api/attendance` | admin | One record per employee per date (409 on duplicate); `check_out` must be after `check_in`; status ∈ Present, Absent, Late, Half-day, Leave |
| PUT | `/api/attendance/{id}` | admin | Partial update |
| DELETE | `/api/attendance/{id}` | admin |  |
| GET | `/api/salaries` | any user | Query: `month` (YYYY-MM), `employee_id` (admin only). Employees: own rows only. `net_salary` = basic + allowances + bonus − deductions (server-computed) |
| GET | `/api/salaries/{id}/payslip` | admin or owner | Payslip breakdown; 403 for another employee's record |
| POST | `/api/salaries` | admin | One record per employee per `pay_month`; amounts 0 – 9,999,999,999.99; deductions may not exceed earnings; `payment_status` ∈ Pending, Paid, On Hold |
| PUT | `/api/salaries/{id}` | admin | Partial update |
| DELETE | `/api/salaries/{id}` | admin |  |
| GET | `/api/leaves` | any user | Query: `status`, `employee_id` (admin). Employees: own rows only |
| POST | `/api/leaves` | employee | `leave_type` ∈ Annual, Sick, Casual, Unpaid, Other; `end_date ≥ start_date`; overlapping pending/approved requests rejected (409) |
| POST | `/api/leaves/{id}/cancel` | owner | Only while Pending |
| PUT | `/api/leaves/{id}/review` | admin | `status` ∈ Approved, Rejected; only Pending requests (409 otherwise) |
| GET | `/api/departments` | admin |  |
| POST | `/api/departments` | admin | Case-insensitive unique |
| PUT | `/api/departments/{id}` | admin | Cannot rename while employees use it |
| DELETE | `/api/departments/{id}` | admin | 409 while assigned to employees |
| GET | `/api/designations` | admin |  |
| POST | `/api/designations` | admin |  |
| PUT | `/api/designations/{id}` | admin |  |
| DELETE | `/api/designations/{id}` | admin | 409 while assigned to employees |
| GET | `/api/reports/summary` | admin | Query: `month` (YYYY-MM). Attendance / leave / payroll totals |
| GET | `/api/activity` | admin | Query: `limit` ≤ 100. Audit trail of admin actions |

## Example bodies

**POST /api/login**
```json
{
  "email": "{{adminEmail}}",
  "password": "{{adminPassword}}"
}
```

**POST /api/register**
```json
{
  "username": "new.user",
  "email": "new.user@example.com",
  "password": "ChangeMe#12345"
}
```

**PUT /api/me/profile**
```json
{
  "phone": "+91 90000 00000",
  "location": "Salem"
}
```

**POST /api/change-password**
```json
{
  "current_password": "old",
  "new_password": "NewPassw0rd!2026"
}
```

**POST /api/employees**
```json
{
  "name": "Asha Kumar",
  "email": "asha@example.com",
  "department": "Engineering",
  "designation": "Developer",
  "employment_type": "Full-time",
  "status": "Active",
  "joining_date": "2026-10-01",
  "initial_password": "TempPass#12345"
}
```

**PUT /api/employees/{id}**
```json
{
  "designation": "Senior Developer"
}
```

**POST /api/attendance**
```json
{
  "employee_id": 1,
  "attendance_date": "2026-10-01",
  "status": "Present",
  "check_in": "09:00",
  "check_out": "18:00",
  "notes": ""
}
```

**PUT /api/attendance/{id}**
```json
{
  "status": "Late",
  "check_in": "09:45"
}
```

**POST /api/salaries**
```json
{
  "employee_id": 1,
  "pay_month": "2026-09",
  "basic_salary": 50000,
  "allowances": 5000,
  "bonus": 0,
  "deductions": 2500,
  "payment_status": "Pending"
}
```

**PUT /api/salaries/{id}**
```json
{
  "payment_status": "Paid",
  "paid_on": "2026-10-01"
}
```

**POST /api/leaves**
```json
{
  "leave_type": "Sick",
  "start_date": "2026-11-02",
  "end_date": "2026-11-03",
  "reason": "Fever"
}
```

**PUT /api/leaves/{id}/review**
```json
{
  "status": "Approved",
  "review_note": "Get well soon"
}
```

**POST /api/departments**
```json
{
  "name": "Legal",
  "description": ""
}
```

**PUT /api/departments/{id}**
```json
{
  "description": "Legal & compliance"
}
```

**POST /api/designations**
```json
{
  "title": "Counsel",
  "department": "Legal"
}
```

**PUT /api/designations/{id}**
```json
{
  "department": "Legal"
}
```
