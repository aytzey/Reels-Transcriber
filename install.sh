#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
USE_CUDA="${USE_CUDA:-auto}"

log() {
  printf '[install] %s\n' "$1"
}

fail() {
  printf '[install] %s\n' "$1" >&2
  exit 1
}

require_command() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "$cmd bulunamadi. $hint"
  fi
}

validate_python() {
  "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    || fail "Python 3.10+ gerekli. Mevcut yorumlayici: $PYTHON_BIN"
}

check_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1; then
    return
  fi

  case "$(uname -s)" in
    Darwin)
      fail "ffmpeg gerekli. Kurmak icin: brew install ffmpeg"
      ;;
    Linux)
      fail "ffmpeg gerekli. Paket yoneticinle kur. Ornek: sudo apt install ffmpeg"
      ;;
    *)
      fail "ffmpeg gerekli ve otomatik kurulum tanimli degil."
      ;;
  esac
}

install_python_deps() {
  local os_name
  os_name="$(uname -s)"

  case "$os_name" in
    Darwin)
      log "macOS algilandi. Varsayilan PyTorch paketleri kuruluyor."
      pip install -r requirements.txt
      ;;
    Linux)
      if [[ "$USE_CUDA" == "1" ]] || { [[ "$USE_CUDA" == "auto" ]] && command -v nvidia-smi >/dev/null 2>&1; }; then
        log "Linux + NVIDIA GPU algilandi. CUDA 12.1 PyTorch paketleri kuruluyor."
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
      else
        log "Linux CPU/default PyTorch paketleri kuruluyor."
      fi
      pip install -r requirements.txt
      ;;
    *)
      fail "Desteklenmeyen isletim sistemi: $os_name"
      ;;
  esac
}

require_command "$PYTHON_BIN" "Ornek: PYTHON_BIN=python3.11 ./install.sh"
validate_python
check_ffmpeg

if [[ ! -d "$VENV_DIR" ]]; then
  log "Sanal ortam olusturuluyor: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  log "Mevcut sanal ortam kullaniliyor: $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "pip/setuptools/wheel guncelleniyor."
pip install --upgrade pip setuptools wheel

install_python_deps

log "Playwright Chromium kuruluyor."
python -m playwright install chromium

if [[ "$(uname -s)" == "Linux" ]]; then
  log "Linux notu: Chromium acilmazsa su komutu calistir: python -m playwright install-deps chromium"
fi

log "Kurulum tamamlandi."
log "Uygulamayi baslatmak icin: ./run.sh"
