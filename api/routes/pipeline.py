"""Pipeline routes — trigger runs and query their status/results.

Async job pattern:
  POST /pipeline/run        → queues work, returns job_id immediately (202)
  GET  /pipeline/{id}/status → poll current stage and elapsed time
  GET  /pipeline/{id}/results → retrieve artifact paths once COMPLETED
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import config
from api.job_store import store, JobRecord
from api.schemas import (
    JobResultsResponse,
    JobStatus,
    JobStatusResponse,
    RunPipelineRequest,
    RunPipelineResponse,
)
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pipeline.graph import build_graph

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)

# Limits concurrent pipeline executions to avoid saturating the LLM rate limits.
_executor = ThreadPoolExecutor(max_workers=2)


def _run_pipeline(record: JobRecord) -> None:
    """Execute the full LangGraph pipeline and write results back to the job record.

    Runs in a background thread spawned by FastAPI's BackgroundTasks. Marks the
    job COMPLETED on success or FAILED (with error message) on any exception.

    Args:
        record: The JobRecord to update throughout execution.
    """
    store.update(record.job_id, status=JobStatus.RUNNING)
    try:
        graph = build_graph()
        final_state = graph.invoke({})

        store.update(
            record.job_id,
            status=JobStatus.COMPLETED,
            current_stage=final_state.get("current_stage"),
            errors=final_state.get("errors", []),
            llm_call_log=final_state.get("llm_call_log", []),
            final_state=final_state,
            completed_at=datetime.now(timezone.utc),
        )
        logger.info("Job %s completed", record.job_id)
    except Exception as exc:
        store.update(
            record.job_id,
            status=JobStatus.FAILED,
            errors=[str(exc)],
            completed_at=datetime.now(timezone.utc),
        )
        logger.exception("Job %s failed", record.job_id)


@router.post("/run", response_model=RunPipelineResponse, status_code=202)
def trigger_run(body: RunPipelineRequest, background_tasks: BackgroundTasks) -> RunPipelineResponse:
    """Queue a new pipeline run and return a job ID immediately.

    The pipeline executes asynchronously. Poll /pipeline/{job_id}/status
    to track progress, then call /pipeline/{job_id}/results when COMPLETED.

    Args:
        body: Optional run overrides (e.g. subset of incident IDs).
        background_tasks: FastAPI dependency that schedules the background job.

    Returns:
        RunPipelineResponse with job_id and initial PENDING status.
    """
    record = store.create()
    background_tasks.add_task(_run_pipeline, record)
    logger.info("Pipeline job queued: %s", record.job_id)
    return RunPipelineResponse(
        job_id=record.job_id,
        status=record.status,
        created_at=record.created_at,
    )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_status(job_id: str) -> JobStatusResponse:
    """Return the current status and pipeline stage for a job.

    Args:
        job_id: UUID of the target job.

    Returns:
        JobStatusResponse with status, current_stage, elapsed time, and any errors.

    Raises:
        HTTPException: 404 if the job_id is not found.
    """
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return JobStatusResponse(
        job_id=record.job_id,
        status=record.status,
        current_stage=record.current_stage,
        elapsed_seconds=record.elapsed(),
        errors=record.errors,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


@router.get("/{job_id}/results", response_model=JobResultsResponse)
def get_results(job_id: str) -> JobResultsResponse:
    """Return final results and artifact file paths for a completed job.

    Only available once the job reaches COMPLETED or FAILED status.
    Call /status first to avoid polling this endpoint prematurely.

    Args:
        job_id: UUID of the target job.

    Returns:
        JobResultsResponse with artifact paths, LLM call count, and errors.

    Raises:
        HTTPException: 404 if the job_id is not found.
        HTTPException: 202 if the job is still PENDING or RUNNING.
    """
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if record.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(status_code=202, detail="Job still running")

    # Map logical artifact names to filesystem paths for the caller.
    artifacts = {
        "parsed_logs_dir": str(config.PARSED_LOGS_DIR),
        "incident_metrics": str(config.INCIDENT_METRICS_FILE),
        "timelines": str(config.TIMELINES_FILE),
        "root_cause_analysis": str(config.ROOT_CAUSE_FILE),
        "postmortem_a": str(config.POSTMORTEM_A_FILE),
        "postmortem_b": str(config.POSTMORTEM_B_FILE),
        "systemic_actions": str(config.SYSTEMIC_ACTIONS_FILE),
        "llm_calls": str(config.LLM_CALLS_FILE),
        "mttr_analysis": str(config.MTTR_ANALYSIS_FILE),
        "communications": str(config.COMMUNICATIONS_FILE),
        "failure_taxonomy": str(config.FAILURE_TAXONOMY_FILE),
        "predictive_signals": str(config.PREDICTIVE_SIGNALS_FILE),
    }

    return JobResultsResponse(
        job_id=record.job_id,
        status=record.status,
        current_stage=record.current_stage,
        llm_calls_total=len(record.llm_call_log),
        errors=record.errors,
        artifacts=artifacts,
        elapsed_seconds=record.elapsed(),
    )
