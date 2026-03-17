from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from rich.console import Console

from .config import get_settings
from .datasets import DatasetLayout, ensure_parent_dirs
from .run_metadata import RunMeta
from .artifacts import update_artifacts_for_run


logger = logging.getLogger("product_observer.runner")
console = Console()


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

    console.print(
        f"[bold cyan]STEP 1/4[/bold cyan]: Logging raw requests for "
        f"scenario '{layout.scenario}' (system '{layout.target_system}')...",
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

    console.print("[bold cyan]STEP 2/4[/bold cyan]: Analyzing endpoints (Phase 2)...")

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

    console.print("[bold cyan]STEP 3/4[/bold cyan]: Running domain discovery (Phase 3)...")

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

    console.print("[bold cyan]STEP 4/4[/bold cyan]: Generating documentation and narratives (Phase 4)...")

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
    console.print(
        f"[bold]Starting observation run {meta.run_id}[/bold] "
        f"for scenario '{meta.scenario}' on system '{meta.target_system}'.",
    )

    # Step 1: capture
    _copy_phase1_capture_to_run(layout)
    meta.phases_completed.append("capture")
    _write_run_meta(layout, meta)
    console.print("[green]STEP 1/4 complete.[/green]")

    # Step 2: API intelligence
    _run_phase2(layout)
    meta.phases_completed.append("phase2")
    _write_run_meta(layout, meta)
    console.print("[green]STEP 2/4 complete.[/green]")

    # Step 3: domain discovery
    _run_phase3(layout)
    meta.phases_completed.append("phase3")
    _write_run_meta(layout, meta)
    console.print("[green]STEP 3/4 complete.[/green]")

    # Step 4: knowledge & documentation
    narrative_path = _run_phase4(layout, no_llm=no_llm)
    meta.phases_completed.append("phase4")
    _write_run_meta(layout, meta)
    console.print("[green]STEP 4/4 complete.[/green]")

    # Update aggregated artifacts for this target system.
    update_artifacts_for_run(layout)

    # After Phase 4, we can sync narratives to Obsidian (if configured)
    if narrative_path is not None:
        try:
            from .obsidian_sync import sync_narrative_to_obsidian

            sync_narrative_to_obsidian(meta, narrative_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Obsidian sync failed: %s", exc)

    console.print(
        f"[bold green]Run {meta.run_id} completed.[/bold green] "
        f"Outputs are under: {layout.run_root}",
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
        console.print(
            f"[yellow]No runs found for scenario '{scenario}' on system '{target_system}'.[/yellow]",
        )
        return 1

    if run_number is not None:
        meta = next((r for r in summary.runs if r.run_number == run_number), None)
        if meta is None:
            console.print(
                f"[yellow]Run number {run_number} not found for scenario '{scenario}'.[/yellow]",
            )
            return 1
    else:
        meta = summary.latest_run
        if meta is None:
            console.print(
                f"[yellow]No latest run available for scenario '{scenario}'.[/yellow]",
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

    console.print(f"[bold]Run summary for {meta.run_id}[/bold]")
    console.print(f"Target system : {meta.target_system}")
    console.print(f"Scenario      : {meta.scenario}")
    console.print(f"Target URL    : {meta.target_url}")
    console.print(f"Created at    : {meta.created_at.isoformat(timespec='seconds')}")
    console.print(f"Phases        : {', '.join(meta.phases_completed) or '-'}")
    console.print("")
    console.print(f"Endpoints observed : {endpoints_count}")
    console.print(f"Workflows detected : {workflows_detected}")
    if most_frequent_endpoint:
        console.print("Most frequent endpoint:")
        console.print(f"  {most_frequent_endpoint}")

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

