#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2}):(\d{2})\]\s*(.*)$")


def to_seconds(hours: str, minutes: str, seconds: str) -> int:
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def format_seconds(total_seconds: float) -> str:
    total = max(0, int(total_seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_chunks(manifest: dict) -> list[str]:
    overlap_seconds = int(manifest.get("overlap_seconds", 0))
    merged_lines: list[str] = []

    for chunk in sorted(manifest["chunks"], key=lambda item: item["index"]):
        chunk_start = float(chunk["start"])
        transcript_path = Path(chunk["transcript_path"])
        if not transcript_path.exists():
            continue

        for raw_line in transcript_path.read_text(encoding="utf-8").splitlines():
            match = LINE_RE.match(raw_line)
            if not match:
                continue
            local_start = to_seconds(match.group(1), match.group(2), match.group(3))
            local_end = to_seconds(match.group(4), match.group(5), match.group(6))
            text = match.group(7).strip()
            if not text:
                continue
            if chunk_start > 0 and local_end <= overlap_seconds:
                continue

            global_start = chunk_start + local_start
            global_end = chunk_start + local_end
            merged_lines.append(
                f"[{format_seconds(global_start)} - {format_seconds(global_end)}] {text}"
            )

    deduped_lines: list[str] = []
    for line in merged_lines:
        if deduped_lines and deduped_lines[-1] == line:
            continue
        deduped_lines.append(line)
    return deduped_lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge per-chunk timestamped transcripts back into one transcript."
    )
    parser.add_argument("manifest", help="manifest.json from prepare_transcription_chunks.py")
    parser.add_argument("output_file", help="Final merged transcript path")
    parser.add_argument("--backend", default="agent_parallel", help="Header label for transcript provenance")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    output_path = Path(args.output_file).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)
    lines = merge_chunks(manifest)
    header = [
        f"Source: {Path(manifest['source']).name}",
        f"Backend: {args.backend}",
        "Language: unknown",
        "",
    ]
    output_path.write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    print(f"Transcript: {output_path}")


if __name__ == "__main__":
    main()
