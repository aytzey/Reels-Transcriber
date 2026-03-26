"""
TikTok video downloader via tikwm.com API.

Supports:
- Single video download via the public ``/api/`` endpoint (no auth required).
- Profile video listing via ``/api/user/posts`` (requires Playwright to
  bypass Cloudflare Turnstile).

The tikwm.com ``/api/`` endpoint proxies TikTok's CDN, so downloads work
even when tiktok.com is blocked at the network level.
"""

from __future__ import annotations

import shutil
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

_TIKWM_API = "https://www.tikwm.com/api/"
_TIKWM_USER_POSTS = "https://www.tikwm.com/api/user/posts"
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ---------------------------------------------------------------------------
# Single video
# ---------------------------------------------------------------------------

def download_single_video(
    url: str,
    out_dir: Path,
) -> dict | None:
    """Download a single TikTok video and return its metadata.

    Accepts full ``tiktok.com`` URLs and short ``vm.tiktok.com`` links.
    Returns a dict with ``path``, ``title``, ``duration``, ``author``, ``url``
    or None on failure.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    resp = requests.post(
        _TIKWM_API,
        data={"url": url, "hd": 1},
        headers={"User-Agent": _UA},
        timeout=20,
        verify=False,
    )
    data = resp.json()

    if data.get("code") != 0:
        return None

    v = data["data"]
    video_id = v.get("id", "unknown")
    play_url = v.get("hdplay") or v.get("play", "")
    if not play_url:
        return None

    # Download video bytes
    r = requests.get(
        play_url,
        timeout=60,
        verify=False,
        stream=True,
        headers={"User-Agent": _UA, "Referer": "https://www.tikwm.com/"},
    )
    if r.status_code != 200:
        return None

    path = out_dir / f"{video_id}.mp4"
    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    if path.stat().st_size < 1_000:
        return None

    author = v.get("author", {})
    return {
        "path": str(path),
        "shortcode": video_id,
        "title": v.get("title", "")[:200],
        "caption": v.get("title", "")[:200],
        "duration": v.get("duration", 0),
        "date": datetime.fromtimestamp(
            v.get("create_time", 0), tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M") if v.get("create_time") else "",
        "author": author.get("unique_id", ""),
        "url": url,
    }


# ---------------------------------------------------------------------------
# Profile scraping (all videos)
# ---------------------------------------------------------------------------

def scrape_profile_videos(
    username: str,
    out_dir: Path,
    progress_cb: Callable | None = None,
) -> tuple[list[dict], dict | None]:
    """Download all videos from a TikTok profile.

    Uses Playwright to call the tikwm.com user/posts API from within a
    browser context (bypasses Cloudflare Turnstile).  Falls back gracefully
    if the challenge cannot be solved in headless mode.

    Returns ``(video_infos, user_info)``.
    """
    from playwright.sync_api import sync_playwright

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    username = username.strip().lstrip("@")

    # -- Get user info (this endpoint has no CF) -------------------------
    user_info = _fetch_user_info(username)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent=_UA,
        )
        page = context.new_page()
        page.add_init_script(
            'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        )

        if progress_cb:
            progress_cb(0, desc=f"Loading @{username} TikTok profile...")

        # Navigate to tikwm to acquire Cloudflare cookies
        page.goto("https://www.tikwm.com/", timeout=30_000)
        page.wait_for_timeout(8_000)

        # Attempt to call user/posts API from the page context
        all_videos: list[dict] = []
        cursor = "0"
        max_pages = 10

        for page_num in range(max_pages):
            if progress_cb:
                progress_cb(
                    0.05 + 0.25 * page_num / max_pages,
                    desc=f"Fetching videos (page {page_num + 1})...",
                )

            try:
                result = page.evaluate(
                    """async ([username, cursor]) => {
                        const fd = new FormData();
                        fd.append('unique_id', username);
                        fd.append('count', '30');
                        fd.append('cursor', cursor);
                        const r = await fetch('/api/user/posts', {method:'POST', body:fd});
                        return await r.json();
                    }""",
                    [username, cursor],
                )
            except Exception:
                break

            if result.get("code") != 0:
                break

            videos = result.get("data", {}).get("videos", [])
            if not videos:
                break

            all_videos.extend(videos)
            cursor = str(result["data"].get("cursor", "0"))
            has_more = result["data"].get("hasMore", False)

            if not has_more:
                break

            time.sleep(0.5)

        browser.close()

    if not all_videos:
        return [], user_info

    if progress_cb:
        progress_cb(0.3, desc=f"Found {len(all_videos)} videos, downloading...")

    # -- Download each video -------------------------------------------
    video_infos = _download_video_list(all_videos, out_dir, progress_cb)

    return video_infos, user_info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_user_info(username: str) -> dict | None:
    """Get TikTok user info via tikwm (no Cloudflare on this endpoint)."""
    try:
        r = requests.post(
            "https://www.tikwm.com/api/user/info",
            data={"unique_id": username},
            headers={"User-Agent": _UA},
            timeout=10,
            verify=False,
        )
        data = r.json()
        if data.get("code") == 0:
            return data["data"]
    except Exception:
        pass
    return None


def _download_video_list(
    videos: list[dict],
    out_dir: Path,
    progress_cb: Callable | None,
) -> list[dict]:
    """Download a list of tikwm video objects."""
    infos: list[dict] = []
    total = len(videos)

    for i, v in enumerate(videos):
        if progress_cb:
            progress_cb(
                0.3 + 0.65 * i / total,
                desc=f"Downloading video ({i + 1}/{total})...",
            )

        video_id = v.get("video_id", v.get("id", f"vid_{i}"))
        play_url = v.get("play", "")
        if not play_url:
            continue

        try:
            r = requests.get(
                play_url,
                timeout=60,
                verify=False,
                stream=True,
                headers={"User-Agent": _UA, "Referer": "https://www.tikwm.com/"},
            )
            if r.status_code != 200:
                continue

            path = out_dir / f"{video_id}.mp4"
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

            if path.stat().st_size < 1_000:
                continue

            ts = v.get("create_time", 0)
            infos.append({
                "path": str(path),
                "shortcode": str(video_id),
                "caption": v.get("title", "")[:200],
                "date": (
                    datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                    if ts else ""
                ),
                "url": f"https://www.tiktok.com/@{v.get('author', {}).get('unique_id', '')}/video/{video_id}",
            })
        except Exception:
            continue

        time.sleep(0.3)  # be polite to the API

    return infos
