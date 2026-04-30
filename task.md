# Task List — Incident Analysis Pipeline

## Phase 1: Project Setup
- [ ] Update `pyproject.toml` with dependencies (langchain-core, langchain-anthropic, langchain-openai, langgraph, pydantic, python-dotenv, langsmith)
- [ ] Run `uv sync` to install dependencies
- [ ] Create `config.py` with all paths, model names, constants
- [ ] Update `.env.example` with required keys
- [ ] Set up Python `logging` configuration

## Phase 2: Pydantic Models (`models/`)
- [ ] `models/__init__.py`
- [ ] `models/log_entry.py` — ParsedFields, ParsedLogEntry
- [ ] `models/incident.py` — IncidentWindow, IncidentMetrics
- [ ] `models/timeline.py` — TimelineEntry, IncidentTimeline
- [ ] `models/root_cause.py` — RootCauseResult, CrossIncidentAnalysis
- [ ] `models/postmortem.py` — ActionItem, PostMortemSections
- [ ] `models/llm_call.py` — LLMCallRecord

## Phase 3: Pipeline Modules (`pipeline/`)
- [ ] `pipeline/__init__.py`
- [ ] `pipeline/state.py` — PipelineState TypedDict for LangGraph
- [ ] `pipeline/llm_client.py` — LangChain model init, fallbacks, call logging
- [ ] `pipeline/log_parser.py` — Deterministic regex parsing node
- [ ] `pipeline/incident_windows.py` — Deterministic window/MTTR node
- [ ] `pipeline/timeline_builder.py` — Stage 1 LLM node (2 calls)
- [ ] `pipeline/root_cause_analyzer.py` — Stage 2 LLM node (1 call)
- [ ] `pipeline/postmortem_generator.py` — Stage 3 LLM node (2 calls)
- [ ] `pipeline/systemic_actions.py` — Deterministic cross-reference node
- [ ] `pipeline/optional_analyses.py` — MTTR, comms, taxonomy, signals

## Phase 4: LangGraph Orchestration
- [ ] `pipeline/graph.py` — StateGraph construction, nodes, edges
- [ ] `main.py` — Entry point, loads env, builds graph, invokes

## Phase 5: Validation & Polish
- [ ] `validate.py` — Standalone validation script
- [ ] Run full pipeline end-to-end
- [ ] Run validation and fix issues
- [ ] Verify replayability (delete outputs, re-run, validate)
- [ ] Update `README.md` with setup + run instructions
