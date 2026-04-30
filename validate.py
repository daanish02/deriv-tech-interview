"""Standalone validation script for pipeline outputs."""

import json
import logging
import sys

import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_ARTIFACTS = [
    (config.PARSED_LOGS_DIR / "incident_a.json", "Parsed logs for incident A"),
    (config.PARSED_LOGS_DIR / "incident_b.json", "Parsed logs for incident B"),
    (config.INCIDENT_METRICS_FILE, "Incident metrics"),
    (config.TIMELINES_FILE, "Timelines"),
    (config.ROOT_CAUSE_FILE, "Root cause analysis"),
    (config.POSTMORTEM_A_FILE, "Post-mortem A"),
    (config.POSTMORTEM_B_FILE, "Post-mortem B"),
    (config.SYSTEMIC_ACTIONS_FILE, "Systemic actions"),
    (config.LLM_CALLS_FILE, "LLM call log"),
]

OPTIONAL_ARTIFACTS = [
    (config.MTTR_ANALYSIS_FILE, "MTTR analysis"),
    (config.COMMUNICATIONS_FILE, "Communications"),
    (config.FAILURE_TAXONOMY_FILE, "Failure taxonomy"),
    (config.PREDICTIVE_SIGNALS_FILE, "Predictive signals"),
]

JSON_ARTIFACTS = [
    config.PARSED_LOGS_DIR / "incident_a.json",
    config.PARSED_LOGS_DIR / "incident_b.json",
    config.INCIDENT_METRICS_FILE,
    config.TIMELINES_FILE,
    config.ROOT_CAUSE_FILE,
]


def check_artifacts() -> list[str]:
    """Check all required artifacts exist and are non-empty.

    Returns:
        List of error strings for missing/empty artifacts.
    """
    errors = []
    for path, desc in REQUIRED_ARTIFACTS:
        if not path.exists():
            errors.append(f"MISSING: {desc} ({path.name})")
        elif path.stat().st_size == 0:
            errors.append(f"EMPTY: {desc} ({path.name})")
    return errors


def check_json_valid() -> list[str]:
    """Validate JSON files parse correctly.

    Returns:
        List of error strings for invalid JSON files.
    """
    errors = []
    for path in JSON_ARTIFACTS:
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                errors.append(f"INVALID JSON: {path.name}: {e}")
    return errors


def check_both_incidents() -> list[str]:
    """Verify both incidents processed in timelines and root cause.

    Returns:
        List of error strings for missing incidents.
    """
    errors = []
    if config.TIMELINES_FILE.exists():
        data = json.loads(config.TIMELINES_FILE.read_text(encoding="utf-8"))
        ids = {t["incident_id"] for t in data}
        for iid in config.INCIDENT_IDS:
            if iid not in ids:
                errors.append(f"MISSING INCIDENT in timelines: {iid}")

    if config.ROOT_CAUSE_FILE.exists():
        data = json.loads(config.ROOT_CAUSE_FILE.read_text(encoding="utf-8"))
        ids = {i["incident_id"] for i in data.get("incidents", [])}
        for iid in config.INCIDENT_IDS:
            if iid not in ids:
                errors.append(f"MISSING INCIDENT in root cause: {iid}")

    return errors


def check_llm_calls() -> list[str]:
    """Verify LLM call log has required stages.

    Returns:
        List of error strings for missing LLM stages.
    """
    errors = []
    if not config.LLM_CALLS_FILE.exists():
        return ["MISSING: llm_calls.jsonl"]

    stages_found = set()
    lines = config.LLM_CALLS_FILE.read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        try:
            record = json.loads(line)
            stages_found.add(record.get("stage", ""))
        except json.JSONDecodeError:
            errors.append("INVALID JSONL line in llm_calls.jsonl")

    for stage in config.REQUIRED_LLM_STAGES:
        if stage not in stages_found:
            errors.append(f"MISSING LLM STAGE: {stage}")

    return errors


REQUIRED_POSTMORTEM_SECTIONS = [
    "incident summary",
    "timeline",
    "root cause",
    "contributing factors",
    "severity classification",
    "action items",
    "recurrence risk",
]


def check_postmortem_sections() -> list[str]:
    """Verify post-mortems contain all required sections.

    Returns:
        List of error strings for missing sections.
    """
    errors = []
    for pm_file in [config.POSTMORTEM_A_FILE, config.POSTMORTEM_B_FILE]:
        if not pm_file.exists():
            errors.append(f"MISSING: {pm_file.name}")
            continue
        content = pm_file.read_text(encoding="utf-8").lower()
        for section in REQUIRED_POSTMORTEM_SECTIONS:
            if section not in content:
                errors.append(f"MISSING SECTION '{section}' in {pm_file.name}")
        # Severity classification must contain SEV1, SEV2, or SEV3
        if "sev1" not in content and "sev2" not in content and "sev3" not in content:
            errors.append(f"NO SEV classification (SEV1/SEV2/SEV3) in {pm_file.name}")
    return errors


def check_action_items() -> list[str]:
    """Verify post-mortems contain action items referencing specific components.

    Returns:
        List of error strings for missing action items.
    """
    errors = []
    for pm_file in [config.POSTMORTEM_A_FILE, config.POSTMORTEM_B_FILE]:
        if pm_file.exists():
            content = pm_file.read_text(encoding="utf-8")
            if "action items" not in content.lower():
                errors.append(f"NO ACTION ITEMS section in {pm_file.name}")
            # Check that action items reference specific components (table rows with |)
            table_rows = [
                line for line in content.splitlines()
                if line.strip().startswith("|") and "p0" in line.lower() or
                line.strip().startswith("|") and "p1" in line.lower() or
                line.strip().startswith("|") and "p2" in line.lower()
            ]
            if not table_rows:
                errors.append(f"NO action item table rows found in {pm_file.name}")
        else:
            errors.append(f"MISSING: {pm_file.name}")
    return errors


def check_communications() -> list[str]:
    """Verify communications.md contains both user-facing and engineering sections.

    Returns:
        List of error strings for missing communications sections.
    """
    errors = []
    if not config.COMMUNICATIONS_FILE.exists():
        return ["OPTIONAL MISSING: communications.md (skipping check)"]
    content = config.COMMUNICATIONS_FILE.read_text(encoding="utf-8").lower()
    required = [
        "user-facing status page update",
        "engineering leadership retrospective summary",
    ]
    for section in required:
        if section not in content:
            errors.append(f"MISSING communications section: '{section}'")
    return errors


def main() -> int:
    """Run all validation checks.

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    all_errors = []
    checks = [
        ("Artifact existence", check_artifacts),
        ("JSON validity", check_json_valid),
        ("Both incidents processed", check_both_incidents),
        ("LLM call log", check_llm_calls),
        ("Postmortem sections", check_postmortem_sections),
        ("Action items", check_action_items),
        ("Communications format", check_communications),
    ]

    for name, check_fn in checks:
        logger.info("Running: %s", name)
        errors = check_fn()
        if errors:
            for e in errors:
                logger.error("  %s", e)
        else:
            logger.info("  PASS")
        all_errors.extend(errors)

    # Optional artifacts (warn only)
    logger.info("Checking optional artifacts:")
    for path, desc in OPTIONAL_ARTIFACTS:
        if path.exists() and path.stat().st_size > 0:
            logger.info("  PRESENT: %s", desc)
        else:
            logger.warning("  OPTIONAL MISSING: %s", desc)

    print("\n" + "=" * 60)
    if all_errors:
        print(f"VALIDATION FAILED: {len(all_errors)} errors")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    else:
        print("VALIDATION PASSED: All checks OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
