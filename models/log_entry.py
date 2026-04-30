"""Models for parsed log entries."""

from pydantic import BaseModel, Field


class ParsedFields(BaseModel):
    """Extracted key-value fields from a log line."""

    query_id: str | None = Field(default=None, description="Query identifier if present")
    duration_ms: int | None = Field(default=None, description="Duration in milliseconds")
    duration_seconds: float | None = Field(default=None, description="Duration in seconds")
    table: str | None = Field(default=None, description="Database table name")
    pool_size: int | None = Field(default=None, description="Connection pool size")
    waiting: int | None = Field(default=None, description="Number of waiting connections")
    service: str | None = Field(default=None, description="Service name from field")
    timeout_ms: int | None = Field(default=None, description="Timeout value in ms")
    job_name: str | None = Field(default=None, description="Batch job name")
    p99_ms: int | None = Field(default=None, description="p99 latency in ms")
    missing_index: str | None = Field(default=None, description="Missing index columns")


class ParsedLogEntry(BaseModel):
    """Single parsed log line."""

    timestamp: str = Field(description="ISO-ish timestamp string")
    level: str = Field(description="Log level: INFO, WARN, ERROR, CRIT")
    source: str = Field(description="Service/component name")
    message: str = Field(description="Raw log message text")
    parsed_fields: ParsedFields = Field(default_factory=ParsedFields, description="Extracted fields")
