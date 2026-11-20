#!/usr/bin/env python3
"""3-second smoke test of the render engine. Run this first on any new machine.

  python3 engine/test_render.py

Renders engine/out/test-render.mp4 (1080x1920, captions, title, progress bar, a test tone)
and saves the frame at 1.5 s as engine/out/test-render.png so the result can be looked at.
"""
from pathlib import Path

from captions import build
from common import ENGINE, ROOT, load_style, run
from render import render

out = ENGINE / "out"
out.mkdir(exist_ok=True)
style = load_style(ROOT / "styles" / "default.md")
cv = style["canvas"]
src = out / "test-source.mp4"
run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x1B2430:s={cv['width']}x{cv['height']}:r={cv['fps']}:d=3",
     "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", src])
text = ["Render", "engine", "works.", "Captions", "are", "on.", "Three", "second", "test."]
words = [{"w": w, "start": round(0.1 + i * 0.31, 2), "end": round(0.1 + i * 0.31 + 0.27, 2)} for i, w in enumerate(text)]
ass, _ = build(words, style, "Test render: title, captions, progress bar")
(out / "test-render.ass").write_text(ass)
spec = render(src, out / "test-render.ass", out / "test-render.mp4", style)
run(["ffmpeg", "-y", "-v", "error", "-ss", "1.5", "-i", out / "test-render.mp4", "-frames:v", "1", out / "test-render.png"])
src.unlink()
print(" ".join(f"{k}={v}" for k, v in spec.items()))
print("look at:", out / "test-render.png")
