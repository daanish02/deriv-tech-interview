"""Models for incident timeline reconstruction."""

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    """Single event in an incident timeline."""

    timestamp: str = Field(description="Event timestamp")
    phase: str = Field(description="Phase: normal, degradation, outage, mitigation, recovery, post-incident")
    component: str = Field(description="Affected component/service")
    event: str = Field(description="Human-readable event description")
    severity: str = Field(description="INFO, WARN, ERROR, CRIT")
    technical_detail: str = Field(default="", description="Technical detail or evidence")


class IncidentTimeline(BaseModel):
    """Complete timeline for one incident."""

    incident_id: str = Field(description="Incident identifier")
    summary: str = Field(description="Brief summary of the incident")
    timeline: list[TimelineEntry] = Field(description="Ordered timeline entries")
    key_observations: list[str] = Field(description="Key observations from log analysis")
