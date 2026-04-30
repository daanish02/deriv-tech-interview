"""Optional stage: Failure mode taxonomy prompts."""

SYSTEM = "You are an SRE creating failure taxonomies. Output JSON only."

USER_TEMPLATE = """Root cause analysis:
{rca}

Create concise failure mode taxonomy JSON: categories, failure modes, detection, prevention. Valid JSON only."""
