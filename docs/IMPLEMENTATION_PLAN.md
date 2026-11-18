# Implementation plan

Phases match the master build prompt. Each phase ends with its own tests passing before moving
on — the brief is explicit that a phase isn't "done" until that happens.

| Phase | Scope | Status |
|---|---|---|
| 1 | Repo scaffold, Postgres schema + Alembic migrations, FastAPI skeleton, JWT auth, Next.js shell with nav | **Done** |
| 2 | Google ADK agents (Discovery, Research, Qualification, Email Generation, Supervisor), Crawl4AI integration, Gemini wiring, agent-run logging, single-lead research/qualify/draft-email endpoints | **Done** |
| 3 | Background discovery jobs (full discover→research→qualify pipeline) with pause/resume/cancel and domain dedup, discovery REST API, Discover Leads UI with live progress, Research Centre UI | **Done** |
| 4 | Email template editor UI, Google OAuth (Gmail/Sheets/Drive), encrypted token storage, Gmail send/draft/reply monitoring, Email Management + Follow-up Agents | **Done** |
| 5 | Campaign builder UI, approval queue UI, suppression-list enforcement end-to-end, rate limiting, role-based permissions, audit logging wired into every mutation | **Done** |
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

## Phase 5 notes

- Campaign builder (`app/api/campaigns.py`): `CampaignCreate`/`CampaignUpdate` now expose every
  builder-relevant field the model already had (`lead_filters` column exists but still isn't read
  by anything — matching uses `target_country`/`target_city`/`target_industry` directly, not the
  JSON blob). `POST /{id}/match-leads` adds every lead matching those three fields that isn't
  already in the campaign and isn't suppressed/unsubscribed, and is idempotent (re-running doesn't
  double-add). `GET /{id}/leads` lists what matched. `approval_mode` is settable and validated but
  not yet enforced anywhere — `automatic` doesn't actually skip the manual approve step in
  `app/api/email_queue.py`; every send still goes through approve then send regardless of mode.
- Approval queue UI (`/approvals`): awaiting-approval and approved-and-ready-to-send lists, wired
  to the Phase 4 approve/reject/send endpoints. The endpoints themselves already existed; this
  phase is what put a UI in front of them and locked them to admin/manager.
- Suppression-list enforcement, actually end-to-end now: a shared `is_suppressed()`
  (`app/services/suppression.py`) is checked at lead creation (already existed), research
  (`pipeline.research_lead` now auto-unsubscribes a lead whose extracted email is suppressed),
  drafting (`pipeline.draft_email_for_lead` refuses an unsubscribed lead), campaign matching
  (skips and counts suppressed leads), and sending (already existed in Phase 4). Discovery-phase
  lead creation has no email yet at that point, so there's nothing to check there — enforcement
  happens as soon as an email exists.
- Rate limiting, two separate things: (1) `app/core/rate_limit.py` — an in-memory, per-IP
  fixed-window limiter (10 requests/60s) on `/api/auth/login` and `/api/auth/register`, the
  brute-force/signup-spam surface. Single-process only, like the Phase 3 BackgroundTasks
  limitation — a multi-process deployment needs this backed by Redis (configured via
  `REDIS_URL`, still not wired to anything) instead of a module dict. (2) a per-campaign daily
  send cap enforced in `email_sender.send_queued_email` against the existing `max_daily_sends`
  column, counting `EmailLog` rows with `send_status="sent"` since midnight.
- Role-based permissions: `require_role(*roles)` (`app/core/deps.py`) alongside the existing
  `require_admin`. Content mutations (templates, campaigns, leads delete, email-queue
  approve/reject/send, follow-up generate/cancel, discovery start/pause/resume/cancel) need
  admin or manager; connecting/disconnecting the Google integration and inviting team members
  are admin-only; approving/unapproving a template specifically needs admin even though editing
  its content only needs manager. There was no way to create a non-admin user before this phase
  (register always makes the first user admin) — added `POST /api/auth/users` (admin-only,
  creates a user in the same org with a chosen role) and `GET /api/auth/users` so RBAC has
  someone to restrict.
- Audit logging (`app/services/audit.py`, `AuditLog` model — it existed since Phase 1 but nothing
  wrote to it until now): one `log_action()` call per mutation across leads, templates, campaigns,
  email-queue actions, follow-ups, integrations connect/disconnect, company profile updates,
  discovery job start/pause/resume/cancel, and user invites. `GET /api/audit-logs` (admin-only)
  surfaces it; `/settings` renders it alongside company profile editing and a team member
  list/invite form (also new — there was previously no UI for either).
- `/settings` and `/campaigns`/`/approvals` had stale `PageStub` phase labels left over from
  before the Phase 5 renumbering (e.g. "Settings" said Phase 2, "Approval Queue" said Phase 6) —
  not touched for any page still legitimately pending (`/agent` Phase 3, `/analytics` Phase 7
  stubs are untouched since those phases are still ahead).

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

## What to do before Phase 6

Phases 4 and 5's code is real and tested (mocked Gmail/OAuth, real Postgres), but nothing in
either has run against a live Google account yet — that still needs the OAuth client from
[GOOGLE_CLOUD_SETUP.md](GOOGLE_CLOUD_SETUP.md) provisioned and a real end-to-end click-through:
connect a Google account on `/integrations`, build a campaign and match leads into it on
`/campaigns`, approve and send a drafted email from `/approvals`, reply to it from another inbox,
and confirm `/inbox` picks up and classifies that reply. Phase 6 (analytics dashboard) needs real
send/reply/campaign data to chart against, so this click-through is also what gives it something
real to aggregate instead of an empty database.
