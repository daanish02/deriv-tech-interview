"""Model for LLM call logging."""

from pydantic import BaseModel, Field


class LLMCallRecord(BaseModel):
    """Record of a single LLM invocation for llm_calls.jsonl."""

    stage: str = Field(description="Pipeline stage name")
    timestamp: str = Field(description="ISO timestamp of call")
    provider: str = Field(description="Provider: anthropic, openai")
    model: str = Field(description="Model name used")
    input_summary: str = Field(description="Brief summary of input")
    output_summary: str = Field(description="Brief summary of output")
    duration_seconds: float = Field(description="Call duration in seconds")
    success: bool = Field(description="Whether call succeeded")
    error: str | None = Field(default=None, description="Error message if failed")
