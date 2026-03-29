"""Browser-based YouTube transcript fallback."""

from __future__ import annotations

import json
import shutil
import sys
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


_TRANSCRIPT_PANEL_IDS = {
    "PAmodern_transcript_view",
    "engagement-panel-searchable-transcript",
}


def _preferred_languages(language: str | None) -> list[str]:
    lowered = (language or "").strip().lower()
    if not lowered or lowered == "auto":
        return []

    options: list[str] = []
    for candidate in (
        lowered,
        lowered.replace("_", "-"),
        lowered.replace("-", "_"),
    ):
        if candidate and candidate not in options:
            options.append(candidate)

    base = lowered.replace("_", "-").split("-", 1)[0]
    if base and base not in options:
        options.append(base)
    if "en" not in options:
        options.append("en")
    return options


def _with_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query[key] = [value]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _parse_timestamp(value: str) -> float:
    value = value.strip()
    if not value:
        return 0.0
    total = 0.0
    for part in value.split(":"):
        if not part.isdigit():
            return 0.0
        total = total * 60 + int(part)
    return total


def _chrome_executable() -> str | None:
    for candidate in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _click_button_script() -> str:
    return """
() => {
  const findButton = (tokens) => Array.from(document.querySelectorAll('button')).find((el) => {
    const text = (el.textContent || '').trim().toLowerCase();
    const label = (el.getAttribute('aria-label') || '').trim().toLowerCase();
    return tokens.some((token) => text.includes(token) || label.includes(token));
  });

  const transcriptTokens = ['show transcript', 'transkripti goster', 'transkripti göster'];
  const moreTokens = ['show more', 'more', 'daha fazla goster', 'daha fazla göster'];

  let button = findButton(transcriptTokens);
  if (!button) {
    const moreButton = findButton(moreTokens);
    if (moreButton) {
      moreButton.click();
      button = findButton(transcriptTokens);
    }
  }
  if (!button) {
    return false;
  }
  button.click();
  return true;
}
"""


def _collect_segments_script() -> str:
    return """
() => Array.from(
  document.querySelectorAll('transcript-segment-view-model, ytd-transcript-segment-renderer')
).map((el) => {
  const timestamp = el.querySelector('.ytwTranscriptSegmentViewModelTimestamp, #timestamp, .segment-timestamp')?.textContent?.trim() || '';
  const textNode = el.querySelector('span[role="text"], .segment-text');
  let text = textNode?.textContent?.trim() || '';
  if (!text) {
    const childTexts = Array.from(el.children)
      .map((child) => child.textContent || '')
      .map((value) => value.trim())
      .filter(Boolean);
    text = childTexts[childTexts.length - 1] || '';
  }
  return { timestamp, text };
}).filter((item) => item.timestamp || item.text)
"""


def fetch_browser_transcript(video_id: str, preferred_language: str = "auto") -> dict:
    watch_url = _with_query_param(
        f"https://www.youtube.com/watch?v={video_id}",
        "hl",
        "en",
    )

    executable = _chrome_executable()
    launch_kwargs = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-dev-shm-usage"],
    }
    if executable:
        launch_kwargs["executable_path"] = executable

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_kwargs)
            page = browser.new_page(locale="en-US")
            page.goto(watch_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            if not page.evaluate(_click_button_script()):
                raise RuntimeError("YouTube transcript panel could not be opened in the browser fallback.")

            segment_count = 0
            for _ in range(60):
                segment_count = page.evaluate(
                    "document.querySelectorAll('transcript-segment-view-model, ytd-transcript-segment-renderer').length"
                )
                if segment_count > 0:
                    break
                page.wait_for_timeout(250)
            if segment_count <= 0:
                raise RuntimeError("YouTube transcript panel opened, but no transcript segments became available.")

            stable_rounds = 0
            previous_count = -1
            for _ in range(24):
                count = page.evaluate(
                    "document.querySelectorAll('transcript-segment-view-model, ytd-transcript-segment-renderer').length"
                )
                if count == previous_count:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                previous_count = count
                if stable_rounds >= 2:
                    break
                page.evaluate(
                    f"""
() => {{
  const panel = Array.from(document.querySelectorAll('ytd-engagement-panel-section-list-renderer')).find((el) =>
    {list(_TRANSCRIPT_PANEL_IDS)!r}.includes(el.getAttribute('target-id') || '')
  );
  if (!panel) return;
  panel.scrollBy(0, panel.scrollHeight);
  const content = panel.querySelector('#content');
  if (content) content.scrollBy(0, content.scrollHeight);
}}
"""
                )
                page.wait_for_timeout(250)

            raw_segments = page.evaluate(_collect_segments_script())
            browser.close()
    except PlaywrightTimeoutError as exc:
        raise RuntimeError("Timed out while waiting for the YouTube transcript panel.") from exc

    if not raw_segments:
        raise RuntimeError("YouTube transcript panel opened, but no transcript segments were found.")

    snippets: list[dict] = []
    for index, segment in enumerate(raw_segments):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = _parse_timestamp(str(segment.get("timestamp", "")))
        next_start = 0.0
        for follower in raw_segments[index + 1 :]:
            next_start = _parse_timestamp(str(follower.get("timestamp", "")))
            if next_start > start:
                break
            next_start = 0.0
        duration = round(max(next_start - start, 0.0), 2) if next_start else 0.0
        snippets.append({"text": text, "start": round(start, 2), "duration": duration})

    if not snippets:
        raise RuntimeError("YouTube transcript panel returned empty transcript segments.")

    language_codes = _preferred_languages(preferred_language)
    return {
        "snippets": snippets,
        "language_code": language_codes[0] if language_codes else "",
        "language": "YouTube browser transcript",
        "is_generated": False,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m reels_transcriber.youtube_browser_fallback <video_id> [language]")
    video_id = sys.argv[1]
    preferred_language = sys.argv[2] if len(sys.argv) > 2 else "auto"
    payload = fetch_browser_transcript(video_id, preferred_language=preferred_language)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
