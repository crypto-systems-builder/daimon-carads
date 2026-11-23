#!/usr/bin/env python3
"""Prove a cut is clean before anyone approves it.

  python3 engine/verify_cut.py <words.json> <edl.json> <cut.mp4> --out <verify.json>
                               [--style styles/default.md] [--truth <truth.json>]

Re-transcribes the cut and checks:
  1 words        the cut says exactly the words the EDL kept: nothing lost, nothing extra
  2 removed      every removed line is gone (a repeated sentence is heard once, not twice)
  3 pauses       no silence longer than the pacing limit survives
  4 joins        no join lands inside speech (the audio is quiet at every cut point)
  5 edges        every kept segment starts and ends on silence, so no word is clipped
  6 sync         picture and sound are the same length
  7 truth        (only with --truth) the cut matches a ground-truth file of planted mistakes

Writes the cut's own word timings next to the report (<cut>.words.json) for the captions step.
Exit code 0 only if every check passes.
"""
import argparse
import sys
from difflib import SequenceMatcher
from pathlib import Path

from common import HOP, envelope, load_audio, load_style, norm_words, probe, read_json, speech_threshold, write_json
from transcribe import transcribe


def overlap(a0, a1, spans):
    return sum(max(0.0, min(a1, e) - max(a0, s)) for s, e in spans)


def verify(words, edl, cut_path, style, truth=None):
    p = style["pacing"]
    keep = [(s["start"], s["end"]) for s in edl["keep"]]
    cutw = transcribe(cut_path, words.get("backend", "auto"))
    write_json(Path(cut_path).with_suffix(".words.json"), cutw)
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # 1 words
    expected = [x for w in words["words"] if overlap(w["start"], w["end"], keep) > 0.5 * (w["end"] - w["start"])
                for x in norm_words(w["w"])]
    got = norm_words(cutw["text"])
    if expected == got:
        add("words", True, f"all {len(expected)} kept words heard in the cut, in order, nothing extra")
    else:
        diff = [f"{tag}: expected '{' '.join(expected[i1:i2])}' heard '{' '.join(got[j1:j2])}'"
                for tag, i1, i2, j1, j2 in SequenceMatcher(None, expected, got).get_opcodes() if tag != "equal"]
        add("words", False, "; ".join(diff))

    # 2 removed lines are gone
    joined, exp_joined, bad = " ".join(got), " ".join(expected), []
    for r in edl["removed"]:
        phrase = " ".join(norm_words(r["text"]))
        if phrase and joined.count(phrase) != exp_joined.count(phrase):
            bad.append(f"'{r['text']}' heard {joined.count(phrase)}x, expected {exp_joined.count(phrase)}x")
        if overlap(r["start"], r["end"], keep) > (p["max_pause"] if r["kind"] == "pause" else 0.05):
            bad.append(f"{r['kind']} at {r['start']:.2f}s is still partly in the cut")
    n_lines = sum(r["kind"] != "pause" for r in edl["removed"])
    n_pauses = sum(r["kind"] == "pause" for r in edl["removed"])
    add("removed", not bad, "; ".join(bad) or f"{n_lines} removed lines and {n_pauses} long pauses are gone")

    # 3 pauses
    cw = cutw["words"]
    gaps = [(cw[i + 1]["start"] - cw[i]["end"], cw[i]["w"]) for i in range(len(cw) - 1)]
    worst = max(gaps, default=(0, ""))
    limit = p["max_pause"] + 0.1
    add("pauses", worst[0] <= limit, f"longest silence in the cut is {worst[0]:.2f}s after '{worst[1]}' (limit {limit:.2f}s)")

    # 4 joins
    audio = load_audio(cut_path)
    db = envelope(audio)
    thr = speech_threshold(db)
    t, loud = 0.0, []
    for s, e in keep[:-1]:
        t += e - s
        a, b = max(0, int((t - 0.02) / HOP)), int((t + 0.02) / HOP) + 1
        level = float(db[a:b].max())
        if level > thr:
            loud.append(f"join at {t:.2f}s is at {level:.0f} dB (speech starts at {thr:.0f} dB)")
    add("joins", not loud, "; ".join(loud) or f"all {len(keep) - 1} joins fall on silence")

    # 5 edges: distance from each segment edge to the nearest kept word edge, in the source
    tight = []
    for s, e in keep:
        inside = [w for w in words["words"] if w["start"] >= s - 0.3 and w["end"] <= e + 0.3
                  and overlap(w["start"], w["end"], [(s, e)]) > 0]
        if not inside:
            continue
        head, tail = inside[0]["start"] - s, e - inside[-1]["end"]
        if head < 0.03:
            tight.append(f"'{inside[0]['w']}' starts {head * 1000:.0f} ms after a cut")
        if tail < 0.03:
            tight.append(f"'{inside[-1]['w']}' ends {tail * 1000:.0f} ms before a cut")
    add("edges", not tight, "; ".join(tight) or "every segment has at least 30 ms of silence at both ends")

    # 6 sync
    info = probe(cut_path)
    drift = abs(info["v_duration"] - info["a_duration"])
    add("sync", drift <= 1.5 / info["fps"], f"picture {info['v_duration']:.3f}s, sound {info['a_duration']:.3f}s")

    # 7 ground truth
    if truth:
        bad, groups = [], {}
        for seg in truth["segments"]:
            groups.setdefault(seg["text"], []).append(seg)
        for text, segs in groups.items():
            want = sum(s["action"] == "keep" for s in segs)
            full = sum(overlap(s["start"], s["end"], keep) >= (s["end"] - s["start"]) - 0.02 for s in segs)
            none = sum(overlap(s["start"], s["end"], keep) <= 0.05 for s in segs)
            if full != want or full + none != len(segs):
                bad.append(f"'{text[:40]}': {full} of {len(segs)} takes kept whole, expected {want}")
        lp = truth["long_pause"]
        left = overlap(lp["start"], lp["end"], keep)
        if left > p["max_pause"]:
            bad.append(f"{left:.2f}s of the planted pause survives")
        m = truth["planted_mistakes"]
        add("truth", not bad, "; ".join(bad) or
            f"planted mistakes all removed ({m['restarts']} restarts, {m['repeated_sentences']} repeat, "
            f"{m['long_pauses']} long pause); every other line kept whole")

    return {"cut": str(cut_path), "duration": info["duration"], "transcript": cutw["text"],
            "passed": all(c["pass"] for c in checks), "checks": checks}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("edl")
    ap.add_argument("cut")
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default="styles/default.md")
    ap.add_argument("--truth")
    a = ap.parse_args()
    rep = verify(read_json(a.words), read_json(a.edl), a.cut, load_style(a.style),
                 read_json(a.truth) if a.truth else None)
    write_json(a.out, rep)
    print("CUT TRANSCRIPT:", rep["transcript"], "\n")
    for c in rep["checks"]:
        print(f"{'PASS' if c['pass'] else 'FAIL'}  {c['check']:8} {c['detail']}")
    print("\nRESULT:", "PASS - safe to approve" if rep["passed"] else "FAIL - do not approve")
    sys.exit(0 if rep["passed"] else 1)
