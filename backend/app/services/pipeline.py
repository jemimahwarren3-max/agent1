"""Glues the ADK agents to the database: runs one agent, persists its structured
output onto the right tables, and logs the run via agent_logging. Kept as plain
async functions (not themselves ADK agents) so each step is independently
callable from an API endpoint and independently testable."""

import json
import uuid

from sqlalchemy.orm import Session

from app.agents.email_agent import build_email_agent
from app.agents.qualification_agent import build_qualification_agent
from app.agents.research_agent import build_research_agent
from app.agents.runner import run_agent
from app.agents.schemas import GeneratedEmail, LeadScoreResult, ResearchExtraction
from app.models.campaigns import EmailQueueItem, EmailQueueStatus
from app.models.core import CompanyProfile
from app.models.jobs import JobStatus
from app.models.leads import Lead, LeadClassification, LeadScore, LeadSource, LeadStatus, ResearchReport
from app.services.agent_logging import track_agent_run


class PipelineError(RuntimeError):
    pass


async def research_lead(db: Session, lead: Lead) -> ResearchReport:
    agent = build_research_agent()
    user_message = (
        f"Business name: {lead.business_name}\nWebsite: {lead.website}\n"
        "Research this business and extract what the brief requires."
    )

    with track_agent_run(
        db, lead.organisation_id, "research_agent", {"lead_id": str(lead.id), "website": lead.website}
    ) as (run, log):
        log("start", f"Researching {lead.website}")
        extraction: ResearchExtraction = await run_agent(agent, user_message)
        run.output_payload = extraction.model_dump()
        log("extraction_complete", "Research extraction returned", data=extraction.model_dump())

    report = ResearchReport(
        lead_id=lead.id,
        crawled_urls=extraction.crawled_urls,
        extracted_data=extraction.model_dump(),
        summary=extraction.business_description,
    )
    db.add(report)

    for email in extraction.business_emails:
        db.add(
            LeadSource(
                lead_id=lead.id,
                source_url=email.source_url,
                field_name="business_email",
                discovered_via="research_agent",
            )
        )
    for phone in extraction.phone_numbers:
        db.add(
            LeadSource(
                lead_id=lead.id,
                source_url=phone.source_url,
                field_name="phone_number",
                discovered_via="research_agent",
            )
        )

    lead.business_description = extraction.business_description or lead.business_description
    if extraction.business_emails:
        lead.business_email = extraction.business_emails[0].value
    if extraction.phone_numbers:
        lead.phone_number = extraction.phone_numbers[0].value
    if extraction.contact_person:
        lead.contact_person = extraction.contact_person.value
    lead.identified_opportunity = extraction.identified_opportunity or lead.identified_opportunity
    lead.recommended_service = extraction.recommended_service or lead.recommended_service
    lead.research_notes = extraction.could_not_extract_reason or None
    lead.status = LeadStatus.RESEARCHED

    db.commit()
    db.refresh(report)
    return report


async def qualify_lead(db: Session, lead: Lead, company_profile: CompanyProfile) -> LeadScore:
    latest_report = (
        db.query(ResearchReport)
        .filter(ResearchReport.lead_id == lead.id)
        .order_by(ResearchReport.created_at.desc())
        .first()
    )
    if latest_report is None:
        raise PipelineError("Lead has not been researched yet — call research first.")

    agent = build_qualification_agent()
    user_message = (
        f"Haki Systems services: {company_profile.services}\n"
        f"Target industries: {company_profile.target_industries}\n\n"
        f"Lead: {lead.business_name} ({lead.industry or 'unknown industry'}, "
        f"{lead.city or ''} {lead.country or ''})\n"
        f"Research findings:\n{json.dumps(latest_report.extracted_data, indent=2)}"
    )

    with track_agent_run(
        db, lead.organisation_id, "qualification_agent", {"lead_id": str(lead.id)}
    ) as (run, log):
        log("start", "Scoring lead")
        result: LeadScoreResult = await run_agent(agent, user_message)
        run.output_payload = result.model_dump()
        log("score_complete", f"Scored {result.score} ({result.classification})")

    score = LeadScore(
        lead_id=lead.id,
        score=result.score,
        classification=LeadClassification(result.classification),
        explanation=result.explanation,
    )
    db.add(score)
    lead.status = LeadStatus.QUALIFIED
    db.commit()
    db.refresh(score)
    return score


async def draft_email_for_lead(
    db: Session, lead: Lead, company_profile: CompanyProfile, campaign_id: uuid.UUID
) -> EmailQueueItem:
    latest_score = (
        db.query(LeadScore).filter(LeadScore.lead_id == lead.id).order_by(LeadScore.created_at.desc()).first()
    )
    if latest_score is None:
        raise PipelineError("Lead has not been qualified yet — call qualify first.")
    if latest_score.classification not in (LeadClassification.HOT, LeadClassification.WARM):
        raise PipelineError(
            f"Lead is classified '{latest_score.classification.value}' — only hot/warm leads get drafted emails."
        )

    latest_report = (
        db.query(ResearchReport)
        .filter(ResearchReport.lead_id == lead.id)
        .order_by(ResearchReport.created_at.desc())
        .first()
    )

    agent = build_email_agent()
    user_message = (
        f"Company profile: {company_profile.company_name}, {company_profile.website}, "
        f"phones: {company_profile.phone_numbers}\n\n"
        f"Lead: {lead.business_name}, industry: {lead.industry or 'unknown'}\n"
        f"Identified opportunity: {lead.identified_opportunity}\n"
        f"Recommended service: {lead.recommended_service}\n"
        f"Research summary: {latest_report.summary if latest_report else ''}"
    )

    with track_agent_run(
        db, lead.organisation_id, "email_generation_agent", {"lead_id": str(lead.id)}
    ) as (run, log):
        log("start", "Drafting email")
        generated: GeneratedEmail = await run_agent(agent, user_message)
        run.output_payload = generated.model_dump()
        log("draft_complete", "Draft generated")

    email_item = EmailQueueItem(
        campaign_id=campaign_id,
        lead_id=lead.id,
        subject=generated.subject,
        body=generated.body,
        status=EmailQueueStatus.AWAITING_APPROVAL,
    )
    db.add(email_item)
    lead.status = LeadStatus.DRAFT_READY
    db.commit()
    db.refresh(email_item)
    return email_item
