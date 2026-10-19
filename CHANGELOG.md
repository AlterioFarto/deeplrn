# DEEPLRN 1.0.0 — 2026-10-20

Initial release of the educational institute management system.

## Highlights

- **Three-role access model** (ADMIN / MENTOR / GUARDIAN) with a single,
  fail-closed authorization boundary (`common/scoping.py`) used by every
  selector and service.
- **Students & guardians**: enrollment with group capacity limits, unique
  admission numbers among live records, guardian linking with per-student
  primary contact, soft delete/restore with full history retention.
- **Academics**: groups, subjects, timeslots, weekly schedules and exams with
  uniqueness constraints (group-slot, mentor-slot) and validated exam config.
- **Attendance**: idempotent bulk recording (re-running a slot overwrites),
  whole-day/slot dedup via DB constraints, configurable late-marks policy,
  attendance risk threshold surfaced on dashboards.
- **Results**: grade bands (A+ to F), bulk upsert, exam-foreign student
  rejection, recompute management command.
- **Billing**: monthly invoice generation task (idempotent per student/period),
  issue/void state machine (void blocked when payments exist), payments that
  never exceed outstanding balance, soft-deleted payments restored in totals.
- **Dashboards**: role-specific stats with request-scoped caching that is
  invalidated version-wide on any domain write; weekly attendance digest
  reports generated into `REPORTS_ROOT` with path-traversal-safe downloads.
- **Security**: CSP with per-response nonce, permissions policy, X-Frame DENY,
  login throttling with lockout, password validation, hardened session/
  CSRF cookie settings (secure in prod), append-only audit log of every
  mutation (actor, action, diff, request id), CSV export formula-injection
  defenses, request IDs on every log line.
- **Operational**: Dockerfile + docker-compose (Postgres/Redis/web/worker/
  beat), GitHub Actions CI (ruff, mypy, pytest against PostgreSQL, system
  checks, image build), pre-commit hooks, `.env`-driven configuration via
  django-environ (`DEEPLRN_*` prefix), Sentry integration (optional), JSON
  logging in production.
- **Quality gates in this release**: pytest (51 tests), ruff, black, mypy
  (django-stubs, zero errors) and an end-to-end smoke script exercising
  all three roles incl. expected 403s all pass.
