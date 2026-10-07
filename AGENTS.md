# Nilai — Django/HTMX rewrite rules

This repo is a Django 5.2 + HTMX port of the original Next.js app. The port is complete and the TypeScript codebase was deleted in Phase 7; parity with the old app is a hard requirement (same DB schema, same URLs without trailing slashes, same Indonesian UI copy incl. typos, same scrypt password-hash format).

## Commands

- Python: always `.venv/bin/python` (3.12); install packages only via `.venv/bin/python -m pip`.
- Dev server: `.venv/bin/python manage.py runserver 0.0.0.1:3001` (tests expect :3001). Docker prod: `docker compose up -d --build` (:3000, gunicorn). DB: `docker compose exec -T db psql -U nilai -d nilai -tAc "..."`.
- Static checks: `.venv/bin/python manage.py check` after edits. **Never regenerate migrations** — the schema is byte-parity with the old app (`db_constraint=False` FKs + RunSQL).
- Tests (run from repo root, suites restore seed state): `tests/http/*.py` (live server, session helper in `tests/http/session.py`, Playwright walkthrough needs Chrome) and `tests/test_*.py` (Django test client). Baseline: 1422 checks / 0 failures.

## Conventions

- Answer the user in English; all UI copy is Indonesian; no emoji.
- Commit only when the user explicitly asks.
- Shell gotchas: zsh expands `=word`/`===` — quote them; `.env.local` is read by `nilai/settings.py`; do not put secrets in code or reports (they live in `.env.local` / `/admin/settings`).
- Templates need their own `{% load nilai_tags %}` (includes don't inherit). HTMX partials: never return an `<td>` root with OOB siblings (foster-parenting breaks htmx's td parser) — return an input-root fragment with `hx-swap="innerHTML"`.
