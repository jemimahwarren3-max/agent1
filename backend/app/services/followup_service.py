"""Turns a due, approved FollowUpTask into a drafted EmailQueueItem using the
Follow-up Agent — mirrors draft_email_for_lead in pipeline.py but for the
no-reply-yet case."""

from sqlalchemy.orm import Session

from app.agents.followup_agent import build_followup_agent
from app.agents.runner import run_agent
from app.agents.schemas import GeneratedEmail
from app.models.campaigns import EmailQueueItem, EmailQueueStatus, FollowUpTask
from app.models.core import CompanyProfile
from app.models.leads import Lead, LeadStatus
from app.services.agent_logging import track_agent_run


class FollowUpError(RuntimeError):
    pass


async def generate_follow_up_draft(
    db: Session, task: FollowUpTask, lead: Lead, company_profile: CompanyProfile
) -> EmailQueueItem:
    if task.is_sent or task.is_cancelled:
        raise FollowUpError("Follow-up task is no longer active.")

    agent = build_followup_agent()
    user_message = (
        f"Company profile: {company_profile.company_name}, {company_profile.website}, "
        f"phones: {company_profile.phone_numbers}\n\n"
        f"Lead: {lead.business_name}, industry: {lead.industry or 'unknown'}\n"
        f"Identified opportunity: {lead.identified_opportunity}\n"
        f"Recommended service: {lead.recommended_service}"
    )

    with track_agent_run(
        db, lead.organisation_id, "followup_agent", {"lead_id": str(lead.id), "task_id": str(task.id)}
    ) as (run, log):
        log("start", "Drafting follow-up email")
        generated: GeneratedEmail = await run_agent(agent, user_message)
        run.output_payload = generated.model_dump()
        log("draft_complete", "Follow-up draft generated")

    email_item = EmailQueueItem(
        campaign_id=task.campaign_id,
        lead_id=lead.id,
        subject=generated.subject,
        body=generated.body,
        status=EmailQueueStatus.AWAITING_APPROVAL,
    )
    db.add(email_item)
    # No separate "drafted" flag on FollowUpTask — is_sent doubles as "this slot
    # has been actioned" so the same due task doesn't generate two drafts.
    task.is_sent = True
    lead.status = LeadStatus.DRAFT_READY
    db.commit()
    db.refresh(email_item)
    return email_item
