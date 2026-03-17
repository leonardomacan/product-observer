from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .datasets import DatasetLayout


class RunMeta(BaseModel):
    """Metadata describing a single observational run."""

    target_system: str = Field(..., description="Logical name of the target system (e.g. WMS_BR).")
    scenario: str = Field(..., description="Scenario or flow name (e.g. inbound_navigation).")
    run_number: int = Field(..., ge=1, description="Monotonically increasing run number per (system, scenario).")
    run_id: str = Field(..., description="Canonical identifier (e.g. run_001).")

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the run was created (UTC).",
    )
    target_url: str = Field(..., description="Target URL used for this run.")
    notes: Optional[str] = Field(default=None, description="Optional free-form notes about this run.")
    tool_version: Optional[str] = Field(default=None, description="Optional tool version or git commit.")
    tags: List[str] = Field(default_factory=list, description="Optional list of tags.")

    phases_completed: List[str] = Field(
        default_factory=list,
        description="List of phases/steps successfully completed (e.g. ['capture', 'phase2', 'phase3', 'phase4']).",
    )

    class Config:
        extra = "ignore"

    @classmethod
    def from_layout(
        cls,
        layout: DatasetLayout,
        *,
        target_url: str,
        notes: Optional[str] = None,
        tool_version: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> "RunMeta":
        return cls(
            target_system=layout.target_system,
            scenario=layout.scenario,
            run_number=layout.run_number,
            run_id=layout.run_id,
            target_url=target_url,
            notes=notes,
            tool_version=tool_version,
            tags=tags or [],
        )

    @property
    def is_complete(self) -> bool:
        """Return True if all four phases have completed."""
        expected = {"capture", "phase2", "phase3", "phase4"}
        return expected.issubset(set(self.phases_completed))


class ScenarioSummary(BaseModel):
    """Aggregated view of runs for a single scenario within a target system."""

    scenario: str
    runs: List[RunMeta] = Field(default_factory=list)

    class Config:
        extra = "ignore"

    @property
    def run_count(self) -> int:
        return len(self.runs)

    @property
    def latest_run(self) -> Optional[RunMeta]:
        if not self.runs:
            return None
        # Sort by run_number, then created_at as tiebreaker.
        return sorted(self.runs, key=lambda r: (r.run_number, r.created_at))[-1]

    @property
    def first_run(self) -> Optional[RunMeta]:
        if not self.runs:
            return None
        return sorted(self.runs, key=lambda r: (r.run_number, r.created_at))[0]


class RunIndex(BaseModel):
    """Index grouping runs by scenario for a single target system."""

    target_system: str
    scenarios: Dict[str, ScenarioSummary] = Field(default_factory=dict)

    class Config:
        extra = "ignore"

    def next_run_number(self, scenario: str) -> int:
        """Return the next run number for the given scenario."""
        summary = self.scenarios.get(scenario)
        if summary is None or not summary.runs:
            return 1
        return max(r.run_number for r in summary.runs) + 1

    def add_run(self, meta: RunMeta) -> None:
        """Add or update a run in the index."""
        summary = self.scenarios.get(meta.scenario)
        if summary is None:
            summary = ScenarioSummary(scenario=meta.scenario, runs=[])
            self.scenarios[meta.scenario] = summary

        # Replace any existing run with same (scenario, run_number), else append.
        for idx, existing in enumerate(summary.runs):
            if existing.run_number == meta.run_number:
                summary.runs[idx] = meta
                break
        else:
            summary.runs.append(meta)


def load_run_index(path: Path, target_system: str) -> RunIndex:
    """Load a RunIndex from path if it exists, else return an empty index."""
    if not path.is_file():
        return RunIndex(target_system=target_system, scenarios={})

    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    return RunIndex.model_validate(data)


def save_run_index(path: Path, index: RunIndex) -> None:
    """Persist a RunIndex to disk as JSON."""
    from .datasets import ensure_parent_dirs

    import json

    ensure_parent_dirs(path)
    path.write_text(index.model_dump_json(indent=2), encoding="utf-8")


def run_index_path(datasets_root: Path, target_system: str) -> Path:
    """Return the path to the run index file for a target system."""
    return datasets_root / target_system / "runs" / "index.json"

