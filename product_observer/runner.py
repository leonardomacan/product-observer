from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .config import get_settings
from .datasets import DatasetLayout, ensure_parent_dirs
from .run_metadata import RunMeta
from .artifacts import update_artifacts_for_run


logger = logging.getLogger("product_observer.runner")


def _copy_phase1_capture_to_run(layout: DatasetLayout) -> None:
    """Run Phase 1 capture into the per-run raw_requests directory.

    This function reuses the existing main.py capture entrypoint but points
    its storage to the run-specific raw_requests folder by temporarily
    overriding the OUTPUT_DIR setting via environment.
    """
    import os
    import subprocess
    import sys

    settings = get_settings()

    ensure_parent_dirs(layout.raw_requests_dir / "dummy")

    env = os.environ.copy()
    env["OUTPUT_DIR"] = str(layout.raw_requests_dir)
    env["TARGET_URL"] = settings.target_url

    logger.info(
        "STEP 1/4: Logging raw requests for scenario '%s' (system '%s')...",
        layout.scenario,
        layout.target_system,
    )
    # Run the existing main.py entrypoint in a subprocess so it can manage
    # Playwright and its own event loop as-is.
    subprocess.run(
        [sys.executable, "-m", "product_observer.main"],
        env=env,
        check=False,
    )


def _run_phase2(layout: DatasetLayout) -> None:
    """Execute Phase 2 into the run-specific phase2 directory."""
    from product_observer.phase2.run import main as phase2_main

    logger.info("STEP 2/4: Analyzing endpoints (Phase 2)...")

    # Monkey-patch sys.argv for the existing CLI-style entrypoint.
    import sys

    argv_backup = sys.argv[:]
    try:
        sys.argv = [
            "phase2",
            "--input",
            str(layout.raw_requests_dir),
            "--output",
            str(layout.phase2_dir),
        ]
        ensure_parent_dirs(layout.phase2_dir / "dummy")
        phase2_main()
    finally:
        sys.argv = argv_backup


def _run_phase3(layout: DatasetLayout) -> None:
    """Execute Phase 3 into the run-specific phase3 directory."""
    from product_observer.phase3.run import main as phase3_main

    logger.info("STEP 3/4: Running domain discovery (Phase 3)...")

    import sys

    argv_backup = sys.argv[:]
    try:
        input_path = layout.phase2_dir / "endpoints.json"
        sys.argv = [
            "phase3",
            "--input",
            str(input_path),
            "--output",
            str(layout.phase3_dir),
        ]
        ensure_parent_dirs(layout.phase3_dir / "dummy")
        phase3_main()
    finally:
        sys.argv = argv_backup


def _run_phase4(layout: DatasetLayout, *, no_llm: bool = False) -> Path:
    """Execute Phase 4 into the run-specific phase4 directory.

    Returns the path to workflow_narratives.md if written, else None.
    """
    from product_observer.phase4.run import main as phase4_main

    logger.info("STEP 4/4: Generating documentation and narratives (Phase 4)...")

    import sys

    argv_backup = sys.argv[:]
    try:
        input_path = layout.phase3_dir / "annotated_endpoints.json"
        sys.argv = [
            "phase4",
            "--input",
            str(input_path),
            "--output",
            str(layout.phase4_dir),
        ]
        if no_llm:
            sys.argv.append("--no-llm")
        ensure_parent_dirs(layout.phase4_dir / "dummy")
        phase4_main()
    finally:
        sys.argv = argv_backup

    narrative = layout.phase4_dir / "workflow_narratives.md"
    return narrative if narrative.is_file() else None


def _write_run_meta(layout: DatasetLayout, meta: RunMeta) -> None:
    """Persist run_meta.json into the run folder."""
    path = layout.run_root / "run_meta.json"
    ensure_parent_dirs(path)
    path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")


def run_observation(layout: DatasetLayout, meta: RunMeta, *, no_llm: bool = False) -> None:
    """Execute the full four-step observation pipeline for a single run."""
    logger.info(
        "Starting observation run %s for scenario '%s' on system '%s'.",
        meta.run_id,
        meta.scenario,
        meta.target_system,
    )

    # Step 1: capture
    _copy_phase1_capture_to_run(layout)
    meta.phases_completed.append("capture")
    _write_run_meta(layout, meta)
    logger.info("STEP 1/4 complete.")

    # Step 2: API intelligence
    _run_phase2(layout)
    meta.phases_completed.append("phase2")
    _write_run_meta(layout, meta)
    logger.info("STEP 2/4 complete.")

    # Step 3: domain discovery
    _run_phase3(layout)
    meta.phases_completed.append("phase3")
    _write_run_meta(layout, meta)
    logger.info("STEP 3/4 complete.")

    # Step 4: knowledge & documentation
    narrative_path = _run_phase4(layout, no_llm=no_llm)
    meta.phases_completed.append("phase4")
    _write_run_meta(layout, meta)
    logger.info("STEP 4/4 complete.")

    # Update aggregated artifacts for this target system.
    update_artifacts_for_run(layout)

    # After Phase 4, we can sync narratives to Obsidian (if configured)
    if narrative_path is not None:
        try:
            from .obsidian_sync import sync_narrative_to_obsidian

            sync_narrative_to_obsidian(meta, narrative_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Obsidian sync failed: %s", exc)

    logger.info(
        "Run %s completed. Outputs are under: %s",
        meta.run_id,
        layout.run_root,
    )


def inspect_run_summary(
    *,
    target_system: str,
    scenario: str,
    run_number: Optional[int] = None,
) -> int:
    """Print a concise summary of a run or scenario.

    Returns 0 on success, non-zero on error.
    """
    from .run_metadata import load_run_index, run_index_path
    from .config import get_settings

    settings = get_settings()
    index_file = run_index_path(settings.datasets_root, target_system)
    index = load_run_index(index_file, target_system=target_system)

    summary = index.scenarios.get(scenario)
    if summary is None or not summary.runs:
        logger.info(
            "No runs found for scenario '%s' on system '%s'.",
            scenario,
            target_system,
        )
        return 1

    if run_number is not None:
        meta = next((r for r in summary.runs if r.run_number == run_number), None)
        if meta is None:
            logger.info(
                "Run number %s not found for scenario '%s'.",
                run_number,
                scenario,
            )
            return 1
    else:
        meta = summary.latest_run
        if meta is None:
            logger.info(
                "No latest run available for scenario '%s'.",
                scenario,
            )
            return 1

    layout = DatasetLayout(
        datasets_root=settings.datasets_root,
        target_system=target_system,
        scenario=scenario,
        run_number=meta.run_number,
    )

    endpoints_count = _count_endpoints(layout.phase2_dir / "endpoints.json")
    workflows_info = _load_workflow_summary(layout.phase4_dir / "workflows.md")
    most_frequent_endpoint = workflows_info.get("most_frequent_endpoint")
    workflows_detected = workflows_info.get("workflows_detected", 0)

    logger.info("Run summary for %s", meta.run_id)
    logger.info("Target system : %s", meta.target_system)
    logger.info("Scenario      : %s", meta.scenario)
    logger.info("Target URL    : %s", meta.target_url)
    logger.info("Created at    : %s", meta.created_at.isoformat(timespec="seconds"))
    logger.info("Phases        : %s", ", ".join(meta.phases_completed) or "-")
    logger.info("Endpoints observed : %s", endpoints_count)
    logger.info("Workflows detected : %s", workflows_detected)
    if most_frequent_endpoint:
        logger.info("Most frequent endpoint: %s", most_frequent_endpoint)

    return 0


def _count_endpoints(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - defensive
        return 0
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict) and "endpoints" in data and isinstance(data["endpoints"], list):
        return len(data["endpoints"])
    return 0


def _load_workflow_summary(path: Path) -> dict:
    """Very lightweight heuristic over workflows.md to get counts and a frequent endpoint."""
    if not path.is_file():
        return {"workflows_detected": 0}

    text = path.read_text(encoding="utf-8")
    # Count headings that look like workflow names (e.g. '## Workflow: ...')
    workflows_detected = sum(1 for line in text.splitlines() if line.strip().startswith("## "))

    # Naively look for the first line that looks like an API path.
    most_frequent = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("/") and "/api" in stripped:
            most_frequent = stripped
            break

    return {
        "workflows_detected": workflows_detected,
        "most_frequent_endpoint": most_frequent,
    }

