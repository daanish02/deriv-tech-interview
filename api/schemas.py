"""Pydantic request/response schemas for the API layer.

Kept separate from domain models in models/ so API contracts
can evolve independently of the pipeline data models.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Lifecycle states for an async pipeline job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RunPipelineRequest(BaseModel):
    """Optional overrides supplied when triggering a pipeline run."""

    incident_ids: list[str] | None = Field(
        default=None,
        description="Subset of incident IDs to process. Defaults to all configured incidents.",
    )


class RunPipelineResponse(BaseModel):
    """Returned immediately after a run is queued (HTTP 202)."""

    job_id: str
    status: JobStatus
    created_at: datetime


class JobStatusResponse(BaseModel):
    """Snapshot of a running or finished job — used for polling."""

    job_id: str
    status: JobStatus
    current_stage: str | None
    elapsed_seconds: float | None
    errors: list[str]
    created_at: datetime
    completed_at: datetime | None


class JobResultsResponse(BaseModel):
    """Full results returned once a job reaches COMPLETED or FAILED."""

    job_id: str
    status: JobStatus
    current_stage: str | None
    llm_calls_total: int
    errors: list[str]
    artifacts: dict[str, str]
    elapsed_seconds: float | None


class SearchRequest(BaseModel):
    """Semantic search query against the Pinecone failure taxonomy index."""

    query: str = Field(..., min_length=1, description="Natural language search query.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return.")


class SearchResult(BaseModel):
    """Single document returned from a vector similarity search."""

    content: str
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    """Semantic search response including cache hit indicator."""

    query: str
    results: list[SearchResult]
    cached: bool


class HealthResponse(BaseModel):
    """API liveness response."""

    status: str
    version: str
