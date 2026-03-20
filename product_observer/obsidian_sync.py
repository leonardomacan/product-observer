from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

from .run_metadata import RunMeta


def _obsidian_base_url() -> Optional[str]:
    return os.environ.get("OBSIDIAN_API_BASE_URL", "").strip() or "http://127.0.0.1:27123/"


def _obsidian_api_key() -> Optional[str]:
    return os.environ.get("OBSIDIAN_API_KEY", "").strip() or None


def _obsidian_vault_folder() -> str:
    return os.environ.get("OBSIDIAN_VAULT_FOLDER", "product observer").strip() or "product observer"


def sync_narrative_to_obsidian(meta: RunMeta, narrative_path: Path) -> None:
    """Send the workflow_narratives.md content to the Obsidian vault.

    This uses Obsidian's local HTTP API. Failures are treated as non-fatal:
    they should not break the main observation pipeline.
    """
    base_url = _obsidian_base_url()
    api_key = _obsidian_api_key()
    if not base_url or not api_key:
        return

    if not narrative_path.is_file():
        return

    content = narrative_path.read_text(encoding="utf-8")
    if not content.strip():
        return

    note_name = f"{meta.target_system}_{meta.scenario}_{meta.run_id}.md"
    vault_folder = _obsidian_vault_folder()
    note_path = f"{vault_folder}/{note_name}"

    # Prepend a small metadata header for navigation.
    header = (
        f"---\n"
        f"target_system: {meta.target_system}\n"
        f"scenario: {meta.scenario}\n"
        f"run_id: {meta.run_id}\n"
        f"created_at: {meta.created_at.isoformat()}\n"
        f"---\n\n"
    )
    body = header + content

    # Obsidian Local REST API (as used by `brd-analyzer.html`) expects:
    #   PUT /vault/<encoded-note-path>
    # with the raw markdown content as the request body.
    #
    # Note: we must URL-encode the full note path because the vault folder
    # includes spaces.
    url = base_url.rstrip("/") + "/vault/" + quote(note_path, safe="")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "text/markdown",
    }

    try:
        requests.put(url, data=body, headers=headers, timeout=5)
    except Exception:
        # Intentionally swallow all errors here: Obsidian sync is best-effort.
        return

