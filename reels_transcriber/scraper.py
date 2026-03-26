"""
Instagram Reels scraper using headless Playwright.

Downloads all public video Reels from a given Instagram profile without
requiring authentication.  Uses a third-party web service (igram.world) as
an intermediary to:

1. **List posts** — profile URL -> paginated GraphQL post edges
2. **Resolve download URLs** — each reel shortcode -> signed proxy CDN URL
3. **Download** — fetch video bytes through the proxy CDN

The proxy CDN layer (media.igram.world) is critical in environments where
direct access to Instagram's CDN (scontent-*.cdninstagram.com) is blocked
by corporate firewalls or SSL-inspecting proxies (e.g. Fortinet).  Playwright
runs with ``ignore_https_errors=True`` so self-signed intercepting
certificates don't break the flow.

All network I/O runs through a single Playwright browser context, keeping
cookies and TLS state consistent across the session.
"""

from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_log = logging.getLogger("reels_transcriber.scraper")


# ---------------------------------------------------------------------------
# Single reel download
# ---------------------------------------------------------------------------

def download_single_reel(
    reel_url: str,
    out_dir: Path,
) -> dict | None:
    """Download a single Instagram Reel by URL.

    Uses igram.world ``/api/convert`` to resolve a proxy CDN link, then
    downloads the video through the Playwright browser context.

    Returns a dict with ``path``, ``shortcode``, ``date``, ``caption``, ``url``
    or None on failure.
    """
    from playwright.sync_api import sync_playwright
    import re

    out_dir.mkdir(parents=True, exist_ok=True)

    m = re.search(r"/(?:reel|p)/([A-Za-z0-9_-]+)", reel_url)
    shortcode = m.group(1) if m else "unknown"

    browser = None
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            captured: list[dict] = []

            def _on_response(resp):
                url = resp.url
                if "/api/" in url and "google" not in url and "sentry" not in url:
                    try:
                        captured.append({"url": url, "body": resp.json()})
                    except Exception:
                        pass

            page.on("response", _on_response)

            page.goto("https://igram.world/en1/", timeout=30_000)
            page.wait_for_selector("#search-form-input", timeout=15_000)
            page.locator("#search-form-input").fill(reel_url)

            with page.expect_response(
                lambda r: "convert" in r.url, timeout=20_000
            ):
                page.keyboard.press("Enter")

            proxy_url = _find_proxy_url(captured)
            if not proxy_url:
                _log.warning("No proxy URL found for reel %s", shortcode)
                return None

            body = _download_with_retry(context, proxy_url)
            if not body or len(body) < 1_000:
                _log.warning("Download too small or empty for reel %s", shortcode)
                return None

        except Exception as exc:
            _log.error("Failed to download reel %s: %s", shortcode, exc)
            return None
        finally:
            if browser:
                browser.close()

    path = out_dir / f"{shortcode}.mp4"
    path.write_bytes(body)

    return {
        "path": str(path),
        "shortcode": shortcode,
        "date": "",
        "caption": "",
        "url": reel_url,
    }


# ---------------------------------------------------------------------------
# Profile scraping (all reels)
# ---------------------------------------------------------------------------

def scrape_and_download(
    username: str,
    out_dir: Path,
    progress_cb: Callable | None = None,
) -> tuple[list[dict], dict | None]:
    """Download all public video Reels for *username*.

    Returns ``(video_infos, user_info)``.
    """
    from playwright.sync_api import sync_playwright

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    t0 = time.monotonic()
    browser = None

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            captured: list[dict] = []

            def _on_response(resp):
                url = resp.url
                if "/api/" in url and "google" not in url and "sentry" not in url:
                    try:
                        captured.append({"url": url, "body": resp.json()})
                    except Exception:
                        pass

            page.on("response", _on_response)

            # -- 1. Fetch post list ----------------------------------------
            if progress_cb:
                progress_cb(0, desc=f"Fetching @{username} profile...")

            page.goto("https://igram.world/en1/", timeout=30_000)
            page.wait_for_selector("#search-form-input", timeout=15_000)
            page.locator("#search-form-input").fill(
                f"https://www.instagram.com/{username}/"
            )

            with page.expect_response(
                lambda r: "posts" in r.url.lower() or "userInfo" in r.url,
                timeout=20_000,
            ):
                page.keyboard.press("Enter")

            # Give a small window for the second response to arrive
            page.wait_for_timeout(3_000)

            all_edges: list[dict] = []
            user_info: dict | None = None

            for r in captured:
                if "posts" in r["url"].lower():
                    edges = r["body"].get("result", {}).get("edges", [])
                    if isinstance(edges, list):
                        all_edges.extend(edges)
                if "userInfo" in r["url"]:
                    try:
                        user_info = r["body"]["result"][0]["user"]
                    except (KeyError, IndexError, TypeError):
                        pass

            if not all_edges:
                _log.info("No posts found for @%s", username)
                return [], user_info

            # -- Pagination ------------------------------------------------
            total_count = _get_total_count(captured)

            if total_count and len(all_edges) < total_count:
                _paginate(page, captured, all_edges, total_count, progress_cb)

            # -- Filter video reels ----------------------------------------
            reels = _extract_reels(all_edges)
            if not reels:
                _log.info("No video reels found for @%s (found %d posts)", username, len(all_edges))
                return [], user_info

            if progress_cb:
                elapsed = time.monotonic() - t0
                progress_cb(
                    0.15,
                    desc=f"Found {len(reels)} reels ({elapsed:.0f}s). Downloading...",
                )

            # -- 2 & 3. Convert + download each reel -----------------------
            video_infos = _download_reels(
                reels, page, context, captured, out_dir, progress_cb, t0
            )

        except Exception as exc:
            _log.error("Scraping failed for @%s: %s", username, exc)
            return [], None
        finally:
            if browser:
                browser.close()

    return video_infos, user_info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _download_with_retry(context, url: str, retries: int = 3, timeout: int = 60_000) -> bytes | None:
    """Download a URL through the browser context with retry + backoff."""
    for attempt in range(retries):
        try:
            resp = context.request.get(url, timeout=timeout)
            if resp.status == 200:
                return resp.body()
            _log.warning("Download returned status %d (attempt %d/%d)", resp.status, attempt + 1, retries)
        except Exception as exc:
            _log.warning("Download failed (attempt %d/%d): %s", attempt + 1, retries, exc)
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return None


def _get_total_count(captured: list[dict]) -> int | None:
    for r in captured:
        if "posts" in r["url"].lower():
            count = r["body"].get("result", {}).get("count")
            if isinstance(count, int):
                return count
    return None


def _paginate(page, captured, all_edges, total_count, progress_cb):
    """Attempt to load additional pages of posts."""
    for _ in range(5):
        prev = len(all_edges)
        captured.clear()

        if progress_cb:
            progress_cb(
                0.05 + 0.1 * len(all_edges) / max(total_count, 1),
                desc=f"Loading posts ({len(all_edges)}/{total_count})...",
            )

        btn = page.locator(
            'button:has-text("Load"), button:has-text("More"), button:has-text("Show")'
        )
        try:
            if btn.count() > 0:
                btn.first.click()
            else:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.wait_for_timeout(8_000)

        existing_ids = {e.get("node", {}).get("id") for e in all_edges}
        for r in captured:
            if "posts" in r["url"].lower():
                for edge in r["body"].get("result", {}).get("edges", []):
                    node_id = edge.get("node", {}).get("id")
                    if node_id and node_id not in existing_ids:
                        all_edges.append(edge)

        if len(all_edges) >= total_count or len(all_edges) == prev:
            break


def _extract_reels(edges: list[dict]) -> list[dict]:
    """Filter post edges down to video reels with download URLs."""
    reels: list[dict] = []
    for edge in edges:
        node = edge.get("node", {})
        if not isinstance(node, dict):
            continue
        if not (node.get("is_video") and node.get("video_url")):
            continue
        caption = ""
        cap = node.get("edge_media_to_caption", {}).get("edges", [])
        if cap and isinstance(cap, list):
            caption = cap[0].get("node", {}).get("text", "")[:200]
        reels.append({
            "shortcode": node.get("shortcode", ""),
            "video_url": node.get("video_url", ""),
            "caption": caption,
            "timestamp": node.get("taken_at_timestamp", 0),
        })
    return reels


def _download_reels(reels, page, context, captured, out_dir, progress_cb, t0):
    """For each reel, resolve a proxy CDN URL and download the video."""
    video_infos: list[dict] = []
    total = len(reels)
    consecutive_failures = 0

    for i, reel in enumerate(reels):
        sc = reel["shortcode"]
        ts = reel.get("timestamp", 0)
        date_str = (
            datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if ts else ""
        )

        elapsed = time.monotonic() - t0
        if progress_cb:
            progress_cb(
                0.15 + 0.45 * i / total,
                desc=(
                    f"Downloading reel {i + 1}/{total}: {sc}  "
                    f"({elapsed:.0f}s elapsed)"
                ),
            )

        # Submit reel URL and wait for the convert API response
        captured.clear()
        reel_url = f"https://www.instagram.com/reel/{sc}/"

        try:
            inp = page.locator("#search-form-input")
            inp.fill("")
            inp.fill(reel_url)
            with page.expect_response(
                lambda r: "convert" in r.url, timeout=15_000
            ):
                page.keyboard.press("Enter")
        except Exception:
            # Fallback: navigate back and retry with a fixed timeout
            try:
                page.goto("https://igram.world/en1/", timeout=30_000)
                page.wait_for_selector("#search-form-input", timeout=15_000)
                page.locator("#search-form-input").fill(reel_url)
                with page.expect_response(
                    lambda r: "convert" in r.url, timeout=15_000
                ):
                    page.keyboard.press("Enter")
            except Exception as exc:
                _log.warning("Skipping reel %s: convert request failed: %s", sc, exc)
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    _log.error("Too many consecutive failures, stopping download")
                    break
                continue

        # Small grace period for the response to be parsed
        page.wait_for_timeout(500)

        proxy_url = _find_proxy_url(captured)
        if not proxy_url:
            _log.warning("No proxy URL for reel %s", sc)
            consecutive_failures += 1
            if consecutive_failures >= 5:
                _log.error("Too many consecutive failures, stopping download")
                break
            continue

        # Download through the browser context with retry
        body = _download_with_retry(context, proxy_url)
        if body and len(body) > 1_000:
            path = out_dir / f"{sc}.mp4"
            path.write_bytes(body)
            video_infos.append({
                "path": str(path),
                "shortcode": sc,
                "date": date_str,
                "caption": reel.get("caption", ""),
                "url": reel_url,
            })
            consecutive_failures = 0
        else:
            _log.warning("Download failed or too small for reel %s", sc)
            consecutive_failures += 1
            if consecutive_failures >= 5:
                _log.error("Too many consecutive failures, stopping download")
                break

    return video_infos


def _find_proxy_url(captured: list[dict]) -> str | None:
    """Extract the first video proxy URL from captured API responses."""
    for r in captured:
        if "convert" in r.get("url", ""):
            urls = r.get("body", {}).get("url", [])
            if urls and isinstance(urls, list):
                url = urls[0].get("url", "") if isinstance(urls[0], dict) else ""
                if url:
                    return url
    return None
