"""Optional stage: Predictive signal identification prompts."""

SYSTEM = "You are an SRE identifying predictive signals. Output JSON only."

USER_TEMPLATE = """Timelines:
{timelines}

Root cause:
{rca}

Identify early warning signals. For each: metric name, threshold, lead time, recommended alert. Valid JSON only."""
