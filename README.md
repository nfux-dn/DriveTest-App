# DriveTest — Network Test Orchestration Platform

A web platform for orchestrating and evaluating network equipment validation tests.
This repository implements the MVP described in [`DriveTest_SPEC.md`](DriveTest_SPEC.md),
built as a modular monolith: a FastAPI + PostgreSQL backend and a React + TypeScript
(dark themed) frontend.

This snapshot delivers milestones 1-5 (spec phases 1-5): skeleton, suite/environment
model, dynamic prerequisites, per-user GitHub connection, and the sequential test runner.
AI review and the final-verdict engine (phases 6-10) come next.

## Architecture at a glance

```
frontend (React/Vite)  ->  backend (FastAPI)  ->  PostgreSQL
                                  |
                                  +-- runner (subprocess per test, isolated workspace)
                                  +-- git (per-user GitHub, encrypted tokens)
```

- Backend modules live under `backend/app/` (one folder per domain: `auth`, `suites`,
  `environments`, `prerequisites`, `git`, `runs`, `runner`, `results`, `secrets`, `core`, `db`).
- Suite/environment/prerequisite definitions live under `definitions/` (the dev "definitions
  source"). A demo shaping suite with four tests is included.
- The frontend lives under `frontend/`.

## Prerequisites

- Docker + Docker Compose. Nothing else needs to be installed on the host
  (Python 3.12 and Node run inside containers).

## First-time setup

1. Create your env file and generate a secret encryption key:

```bash
cd DriveTest
cp .env.example .env
docker compose run --rm --entrypoint sh backend -c "python -m app.cli genkey"
```

Put the printed value into `.env` as `DRIVETEST_SECRET_ENCRYPTION_KEY` (required only
to connect GitHub; the rest of the app runs without it).

2. Start everything:

```bash
docker compose up --build
```

On startup the backend waits for the database, applies Alembic migrations, and seeds
the demo definitions. Then open:

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Manual verification (demo flow)

1. Sign in with any email (dev login).
2. Go to New Run -> pick "Demo Shaping Suite". Only compatible environments appear
   (Lab 23 shows; Lab Optics is filtered out).
3. Select Lab 23. Fill the dynamic prerequisite form. Choosing traffic generator
   "ixia" reveals the Ixia Chassis IP field (conditional logic). Click "Validate &
   Continue" — validation runs on the backend.
4. Git Revision: leave "Use built-in demo definitions" (or connect GitHub first from
   the Git Connection page to run from a real repo).
5. Review & Run. Watch the tests execute sequentially. You will see:
   - `basic_pass` -> COMPLETED, test verdict PASSED
   - `ai_anomaly` -> COMPLETED, test verdict PASSED
   - `ai_judged` -> COMPLETED, test verdict null (AI-judged)
   - `script_error` -> SCRIPT_ERROR (execution failure, kept separate from verdicts)

## Running tests

Backend unit tests (verdict-critical logic, compatibility, prerequisite validation,
result schema, checks):

```bash
docker compose run --rm --no-deps --entrypoint sh backend -c "pytest -q"
```

Frontend type check:

```bash
docker compose exec frontend npm run typecheck
```

## Database migrations

Migrations are applied automatically on backend startup. To create a new migration
after changing models:

```bash
docker compose run --rm --entrypoint sh backend -c "alembic revision --autogenerate -m 'your message'"
```

## Security notes (spec section 37)

- GitHub tokens are encrypted at rest (Fernet) and referenced only by an opaque id;
  they are never returned to the frontend or written to logs.
- Test code runs in a separate process, never inside the API.
- Git repository/branch/commit inputs are validated to prevent injection/traversal.
