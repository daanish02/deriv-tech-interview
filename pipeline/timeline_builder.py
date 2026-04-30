"""Stage 1 LLM node: timeline reconstruction (2 LLM calls)."""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

import config
from models.timeline import IncidentTimeline
from pipeline.llm_client import get_structured_llm, invoke_and_log
from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an SRE analyzing production incidents. Given parsed log entries, reconstruct a concise timeline.
Classify events into phases: normal, degradation, outage, mitigation, recovery, post-incident.
Be concise but technically precise. Include key observations."""


def timeline_builder_node(state: PipelineState) -> dict:
    """LangGraph node: build timelines for each incident via LLM.

    Args:
        state: Pipeline state with parsed_logs and incident_metrics.

    Returns:
        State update with timelines and llm_call_log entries.
    """
    logger.info("Building incident timelines (Stage 1 LLM)")
    llm = get_structured_llm(IncidentTimeline)
    parsed_logs = state["parsed_logs"]
    metrics = state.get("incident_metrics", {})
    timelines = []
    call_records = []

    for incident_id, entries in parsed_logs.items():
        user_content = (
            f"Incident ID: {incident_id}\n\n"
            f"Parsed log entries:\n{json.dumps(entries, indent=2)}\n\n"
            f"Incident metrics:\n{json.dumps(metrics, indent=2)}\n\n"
            "Reconstruct a detailed incident timeline with phases and key observations."
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
        result, record = invoke_and_log(
            llm, messages,
            stage=config.LLM_STAGE_TIMELINE,
            input_summary=f"Timeline for {incident_id} ({len(entries)} log entries)",
        )
        timelines.append(result.model_dump())
        call_records.append(record)
        logger.info("Timeline built for %s: %d events", incident_id, len(result.timeline))

    config.TIMELINES_FILE.write_text(
        json.dumps(timelines, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "timelines": timelines,
        "llm_call_log": call_records,
        "current_stage": config.STAGE_TIMELINES_RECONSTRUCTED,
    }
