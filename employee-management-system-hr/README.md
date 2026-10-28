# PeopleDesk HR — Employee Management, Attendance, Leave & Payroll

React (Vite) · Flask · PostgreSQL · SQLAlchemy · Flask-Migrate · JWT · bcrypt

```
employee-management-system-hr/
├── backend/            Flask API  (app.py = entry point, hr/ = package, migrations/, tests/)
├── frontend/           React + Vite app (React Router, Axios)
└── docs/               API.md, TROUBLESHOOTING.md, postman/
```

## Features
**Admin** – dashboard with live statistics and recent activity · create / search / update / **deactivate** employees (and create their login) · departments & designations · attendance · approve / reject leave · salary records & payslips · monthly report · activity log · CSV export.
**Employee** – sees *only their own* profile, attendance, leave, salary and payslips · edits phone/location · requests / cancels leave · changes password.
**Security** – roles are enforced in Flask (not just React) · bcrypt hashes never leave the server · JWT with expiry · explicit CORS allow-list · input validation on every write · public self-registration **off** by default · login disabled automatically when an employee is deactivated · audit trail of admin actions · CSV-formula-injection protection.

---
## 1. Prerequisites
Python 3.10+, Node.js 18+ (20+ recommended), PostgreSQL 14+, VS Code.

## 2. Create the database (one time)
```powershell
psql -U postgres -c "CREATE DATABASE employee_management;"
```
(Use the PostgreSQL username you chose at install. Do **not** drop an existing database — see §5 if you already have data.)

## 3. Backend (Terminal 1 in VS Code)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1          # macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env               # macOS/Linux:  cp .env.example .env
```
Edit `backend/.env`:
1. `DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/employee_management`
   (URL-encode special characters in the password, e.g. `@` → `%40`.)
2. **JWT secret** – generate one and paste it as `JWT_SECRET_KEY=`:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
   The app refuses to start if the secret is missing, shorter than 32 characters, or still the placeholder. Never commit `.env`; changing the secret logs everyone out.

Create the tables and the first administrator:
```powershell
flask --app app db upgrade                                   # creates / updates all tables
flask --app app create-admin --email admin@yourcompany.com   # prompts for the password (hidden, never stored in files)
python app.py                                                # API on http://127.0.0.1:5000
```
Check: open http://127.0.0.1:5000/api/health → `{"database":"connected","status":"ok"}`.

## 4. Frontend (Terminal 2)
```powershell
cd frontend
copy .env.example .env               # VITE_API_BASE_URL=http://127.0.0.1:5000
npm install
npm run dev                          # http://localhost:5173
```
Sign in with the admin you created. **Add employee → fill "Initial password"** to give an employee a login; they must change it at first sign-in.

## 5. Already have data from the earlier version? (safe upgrade, no drops)
Your database was created by `db.create_all()`. Adopt it into migrations **without touching data**:
```powershell
# 0. BACK UP FIRST:
pg_dump -U postgres -Fc employee_management > backup_before_upgrade.dump
flask --app app db stamp 0001_baseline     # tells Alembic "the 4 original tables already exist"
flask --app app db upgrade                 # adds only: users.is_active, users.must_change_password,
                                           #   departments, designations, leave_requests, activity_logs
```
The upgrade only *adds* columns/tables (with safe defaults), seeds departments/designations from your existing employee values, and links any login whose email matches an employee. Existing users, hashes, attendance and salary rows are untouched. Existing admin accounts keep working.

**Behaviour changes from the earlier version** – please read:
| Before | Now | Why |
|---|---|---|
| `python app.py` created tables and an admin from `ADMIN_PASSWORD` in `.env` | `flask db upgrade` + `flask create-admin` (password prompted) | Migrations are safe for existing data; no password stored in a file |
| Anyone could self-register; a login claimed an employee record by matching email | Registration disabled (`ALLOW_SELF_REGISTRATION=false`); admins create logins; records are linked explicitly | An unverified email must not unlock someone's salary data |
| `VITE_API_URL` | `VITE_API_BASE_URL` | Naming as requested |
| `frontend/` inside `backend/` | `frontend/` at the top level | Clearer layout |
| `FRONTEND_ORIGIN` single origin | comma-separated list | `localhost` vs `127.0.0.1` both work |

## 6. Tests
```powershell
cd backend
pytest -q                                    # 22 API tests (in-memory SQLite by default)
# against real PostgreSQL — the DB name MUST contain "test" (the suite drops/creates its tables):
psql -U postgres -c "CREATE DATABASE employee_test;"
$env:TEST_DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/employee_test"; pytest -q

cd ../frontend
npm test                                     # route-guard / helper unit tests; the live E2E test is skipped
```
Optional **live end-to-end test** (real React UI → real API → PostgreSQL): start the backend on a throw-away database, create an admin, then
```powershell
$env:VITE_E2E="true"; $env:VITE_API_BASE_URL="http://127.0.0.1:5000"
$env:VITE_E2E_ADMIN_EMAIL="admin@example.com"; $env:VITE_E2E_ADMIN_PASSWORD="<that admin's password>"
npm test
```
It creates real records – never point it at production data.

## 7. Production notes
`FLASK_DEBUG=false`; run behind gunicorn/waitress + HTTPS; set `FRONTEND_ORIGIN` to your real site only; build the UI with `npm run build` and serve `frontend/dist`; add login rate-limiting (e.g. Flask-Limiter) and regular `pg_dump` backups. See `docs/TROUBLESHOOTING.md` and `docs/API.md`.
