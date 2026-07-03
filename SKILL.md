---
name: ts-to-mp4-transcript-mac
description: Use this skill when a user wants to transcribe local media into a timestamped `.txt` on macOS, especially when speed matters and the workflow should use chunked parallel transcription through a remote model API. Also use it for `.ts` to `.mp4` conversion when the user explicitly needs a standard MP4 output.
---

# TS To MP4 Transcript Mac

## Overview

This skill packages a macOS workflow for fast transcription-first media handling. The default path is chunked parallel transcription through the OpenAI Audio API, while the older local Whisper path remains as a fallback. `.ts` to `.mp4` conversion is still supported when the user explicitly asks for it.

## When To Use It

- The user has a local `.ts` video and wants a normal `.mp4`.
- The user wants a transcript file from a local video on Mac.
- The user wants a reusable workflow for video conversion plus transcription.
- The user wants large files transcribed faster than a single local CPU Whisper run.
- The user explicitly allows parallel agent work or wants the fastest practical path.

## Workflow

1. Probe the input first and decide whether the user wants:
   - transcript only, or
   - transcript plus `.mp4` conversion.
2. Default to the fast path for transcript-only jobs:
   - use `scripts/parallel_openai_transcribe.py`
   - chunk the media
   - transcribe chunks in parallel
   - merge offsets and remove overlap duplicates
3. Use the local fallback path only when remote API access is unavailable or the user explicitly wants local-only processing.
4. Use `scripts/video_to_mp4_and_transcript.py` only when the user explicitly needs `.ts -> .mp4` plus transcript in one local workflow.
5. If the user wants a one-command setup on another Mac, use:
   - `scripts/bootstrap_fast_transcribe.sh` for the fast path
   - `scripts/bootstrap_and_run.sh` for the local fallback

## Commands

Run the recommended fast path:

```bash
export OPENAI_API_KEY="your-key-here"
bash scripts/bootstrap_fast_transcribe.sh /path/to/media.mp4 /path/to/output.txt
```

Run the fast path directly when dependencies are already available:

```bash
export OPENAI_API_KEY="your-key-here"
python3 scripts/parallel_openai_transcribe.py /path/to/media.mp4 /path/to/output.txt
```

Run the local fallback workflow when dependencies are already available:

```bash
python3 scripts/video_to_mp4_and_transcript.py /path/to/video.ts --overwrite
```

Run the setup wrapper for the local fallback on another Mac:

```bash
bash scripts/bootstrap_and_run.sh /path/to/video.ts --overwrite
```

## Output Rules

- The `.mp4` goes next to the input by default, using the same basename.
- The transcript goes next to the input by default, named with the current date, like `2026-05-28.txt`.

## Guardrails

- This workflow expects `ffmpeg` and `ffprobe` to exist on the Mac.
- The fast path expects `OPENAI_API_KEY`.
- For the fast path, prefer `gpt-4o-transcribe` first and drop to `gpt-4o-mini-transcribe` when cost or throughput matters more than maximum accuracy.
- If the media has no audio stream, do not pretend transcription succeeded. Surface that clearly.
- The local audio-preservation path only accepts AAC audio for the MP4 output, because the goal is to avoid audio distortion.
- If the source audio codec is not AAC, surface that clearly instead of silently re-encoding it.
- Prefer `language=zh` for Chinese livestream content. Use `auto` only if the language is unclear.

## Parallelism

- When the user explicitly allows parallel agent work, it is valid to split long media into chunks and process them concurrently.
- The real speedup comes from parallel backend calls, not from wrapping one local CPU Whisper process with many agent shells.
- Treat subagents as orchestration helpers. Treat the remote transcription backend as the actual acceleration layer.

## Files

- `scripts/parallel_openai_transcribe.py`: default fast path for chunked parallel transcription
- `scripts/bootstrap_fast_transcribe.sh`: one-command setup for the fast path
- `scripts/video_to_mp4_and_transcript.py`: local fallback workflow for `.ts -> .mp4` plus transcript
- `scripts/bootstrap_and_run.sh`: one-command bootstrap for the local fallback
