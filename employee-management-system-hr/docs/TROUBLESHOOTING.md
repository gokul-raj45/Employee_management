# Troubleshooting

## Backend won't start
| Message | Cause / fix |
|---|---|
| `DATABASE_URL is not set` | `backend/.env` missing. `copy .env.example .env`, run from the `backend` folder. |
| `JWT_SECRET_KEY must be a random value of at least 32 characters` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ModuleNotFoundError: No module named 'psycopg'` | SQLAlchemy 2.1 was installed. `pip install -r requirements.txt` (it pins `SQLAlchemy<2.1`). |
| `ModuleNotFoundError: flask_migrate` / any module | venv not active, or `pip install -r requirements.txt` not run. Prompt must show `(venv)`. |
| `Port 5000 is in use` (macOS AirPlay) | Run `flask --app app run --port 5001` and set `VITE_API_BASE_URL=http://127.0.0.1:5001` + `FRONTEND_ORIGIN`. |

## PostgreSQL
| Message | Cause / fix |
|---|---|
| `password authentication failed for user "postgres"` | Wrong password / user in `DATABASE_URL`. Test with `psql -U postgres -h localhost`. URL-encode special characters (`@`→`%40`, `#`→`%23`, `/`→`%2F`). |
| `database "employee_management" does not exist` | `psql -U postgres -c "CREATE DATABASE employee_management;"` |
| `could not connect to server` / `Connection refused` | PostgreSQL service not running (Windows: *Services → postgresql-x64-XX → Start*) or wrong port (default 5432). |
| `relation "users" does not exist` | Migrations not applied: `flask --app app db upgrade`. |
| `relation "users" already exists` during `db upgrade` | Database was made by the old `create_all()`. Back up, then `flask --app app db stamp 0001_baseline` and `db upgrade` (README §5). **Do not drop the database.** |
| `column users.is_active does not exist` | Same as above – `db upgrade` not run on the old database. |
| `Target database is not up to date` (`db migrate`) | Run `db upgrade` first. |
| `Can't locate revision` | You are in the wrong folder; run from `backend/`. |

## Login problems
| Symptom | Cause / fix |
|---|---|
| **401 "Invalid email or password"** | Wrong credentials. Emails are case-insensitive. To reset an admin you can't use: create a second one with `flask create-admin --username other --email other@x.com`, sign in, and change passwords from *Profile*. |
| **403 "account has been deactivated"** | Employee is *Inactive*. Admin → Employee details → Reactivate. |
| **403 "Self-registration is disabled"** | Intended. Admin creates logins (Add employee → Initial password). Re-enable only with `ALLOW_SELF_REGISTRATION=true`. |
| Signed in but "not linked to an employee record" | The login has no employee row. Admin must create the employee with the *same* email and (when creating) leave password blank to link an existing login. |
| Kicked back to login after a while | Token expired (`JWT_EXPIRES_HOURS`, default 8) – expected. |
| Everyone logged out after restart | `JWT_SECRET_KEY` changed. |
| 500 on login | Look at the backend terminal for the traceback (responses never include details). Usually a DB problem – check `/api/health`. |

## JWT
- `401 {"error":"Authentication required"}` – no `Authorization: Bearer <token>` header.
- `401 {"error":"Invalid token"}` – token altered, or signed with a different `JWT_SECRET_KEY`.
- `401 {"error":"Session expired…"}` – expired; sign in again.
- `401 {"error":"Account not found or disabled"}` – user deleted/deactivated since the token was issued.
- `403 {"error":"Administrator access required"}` – employee token used on an admin endpoint.

## CORS (browser console: "blocked by CORS policy" / UI says "Cannot reach the server")
1. Open the UI at the **same host** listed in `FRONTEND_ORIGIN`. `http://localhost:5173` and `http://127.0.0.1:5173` are different origins; both are allowed by default. If you use another host/port, add it (comma separated) and **restart Flask**.
2. `VITE_API_BASE_URL` must point to the running backend; restart `npm run dev` after editing `.env`.
3. A *network error* with no CORS message usually means the backend isn't running – check `http://127.0.0.1:5000/api/health`.
4. Never "fix" CORS with `*`; add the exact origin.

## Frontend
| Symptom | Fix |
|---|---|
| `npm install` errors | Node ≥ 18; delete `node_modules` + `package-lock.json` only inside `frontend/`, reinstall. |
| Blank page | Open DevTools console; usually `VITE_API_BASE_URL` typo or a stale tab after changing `.env` (restart Vite). |
| Page unstyled | Hard refresh; confirm `src/main.jsx` imports `./App.css`. |
| Changes to `.env` ignored | Vite reads `.env` only at start – restart `npm run dev`. |

## Quick health checklist
1. `http://127.0.0.1:5000/api/health` → `ok / connected`
2. `flask --app app db current` → `0002_features (head)`
3. `flask --app app db check` → `No new upgrade operations detected`
4. UI opens at `http://localhost:5173`, no red errors in the console.
