from .conftest import PW, _login


# ---------------- authentication ----------------
def test_login_success_and_no_hash_leak(client):
    r = client.post("/api/login", json={"email": "ADMIN@test.local", "password": PW})
    assert r.status_code == 200
    body = r.get_json()
    assert body["user"]["role"] == "admin" and "access_token" in body
    assert "password" not in r.get_data(as_text=True).lower().replace("must_change_password", "")


def test_login_invalid_credentials_same_message(client):
    a = client.post("/api/login", json={"email": "admin@test.local", "password": "wrong-password"})
    b = client.post("/api/login", json={"email": "nobody@test.local", "password": "wrong-password"})
    assert a.status_code == b.status_code == 401
    assert a.get_json() == b.get_json()


def test_login_validation(client):
    assert client.post("/api/login", json={}).status_code == 400
    assert client.post("/api/login", data="not json").status_code == 400
    assert client.post("/api/login", json={"email": 5, "password": ["x"]}).status_code == 400


def test_protected_endpoints_need_valid_token(client):
    assert client.get("/api/employees").status_code == 401
    assert client.get("/api/employees", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert "error" in client.get("/api/me").get_json()


def test_self_registration_disabled_by_default(client):
    r = client.post("/api/register", json={"username": "x", "email": "x@test.local", "password": PW})
    assert r.status_code == 403


def test_change_password_flow(client, make_employee):
    _, h = make_employee("Asha", "asha@test.local")
    assert client.post("/api/change-password", json={"current_password": "bad", "new_password": "NewPassw0rd!"},
                       headers=h).status_code == 400
    assert client.post("/api/change-password", json={"current_password": PW, "new_password": "short"},
                       headers=h).status_code == 400
    assert client.post("/api/change-password", json={"current_password": PW, "new_password": "NewPassw0rd!"},
                       headers=h).status_code == 200
    assert client.post("/api/login", json={"email": "asha@test.local", "password": PW}).status_code == 401
    assert client.post("/api/login", json={"email": "asha@test.local", "password": "NewPassw0rd!"}).status_code == 200


def test_admin_created_login_must_change_password(client, make_employee):
    _, h = make_employee("Asha", "asha@test.local")
    assert client.get("/api/me", headers=h).get_json()["must_change_password"] is True
    client.post("/api/change-password", json={"current_password": PW, "new_password": "NewPassw0rd!"}, headers=h)
    assert client.get("/api/me", headers=h).get_json()["must_change_password"] is False


# ---------------- role-based authorization ----------------
ADMIN_ONLY = [
    ("post", "/api/employees"), ("put", "/api/employees/1"), ("delete", "/api/employees/1"),
    ("post", "/api/employees/1/deactivate"), ("get", "/api/employees/export.csv"),
    ("post", "/api/attendance"), ("put", "/api/attendance/1"), ("delete", "/api/attendance/1"),
    ("post", "/api/salaries"), ("put", "/api/salaries/1"), ("delete", "/api/salaries/1"),
    ("put", "/api/leaves/1/review"), ("get", "/api/departments"), ("post", "/api/departments"),
    ("get", "/api/designations"), ("get", "/api/activity"), ("get", "/api/reports/summary"),
]


def test_employee_blocked_from_all_admin_endpoints(client, make_employee):
    _, h = make_employee("Asha", "asha@test.local")
    for method, url in ADMIN_ONLY:
        r = getattr(client, method)(url, json={}, headers=h)
        assert r.status_code == 403, (method, url, r.status_code)


def test_employee_cannot_read_other_employees_data(client, admin, make_employee):
    a, ha = make_employee("Asha", "asha@test.local")
    b, hb = make_employee("Bala", "bala@test.local")
    sal = client.post("/api/salaries", json={"employee_id": b["id"], "pay_month": "2026-09", "basic_salary": 1000},
                      headers=admin).get_json()["salary"]
    client.post("/api/attendance", json={"employee_id": b["id"], "attendance_date": "2026-09-01"}, headers=admin)
    # changing the ID in the URL must not expose someone else's records
    assert client.get(f"/api/employees/{b['id']}", headers=ha).status_code == 403
    assert client.get(f"/api/salaries/{sal['id']}/payslip", headers=ha).status_code == 403
    assert client.get(f"/api/employees/{a['id']}", headers=ha).status_code == 200
    # list endpoints are scoped server-side, even when a foreign employee_id filter is supplied
    assert client.get("/api/employees", headers=ha).get_json()["total"] == 1
    assert client.get(f"/api/salaries?employee_id={b['id']}", headers=ha).get_json()["items"] == []
    assert client.get(f"/api/attendance?employee_id={b['id']}", headers=ha).get_json()["items"] == []
    assert len(client.get("/api/salaries", headers=hb).get_json()["items"]) == 1
    assert client.get(f"/api/salaries/{sal['id']}/payslip", headers=hb).status_code == 200


def test_employee_profile_update_limited_to_contact_fields(client, make_employee):
    a, h = make_employee("Asha", "asha@test.local", department="Sales")
    r = client.put("/api/me/profile", json={"phone": "99999", "location": "Salem", "department": "Finance",
                                            "status": "Inactive", "email": "evil@test.local"}, headers=h)
    assert r.status_code == 200
    emp = r.get_json()["employee"]
    assert emp["phone"] == "99999" and emp["location"] == "Salem"
    assert emp["department"] == "Sales" and emp["status"] == "Active" and emp["email"] == "asha@test.local"


# ---------------- employees ----------------
def test_employee_crud_validation_and_duplicates(client, admin):
    r = client.post("/api/employees", json={"name": "A", "email": "bad", "department": "X", "designation": "Y"}, headers=admin)
    assert r.status_code == 400
    ok = {"name": "Asha", "email": "Asha@Test.local", "department": "Sales", "designation": "Rep", "joining_date": "2026-01-05"}
    r = client.post("/api/employees", json=ok, headers=admin)
    assert r.status_code == 201 and r.get_json()["employee"]["email"] == "asha@test.local"
    assert client.post("/api/employees", json=ok, headers=admin).status_code == 409
    eid = r.get_json()["employee"]["id"]
    assert client.put(f"/api/employees/{eid}", json={"status": "Bogus"}, headers=admin).status_code == 400
    assert client.put(f"/api/employees/{eid}", json={"joining_date": "05-01-2026"}, headers=admin).status_code == 400
    assert client.put(f"/api/employees/{eid}", json={"designation": "Lead"}, headers=admin).get_json()["employee"]["designation"] == "Lead"
    assert client.get("/api/employees/9999", headers=admin).status_code == 404


def test_search_filter_pagination(client, admin):
    for i in range(12):
        client.post("/api/employees", json={"name": f"Person {i:02d}", "email": f"p{i}@test.local",
                                            "department": "Sales" if i % 2 else "Finance", "designation": "X"}, headers=admin)
    d = client.get("/api/employees?per_page=5&page=3", headers=admin).get_json()
    assert d["total"] == 12 and d["pages"] == 3 and len(d["items"]) == 2
    assert client.get("/api/employees?department=Sales", headers=admin).get_json()["total"] == 6
    assert client.get("/api/employees?search=Person 07", headers=admin).get_json()["total"] == 1
    assert client.get("/api/employees?search=%25", headers=admin).get_json()["total"] == 0  # % is literal
    assert client.get("/api/employees?page=abc", headers=admin).status_code == 400


def test_deactivate_disables_login_and_reactivate(client, admin, make_employee):
    e, h = make_employee("Asha", "asha@test.local")
    assert client.post(f"/api/employees/{e['id']}/deactivate", headers=admin).status_code == 200
    assert client.get("/api/me", headers=h).status_code == 401  # existing token stops working
    r = client.post("/api/login", json={"email": "asha@test.local", "password": PW})
    assert r.status_code == 403
    client.post(f"/api/employees/{e['id']}/activate", headers=admin)
    assert client.post("/api/login", json={"email": "asha@test.local", "password": PW}).status_code == 200


def test_csv_export_neutralises_formulas(client, admin):
    client.post("/api/employees", json={"name": "=HYPERLINK(\"http://x\")", "email": "f@test.local",
                                        "department": "Sales", "designation": "X"}, headers=admin)
    r = client.get("/api/employees/export.csv", headers=admin)
    assert r.status_code == 200 and "'=HYPERLINK" in r.get_data(as_text=True)


# ---------------- attendance ----------------
def test_attendance_rules(client, admin, make_employee):
    e, h = make_employee("Asha", "asha@test.local")
    base = {"employee_id": e["id"], "attendance_date": "2026-10-01", "status": "Present",
            "check_in": "09:00", "check_out": "18:00"}
    assert client.post("/api/attendance", json=base, headers=admin).status_code == 201
    assert client.post("/api/attendance", json=base, headers=admin).status_code == 409
    assert client.post("/api/attendance", json={**base, "attendance_date": "2026-10-02", "check_out": "08:00"}, headers=admin).status_code == 400
    assert client.post("/api/attendance", json={**base, "attendance_date": "2026-10-03", "status": "Nope"}, headers=admin).status_code == 400
    assert client.post("/api/attendance", json={**base, "attendance_date": "bad"}, headers=admin).status_code == 400
    assert client.post("/api/attendance", json={"attendance_date": "2026-10-04"}, headers=admin).status_code == 400
    assert client.post("/api/attendance", json={**base, "employee_id": 9999, "attendance_date": "2026-10-05"}, headers=admin).status_code == 404
    assert len(client.get("/api/attendance", headers=h).get_json()["items"]) == 1
    # employee cannot write
    assert client.post("/api/attendance", json=base, headers=h).status_code == 403


# ---------------- salary ----------------
def test_salary_calculation_and_validation(client, admin, make_employee):
    e, h = make_employee("Asha", "asha@test.local")
    body = {"employee_id": e["id"], "pay_month": "2026-09", "basic_salary": "50000", "allowances": 2500.5,
            "bonus": 1000, "deductions": 3000.25}
    r = client.post("/api/salaries", json=body, headers=admin)
    assert r.status_code == 201
    s = r.get_json()["salary"]
    assert s["net_salary"] == 50000 + 2500.5 + 1000 - 3000.25
    assert client.post("/api/salaries", json=body, headers=admin).status_code == 409
    for bad in ({"pay_month": "2026-13"}, {"pay_month": "abcd-ef"}, {"basic_salary": -1}, {"basic_salary": "abc"},
                {"basic_salary": "1e20"}, {"payment_status": "Maybe"}, {"deductions": 100000}):
        r = client.post("/api/salaries", json={**body, "pay_month": "2026-10", **bad}, headers=admin)
        assert r.status_code == 400, (bad, r.get_json())
    p = client.get(f"/api/salaries/{s['id']}/payslip", headers=h).get_json()["payslip"]
    assert p["gross_earnings"] == 53500.5 and p["department"] == "Engineering"
    assert client.put(f"/api/salaries/{s['id']}", json={"basic_salary": 1}, headers=h).status_code == 403


# ---------------- leave ----------------
def test_leave_submit_review_cancel(client, admin, make_employee):
    e, h = make_employee("Asha", "asha@test.local")
    body = {"leave_type": "Sick", "start_date": "2026-11-02", "end_date": "2026-11-04", "reason": "Fever"}
    r = client.post("/api/leaves", json=body, headers=h)
    assert r.status_code == 201 and r.get_json()["leave"]["days"] == 3
    lid = r.get_json()["leave"]["id"]
    assert client.post("/api/leaves", json={**body, "start_date": "2026-11-04", "end_date": "2026-11-06"}, headers=h).status_code == 409
    assert client.post("/api/leaves", json={**body, "end_date": "2026-11-01"}, headers=h).status_code == 400
    assert client.post("/api/leaves", json={**body, "leave_type": "Holiday"}, headers=h).status_code == 400
    assert client.post("/api/leaves", json={**body, "reason": " "}, headers=h).status_code == 400
    # employee cannot review their own request
    assert client.put(f"/api/leaves/{lid}/review", json={"status": "Approved"}, headers=h).status_code == 403
    assert client.put(f"/api/leaves/{lid}/review", json={"status": "Maybe"}, headers=admin).status_code == 400
    r = client.put(f"/api/leaves/{lid}/review", json={"status": "Approved", "review_note": "Get well"}, headers=admin)
    assert r.status_code == 200 and r.get_json()["leave"]["status"] == "Approved"
    assert client.put(f"/api/leaves/{lid}/review", json={"status": "Rejected"}, headers=admin).status_code == 409
    assert client.post(f"/api/leaves/{lid}/cancel", headers=h).status_code == 409  # no longer pending
    assert client.get("/api/leaves?status=Approved", headers=admin).get_json()["items"][0]["employee_name"] == "Asha"


def test_leave_isolation_and_cancel(client, admin, make_employee):
    _, ha = make_employee("Asha", "asha@test.local")
    _, hb = make_employee("Bala", "bala@test.local")
    lid = client.post("/api/leaves", json={"leave_type": "Casual", "start_date": "2026-12-01", "end_date": "2026-12-01",
                                           "reason": "Personal"}, headers=ha).get_json()["leave"]["id"]
    assert client.get("/api/leaves", headers=hb).get_json()["items"] == []
    assert client.post(f"/api/leaves/{lid}/cancel", headers=hb).status_code == 403
    assert client.post(f"/api/leaves/{lid}/cancel", headers=ha).get_json()["leave"]["status"] == "Cancelled"


def test_admin_without_employee_record_cannot_request_leave(client, admin):
    r = client.post("/api/leaves", json={"leave_type": "Sick", "start_date": "2026-11-02", "end_date": "2026-11-02", "reason": "x"}, headers=admin)
    assert r.status_code == 403


# ---------------- departments, dashboard, reports ----------------
def test_departments_and_designations(client, admin, make_employee):
    r = client.post("/api/departments", json={"name": "Legal"}, headers=admin)
    assert r.status_code == 201
    assert client.post("/api/departments", json={"name": "legal"}, headers=admin).status_code == 409
    make_employee("Asha", "asha@test.local", department="Legal")
    did = r.get_json()["item"]["id"]
    assert client.delete(f"/api/departments/{did}", headers=admin).status_code == 409  # in use
    assert client.put(f"/api/departments/{did}", json={"name": "Law"}, headers=admin).status_code == 409
    d = client.post("/api/designations", json={"title": "Counsel"}, headers=admin).get_json()["item"]
    assert client.delete(f"/api/designations/{d['id']}", headers=admin).status_code == 200


def test_dashboard_reports_and_activity(client, admin, make_employee):
    e, h = make_employee("Asha", "asha@test.local")
    client.post("/api/salaries", json={"employee_id": e["id"], "pay_month": "2026-09", "basic_salary": 1000, "payment_status": "Paid"}, headers=admin)
    d = client.get("/api/dashboard", headers=admin).get_json()
    assert d["total"] == 1 and d["active"] == 1 and d["by_department"] == [{"department": "Engineering", "count": 1}]
    assert any(a["action"] == "employee.create" for a in d["recent_activity"])
    rep = client.get("/api/reports/summary?month=2026-09", headers=admin).get_json()
    assert rep["payroll"]["total_net"] == 1000 and rep["payroll"]["by_status"] == {"Paid": 1}
    assert client.get("/api/reports/summary?month=2026-9", headers=admin).status_code == 400
    ed = client.get("/api/dashboard", headers=h).get_json()
    assert ed["role"] == "employee" and ed["employee"]["email"] == "asha@test.local"


def test_unknown_route_and_method_return_json(client):
    assert client.get("/api/nope").get_json()["error"]
    assert client.delete("/api/login").status_code == 405
