# DriveTest — Network Test Orchestration Platform

A web platform for orchestrating and evaluating network equipment validation tests.
It implements the MVP described in [`DriveTest_SPEC.md`](DriveTest_SPEC.md), built as a
modular monolith: a FastAPI + PostgreSQL backend and a React + TypeScript (dark themed)
frontend. Spec phases 1-10 are implemented.

## Contents

- [What you can do](#what-you-can-do)
- [Key concepts](#key-concepts)
- [Architecture](#architecture)
- [Project layout](#project-layout)
- [Prerequisites](#prerequisites)
- [First-time setup](#first-time-setup)
- [Everyday commands](#everyday-commands)
- [Manual demo walkthrough](#manual-demo-walkthrough)
- [Connecting GitHub](#connecting-github)
- [AI evaluator](#ai-evaluator)
- [Running tests](#running-tests)
- [Database migrations](#database-migrations)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)
- [Security notes](#security-notes)

## What you can do

Sign in, connect your GitHub account, pick a test Suite, open its Environment tab (suite
README + a dynamically generated prerequisite form where you enter device IPs),
choose a Git branch/commit, start a Run,
watch tests execute one by one, and review each test's result — including an AI review and
a final verdict — plus an export-friendly report.

## Key concepts

The heart of the product is how a verdict is decided. Four values are always kept separate
and shown in the UI (never hidden):

- **Execution status** — did the test process run at all? (`COMPLETED`, `SCRIPT_ERROR`,
  `INFRA_ERROR`, `TIMEOUT`, ...). An execution failure is NOT a product failure.
- **Test verdict** — what the test script itself decided: `PASSED`, `FAILED`, or `null`
  (the test punts the decision to AI).
- **AI verdict** — the AI reviewer's opinion: `PASSED`, `FAILED`, or `INCONCLUSIVE`.
  AI reviews every completed test.
- **Final verdict** — computed by the backend from the exact rule in the spec
  (`app/evaluation/verdict.py`). A deterministic `FAILED` can never become `PASSED`.
  If AI is `INCONCLUSIVE`, the final verdict is `REVIEW_REQUIRED`.

The final-verdict rule lives only in the backend and is covered by unit tests
(`backend/tests/test_final_verdict.py`).

## Architecture

```
frontend (React/Vite)  ->  backend (FastAPI)  ->  PostgreSQL
                                  |
                                  +-- runner (one subprocess per test, isolated workspace)
                                  +-- ai (pluggable evaluator: mock | openai | anthropic)
                                  +-- git (per-user GitHub, tokens encrypted at rest)
```

Everything runs in Docker: PostgreSQL 16, a Python 3.12 backend, and a Node 20 frontend.

## Project layout

```
DriveTest/
├── docker-compose.yml         # runs db + backend + frontend
├── .env.example               # copy to .env and fill in
├── DriveTest_SPEC.md          # the source-of-truth specification
├── definitions/               # demo Suites, prerequisite forms, tests
│   ├── suites/<id>/           # suite.yaml + README.md + tests/<id>/{test.py,test.yaml}
│   └── prerequisites/<id>/    # common.yaml (the device/prerequisite form)
├── backend/
│   ├── app/                   # one folder per domain:
│   │   ├── core/              #   config, logging, enums, error shape
│   │   ├── db/                #   SQLAlchemy base/session/model registry
│   │   ├── auth/ suites/ prerequisites/ git/ runs/ results/ connections/
│   │   ├── runner/            #   subprocess execution + result contract
│   │   ├── ai/                #   evaluator abstraction + providers
│   │   └── evaluation/        #   final verdict engine
│   ├── alembic/               # database migrations
│   └── tests/                 # pytest suite
└── frontend/
    └── src/
        ├── api/               # typed client + TanStack Query hooks
        ├── components/        # layout, status pills, prerequisite form
        └── pages/             # login, dashboard, new-run wizard, run detail
```

## Prerequisites

- Docker and Docker Compose. Nothing else is needed on your machine (Python and Node run
  inside the containers). Make sure the Docker daemon is running.

## First-time setup

1. Create your env file and generate a secret encryption key:

```bash
cd DriveTest
cp .env.example .env
docker compose run --rm --entrypoint sh backend -c "python -m app.cli genkey"
```

Copy the printed value into `.env` as `DRIVETEST_SECRET_ENCRYPTION_KEY`. (This is only
required to connect GitHub; the rest of the app runs without it.)

2. Start everything:

```bash
docker compose up --build
```

On startup the backend waits for the database, applies migrations, and seeds the demo
definitions. Then open:

- Frontend: http://localhost:5173
- Backend API docs (interactive): http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Everyday commands

```bash
# Start in the background (no logs in your terminal)
docker compose up -d

# Follow logs (all services, or one)
docker compose logs -f
docker compose logs -f backend

# Stop the stack (keeps the database)
docker compose down

# Stop AND wipe the database (fresh start; re-seeds on next up)
docker compose down -v

# Restart just the backend
docker compose restart backend

# Re-seed definitions after editing files under definitions/
docker compose exec backend python -m app.cli seed
```

Backend code changes hot-reload automatically. Frontend changes hot-reload in the browser.
Changing Python dependencies requires `docker compose build backend`.

## Manual demo walkthrough

1. Sign in with any email (this is dev login; no password).
2. New Run → pick "Demo Shaping Suite".
3. Environment tab: read the suite README (purpose + connectivity), then fill the
   prerequisite form — enter the DUT Management IP. Click "Validate & Continue" (validation
   runs on the backend). There is no separate environment to select; you provide the devices.
4. Git Revision: leave "Use built-in demo definitions" (or connect GitHub first to run
   from a real repository).
5. Review & Run. Watch tests execute sequentially, then expand each to see its AI review
   and final verdict. With the default mock evaluator you will see:
   - `device_facts` → uses the Run-owned device connection via ExecutionContext, final PASSED
   - `basic_pass` → test PASSED, AI PASSED, final PASSED
   - `ai_anomaly` → test PASSED, AI FAILED (anomaly), final FAILED (disagreement shown)
   - `ai_judged` → test null, AI PASSED, final PASSED
   - `script_error` → SCRIPT_ERROR (execution failure, no product verdict)
6. Use "Print report" on the run page for an export-friendly summary.

## Connecting GitHub

Two options:

- **Personal access token (simplest).** In GitHub, create a token (a fine-grained or
  classic read-only token; classic needs the `repo` scope to see private repos). On the
  Git Connection page, paste it and click Connect. The token is validated, encrypted, and
  stored; it is never shown again or sent back to the browser.
- **OAuth.** Set `DRIVETEST_GITHUB_CLIENT_ID` / `DRIVETEST_GITHUB_CLIENT_SECRET` in `.env`
  from a GitHub OAuth app whose callback is `http://localhost:8000/api/git/oauth/callback`,
  then use "Connect with GitHub".

Each user connects their own account; the app only ever uses your access, never a shared
token.

## AI evaluator

Every completed test gets an AI review (spec §6). The provider is pluggable behind
`app/ai`. The default is an offline `mock` evaluator, so the demo works with no network or
API key. To use a real model, set in `.env`:

```bash
DRIVETEST_AI_PROVIDER=openai        # or: anthropic
DRIVETEST_OPENAI_API_KEY=sk-...     # or DRIVETEST_ANTHROPIC_API_KEY=...
```

The model name and prompt/policy versions are recorded with every evaluation for
reproducibility.

## Device connections

SSH connections are owned by the Run, not by individual tests (spec §51). At the start of a
Run, the Connection Manager establishes one persistent session per required device and starts
a per-Run connection broker (localhost, token-authenticated). Tests never open SSH themselves
and never see hosts or credentials — they use the `drivetest` ExecutionContext SDK, which the
platform injects onto the test's `PYTHONPATH`:

```python
from drivetest import ExecutionContext

ctx = ExecutionContext.from_env()
dut = ctx.device("dut")
dut.run("show interfaces description")               # read
dut.configure(["interfaces", "  ge0", '    description "x"', "  !", "!"])  # stage candidate
dut.commit()                                          # apply
dut.rollback(1); dut.commit()                         # revert to previous committed config
```

Sessions are **prerequisite-driven**: a prerequisite field marked `device_role` opens one
session to the host the user enters (see `definitions/prerequisites/*/common.yaml`). The number
of such fields determines how many sessions open; the operator picks the hostnames at run time.
The transport is pluggable: the default `simulated` transport is a small stateful DNOS model
(supports `show interfaces description`, `configure`/`commit`/`rollback`) so tests run and
verify offline; set `DRIVETEST_SSH_TRANSPORT=ssh` (rebuild the backend image) to use a real
persistent SSH shell via paramiko. Sessions are closed automatically at the end of the Run.

## Running tests

Backend unit tests (final-verdict truth table, compatibility, prerequisite validation,
result schema, checks, AI evaluator):

```bash
docker compose run --rm --no-deps --entrypoint sh backend -c "pytest -q"
```

Frontend type check and production build:

```bash
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run build
```

## Database migrations

Migrations are applied automatically on backend startup. After changing models, create a
new migration:

```bash
docker compose run --rm --entrypoint sh backend -c "alembic revision --autogenerate -m 'your message'"
```

## Troubleshooting

- **"port is already allocated" / address in use** — something else uses 5173, 8000, or
  5432. Stop it, or change the left-hand port in `docker-compose.yml` (e.g. `8001:8000`).
- **Cannot connect to the Docker daemon** — start Docker and retry.
- **Frontend can't reach the backend** — confirm the backend is up
  (`curl http://localhost:8000/health`) and that the sidebar shows "Backend online".
- **401 on API calls** — you're signed out; sign in again (the session cookie expired or
  was cleared).
- **Login/session issues across origins** — use `http://localhost:5173` (not `127.0.0.1`)
  so cookies match the configured CORS origin.
- **Database looks stale / migration errors** — reset with `docker compose down -v` then
  `docker compose up`, which recreates and re-seeds the database.
- **GitHub connect fails** — ensure `DRIVETEST_SECRET_ENCRYPTION_KEY` is set in `.env`
  (needed to encrypt the token) and that your token is valid.

## Known limitations

These are intentional MVP scope choices, not bugs:

- Cancelling a run marks it `CANCELLED` but does not interrupt an in-flight test process.
- OAuth requests read-only user scope; cloning private repos currently needs a PAT with
  `repo` scope.
- Lists (repositories, commits, runs) return the first page only (no pagination yet).
- Frontend automated tests are not included yet; the backend is fully unit-tested.

## Security notes (spec §37)

- GitHub tokens are encrypted at rest (Fernet) and referenced only by an opaque id; they
  are never returned to the frontend or written to logs.
- Test code always runs in a separate process, never inside the API.
- Automatic prerequisite checks use a fixed registry of handlers — YAML can never run
  arbitrary commands.
- Git repository/branch/commit inputs are validated to prevent injection/path traversal.
- Never commit your `.env` (it is git-ignored).
```
