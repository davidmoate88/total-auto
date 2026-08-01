"""
Data model + interface stub for the meeting-minutes domain: transcript in,
structured minutes and actions out.

ARCHITECTURE STUB: `extract_minutes()` defines the intended interface and
raises NotImplementedError — no transcript-processing logic exists yet (see
docs/ROADMAP.md Milestone 2). The point of committing the interface now is so
downstream code (the eventual reminders mechanism, portfolio linkage) can be
written against a stable shape.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Attendee(BaseModel):
    name: str
    organisation: Optional[str] = None
    role: Optional[str] = None


class ActionItem(BaseModel):
    description: str
    owner: Optional[str] = None
    due_date: Optional[date] = None
    status: str = Field("open", description="open / in_progress / done / blocked")
    # Optional link back to a portfolio.Project.reference, once that integration exists.
    related_project_reference: Optional[str] = None


class MeetingMinutes(BaseModel):
    title: str
    date: Optional[date] = None
    attendees: list[Attendee] = Field(default_factory=list)
    topics_discussed: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    actions: list[ActionItem] = Field(default_factory=list)


class TranscriptInput(BaseModel):
    meeting_title: str
    meeting_date: Optional[date] = None
    raw_text: str


def extract_minutes(transcript: TranscriptInput) -> MeetingMinutes:
    """
    Intended interface: turn a raw transcript into structured minutes with
    extracted actions (owner + due date where stated). Not implemented yet —
    this is the extension point Milestone 2 will build against.
    """
    raise NotImplementedError(
        "Transcript -> minutes extraction is not yet built (docs/ROADMAP.md Milestone 2). "
        "This function's signature is the stable interface to build against."
    )
