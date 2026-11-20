---
name: render
description: Render the finished short from a verified cut and its captions, or run the 3-second engine smoke test. Use for the final export, or to check the render engine works on a machine.
---

# Render

Final export:
`python3 engine/render.py <project>/work/cut.mp4 <project>/work/captions.ass --out <project>/out/final.mp4`

It burns in captions and title, adds the progress bar, normalises loudness to the
style's target, and mixes the first file in `assets/music/` if there is one (none if
empty; `--music <file>` to choose). Specs are written to `out/final.json`.

Afterwards, look at real frames before reporting success:
`ffmpeg -y -v error -i <final.mp4> -vf "select='eq(n,45)+eq(n,150)+eq(n,330)',scale=360:-1,tile=3x1" -frames:v 1 <sheet.png>`

Smoke test on a new machine:
`python3 engine/test_render.py` then view `engine/out/test-render.png`. Expect a yellow
progress bar at the top, a boxed title, and a three-word caption with one yellow word.
