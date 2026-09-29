"""Issue CRUD routes. operation_id values are the MCP tool names."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Issue
from app.schemas import ErrorResponse, IssueCreate, IssueRead, IssueUpdate

router = APIRouter(prefix="/api", tags=["issues"])
DbSession = Annotated[Session, Depends(get_db)]

IssueId = Annotated[
    int,
    Path(
        ge=1,
        description=(
            "Numeric id of the issue. Ids are positive integers assigned when the issue is created."
        ),
    ),
]

NOT_FOUND = "No issue exists with this id."


def _get_or_404(session: Session, issue_id: int) -> Issue:
    issue = session.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return issue


@router.get(
    "/issues",
    response_model=list[IssueRead],
    operation_id="list_issues",
    summary="List issues",
    description=(
        "Return every issue stored in the local database. "
        "The newest issue is first, ordered by created_at descending, then id descending."
    ),
)
def list_issues(session: DbSession) -> list[Issue]:
    statement = select(Issue).order_by(Issue.created_at.desc(), Issue.id.desc())
    return list(session.scalars(statement).all())


@router.get(
    "/issues/{issue_id}",
    response_model=IssueRead,
    operation_id="get_issue",
    summary="Get an issue",
    description="Return one issue by its numeric id. The response is 404 when no row has that id.",
    responses={
        404: {"model": ErrorResponse, "description": "No issue exists with this id."},
    },
)
def get_issue(issue_id: IssueId, session: DbSession) -> Issue:
    return _get_or_404(session, issue_id)


@router.post(
    "/issues",
    response_model=IssueRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_issue",
    summary="Create an issue",
    description=(
        "Create one issue and return it, including the id and timestamps assigned by the server. "
        "Put reproduction notes in description. priority accepts low, medium, or high. "
        "status accepts open, in_progress, or resolved."
    ),
)
def create_issue(payload: IssueCreate, session: DbSession) -> Issue:
    now = datetime.now(timezone.utc)
    issue = Issue(
        title=payload.title,
        description=payload.description,
        priority=payload.priority.value,
        status=payload.status.value,
        created_at=now,
        updated_at=now,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue


@router.patch(
    "/issues/{issue_id}",
    response_model=IssueRead,
    operation_id="update_issue",
    summary="Update an issue",
    description=(
        "Change one or more fields on an existing issue. Omit a field to leave it unchanged. "
        "Send description as null to clear the notes. The response is the issue after the change. "
        "The response is 404 when no row has that id."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "No issue exists with this id."},
    },
)
def update_issue(issue_id: IssueId, payload: IssueUpdate, session: DbSession) -> Issue:
    issue = _get_or_404(session, issue_id)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    if not changes:
        return issue
    for key, value in changes.items():
        setattr(issue, key, value)
    issue.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(issue)
    return issue


@router.delete(
    "/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    operation_id="delete_issue",
    summary="Delete an issue",
    description=(
        "Delete one issue by its numeric id. A successful delete returns 204 and an empty body. "
        "The response is 404 when no row has that id."
    ),
    responses={
        204: {"description": "The issue was deleted. The body is empty."},
        404: {"model": ErrorResponse, "description": "No issue exists with this id."},
    },
)
def delete_issue(issue_id: IssueId, session: DbSession) -> Response:
    issue = _get_or_404(session, issue_id)
    session.delete(issue)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
