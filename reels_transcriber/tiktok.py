"""
TikTok video downloader via tikwm.com API.

Supports:
- **Single video** download via the public ``/api/`` endpoint (no Cloudflare,
  always works).  Accepts full ``tiktok.com`` URLs and short ``vm.tiktok.com``
  links.
- **Profile scraping** via ``/api/user/posts``.  This endpoint is behind
  Cloudflare Turnstile, so we use two strategies:

  1. **curl_cffi** with TLS fingerprint impersonation (fastest, works when CF
     doesn't require JS challenge).
  2. **Playwright** — navigates tikwm.com in a headed browser to solve the
     Turnstile challenge, then calls the API with the cleared cookies.

  If the network blocks ``tiktok.com`` entirely (e.g. corporate firewalls),
  profile scraping still works because tikwm.com proxies all requests through
  their own servers.

The tikwm CDN also proxies video downloads, so ``tiktokcdn.com`` being
blocked doesn't matter.
"""

from __future__ import annotations

import logging
import shutil
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

_log = logging.getLogger("reels_transcriber.tiktok")

_TIKWM = "https://www.tikwm.com"
_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_REQUEST_TIMEOUT = 20
_DOWNLOAD_TIMEOUT = 90


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _request_with_retry(
    method: str,
    url: str,
    retries: int = 3,
    backoff: float = 2.0,
    **kwargs,
) -> requests.Response | None:
    """Make an HTTP request with exponential backoff on failure."""
    kwargs.setdefault("headers", {}).setdefault("User-Agent", _UA)
    kwargs.setdefault("verify", False)
    kwargs.setdefault("timeout", _REQUEST_TIMEOUT)

    for attempt in range(retries):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 200:
                return resp
            _log.warning(
                "%s %s returned %d (attempt %d/%d)",
                method.upper(), url[:80], resp.status_code, attempt + 1, retries,
            )
        except requests.RequestException as exc:
            _log.warning(
                "%s %s failed (attempt %d/%d): %s",
                method.upper(), url[:80], attempt + 1, retries, exc,
            )
        if attempt < retries - 1:
            time.sleep(backoff ** attempt)
    return None


# ---------------------------------------------------------------------------
# Single video download (no Cloudflare — always works)
# ---------------------------------------------------------------------------

def download_single_video(url: str, out_dir: Path) -> dict | None:
    """Download one TikTok video.  Returns metadata dict or None."""
    out_dir.mkdir(parents=True, exist_ok=True)

    resp = _request_with_retry(
        "POST", f"{_TIKWM}/api/",
        data={"url": url, "hd": 1},
    )
    if not resp:
        _log.error("TikTok API request failed for %s", url)
        return None

    try:
        data = resp.json()
    except ValueError:
        _log.error("Invalid JSON from TikTok API for %s", url)
        return None

    if data.get("code") != 0:
        _log.warning("TikTok API error code %s for %s", data.get("code"), url)
        return None

    v = data.get("data")
    if not isinstance(v, dict):
        return None

    play_url = v.get("hdplay") or v.get("play", "")
    if not play_url:
        _log.warning("No play URL in TikTok API response for %s", url)
        return None

    r = _request_with_retry(
        "GET", play_url,
        timeout=_DOWNLOAD_TIMEOUT,
        stream=True,
        headers={"User-Agent": _UA, "Referer": f"{_TIKWM}/"},
    )
    if not r:
        _log.error("Video download failed for %s", url)
        return None

    video_id = v.get("id", "unknown")
    path = out_dir / f"{video_id}.mp4"
    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    if path.stat().st_size < 1_000:
        _log.warning("Downloaded file too small for %s (%d bytes)", url, path.stat().st_size)
        path.unlink(missing_ok=True)
        return None

    author = v.get("author", {}) if isinstance(v.get("author"), dict) else {}
    ts = v.get("create_time", 0)
    return {
        "path": str(path),
        "shortcode": str(video_id),
        "caption": (v.get("title") or "")[:200],
        "duration": v.get("duration", 0),
        "date": (
            datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if ts else ""
        ),
        "author": author.get("unique_id", ""),
        "url": url,
    }


# ---------------------------------------------------------------------------
# Profile scraping
# ---------------------------------------------------------------------------

def scrape_profile_videos(
    username: str,
    out_dir: Path,
    progress_cb: Callable | None = None,
) -> tuple[list[dict], dict | None]:
    """Download all videos from a TikTok profile.

    Tries multiple strategies to bypass Cloudflare on tikwm.com/api/user/posts:
    1. curl_cffi session with browser TLS fingerprint
    2. Playwright headed browser (solves Turnstile via real rendering)

    Returns ``(video_infos, user_info)``.
    """
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    username = username.strip().lstrip("@")

    if progress_cb:
        progress_cb(0, desc=f"Fetching @{username} info...")

    user_info = _fetch_user_info(username)

    # Try strategies in order
    all_videos = _try_curl_cffi(username, progress_cb)

    if not all_videos:
        all_videos = _try_playwright(username, progress_cb)

    if not all_videos:
        _log.info("No videos found for @%s via any strategy", username)
        return [], user_info

    if progress_cb:
        progress_cb(0.3, desc=f"Found {len(all_videos)} videos, downloading...")

    video_infos = _download_video_list(all_videos, out_dir, progress_cb)
    return video_infos, user_info


# ---------------------------------------------------------------------------
# Strategy 1: curl_cffi (TLS impersonation)
# ---------------------------------------------------------------------------

def _try_curl_cffi(username: str, progress_cb: Callable | None) -> list[dict]:
    """Attempt to fetch user posts using curl_cffi browser impersonation."""
    try:
        from curl_cffi import requests as cffi_req
    except ImportError:
        _log.info("curl_cffi not installed, skipping TLS impersonation strategy")
        return []

    if progress_cb:
        progress_cb(0.05, desc="Trying TLS impersonation...")

    all_videos: list[dict] = []
    cursor = "0"

    for page_num in range(10):
        session = None
        try:
            session = cffi_req.Session(impersonate="chrome120", verify=False)
            # Pre-visit the homepage to establish cookies
            session.get(f"{_TIKWM}/", timeout=10)
            time.sleep(0.5)

            r = session.post(
                f"{_TIKWM}/api/user/posts",
                data={"unique_id": username, "count": "30", "cursor": cursor},
                timeout=15,
            )
            if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                _log.warning("curl_cffi: unexpected response (status=%d)", r.status_code)
                return all_videos

            data = r.json()
            if data.get("code") != 0:
                _log.warning("curl_cffi: API error code %s", data.get("code"))
                return all_videos

            videos = data.get("data", {}).get("videos", [])
            if not isinstance(videos, list) or not videos:
                break

            all_videos.extend(videos)
            cursor = str(data["data"].get("cursor", "0"))

            if progress_cb:
                progress_cb(
                    0.05 + 0.2 * (page_num + 1) / 10,
                    desc=f"Fetching videos ({len(all_videos)})...",
                )

            if not data["data"].get("hasMore", False):
                break

            time.sleep(1)
        except Exception as exc:
            _log.warning("curl_cffi page %d failed: %s", page_num, exc)
            break
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

    return all_videos


# ---------------------------------------------------------------------------
# Strategy 2: Playwright (headless browser with stealth)
# ---------------------------------------------------------------------------

def _try_playwright(username: str, progress_cb: Callable | None) -> list[dict]:
    """Use Playwright to solve Cloudflare challenge and call the API."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log.info("Playwright not installed, skipping browser strategy")
        return []

    if progress_cb:
        progress_cb(0.05, desc="Attempting browser-based fetch...")

    all_videos: list[dict] = []
    browser = None

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                ignore_https_errors=True,
                user_agent=_UA,
            )
            page = ctx.new_page()
            page.add_init_script(
                'Object.defineProperty(navigator,"webdriver",{get:()=>undefined})'
            )

            page.goto(f"{_TIKWM}/", timeout=30_000)
            page.wait_for_timeout(12_000)

            if "moment" in page.title().lower():
                _log.warning("Cloudflare challenge not solved for tikwm.com")
                return []

            cursor = "0"
            for page_num in range(10):
                if progress_cb:
                    progress_cb(
                        0.05 + 0.2 * (page_num + 1) / 10,
                        desc=f"Fetching videos ({len(all_videos)})...",
                    )
                try:
                    result = page.evaluate(
                        """async ([u, c]) => {
                            const fd = new FormData();
                            fd.append('unique_id', u);
                            fd.append('count', '30');
                            fd.append('cursor', c);
                            const r = await fetch('/api/user/posts',
                                                  {method:'POST', body:fd});
                            return await r.json();
                        }""",
                        [username, cursor],
                    )
                except Exception as exc:
                    _log.warning("Playwright API call failed at page %d: %s", page_num, exc)
                    break

                if not isinstance(result, dict) or result.get("code") != 0:
                    break

                videos = result.get("data", {}).get("videos", [])
                if not isinstance(videos, list) or not videos:
                    break

                all_videos.extend(videos)
                cursor = str(result["data"].get("cursor", "0"))

                if not result["data"].get("hasMore", False):
                    break

                time.sleep(0.5)

        except Exception as exc:
            _log.error("Playwright strategy failed: %s", exc)
        finally:
            if browser:
                browser.close()

    return all_videos


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_user_info(username: str) -> dict | None:
    """Get user metadata (no Cloudflare on this endpoint)."""
    resp = _request_with_retry(
        "POST", f"{_TIKWM}/api/user/info",
        data={"unique_id": username},
    )
    if not resp:
        return None
    try:
        data = resp.json()
        if data.get("code") == 0 and isinstance(data.get("data"), dict):
            return data["data"]
    except (ValueError, KeyError):
        pass
    return None


def _download_video_list(
    videos: list[dict],
    out_dir: Path,
    progress_cb: Callable | None,
) -> list[dict]:
    """Download video files from tikwm video metadata."""
    infos: list[dict] = []
    total = len(videos)
    consecutive_failures = 0

    for i, v in enumerate(videos):
        if not isinstance(v, dict):
            continue

        if progress_cb:
            progress_cb(
                0.3 + 0.65 * i / total,
                desc=f"Downloading video ({i + 1}/{total})...",
            )

        video_id = v.get("video_id", v.get("id", f"vid_{i}"))
        play_url = v.get("play", "")
        if not play_url:
            continue

        r = _request_with_retry(
            "GET", play_url,
            timeout=_DOWNLOAD_TIMEOUT,
            stream=True,
            headers={"User-Agent": _UA, "Referer": f"{_TIKWM}/"},
        )
        if not r:
            consecutive_failures += 1
            if consecutive_failures >= 5:
                _log.error("Too many consecutive download failures, stopping")
                break
            continue

        path = out_dir / f"{video_id}.mp4"
        try:
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

            if path.stat().st_size < 1_000:
                _log.warning("Video %s too small (%d bytes), skipping", video_id, path.stat().st_size)
                path.unlink(missing_ok=True)
                continue
        except OSError as exc:
            _log.warning("Failed to write video %s: %s", video_id, exc)
            continue

        ts = v.get("create_time", 0)
        author = v.get("author", {}) if isinstance(v.get("author"), dict) else {}
        infos.append({
            "path": str(path),
            "shortcode": str(video_id),
            "caption": (v.get("title") or "")[:200],
            "date": (
                datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M"
                )
                if ts else ""
            ),
            "url": (
                f"https://www.tiktok.com/"
                f"@{author.get('unique_id', '')}/video/{video_id}"
            ),
        })
        consecutive_failures = 0

        time.sleep(0.3)

    return infos
