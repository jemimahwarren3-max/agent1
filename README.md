# Haki Systems AI Prospecting & Outreach Platform

Status: **Phase 4 — Gmail OAuth, sending, reply monitoring, and follow-up agents wired in
(on top of Phases 1-3's schema/auth/agents/discovery).** See
[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the full phase breakdown and what
is / isn't built yet.

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL + Redis
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS
- AI: Google ADK + Gemini
- Scraping: Crawl4AI
- Google Workspace: Gmail / Sheets / Drive via OAuth 2.0 (Gmail send + reply monitoring wired in
  Phase 4; Sheets/Drive scopes requested but not yet used by any feature)

## What works right now

- User + organisation registration and JWT login (`/api/auth/*`)
- Editable company profile (`/api/company-profile`) — services, markets, messaging live in the
  database, not source code
- Lead CRUD with suppression-list checking (`/api/leads/*`)
- Full relational schema (21 tables) for leads, campaigns, email queue/logs, agent runs, audit
  logs, OAuth token storage (encrypted at rest), etc. — see `backend/app/models/`
- **Seven Google ADK agents** (`backend/app/agents/`, registry in `registry.py`): Discovery, Research,
  Qualification, Email Generation, Supervisor (wires the first four), **Email Management** (reply
  classification), and **Follow-up** (second-touch drafts). Each uses a Gemini model and a Pydantic
  `output_schema` for validated JSON output.
- **Agent-action endpoints** that run a single agent and persist its output:
  `POST /api/leads/{id}/research`, `/qualify`, `/draft-email` — each logged to `agent_runs` /
  `agent_execution_logs`. Research records a `LeadSource` (source URL) for every contact detail
  it extracts; email drafting is gated to hot/warm leads only and lands in the approval queue
  (`awaiting_approval`), never sent.
- Minimal campaign CRUD (`/api/campaigns`) so drafted emails have a campaign to belong to.
- Next.js dashboard shell with the 12-section navigation from the spec, a working login page,
  and a working Lead Database page reading real data from Postgres
- **Google OAuth** (`/integrations`) for Gmail/Sheets/Drive — encrypted token storage, automatic
  refresh. **Gmail sending**: an approved `EmailQueueItem` is sent for real and logged
  (`EmailLog`), scheduling a `FollowUpTask`. **Reply monitoring**: the Email Management Agent
  classifies new replies on a connected campaign's threads (`/inbox`, `POST
  /api/campaigns/{id}/sync-replies`), updates lead status, and auto-suppresses unsubscribe
  requests. **Follow-up Agent** drafts a follow-up for a due task through the same
  approve/send path. **Email Templates** CRUD + editor UI at `/templates`.
- Automated tests: 80 passing in `backend/tests/`. DB-backed tests run against a **real** Postgres
  (embedded via the `pgserver` dev dependency when Docker isn't available). Agent builders, the
  research→qualify→draft pipeline, and the new Gmail/OAuth/reply-monitoring/follow-up services are
  tested with mocked I/O (no live Gemini key or Google account needed to run the suite).

## What's explicitly NOT built yet

The polished campaign builder and approval-queue UIs, suppression-list enforcement wired into
every mutation, rate limiting, role-based permissions, audit logging, and analytics (Phase 5-7).
Agent calls require a real `GEMINI_API_KEY`; without one the endpoints return a clear 503 rather
than fabricating data (the brief prohibits fake functionality). Gmail/reply features require a
Google account actually connected via `/integrations`, which needs a real OAuth client. See
[docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md) to provision both.

## Running locally

### With Docker (recommended once you have Docker Desktop installed)

```bash
cp .env.example .env
# Fill in at least SECRET_KEY and TOKEN_ENCRYPTION_KEY — see .env.example for how to generate them.
docker compose up --build
```

- Backend: http://localhost:8000/docs (FastAPI's auto-generated Swagger UI)
- Frontend: http://localhost:3000

### Without Docker

Backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp ../.env.example ../.env    # edit DATABASE_URL to point at your local Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

### Running tests

```bash
cd backend
pytest -v
```

Tests that need Postgres are skipped automatically if `DATABASE_URL` isn't reachable (printed as
`SKIPPED` in the output) — start Postgres (`docker compose up postgres` or a local install) to
run the full suite.

## Security notes

- Google OAuth refresh/access tokens are stored encrypted (`app/core/crypto.py`, Fernet) — never
  in plaintext, never sent to the browser.
- Default approval mode for sending email is manual for every campaign; automatic sending is an
  explicit opt-in per campaign (built in Phase 6).
- `.env` is gitignored. Never commit real credentials.
