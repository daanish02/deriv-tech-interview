"""In-memory job registry for async pipeline runs.

Stores job state in a module-level dict guarded by a threading.Lock.
In production, swap the dict for a Redis or database backend so state
survives restarts and scales across multiple API workers.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from api.schemas import JobStatus


class JobRecord:
    """Mutable state for a single pipeline job.

    Uses __slots__ to reduce per-instance memory overhead.
    """

    __slots__ = (
        "job_id", "status", "current_stage", "errors",
        "llm_call_log", "created_at", "completed_at", "final_state",
    )

    def __init__(self, job_id: str) -> None:
        """Initialise a new job record in PENDING state.

        Args:
            job_id: UUID string identifying this job.
        """
        self.job_id = job_id
        self.status = JobStatus.PENDING
        self.current_stage: str | None = None
        self.errors: list[str] = []
        self.llm_call_log: list[dict] = []
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.final_state: dict[str, Any] | None = None

    def elapsed(self) -> float | None:
        """Seconds since job creation.

        Uses completed_at when available so the value is stable after the job ends.

        Returns:
            Elapsed time in seconds, or None if created_at is unset.
        """
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.created_at).total_seconds()


class JobStore:
    """Thread-safe registry mapping job IDs to JobRecord instances."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create(self) -> JobRecord:
        """Create a new job, add it to the registry, and return it.

        Returns:
            Newly created JobRecord in PENDING state.
        """
        job_id = str(uuid.uuid4())
        record = JobRecord(job_id)
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        """Retrieve a job by ID.

        Args:
            job_id: UUID string of the target job.

        Returns:
            JobRecord if found, else None.
        """
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs: Any) -> None:
        """Set one or more attributes on an existing job record.

        Args:
            job_id: UUID string of the target job.
            **kwargs: Attribute name/value pairs to apply.
        """
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            for k, v in kwargs.items():
                setattr(record, k, v)


# Module-level singleton shared across all requests in the same process.
# Replace with a distributed store (e.g. Redis) for multi-worker deployments.
store = JobStore()
