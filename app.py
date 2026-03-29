"""StoryToText web application server."""

from __future__ import annotations

import argparse
import cgi
import json
import logging
import mimetypes
import os
import secrets
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from reels_transcriber.jobs import JobManager
from reels_transcriber.state import DATA_DIR, STATE_PATH, StateStore, TMP_DIR


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
INDEX_PATH = WEB_DIR / "index.html"

TMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("TMPDIR", str(TMP_DIR))
tempfile.tempdir = str(TMP_DIR)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
_log = logging.getLogger("storytotext.server")


class StoryToTextServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, StoryToTextHandler)
        self.store = StateStore()
        self.jobs = JobManager(self.store)


class StoryToTextHandler(BaseHTTPRequestHandler):
    server: StoryToTextServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return

        if path.startswith("/api/"):
            self._handle_api_get(path)
            return

        if path.startswith("/downloads/"):
            self._handle_download(path)
            return

        if path.startswith("/assets/"):
            self._serve_static(path.removeprefix("/assets/"))
            return

        self._serve_index()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._handle_api_post(path)

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/keys/"):
            key_id = path.rsplit("/", 1)[-1]
            deleted = self.server.store.revoke_api_key(key_id)
            if deleted:
                self._json_response({"ok": True})
            else:
                self._json_response({"error": "Key not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args) -> None:
        _log.info("%s - %s", self.address_string(), fmt % args)

    def _handle_api_get(self, path: str) -> None:
        if path == "/api/bootstrap":
            self._json_response(self.server.store.bootstrap())
            return

        if path == "/api/health":
            bootstrap = self.server.store.bootstrap()
            self._json_response(
                {
                    "ok": True,
                    "jobs": len(bootstrap["jobs"]),
                    "response_rate": bootstrap["health"]["response_rate"],
                    "state_path": str(STATE_PATH),
                }
            )
            return

        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            job = self.server.store.get_job(job_id)
            if job:
                self._json_response(job)
            else:
                self._json_response({"error": "Job not found"}, status=HTTPStatus.NOT_FOUND)
            return

        if path.startswith("/api/v1/jobs/"):
            secret = self._require_api_key()
            if not secret:
                return
            parts = path.strip("/").split("/")
            if len(parts) == 4:
                job_id = parts[-1]
                job = self.server.store.get_job(job_id)
                if not job:
                    self._json_response({"error": "Job not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                self.server.store.record_api_request(secret, path, "GET", job_id=job_id)
                self._json_response(self._job_api_payload(job))
                return
            if len(parts) == 5 and parts[-1] == "result":
                job_id = parts[-2]
                job = self.server.store.get_job(job_id)
                if not job:
                    self._json_response({"error": "Job not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                if job.get("status") != "completed":
                    self._json_response(
                        {"error": "Job is not completed yet", "status": job.get("status")},
                        status=HTTPStatus.CONFLICT,
                    )
                    return
                self.server.store.record_api_request(
                    secret,
                    path,
                    "GET",
                    job_id=job_id,
                    minutes=float(job.get("duration_minutes", 0.0)),
                )
                self._json_response(
                    {
                        "id": job_id,
                        "title": job.get("title"),
                        "results": job.get("results", []),
                        "word_count": job.get("word_count", 0),
                        "duration_minutes": job.get("duration_minutes", 0.0),
                    }
                )
                return

        self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_api_post(self, path: str) -> None:
        if path == "/api/onboarding":
            payload = self._read_json()
            self._json_response(self.server.store.save_onboarding(payload))
            return

        if path == "/api/settings":
            payload = self._read_json()
            self._json_response(self.server.store.save_settings(payload))
            return

        if path == "/api/keys":
            payload = self._read_json()
            record = self.server.store.create_api_key((payload.get("name") or "").strip() or "Production Main")
            self._json_response(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "secret": record["secret"],
                    "masked": record["masked"],
                    "created_at": record["created_at"],
                },
                status=HTTPStatus.CREATED,
            )
            return

        if path == "/api/jobs":
            if "multipart/form-data" in (self.headers.get("Content-Type") or ""):
                payload = self._read_multipart_job()
            else:
                payload = self._read_json()
            payload["via"] = "web"
            payload.setdefault("title", self._derive_title(payload))
            payload.setdefault("platform_label", self._platform_label(payload.get("platform_hint", "")))
            job = self.server.store.create_job(payload)
            self.server.jobs.enqueue(job["id"])
            self._json_response(job, status=HTTPStatus.CREATED)
            return

        if path.startswith("/api/jobs/") and path.endswith("/retry"):
            job_id = path.split("/")[-2]
            retried = self.server.jobs.retry(job_id)
            if retried:
                self._json_response(retried, status=HTTPStatus.CREATED)
            else:
                self._json_response({"error": "Retry failed"}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/v1/transcriptions":
            secret = self._require_api_key()
            if not secret:
                return
            payload = self._read_json()
            payload["via"] = "api"
            payload.setdefault("platform_hint", payload.get("platform"))
            payload.setdefault("title", self._derive_title(payload))
            payload.setdefault("platform_label", self._platform_label(payload.get("platform_hint", "")))
            job = self.server.store.create_job(payload)
            self.server.jobs.enqueue(job["id"])
            self.server.store.record_api_request(secret, path, "POST", job_id=job["id"])
            self._json_response(
                {
                    "id": job["id"],
                    "status": job["status"],
                    "status_url": f"/api/v1/jobs/{job['id']}",
                    "result_url": f"/api/v1/jobs/{job['id']}/result",
                },
                status=HTTPStatus.CREATED,
            )
            return

        self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_download(self, path: str) -> None:
        name = path.removeprefix("/downloads/")
        if "." not in name:
            self._json_response({"error": "Invalid download URL"}, status=HTTPStatus.BAD_REQUEST)
            return
        job_id, ext = name.rsplit(".", 1)
        job = self.server.store.get_job(job_id)
        if not job:
            self._json_response({"error": "Job not found"}, status=HTTPStatus.NOT_FOUND)
            return
        filename = f"{job.get('title', 'storytotext').replace(' ', '_').lower()}_transcript.{ext}"
        if ext == "json":
            body = json.dumps(job.get("results", []), ensure_ascii=False, indent=2).encode("utf-8")
            self._bytes_response(body, "application/json; charset=utf-8", filename)
            return
        if ext == "txt":
            body = self._build_txt_export(job).encode("utf-8")
            self._bytes_response(body, "text/plain; charset=utf-8", filename)
            return
        self._json_response({"error": "Unsupported format"}, status=HTTPStatus.BAD_REQUEST)

    def _serve_index(self) -> None:
        body = INDEX_PATH.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, relative_path: str) -> None:
        target = (WEB_DIR / relative_path).resolve()
        if not target.exists() or WEB_DIR.resolve() not in target.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        mime, _ = mimetypes.guess_type(target.name)
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _build_txt_export(self, job: dict) -> str:
        lines = [job.get("title", "StoryToText export"), ""]
        for index, result in enumerate(job.get("results", []), start=1):
            heading = result.get("caption") or result.get("filename") or f"Item {index}"
            lines.append(f"[{index}] {heading}")
            if result.get("url"):
                lines.append(f"Source: {result['url']}")
            lines.append("")
            chunks = result.get("chunks") or []
            if chunks:
                for chunk in chunks:
                    timestamp = chunk.get("timestamp") or [0, 0]
                    lines.append(f"{timestamp[0]:>5} - {timestamp[1]:>5}  {chunk.get('text', '')}")
            else:
                lines.append(result.get("transcription", ""))
            lines.append("")
            lines.append("=" * 60)
            lines.append("")
        return "\n".join(lines)

    def _job_api_payload(self, job: dict) -> dict:
        return {
            "id": job.get("id"),
            "title": job.get("title"),
            "status": job.get("status"),
            "phase": job.get("phase"),
            "progress": job.get("progress"),
            "error": job.get("error", ""),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "word_count": job.get("word_count", 0),
            "duration_minutes": job.get("duration_minutes", 0.0),
            "result_count": job.get("result_count", 0),
        }

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def _read_multipart_job(self) -> dict:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )
        payload = {
            "mode": form.getfirst("mode", "upload_files"),
            "platform_hint": form.getfirst("platform_hint", "upload"),
            "source_value": form.getfirst("source_value", ""),
            "language": form.getfirst("language", "en"),
            "model": form.getfirst("model", "distil-large-v3 (fast)"),
            "speaker_detection": form.getfirst("speaker_detection", "false") == "true",
            "title": form.getfirst("title", ""),
            "uploaded_files": [],
        }
        staged_dir = DATA_DIR / "staged_uploads" / secrets.token_hex(5)
        staged_dir.mkdir(parents=True, exist_ok=True)

        field = form["media"] if "media" in form else []
        items = field if isinstance(field, list) else [field]
        for item in items:
            if not getattr(item, "filename", ""):
                continue
            safe_name = Path(item.filename).name
            target = staged_dir / safe_name
            with target.open("wb") as fh:
                fh.write(item.file.read())
            payload["uploaded_files"].append({"path": str(target), "name": safe_name})
        return payload

    def _require_api_key(self) -> str | None:
        header = self.headers.get("Authorization", "")
        if not header.lower().startswith("bearer "):
            self._json_response({"error": "Missing Bearer token"}, status=HTTPStatus.UNAUTHORIZED)
            return None
        secret = header.split(" ", 1)[1].strip()
        if not self.server.store.authenticate_api_key(secret):
            self._json_response({"error": "Invalid API key"}, status=HTTPStatus.UNAUTHORIZED)
            return None
        return secret

    def _json_response(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes_response(self, body: bytes, content_type: str, filename: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _derive_title(self, payload: dict) -> str:
        mode = payload.get("mode", "single_url")
        source_value = (payload.get("source_value") or "").strip()
        if mode == "profile_batch":
            return f"{source_value or 'Profile'} archive"
        if mode == "upload_files":
            count = len(payload.get("uploaded_files") or [])
            return f"{count or 'New'} upload transcription"
        if source_value:
            return source_value.split("/")[-1][:72] or "New transcription"
        return "New transcription"

    def _platform_label(self, platform: str) -> str:
        return {
            "instagram": "Instagram",
            "tiktok": "TikTok",
            "youtube": "YouTube",
            "upload": "Upload",
            "api": "API",
        }.get((platform or "").lower(), "Source")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the StoryToText web application.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()

    server = StoryToTextServer((args.host, args.port))
    _log.info("StoryToText running at http://%s:%s", args.host, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
