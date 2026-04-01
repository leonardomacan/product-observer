from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import get_settings
from .datasets import DatasetLayout
from .run_metadata import (
    RunMeta,
    RunIndex,
    load_run_index,
    run_index_path,
    save_run_index,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="observe", description="Product Observer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    run_parser = subparsers.add_parser("run", help="Create and execute a new run for a scenario.")
    run_parser.add_argument("scenario", help="Scenario name (e.g. inbound_navigation).")
    run_parser.add_argument(
        "--target-system",
        dest="target_system",
        help="Logical target system name (e.g. WMS_BR). Defaults to TARGET_SYSTEM env or config.",
    )
    run_parser.add_argument(
        "--target-url",
        dest="target_url",
        help="Override TARGET_URL for this run.",
    )
    run_parser.add_argument(
        "--notes",
        dest="notes",
        help="Optional notes describing this run.",
    )

    # rerun
    rerun_parser = subparsers.add_parser("rerun", help="Rerun an existing scenario for the same target system.")
    rerun_parser.add_argument("scenario", help="Scenario name to rerun.")
    rerun_parser.add_argument(
        "--target-system",
        dest="target_system",
        help="Logical target system name. Defaults to TARGET_SYSTEM env or config.",
    )
    rerun_parser.add_argument(
        "--run-number",
        dest="run_number",
        type=int,
        help="Specific historical run number to base the rerun on (defaults to latest).",
    )
    rerun_parser.add_argument(
        "--override-url",
        dest="override_url",
        help="Override the target URL for the rerun.",
    )

    # list
    list_parser = subparsers.add_parser("list", help="List scenarios and runs for a target system.")
    list_parser.add_argument(
        "--target-system",
        dest="target_system",
        help="Logical target system name. Defaults to TARGET_SYSTEM env or config.",
    )
    list_parser.add_argument(
        "--scenario",
        dest="scenario",
        help="Filter by a single scenario name.",
    )
    list_parser.add_argument(
        "--runs",
        dest="show_runs",
        action="store_true",
        help="Show individual runs for the selected scenario.",
    )

    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a scenario (optionally a specific run).")
    inspect_parser.add_argument("scenario", help="Scenario name to inspect.")
    inspect_parser.add_argument(
        "--target-system",
        dest="target_system",
        help="Logical target system name. Defaults to TARGET_SYSTEM env or config.",
    )
    inspect_parser.add_argument(
        "--run-number",
        dest="run_number",
        type=int,
        help="Specific run number to inspect (defaults to latest).",
    )

    # reset
    reset_parser = subparsers.add_parser("reset", help="Delete runs and related data.")
    reset_parser.add_argument(
        "--target-system",
        dest="target_system",
        help="Logical target system name to reset. Defaults to TARGET_SYSTEM env or config.",
    )
    reset_parser.add_argument(
        "--scenario",
        dest="scenario",
        help="Scenario name to reset (within the target system).",
    )
    reset_parser.add_argument(
        "--all-scenarios",
        dest="all_scenarios",
        action="store_true",
        help="Reset all scenarios for the selected target system.",
    )
    reset_parser.add_argument(
        "--global",
        dest="global_reset",
        action="store_true",
        help="Reset all datasets for all target systems (dangerous).",
    )
    reset_parser.add_argument(
        "--browser-profile",
        dest="browser_profile",
        action="store_true",
        help="Also delete the browser_profile directory.",
    )
    reset_parser.add_argument(
        "--yes",
        dest="assume_yes",
        action="store_true",
        help="Do not prompt for confirmation.",
    )

    return parser


def _resolve_target_system(cli_value: Optional[str]) -> str:
    settings = get_settings()
    return cli_value or settings.target_system


def _load_index_for(target_system: str) -> RunIndex:
    settings = get_settings()
    index_file = run_index_path(settings.datasets_root, target_system)
    return load_run_index(index_file, target_system=target_system)


def _save_index_for(target_system: str, index: RunIndex) -> None:
    settings = get_settings()
    index_file = run_index_path(settings.datasets_root, target_system)
    save_run_index(index_file, index)


def _command_run(args: argparse.Namespace) -> int:
    settings = get_settings()
    target_system = _resolve_target_system(args.target_system)
    scenario = args.scenario

    index = _load_index_for(target_system)
    next_number = index.next_run_number(scenario)

    layout = DatasetLayout(
        datasets_root=settings.datasets_root,
        target_system=target_system,
        scenario=scenario,
        run_number=next_number,
    )

    target_url = args.target_url or settings.target_url
    meta = RunMeta.from_layout(
        layout,
        target_url=target_url,
        notes=args.notes,
    )

    # Orchestration is implemented in a dedicated module to keep CLI thin.
    from .runner import run_observation  # Imported here to avoid cycles.

    print(f"Creating run {meta.run_id} for scenario '{scenario}' on system '{target_system}'...")
    run_observation(layout=layout, meta=meta)

    index.add_run(meta)
    _save_index_for(target_system, index)
    return 0


def _command_rerun(args: argparse.Namespace) -> int:
    settings = get_settings()
    target_system = _resolve_target_system(args.target_system)
    scenario = args.scenario

    index = _load_index_for(target_system)
    summary = index.scenarios.get(scenario)
    if summary is None or not summary.runs:
        print(f"No existing runs found for scenario '{scenario}' on system '{target_system}'.")
        print("Use 'observe run' to create the first run.")
        return 1

    if args.run_number is not None:
        base_run = next((r for r in summary.runs if r.run_number == args.run_number), None)
        if base_run is None:
            print(f"Run number {args.run_number} not found for scenario '{scenario}'.")
            return 1
    else:
        base_run = summary.latest_run
        if base_run is None:
            print(f"No latest run available for scenario '{scenario}'.")
            return 1

    next_number = index.next_run_number(scenario)
    layout = DatasetLayout(
        datasets_root=settings.datasets_root,
        target_system=target_system,
        scenario=scenario,
        run_number=next_number,
    )

    target_url = args.override_url or base_run.target_url
    meta = RunMeta.from_layout(
        layout,
        target_url=target_url,
        notes=base_run.notes,
        tool_version=base_run.tool_version,
        tags=base_run.tags,
    )

    from .runner import run_observation

    print(
        f"Rerunning scenario '{scenario}' on system '{target_system}' "
        f"based on run {base_run.run_id} -> new run {meta.run_id}...",
    )
    run_observation(layout=layout, meta=meta)

    index.add_run(meta)
    _save_index_for(target_system, index)
    return 0


def _command_list(args: argparse.Namespace) -> int:
    target_system = _resolve_target_system(args.target_system)
    index = _load_index_for(target_system)

    if not index.scenarios:
        print(f"No runs found for target system '{target_system}'.")
        return 0

    scenario_filter = args.scenario
    show_runs: bool = bool(args.show_runs)

    print(f"Runs for target system '{target_system}':")
    print("SCENARIO               FIRST_RUN           LAST_RUN            RUNS")
    print("---------------------------------------------------------------------")

    for scenario, summary in sorted(index.scenarios.items(), key=lambda kv: kv[0]):
        if scenario_filter and scenario != scenario_filter:
            continue

        first = summary.first_run
        latest = summary.latest_run
        first_str = first.created_at.isoformat(timespec="seconds") if first else "-"
        latest_str = latest.created_at.isoformat(timespec="seconds") if latest else "-"
        print(f"{scenario:22} {first_str:20} {latest_str:20} {summary.run_count:4}")

        if show_runs and summary.runs:
            for r in sorted(summary.runs, key=lambda rr: rr.run_number):
                phases = ",".join(r.phases_completed) if r.phases_completed else "-"
                print(
                    f"  - {r.run_id:10}  "
                    f"{r.created_at.isoformat(timespec='seconds'):20}  "
                    f"phases=[{phases}]",
                )

    return 0


def _command_inspect(args: argparse.Namespace) -> int:
    from .runner import inspect_run_summary

    target_system = _resolve_target_system(args.target_system)
    scenario = args.scenario
    run_number = args.run_number

    return inspect_run_summary(
        target_system=target_system,
        scenario=scenario,
        run_number=run_number,
    )


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} (y/n) ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def _rm_tree(path: Path) -> None:
    if not path.exists():
        return
    # Local, controlled recursive removal.
    import shutil

    shutil.rmtree(path)


def _command_reset(args: argparse.Namespace) -> int:
    settings = get_settings()

    target_system_opt = args.target_system
    global_reset: bool = bool(args.global_reset)
    all_scenarios: bool = bool(args.all_scenarios)
    scenario_opt: Optional[str] = args.scenario
    assume_yes: bool = bool(args.assume_yes)
    reset_browser: bool = bool(args.browser_profile)

    datasets_root = settings.datasets_root

    if global_reset:
        prompt = (
            f"This will delete ALL datasets under {datasets_root} "
            "for all target systems."
        )
        if not assume_yes and not _confirm(prompt):
            print("Aborted.")
            return 1

        _rm_tree(datasets_root)
        if reset_browser:
            _rm_tree(settings.browser_profile_dir)
        print("Global reset completed.")
        return 0

    target_system = _resolve_target_system(target_system_opt)
    index = _load_index_for(target_system)

    if all_scenarios:
        prompt = (
            f"This will delete all runs for target system '{target_system}' "
            f"under {datasets_root}."
        )
        if not assume_yes and not _confirm(prompt):
            print("Aborted.")
            return 1

        system_root = datasets_root / target_system
        _rm_tree(system_root)
        if reset_browser:
            _rm_tree(settings.browser_profile_dir)
        print(f"Reset all scenarios for target system '{target_system}'.")
        return 0

    if not scenario_opt:
        print("reset: either --global, --all-scenarios, or --scenario must be provided.")
        return 1

    scenario = scenario_opt
    if scenario not in index.scenarios:
        print(f"No runs found for scenario '{scenario}' on system '{target_system}'. Nothing to reset.")
        return 0

    prompt = (
        f"This will delete all runs for scenario '{scenario}' on system '{target_system}'."
    )
    if not assume_yes and not _confirm(prompt):
        print("Aborted.")
        return 1

    scenario_root = datasets_root / target_system / "runs" / scenario
    _rm_tree(scenario_root)

    # Remove from index and save.
    index.scenarios.pop(scenario, None)
    _save_index_for(target_system, index)

    if reset_browser:
        _rm_tree(settings.browser_profile_dir)

    print(f"Reset scenario '{scenario}' on system '{target_system}'.")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    # So runner/phase INFO lines (e.g. STEP 1/4) appear without extra setup.
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    parser = _build_parser()
    args = parser.parse_args(argv)

    command = args.command
    if command == "run":
        return _command_run(args)
    if command == "rerun":
        return _command_rerun(args)
    if command == "list":
        return _command_list(args)
    if command == "inspect":
        return _command_inspect(args)
    if command == "reset":
        return _command_reset(args)

    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))

