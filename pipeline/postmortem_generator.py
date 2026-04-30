"""Stage 3 LLM node: post-mortem generation (2 LLM calls — one per incident)."""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

import config
from pipeline.llm_client import get_llm, invoke_and_log
from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an SRE writing a concise post-mortem in markdown. Include these sections:
# Post-Mortem: [Title]
**Incident ID:** [id]
## Executive Summary
2-3 sentences.
## Impact
1-2 sentences.
## Timeline Summary
Condensed key events as bullet list.
## Root Cause
1 paragraph.
## Contributing Factors
- bullet list
## Action Items
| Priority | Title | Component | Owner | Category |
|----------|-------|-----------|-------|----------|
Include 3-5 rows. Priority: P0-P3. Category: prevention/detection/response/recovery.
## Lessons Learned
- 2-3 bullets
Be concise but technically detailed. Reference concrete components/services in action items."""

POSTMORTEM_FILES = {
    "incident_a": config.POSTMORTEM_A_FILE,
    "incident_b": config.POSTMORTEM_B_FILE,
}

# Regex to extract action items from markdown table
ACTION_ITEM_RE = re.compile(
    r"\|\s*(P[0-3])\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|"
)


def _extract_action_items(md: str) -> list[dict]:
    """Extract action items from markdown table.

    Args:
        md: Markdown post-mortem text.

    Returns:
        List of action item dicts.
    """
    items = []
    for m in ACTION_ITEM_RE.finditer(md):
        items.append({
            "title": m.group(2).strip(),
            "description": m.group(2).strip(),
            "priority": m.group(1).strip(),
            "owner_team": m.group(4).strip(),
            "component": m.group(3).strip(),
            "category": m.group(5).strip(),
        })
    return items


def postmortem_generator_node(state: PipelineState) -> dict:
    """LangGraph node: generate post-mortems (1 LLM call per incident, markdown output).

    Args:
        state: Pipeline state with timelines, root_cause_analysis, incident_metrics.

    Returns:
        State update with postmortems, postmortem_action_items, llm_call_log.
    """
    logger.info("Generating post-mortems (Stage 3 LLM)")
    llm = get_llm()
    rca = state["root_cause_analysis"]
    timelines = state["timelines"]
    metrics = state["incident_metrics"]

    historical = json.loads(
        config.HISTORICAL_INCIDENTS_FILE.read_text(encoding="utf-8")
    )

    postmortems: dict[str, str] = {}
    action_items: dict[str, list] = {}
    call_records = []

    for timeline in timelines:
        incident_id = timeline["incident_id"]
        incident_rca = next(
            (i for i in rca.get("incidents", []) if i["incident_id"] == incident_id),
            {},
        )
        user_content = (
            f"Incident ID: {incident_id}\n\n"
            f"Timeline:\n{json.dumps(timeline, indent=2)}\n\n"
            f"Root Cause Analysis:\n{json.dumps(incident_rca, indent=2)}\n\n"
            f"Metrics:\n{json.dumps(metrics, indent=2)}\n\n"
            f"Historical Incidents:\n{json.dumps(historical, indent=2)}\n\n"
            "Generate the post-mortem report."
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
        result, record = invoke_and_log(
            llm, messages,
            stage=config.LLM_STAGE_POSTMORTEM,
            input_summary=f"Post-mortem for {incident_id}",
        )

        md = result.content if hasattr(result, "content") else str(result)
        call_records.append(record)

        # Save markdown
        out_file = POSTMORTEM_FILES.get(incident_id)
        if out_file:
            out_file.write_text(md, encoding="utf-8")
        postmortems[incident_id] = md

        # Extract action items from markdown table (no extra LLM call)
        items = _extract_action_items(md)
        action_items[incident_id] = items
        logger.info("Post-mortem generated for %s: %d action items extracted", incident_id, len(items))

    return {
        "postmortems": postmortems,
        "postmortem_action_items": action_items,
        "llm_call_log": call_records,
        "current_stage": config.STAGE_POSTMORTEMS_GENERATED,
    }
