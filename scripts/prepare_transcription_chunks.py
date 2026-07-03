#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path


def require_binary(name: str) -> None:
    if shutil.which(name):
        return
    raise SystemExit(f"Missing required binary: {name}")


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_media(input_path: Path) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-show_entries",
        "stream=index,codec_type,codec_name,channels,sample_rate,width,height",
        "-of",
        "json",
        str(input_path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "{}")


def has_audio_stream(media_info: dict) -> bool:
    return any(stream.get("codec_type") == "audio" for stream in media_info.get("streams", []))


def build_chunk_plan(total_seconds: float, chunk_seconds: int, overlap_seconds: int) -> list[dict]:
    if total_seconds <= 0:
        return [{"index": 0, "start": 0.0, "end": 0.0}]

    step = max(1, chunk_seconds - overlap_seconds)
    chunks: list[dict] = []
    index = 0
    start = 0.0
    while start < total_seconds:
        end = min(total_seconds, start + chunk_seconds)
        chunks.append({"index": index, "start": round(start, 3), "end": round(end, 3)})
        if end >= total_seconds:
            break
        start += step
        index += 1
    return chunks


def extract_chunks(input_path: Path, output_dir: Path, chunks: list[dict]) -> list[dict]:
    extracted: list[dict] = []
    for chunk in chunks:
        index = chunk["index"]
        start = chunk["start"]
        end = chunk["end"]
        chunk_path = output_dir / f"chunk_{index:04d}.wav"
        duration = max(0.1, end - start)
        command = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(chunk_path),
        ]
        run_command(command)
        extracted.append(
            {
                **chunk,
                "audio_path": str(chunk_path),
                "transcript_path": str(output_dir / f"chunk_{index:04d}.txt"),
            }
        )
    return extracted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare overlapping audio chunks for parallel agent transcription."
    )
    parser.add_argument("input_file", help="Source media file with an audio stream")
    parser.add_argument("output_dir", help="Directory for chunk audio and manifest")
    parser.add_argument("--chunk-seconds", type=int, default=120, help="Chunk size in seconds")
    parser.add_argument("--overlap-seconds", type=int, default=4, help="Overlap in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_binary("ffmpeg")
    require_binary("ffprobe")

    input_path = Path(args.input_file).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    media_info = probe_media(input_path)
    if not has_audio_stream(media_info):
        raise SystemExit(f"No audio stream found in: {input_path}")

    duration = float(media_info.get("format", {}).get("duration", 0.0))
    chunk_plan = build_chunk_plan(duration, args.chunk_seconds, args.overlap_seconds)
    extracted = extract_chunks(input_path, output_dir, chunk_plan)

    manifest = {
        "source": str(input_path),
        "duration_seconds": duration,
        "chunk_seconds": args.chunk_seconds,
        "overlap_seconds": args.overlap_seconds,
        "chunks": extracted,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {manifest_path}")
    print(f"Chunks: {len(extracted)}")


if __name__ == "__main__":
    main()
