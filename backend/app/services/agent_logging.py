"""Wraps an agent/tool invocation with AgentRun + AgentExecutionLog persistence,
per the brief's requirement that every agent execution be tracked and auditable."""

import uuid
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session

from app.models.jobs import AgentExecutionLog, AgentRun, JobStatus


@contextmanager
def track_agent_run(
    db: Session,
    organisation_id: uuid.UUID,
    agent_name: str,
    input_payload: dict[str, Any],
    scraping_job_id: uuid.UUID | None = None,
):
    run = AgentRun(
        organisation_id=organisation_id,
        agent_name=agent_name,
        scraping_job_id=scraping_job_id,
        status=JobStatus.RUNNING,
        input_payload=input_payload,
        output_payload={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    def log(step_name: str, message: str, level: str = "info", data: dict | None = None) -> None:
        db.add(
            AgentExecutionLog(
                agent_run_id=run.id,
                step_name=step_name,
                level=level,
                message=message,
                data=data or {},
            )
        )
        db.commit()

    try:
        yield run, log
    except Exception as exc:
        run.status = JobStatus.FAILED
        log("run_failed", str(exc), level="error")
        db.commit()
        raise
    else:
        run.status = JobStatus.COMPLETED
        db.commit()
