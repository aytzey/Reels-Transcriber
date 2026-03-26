"""Output formatting — Markdown, plain text, JSON, and TXT file export."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from .transcriber import MODEL_NAME

_log = logging.getLogger("reels_transcriber.formatter")


def format_results(
    results: list[dict],
    title: str,
    output_dir: Path,
) -> tuple[str, str, str]:
    """Format transcription results and write export files.

    Returns
    -------
    markdown : str
        Full Markdown document for in-app display.
    json_path : str
        Path to the exported JSON file.
    txt_path : str
        Path to the exported plain-text file.
    """
    if not results:
        return "No results to display.", "", ""

    output_dir.mkdir(parents=True, exist_ok=True)

    md_parts: list[str] = []
    txt_parts: list[str] = []

    for idx, r in enumerate(results, 1):
        if not isinstance(r, dict):
            continue

        name = r.get("shortcode") or r.get("filename") or f"video_{idx}"
        date = r.get("date") or ""
        caption = r.get("caption") or ""
        url = r.get("url") or ""
        transcription = r.get("transcription") or "(no transcription)"

        md = f"### {idx}. {name}\n"
        if date:
            md += f"**Date:** {date}  \n"
        if caption:
            md += f"**Caption:** {caption}  \n"
        if url:
            md += f"**Link:** [{url}]({url})  \n"
        md += f"\n{transcription}\n\n---\n"
        md_parts.append(md)

        txt = f"[{idx}] {name}"
        if date:
            txt += f" ({date})"
        txt += "\n"
        if url:
            txt += f"Link: {url}\n"
        if caption:
            txt += f"Caption: {caption}\n"
        txt += f"\n{transcription}\n{'=' * 60}\n"
        txt_parts.append(txt)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    markdown = (
        f"# {title}\n\n"
        f"**Total:** {len(results)} videos  \n"
        f"**Model:** {MODEL_NAME}  \n"
        f"**Date:** {now}\n\n---\n\n"
        + "\n".join(md_parts)
    )

    plain = "\n".join(txt_parts)
    safe = _safe_filename(title)

    try:
        json_path = output_dir / f"{safe}_transcripts.json"
        json_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError as exc:
        _log.error("Failed to write JSON export: %s", exc)
        json_path = Path("")

    try:
        txt_path = output_dir / f"{safe}_transcripts.txt"
        txt_path.write_text(
            f"{title}\nTotal: {len(results)} videos\n"
            f"Model: {MODEL_NAME}\nDate: {now}\n{'=' * 60}\n\n{plain}",
            encoding="utf-8",
        )
    except OSError as exc:
        _log.error("Failed to write TXT export: %s", exc)
        txt_path = Path("")

    return markdown, str(json_path), str(txt_path)


def _safe_filename(title: str) -> str:
    """Convert a title string into a filesystem-safe name."""
    safe = re.sub(r"[^\w\s-]", "", title)
    safe = re.sub(r"\s+", "_", safe).strip("_")
    return safe[:50] or "export"
