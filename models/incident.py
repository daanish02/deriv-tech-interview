"""Models for incident windows and metrics."""

from pydantic import BaseModel, Field


class IncidentWindow(BaseModel):
    """Time window for a single incident."""

    incident_id: str = Field(description="Incident identifier")
    first_warning: str = Field(description="Timestamp of first warning/anomaly")
    first_critical: str = Field(description="Timestamp of first critical event")
    final_recovery: str = Field(description="Timestamp of service recovery")
    incident_window_minutes: float = Field(description="Total window from warning to recovery")
    mttr_minutes: float = Field(description="Mean time to recovery from critical to recovery")


class IncidentMetrics(BaseModel):
    """Aggregated metrics for all incidents."""

    incidents: list[IncidentWindow] = Field(description="Per-incident window data")
    average_mttr_minutes: float = Field(description="Average MTTR across incidents")
