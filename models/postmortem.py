"""Models for post-mortem generation."""

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """Single action item from a post-mortem."""

    title: str = Field(description="Action item title")
    description: str = Field(description="Detailed description")
    priority: str = Field(description="P0, P1, P2, P3")
    owner_team: str = Field(description="Responsible team")
    component: str = Field(description="Affected component/service")
    category: str = Field(description="Category: prevention, detection, response, recovery")


class PostMortemSections(BaseModel):
    """Structured post-mortem output."""

    incident_id: str = Field(description="Incident identifier")
    title: str = Field(description="Post-mortem title")
    executive_summary: str = Field(description="Brief executive summary")
    impact: str = Field(description="Impact description")
    timeline_summary: str = Field(description="Condensed timeline")
    root_cause: str = Field(description="Root cause explanation")
    contributing_factors: list[str] = Field(description="Contributing factors")
    action_items: list[ActionItem] = Field(description="Recommended action items")
    lessons_learned: list[str] = Field(description="Key lessons learned")
