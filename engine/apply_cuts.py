#!/usr/bin/env python3
"""Cut a recording according to an EDL.

  python3 engine/apply_cuts.py <source.mp4> <edl.json> --out <cut.mp4> [--style styles/default.md]

Every kept segment gets an 8 ms audio fade at each end so joins do not click.
Every other segment is punched in slightly (pacing.jump_cut_zoom) to hide the jump cut.
"""
import argparse

from common import load_style, probe, read_json, run


def apply(source, edl, out, style):
    info = probe(source)
    W, H, fps = style["canvas"]["width"], style["canvas"]["height"], style["canvas"]["fps"]
    zoom = style["pacing"].get("jump_cut_zoom", 0) or 1.0
    ex = style["export"]
    parts, labels = [], ""
    for i, s in enumerate(edl["keep"]):
        d = s["end"] - s["start"]
        v = f"[0:v]trim=start={s['start']}:end={s['end']},setpts=PTS-STARTPTS,scale={W}:{H}"
        if zoom > 1 and i % 2 == 1:
            v += f",scale=trunc(iw*{zoom}/2)*2:trunc(ih*{zoom}/2)*2,crop={W}:{H}"
        parts.append(v + f",setsar=1[v{i}]")
        parts.append(f"[0:a]atrim=start={s['start']}:end={s['end']},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.008,afade=t=out:st={max(0, d - 0.008):.4f}:d=0.008[a{i}]")
        labels += f"[v{i}][a{i}]"
    n = len(edl["keep"])
    parts.append(f"{labels}concat=n={n}:v=1:a=1[v][a]")
    run(["ffmpeg", "-y", "-v", "error", "-i", source, "-filter_complex", ";".join(parts),
         "-map", "[v]", "-map", "[a]", "-r", fps, "-c:v", "libx264", "-preset", ex["preset"], "-crf", ex["crf"],
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", ex["audio_bitrate"], "-ar", "48000",
         "-movflags", "+faststart", out])
    o = probe(out)
    print(f"cut: {info['duration']:.2f}s -> {o['duration']:.2f}s, {n} segments -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default="styles/default.md")
    a = ap.parse_args()
    apply(a.source, read_json(a.edl), a.out, load_style(a.style))
