#!/usr/bin/env python3
"""Transcribe a video/audio file to word-level timestamps.

  python3 engine/transcribe.py <media> --out <words.json> [--backend auto|sherpa|faster-whisper]

Backends
  sherpa          NVIDIA Parakeet TDT 0.6b v2 via sherpa-onnx. English only. Verbatim: it
                  keeps false starts and repeats, which an editor needs. Model is fetched
                  from GitHub releases into engine/models/ (see CLAUDE.md working commands).
  faster-whisper  Whisper via faster-whisper. Needs huggingface.co to fetch the model.
  auto            sherpa if its model folder exists, otherwise faster-whisper.

Word starts come from the model; word ends and the silences between words are then
measured from the audio itself, so cut points are placed on real silence.
"""
import argparse
import os
from pathlib import Path

import numpy as np

from common import ENGINE, HOP, SR, envelope, load_audio, speech_threshold, write_json

SHERPA_DIR = Path(os.environ.get("VIDEO_ASR_MODEL_DIR",
                                 ENGINE / "models" / "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"))
_REC = None


def _sherpa(audio):
    global _REC
    import sherpa_onnx
    if _REC is None:
        _REC = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(SHERPA_DIR / "encoder.int8.onnx"), decoder=str(SHERPA_DIR / "decoder.int8.onnx"),
            joiner=str(SHERPA_DIR / "joiner.int8.onnx"), tokens=str(SHERPA_DIR / "tokens.txt"),
            model_type="nemo_transducer", num_threads=4)
    db = envelope(audio)
    # Decode in pieces of at most ~45 s, split at the quietest point of each window.
    bounds, pos, total = [0.0], 0.0, len(audio) / SR
    while total - pos > 60:
        a, b = int((pos + 20) / HOP), int((pos + 45) / HOP)
        pos = (a + int(np.argmin(db[a:b]))) * HOP
        bounds.append(pos)
    bounds.append(total)
    raw = []
    for s, e in zip(bounds[:-1], bounds[1:]):
        st = _REC.create_stream()
        st.accept_waveform(SR, audio[int(s * SR):int(e * SR)])
        _REC.decode_stream(st)
        for tok, ts in zip(st.result.tokens, st.result.timestamps):
            if tok.startswith((" ", "▁")) or not raw:
                raw.append([tok.strip(" ▁"), s + ts])
            else:
                raw[-1][0] += tok
    return [(w, t) for w, t in raw if w]


def _faster_whisper(path, model_name, language):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(path), word_timestamps=True, language=language,
                                   condition_on_previous_text=False)
    return [(w.word.strip(), w.start) for seg in segments for w in seg.words if w.word.strip()]


def refine(raw, audio):
    """Turn (word, rough start) pairs into words with measured start/end times."""
    db = envelope(audio)
    sp = db > speech_threshold(db)
    n = len(sp)
    f = lambda t: max(0, min(n - 1, int(round(t / HOP))))
    out = [{"w": w, "start": float(t), "end": None} for w, t in raw]
    if not out:
        return out
    j = f(out[0]["start"] + 0.05)
    if sp[j]:
        while j > 0 and sp[j - 1]:
            j -= 1
    else:
        while j < n - 1 and not sp[j]:
            j += 1
    out[0]["start"] = j * HOP
    for i in range(len(out) - 1):
        a = f(max(raw[i][1] + 0.05, out[i]["start"] + 0.03))
        b = f(raw[i + 1][1] + 0.08)
        best, j = None, a
        while j < b:
            if not sp[j]:
                k = j
                while k < n and not sp[k]:
                    k += 1
                if k - j >= 6 and (best is None or k - j > best[1] - best[0]):
                    best = (j, k)
                j = k
            else:
                j += 1
        if best:  # a real silence of 60 ms or more between the two words
            out[i]["end"], out[i + 1]["start"] = best[0] * HOP, best[1] * HOP
        else:     # the words run together
            out[i]["end"] = out[i + 1]["start"] = max(float(raw[i + 1][1]), out[i]["start"] + 0.02)
    j, quiet = f(out[-1]["start"] + 0.05), 0
    end = j
    while j < n and quiet < 25:
        quiet = 0 if sp[j] else quiet + 1
        if sp[j]:
            end = j + 1
        j += 1
    out[-1]["end"] = end * HOP
    for w in out:
        w["start"], w["end"] = round(w["start"], 3), round(max(w["end"], w["start"] + 0.02), 3)
    return out


def transcribe(path, backend="auto", model="small.en", language="en"):
    audio = load_audio(path)
    if backend == "auto":
        backend = "sherpa" if (SHERPA_DIR / "tokens.txt").exists() else "faster-whisper"
    raw = _sherpa(audio) if backend == "sherpa" else _faster_whisper(path, model, language)
    words = refine(raw, audio)
    return {"source": str(path), "backend": backend, "duration": round(len(audio) / SR, 3),
            "text": " ".join(w["w"] for w in words), "words": words}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", default="auto", choices=["auto", "sherpa", "faster-whisper"])
    ap.add_argument("--model", default="small.en", help="faster-whisper model name")
    ap.add_argument("--language", default="en")
    a = ap.parse_args()
    result = transcribe(a.media, a.backend, a.model, a.language)
    write_json(a.out, result)
    print(f"{len(result['words'])} words, {result['duration']}s, backend={result['backend']} -> {a.out}")
    print(result["text"])
