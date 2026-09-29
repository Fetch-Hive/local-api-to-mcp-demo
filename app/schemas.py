"""Request and response models. Field descriptions are copied into OpenAPI."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


class Priority(str, Enum):
    """How urgent an issue is. Exactly one of low, medium, or high."""

    low = "low"
    medium = "medium"
    high = "high"


class Status(str, Enum):
    """Workflow state of an issue. Exactly one of open, in_progress, or resolved."""

    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


def _strip_title(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("Title must not be blank.")
    return stripped


def _blank_description_is_null(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class IssueCreate(BaseModel):
    """Body for create_issue. title is required. priority and status have defaults."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "Short name of the issue. Required. Leading and trailing spaces are removed. "
            "Maximum 200 characters."
        ),
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description=(
            "Longer notes, including reproduction steps. Optional. Maximum 5000 characters. "
            "Omit it, or send null, when there are no notes."
        ),
    )
    priority: Priority = Field(
        default=Priority.medium,
        description=(
            "How urgent the issue is. Accepts low, medium, or high. "
            "Defaults to medium when omitted."
        ),
    )
    status: Status = Field(
        default=Status.open,
        description=(
            "Workflow state. Accepts open, in_progress, or resolved. "
            "Defaults to open when omitted. Use open for a newly reported issue."
        ),
    )

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = _strip_title(value)
        assert stripped is not None
        return stripped

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return _blank_description_is_null(value)


class IssueUpdate(BaseModel):
    """Body for update_issue. Every field is optional. Omitted fields stay unchanged."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description=(
            "Replacement name. Omit this field to keep the current title. "
            "Null is rejected. Maximum 200 characters."
        ),
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description=(
            "Replacement notes, including reproduction steps. Omit this field to keep "
            "the current description. Send null to clear it. Maximum 5000 characters."
        ),
    )
    priority: Priority | None = Field(
        default=None,
        description=(
            "Replacement urgency. Omit this field to keep the current priority. "
            "Accepts low, medium, or high. Null is rejected."
        ),
    )
    status: Status | None = Field(
        default=None,
        description=(
            "Replacement workflow state. Omit this field to keep the current status. "
            "Accepts open, in_progress, or resolved. Null is rejected."
        ),
    )

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _strip_title(value)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return _blank_description_is_null(value)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> IssueUpdate:
        for name in ("title", "priority", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(
                    f"{name} cannot be null. Omit {name} to leave it unchanged."
                )
        return self


class IssueRead(BaseModel):
    """One issue, including the id and timestamps assigned by the server."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        description="Numeric id assigned by the database when the issue is created."
    )
    title: str = Field(description="Short name of the issue.")
    description: str | None = Field(
        description="Longer notes, including reproduction steps. Null when the issue has no notes."
    )
    priority: Priority = Field(
        description="How urgent the issue is: low, medium, or high."
    )
    status: Status = Field(
        description="Workflow state: open, in_progress, or resolved."
    )
    created_at: datetime = Field(
        description="UTC time when the issue was created, in ISO 8601."
    )
    updated_at: datetime = Field(
        description=(
            "UTC time when the issue was last changed, in ISO 8601. "
            "Matches created_at until the first update."
        )
    )

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )


class ErrorResponse(BaseModel):
    """A failed request that is not a field-validation error."""

    detail: str = Field(description="Human-readable explanation of why the request failed.")
