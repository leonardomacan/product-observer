"""File storage for captured network responses."""

import gzip
import json
from pathlib import Path

from product_observer.models.network import NetworkEvent


class FileStorage:
    """Persists captured network events and response bodies to disk."""

    def __init__(self, base_dir: Path, compress: bool = False) -> None:
        """Initialize storage.

        Args:
            base_dir: Directory for saved files (e.g. data/raw_requests).
            compress: If True, gzip response files.
        """
        self._base_dir = Path(base_dir)
        self._compress = compress
        self._counter = 0
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _next_filename(self) -> str:
        """Generate next deterministic filename."""
        self._counter += 1
        suffix = ".json.gz" if self._compress else ".json"
        return f"request_{self._counter:03d}{suffix}"

    def save_event(self, event: NetworkEvent, response_body: bytes) -> Path:
        """Save a network event and its response body to disk.

        Args:
            event: Network event metadata.
            response_body: Raw response body bytes.

        Returns:
            Path to the saved file.
        """
        filename = self._next_filename()
        filepath = self._base_dir / filename

        # Decode body as UTF-8 with fallback for binary
        try:
            body_text = response_body.decode("utf-8")
            # Try to parse as JSON for structured storage
            try:
                body_structured = json.loads(body_text)
            except json.JSONDecodeError:
                body_structured = body_text
        except UnicodeDecodeError:
            body_structured = f"<binary: {len(response_body)} bytes>"

        payload = {
            "metadata": event.to_metadata_dict(),
            "response_body": body_structured,
        }

        if self._compress:
            with gzip.open(filepath, "wt", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
        else:
            filepath.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

        return filepath
