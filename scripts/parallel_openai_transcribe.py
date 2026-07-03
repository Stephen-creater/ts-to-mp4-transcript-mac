#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Chunk:
    index: int
    start: float
    end: float
    path: Path


def require_binary(name: str) -> None:
    if shutil.which(name):
        return
    raise SystemExit(f"Missing required binary: {name}")


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_media(input_path: Path) -> dict[str, Any]:
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
    import json

    return json.loads(result.stdout or "{}")


def ensure_audio_stream(media_info: dict[str, Any], input_path: Path) -> None:
    streams = media_info.get("streams", [])
    if any(stream.get("codec_type") == "audio" for stream in streams):
        return
    raise SystemExit(f"No audio stream found in: {input_path}")


def plan_chunks(total_seconds: float, chunk_seconds: int, overlap_seconds: int) -> list[tuple[int, float, float]]:
    if total_seconds <= 0:
        return [(0, 0.0, 0.0)]

    step = max(1, chunk_seconds - overlap_seconds)
    chunks: list[tuple[int, float, float]] = []
    start = 0.0
    index = 0
    while start < total_seconds:
        end = min(total_seconds, start + chunk_seconds)
        chunks.append((index, start, end))
        if end >= total_seconds:
            break
        start += step
        index += 1
    return chunks


def extract_chunk(input_path: Path, chunk: tuple[int, float, float], output_dir: Path) -> Chunk:
    index, start, end = chunk
    output_path = output_dir / f"chunk_{index:04d}.wav"
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
        str(output_path),
    ]
    run_command(command)
    return Chunk(index=index, start=start, end=end, path=output_path)


def extract_all_chunks(input_path: Path, chunk_plan: list[tuple[int, float, float]], output_dir: Path) -> list[Chunk]:
    return [extract_chunk(input_path, chunk, output_dir) for chunk in chunk_plan]


def load_openai_client() -> Any:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for the fast parallel transcription path.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Missing Python package 'openai'. Install it before using this script.") from exc
    return OpenAI()


def object_to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    raise TypeError(f"Unsupported transcription result object: {type(obj)}")


def transcribe_chunk(client: Any, chunk: Chunk, model: str, language: str | None) -> dict[str, Any]:
    with chunk.path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            response_format="verbose_json",
            language=language,
        )
    payload = object_to_dict(result)
    payload["_chunk_index"] = chunk.index
    payload["_chunk_start"] = chunk.start
    return payload


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def merge_results(results: list[dict[str, Any]], overlap_seconds: int) -> tuple[str, list[str]]:
    merged_lines: list[str] = []
    detected_language = "unknown"

    for result in sorted(results, key=lambda item: item["_chunk_index"]):
        detected_language = result.get("language") or detected_language
        chunk_start = float(result["_chunk_start"])
        segments = result.get("segments") or []

        if segments:
            for segment in segments:
                text = (segment.get("text") or "").strip()
                if not text:
                    continue
                local_start = float(segment.get("start", 0.0))
                local_end = float(segment.get("end", local_start))
                if chunk_start > 0 and local_end <= overlap_seconds:
                    continue
                global_start = chunk_start + local_start
                global_end = chunk_start + local_end
                merged_lines.append(
                    f"[{format_timestamp(global_start)} - {format_timestamp(global_end)}] {text}"
                )
        else:
            text = (result.get("text") or "").strip()
            if text:
                merged_lines.append(
                    f"[{format_timestamp(chunk_start)} - {format_timestamp(chunk_start)}] {text}"
                )

    # Remove exact adjacent duplicates that can appear at chunk joins.
    deduped_lines: list[str] = []
    for line in merged_lines:
        if deduped_lines and deduped_lines[-1] == line:
            continue
        deduped_lines.append(line)

    return detected_language, deduped_lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fast chunked parallel transcription via the OpenAI Audio API."
    )
    parser.add_argument("input_file", help="Path to the input media file")
    parser.add_argument("output_file", help="Path to the output transcript .txt")
    parser.add_argument(
        "--model",
        default="gpt-4o-transcribe",
        help="OpenAI transcription model. Example: gpt-4o-transcribe or gpt-4o-mini-transcribe",
    )
    parser.add_argument(
        "--language",
        default="zh",
        help="Language hint such as zh or en. Use auto to omit the hint.",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=120,
        help="Chunk size in seconds. Default: 120",
    )
    parser.add_argument(
        "--overlap-seconds",
        type=int,
        default=4,
        help="Overlap between adjacent chunks in seconds. Default: 4",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Parallel upload/transcription workers. Default: 8",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_binary("ffmpeg")
    require_binary("ffprobe")

    input_path = Path(args.input_file).expanduser().resolve()
    output_path = Path(args.output_file).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    media_info = probe_media(input_path)
    ensure_audio_stream(media_info, input_path)
    total_seconds = float(media_info.get("format", {}).get("duration", 0.0))
    chunk_plan = plan_chunks(total_seconds, args.chunk_seconds, args.overlap_seconds)
    client = load_openai_client()
    language = None if args.language.lower() == "auto" else args.language

    with tempfile.TemporaryDirectory(prefix="openai_transcribe_chunks_") as temp_dir:
        chunks = extract_all_chunks(input_path, chunk_plan, Path(temp_dir))
        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {
                executor.submit(transcribe_chunk, client, chunk, args.model, language): chunk
                for chunk in chunks
            }
            for future in as_completed(futures):
                results.append(future.result())

    detected_language, merged_lines = merge_results(results, args.overlap_seconds)
    header = [
        f"Source: {input_path.name}",
        f"Backend: openai_parallel",
        f"Model: {args.model}",
        f"Language: {detected_language}",
        "",
    ]
    output_path.write_text("\n".join(header + merged_lines) + "\n", encoding="utf-8")
    print(f"Transcript: {output_path}")
    print(f"Chunks: {len(chunk_plan)}")
    print(f"Workers: {max(1, args.workers)}")


if __name__ == "__main__":
    main()
