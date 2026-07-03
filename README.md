# TS to MP4 Transcript Mac

Convert local media on macOS into timestamped `.txt` transcripts, with a fast default path for large files and a local fallback path when API access is unavailable.

This repo now supports:

1. Fast parallel transcription with the OpenAI Audio API
2. Local Whisper fallback for offline or no-key scenarios
3. `TS -> MP4` conversion when the user explicitly needs a standard MP4 output

## Requirements

- macOS
- `ffmpeg` and `ffprobe`
- `python3`

Install the system dependency first:

```bash
brew install ffmpeg python
```

## Default path: fast parallel transcription

This is the recommended path going forward when speed matters.

```bash
export OPENAI_API_KEY="your-key-here"
bash scripts/bootstrap_fast_transcribe.sh /path/to/media.mp4 /path/to/output.txt
```

You can tune the parallelism:

```bash
export OPENAI_API_KEY="your-key-here"
bash scripts/bootstrap_fast_transcribe.sh /path/to/media.mp4 /path/to/output.txt \
  --model gpt-4o-transcribe \
  --chunk-seconds 120 \
  --overlap-seconds 4 \
  --workers 8
```

Recommended defaults:

- `gpt-4o-transcribe`: higher accuracy
- `gpt-4o-mini-transcribe`: lower cost / often faster
- chunk size: `120s`
- overlap: `4s`
- workers: `8`

## Local fallback path

Use this when you do not want to call a remote API, or when `OPENAI_API_KEY` is unavailable.

### One-command usage

```bash
bash scripts/bootstrap_and_run.sh /path/to/video.ts --overwrite
```

Default outputs:

- MP4: same folder as the input, same basename
- Transcript: same folder as the input, named as `YYYY-MM-DD.txt`

## Direct Python usage

If you already have local Whisper dependencies available:

```bash
python3 scripts/video_to_mp4_and_transcript.py /path/to/video.ts --overwrite
```

If you already have `openai` installed and want the fast path directly:

```bash
export OPENAI_API_KEY="your-key-here"
python3 scripts/parallel_openai_transcribe.py /path/to/media.mp4 /path/to/output.txt
```

Useful options:

```bash
python3 scripts/video_to_mp4_and_transcript.py /path/to/video.ts \
  --output-dir /path/to/output \
  --mp4-name result.mp4 \
  --transcript-name 2026-05-28.txt \
  --language zh \
  --overwrite
```

## Notes

- The fast path is built for transcript speed, not MP4 conversion. It chunks audio locally, transcribes chunks in parallel, then merges timestamps back into one `.txt`.
- The fast path requires `OPENAI_API_KEY`.
- The local fallback path uses Whisper `turbo` and is slower on CPU, but does not require remote API access.
- The `TS -> MP4` path still encodes to H.264 MP4 with `CRF 23` and `preset slow`.
- The old local script preserves original AAC audio when creating MP4 outputs.
