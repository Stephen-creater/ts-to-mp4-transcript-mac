---
name: ts-to-mp4-transcript-mac
description: Use this skill when a user wants to convert a local `.ts` video into a standard `.mp4` on macOS and generate a timestamped `.txt` transcript from the video. Trigger on requests about `.ts` livestream recordings, video format conversion, local Mac video cleanup, or turning a video into plain text.
---

# TS To MP4 Transcript Mac

## Overview

This skill packages a small macOS workflow for two tasks only: converting a local `.ts` video file into a more compatible `.mp4`, and creating a timestamped `.txt` transcript from the resulting video.

## When To Use It

- The user has a local `.ts` video and wants a normal `.mp4`.
- The user wants a transcript file from a local video on Mac.
- The user wants a reusable, local-first workflow for video conversion plus transcription.

## Workflow

1. Confirm the input is a local video file, usually a `.ts`.
2. Use `scripts/video_to_mp4_and_transcript.py` for the actual workflow.
3. Default behavior:
   - Convert the source into H.264 MP4 with `CRF 23` and `preset slow`.
   - Preserve the original AAC audio track without re-encoding.
   - Generate a timestamped transcript as `YYYY-MM-DD.txt`.
4. If the user wants a one-command setup on another Mac, use `scripts/bootstrap_and_run.sh`.

## Commands

Run the direct Python workflow when dependencies are already available:

```bash
python3 scripts/video_to_mp4_and_transcript.py /path/to/video.ts --overwrite
```

Run the setup wrapper on another Mac when the user wants a one-command path:

```bash
bash scripts/bootstrap_and_run.sh /path/to/video.ts --overwrite
```

## Output Rules

- The `.mp4` goes next to the input by default, using the same basename.
- The transcript goes next to the input by default, named with the current date, like `2026-05-28.txt`.

## Guardrails

- This workflow expects `ffmpeg` and `ffprobe` to exist on the Mac.
- The default audio-preservation path only accepts AAC audio for the MP4 output, because the goal is to avoid audio distortion.
- If the source audio codec is not AAC, surface that clearly instead of silently re-encoding it.
- Prefer `language=zh` for Chinese livestream content. Use `auto` only if the language is unclear.

## Files

- `scripts/video_to_mp4_and_transcript.py`: main workflow
- `scripts/bootstrap_and_run.sh`: one-command bootstrap for another Mac
