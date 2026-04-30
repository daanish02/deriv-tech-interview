"""Optional analyses: MTTR, comms, taxonomy, predictive signals (4 LLM calls, parallel)."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import HumanMessage, SystemMessage

import config
from pipeline.llm_client import get_llm, invoke_and_log
from pipeline.state import PipelineState
from prompts import mttr_analysis as mttr_prompts
from prompts import communication_drafts as comms_prompts
from prompts import failure_taxonomy as taxonomy_prompts
from prompts import predictive_signals as signals_prompts

logger = logging.getLogger(__name__)


def _mttr_analysis(state: PipelineState) -> tuple[str, dict]:
    """Generate MTTR trend analysis via LLM.

    Args:
        state: Pipeline state with incident_metrics.

    Returns:
        Tuple of (markdown content, LLM call record dict).
    """
    llm = get_llm()
    historical = json.loads(
        config.HISTORICAL_INCIDENTS_FILE.read_text(encoding="utf-8")
    )
    metrics = state["incident_metrics"]

    messages = [
        SystemMessage(content=mttr_prompts.SYSTEM),
        HumanMessage(content=mttr_prompts.USER_TEMPLATE.format(
            metrics=json.dumps(metrics, indent=2),
            historical=json.dumps(historical, indent=2),
        )),
    ]
    result, record = invoke_and_log(
        llm,
        messages,
        stage=config.LLM_STAGE_MTTR,
        input_summary="MTTR trend analysis",
    )
    content = result.content if hasattr(result, "content") else str(result)
    config.MTTR_ANALYSIS_FILE.write_text(content, encoding="utf-8")
    return content, record


def _communication_drafts(state: PipelineState) -> tuple[str, dict]:
    """Generate incident communication drafts via LLM.

    Args:
        state: Pipeline state with postmortems.

    Returns:
        Tuple of (markdown content, LLM call record dict).
    """
    llm = get_llm()
    postmortem_context = "\n---\n".join(
        f"[{iid}]\n{pm[:config.POSTMORTEM_CONTEXT_MAX_LENGTH]}"
        for iid, pm in state.get("postmortems", {}).items()
    )
    messages = [
        SystemMessage(content=comms_prompts.SYSTEM),
        HumanMessage(content=comms_prompts.USER_TEMPLATE.format(
            postmortem_context=postmortem_context,
        )),
    ]
    result, record = invoke_and_log(
        llm,
        messages,
        stage=config.LLM_STAGE_COMMS,
        input_summary="Stakeholder communication drafts",
    )
    content = result.content if hasattr(result, "content") else str(result)
    config.COMMUNICATIONS_FILE.write_text(content, encoding="utf-8")
    return content, record


def _failure_taxonomy(state: PipelineState) -> tuple[str, dict]:
    """Generate failure mode taxonomy via LLM.

    Args:
        state: Pipeline state with root_cause_analysis.

    Returns:
        Tuple of (JSON content string, LLM call record dict).
    """
    llm = get_llm()
    rca = state["root_cause_analysis"]
    messages = [
        SystemMessage(content=taxonomy_prompts.SYSTEM),
        HumanMessage(content=taxonomy_prompts.USER_TEMPLATE.format(
            rca=json.dumps(rca, indent=2),
        )),
    ]
    result, record = invoke_and_log(
        llm,
        messages,
        stage=config.LLM_STAGE_TAXONOMY,
        input_summary="Failure mode taxonomy",
    )
    content = result.content if hasattr(result, "content") else str(result)
    # Try to extract JSON
    try:
        # Handle markdown code blocks
        text = content
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        parsed = json.loads(text)
        config.FAILURE_TAXONOMY_FILE.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except (json.JSONDecodeError, IndexError):
        config.FAILURE_TAXONOMY_FILE.write_text(
            json.dumps({"raw_output": content}, indent=2), encoding="utf-8"
        )
    return content, record


def _predictive_signals(state: PipelineState) -> tuple[str, dict]:
    """Identify predictive signals for early incident detection via LLM.

    Args:
        state: Pipeline state with timelines and root_cause_analysis.

    Returns:
        Tuple of (JSON content string, LLM call record dict).
    """
    llm = get_llm()
    messages = [
        SystemMessage(content=signals_prompts.SYSTEM),
        HumanMessage(content=signals_prompts.USER_TEMPLATE.format(
            timelines=json.dumps(state.get("timelines", []), indent=2),
            rca=json.dumps(state.get("root_cause_analysis", {}), indent=2),
        )),
    ]
    result, record = invoke_and_log(
        llm,
        messages,
        stage=config.LLM_STAGE_SIGNALS,
        input_summary="Predictive signal identification",
    )
    content = result.content if hasattr(result, "content") else str(result)
    try:
        text = content
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        parsed = json.loads(text)
        config.PREDICTIVE_SIGNALS_FILE.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except (json.JSONDecodeError, IndexError):
        config.PREDICTIVE_SIGNALS_FILE.write_text(
            json.dumps({"raw_output": content}, indent=2), encoding="utf-8"
        )
    return content, record


def optional_analyses_node(state: PipelineState) -> dict:
    """LangGraph node: run all optional analyses.

    Args:
        state: Pipeline state with all prior analysis data.

    Returns:
        State update with optional_outputs and llm_call_log.
    """
    logger.info("Running optional analyses (4 LLM calls in parallel)")
    optional_outputs: dict[str, str] = {}
    call_records = []

    analyses = [
        ("mttr_analysis", _mttr_analysis),
        ("communication_drafts", _communication_drafts),
        ("failure_mode_taxonomy", _failure_taxonomy),
        ("predictive_signals", _predictive_signals),
    ]

    with ThreadPoolExecutor(max_workers=config.PARALLEL_MAX_WORKERS) as executor:
        futures = {executor.submit(fn, state): name for name, fn in analyses}
        for future in as_completed(futures):
            name = futures[future]
            try:
                content, record = future.result()
                optional_outputs[name] = content
                call_records.append(record)
                logger.info("Completed optional analysis: %s", name)
            except Exception as e:
                logger.error("Failed optional analysis %s: %s", name, e)
                optional_outputs[name] = f"ERROR: {e}"

    return {
        "optional_outputs": optional_outputs,
        "llm_call_log": call_records,
        "current_stage": config.STAGE_OPTIONAL_ANALYSES_GENERATED,
    }
