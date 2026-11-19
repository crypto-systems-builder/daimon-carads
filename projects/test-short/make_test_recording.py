#!/usr/bin/env python3
"""Build a synthetic talking-head test recording with planted mistakes.

Output:  projects/test-short/raw/test-recording.mp4   (1080x1920, 30 fps, AAC)
         projects/test-short/raw/test-recording.truth.json  (ground truth)

The ground-truth file lists every spoken segment with start/end times and
whether an editor should KEEP or CUT it, so a cut can be checked against
something objective instead of by ear.

Speech engine: ffmpeg's built-in `flite` filter (Linux). On macOS, pass
--engine say to use the `say` command instead.

Usage:  python3 projects/test-short/make_test_recording.py [--engine flite|say]
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SR = 48000

# The fact (checkable): the first iPhone went on sale 29 June 2007 with no
# App Store; the App Store opened 10 July 2008 with 500 apps.
#
# (kind, text, silence_after_seconds)
#   keep     - belongs in the final cut
#   restart  - false start; the next line says it again properly  -> CUT
#   repeat   - an exact repeat of the previous sentence           -> CUT
# The 3.0 s gap after the repeat is the planted long pause        -> CUT
SCRIPT = [
    ("keep",    "Here is a fact about the iPhone that surprises most people.", 0.35),
    ("restart", "When the first iPhone came out in.", 0.30),
    ("keep",    "When the first iPhone went on sale in June two thousand seven, it had no App Store.", 0.35),
    ("keep",    "You could not install a single app from another company.", 0.40),
    ("repeat",  "You could not install a single app from another company.", 3.00),
    ("restart", "The App Store only arrived a year.", 0.30),
    ("keep",    "The App Store only arrived in July two thousand eight, about a year later.", 0.35),
    ("keep",    "It opened with just five hundred apps.", 0.35),
    ("keep",    "So the phone that changed everything shipped without the thing it is famous for.", 0.50),
]
LONG_PAUSE_AFTER_INDEX = 4
LEAD_IN = 0.40


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def synth(text, out_wav, engine, tmp):
    """Speak one line to a mono 48 kHz wav, trimmed of leading/trailing silence."""
    rawf = tmp / (out_wav.stem + ".raw.wav")
    if engine == "say":
        aiff = tmp / (out_wav.stem + ".aiff")
        run(["say", "-o", str(aiff), text])
        run(["ffmpeg", "-y", "-i", str(aiff), str(rawf)])
    else:
        txt = tmp / (out_wav.stem + ".txt")
        txt.write_text(text)
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"flite=textfile={txt}:voice=slt", str(rawf)])
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB,areverse")
    run(["ffmpeg", "-y", "-i", str(rawf), "-af", trim, "-ar", str(SR), "-ac", "1", str(out_wav)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["flite", "say"], default="flite")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        t = LEAD_IN
        segments, inputs, parts = [], [], []
        inputs += ["-f", "lavfi", "-t", f"{LEAD_IN}", "-i", f"anullsrc=r={SR}:cl=mono"]
        parts.append("[0:a]")
        n = 1
        for i, (kind, text, gap) in enumerate(SCRIPT):
            wav = tmp / f"seg{i:02d}.wav"
            synth(text, wav, args.engine, tmp)
            d = duration(wav)
            segments.append({
                "index": i, "kind": kind, "action": "keep" if kind == "keep" else "cut",
                "text": text, "start": round(t, 3), "end": round(t + d, 3),
            })
            t += d
            inputs += ["-i", str(wav)]
            parts.append(f"[{n}:a]"); n += 1
            inputs += ["-f", "lavfi", "-t", f"{gap}", "-i", f"anullsrc=r={SR}:cl=mono"]
            parts.append(f"[{n}:a]"); n += 1
            if i == LONG_PAUSE_AFTER_INDEX:
                long_pause = {"start": round(t, 3), "end": round(t + gap, 3), "action": "cut"}
            t += gap
        total = t
        audio = tmp / "voice.wav"
        run(["ffmpeg", "-y", *inputs, "-filter_complex",
             "".join(parts) + f"concat=n={n}:v=0:a=1[a]", "-map", "[a]", str(audio)])
        total = duration(audio)

        font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not Path(font).exists():
            font = "/System/Library/Fonts/Helvetica.ttc"
        # Plain background, a framed "speaker" placeholder, and a burned-in
        # source timecode so every cut is visible when checking the edit.
        vf = (
            "drawbox=x=140:y=330:w=800:h=1000:color=0x2A3340:t=fill,"
            "drawbox=x=140:y=330:w=800:h=1000:color=0x5B6B80:t=6,"
            f"drawtext=fontfile={font}:text='SPEAKER':fontsize=96:fontcolor=0x9FB0C6:x=(w-text_w)/2:y=740,"
            f"drawtext=fontfile={font}:text='PLACEHOLDER':fontsize=64:fontcolor=0x6F8098:x=(w-text_w)/2:y=860,"
            f"drawtext=fontfile={font}:text='src %{{pts\\:hms}}':fontsize=44:fontcolor=0x6F8098:x=(w-text_w)/2:y=1380"
        )
        out = RAW / "test-recording.mp4"
        run(["ffmpeg", "-y",
             "-f", "lavfi", "-i", f"color=c=0x12161C:s=1080x1920:r=30:d={total:.3f}",
             "-i", str(audio), "-vf", vf,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-ar", str(SR), "-shortest", "-movflags", "+faststart",
             str(out)])

    truth = {
        "file": "test-recording.mp4", "engine": args.engine, "duration": round(total, 3),
        "fact": "First iPhone on sale 29 June 2007 with no App Store; App Store opened 10 July 2008 with 500 apps.",
        "planted_mistakes": {"restarts": 2, "repeated_sentences": 1, "long_pauses": 1},
        "long_pause": long_pause,
        "segments": segments,
        "clean_script": " ".join(s["text"] for s in segments if s["action"] == "keep"),
    }
    (RAW / "test-recording.truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    print(f"wrote {out}  ({total:.2f}s)")
    for s in segments:
        print(f"  {s['start']:6.2f}-{s['end']:6.2f}  {s['action']:4}  {s['kind']:8} {s['text']}")
    print(f"  long pause {long_pause['start']:.2f}-{long_pause['end']:.2f}  cut")


if __name__ == "__main__":
    main()
