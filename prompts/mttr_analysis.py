"""Optional stage: MTTR trend analysis prompts."""

SYSTEM = "You are an SRE analyzing MTTR trends. Be concise."

USER_TEMPLATE = """Current metrics:
{metrics}

Historical:
{historical}

Compare current vs historical MTTR. Identify trends and improvements. Markdown, keep under 500 words."""
