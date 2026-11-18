from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agent_actions,
    audit,
    auth,
    campaigns,
    company_profile,
    discovery,
    email_queue,
    followups,
    health,
    integrations,
    leads,
    replies,
    templates,
)
from app.core.config import settings

app = FastAPI(title="Haki Systems Prospecting Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(company_profile.router)
app.include_router(leads.router)
app.include_router(agent_actions.router)
app.include_router(campaigns.router)
app.include_router(discovery.router)
app.include_router(templates.router)
app.include_router(integrations.router)
app.include_router(email_queue.router)
app.include_router(followups.router)
app.include_router(replies.router)
app.include_router(audit.router)
