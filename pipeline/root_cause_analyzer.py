"""Stage 2 LLM node: root cause analysis (1 combined call)."""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

import config
from models.root_cause import CrossIncidentAnalysis
from pipeline.llm_client import get_structured_llm, invoke_and_log
from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer performing root cause analysis.
Analyze the provided incident timelines, metrics, and historical incident database.
Identify root causes, contributing factors, common patterns, and systemic issues.
Correlate with historical incidents to identify recurring problems.

Use these root cause categories when applicable:
- missing_query_timeout: Queries running without timeout limits
- db_latency_cascade: DB latency causing cascading service failures
- missing_index_batch_job: Batch jobs triggering full table scans due to missing indexes
- connection_pool_exhaustion: Connection pool saturation
- circuit_breaker_failure: Circuit breaker issues
- scheduling_conflict: Batch jobs running during peak hours"""


def root_cause_analyzer_node(state: PipelineState) -> dict:
    """LangGraph node: perform cross-incident root cause analysis.

    Args:
        state: Pipeline state with timelines, metrics, parsed_logs.

    Returns:
        State update with root_cause_analysis and llm_call_log entry.
    """
    logger.info("Performing root cause analysis (Stage 2 LLM)")
    llm = get_structured_llm(CrossIncidentAnalysis)

    historical = json.loads(
        config.HISTORICAL_INCIDENTS_FILE.read_text(encoding="utf-8")
    )

    user_content = (
        f"Incident timelines:\n{json.dumps(state['timelines'], indent=2)}\n\n"
        f"Incident metrics:\n{json.dumps(state['incident_metrics'], indent=2)}\n\n"
        f"Historical incidents database:\n{json.dumps(historical, indent=2)}\n\n"
        "Perform a thorough cross-incident root cause analysis. "
        "Identify root causes, contributing factors, common patterns, "
        "systemic issues, and correlation with historical incidents."
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    result, record = invoke_and_log(
        llm, messages,
        stage=config.LLM_STAGE_ROOT_CAUSE,
        input_summary="Cross-incident root cause with historical correlation",
    )

    result_dict = result.model_dump()
    config.ROOT_CAUSE_FILE.write_text(
        json.dumps(result_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "root_cause_analysis": result_dict,
        "llm_call_log": [record],
        "current_stage": config.STAGE_ROOT_CAUSES_ANALYSED,
    }
