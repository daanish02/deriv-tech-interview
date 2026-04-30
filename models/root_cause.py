"""Models for root cause analysis."""

from pydantic import BaseModel, Field


class RootCauseResult(BaseModel):
    """Root cause analysis for a single incident."""

    incident_id: str = Field(description="Incident identifier")
    root_cause: str = Field(description="Identified root cause")
    root_cause_category: str = Field(description="Category: missing_query_timeout, db_latency_cascade, missing_index_batch_job, etc.")
    contributing_factors: list[str] = Field(description="Contributing factors")
    evidence: list[str] = Field(description="Evidence from logs supporting the analysis")
    similar_historical: list[str] = Field(description="IDs of similar historical incidents")


class CrossIncidentAnalysis(BaseModel):
    """Combined root cause analysis across all incidents."""

    incidents: list[RootCauseResult] = Field(description="Per-incident root cause results")
    common_patterns: list[str] = Field(description="Patterns shared across incidents")
    systemic_issues: list[str] = Field(description="Underlying systemic issues identified")
    historical_correlation: str = Field(description="How current incidents relate to historical ones")
