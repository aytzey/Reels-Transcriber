"""Persistent application state for the StoryToText web shell."""

from __future__ import annotations

import copy
import json
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "runtime_data"
TMP_DIR = DATA_DIR / "tmp"
UPLOADS_DIR = DATA_DIR / "uploads"
EXPORTS_DIR = DATA_DIR / "exports"
STATE_PATH = DATA_DIR / "state.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds")


def mask_secret(secret: str) -> str:
    if len(secret) <= 12:
        return secret
    return f"{secret[:8]}••••••••{secret[-4:]}"


def _cycle_anchor() -> str:
    now = utc_now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(timespec="seconds")


def _next_renewal() -> str:
    now = utc_now()
    if now.month == 12:
        nxt = now.replace(
            year=now.year + 1,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    else:
        nxt = now.replace(
            month=now.month + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    return nxt.isoformat(timespec="seconds")


def _sample_chunks() -> list[dict[str, Any]]:
    return [
        {
            "timestamp": [0, 136],
            "text": (
                "In the landscape of modern media, we're witnessing a paradigm "
                "shift that rivals the invention of the printing press. The "
                "integration of large language models into our creative workflows "
                "isn't just about efficiency, it's about the democratization of "
                "narrative structure itself."
            ),
        },
        {
            "timestamp": [136, 340],
            "text": (
                "Today the storyteller has evolved. We are no longer just writers; "
                "we are architects of prompts and curators of generated potential. "
                "The human role shifts from the manual labor of assembly to the "
                "high-level philosophy of intent."
            ),
        },
        {
            "timestamp": [341, 503],
            "text": (
                "A small technical writer can now produce documentation that reads "
                "like an editorial piece, and an independent filmmaker can generate "
                "script variations that once required an entire writers' room."
            ),
        },
        {
            "timestamp": [503, 765],
            "text": (
                "The value of content is shifting from the act of creation to the "
                "act of verification. In this post-truth media environment, the "
                "credible archivist becomes the most important figure in the room."
            ),
        },
        {
            "timestamp": [766, 910],
            "text": (
                "As these tools disappear into the background, the distance between "
                "thought and expression narrows. We are entering an era of seamless "
                "cognitive extension."
            ),
        },
    ]


def _sample_results() -> list[dict[str, Any]]:
    chunks = _sample_chunks()
    return [
        {
            "filename": "the-future-of-generative-storytelling",
            "shortcode": "yt_demo_01",
            "date": "2026-03-28 10:45",
            "caption": (
                "The Future of Generative Storytelling: Navigating the Intersection "
                "of AI and Human Creativity"
            ),
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "transcription": "\n\n".join(chunk["text"] for chunk in chunks),
            "chunks": chunks,
        }
    ]


def _make_demo_job(
    job_id: str,
    title: str,
    created_delta_hours: int,
    source_label: str,
    status: str,
    via: str = "web",
    progress: float = 1.0,
    error: str = "",
) -> dict[str, Any]:
    created_at = (utc_now() - timedelta(hours=created_delta_hours)).isoformat(timespec="seconds")
    completed_at = created_at if status == "completed" else ""
    results = _sample_results() if status == "completed" else []
    word_count = 2482 if status == "completed" else 0
    minutes = 15.2 if status == "completed" else 0.0
    model_label = (
        "YouTube native transcript"
        if source_label.lower() == "youtube"
        else "distil-whisper/distil-large-v3"
    )
    return {
        "id": job_id,
        "title": title,
        "mode": "single_url",
        "platform": source_label.lower(),
        "platform_label": source_label,
        "source_value": results[0]["url"] if results else "",
        "language": "en",
        "model": model_label,
        "speaker_detection": False,
        "via": via,
        "status": status,
        "phase": "completed" if status == "completed" else status,
        "progress": progress,
        "status_text": "Transcript ready" if status == "completed" else error,
        "error": error,
        "created_at": created_at,
        "updated_at": created_at,
        "started_at": created_at,
        "completed_at": completed_at,
        "duration_minutes": minutes,
        "word_count": word_count,
        "results": results,
        "result_count": len(results),
        "export_json_path": "",
        "export_txt_path": "",
        "request_payload": {
            "mode": "single_url",
            "source_value": results[0]["url"] if results else "",
            "platform_hint": source_label.lower(),
            "language": "en",
            "model": "distil-large-v3 (fast)",
            "speaker_detection": False,
        },
    }


def default_state() -> dict[str, Any]:
    return {
        "meta": {
            "version": 2,
            "created_at": iso_now(),
        },
        "user": {
            "full_name": "Julian Barnes",
            "email": "julian@storytotext.studio",
            "bio": (
                "AI-first creator building prompt-ready archives from modern "
                "video formats."
            ),
            "timezone": "Europe/Istanbul",
        },
        "settings": {
            "default_language": "en",
            "default_language_label": "English (US)",
            "default_model": "distil-large-v3 (fast)",
            "email_on_complete": True,
            "product_updates": False,
            "speaker_detection": False,
        },
        "onboarding": {
            "intent": "",
            "source_preference": "",
            "completed": False,
        },
        "billing": {
            "plan": "Pro",
            "price_monthly": 49,
            "minutes_limit": 1200,
            "cycle_anchor": _cycle_anchor(),
            "next_renewal": _next_renewal(),
        },
        "api_keys": [],
        "api_requests": [],
        "jobs": [
            _make_demo_job(
                "job_demo_youtube",
                "The Future of Generative Storytelling",
                created_delta_hours=2,
                source_label="YouTube",
                status="completed",
            ),
            _make_demo_job(
                "job_demo_reels",
                "Street Style Reel #04",
                created_delta_hours=20,
                source_label="Reels",
                status="completed",
            ),
            _make_demo_job(
                "job_demo_tiktok",
                "Product Launch Keynote",
                created_delta_hours=30,
                source_label="TikTok",
                status="completed",
            ),
            _make_demo_job(
                "job_demo_spotify",
                "Morning Brew Podcast Ep. 42",
                created_delta_hours=36,
                source_label="Upload",
                status="processing",
                progress=0.45,
            ),
            _make_demo_job(
                "job_demo_api",
                "Technical Doc Interview 1",
                created_delta_hours=48,
                source_label="API",
                status="failed",
                via="api",
                progress=1.0,
                error="The upstream source returned an incomplete media payload.",
            ),
            _make_demo_job(
                "job_demo_tiktok2",
                "Summer Solstice Editorial mp4",
                created_delta_hours=72,
                source_label="TikTok",
                status="completed",
            ),
        ],
    }


class StateStore:
    """JSON-backed application state with coarse-grained locking."""

    def __init__(self) -> None:
        for path in (DATA_DIR, TMP_DIR, UPLOADS_DIR, EXPORTS_DIR):
            path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._state = self._load_state()
        self._normalize_state()
        self._save_locked()

    @property
    def uploads_dir(self) -> Path:
        return UPLOADS_DIR

    @property
    def exports_dir(self) -> Path:
        return EXPORTS_DIR

    def _load_state(self) -> dict[str, Any]:
        if not STATE_PATH.exists():
            return default_state()
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default_state()

    def _normalize_state(self) -> None:
        state = self._state
        state.setdefault("meta", {})
        state["meta"].setdefault("version", 2)
        state.setdefault("user", default_state()["user"])
        state.setdefault("settings", default_state()["settings"])
        state.setdefault("onboarding", default_state()["onboarding"])
        state.setdefault("billing", default_state()["billing"])
        state.setdefault("api_keys", [])
        state.setdefault("api_requests", [])
        state.setdefault("jobs", [])

    def _save_locked(self) -> None:
        tmp_path = STATE_PATH.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(self._state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(STATE_PATH)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            for job in self._state["jobs"]:
                if job["id"] == job_id:
                    return copy.deepcopy(job)
        return None

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = copy.deepcopy(self._state["jobs"])
        return sorted(jobs, key=lambda job: job.get("created_at", ""), reverse=True)

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            job_id = f"job_{secrets.token_hex(6)}"
            created_at = iso_now()
            job = {
                "id": job_id,
                "title": payload.get("title") or "Untitled transcription",
                "mode": payload.get("mode", "single_url"),
                "platform": payload.get("platform_hint", ""),
                "platform_label": payload.get("platform_label", "Source"),
                "source_value": payload.get("source_value", ""),
                "language": payload.get("language", self._state["settings"]["default_language"]),
                "model": payload.get("model", self._state["settings"]["default_model"]),
                "speaker_detection": bool(payload.get("speaker_detection", False)),
                "via": payload.get("via", "web"),
                "status": "queued",
                "phase": "validating",
                "progress": 0.02,
                "status_text": "Queued for processing",
                "error": "",
                "created_at": created_at,
                "updated_at": created_at,
                "started_at": "",
                "completed_at": "",
                "duration_minutes": 0.0,
                "word_count": 0,
                "results": [],
                "result_count": 0,
                "export_json_path": "",
                "export_txt_path": "",
                "request_payload": copy.deepcopy(payload),
            }
            self._state["jobs"].append(job)
            self._save_locked()
            return copy.deepcopy(job)

    def update_job(self, job_id: str, **updates: Any) -> dict[str, Any] | None:
        with self._lock:
            for job in self._state["jobs"]:
                if job["id"] != job_id:
                    continue
                job.update(updates)
                job["updated_at"] = iso_now()
                self._save_locked()
                return copy.deepcopy(job)
        return None

    def save_onboarding(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._state["onboarding"].update(data)
            self._save_locked()
            return copy.deepcopy(self._state["onboarding"])

    def save_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            user_fields = {"full_name", "email", "bio", "timezone"}
            setting_fields = {
                "default_language",
                "default_language_label",
                "default_model",
                "email_on_complete",
                "product_updates",
                "speaker_detection",
            }
            for key, value in data.items():
                if key in user_fields:
                    self._state["user"][key] = value
                if key in setting_fields:
                    self._state["settings"][key] = value
            self._save_locked()
            return {
                "user": copy.deepcopy(self._state["user"]),
                "settings": copy.deepcopy(self._state["settings"]),
            }

    def create_api_key(self, name: str) -> dict[str, Any]:
        secret = f"st_live_{secrets.token_urlsafe(18).replace('-', '').replace('_', '')[:28]}"
        record = {
            "id": f"key_{secrets.token_hex(5)}",
            "name": name or "Untitled key",
            "secret": secret,
            "masked": mask_secret(secret),
            "created_at": iso_now(),
            "last_used_at": "",
            "request_count": 0,
            "minutes_processed": 0.0,
        }
        with self._lock:
            self._state["api_keys"].insert(0, record)
            self._save_locked()
        return copy.deepcopy(record)

    def revoke_api_key(self, key_id: str) -> bool:
        with self._lock:
            before = len(self._state["api_keys"])
            self._state["api_keys"] = [
                record for record in self._state["api_keys"] if record["id"] != key_id
            ]
            changed = len(self._state["api_keys"]) != before
            if changed:
                self._save_locked()
            return changed

    def get_api_key(self, key_id: str) -> dict[str, Any] | None:
        with self._lock:
            for record in self._state["api_keys"]:
                if record["id"] == key_id:
                    return copy.deepcopy(record)
        return None

    def authenticate_api_key(self, secret: str) -> dict[str, Any] | None:
        with self._lock:
            for record in self._state["api_keys"]:
                if record["secret"] == secret:
                    return copy.deepcopy(record)
        return None

    def record_api_request(
        self,
        secret: str,
        path: str,
        method: str,
        job_id: str = "",
        minutes: float = 0.0,
    ) -> None:
        with self._lock:
            for record in self._state["api_keys"]:
                if record["secret"] != secret:
                    continue
                record["last_used_at"] = iso_now()
                record["request_count"] += 1
                record["minutes_processed"] = round(
                    float(record.get("minutes_processed", 0.0)) + float(minutes),
                    2,
                )
                self._state["api_requests"].append(
                    {
                        "at": iso_now(),
                        "path": path,
                        "method": method,
                        "job_id": job_id,
                        "key_id": record["id"],
                    }
                )
                self._save_locked()
                return

    def bootstrap(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        jobs = sorted(snapshot["jobs"], key=lambda job: job.get("created_at", ""), reverse=True)
        completed_jobs = [job for job in jobs if job.get("status") == "completed"]
        current_cycle_start = datetime.fromisoformat(snapshot["billing"]["cycle_anchor"])
        cycle_jobs = [
            job
            for job in completed_jobs
            if job.get("completed_at")
            and datetime.fromisoformat(job["completed_at"]) >= current_cycle_start
        ]
        minutes_used = round(sum(float(job.get("duration_minutes", 0.0)) for job in cycle_jobs), 1)
        api_minutes = round(
            sum(float(job.get("duration_minutes", 0.0)) for job in cycle_jobs if job.get("via") == "api"),
            1,
        )
        web_minutes = round(max(minutes_used - api_minutes, 0.0), 1)
        minutes_limit = float(snapshot["billing"]["minutes_limit"])
        usage_pct = round((minutes_used / minutes_limit) * 100, 1) if minutes_limit else 0.0
        failed_count = len([job for job in jobs if job.get("status") == "failed"])
        completed_count = len(completed_jobs)
        response_rate = 100.0 if completed_count == 0 else round(
            max(90.0, min(99.9, 100.0 - (failed_count * 3.4))),
            1,
        )
        next_renewal = datetime.fromisoformat(snapshot["billing"]["next_renewal"])
        cycle_days_left = max((next_renewal - utc_now()).days, 0)
        return {
            "user": snapshot["user"],
            "settings": snapshot["settings"],
            "onboarding": snapshot["onboarding"],
            "billing": {
                **snapshot["billing"],
                "minutes_used": minutes_used,
                "web_minutes": web_minutes,
                "api_minutes": api_minutes,
                "usage_pct": usage_pct,
                "cycle_days_left": cycle_days_left,
                "response_rate": response_rate,
            },
            "api_keys": [
                {
                    "id": record["id"],
                    "name": record["name"],
                    "masked": record["masked"],
                    "created_at": record["created_at"],
                    "last_used_at": record["last_used_at"],
                    "request_count": record["request_count"],
                    "minutes_processed": record["minutes_processed"],
                }
                for record in snapshot["api_keys"]
            ],
            "jobs": jobs,
            "health": {
                "response_rate": response_rate,
                "avg_latency_ms": 120,
                "api_request_count": len(snapshot["api_requests"]),
            },
        }
