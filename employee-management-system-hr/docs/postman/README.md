# Postman testing

1. Postman → **Import** → `PeopleDesk.postman_collection.json`.
2. Open the collection → **Variables**: set `adminEmail` and `adminPassword` (current value only – don't sync secrets), keep `baseUrl`.
3. Run **POST /api/login** first. Its test script stores the JWT in `{{token}}`; every other request sends it automatically (collection-level Bearer auth).
4. Set `{{id}}` to the record id before calling `/{id}` endpoints.

## Suggested checks
| Request | Expected |
|---|---|
| POST /api/login with wrong password | 401 `Invalid email or password` |
| GET /api/employees with the Authorization header removed | 401 |
| POST /api/employees (admin) with `initial_password` | 201 |
| Log in as that employee (change `adminEmail`/`adminPassword`) then POST /api/employees | **403** |
| …as the employee, GET /api/employees/{another employee's id} | **403** |
| …as the employee, GET /api/salaries | only their own rows |
| …as the employee, PUT /api/leaves/{id}/review | **403** |
| POST /api/attendance twice for same employee+date | 201 then 409 |
| POST /api/salaries with `pay_month` `2026-13` | 400 |
