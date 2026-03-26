"""Download public Instagram Reels via igram.world + Playwright.

Flow:
1. Submit profile URL to igram.world to get post list (incl. pagination).
2. For each video reel, call /api/convert to obtain a proxy download URL
   served through media.igram.world (bypasses network-level blocks on
   cdninstagram.com).
3. Download each video through the same Playwright browser context.
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


def scrape_and_download(
    username: str,
    out_dir: Path,
    progress_cb: Callable | None = None,
) -> tuple[list[dict], dict | None]:
    """Return ``(video_infos, user_info)`` for *username*.

    Each entry in *video_infos* contains ``path``, ``shortcode``, ``date``,
    ``caption`` and ``url``.
    """
    from playwright.sync_api import sync_playwright

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    with sync_playwright() as pw:
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

        # -- Step 1: fetch posts ----------------------------------------
        if progress_cb:
            progress_cb(0, desc=f"Fetching @{username} profile...")

        page.goto("https://igram.world/en1/", timeout=30_000)
        page.wait_for_selector("#search-form-input", timeout=15_000)

        page.locator("#search-form-input").fill(
            f"https://www.instagram.com/{username}/"
        )
        page.keyboard.press("Enter")
        page.wait_for_timeout(12_000)

        all_edges: list[dict] = []
        user_info: dict | None = None

        for r in captured:
            if "posts" in r["url"].lower():
                all_edges.extend(
                    r["body"].get("result", {}).get("edges", [])
                )
            if "userInfo" in r["url"]:
                try:
                    user_info = r["body"]["result"][0]["user"]
                except (KeyError, IndexError, TypeError):
                    pass

        if not all_edges:
            browser.close()
            return [], user_info

        # pagination
        total_count = None
        for r in captured:
            if "posts" in r["url"].lower():
                total_count = r["body"].get("result", {}).get("count")
                break

        if total_count and len(all_edges) < total_count:
            for _ in range(5):
                prev = len(all_edges)
                captured.clear()

                if progress_cb:
                    progress_cb(
                        0.05 + 0.1 * len(all_edges) / max(total_count, 1),
                        desc=f"Loading posts ({len(all_edges)}/{total_count})...",
                    )

                btn = page.locator(
                    'button:has-text("Load"), '
                    'button:has-text("More"), '
                    'button:has-text("Show")'
                )
                if btn.count() > 0:
                    try:
                        btn.first.click()
                    except Exception:
                        page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight)"
                        )
                else:
                    page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )

                page.wait_for_timeout(8_000)

                existing_ids = {e["node"]["id"] for e in all_edges}
                for r in captured:
                    if "posts" in r["url"].lower():
                        for edge in (
                            r["body"].get("result", {}).get("edges", [])
                        ):
                            if edge["node"]["id"] not in existing_ids:
                                all_edges.append(edge)

                if len(all_edges) >= total_count or len(all_edges) == prev:
                    break

        # filter videos
        reels = _extract_reels(all_edges)
        if not reels:
            browser.close()
            return [], user_info

        if progress_cb:
            progress_cb(0.15, desc=f"Found {len(reels)} reels, downloading...")

        # -- Step 2 & 3: convert + download each reel -------------------
        video_infos = _download_reels(
            reels, page, context, captured, out_dir, progress_cb
        )

        browser.close()

    return video_infos, user_info


# -- helpers ----------------------------------------------------------------

def _extract_reels(edges: list[dict]) -> list[dict]:
    reels = []
    for edge in edges:
        node = edge.get("node", {})
        if not (node.get("is_video") and node.get("video_url")):
            continue
        caption = ""
        cap = node.get("edge_media_to_caption", {}).get("edges", [])
        if cap:
            caption = cap[0].get("node", {}).get("text", "")[:200]
        reels.append({
            "shortcode": node.get("shortcode", ""),
            "video_url": node.get("video_url", ""),
            "caption": caption,
            "timestamp": node.get("taken_at_timestamp", 0),
        })
    return reels


def _download_reels(reels, page, context, captured, out_dir, progress_cb):
    video_infos: list[dict] = []
    total = len(reels)

    for i, reel in enumerate(reels):
        sc = reel["shortcode"]
        ts = reel.get("timestamp", 0)
        date_str = (
            datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if ts
            else ""
        )

        if progress_cb:
            progress_cb(
                0.15 + 0.45 * i / total,
                desc=f"Downloading reel ({i + 1}/{total}): {sc}",
            )

        captured.clear()
        reel_url = f"https://www.instagram.com/reel/{sc}/"

        try:
            inp = page.locator("#search-form-input")
            inp.fill("")
            inp.fill(reel_url)
            page.keyboard.press("Enter")
            page.wait_for_timeout(8_000)
        except Exception:
            page.goto("https://igram.world/en1/", timeout=30_000)
            page.wait_for_selector("#search-form-input", timeout=15_000)
            page.locator("#search-form-input").fill(reel_url)
            page.keyboard.press("Enter")
            page.wait_for_timeout(8_000)

        proxy_url = None
        for r in captured:
            if "convert" in r["url"]:
                urls = r["body"].get("url", [])
                if urls and isinstance(urls, list):
                    proxy_url = urls[0].get("url", "")
                break

        if not proxy_url:
            continue

        try:
            resp = context.request.get(proxy_url, timeout=60_000)
            if resp.status == 200:
                body = resp.body()
                if len(body) > 1_000:
                    path = out_dir / f"{sc}.mp4"
                    path.write_bytes(body)
                    video_infos.append({
                        "path": str(path),
                        "shortcode": sc,
                        "date": date_str,
                        "caption": reel.get("caption", ""),
                        "url": reel_url,
                    })
        except Exception:
            pass

    return video_infos
