"""LangGraph pipeline state definition."""

from typing import Annotated, TypedDict
from operator import add


class PipelineState(TypedDict, total=False):
    """State flowing through the LangGraph StateGraph."""

    current_stage: str
    incident_ids: list[str]
    raw_logs: dict[str, str]
    parsed_logs: dict[str, list[dict]]
    incident_metrics: dict
    timelines: list[dict]
    root_cause_analysis: dict
    postmortems: dict[str, str]
    postmortem_action_items: dict[str, list]
    systemic_actions: str
    optional_outputs: dict[str, str]
    llm_call_log: Annotated[list[dict], add]
    validation_results: dict
    errors: Annotated[list[str], add]
