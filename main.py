"""Entry point: builds and runs the LangGraph incident analysis pipeline."""

import logging
import sys

from dotenv import load_dotenv

import config
from pipeline.graph import build_graph


def main() -> None:
    """Run the incident analysis pipeline."""
    load_dotenv()

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    # Clear previous llm_calls.jsonl
    if config.LLM_CALLS_FILE.exists():
        config.LLM_CALLS_FILE.unlink()

    logger.info("Building pipeline graph")
    graph = build_graph()

    logger.info("Invoking pipeline")
    try:
        final_state = graph.invoke({})
        logger.info("Pipeline finished. Stage: %s", final_state.get("current_stage"))
        if final_state.get("errors"):
            logger.warning("Errors encountered: %s", final_state["errors"])
        logger.info("LLM calls logged: %d", len(final_state.get("llm_call_log", [])))
    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
