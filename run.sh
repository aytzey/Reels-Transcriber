#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python}"

log() {
  printf '[run] %s\n' "$1"
}

fail() {
  printf '[run] %s\n' "$1" >&2
  exit 1
}

if [[ ! -d "$VENV_DIR" ]]; then
  fail "$VENV_DIR bulunamadi. Once ./install.sh calistir."
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  fail "ffmpeg bulunamadi. Once ffmpeg kur."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail "Python yorumlayicisi bulunamadi: $PYTHON_BIN"
fi

log "Gradio uygulamasi baslatiliyor: http://localhost:7860"
exec "$PYTHON_BIN" app.py
