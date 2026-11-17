"""Polls Gmail threads for replies to sent campaign emails, classifies each
new one with the Email Management Agent, and updates the lead's status.
Called on demand from the API rather than a background scheduler — there's
no task queue wired up yet (see the Phase 3 notes on BackgroundTasks)."""

from sqlalchemy.orm import Session

from app.agents.reply_classification_agent import build_reply_classification_agent
from app.agents.runner import run_agent
from app.agents.schemas import ReplyClassificationResult
from app.models.campaigns import Campaign, EmailLog, EmailQueueItem, EmailReply, FollowUpTask, ReplyClassification
from app.models.integrations import Integration
from app.models.leads import Lead, LeadStatus, SuppressionListEntry
from app.services import gmail_service
from app.services.integration_credentials import get_valid_credentials

_LEAD_STATUS_BY_CLASSIFICATION = {
    ReplyClassification.INTERESTED: LeadStatus.INTERESTED,
    ReplyClassification.WANTS_MEETING: LeadStatus.MEETING_REQUESTED,
    ReplyClassification.NOT_INTERESTED: LeadStatus.NOT_INTERESTED,
    ReplyClassification.UNSUBSCRIBE: LeadStatus.UNSUBSCRIBED,
}


class ReplyMonitorError(RuntimeError):
    pass


def _apply_classification(db: Session, lead: Lead, classification: ReplyClassification) -> None:
    lead.status = _LEAD_STATUS_BY_CLASSIFICATION.get(classification, LeadStatus.REPLIED)

    if classification == ReplyClassification.UNSUBSCRIBE and lead.business_email:
        lead.is_unsubscribed = True
        already_suppressed = (
            db.query(SuppressionListEntry)
            .filter(
                SuppressionListEntry.organisation_id == lead.organisation_id,
                SuppressionListEntry.email == lead.business_email,
            )
            .first()
        )
        if not already_suppressed:
            db.add(
                SuppressionListEntry(
                    organisation_id=lead.organisation_id,
                    email=lead.business_email,
                    reason="Replied with unsubscribe request",
                )
            )

    if classification != ReplyClassification.OUT_OF_OFFICE:
        # A real human reply means the automated follow-up cadence should stop.
        db.query(FollowUpTask).filter(
            FollowUpTask.lead_id == lead.id,
            FollowUpTask.is_sent == False,  # noqa: E712
            FollowUpTask.is_cancelled == False,  # noqa: E712
        ).update({"is_cancelled": True})


async def sync_replies_for_campaign(db: Session, campaign: Campaign) -> list:
    """Returns the newly created EmailReply rows."""
    if campaign.integration_id is None:
        raise ReplyMonitorError("Campaign has no connected Google integration.")

    integration = db.get(Integration, campaign.integration_id)
    credentials = get_valid_credentials(db, integration)
    our_email = integration.connected_account_email or ""

    sent_logs = (
        db.query(EmailLog, EmailQueueItem)
        .join(EmailQueueItem, EmailLog.email_queue_id == EmailQueueItem.id)
        .filter(
            EmailQueueItem.campaign_id == campaign.id,
            EmailLog.send_status == "sent",
            EmailLog.gmail_thread_id.isnot(None),
        )
        .all()
    )

    agent = build_reply_classification_agent()
    created: list = []

    for log, queue_item in sent_logs:
        lead = db.get(Lead, queue_item.lead_id)
        if lead is None:
            continue

        messages = gmail_service.list_thread_messages(credentials, log.gmail_thread_id)
        for message in messages:
            if gmail_service.is_from_us(message, our_email):
                continue

            exists = db.query(EmailReply).filter(EmailReply.gmail_message_id == message["id"]).first()
            if exists:
                continue

            body_text = gmail_service.extract_message_text(message)
            result: ReplyClassificationResult = await run_agent(agent, body_text)
            classification = ReplyClassification(result.classification)

            reply = EmailReply(
                lead_id=lead.id,
                gmail_thread_id=log.gmail_thread_id,
                gmail_message_id=message["id"],
                body_snippet=body_text[:2000],
                classification=classification,
            )
            db.add(reply)
            _apply_classification(db, lead, classification)
            db.commit()
            db.refresh(reply)
            created.append(reply)

    return created
