"""Stage 2 LLM node: root cause analysis (1 combined call)."""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

import config
from models.root_cause import CrossIncidentAnalysis
from pipeline.llm_client import get_structured_llm, invoke_and_log
from pipeline.state import PipelineState
from prompts import root_cause_analysis as prompts

logger = logging.getLogger(__name__)


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

    user_content = prompts.USER_TEMPLATE.format(
        timelines=json.dumps(state["timelines"], indent=2),
        metrics=json.dumps(state["incident_metrics"], indent=2),
        historical=json.dumps(historical, indent=2),
    )

    messages = [
        SystemMessage(content=prompts.SYSTEM),
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
