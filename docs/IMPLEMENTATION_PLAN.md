# Implementation plan

Phases match the master build prompt. Each phase ends with its own tests passing before moving
on — the brief is explicit that a phase isn't "done" until that happens.

| Phase | Scope | Status |
|---|---|---|
| 1 | Repo scaffold, Postgres schema + Alembic migrations, FastAPI skeleton, JWT auth, Next.js shell with nav | **Done** |
| 2 | Google ADK agents (Discovery, Research, Qualification, Email Generation, Supervisor), Crawl4AI integration, Gemini wiring, agent-run logging, single-lead research/qualify/draft-email endpoints | **Done** |
| 3 | Background discovery jobs (full discover→research→qualify pipeline) with pause/resume/cancel and domain dedup, discovery REST API, Discover Leads UI with live progress, Research Centre UI | **Done** |
| 4 | Email template editor UI, Google OAuth (Gmail/Sheets/Drive), encrypted token storage, Gmail send/draft/reply monitoring, Email Management + Follow-up Agents | **Done** |
| 5 | Campaign builder UI, approval queue UI, suppression-list enforcement end-to-end, rate limiting, role-based permissions, audit logging wired into every mutation | Not started |
| 6 | Analytics dashboard wired to real DB aggregates, Recharts visualizations | Not started |
| 7 | Full Playwright/Vitest coverage for the frontend, Cloud Run deployment config, production security checklist | Not started |

(Renumbered from the original 8-phase split: RBAC/audit/settings — originally Phase 2 — moved alongside the campaign/approval work in Phase 5, since both need the same "who can act on what" plumbing. Agents moved earlier since they're the system's core value and the brief's own ordering starts there.)

## Phase 2 notes

- Every agent is a real `google.adk.Agent` (ADK 2.11.0) with a Pydantic `output_schema`, built
  and unit-tested against the actual library (not just assumed) — `backend/tests/test_agent_builders.py`
  constructs all five and checks their tool/sub-agent wiring.
- Research and Discovery agents call real tools: `crawl_page` (Crawl4AI, `check_robots_txt=True`)
  and `web_search` (Google Custom Search JSON API, behind a swappable `SearchProvider` interface).
  Both are unit-tested with mocked I/O.
- `backend/tests/test_pipeline.py` runs the actual DB-writing logic (research → qualify → draft
  email, including the "only hot/warm leads get a drafted email" gate) against a **real** Postgres
  — an embedded instance via the `pgserver` dev dependency when Docker isn't available, so these
  tests exercise real SQL instead of skipping. 34/34 tests pass.
- The Alembic migration from Phase 1 was also verified end-to-end against this embedded Postgres
  (not just offline `--sql` mode): `alembic upgrade head` succeeds, all 21 tables + `alembic_version`
  are created.
- Nothing here calls Gemini without a real `GEMINI_API_KEY` — `build_gemini_model()` raises a clear
  `GeminiNotConfiguredError` instead of silently falling back to fake data, matching the brief's
  "do not create fake functionality" rule. Set the key (see `GOOGLE_CLOUD_SETUP.md`) to actually
  run a pipeline end-to-end.

## Phase 3 notes

- Discovery runs as a **background job** (`app/services/discovery_job.py`), triggered via FastAPI
  `BackgroundTasks` so the API never blocks on scraping. The full pipeline runs per job: Discovery
  agent → dedup by normalized domain → save as NEW leads → research each → qualify each, updating
  the `scraping_jobs` counters (discovered/researched/duplicate/qualified/failed) as it goes.
- **Pause/resume/cancel** are coordinated through the job's `status` column: the research loop
  re-reads status before each business, so a pause stops cleanly at a business boundary. Resume is
  idempotent — leads are persisted during discovery and the research phase only touches still-NEW
  leads, so resuming never re-runs the quota-costing search. Verified end-to-end against real
  Postgres in `tests/test_discovery_job.py`, plus the HTTP state machine in `tests/test_discovery_api.py`.
- A per-business failure (e.g. a crawl blocked by robots.txt) is caught, counted in `failed_count`,
  the lead archived with the reason, and the job continues — one bad site never kills the run.
- Added a `leads.scraping_job_id` FK via a second Alembic migration (`defd2e237979`), tested
  upgrade **and** downgrade against real Postgres.
- Frontend: Discover Leads page (`/discover`) with the full brief's form and a live-polling progress
  panel (pause/resume/cancel buttons, per-stage counts); Research Centre (`/research`) to run
  research/qualify on individual leads and review extracted opportunities.
- Known limitation (documented, not faked): processing is sequential within a job and jobs run in
  the API process via BackgroundTasks. A real queue/worker (Celery+Redis, already in requirements)
  with a global concurrency cap is a Phase 5+ hardening step; the `enqueue`-shaped seam is in place.

## Phase 4 notes

- Google OAuth (`app/services/google_oauth.py`, `app/api/integrations.py`): the authorize step is
  a normal JWT-authenticated endpoint; the callback is not, since Google redirects the browser
  straight to it with no Authorization header. A short-lived signed `state` token
  (`create_oauth_state_token` / `decode_oauth_state_token` in `app/core/security.py`) carries the
  organisation id across that gap. Tokens are encrypted at rest via the existing `app/core/crypto.py`
  Fernet helper and refreshed transparently in `app/services/integration_credentials.py`, which
  re-encrypts and persists whatever Google hands back after a refresh.
- Gmail (`app/services/gmail_service.py`): thin wrapper over `googleapiclient` — send, read a
  thread's messages, extract plain-text body, and tell our own sent messages apart from replies.
  `app/services/email_sender.py` glues this to the DB: sends an **approved** `EmailQueueItem`,
  logs the Gmail message/thread id to `EmailLog`, updates the lead, and schedules the next
  `FollowUpTask` based on the campaign's `follow_up_interval_days`.
- Approve/reject/send endpoints (`app/api/email_queue.py`) exist now because Phase 4's Gmail
  sending needs something to drive the `AWAITING_APPROVAL -> APPROVED -> SENT` transition — the
  polished approval-queue UI itself is still Phase 5.
- Email Management Agent (`app/agents/reply_classification_agent.py`) classifies each new reply
  into interested/requesting_info/wants_meeting/not_interested/out_of_office/unsubscribe/other.
  `app/services/reply_monitor.py` polls Gmail threads for sent campaign emails, classifies replies
  not already seen (keyed by Gmail message id), updates the lead's status, cancels pending
  follow-ups on a real reply, and adds an unsubscribe reply straight to the suppression list.
  There's no scheduler yet — sync is triggered on demand via
  `POST /api/campaigns/{id}/sync-replies`, same BackgroundTasks-only limitation noted in Phase 3.
- Follow-up Agent (`app/agents/followup_agent.py`) drafts a short follow-up email reusing the
  `GeneratedEmail` schema; `app/services/followup_service.py` turns a due, non-cancelled
  `FollowUpTask` into a new `AWAITING_APPROVAL` queue item through the normal approval/send path.
- Email Templates CRUD (`app/api/templates.py`) and its frontend editor at `/templates` — the
  actual re-use of an approved template as a starting point for an agent draft is not wired in
  yet (the email/followup agents still generate from scratch each time).
- Frontend: `/templates` (create/edit/approve/delete), `/integrations` (connect/disconnect Google,
  shows connected account + granted scopes), `/inbox` (lists classified replies, a "check for
  replies" button per campaign).
- `google-auth` had to move from the `==2.35.0` pin to `==2.62.2` — `google-adk` 2.11.0 and
  `google-genai` 2.33.0 both need `google-auth>=2.47`/`>=2.56` respectively, which the original
  pin predates. Verified the existing agent-builder tests still pass after the bump.

## Why Phase 1 stopped where it did

The master prompt itself warns against generating all phases in one pass — "that will save you
from ending up with a beautiful interface and an agent that doesn't actually work." Phases 3–7
all depend on credentials that don't exist yet in this environment (Gemini API key, Google OAuth
client, a Programmable Search Engine key). Building those agents now would mean either:

1. Writing code that calls real APIs with placeholder keys (untestable, and risks shipping an
   integration bug straight to your real Gmail account later), or
2. Hardcoding sample/demo data to make the UI look functional — which section 16 of the brief
   explicitly forbids ("Do not create fake functionality... Do not replace working backend logic
   with hardcoded sample data").

Phase 1 instead builds everything that doesn't depend on those credentials and is fully testable
now: the data model, auth, the editable company profile, and the dashboard shell.

## What to do before Phase 2+

1. Provision the credentials in [GOOGLE_CLOUD_SETUP.md](GOOGLE_CLOUD_SETUP.md).
2. Install Docker Desktop (or a local Postgres) so the DB-backed tests actually run, not just
   skip.
3. Decide on a search provider for lead discovery (Google Programmable Search Engine is the
   default assumption; Bing/SerpAPI are viable swaps behind the same abstraction).

## What to do before Phase 5

Phase 4's code is real and tested (mocked Gmail/OAuth, real Postgres), but nothing in it has run
against a live Google account yet — that needs the OAuth client from
[GOOGLE_CLOUD_SETUP.md](GOOGLE_CLOUD_SETUP.md) provisioned and a real end-to-end click-through:
connect a Google account on `/integrations`, send an approved email, reply to it from another
inbox, and confirm `/inbox` picks up and classifies that reply. Phase 5 (campaign builder,
approval queue UI, suppression enforcement, RBAC, audit logging) builds UI on top of the
email-queue/follow-up endpoints Phase 4 added, so getting a real send/reply loop verified first
will surface any Gmail-specific edge case before more UI gets built on top of it.
