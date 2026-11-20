#!/usr/bin/env python3
"""Render the finished short: captions, title, progress bar, loudness, optional music.

  python3 engine/render.py <cut.mp4> <captions.ass> --out <final.mp4> [--style styles/default.md]
                           [--music <file>]   (default: first file in assets/music, none if empty)

Writes <final>.json next to the video with the measured specs.
"""
import argparse
import re
import subprocess
from pathlib import Path

from common import FONTS, MUSIC, fesc, load_style, probe, run, write_json

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def pick_music():
    files = sorted(f for f in MUSIC.glob("*") if f.suffix.lower() in AUDIO_EXT) if MUSIC.exists() else []
    return files[0] if files else None


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[0-9.]+) LUFS", tail)
    pk = re.search(r"Peak:\s+(-?[0-9.]+) dBFS", tail)
    return (float(i.group(1)) if i else None, float(pk.group(1)) if pk else None)


def render(cut, ass, out, style, music=None):
    info = probe(cut)
    cv, au, ex, pb = style["canvas"], style["audio"], style["export"], style["progress_bar"]
    D = info["duration"]
    inputs = ["-i", cut]
    fc = [f"[0:v]ass=filename={fesc(Path(ass).resolve())}:fontsdir={fesc(FONTS)}[vc]"]
    last = "[vc]"
    if pb["enabled"]:
        color = "0x" + pb["color"].lstrip("#")
        inputs += ["-f", "lavfi", "-i", f"color=c={color}:s={cv['width']}x{pb['height']}:r={cv['fps']}:d={D:.3f}"]
        fc.append(f"[vc][1:v]overlay=x='-W+W*t/{D:.3f}':y=0:shortest=1[vp]")
        last = "[vp]"
    norm = f"loudnorm=I={au['loudness_lufs']}:TP={au['true_peak_db']}:LRA=11,aresample=48000"
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        mi = 2 if pb["enabled"] else 1
        fc.append(f"[{mi}:a]volume={au['music_db']}dB,atrim=0:{D:.3f},afade=t=in:d=0.5,"
                  f"afade=t=out:st={max(0, D - 1.0):.3f}:d=1.0[m]")
        fc.append(f"[0:a][m]amix=inputs=2:duration=first:normalize=0,{norm}[a]")
    else:
        fc.append(f"[0:a]{norm}[a]")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", last, "-map", "[a]",
         "-t", f"{D:.3f}", "-r", cv["fps"], "-c:v", "libx264", "-preset", ex["preset"], "-crf", ex["crf"],
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", ex["audio_bitrate"], "-movflags", "+faststart", out])
    o = probe(out)
    lufs, peak = loudness(out)
    spec = {"file": str(out), "width": o["width"], "height": o["height"], "fps": o["fps"],
            "duration": round(o["duration"], 3), "size_mb": round(o["size"] / 1e6, 2),
            "video": o["v_codec"], "audio": o["a_codec"], "loudness_lufs": lufs, "peak_dbfs": peak,
            "music": Path(music).name if music else None}
    write_json(Path(out).with_suffix(".json"), spec)
    return spec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cut")
    ap.add_argument("ass")
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default="styles/default.md")
    ap.add_argument("--music")
    a = ap.parse_args()
    music = a.music or pick_music()
    print("music:", music or "none (assets/music is empty)")
    spec = render(a.cut, a.ass, a.out, load_style(a.style), music)
    print(" ".join(f"{k}={v}" for k, v in spec.items()))
