# Implementation plan

Phases match the master build prompt. Each phase ends with its own tests passing before moving
on — the brief is explicit that a phase isn't "done" until that happens.

| Phase | Scope | Status |
|---|---|---|
| 1 | Repo scaffold, Postgres schema + Alembic migrations, FastAPI skeleton, JWT auth, Next.js shell with nav | **Done** |
| 2 | Google ADK agents (Discovery, Research, Qualification, Email Generation, Supervisor), Crawl4AI integration, Gemini wiring, agent-run logging, single-lead research/qualify/draft-email endpoints | **Done** |
| 3 | Background discovery jobs (full discover→research→qualify pipeline) with pause/resume/cancel and domain dedup, discovery REST API, Discover Leads UI with live progress, Research Centre UI | **Done** |
| 4 | Email template editor UI, Google OAuth (Gmail/Sheets/Drive), encrypted token storage, Gmail send/draft/reply monitoring, Email Management + Follow-up Agents | Not started |
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
