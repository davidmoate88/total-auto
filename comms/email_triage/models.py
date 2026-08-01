"""
Data model + interface stub for email/information triage.

ARCHITECTURE STUB: `triage_inbox()` defines the intended interface and raises
NotImplementedError — no inbox connector or triage logic exists yet (see
docs/ROADMAP.md Milestone 4, which is gated on an email connector being
available).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Priority = Literal["low", "medium", "high", "urgent"]


class EmailSummary(BaseModel):
    subject: str
    sender: str
    received_at: Optional[datetime] = None
    summary: Optional[str] = None
    priority: Priority = "medium"
    requires_action: bool = False
    suggested_action: Optional[str] = None
    # Optional link back to a portfolio.Project.reference, once that integration exists.
    related_project_reference: Optional[str] = None


class TriageResult(BaseModel):
    emails: list[EmailSummary] = Field(default_factory=list)


def triage_inbox() -> TriageResult:
    """
    Intended interface: connect to an inbox, summarize and prioritize incoming
    project emails, and flag ones needing action. Not implemented yet — gated
    on an email connector (Outlook/Gmail) being available (docs/ROADMAP.md
    Milestone 4).
    """
    raise NotImplementedError(
        "Email triage is not yet built (docs/ROADMAP.md Milestone 4) — gated on "
        "an inbox connector being available. This function's signature is the "
        "stable interface to build against."
    )
