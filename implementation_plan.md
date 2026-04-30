# AI-Powered Incident Analysis Pipeline — LangChain + LangGraph

## Decisions Made (from your feedback)

- **Primary LLM**: Claude Sonnet 4.6 via `langchain-anthropic`
- **Fallback chain**: Sonnet 4.6 → Sonnet 4.5 → OpenAI 5.4 → gpt-3.5-turbo
- **Framework**: LangChain (model init, structured output, prompts) + LangGraph (pipeline orchestration as a StateGraph)
- **Observability**: LangSmith tracing (already configured) + `llm_calls.jsonl`
- **Logging**: Python `logging` module throughout for debugging
- **No vector store needed** — historical DB fits in context

---

## Architecture

The pipeline is a **LangGraph StateGraph** where each node is a pipeline stage. State flows through the graph as a `TypedDict`. Deterministic nodes (parsing, windowing) run first with zero LLM calls. LLM nodes use LangChain's `ChatAnthropic.with_structured_output()` and `.with_fallbacks()`.

```
INIT → INPUTS_LOADED → LOGS_PARSED → INCIDENT_WINDOWS_IDENTIFIED
  → TIMELINES_RECONSTRUCTED → ROOT_CAUSES_ANALYSED → POSTMORTEMS_GENERATED
  → SYSTEMIC_ACTIONS_IDENTIFIED → OPTIONAL_ANALYSES_GENERATED
  → VALIDATION_COMPLETE → RESULTS_FINALISED
```

Each node reads from state, writes artifacts to disk, and updates state for the next node.

---

## Dependencies

```toml
dependencies = [
    "langchain-core>=0.3.0",
    "langchain-anthropic>=0.3.0",
    "langchain-openai>=0.3.0",
    "langgraph>=0.4.0",
    "pydantic>=2.11.0",
    "python-dotenv>=1.1.0",
    "langsmith>=0.3.0",
]
```

---

## Project Structure

```
deriv-tech-interview/
├── main.py                     # Entry: builds & runs the LangGraph StateGraph
├── config.py                   # All configurable vars, paths, model names
├── validate.py                 # Standalone validation script
├── pyproject.toml
├── pipeline/
│   ├── __init__.py
│   ├── state.py                # PipelineState TypedDict for LangGraph
│   ├── graph.py                # StateGraph construction (nodes + edges)
│   ├── log_parser.py           # Node: deterministic regex parsing
│   ├── incident_windows.py     # Node: deterministic window/MTTR calc
│   ├── timeline_builder.py     # Node: Stage 1 LLM (2 calls)
│   ├── root_cause_analyzer.py  # Node: Stage 2 LLM (1 combined call)
│   ├── postmortem_generator.py # Node: Stage 3 LLM (2 calls)
│   ├── systemic_actions.py     # Node: deterministic + optional LLM
│   ├── optional_analyses.py    # Node: MTTR, comms, taxonomy, signals
│   └── llm_client.py           # LangChain model init, fallbacks, logging
├── models/
│   ├── __init__.py
│   ├── log_entry.py            # ParsedLogEntry, ParsedFields
│   ├── incident.py             # IncidentWindow, IncidentMetrics
│   ├── timeline.py             # TimelineEntry, IncidentTimeline
│   ├── root_cause.py           # RootCauseResult, CrossIncidentAnalysis
│   ├── postmortem.py           # ActionItem, PostMortem sections
│   └── llm_call.py             # LLMCallRecord for llm_calls.jsonl
├── incident_a.log              # Input
├── incident_b.log              # Input
└── historical_incidents.json   # Input
```

---

## Key Module Designs

### `pipeline/state.py` — LangGraph State

```python
class PipelineState(TypedDict):
    current_stage: str
    incident_ids: list[str]
    raw_logs: dict[str, str]                    # {id: raw text}
    parsed_logs: dict[str, list[dict]]          # {id: parsed entries}
    incident_metrics: dict                       # windows + MTTR
    timelines: list[dict]                        # Stage 1 output
    root_cause_analysis: dict                    # Stage 2 output
    postmortems: dict[str, str]                  # {id: markdown}
    postmortem_action_items: dict[str, list]     # structured items
    systemic_actions: str                        # markdown
    optional_outputs: dict[str, str]             # {name: content}
    llm_call_log: list[dict]                     # accumulated call records
    validation_results: dict
    errors: list[str]
```

### `pipeline/graph.py` — StateGraph Construction

Builds the graph with `StateGraph(PipelineState)`, adds each stage as a node, connects with `add_edge()` in strict sequence. Compiles to a runnable graph.

### `pipeline/llm_client.py` — LangChain Model with Fallbacks

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

primary = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.2)
fallback_1 = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0.2)
fallback_2 = ChatOpenAI(model="gpt-5.4-2026-03-05", temperature=0.2)
fallback_3 = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

llm = primary.with_fallbacks([fallback_1, fallback_2, fallback_3])
```

For structured output: `llm.with_structured_output(PydanticSchema)` on each model before chaining fallbacks. Every call logs to `llm_calls.jsonl` via a wrapper that captures stage, timestamp, provider, model, prompt_hash, input/output artifacts.

### `pipeline/log_parser.py` — Deterministic (no LLM)

Regex parses each log line. Extracts `parsed_fields` (query_id, duration_ms, duration_seconds, table, pool_size, waiting, job_name, etc.). Saves to `parsed_logs/incident_*.json`.

### `pipeline/incident_windows.py` — Deterministic (no LLM)

Computes first_warning, first_critical, final_recovery, incident_window, MTTR from parsed timestamps. Saves to `incident_metrics.json`.

### `pipeline/timeline_builder.py` — Stage 1 (2 LLM calls)

Two separate calls, one per incident. Receives structured parsed records (not raw logs). Uses `with_structured_output(IncidentTimeline)`. Saves to `timelines.json`.

### `pipeline/root_cause_analyzer.py` — Stage 2 (1 LLM call)

One combined call with both timelines + metrics + historical DB + root cause vocabulary. Uses `with_structured_output(CrossIncidentAnalysis)`. Saves to `root_cause_analysis.json`.

### `pipeline/postmortem_generator.py` — Stage 3 (2 LLM calls)

Two separate calls. Each receives metrics, timeline, root cause, historical context. Outputs markdown with required sections. Saves to `postmortem_a.md`, `postmortem_b.md`. Also extracts structured action items for systemic analysis.

### `pipeline/systemic_actions.py` — Deterministic first, optional LLM

Compares action items across both postmortems using keyword/component overlap. Flags shared items. Saves to `systemic_actions.md`.

### `pipeline/optional_analyses.py` — SHOULD + STRETCH

MTTR analysis, communication drafts, failure mode taxonomy, predictive signals. Each is a separate LLM call. Saves respective output files.

---

## LLM Call Budget

| Stage | Calls | Logged as |
|-------|-------|-----------|
| Timeline Reconstruction | 2 | `timeline_reconstruction` |
| Root Cause Analysis | 1 | `root_cause_analysis` |
| Post-Mortem Generation | 2 | `postmortem_generation` |
| MTTR Analysis | 1 | `mttr_analysis` |
| Communication Drafts | 1 | `communication_drafts` |
| Failure Mode Taxonomy | 1 | `failure_mode_taxonomy` |
| Predictive Signals | 1 | `predictive_signals` |
| **Total** | **9** | All in `llm_calls.jsonl` |

---

## Verification Plan

```bash
uv run python main.py        # Full pipeline
uv run python validate.py    # Standalone validation
```

Validation checks: all artifacts exist, JSON valid, both incidents processed, stage ordering correct, action items reference named components, llm_calls.jsonl has all required records.
