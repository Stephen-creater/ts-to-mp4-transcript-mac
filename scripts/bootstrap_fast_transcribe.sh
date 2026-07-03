#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: bash scripts/bootstrap_fast_transcribe.sh /path/to/media /path/to/output.txt [extra args...]"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv-fast"

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

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required for the fast parallel path."
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

"${PYTHON_BIN}" -m pip install --disable-pip-version-check --quiet --upgrade pip
"${PIP_BIN}" install --disable-pip-version-check --quiet openai

"${PYTHON_BIN}" "${SCRIPT_DIR}/parallel_openai_transcribe.py" "$@"
