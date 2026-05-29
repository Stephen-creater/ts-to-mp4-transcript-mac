#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/bootstrap_and_run.sh /path/to/video.ts [extra args...]"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Missing ffmpeg. Install it first with: brew install ffmpeg"
  exit 1
fi

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "Missing ffprobe. It is included with ffmpeg. Install with: brew install ffmpeg"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Missing python3. Install it first with: brew install python"
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

"${PYTHON_BIN}" -m pip install --disable-pip-version-check --quiet --upgrade pip
"${PIP_BIN}" install --disable-pip-version-check --quiet openai-whisper

"${PYTHON_BIN}" "${SCRIPT_DIR}/video_to_mp4_and_transcript.py" "$@"
