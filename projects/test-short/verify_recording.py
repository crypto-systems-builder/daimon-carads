#!/usr/bin/env python3
"""Check that raw/test-recording.mp4 really contains every planted mistake.

Transcribes the recording with Whisper (small.en, via sherpa-onnx) and runs
ffmpeg silencedetect, then asserts:
  - each restarted line's opening words are heard twice
  - the repeated sentence is heard twice
  - exactly one silence of 2.5 s or longer exists

Setup (works without huggingface.co, which cloud sessions may block):
  pip install sherpa-onnx numpy
  curl -L -O https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.en.tar.bz2
  tar xjf sherpa-onnx-whisper-small.en.tar.bz2

Usage:  python3 projects/test-short/verify_recording.py <path>/sherpa-onnx-whisper-small.en
"""
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx

RAW = Path(__file__).resolve().parent / "raw"
model = Path(sys.argv[1])
truth = json.loads((RAW / "test-recording.truth.json").read_text())
video = RAW / truth["file"]

rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=str(model / "small.en-encoder.int8.onnx"),
    decoder=str(model / "small.en-decoder.int8.onnx"),
    tokens=str(model / "small.en-tokens.txt"),
    language="en", task="transcribe", num_threads=4,
)

with tempfile.TemporaryDirectory() as td:
    wav = Path(td) / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
                    "-ar", "16000", "-ac", "1", str(wav)], check=True)
    w = wave.open(str(wav))
    sr = w.getframerate()
    audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

# Whisper decodes at most 30 s at a time, so split in the middle of the long pause.
mid = (truth["long_pause"]["start"] + truth["long_pause"]["end"]) / 2
text = ""
for s, e in [(0, mid), (mid, len(audio) / sr)]:
    st = rec.create_stream()
    st.accept_waveform(sr, audio[int(s * sr):int(e * sr)])
    rec.decode_stream(st)
    text += " " + st.result.text
norm = re.sub(r"[^a-z0-9 ]", "", text.lower())
norm = re.sub(r"\s+", " ", norm).strip()
print("TRANSCRIPT:", text.strip(), "\n")

sd = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af",
                     "silencedetect=noise=-40dB:d=2.5", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
pauses = [float(x) for x in re.findall(r"silence_duration: ([0-9.]+)", sd)]

checks = [
    ("restart 1 heard twice ('when the first iphone')", norm.count("when the first iphone") == 2),
    ("restart 2 heard twice ('the app store only arrived')", norm.count("the app store only arrived") == 2),
    ("repeated sentence heard twice",
     norm.count("you could not install a single app from another company") == 2),
    (f"exactly one long pause (found {pauses})", len(pauses) == 1),
]
ok = True
for name, passed in checks:
    print("PASS" if passed else "FAIL", "-", name)
    ok &= passed
sys.exit(0 if ok else 1)
