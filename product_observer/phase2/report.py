"""Build and write Phase 2 report: endpoints.json and optional api_surface.md."""

import json
from pathlib import Path
from typing import Any

from product_observer.phase2.schema_inference import infer_response_schema


def build_report(
    groups: dict[tuple[str, str], list[tuple[dict[str, Any], Any]]],
) -> list[dict[str, Any]]:
    """Build the list of endpoint entries (method, path, count, example_urls, response_schema)."""
    report: list[dict[str, Any]] = []
    for (method, normalized_path), records in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
        example_urls: list[str] = []
        seen_urls: set[str] = set()
        for metadata, _ in records[:5]:
            url = metadata.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                example_urls.append(url)

        response_schema = infer_response_schema(records)

        report.append({
            "method": method,
            "normalized_path": normalized_path,
            "request_count": len(records),
            "example_urls": example_urls,
            "response_schema": response_schema,
        })
    return report


def write_report(
    report: list[dict[str, Any]],
    output_dir: Path,
    *,
    write_markdown: bool = True,
) -> None:
    """Write endpoints.json and optionally api_surface.md to output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    endpoints_path = output_dir / "endpoints.json"
    with open(endpoints_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    if write_markdown:
        md_path = output_dir / "api_surface.md"
        md_lines = [
            "# API Surface (Phase 2)",
            "",
            "Endpoints inferred from captured requests.",
            "",
            "| Method | Path | Count |",
            "|--------|------|-------|",
        ]
        for entry in report:
            md_lines.append(
                f"| {entry['method']} | `{entry['normalized_path']}` | {entry['request_count']} |"
            )
        md_lines.append("")
        md_lines.append("## Response schemas")
        md_lines.append("")
        for entry in report:
            md_lines.append(f"### {entry['method']} {entry['normalized_path']}")
            md_lines.append("")
            md_lines.append("```json")
            md_lines.append(json.dumps(entry["response_schema"], indent=2, default=str))
            md_lines.append("```")
            md_lines.append("")
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
