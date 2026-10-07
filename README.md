# Nilai — AI-Assisted Academic Grading Platform

A web platform for running courses, assignments, submissions, and grading end-to-end, with optional AI-assisted grading (LLM + RAG over document chunks). Three roles: **Admin**, **Dosen (lecturer)**, and **Mahasiswa (student)**. The display name, footer text, and logo are configurable from the admin panel (Admin → Aplikasi; defaults to "MiniCourse").

## Features

**Admin**
- User management (create/edit/activate) with **Excel import**: upload `.xlsx` → preview → confirm; existing emails are skipped, never overwritten; template download provided
- Classes with **Periode** (e.g. 2025/2026 Ganjil) and **Kelas** (section), student placement/enrollment
- App branding: name, footer, logo (used for browser title, navbar, login, breadcrumbs, footer)
- Model settings: OpenAI-compatible chat + embeddings endpoints, API keys

**Dosen**
- Courses, topics (pertemuan), assignments in 4 types: **PG (multiple choice), Essay, PDF, DOCX**
- Weighted rubric (criteria × levels, drag & drop) and release modes: *review* (manual publish) or *langsung* (instant AI grading on submit)
- Submissions overview, manual grading or **grade with model**, draft → publish workflow
- Read-only view of course period/section

**Mahasiswa**
- Course catalog with index, tasks overview, quiz-taking UI with question navigator
- Submissions (text, file upload), grades with predikat (A–D) and feedback

**AI grading**
- DOCX/PDF extraction (`python-docx` / `pypdf`) → chunked → embedded into `pgvector` → top-k retrieval feeds an OpenAI-compatible `/chat/completions` call; grading source is recorded per grade (`code` | `model` | manual)

## Tech stack

Python 3.12 + Django 5.2 (server-rendered templates) with HTMX (`django-htmx`) for partial actions, PostgreSQL 17 + pgvector, openpyxl, Gunicorn + WhiteNoise, Docker Compose.

## Quickstart (local)

Prerequisites: Docker + Docker Compose.

```bash
git clone <repo> && cd <repo>
cp .env.example .env.local   # then edit the values
docker compose up -d --build  # app on http://localhost:3000
```

- **Dev mode** (hot reload on port 3001): `docker compose --profile dev up -d`
- **Reset database** (drops all data, re-seeds): `docker compose --profile dev down -v && docker compose up -d --build`
- **Seed accounts** (password `password123`):

| Role | Email |
|---|---|
| Admin | audyah@nilai.test |
| Dosen | ramadan@nilai.test |
| Mahasiswa | aldy@nilai.test, miratil@nilai.test, ismail@nilai.test, fitri@nilai.test |

Seeds and schema migrations run automatically on first boot.

## Standalone install (without Docker)

Prerequisites: **Python 3.12** and a reachable **PostgreSQL 17 with the `pgvector` extension available**. The first migration runs `CREATE EXTENSION IF NOT EXISTS vector`, so the connecting role needs permission to create it — either use a superuser role or pre-create the extension once (`CREATE EXTENSION vector;`).

```bash
git clone <repo> && cd <repo>

# 1. Virtualenv + dependencies
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 2. Database (create once; the `vector` extension is added by migrations)
createdb nilai

# 3. Configuration
cp .env.example .env.local   # then set DATABASE_URL, SESSION_SECRET, LLM_*/EMB_*

# 4. Schema + seed data (the same steps Docker runs on boot)
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed

# 5. Run the dev server
.venv/bin/python manage.py runserver 127.0.0.1:3001   # http://localhost:3001
```

Set `DATABASE_URL` to your local database (adjust the user/password to your role), e.g. `postgresql://nilai:nilai@localhost:5432/nilai`. `runserver` serves static assets in development; for a production-style run without Docker, collect static files and use Gunicorn behind a reverse proxy:

```bash
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/gunicorn nilai.wsgi:application --bind 0.0.0.0:3000 --workers 2 --timeout 120
```

**Grading CLI (no Docker, no PostgreSQL).** The simulation tool in `tools/grade_cli.py` reuses the same `.venv` but needs neither Docker nor a database — it only reads the LLM settings from `.env.local`:

```bash
.venv/bin/python tools/grade_cli.py
```

## Configuration (`.env.local`)


| Variable | Purpose |
|---|---|
| `SESSION_SECRET` | Cookie signing secret — **must** be a long random string |
| `DATABASE_URL` | Overridden by compose; only needed when running Django outside Docker |
| `EMBEDDING_DIM` | Vector size, must match the embedding model (default 1536) |
| `EMBEDDING_TOP_K` | RAG chunks retrieved per grading prompt (default 6) |
| `LLM_*` / `EMB_*` | Chat + embeddings base URL, model, API key (seeded to `/admin/settings` on first boot; runtime edits there win until the DB volume is reset) |

## Tests

HTTP-level suites run against a live dev server (`http://localhost:3001`, e.g. `docker compose --profile dev up -d` or `.venv/bin/python manage.py runserver 0.0.0.1:3001`). Django test-client suites need no server. Run each suite from the repo root with `.venv/bin/python`; suites mutate the database and restore seed state on exit.

```bash
# live-server suites (tests/http/)
.venv/bin/python tests/http/spot.py              # page smoke checks per role (30)
.venv/bin/python tests/http/login_test.py        # login/session (9)
.venv/bin/python tests/http/walkthrough_admin.py # Playwright admin walkthrough, needs Chrome (38)
.venv/bin/python tests/http/test_actions.py      # full e2e: grading, branding, import (70)

# Django test-client suites (tests/test_*.py, 1275 checks total)
for f in tests/test_*.py; do .venv/bin/python "$f"; done
```

Full regression baseline: **1422 checks, 0 failures**.

## Deployment

The app is containerized — any Docker host works. Recommended: **a small VPS** (needs ≥ 1 GB RAM).

```bash
git clone <repo> && cd <repo>
# create .env.local: SESSION_SECRET, LLM_*, EMB_* (see above)
docker compose up -d --build
```

Production checklist:

- Set a strong `SESSION_SECRET` (the code falls back to a dev secret if unset → forgeable sessions)
- The compose file ships dev Postgres credentials (`nilai:nilai`) and publishes `5432` — change the password and remove (or bind to `127.0.0.1`) the `db.ports` mapping before going public
- Put a reverse proxy (Caddy/nginx/Traefik) in front for HTTPS → `localhost:3000`
- Back up the `pgdata` volume regularly (`pg_dump`)
- The `dev` profile is for local development only — don't run it in production

**PaaS alternatives** (connect the repo): Railway, Render, or Fly.io — deploy the Dockerfile and attach a Postgres with **pgvector** enabled, then set the env vars above. Generic serverless platforms are a poor fit: AI grading calls exceed serverless timeouts and you'd need an external pgvector database.
