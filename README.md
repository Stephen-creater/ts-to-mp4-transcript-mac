# TS to MP4 Transcript Mac

Convert a local `.ts` video on macOS into a standard `.mp4`, then generate a timestamped `.txt` transcript.

This repo only covers:

1. `TS -> MP4`
2. `Video -> Transcript TXT`

## Requirements

- macOS
- `ffmpeg` and `ffprobe`
- `python3`

Install the system dependency first:

```bash
brew install ffmpeg python
```

## One-command usage

```bash
bash scripts/bootstrap_and_run.sh /path/to/video.ts --overwrite
```

Default outputs:

- MP4: same folder as the input, same basename
- Transcript: same folder as the input, named as `YYYY-MM-DD.txt`

## Direct Python usage

If you already have Python dependencies available:

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

- Video is encoded to H.264 MP4 with `CRF 23` and `preset slow`.
- Audio is preserved without re-encoding, so this workflow expects AAC audio in the source when producing the MP4.
- The transcript is timestamped and uses Whisper `turbo` by default.
