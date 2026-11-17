# Haki Systems AI Prospecting & Outreach Platform

Status: **Phase 2 — ADK agents + Crawl4AI + Gemini wired in (on top of Phase 1's schema/auth).**
See [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the full phase breakdown and
what is / isn't built yet.

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL + Redis
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS
- AI: Google ADK + Gemini (wired in Phase 3)
- Scraping: Crawl4AI (wired in Phase 3/4)
- Google Workspace: Gmail / Sheets / Drive via OAuth 2.0 (wired in Phase 5)

## What works right now

- User + organisation registration and JWT login (`/api/auth/*`)
- Editable company profile (`/api/company-profile`) — services, markets, messaging live in the
  database, not source code
- Lead CRUD with suppression-list checking (`/api/leads/*`)
- Full relational schema (21 tables) for leads, campaigns, email queue/logs, agent runs, audit
  logs, OAuth token storage (encrypted at rest), etc. — see `backend/app/models/`
- **Five Google ADK agents** (`backend/app/agents/`): Discovery (web search via a swappable
  `SearchProvider`), Research (Crawl4AI with `check_robots_txt=True`), Qualification, Email
  Generation, and a Supervisor that wires the other four as sub-agents. Each uses a Gemini model
  and a Pydantic `output_schema` for validated JSON output.
- **Agent-action endpoints** that run a single agent and persist its output:
  `POST /api/leads/{id}/research`, `/qualify`, `/draft-email` — each logged to `agent_runs` /
  `agent_execution_logs`. Research records a `LeadSource` (source URL) for every contact detail
  it extracts; email drafting is gated to hot/warm leads only and lands in the approval queue
  (`awaiting_approval`), never sent.
- Minimal campaign CRUD (`/api/campaigns`) so drafted emails have a campaign to belong to.
- Next.js dashboard shell with the 12-section navigation from the spec, a working login page,
  and a working Lead Database page reading real data from Postgres
- Automated tests: 34 passing in `backend/tests/`. DB-backed tests run against a **real** Postgres
  (embedded via the `pgserver` dev dependency when Docker isn't available). Agent builders and the
  research→qualify→draft pipeline are tested with mocked I/O so no live Gemini key is needed.

## What's explicitly NOT built yet

Background/at-scale discovery jobs (pause/resume), the Discover/Research/Templates/Approval UIs,
Gmail/Sheets/Drive OAuth and actual email sending, the Email Management + Follow-up agents,
campaign execution, role-based permissions, and analytics. Agent calls require a real
`GEMINI_API_KEY`; without one the endpoints return a clear 503 rather than fabricating data
(the brief prohibits fake functionality). See
[docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md) to provision the credentials.

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
