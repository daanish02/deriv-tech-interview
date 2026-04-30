"""LangGraph StateGraph construction — nodes and edges."""

import json
import logging

from langgraph.graph import StateGraph, END

import config
from pipeline.state import PipelineState
from pipeline.log_parser import log_parser_node
from pipeline.incident_windows import incident_windows_node
from pipeline.timeline_builder import timeline_builder_node
from pipeline.root_cause_analyzer import root_cause_analyzer_node
from pipeline.postmortem_generator import postmortem_generator_node
from pipeline.systemic_actions import systemic_actions_node
from pipeline.optional_analyses import optional_analyses_node
from pipeline.vector_store import build_taxonomy_index

logger = logging.getLogger(__name__)


def load_inputs_node(state: PipelineState) -> dict:
    """LangGraph node: load raw logs and historical data into state.

    Args:
        state: Initial (empty) pipeline state.

    Returns:
        State update with raw_logs, incident_ids, current_stage.
    """
    logger.info("Loading inputs")
    raw_logs = {}
    for incident_id, log_path in config.INCIDENT_LOG_MAP.items():
        raw_logs[incident_id] = log_path.read_text(encoding="utf-8")
        logger.info("Loaded %s (%d bytes)", incident_id, len(raw_logs[incident_id]))

    return {
        "raw_logs": raw_logs,
        "incident_ids": config.INCIDENT_IDS,
        "current_stage": config.STAGE_INPUTS_LOADED,
        "errors": [],
        "llm_call_log": [],
    }


def finalize_node(state: PipelineState) -> dict:
    """LangGraph node: log summary and mark pipeline complete.

    Args:
        state: Pipeline state with all analysis results.

    Returns:
        State update with current_stage set to RESULTS_FINALISED.
    """
    logger.info("Pipeline complete")
    logger.info("LLM calls made: %d", len(state.get("llm_call_log", [])))
    logger.info("Errors: %d", len(state.get("errors", [])))

    # Write final summary
    summary = {
        "stages_completed": state.get("current_stage", ""),
        "incidents_processed": state.get("incident_ids", []),
        "llm_calls_total": len(state.get("llm_call_log", [])),
        "errors": state.get("errors", []),
        "artifacts": {
            "parsed_logs": str(config.PARSED_LOGS_DIR),
            "incident_metrics": str(config.INCIDENT_METRICS_FILE),
            "timelines": str(config.TIMELINES_FILE),
            "root_cause_analysis": str(config.ROOT_CAUSE_FILE),
            "postmortem_a": str(config.POSTMORTEM_A_FILE),
            "postmortem_b": str(config.POSTMORTEM_B_FILE),
            "systemic_actions": str(config.SYSTEMIC_ACTIONS_FILE),
            "llm_calls": str(config.LLM_CALLS_FILE),
        },
    }
    logger.info("Summary: %s", json.dumps(summary, indent=2))

    return {"current_stage": config.STAGE_RESULTS_FINALISED}


def build_vector_store_node(state: PipelineState) -> dict:
    """LangGraph node: index failure taxonomy into Pinecone.

    Args:
        state: Pipeline state (taxonomy file must exist on disk).

    Returns:
        State update with current_stage (and errors on failure).
    """
    logger.info("Building taxonomy vector store")
    try:
        build_taxonomy_index()
    except Exception as e:
        logger.error("Vector store build failed (non-fatal): %s", e)
        return {"errors": [f"vector_store: {e}"], "current_stage": config.STAGE_VECTOR_STORE_BUILT}
    return {"current_stage": config.STAGE_VECTOR_STORE_BUILT}


def build_graph() -> StateGraph:
    """Build the incident analysis pipeline graph.

    Returns:
        Compiled LangGraph StateGraph ready to invoke.
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("load_inputs", load_inputs_node)
    graph.add_node("parse_logs", log_parser_node)
    graph.add_node("compute_windows", incident_windows_node)
    graph.add_node("build_timelines", timeline_builder_node)
    graph.add_node("analyze_root_cause", root_cause_analyzer_node)
    graph.add_node("generate_postmortems", postmortem_generator_node)
    graph.add_node("identify_systemic_actions", systemic_actions_node)
    graph.add_node("run_optional_analyses", optional_analyses_node)
    graph.add_node("build_vector_store", build_vector_store_node)
    graph.add_node("finalize", finalize_node)

    # Set entry point
    graph.set_entry_point("load_inputs")

    # Add edges (strict sequential)
    graph.add_edge("load_inputs", "parse_logs")
    graph.add_edge("parse_logs", "compute_windows")
    graph.add_edge("compute_windows", "build_timelines")
    graph.add_edge("build_timelines", "analyze_root_cause")
    graph.add_edge("analyze_root_cause", "generate_postmortems")
    graph.add_edge("generate_postmortems", "identify_systemic_actions")
    graph.add_edge("identify_systemic_actions", "run_optional_analyses")
    graph.add_edge("run_optional_analyses", "build_vector_store")
    graph.add_edge("build_vector_store", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
