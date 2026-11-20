"""Shared helpers for the render engine."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
FONTS = ROOT / "assets" / "fonts"
MUSIC = ROOT / "assets" / "music"
SR = 16000
HOP = 0.01  # envelope resolution, seconds


def run(cmd, cwd=None):
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit("FAILED: " + " ".join(map(str, cmd))[:400] + "\n" + p.stderr[-2500:])
    return p


def probe(path):
    j = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json",
                        "-show_streams", "-show_format", path]).stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    info = {"duration": float(j["format"]["duration"]), "size": int(j["format"]["size"])}
    if v:
        num, den = v["r_frame_rate"].split("/")
        info.update(width=v["width"], height=v["height"], fps=float(num) / float(den),
                    v_duration=float(v.get("duration", info["duration"])), v_codec=v["codec_name"])
    if a:
        info.update(a_duration=float(a.get("duration", info["duration"])), a_codec=a["codec_name"],
                    sample_rate=int(a["sample_rate"]))
    return info


def load_audio(path, sr=SR):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1",
                        "-ar", str(sr), "-"], capture_output=True)
    if p.returncode != 0:
        sys.exit("FAILED to read audio from %s\n%s" % (path, p.stderr.decode()[-1000:]))
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def envelope(audio, sr=SR):
    """RMS level in dBFS, one value per HOP seconds."""
    hop = int(sr * HOP)
    n = len(audio) // hop
    frames = audio[: n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)


def speech_threshold(db):
    """Level above which a frame counts as speech: 35 dB under the loud parts."""
    return max(float(np.percentile(db, 95)) - 35.0, -55.0)


def norm_words(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower().replace("'", "")).split()


def load_style(path):
    text = Path(path).read_text()
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        sys.exit(f"{path}: no ```json settings block found")
    return json.loads(m.group(1))


def fesc(path):
    """Escape a path for use as an ffmpeg filter option value."""
    s = str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return s.replace(",", "\\,").replace("[", "\\[").replace("]", "\\]").replace(";", "\\;")


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text())
