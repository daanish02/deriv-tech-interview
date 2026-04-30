"""Optional analyses: MTTR, comms, taxonomy, predictive signals (4 LLM calls, parallel)."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import HumanMessage, SystemMessage

import config
from pipeline.llm_client import get_llm, invoke_and_log
from pipeline.state import PipelineState

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
        SystemMessage(content="You are an SRE analyzing MTTR trends. Be concise."),
        HumanMessage(
            content=(
                f"Current metrics:\n{json.dumps(metrics, indent=2)}\n\n"
                f"Historical:\n{json.dumps(historical, indent=2)}\n\n"
                "Compare current vs historical MTTR. Identify trends and improvements. Markdown, keep under 500 words."
            )
        ),
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
    messages = [
        SystemMessage(content="You are a communications expert. Be concise."),
        HumanMessage(
            content=(
                "Incident summaries:\n"
                + "\n---\n".join(
                    pm[:config.POSTMORTEM_CONTEXT_MAX_LENGTH] for pm in state.get("postmortems", {}).values()
                )
                + "\n\nDraft brief stakeholder comms for each incident: "
                "initial notification, status update, resolution notice. Markdown, keep each under 200 words."
            )
        ),
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
        SystemMessage(
            content="You are an SRE creating failure taxonomies. Output JSON only."
        ),
        HumanMessage(
            content=(
                f"Root cause analysis:\n{json.dumps(rca, indent=2)}\n\n"
                "Create concise failure mode taxonomy JSON: categories, failure modes, detection, prevention. Valid JSON only."
            )
        ),
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
        SystemMessage(
            content="You are an SRE identifying predictive signals. Output JSON only."
        ),
        HumanMessage(
            content=(
                f"Timelines:\n{json.dumps(state.get('timelines', []), indent=2)}\n\n"
                f"Root cause:\n{json.dumps(state.get('root_cause_analysis', {}), indent=2)}\n\n"
                "Identify early warning signals. For each: metric name, threshold, lead time, recommended alert. Valid JSON only."
            )
        ),
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
