"""Background job execution for StoryToText."""

from __future__ import annotations

import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from .state import StateStore, iso_now


_log = logging.getLogger("reels_transcriber.jobs")


MODEL_MAP = {
    "distil-large-v3 (fast)": "distil-whisper/distil-large-v3",
    "large-v3 (accurate)": "openai/whisper-large-v3",
}


PHASE_SEQUENCE = [
    "validating",
    "fetching",
    "downloading",
    "transcribing",
    "exporting",
    "completed",
]


def humanize_timestamp(timestamp: list[Any] | tuple[Any, Any] | None) -> str:
    if not timestamp or len(timestamp) != 2:
        return ""

    def _format_part(value: Any) -> str:
        if value is None:
            return "00:00"
        total = int(float(value))
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    return f"{_format_part(timestamp[0])} — {_format_part(timestamp[1])}"


class JobManager:
    """Small in-process job queue."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="storytotext")

    def enqueue(self, job_id: str) -> None:
        self.executor.submit(self._run_job, job_id)

    def retry(self, job_id: str) -> dict[str, Any] | None:
        original = self.store.get_job(job_id)
        if not original:
            return None
        payload = dict(original.get("request_payload") or {})
        if not payload:
            return None
        payload["via"] = original.get("via", "web")
        job = self.store.create_job(payload)
        self.enqueue(job["id"])
        return job

    def _run_job(self, job_id: str) -> None:
        job = self.store.get_job(job_id)
        if not job:
            return

        self.store.update_job(
            job_id,
            status="processing",
            phase="validating",
            progress=0.05,
            status_text="Validating request",
            started_at=iso_now(),
            error="",
        )

        try:
            payload = dict(job.get("request_payload") or {})
            payload["model_name"] = MODEL_MAP.get(job.get("model"), MODEL_MAP["distil-large-v3 (fast)"])
            results, title, platform_label, minutes = self._execute_payload(job_id, payload)

            self.store.update_job(
                job_id,
                status="completed",
                phase="completed",
                progress=1.0,
                status_text="Transcript ready",
                completed_at=iso_now(),
                title=title,
                platform_label=platform_label,
                word_count=sum(len((item.get("transcription") or "").split()) for item in results),
                duration_minutes=round(minutes, 2),
                results=results,
                result_count=len(results),
            )
        except Exception as exc:  # noqa: BLE001
            _log.exception("Job %s failed", job_id)
            self.store.update_job(
                job_id,
                status="failed",
                phase="failed",
                progress=1.0,
                status_text="Processing failed",
                error=str(exc),
                completed_at=iso_now(),
            )

    def _execute_payload(
        self,
        job_id: str,
        payload: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str, str, float]:
        mode = payload.get("mode", "single_url")
        language = payload.get("language", "en")
        model_name = payload.get("model_name")

        if mode == "upload_files":
            file_infos, title, platform_label = self._prepare_uploads(job_id, payload)
        elif mode == "profile_batch":
            file_infos, title, platform_label = self._prepare_profile_batch(job_id, payload)
        else:
            file_infos, title, platform_label = self._prepare_single_url(job_id, payload)

        if not file_infos:
            raise RuntimeError("No media files were resolved for this job.")

        processor_label = payload.get("model") or "Whisper"
        if self._uses_source_transcript(file_infos):
            processor_label = f"{platform_label} native transcript"
            self.store.update_job(
                job_id,
                phase="transcribing",
                progress=0.84,
                status_text=f"Using {processor_label}",
                platform_label=platform_label,
                title=title,
                model=processor_label,
            )
            results = self._materialize_source_results(file_infos)
        else:
            self.store.update_job(
                job_id,
                phase="transcribing",
                progress=0.72,
                status_text="Transcribing media with Whisper",
                platform_label=platform_label,
                title=title,
            )

            transcribe = self._lazy_transcribe()
            results = transcribe(
                file_infos,
                language=language,
                progress_cb=self._progress_bridge(job_id),
                progress_start=0.72,
                progress_end=0.96,
                model_name=model_name,
            )

        self.store.update_job(
            job_id,
            phase="exporting",
            progress=0.97,
            status_text="Preparing exports",
        )

        format_results = self._lazy_formatter()
        md, json_path, txt_path = format_results(
            results,
            title,
            self.store.exports_dir,
            processor_label=processor_label,
        )
        _ = md
        self.store.update_job(
            job_id,
            export_json_path=json_path,
            export_txt_path=txt_path,
        )

        minutes = self._estimate_minutes(file_infos, results)
        return results, title, platform_label, minutes

    def _prepare_single_url(
        self,
        job_id: str,
        payload: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str, str]:
        source_value = (payload.get("source_value") or "").strip()
        if not source_value:
            raise RuntimeError("A media URL is required.")

        platform = self._detect_platform(source_value, payload.get("platform_hint"))
        self.store.update_job(
            job_id,
            phase="fetching",
            progress=0.12,
            status_text=f"Resolving {platform.title()} source",
            platform=platform,
            platform_label=self._platform_label(platform),
            source_value=source_value,
        )
        info = self._download_single(
            platform,
            source_value,
            job_id,
            payload.get("language", "en"),
        )
        title = info.get("caption") or info.get("filename") or "New transcription"
        return [info], title, self._platform_label(platform)

    def _prepare_profile_batch(
        self,
        job_id: str,
        payload: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str, str]:
        source_value = self._normalize_batch_source(
            self._detect_platform(payload.get("source_value", ""), payload.get("platform_hint")),
            (payload.get("source_value") or "").strip(),
        )
        if not source_value:
            raise RuntimeError("A profile, channel, or playlist source is required.")

        platform = self._detect_platform(source_value, payload.get("platform_hint"))
        self.store.update_job(
            job_id,
            phase="fetching",
            progress=0.12,
            status_text=f"Fetching {self._platform_label(platform)} batch metadata",
            platform=platform,
            platform_label=self._platform_label(platform),
            source_value=source_value,
        )
        items, owner = self._download_batch(
            platform,
            source_value,
            job_id,
            payload.get("language", "en"),
        )
        if not items:
            raise RuntimeError("No items were found for that source.")
        owner_label = (
            owner.get("full_name")
            or owner.get("channel")
            or owner.get("uploader")
            or owner.get("title")
            or source_value
        )
        title = f"{owner_label} archive"
        return items, title, self._platform_label(platform)

    def _prepare_uploads(
        self,
        job_id: str,
        payload: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str, str]:
        uploads = payload.get("uploaded_files") or []
        if not uploads:
            raise RuntimeError("Upload at least one audio or video file.")

        root = self.store.uploads_dir / job_id
        root.mkdir(parents=True, exist_ok=True)
        file_infos = []
        for entry in uploads:
            source_path = Path(entry["path"])
            if not source_path.exists():
                continue
            target = root / source_path.name
            if source_path.resolve() != target.resolve():
                shutil.copy2(source_path, target)
            file_infos.append(
                {
                    "path": str(target),
                    "filename": target.stem,
                    "caption": target.stem.replace("_", " ").title(),
                    "date": "",
                    "url": "",
                }
            )
        if not file_infos:
            raise RuntimeError("Uploaded files could not be prepared.")

        self.store.update_job(
            job_id,
            phase="downloading",
            progress=0.18,
            status_text=f"Prepared {len(file_infos)} uploaded file(s)",
            platform="upload",
            platform_label="Upload",
        )
        title = payload.get("title") or (
            f"{len(file_infos)} uploaded file{'s' if len(file_infos) != 1 else ''}"
        )
        return file_infos, title, "Upload"

    def _download_single(
        self,
        platform: str,
        source_value: str,
        job_id: str,
        language: str,
    ) -> dict[str, Any]:
        out_dir = self.store.uploads_dir / job_id
        out_dir.mkdir(parents=True, exist_ok=True)

        status_text = f"Downloading from {self._platform_label(platform)}"
        if platform == "youtube":
            status_text = "Fetching transcript from YouTube"

        self.store.update_job(
            job_id,
            phase="downloading",
            progress=0.3,
            status_text=status_text,
        )

        if platform == "instagram":
            from .scraper import download_single_reel

            info = download_single_reel(source_value, out_dir)
        elif platform == "tiktok":
            from .tiktok import download_single_video

            info = download_single_video(source_value, out_dir)
        elif platform == "youtube":
            from .youtube import fetch_single_transcript

            info = fetch_single_transcript(source_value, preferred_language=language)
        else:
            raise RuntimeError("Unsupported source for single URL mode.")

        if not info:
            if platform == "youtube":
                raise RuntimeError("No YouTube transcript could be resolved for this video.")
            raise RuntimeError("The source could not be downloaded.")
        return info

    def _download_batch(
        self,
        platform: str,
        source_value: str,
        job_id: str,
        language: str,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        out_dir = self.store.uploads_dir / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        progress_cb = self._progress_bridge(job_id)

        if platform == "instagram":
            from .scraper import scrape_and_download

            items, owner = scrape_and_download(source_value, out_dir, progress_cb)
        elif platform == "tiktok":
            from .tiktok import scrape_profile_videos

            items, owner = scrape_profile_videos(source_value, out_dir, progress_cb)
        elif platform == "youtube":
            from .youtube import fetch_collection_transcripts

            items, owner = fetch_collection_transcripts(
                source_value,
                progress_cb=progress_cb,
                preferred_language=language,
            )
        else:
            raise RuntimeError("Unsupported source for batch mode.")

        return items, owner or {}

    def _uses_source_transcript(self, file_infos: list[dict[str, Any]]) -> bool:
        return bool(file_infos) and all(bool(item.get("source_transcript")) for item in file_infos)

    def _materialize_source_results(
        self,
        file_infos: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "filename": info.get("filename", ""),
                "shortcode": info.get("shortcode", ""),
                "date": info.get("date", ""),
                "caption": info.get("caption", ""),
                "url": info.get("url", ""),
                "transcription": info.get("transcription", ""),
                "chunks": list(info.get("chunks") or []),
            }
            for info in file_infos
        ]

    def _progress_bridge(self, job_id: str) -> Callable[[float, str], None]:
        def _callback(progress: float, desc: str = "") -> None:
            lowered = (desc or "").lower()
            phase = "transcribing"
            if "fetch" in lowered or "profile" in lowered or "metadata" in lowered:
                phase = "fetching"
            elif "download" in lowered or "extracting" in lowered:
                phase = "downloading"
            elif "transcrib" in lowered or "processing results" in lowered:
                phase = "transcribing"
            elif "export" in lowered:
                phase = "exporting"

            self.store.update_job(
                job_id,
                phase=phase,
                progress=max(0.05, min(float(progress), 0.99)),
                status="processing",
                status_text=desc or "Processing",
            )

        return _callback

    def _estimate_minutes(
        self,
        file_infos: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> float:
        minutes = 0.0
        for info in file_infos:
            duration = info.get("duration", 0)
            if duration:
                minutes += float(duration) / 60.0

        if minutes > 0:
            return minutes

        for result in results:
            chunks = result.get("chunks") or []
            for chunk in chunks:
                ts = chunk.get("timestamp") or [0, 0]
                if len(ts) == 2 and ts[1]:
                    minutes = max(minutes, float(ts[1]) / 60.0)
        return minutes or 1.5

    def _platform_label(self, platform: str) -> str:
        return {
            "instagram": "Instagram",
            "tiktok": "TikTok",
            "youtube": "YouTube",
            "upload": "Upload",
            "api": "API",
        }.get(platform, "Source")

    def _detect_platform(self, source_value: str, hint: str | None) -> str:
        if hint:
            lowered = hint.lower()
            if lowered in {"instagram", "tiktok", "youtube", "upload"}:
                return lowered

        lowered = source_value.lower()
        if "instagram.com" in lowered:
            return "instagram"
        if "tiktok.com" in lowered:
            return "tiktok"
        if "youtube.com" in lowered or "youtu.be" in lowered or source_value.startswith("@"):
            return "youtube"
        raise RuntimeError("Unsupported source. Use Instagram, TikTok, YouTube, or uploads.")

    def _normalize_batch_source(self, platform: str, source_value: str) -> str:
        value = source_value.strip()
        if platform == "instagram":
            value = value.rstrip("/").split("/")[-1]
            return value.lstrip("@")
        if platform == "tiktok":
            value = value.rstrip("/").split("/")[-1]
            return value.lstrip("@")
        return value

    def _lazy_transcribe(self) -> Callable[..., Any]:
        try:
            from .transcriber import transcribe
        except ModuleNotFoundError as exc:  # pragma: no cover - env-specific
            raise RuntimeError(
                "Transcription dependencies are missing. Run `pip install -r requirements.txt`."
            ) from exc
        return transcribe

    def _lazy_formatter(self) -> Callable[..., Any]:
        try:
            from .formatter import format_results
        except ModuleNotFoundError as exc:  # pragma: no cover - env-specific
            raise RuntimeError(
                "Formatter dependencies are missing. Run `pip install -r requirements.txt`."
            ) from exc
        return format_results
