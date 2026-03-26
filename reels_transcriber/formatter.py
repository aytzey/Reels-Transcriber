"""Output formatting — Markdown, plain text, JSON, and TXT file export."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .transcriber import MODEL_NAME


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
    md_parts: list[str] = []
    txt_parts: list[str] = []

    for idx, r in enumerate(results, 1):
        name = r.get("shortcode") or r.get("filename", f"video_{idx}")

        md = f"### {idx}. {name}\n"
        if r["date"]:
            md += f"**Date:** {r['date']}  \n"
        if r["caption"]:
            md += f"**Caption:** {r['caption']}  \n"
        if r["url"]:
            md += f"**Link:** [{r['url']}]({r['url']})  \n"
        md += f"\n{r['transcription']}\n\n---\n"
        md_parts.append(md)

        txt = f"[{idx}] {name}"
        if r["date"]:
            txt += f" ({r['date']})"
        txt += "\n"
        if r["url"]:
            txt += f"Link: {r['url']}\n"
        if r["caption"]:
            txt += f"Caption: {r['caption']}\n"
        txt += f"\n{r['transcription']}\n{'=' * 60}\n"
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
    safe = title.replace(" ", "_").replace("@", "").replace("/", "")[:50]

    json_path = output_dir / f"{safe}_transcripts.json"
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    txt_path = output_dir / f"{safe}_transcripts.txt"
    txt_path.write_text(
        f"{title}\nTotal: {len(results)} videos\n"
        f"Model: {MODEL_NAME}\nDate: {now}\n{'=' * 60}\n\n{plain}",
        encoding="utf-8",
    )

    return markdown, str(json_path), str(txt_path)
