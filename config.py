"""Central configuration for the incident analysis pipeline.

All configurable variables, paths, model names, and constants live here
for single-source-of-truth management.
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
INCIDENT_A_LOG = PROJECT_ROOT / "incident_a.log"
INCIDENT_B_LOG = PROJECT_ROOT / "incident_b.log"
HISTORICAL_INCIDENTS_FILE = PROJECT_ROOT / "historical_incidents.json"

# Output directories / files
PARSED_LOGS_DIR = PROJECT_ROOT / "parsed_logs"
INCIDENT_METRICS_FILE = PROJECT_ROOT / "incident_metrics.json"
TIMELINES_FILE = PROJECT_ROOT / "timelines.json"
ROOT_CAUSE_FILE = PROJECT_ROOT / "root_cause_analysis.json"
POSTMORTEM_A_FILE = PROJECT_ROOT / "postmortem_a.md"
POSTMORTEM_B_FILE = PROJECT_ROOT / "postmortem_b.md"
SYSTEMIC_ACTIONS_FILE = PROJECT_ROOT / "systemic_actions.md"
MTTR_ANALYSIS_FILE = PROJECT_ROOT / "mttr_analysis.md"
COMMUNICATIONS_FILE = PROJECT_ROOT / "communications.md"
FAILURE_TAXONOMY_FILE = PROJECT_ROOT / "failure_mode_taxonomy.json"
PREDICTIVE_SIGNALS_FILE = PROJECT_ROOT / "predictive_signals.json"
LLM_CALLS_FILE = PROJECT_ROOT / "llm_calls.jsonl"

# ── Incident IDs ───────────────────────────────────────────────────────────
INCIDENT_IDS = ["incident_a", "incident_b"]
INCIDENT_LOG_MAP: dict[str, Path] = {
    "incident_a": INCIDENT_A_LOG,
    "incident_b": INCIDENT_B_LOG,
}

# ── Model Names ────────────────────────────────────────────────────────────
PRIMARY_MODEL = "claude-sonnet-4-5-20250929"
FALLBACK_MODEL_1 = "claude-haiku-4-5-20251001"
FALLBACK_MODEL_2 = "gpt-5.4-mini-2026-03-17"
FALLBACK_MODEL_3 = "gpt-4.1-nano"
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 8192
DEFAULT_PROVIDER = "anthropic"

# ── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ── Cache ──────────────────────────────────────────────────────────────────
LLM_CACHE_ENABLED = True
LLM_CACHE_DB = PROJECT_ROOT / ".llm_cache.db"
VECTOR_QUERY_CACHE_FILE = PROJECT_ROOT / ".vector_query_cache.json"

# ── Vector Store (Pinecone) ────────────────────────────────────────────────
PINECONE_INDEX_NAME = "failure-taxonomy"
PINECONE_NAMESPACE = "taxonomy"
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"
PINECONE_METRIC = "cosine"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
VECTOR_SEARCH_TOP_K = 5
METADATA_MAX_LENGTH = 500

# ── Pipeline Stages ────────────────────────────────────────────────────────
STAGE_INPUTS_LOADED = "INPUTS_LOADED"
STAGE_LOGS_PARSED = "LOGS_PARSED"
STAGE_WINDOWS_IDENTIFIED = "INCIDENT_WINDOWS_IDENTIFIED"
STAGE_TIMELINES_RECONSTRUCTED = "TIMELINES_RECONSTRUCTED"
STAGE_ROOT_CAUSES_ANALYSED = "ROOT_CAUSES_ANALYSED"
STAGE_POSTMORTEMS_GENERATED = "POSTMORTEMS_GENERATED"
STAGE_SYSTEMIC_ACTIONS_IDENTIFIED = "SYSTEMIC_ACTIONS_IDENTIFIED"
STAGE_OPTIONAL_ANALYSES_GENERATED = "OPTIONAL_ANALYSES_GENERATED"
STAGE_VECTOR_STORE_BUILT = "VECTOR_STORE_BUILT"
STAGE_RESULTS_FINALISED = "RESULTS_FINALISED"

# ── LLM Call Stage Names (for logging/validation) ─────────────────────────
LLM_STAGE_TIMELINE = "timeline_reconstruction"
LLM_STAGE_ROOT_CAUSE = "root_cause_analysis"
LLM_STAGE_POSTMORTEM = "postmortem_generation"
LLM_STAGE_MTTR = "mttr_analysis"
LLM_STAGE_COMMS = "communication_drafts"
LLM_STAGE_TAXONOMY = "failure_mode_taxonomy"
LLM_STAGE_SIGNALS = "predictive_signals"

REQUIRED_LLM_STAGES = {LLM_STAGE_TIMELINE, LLM_STAGE_ROOT_CAUSE, LLM_STAGE_POSTMORTEM}
OPTIONAL_LLM_STAGES = {LLM_STAGE_MTTR, LLM_STAGE_COMMS, LLM_STAGE_TAXONOMY, LLM_STAGE_SIGNALS}

# ── Numeric Constants ──────────────────────────────────────────────────────
PARALLEL_MAX_WORKERS = 4
OUTPUT_SUMMARY_MAX_LENGTH = 200
POSTMORTEM_CONTEXT_MAX_LENGTH = 500

# ── Log Parsing ────────────────────────────────────────────────────────────
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
WARNING_LEVELS = {"WARN", "ERROR", "CRIT"}
CRITICAL_LEVELS = {"CRIT"}
RECOVERY_KEYWORDS = {"resumed", "recovering", "CLOSED", "returning to normal"}

# ── Root Cause Categories ──────────────────────────────────────────────────
ROOT_CAUSE_CATEGORIES = [
    "missing_query_timeout",
    "db_latency_cascade",
    "missing_index_batch_job",
    "connection_pool_exhaustion",
    "circuit_breaker_failure",
    "scheduling_conflict",
]
