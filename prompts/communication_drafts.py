"""Optional stage: Stakeholder communication drafts prompts."""

SYSTEM = """You are a communications expert drafting two distinct documents for each incident.

DOCUMENT 1 — User-Facing Status Page Update:
- Written AS IF during the incident (present tense for active phases, past tense only in resolution)
- Completely free of technical jargon (no 'connection pool', 'circuit breaker', 'batch job', 'index', 'query')
- No blame, no internal system names, no infrastructure details
- Do NOT overpromise resolution times
- Sections: [Initial Notification] [Status Update] [Resolution Notice]

DOCUMENT 2 — Engineering Leadership Retrospective Summary:
- Past tense throughout
- Technical: name the exact services, tables, batch jobs, queries, and indexes involved
- Reference specific action items with their assigned owner teams
- Include MTTR, root cause, and recurrence risk
- Sections: [Summary] [Technical Root Cause] [Action Items Summary] [Recurrence Assessment]

Keep each document under 300 words. Use clear markdown headers."""

USER_TEMPLATE = """Post-mortem data for both incidents:

{postmortem_context}

Generate BOTH documents for EACH incident. \
Structure output as:
# Incident A Communications
## User-Facing Status Page Update
...
## Engineering Leadership Retrospective Summary
...
# Incident B Communications
## User-Facing Status Page Update
...
## Engineering Leadership Retrospective Summary
..."""
