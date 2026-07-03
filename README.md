# TS to MP4 Transcript Mac

Convert local media on macOS into timestamped `.txt` transcripts, with an agent-native fast path for large files and a local fallback path when parallel orchestration is unavailable.

This repo now supports:

1. Agent-native chunking + parallel transcription SOP
2. Local Whisper fallback for offline or no-parallel scenarios
3. `TS -> MP4` conversion when the user explicitly needs a standard MP4 output

## Requirements

- macOS
- `ffmpeg` and `ffprobe`
- `python3`

Install the system dependency first:

```bash
brew install ffmpeg python
```

## Default path: agent-native parallel transcription

This is the recommended path going forward when speed matters.

```bash
python3 scripts/prepare_transcription_chunks.py /path/to/media.mp4 /tmp/transcript_job
```

Then let your host agent do the actual parallel work:

1. Read `/tmp/transcript_job/manifest.json`
2. Assign one chunk per subagent
3. Each subagent transcribes its own chunk into the matching `chunk_XXXX.txt`
4. Merge all chunk transcripts:

```bash
python3 scripts/merge_chunk_transcripts.py /tmp/transcript_job/manifest.json /path/to/output.txt
```

Recommended defaults:

- chunk size: `120s`
- overlap: `4s`
- many parallel workers when the host agent supports it
- use the host agent's strongest available audio or multimodal transcription path

## Local fallback path

Use this when you do not want to depend on parallel agent orchestration, or when the host environment only has a local CPU path.

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

- The default fast path is agent-native. It chunks audio locally, lets the host agent parallelize chunk transcription, then merges timestamps back into one `.txt`.
- The repo does not require a single fixed remote transcription vendor. The host agent can choose the best available backend.
- The local fallback path uses Whisper `turbo` and is slower on CPU, but does not require remote API access.
- The `TS -> MP4` path still encodes to H.264 MP4 with `CRF 23` and `preset slow`.
- The old local script preserves original AAC audio when creating MP4 outputs.
