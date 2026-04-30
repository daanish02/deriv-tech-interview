"""Deterministic log parser node — no LLM calls."""

import json
import logging
import re
from pathlib import Path

import config
from models.log_entry import ParsedFields, ParsedLogEntry
from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

# Regex for log line format: [timestamp] LEVEL source message
LOG_LINE_RE = re.compile(
    r"\[(?P<timestamp>[^\]]+)\]\s+"
    r"(?P<level>INFO|WARN|ERROR|CRIT)\s+"
    r"(?P<source>\S+)\s+"
    r"(?P<message>.+)"
)

# Field extraction patterns
FIELD_PATTERNS = {
    "query_id": re.compile(r"query_id=(\S+)"),
    "duration_ms": re.compile(r"duration=(\d+)ms"),
    "duration_seconds": re.compile(r"duration=(\d+)s"),
    "table": re.compile(r"table=(\S+)"),
    "pool_size": re.compile(r"pool_size=(\d+)"),
    "waiting": re.compile(r"waiting=(\d+)"),
    "service": re.compile(r"service=(\S+)"),
    "timeout_ms": re.compile(r"timeout=(\d+)ms"),
    "p99_ms": re.compile(r"p99=(\d+)ms"),
}

JOB_NAME_RE = re.compile(r"(?:batch job|from batch job)\s+(\S+)")
INDEX_RE = re.compile(r"lacks index on\s+(.+?)(?:\s*—|\s*$)")


def _extract_fields(message: str) -> ParsedFields:
    """Extract structured fields from a log message.

    Args:
        message: Raw log message text.

    Returns:
        ParsedFields with extracted values.
    """
    fields: dict = {}
    for name, pattern in FIELD_PATTERNS.items():
        m = pattern.search(message)
        if m:
            val = m.group(1)
            if name in ("duration_ms", "pool_size", "waiting", "timeout_ms", "p99_ms"):
                fields[name] = int(val)
            elif name == "duration_seconds":
                fields[name] = float(val)
            else:
                fields[name] = val

    job_m = JOB_NAME_RE.search(message)
    if job_m:
        fields["job_name"] = job_m.group(1)

    idx_m = INDEX_RE.search(message)
    if idx_m:
        fields["missing_index"] = idx_m.group(1).strip()

    return ParsedFields(**fields)


def _parse_log_file(log_path: Path) -> list[ParsedLogEntry]:
    """Parse all lines from a log file.

    Args:
        log_path: Path to the .log file.

    Returns:
        List of ParsedLogEntry objects.
    """
    entries = []
    text = log_path.read_text(encoding="utf-8")
    for line in text.strip().splitlines():
        m = LOG_LINE_RE.match(line.strip())
        if not m:
            logger.warning("Unparseable line: %s", line)
            continue
        entry = ParsedLogEntry(
            timestamp=m.group("timestamp").strip(),
            level=m.group("level"),
            source=m.group("source"),
            message=m.group("message").strip(),
            parsed_fields=_extract_fields(m.group("message")),
        )
        entries.append(entry)
    return entries


def log_parser_node(state: PipelineState) -> dict:
    """LangGraph node: parse raw logs into structured entries.

    Args:
        state: Current pipeline state with raw_logs populated.

    Returns:
        State update with parsed_logs and current_stage.
    """
    logger.info("Starting log parsing")
    parsed_logs: dict[str, list[dict]] = {}

    config.PARSED_LOGS_DIR.mkdir(exist_ok=True)

    for incident_id, log_path in config.INCIDENT_LOG_MAP.items():
        entries = _parse_log_file(log_path)
        entries_dicts = [e.model_dump() for e in entries]
        parsed_logs[incident_id] = entries_dicts

        out_file = config.PARSED_LOGS_DIR / f"{incident_id}.json"
        out_file.write_text(
            json.dumps(entries_dicts, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Parsed %d entries from %s", len(entries), incident_id)

    return {"parsed_logs": parsed_logs, "current_stage": config.STAGE_LOGS_PARSED}
