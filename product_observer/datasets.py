from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetLayout:
    """Represents the high-level dataset layout for a single run.

    This is a thin, filesystem-focused helper built around the concepts of:
    - target_system: logical system name (e.g. WMS_BR)
    - scenario: scenario or flow name (e.g. inbound_navigation)
    - run_number: monotonically increasing integer per (target_system, scenario)

    It does not know how run numbers are allocated; that is the responsibility
    of the run metadata/index layer.
    """

    datasets_root: Path
    target_system: str
    scenario: str
    run_number: int

    @property
    def run_id(self) -> str:
        """Return the canonical run identifier for this run."""
        return f"run_{self.run_number:03d}"

    @property
    def target_system_root(self) -> Path:
        return self.datasets_root / self.target_system

    @property
    def runs_root(self) -> Path:
        return self.target_system_root / "runs"

    @property
    def artifacts_root(self) -> Path:
        return self.target_system_root / "artifacts"

    @property
    def knowledge_root(self) -> Path:
        return self.target_system_root / "knowledge"

    @property
    def scenario_root(self) -> Path:
        return self.runs_root / self.scenario

    @property
    def run_root(self) -> Path:
        return self.scenario_root / self.run_id

    # Per-run phase folders

    @property
    def raw_requests_dir(self) -> Path:
        """Directory for Phase 1 raw captures for this run."""
        return self.run_root / "raw_requests"

    @property
    def phase2_dir(self) -> Path:
        """Directory for Phase 2 outputs for this run."""
        return self.run_root / "phase2"

    @property
    def phase3_dir(self) -> Path:
        """Directory for Phase 3 outputs for this run."""
        return self.run_root / "phase3"

    @property
    def phase4_dir(self) -> Path:
        """Directory for Phase 4 outputs for this run."""
        return self.run_root / "phase4"


def ensure_parent_dirs(path: Path) -> None:
    """Create parent directories for a path if they do not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)

