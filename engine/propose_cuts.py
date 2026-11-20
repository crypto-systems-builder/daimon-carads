#!/usr/bin/env python3
"""Propose an edit decision list (EDL) from a word-level transcript.

  python3 engine/propose_cuts.py <words.json> --out <edl.json> [--style styles/default.md]
                                 [--drop 3,7] [--keep 4]

Finds, mechanically:
  false start  a line that is abandoned and begun again        -> keep the last take
  repeat       the same sentence said twice in a row            -> keep the last take
  filler       an utterance that is only um / uh                -> cut
  pause        any silence longer than pacing.max_pause         -> tighten to target_pause

It prints a numbered table of utterances. The editor (Claude, then the human at the
approval checkpoint) can overrule it: --drop cuts extra utterances, --keep restores them.
"""
import argparse
from difflib import SequenceMatcher

from common import load_style, norm_words, read_json, write_json

FILLERS = {"um", "uh", "uhm", "erm", "er", "hmm", "mm"}


def utterances(words, split_gap=0.2):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        last = i == len(words) - 1
        gap = 0 if last else words[i + 1]["start"] - w["end"]
        if last or gap >= split_gap or w["w"][-1:] in ".?!":
            out.append({"start": cur[0]["start"], "end": cur[-1]["end"],
                        "text": " ".join(x["w"] for x in cur), "n": norm_words(" ".join(x["w"] for x in cur))})
            cur = []
    return out


def classify(utts):
    """Mark utterances that an editor would remove. Returns {index: (kind, reason)}."""
    cut = {}
    for i, u in enumerate(utts):
        a = u["n"]
        if a and all(x in FILLERS for x in a):
            cut[i] = ("filler", "filler sound only")
            continue
        if i + 1 == len(utts):
            continue
        b = utts[i + 1]["n"]
        prefix = 0
        while prefix < min(len(a), len(b)) and a[prefix] == b[prefix]:
            prefix += 1
        if len(a) >= 3 and SequenceMatcher(None, a, b).ratio() >= 0.9:
            cut[i] = ("repeat", "same sentence repeated; kept the last take")
        elif len(a) >= 2 and prefix >= 2 and prefix >= 0.5 * len(a) and len(a) <= len(b):
            cut[i] = ("false_start", "line restarted; kept the complete take")
    return cut


def build(words_json, style, drop=(), keep=()):
    p = style["pacing"]
    fps = style["canvas"]["fps"]
    dur = words_json["duration"]
    utts = utterances(words_json["words"])
    cut = classify(utts)
    for i in drop:
        cut[i] = ("manual", "removed by the editor")
    for i in keep:
        cut.pop(i, None)
    snap = lambda t: round(round(t * fps) / fps, 4)
    segs, warnings = [], []
    for i, u in enumerate(utts):
        if i in cut:
            continue
        gap_b = u["start"] - utts[i - 1]["end"] if i else u["start"]
        gap_a = utts[i + 1]["start"] - u["end"] if i + 1 < len(utts) else dur - u["end"]
        joined = segs and i - 1 not in cut and i and gap_b <= p["max_pause"]
        if joined:
            segs[-1]["text"] += " " + u["text"]
        else:
            pre = min(p["lead_in"], gap_b) if not segs else min(p["target_pause"] / 2, gap_b / 2)
            if i and gap_b < 0.08:
                warnings.append(f"tight cut before '{u['text'][:30]}' (only {gap_b:.2f}s of silence)")
            segs.append({"start": max(0.0, u["start"] - pre), "text": u["text"]})
        last_kept = all(j in cut for j in range(i + 1, len(utts)))
        next_cut = i + 1 in cut or (i + 1 < len(utts) and gap_a > p["max_pause"])
        post = min(p["tail"], gap_a) if last_kept else min(p["target_pause"] / 2, gap_a / 2)
        if next_cut and not last_kept and gap_a < 0.08:
            warnings.append(f"tight cut after '{u['text'][-30:]}' (only {gap_a:.2f}s of silence)")
        segs[-1]["end"] = min(dur, u["end"] + post)
    for s in segs:
        s["start"], s["end"] = snap(s["start"]), snap(s["end"])
    removed = [{"kind": cut[i][0], "reason": cut[i][1], "start": utts[i]["start"], "end": utts[i]["end"],
                "text": utts[i]["text"]} for i in sorted(cut)]
    for i in range(len(utts) - 1):
        gap = utts[i + 1]["start"] - utts[i]["end"]
        if gap >= p["long_pause"]:
            removed.append({"kind": "pause", "reason": f"{gap:.1f}s of silence", "start": utts[i]["end"],
                            "end": utts[i + 1]["start"], "text": ""})
    removed.sort(key=lambda r: r["start"])
    out_dur = sum(s["end"] - s["start"] for s in segs)
    return {"source": words_json["source"], "fps": fps, "duration_src": dur, "duration_out": round(out_dur, 3),
            "keep": segs, "removed": removed, "warnings": warnings,
            "utterances": [{"i": i, "start": u["start"], "end": u["end"], "text": u["text"],
                            "action": "cut" if i in cut else "keep",
                            "why": cut[i][1] if i in cut else ""} for i, u in enumerate(utts)]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default="styles/default.md")
    ap.add_argument("--drop", default="")
    ap.add_argument("--keep", default="")
    a = ap.parse_args()
    ints = lambda s: [int(x) for x in s.split(",") if x.strip()]
    edl = build(read_json(a.words), load_style(a.style), ints(a.drop), ints(a.keep))
    write_json(a.out, edl)
    print(f"{'#':>2}  {'start':>6} {'end':>6}  action  text")
    for u in edl["utterances"]:
        print(f"{u['i']:>2}  {u['start']:6.2f} {u['end']:6.2f}  {u['action'].upper():6}  {u['text']}"
              + (f"   <- {u['why']}" if u["why"] else ""))
    for r in edl["removed"]:
        if r["kind"] == "pause":
            print(f"    {r['start']:6.2f} {r['end']:6.2f}  CUT     [{r['reason']}]")
    for w in edl["warnings"]:
        print("WARNING:", w)
    print(f"\n{edl['duration_src']:.2f}s -> {edl['duration_out']:.2f}s in {len(edl['keep'])} segments -> {a.out}")
