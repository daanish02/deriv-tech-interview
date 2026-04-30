"""Deterministic incident window & MTTR calculator — no LLM calls."""

import json
import logging
from datetime import datetime

import config
from models.incident import IncidentWindow, IncidentMetrics
from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

TIMESTAMP_FMT = config.TIMESTAMP_FORMAT
WARNING_LEVELS = config.WARNING_LEVELS
CRITICAL_LEVELS = config.CRITICAL_LEVELS
RECOVERY_KEYWORDS = config.RECOVERY_KEYWORDS


def _parse_ts(ts_str: str) -> datetime:
    """Parse timestamp string to datetime.

    Args:
        ts_str: Timestamp like '2024-03-15 14:02:11 UTC'.

    Returns:
        datetime object.
    """
    return datetime.strptime(ts_str.strip(), TIMESTAMP_FMT)


def _compute_window(incident_id: str, entries: list[dict]) -> IncidentWindow:
    """Compute incident window from parsed log entries.

    Args:
        incident_id: Incident identifier.
        entries: List of parsed log entry dicts.

    Returns:
        IncidentWindow with computed timestamps and MTTR.
    """
    first_warning = None
    first_critical = None
    final_recovery = None

    for entry in entries:
        level = entry["level"]
        ts_str = entry["timestamp"]
        msg = entry["message"]

        if level in WARNING_LEVELS and first_warning is None:
            first_warning = ts_str

        if level in CRITICAL_LEVELS and first_critical is None:
            first_critical = ts_str

        if any(kw in msg for kw in RECOVERY_KEYWORDS):
            final_recovery = ts_str

    if not first_warning or not first_critical or not final_recovery:
        logger.error("Incomplete window data for %s", incident_id)
        first_warning = first_warning or entries[0]["timestamp"]
        first_critical = first_critical or first_warning
        final_recovery = final_recovery or entries[-1]["timestamp"]

    warn_dt = _parse_ts(first_warning)
    crit_dt = _parse_ts(first_critical)
    recov_dt = _parse_ts(final_recovery)

    window_mins = (recov_dt - warn_dt).total_seconds() / 60.0
    mttr_mins = (recov_dt - crit_dt).total_seconds() / 60.0

    return IncidentWindow(
        incident_id=incident_id,
        first_warning=first_warning,
        first_critical=first_critical,
        final_recovery=final_recovery,
        incident_window_minutes=round(window_mins, 2),
        mttr_minutes=round(mttr_mins, 2),
    )


def incident_windows_node(state: PipelineState) -> dict:
    """LangGraph node: compute incident windows and MTTR.

    Args:
        state: Pipeline state with parsed_logs.

    Returns:
        State update with incident_metrics and current_stage.
    """
    logger.info("Computing incident windows")
    parsed_logs = state["parsed_logs"]
    windows = []

    for incident_id, entries in parsed_logs.items():
        window = _compute_window(incident_id, entries)
        windows.append(window)
        logger.info("Window for %s: MTTR=%.1f min", incident_id, window.mttr_minutes)

    avg_mttr = sum(w.mttr_minutes for w in windows) / len(windows) if windows else 0
    metrics = IncidentMetrics(incidents=windows, average_mttr_minutes=round(avg_mttr, 2))

    metrics_dict = metrics.model_dump()
    config.INCIDENT_METRICS_FILE.write_text(
        json.dumps(metrics_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {"incident_metrics": metrics_dict, "current_stage": config.STAGE_WINDOWS_IDENTIFIED}
