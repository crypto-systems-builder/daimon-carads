---
name: transcribe
description: Transcribe a video or audio file to word-level timestamps. Use when a recording needs a transcript, word timings, or is about to be edited.
---

# Transcribe

`python3 engine/transcribe.py <media> --out <project>/work/words.json`

- Default backend is Parakeet (via sherpa-onnx) when `engine/models/` holds the model.
  It is verbatim: it keeps false starts and repeats, which editing depends on. English only.
- `--backend faster-whisper --model small.en` uses Whisper instead. It needs
  huggingface.co, and Whisper sometimes silently drops repeated phrases, so check its
  transcript against the audio before trusting it for cuts.
- Word start and end times are measured against the audio's own silences.

Read the printed transcript once. If a name or number is wrong, note it for the
captions step; do not edit `words.json` timings by hand.

If the model folder is missing, the download command is in `CLAUDE.md` under
Working commands.
