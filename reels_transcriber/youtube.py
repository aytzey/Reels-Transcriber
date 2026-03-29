"""YouTube transcript helpers powered by youtube-transcript-api."""

from __future__ import annotations

import html
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp


_log = logging.getLogger("reels_transcriber.youtube")
_APP_ROOT = Path(__file__).resolve().parents[1]
_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
_OEMBED_URL = "https://www.youtube.com/oembed"
_YOUTUBE_CACHE_PATH = _APP_ROOT / "runtime_data" / "youtube_transcripts.json"


def is_youtube_url(value: str) -> bool:
    lowered = value.lower()
    return (
        "youtube.com" in lowered
        or "youtu.be" in lowered
        or lowered.startswith("@")
    )


def is_youtube_collection(value: str) -> bool:
    lowered = value.lower()
    return any(
        token in lowered
        for token in (
            "playlist",
            "list=",
            "/channel/",
            "/videos",
            "/@",
            "/c/",
            "/user/",
        )
    ) or lowered.startswith("@")


def normalize_input(value: str) -> str:
    value = value.strip()
    if value.startswith("@"):
        return f"https://www.youtube.com/{value}/videos"
    return value


def extract_video_id(value: str) -> str | None:
    value = normalize_input(value)
    if _VIDEO_ID_PATTERN.fullmatch(value):
        return value

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        candidate = path_parts[0]
        return candidate if _VIDEO_ID_PATTERN.fullmatch(candidate) else None

    if "youtube.com" not in host:
        return None

    if parsed.path == "/watch":
        candidate = parse_qs(parsed.query).get("v", [""])[0]
        return candidate if _VIDEO_ID_PATTERN.fullmatch(candidate) else None

    if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
        candidate = path_parts[1]
        return candidate if _VIDEO_ID_PATTERN.fullmatch(candidate) else None

    return None


def _format_upload_date(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        return datetime.strptime(raw, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return raw


def _format_unix_date(raw: int | float | None) -> str:
    if not raw:
        return ""
    try:
        return datetime.utcfromtimestamp(float(raw)).strftime("%Y-%m-%d")
    except (OverflowError, TypeError, ValueError):
        return ""


def _slugify(value: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", value).strip().lower()
    safe = re.sub(r"[-\s]+", "-", safe)
    return safe[:80] or "youtube-transcript"


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


def _is_blocked_transcript_error(exc: Exception) -> bool:
    return exc.__class__.__name__ in {"RequestBlocked", "IpBlocked", "PoTokenRequired"}


def _load_transcript_client():
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ModuleNotFoundError as exc:  # pragma: no cover - env-specific
        raise RuntimeError(
            "YouTube transcript support requires `youtube-transcript-api`. "
            "Run `pip install -r requirements.txt`."
        ) from exc
    return YouTubeTranscriptApi()


def _friendly_transcript_error(exc: Exception) -> str:
    name = exc.__class__.__name__
    if name == "TranscriptsDisabled":
        return "YouTube transcripts are disabled for this video."
    if name == "NoTranscriptFound":
        return "No YouTube transcript is available for this video."
    if name == "VideoUnavailable":
        return "This YouTube video is unavailable."
    if name == "AgeRestricted":
        return "This YouTube video is age-restricted, so its transcript cannot be retrieved."
    if name in {"RequestBlocked", "IpBlocked"}:
        return "YouTube blocked transcript retrieval from this environment."
    if name == "PoTokenRequired":
        return "YouTube requires an additional verification token for this transcript."
    return f"Could not retrieve the YouTube transcript: {exc}"


def _cache_key(video_id: str, preferred_language: str) -> str:
    return f"{video_id}::{preferred_language or 'auto'}"


def _load_cached_transcript(video_id: str, preferred_language: str) -> dict[str, Any] | None:
    if not _YOUTUBE_CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(_YOUTUBE_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    cached = payload.get(_cache_key(video_id, preferred_language))
    return cached if isinstance(cached, dict) else None


def _save_cached_transcript(
    video_id: str,
    preferred_language: str,
    transcript_payload: dict[str, Any],
) -> None:
    _YOUTUBE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = {}
        if _YOUTUBE_CACHE_PATH.exists():
            existing = json.loads(_YOUTUBE_CACHE_PATH.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
    except (OSError, json.JSONDecodeError):
        existing = {}

    existing[_cache_key(video_id, preferred_language)] = transcript_payload
    try:
        _YOUTUBE_CACHE_PATH.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        _log.warning("Failed to write YouTube transcript cache to %s", _YOUTUBE_CACHE_PATH)


def _fetch_transcript_with_browser(
    video_id: str,
    preferred_language: str = "auto",
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "reels_transcriber.youtube_browser_fallback",
        video_id,
        preferred_language or "auto",
    ]
    env = dict(os.environ)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(Path(__file__).resolve().parents[1]),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Browser fallback timed out while retrieving the YouTube transcript.") from exc

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        detail_suffix = f": {details}" if details else ""
        raise RuntimeError(f"Browser fallback could not retrieve the YouTube transcript{detail_suffix}")

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Browser fallback returned invalid transcript data.") from exc


def _pick_transcript(transcript_list, languages: list[str]):
    if languages:
        try:
            return transcript_list.find_transcript(languages)
        except Exception as exc:  # noqa: BLE001
            if exc.__class__.__name__ != "NoTranscriptFound":
                raise

    manual = next((item for item in transcript_list if not item.is_generated), None)
    if manual is not None:
        return manual
    return next(iter(transcript_list), None)


def _fetch_transcript(video_id: str, preferred_language: str = "auto"):
    try:
        client = _load_transcript_client()
    except RuntimeError:
        return _fetch_transcript_with_browser(video_id, preferred_language=preferred_language)

    languages = _preferred_languages(preferred_language)
    try:
        transcript_list = client.list(video_id)
        transcript = _pick_transcript(transcript_list, languages)
        if transcript is None:
            raise RuntimeError("No YouTube transcript is available for this video.")
        try:
            return transcript.fetch(preserve_formatting=True)
        except Exception as exc:  # noqa: BLE001
            if _is_blocked_transcript_error(exc):
                return _fetch_transcript_with_browser(video_id, preferred_language=preferred_language)
            raise RuntimeError(_friendly_transcript_error(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        if _is_blocked_transcript_error(exc):
            return _fetch_transcript_with_browser(video_id, preferred_language=preferred_language)
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(_friendly_transcript_error(exc)) from exc


def _fetch_oembed_metadata(url: str) -> dict[str, Any]:
    try:
        response = requests.get(
            _OEMBED_URL,
            params={"url": url, "format": "json"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        _log.warning("YouTube oEmbed lookup failed for %s: %s", url, exc)
        return {}

    return {
        "title": payload.get("title", ""),
        "author": payload.get("author_name", ""),
        "author_url": payload.get("author_url", ""),
        "thumbnail": payload.get("thumbnail_url", ""),
    }


def _transcript_raw_data(transcript) -> tuple[list[dict[str, Any]], str, str, bool]:
    if isinstance(transcript, dict):
        return (
            list(transcript.get("snippets") or []),
            str(transcript.get("language_code", "")),
            str(transcript.get("language", "")),
            bool(transcript.get("is_generated", False)),
        )

    return (
        list(transcript.to_raw_data()),
        str(getattr(transcript, "language_code", "")),
        str(getattr(transcript, "language", "")),
        bool(getattr(transcript, "is_generated", False)),
    )


def _build_transcript_payload(
    video_id: str,
    url: str,
    transcript,
    seed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = dict(seed or {})
    raw_chunks, language_code, language_label, is_generated = _transcript_raw_data(transcript)
    chunks: list[dict[str, Any]] = []
    transcript_parts: list[str] = []
    max_end = 0.0

    for chunk in raw_chunks:
        text = html.unescape(str(chunk.get("text", "")).strip())
        if not text:
            continue
        start = round(float(chunk.get("start", 0.0)), 2)
        duration = max(float(chunk.get("duration", 0.0)), 0.0)
        end = round(start + duration, 2)
        max_end = max(max_end, end)
        chunks.append({"timestamp": [start, end], "text": text})
        transcript_parts.append(text)

    transcription = "\n\n".join(transcript_parts).strip()
    if not transcription:
        raise RuntimeError("YouTube returned an empty transcript for this video.")

    title = metadata.get("title") or video_id
    return {
        "path": "",
        "filename": _slugify(title),
        "shortcode": video_id,
        "date": metadata.get("date", ""),
        "caption": title,
        "duration": metadata.get("duration") or max_end,
        "url": url,
        "thumbnail": metadata.get("thumbnail", ""),
        "author": metadata.get("author", ""),
        "transcription": transcription,
        "chunks": chunks,
        "source_transcript": True,
        "transcript_language": language_code,
        "transcript_language_label": language_label,
        "transcript_is_generated": is_generated,
    }


def fetch_single_transcript(
    url: str,
    preferred_language: str = "auto",
    seed: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    canonical_url = normalize_input(url)
    video_id = extract_video_id(canonical_url)
    if not video_id:
        raise RuntimeError("A valid YouTube video URL is required.")

    cached = _load_cached_transcript(video_id, preferred_language)
    if cached is not None:
        merged = dict(cached)
        for key in ("date", "author", "thumbnail", "caption", "duration"):
            if not merged.get(key) and seed and seed.get(key):
                merged[key] = seed[key]
        return merged

    transcript = _fetch_transcript(video_id, preferred_language=preferred_language)
    metadata = dict(seed or {})
    if not metadata.get("title") or not metadata.get("thumbnail"):
        metadata = {
            **_fetch_oembed_metadata(f"https://www.youtube.com/watch?v={video_id}"),
            **metadata,
        }
    if not metadata.get("date"):
        metadata["date"] = _format_upload_date(metadata.get("upload_date")) or _format_unix_date(
            metadata.get("timestamp")
        )

    payload = _build_transcript_payload(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        transcript=transcript,
        seed=metadata,
    )
    _save_cached_transcript(video_id, preferred_language, payload)
    return payload


def _ydl_base_opts(out_dir: Path) -> dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "skip_download": True,
        "restrictfilenames": True,
    }


def download_single_video(
    url: str,
    out_dir: Path,
    preferred_language: str = "auto",
) -> dict[str, Any] | None:
    """Backward-compatible wrapper for transcript-based single-video fetches."""
    _ = out_dir
    return fetch_single_transcript(url, preferred_language=preferred_language)


def fetch_collection_transcripts(
    source: str,
    progress_cb: Callable | None = None,
    preferred_language: str = "auto",
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Resolve transcripts for videos in a playlist or channel."""
    source = normalize_input(source)

    if progress_cb:
        progress_cb(0.05, desc="Fetching YouTube collection metadata...")

    meta_opts = {
        **_ydl_base_opts(Path(".")),
        "extract_flat": True,
        "playlistend": 20,
    }

    with yt_dlp.YoutubeDL(meta_opts) as ydl:
        try:
            info = ydl.extract_info(source, download=False)
        except yt_dlp.DownloadError as exc:
            _log.error("YouTube collection lookup failed for %s: %s", source, exc)
            return [], None

    entries = info.get("entries") or []
    if not isinstance(entries, list):
        entries = []

    videos: list[dict[str, Any]] = []
    skipped = 0
    total = len(entries)
    for index, entry in enumerate(entries, start=1):
        entry_url = (
            entry.get("url")
            or entry.get("webpage_url")
            or (f"https://www.youtube.com/watch?v={entry.get('id')}" if entry.get("id") else "")
        )
        if not entry_url:
            continue
        if not re.match(r"^https?://", entry_url):
            entry_url = f"https://www.youtube.com/watch?v={entry_url}"

        if progress_cb:
            progress_cb(
                0.05 + (0.35 * (index / max(total, 1))),
                desc=f"Fetching YouTube transcript {index}/{total}...",
            )

        seed = {
            "title": entry.get("title", ""),
            "duration": entry.get("duration", 0),
            "date": _format_upload_date(entry.get("upload_date")) or _format_unix_date(
                entry.get("timestamp")
            ),
            "author": entry.get("uploader") or entry.get("channel") or "",
            "thumbnail": "",
        }

        try:
            item = fetch_single_transcript(
                entry_url,
                preferred_language=preferred_language,
                seed=seed,
            )
        except RuntimeError as exc:
            skipped += 1
            _log.warning("Skipping YouTube video %s: %s", entry_url, exc)
            continue

        if item is not None:
            videos.append(item)

    user_info = {
        "title": info.get("title", ""),
        "channel": info.get("channel", ""),
        "uploader": info.get("uploader", ""),
        "url": info.get("webpage_url", source),
        "skipped": skipped,
    }
    return videos, user_info


def download_collection(
    source: str,
    out_dir: Path,
    progress_cb: Callable | None = None,
    preferred_language: str = "auto",
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Backward-compatible wrapper for transcript-based collection fetches."""
    _ = out_dir
    return fetch_collection_transcripts(
        source,
        progress_cb=progress_cb,
        preferred_language=preferred_language,
    )
