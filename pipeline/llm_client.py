"""LLM client with fallback chain, SQLite caching, and call logging."""

import json
import logging
import time
from datetime import datetime, timezone

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_core.language_models import BaseChatModel

import config
from models.llm_call import LLMCallRecord

logger = logging.getLogger(__name__)

_cache_initialized = False


def _init_cache() -> None:
    """Initialize LLM cache if enabled. Uses SQLite for disk persistence."""
    global _cache_initialized
    if _cache_initialized:
        return
    if not config.LLM_CACHE_ENABLED:
        _cache_initialized = True
        return
    try:
        from langchain_community.cache import SQLiteCache
        set_llm_cache(SQLiteCache(database_path=str(config.LLM_CACHE_DB)))
        logger.info("LLM cache enabled: SQLite at %s", config.LLM_CACHE_DB)
    except ImportError:
        logger.info("langchain-community not installed, using in-memory cache")
        set_llm_cache(InMemoryCache())
    _cache_initialized = True


def get_llm() -> BaseChatModel:
    """Build primary LLM with fallback chain.

    Returns:
        BaseChatModel with fallbacks configured.
    """
    _init_cache()
    primary = ChatAnthropic(
        model=config.PRIMARY_MODEL,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )
    fallback_1 = ChatAnthropic(
        model=config.FALLBACK_MODEL_1,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )
    fallback_2 = ChatOpenAI(
        model=config.FALLBACK_MODEL_2,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )
    fallback_3 = ChatOpenAI(
        model=config.FALLBACK_MODEL_3,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )
    return primary.with_fallbacks([fallback_1, fallback_2, fallback_3])


def get_structured_llm(schema):
    """Build LLM with structured output and fallbacks.

    Args:
        schema: Pydantic model class for structured output.

    Returns:
        Runnable that outputs structured Pydantic objects.
    """
    _init_cache()
    primary = ChatAnthropic(
        model=config.PRIMARY_MODEL,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    ).with_structured_output(schema)
    fallback_1 = ChatAnthropic(
        model=config.FALLBACK_MODEL_1,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    ).with_structured_output(schema)
    fallback_2 = ChatOpenAI(
        model=config.FALLBACK_MODEL_2,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    ).with_structured_output(schema)
    fallback_3 = ChatOpenAI(
        model=config.FALLBACK_MODEL_3,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    ).with_structured_output(schema)
    return primary.with_fallbacks([fallback_1, fallback_2, fallback_3])


def log_llm_call(
    stage: str,
    input_summary: str,
    output_summary: str,
    duration: float,
    success: bool,
    model: str = "",
    provider: str = "",
    error: str | None = None,
) -> dict:
    """Log an LLM call to llm_calls.jsonl and return record dict.

    Args:
        stage: Pipeline stage name.
        input_summary: Brief input description.
        output_summary: Brief output description.
        duration: Call duration in seconds.
        success: Whether call succeeded.
        model: Model name used.
        provider: Provider name.
        error: Error message if failed.

    Returns:
        Dict representation of the call record.
    """
    record = LLMCallRecord(
        stage=stage,
        timestamp=datetime.now(timezone.utc).isoformat(),
        provider=provider or config.DEFAULT_PROVIDER,
        model=model or config.PRIMARY_MODEL,
        input_summary=input_summary,
        output_summary=output_summary,
        duration_seconds=round(duration, 3),
        success=success,
        error=error,
    )
    with open(config.LLM_CALLS_FILE, "a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")
    logger.info("LLM call logged: stage=%s duration=%.2fs success=%s", stage, duration, success)
    return record.model_dump()


def invoke_and_log(llm, messages, stage: str, input_summary: str) -> tuple:
    """Invoke LLM, log call, return (result, record_dict).

    Args:
        llm: LangChain runnable (with or without structured output).
        messages: List of messages to send.
        stage: Pipeline stage for logging.
        input_summary: Brief description of input.

    Returns:
        Tuple of (llm_result, call_record_dict).
    """
    start = time.time()
    try:
        result = llm.invoke(messages)
        duration = time.time() - start
        output_summary = str(result)[:config.OUTPUT_SUMMARY_MAX_LENGTH]
        record = log_llm_call(
            stage=stage,
            input_summary=input_summary,
            output_summary=output_summary,
            duration=duration,
            success=True,
        )
        return result, record
    except Exception as e:
        duration = time.time() - start
        record = log_llm_call(
            stage=stage,
            input_summary=input_summary,
            output_summary="",
            duration=duration,
            success=False,
            error=str(e),
        )
        raise
