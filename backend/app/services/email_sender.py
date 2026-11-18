"""Sends an approved EmailQueueItem via Gmail and logs the result. Scheduling
the next follow-up task lives here too, since "sent with no reply yet" is
exactly the condition a follow-up task represents."""

import datetime

from sqlalchemy.orm import Session

from app.models.campaigns import Campaign, EmailLog, EmailQueueItem, EmailQueueStatus, FollowUpTask
from app.models.integrations import Integration
from app.models.leads import Lead, LeadStatus
from app.services import gmail_service
from app.services.integration_credentials import get_valid_credentials


class EmailSendError(RuntimeError):
    pass


def _sent_today_count(db: Session, campaign_id) -> int:
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    return (
        db.query(EmailLog)
        .join(EmailQueueItem, EmailLog.email_queue_id == EmailQueueItem.id)
        .filter(
            EmailQueueItem.campaign_id == campaign_id,
            EmailLog.send_status == "sent",
            EmailLog.created_at >= today_start,
        )
        .count()
    )


def schedule_follow_up(db: Session, campaign: Campaign, lead: Lead) -> FollowUpTask:
    scheduled_for = datetime.date.today() + datetime.timedelta(days=campaign.follow_up_interval_days)
    task = FollowUpTask(campaign_id=campaign.id, lead_id=lead.id, scheduled_for=scheduled_for)
    db.add(task)
    lead.next_follow_up_at = scheduled_for
    db.commit()
    db.refresh(task)
    return task


def send_queued_email(db: Session, email_item: EmailQueueItem) -> EmailLog:
    if email_item.status != EmailQueueStatus.APPROVED:
        raise EmailSendError(
            f"Email is '{email_item.status.value}' — it must be approved before it can be sent."
        )

    lead = db.get(Lead, email_item.lead_id)
    if lead is None:
        raise EmailSendError("Lead for this email no longer exists.")
    if lead.is_unsubscribed:
        raise EmailSendError("Lead is unsubscribed — refusing to send.")
    if not lead.business_email:
        raise EmailSendError("Lead has no business email on file.")

    campaign = db.get(Campaign, email_item.campaign_id)
    if campaign is None or campaign.integration_id is None:
        raise EmailSendError("Campaign has no connected Google integration to send through.")

    sent_today = _sent_today_count(db, campaign.id)
    if sent_today >= campaign.max_daily_sends:
        raise EmailSendError(
            f"Campaign has already sent its daily limit of {campaign.max_daily_sends} emails today."
        )

    integration = db.get(Integration, campaign.integration_id)
    credentials = get_valid_credentials(db, integration)

    email_item.status = EmailQueueStatus.SENDING
    db.commit()

    try:
        result = gmail_service.send_email(credentials, lead.business_email, email_item.subject, email_item.body)
    except Exception as exc:
        email_item.status = EmailQueueStatus.FAILED
        log = EmailLog(email_queue_id=email_item.id, send_status="failed", error_message=str(exc))
        db.add(log)
        db.commit()
        raise EmailSendError(str(exc)) from exc

    email_item.status = EmailQueueStatus.SENT
    log = EmailLog(
        email_queue_id=email_item.id,
        gmail_message_id=result.get("id"),
        gmail_thread_id=result.get("threadId"),
        send_status="sent",
    )
    db.add(log)
    lead.status = LeadStatus.SENT
    lead.last_contact_at = datetime.date.today()
    db.commit()
    db.refresh(log)

    schedule_follow_up(db, campaign, lead)
    return log
