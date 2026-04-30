"""Artifact retrieval routes — serve pipeline output files over HTTP.

All output files produced by the pipeline are addressable by a short logical
name (e.g. "postmortem_a", "timelines"). JSON files are returned as JSON,
Markdown and JSONL as plain text, and anything else as a raw file download.
"""

import json
import logging

import config
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])
logger = logging.getLogger(__name__)

# Maps logical artifact names to filesystem paths from config.
# Add new entries here when the pipeline produces additional output files.
_ARTIFACT_MAP: dict[str, object] = {
    "incident_metrics": config.INCIDENT_METRICS_FILE,
    "timelines": config.TIMELINES_FILE,
    "root_cause_analysis": config.ROOT_CAUSE_FILE,
    "postmortem_a": config.POSTMORTEM_A_FILE,
    "postmortem_b": config.POSTMORTEM_B_FILE,
    "systemic_actions": config.SYSTEMIC_ACTIONS_FILE,
    "mttr_analysis": config.MTTR_ANALYSIS_FILE,
    "communications": config.COMMUNICATIONS_FILE,
    "failure_taxonomy": config.FAILURE_TAXONOMY_FILE,
    "predictive_signals": config.PREDICTIVE_SIGNALS_FILE,
    "llm_calls": config.LLM_CALLS_FILE,
    "parsed_logs_a": config.PARSED_LOGS_DIR / "incident_a.json",
    "parsed_logs_b": config.PARSED_LOGS_DIR / "incident_b.json",
}


@router.get("")
def list_artifacts() -> JSONResponse:
    """List all known artifact names with existence and size information.

    Returns:
        JSON object mapping each artifact name to its existence flag and
        file size in bytes (0 if not yet generated).
    """
    result = {
        name: {
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        for name, path in _ARTIFACT_MAP.items()
    }
    return JSONResponse(content=result)


@router.get("/{name}")
def get_artifact(name: str):
    """Serve a named pipeline output artifact.

    Content-type is inferred from the file extension:
    - .json  → application/json (parsed and re-serialised for pretty printing)
    - .md / .jsonl / .txt → text/plain
    - anything else → application/octet-stream (file download)

    Args:
        name: Logical artifact name (e.g. "postmortem_a", "timelines").

    Returns:
        The artifact content in the appropriate content-type.

    Raises:
        HTTPException: 404 if the name is unrecognised or the file does not exist yet.
    """
    path = _ARTIFACT_MAP.get(name)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown artifact '{name}'. Available: {list(_ARTIFACT_MAP)}",
        )
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact '{name}' not yet generated")

    suffix = path.suffix.lower()
    if suffix == ".json":
        return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))
    if suffix in (".md", ".jsonl", ".txt"):
        return PlainTextResponse(content=path.read_text(encoding="utf-8"))
    return FileResponse(path=str(path))
