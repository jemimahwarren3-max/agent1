# Haki Systems AI Prospecting & Outreach Platform

Status: **Phase 5 — campaign builder, approval queue, suppression enforcement, rate limiting,
RBAC, and audit logging (on top of Phases 1-4's schema/auth/agents/discovery/Gmail).** See
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
- **Five Google ADK agents** (`backend/app/agents/`): Discovery (web search via a swappable
  `SearchProvider`), Research (Crawl4AI with `check_robots_txt=True`), Qualification, Email
  Generation, and a Supervisor that wires the other four as sub-agents. Each uses a Gemini model
  and a Pydantic `output_schema` for validated JSON output.
- **Agent-action endpoints** that run a single agent and persist its output:
  `POST /api/leads/{id}/research`, `/qualify`, `/draft-email` — each logged to `agent_runs` /
  `agent_execution_logs`. Research records a `LeadSource` (source URL) for every contact detail
  it extracts; email drafting is gated to hot/warm leads only and lands in the approval queue
  (`awaiting_approval`), never sent.
- Next.js dashboard shell with the 12-section navigation from the spec, a working login page,
  and a working Lead Database page reading real data from Postgres
- **Google OAuth** (`/integrations`, admin-only) for Gmail/Sheets/Drive — encrypted token
  storage, automatic refresh. **Gmail sending**: an approved `EmailQueueItem` is sent for real and
  logged (`EmailLog`), scheduling a `FollowUpTask`. **Reply monitoring**: the Email Management
  Agent classifies new replies on a connected campaign's threads (`/inbox`, `POST
  /api/campaigns/{id}/sync-replies`), updates lead status, and auto-suppresses unsubscribe
  requests. **Follow-up Agent** drafts a follow-up for a due task through the same
  approve/send path. **Email Templates** CRUD + editor UI at `/templates`.
- **Campaign builder** (`/campaigns`): full CRUD (`/api/campaigns`) plus `POST
  /{id}/match-leads`, which adds every lead matching the campaign's target
  country/city/industry that isn't already in it and isn't suppressed. **Approval queue UI**
  (`/approvals`) for the Phase 4 approve/reject/send actions.
- **Suppression-list enforcement**, now checked at every point an email could go out: lead
  creation, research (auto-unsubscribes a lead whose extracted email is suppressed), drafting,
  campaign matching, and sending.
- **Rate limiting**: an in-memory per-IP limiter on login/register (brute-force/signup-spam), and
  a per-campaign daily send cap enforced against `Campaign.max_daily_sends`.
- **Role-based permissions**: `admin`/`manager`/`member`. Content mutations need admin or
  manager; connecting Google and inviting team members are admin-only. `POST /api/auth/users`
  (admin-only) creates teammates with a chosen role — there was no way to do this before.
- **Audit logging**: every mutation above writes an `AuditLog` row; `/settings` (admin-only
  sections) shows the company profile editor, team list/invite form, and the audit log itself.
- Automated tests: 103 passing in `backend/tests/`. DB-backed tests run against a **real**
  Postgres (embedded via the `pgserver` dev dependency when Docker isn't available). Agent
  builders, the research→qualify→draft pipeline, Gmail/OAuth/reply-monitoring/follow-up, and the
  new RBAC/suppression/rate-limit/audit behavior are all tested (no live Gemini key or Google
  account needed to run the suite).

## What's explicitly NOT built yet

Analytics dashboard with real aggregates/Recharts, full Playwright/Vitest coverage, Cloud Run
deployment config, and a production security checklist (Phase 6-7). The `lead_filters` JSON
column on `Campaign` still isn't read by anything — lead matching uses the plain
country/city/industry fields instead. Agent calls require a real `GEMINI_API_KEY`; without one
the endpoints return a clear 503 rather than fabricating data (the brief prohibits fake
functionality). Gmail/reply features require a Google account actually connected via
`/integrations`, which needs a real OAuth client. See
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
- Default approval mode for sending email is manual for every campaign. `Campaign.approval_mode`
  can be set to `automatic`, but nothing reads it yet to skip the manual approve step — every
  send still goes through `POST /api/email-queue/{id}/approve` then `/send`. Wiring automatic
  mode to actually bypass approval is not yet built (noted rather than faked).
- `.env` is gitignored. Never commit real credentials.
