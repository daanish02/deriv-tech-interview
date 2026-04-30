"""Deterministic systemic actions node — cross-references action items."""

import logging

import config
from pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def _find_common_actions(action_items: dict[str, list]) -> list[dict]:
    """Find common action items across incidents by component/keyword overlap.

    Args:
        action_items: Dict of incident_id -> list of action item dicts.

    Returns:
        List of common action groups.
    """
    all_items = []
    for incident_id, items in action_items.items():
        for item in items:
            all_items.append({**item, "source_incident": incident_id})

    # Group by component
    component_groups: dict[str, list] = {}
    for item in all_items:
        comp = item.get("component", "unknown").lower()
        component_groups.setdefault(comp, []).append(item)

    # Find shared (appear in >1 incident)
    common = []
    for comp, items in component_groups.items():
        source_incidents = set(i["source_incident"] for i in items)
        if len(source_incidents) > 1:
            common.append({
                "component": comp,
                "affected_incidents": sorted(source_incidents),
                "actions": items,
                "is_systemic": True,
            })

    # Also group by category keywords
    category_groups: dict[str, list] = {}
    for item in all_items:
        cat = item.get("category", "unknown").lower()
        category_groups.setdefault(cat, []).append(item)

    existing_comps = {c.get("component", "") for c in common}
    for cat, items in category_groups.items():
        source_incidents = set(i["source_incident"] for i in items)
        if len(source_incidents) > 1:
            unique_items = [i for i in items if i.get("component", "").lower() not in existing_comps]
            if unique_items:
                common.append({
                    "component": cat,
                    "category": cat,
                    "affected_incidents": sorted(source_incidents),
                    "actions": unique_items,
                    "is_systemic": True,
                })

    return common


def _render_systemic_md(common_actions: list[dict], action_items: dict[str, list]) -> str:
    """Render systemic actions to markdown.

    Args:
        common_actions: Common action groups.
        action_items: All action items by incident.

    Returns:
        Markdown string.
    """
    lines = [
        "# Systemic Actions — Cross-Incident Analysis",
        "",
        "## Overview",
        f"Analyzed action items across {len(action_items)} incidents.",
        f"Found {len(common_actions)} systemic action groups.",
        "",
    ]

    if common_actions:
        lines.append("## Systemic Issues (Shared Across Incidents)")
        lines.append("")
        for i, group in enumerate(common_actions, 1):
            label = group.get("component", group.get("category", "unknown"))
            lines.append(f"### {i}. {label.title()}")
            lines.append(f"**Affected incidents:** {', '.join(group['affected_incidents'])}")
            lines.append("")
            for action in group["actions"]:
                lines.append(f"- **[{action.get('priority', '?')}]** {action.get('title', 'N/A')}")
                lines.append(f"  - {action.get('description', '')}")
            lines.append("")

    lines.append("## All Action Items by Incident")
    lines.append("")
    for incident_id, items in action_items.items():
        lines.append(f"### {incident_id}")
        for item in items:
            lines.append(f"- **[{item.get('priority', '?')}]** {item.get('title', 'N/A')} ({item.get('component', 'N/A')})")
        lines.append("")

    return "\n".join(lines) + "\n"


def systemic_actions_node(state: PipelineState) -> dict:
    """LangGraph node: identify systemic actions across incidents.

    Args:
        state: Pipeline state with postmortem_action_items.

    Returns:
        State update with systemic_actions markdown.
    """
    logger.info("Identifying systemic actions")
    action_items = state.get("postmortem_action_items", {})
    common = _find_common_actions(action_items)
    md = _render_systemic_md(common, action_items)

    config.SYSTEMIC_ACTIONS_FILE.write_text(md, encoding="utf-8")
    logger.info("Systemic actions: %d common groups found", len(common))

    return {"systemic_actions": md, "current_stage": config.STAGE_SYSTEMIC_ACTIONS_IDENTIFIED}
