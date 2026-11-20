#!/usr/bin/env python3
"""Build word-by-word captions (ASS subtitles) from word timings.

  python3 engine/captions.py <cut.words.json> --out <captions.ass> [--style styles/default.md]
                             [--title "Hook text shown at the top"]

Words are grouped into short chunks; the word being spoken is lit in the highlight colour.
"""
import argparse
import textwrap
from pathlib import Path

from common import load_style, read_json


def ass_color(hex_color, alpha=0):
    h = hex_color.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ts(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def chunks(words, max_words, max_chars):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        text_len = sum(len(x["w"]) for x in cur) + len(cur) - 1
        nxt = words[i + 1] if i + 1 < len(words) else None
        full = nxt is None or len(cur) >= max_words or text_len + 1 + len(nxt["w"]) > max_chars
        if full or w["w"][-1:] in ".?!," or nxt["start"] - w["end"] > 0.3:
            out.append(cur)
            cur = []
    return out


def build(words, style, title=None):
    c, t, cv = style["captions"], style["title"], style["canvas"]
    W = cv["width"]
    clean = lambda s: (s.upper() if c["uppercase"] else s).strip().rstrip(",.").replace("{", "(").replace("}", ")")
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {cv['height']}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{c['font']},{c['size']},{ass_color(c['color'])},{ass_color(c['color'])},{ass_color(c['outline_color'])},{ass_color('#000000', 0x80)},0,0,0,0,100,100,0,0,1,{c['outline']},{c['shadow']},5,40,40,0,1
Style: Title,{t['font']},{t['size']},{ass_color(t['color'])},{ass_color(t['color'])},{ass_color(t['box_color'])},{ass_color(t['box_color'])},-1,0,0,0,100,100,0,0,3,18,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if title:
        text = "\\N".join(textwrap.wrap(title, t["wrap_chars"]))
        lines.append(f"Dialogue: 1,{ts(0)},{ts(t['seconds'])},Title,,0,0,0,,{{\\an5\\pos({W // 2},{t['y']})\\fad(150,250)}}{text}")
    groups = chunks(words, c["max_words"], c["max_chars"])
    white, hi = ass_color(c["color"]), ass_color(c["highlight"])
    for gi, g in enumerate(groups):
        nxt_start = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else g[-1]["end"] + 0.4
        g_end = min(g[-1]["end"] + 0.25, nxt_start)
        for i, w in enumerate(g):
            start = g[0]["start"] if i == 0 else w["start"]
            end = g[i + 1]["start"] if i + 1 < len(g) else g_end
            if end - start < 0.02:
                continue
            body = " ".join(f"{{\\c{hi}}}{clean(x['w'])}{{\\c{white}}}" if j == i else clean(x["w"])
                            for j, x in enumerate(g))
            pop = "\\fscx86\\fscy86\\t(0,90,\\fscx100\\fscy100)" if c["pop"] and i == 0 else ""
            lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Caption,,0,0,0,,{{\\an5\\pos({W // 2},{c['y']}){pop}}}{body}")
    return head + "\n".join(lines) + "\n", len(groups)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default="styles/default.md")
    ap.add_argument("--title")
    a = ap.parse_args()
    text, n = build(read_json(a.words)["words"], load_style(a.style), a.title)
    Path(a.out).write_text(text)
    print(f"{n} caption chunks -> {a.out}")
