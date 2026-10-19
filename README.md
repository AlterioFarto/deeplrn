# DEEPLRN — educational institute management system

DEEPLRN manages an educational institute end to end: students and their
guardians, groups and timetables, attendance, exam results and monthly
invoicing — with three clearly separated roles and an audit trail on every
mutation.

## Roles

| Role | What they can do |
| --- | --- |
| **ADMIN** | Everything: users, guardians, students, groups, schedules, exams, billing, reports |
| **MENTOR** | Manages the groups they are assigned to; records attendance and results |
| **GUARDIAN** | Read-only dashboards for their linked students: attendance, results, invoices |

Authorization is centralised in `common/scoping.py`: every selector works on a
boundary-scoped queryset and fails **closed** for anything it cannot model.

## Quickstart (local development)

```console
$ uv sync --all-groups
$ cp .env.example .env          # adjust if you like; defaults work for SQLite
$ .venv\Scripts\python manage.py migrate
$ .venv\Scripts\python manage.py seed_demo     # requires DEEPLRN_SEED_DEMO=1 and DEBUG
$ .venv\Scripts\python manage.py runserver
```

`seed_demo` prints one-time random passwords for its demo accounts
(admin / mentors / guardians). It refuses to run unless `DEEPLRN_SEED_DEMO=1`
**and** `DEBUG=true` are set.

## Tests & static analysis

```console
$ .venv\Scripts\python -m pytest -q
$ .venv\Scripts\python -m ruff check .
$ .venv\Scripts\python -m ruff format --check .
$ .venv\Scripts\python -m black --check .
$ .venv\Scripts\python -m mypy .
```

## Architecture

```
config/          settings (base/dev/prod/test), URL conf, Celery, WSGI/ASGI
common/          audit log, authorization scoping, soft delete, CSV, pagination,
                 view mixins, template tags, seed_demo & logging middleware
accounts/        custom user, roles, login security (throttle/lockout), profiles
academics/       groups, subjects, timeslots, schedules, exams
students/        students, guardian links, enrollments (soft delete + restore)
attendance/      policies, timeslot attendance, bulk recording, selectors
results/         results + grade computation
billing/         invoices, payments, monthly generation task
dashboard/       role stats (versioned cache), attendance digest reports
templates/ static/  handcrafted UI (no external CSS/JS frameworks)
```

Layers: **views** (thin, mixins-driven) → **selectors** (reads; always
boundary-scoped) → **services** (writes; transactional, audited, raise
`ConflictError`/`AuthorizationError` instead of leaking model errors).

## Configuration

Everything is environment-driven with the `DEEPLRN_*` prefix — see
`.env.example` for the full catalogue. Production (`config.settings.prod`)
**fails fast** if `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`,
`DATABASE_URL` or `REDIS_URL` are missing.

## Running with Docker

```console
$ docker compose up --build
```

This starts Postgres, Redis, the gunicorn web tier and the Celery worker +
beat processes. The web tier applies migrations on boot and serves static
files through WhiteNoise.

## Operations notes

- **Celery beat schedule**: monthly invoices on the 1st (00:30) and the weekly
  attendance digest every Monday (06:00).
- **Reports** are written to `DEEPLRN_REPORTS_ROOT` (outside the web root) and
  downloaded only by ADMIN with a validated path.
- **Audit log**: every service mutation writes an append-only entry with
  actor, action and a JSON diff.
