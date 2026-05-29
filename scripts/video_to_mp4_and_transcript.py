#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import whisper


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def require_binary(name: str) -> None:
    if shutil.which(name):
        return
    raise SystemExit(f"Missing required binary: {name}")


def probe_first_audio_codec(input_path: Path) -> str | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "json",
        str(input_path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams", [])
    if not streams:
        return None
    return streams[0].get("codec_name")


def convert_ts_to_mp4(
    input_path: Path,
    output_path: Path,
    crf: int,
    preset: str,
    overwrite: bool,
) -> None:
    audio_codec = probe_first_audio_codec(input_path)
    if audio_codec != "aac":
        raise SystemExit(
            "This workflow preserves original audio without re-encoding. "
            f"Detected audio codec: {audio_codec or 'none'}. "
            "Use an AAC-audio source, or adapt the script intentionally."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-y" if overwrite else "-n",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run_command(command)


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def transcribe_to_txt(
    input_path: Path,
    output_path: Path,
    model_name: str,
    download_root: Path,
    language: str | None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model(model_name, download_root=str(download_root))
    result = model.transcribe(
        str(input_path),
        fp16=False,
        verbose=False,
        language=language,
        task="transcribe",
        condition_on_previous_text=True,
        temperature=0.0,
    )

    lines: list[str] = [
        f"Source: {input_path.name}",
        f"Model: {model_name}",
        f"Language: {result.get('language', 'unknown')}",
        "",
    ]
    for segment in result.get("segments", []):
        text = segment.get("text", "").strip()
        if not text:
            continue
        start = format_timestamp(segment.get("start", 0.0))
        end = format_timestamp(segment.get("end", 0.0))
        lines.append(f"[{start} - {end}] {text}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a TS video to MP4 and generate a timestamped transcript."
    )
    parser.add_argument("input_file", help="Path to the source .ts video")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Where to write the MP4 and transcript. Default: same folder as the input file.",
    )
    parser.add_argument(
        "--mp4-name",
        default=None,
        help="Custom MP4 filename. Default: <input_stem>.mp4",
    )
    parser.add_argument(
        "--transcript-name",
        default=None,
        help="Custom transcript filename. Default: today's date as YYYY-MM-DD.txt",
    )
    parser.add_argument("--crf", type=int, default=23, help="Video quality target. Lower is higher quality.")
    parser.add_argument("--preset", default="slow", help="x264 preset. Default: slow")
    parser.add_argument("--model", default="turbo", help="Whisper model name. Default: turbo")
    parser.add_argument(
        "--download-root",
        default=None,
        help="Whisper model cache directory. Default: <repo>/.whisper-models",
    )
    parser.add_argument(
        "--language",
        default="zh",
        help="Whisper language code. Use auto to let Whisper detect it. Default: zh",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing MP4 or transcript outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_binary("ffmpeg")
    require_binary("ffprobe")

    input_path = Path(args.input_file).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file does not exist: {input_path}")

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else input_path.parent
    )
    mp4_name = args.mp4_name or f"{input_path.stem}.mp4"
    transcript_name = args.transcript_name or f"{datetime.now().strftime('%Y-%m-%d')}.txt"

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    download_root = (
        Path(args.download_root).expanduser().resolve()
        if args.download_root
        else (repo_root / ".whisper-models").resolve()
    )
    language = None if args.language.lower() == "auto" else args.language

    mp4_path = output_dir / mp4_name
    transcript_path = output_dir / transcript_name

    convert_ts_to_mp4(
        input_path=input_path,
        output_path=mp4_path,
        crf=args.crf,
        preset=args.preset,
        overwrite=args.overwrite,
    )
    transcribe_to_txt(
        input_path=mp4_path,
        output_path=transcript_path,
        model_name=args.model,
        download_root=download_root,
        language=language,
    )

    print(f"MP4: {mp4_path}")
    print(f"Transcript: {transcript_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(f"Command failed with exit code {error.returncode}: {error.cmd}", file=sys.stderr)
        raise
