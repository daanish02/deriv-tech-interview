"""Stage 1: Timeline reconstruction prompts."""

SYSTEM = """You are an SRE analyzing production incidents. Given parsed log entries, reconstruct a concise timeline.
Classify events into phases: normal, degradation, outage, mitigation, recovery, post-incident.
Be concise but technically precise. Include key observations."""

USER_TEMPLATE = """Incident ID: {incident_id}

Parsed log entries:
{log_entries}

Incident metrics:
{metrics}

Reconstruct a detailed incident timeline with phases and key observations."""
