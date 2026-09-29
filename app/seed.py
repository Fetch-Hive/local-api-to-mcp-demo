"""Seed rows inserted when the issues table is empty."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Issue
from app.schemas import Priority, Status

# Created during the demo by a remote MCP client. Do not insert it here.
DEMO_ISSUE_TITLE = "Checkout fails when the session expires"


@dataclass(frozen=True)
class SeedIssue:
    title: str
    description: str
    priority: Priority
    status: Status
    age: timedelta


SEED_ISSUES: tuple[SeedIssue, ...] = (
    SeedIssue(
        title="Add CSV export",
        description="Let someone download the current issue list as a CSV file.",
        priority=Priority.medium,
        status=Status.open,
        age=timedelta(hours=3),
    ),
    SeedIssue(
        title="Review onboarding email copy",
        description="Read the welcome email and note any copy that is unclear.",
        priority=Priority.low,
        status=Status.in_progress,
        age=timedelta(hours=2),
    ),
    SeedIssue(
        title="Fix incorrect dashboard totals",
        description="The dashboard counts do not match the issues stored in the tracker.",
        priority=Priority.high,
        status=Status.resolved,
        age=timedelta(hours=1),
    ),
)


def seed_if_empty(session: Session) -> None:
    count = session.scalar(select(func.count()).select_from(Issue))
    if count:
        return
    now = datetime.now(timezone.utc)
    for item in SEED_ISSUES:
        created_at = now - item.age
        session.add(
            Issue(
                title=item.title,
                description=item.description,
                priority=item.priority.value,
                status=item.status.value,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    session.commit()
