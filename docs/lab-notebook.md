# Lab Notebook

Append-only log of non-trivial passes through the loop in `CLAUDE.md`. Newest at
the bottom. Read before starting related work. Failures belong here — they are the map.

## Entry template

```
### <date> — <short title>
CONSTRAINT   what limited output here, measured (Law 2)
HYPOTHESIS   If X, then Y — because Z
PREDICTION   written before the test
RESULT       what happened, including what didn't fit
CONCLUSION   kept / killed / revised
PROCEDURE    Do X, under condition C, to get Y — because Z
NEXT         the next question, and where the constraint moved
```

## Entries

### 2026-11-19 — Video-editing system proof run: stopped at step 1, test recording built

CONSTRAINT   Input, not capacity. The system to be proven is not in this repo:
             `.claude/skills/` holds 1 skill (`scientific-method`), not 7. There is
             no `playbook.md`, no `styles/default.md`, no `/short` or `review-page`
             skill, no `engine/`, and `CLAUDE.md` has no "Working commands" or
             "Status" section. Checked `main` plus all 7 other remote branches.
HYPOTHESIS   If each scripted line is synthesized on its own and joined with known
             gaps, then a recording with exactly-known mistakes comes out — because
             segment times are measured at build time instead of guessed afterwards.
PREDICTION   (held before transcribing) Whisper hears both restarts and the repeated
             sentence twice each; silencedetect finds exactly one pause >= 2.5 s.
RESULT       Held. 33.71 s, 1080x1920, 30 fps. `verify_recording.py`: 4/4 PASS, one
             3.02 s silence at 17.66-20.68 s. Failures and workarounds on the way:
             - `say` does not exist on Linux (cloud sessions). Used ffmpeg's built-in
               `flite` filter. The `--engine say` path is written but NOT run.
             - `pip install faster-whisper` works (1.2.1) but it cannot load a model:
               huggingface.co is denied by this environment's network policy (403).
             - Worked around with `sherpa-onnx` + Whisper small.en from GitHub
               releases, which the policy allows. Text only, no word timestamps tested.
             - A read-only look for the kit in two other repos was denied by policy.
             - Not done, because they need the kit: engine setup and 3 s test render,
               the `/short` run, the cut approval, the review page.
CONCLUSION   Recording hypothesis kept. The proof run itself is unstarted, not failed.
PROCEDURE    Do `python3 projects/test-short/make_test_recording.py`, under the
             condition that ffmpeg has the flite filter (Linux) or with `--engine say`
             (macOS, untested), to get `raw/test-recording.mp4` plus
             `raw/test-recording.truth.json` listing every segment as keep/cut —
             because a cut can then be scored against ground truth instead of by ear.
             To transcribe where huggingface.co is blocked: follow the setup lines at
             the top of `projects/test-short/verify_recording.py`.
NEXT         Where does the kit live? Bring it into the session (private repo, or run
             on the Mac), then re-run the proof from step 1. In a cloud session the
             next constraint is already known: allow huggingface.co or faster-whisper
             has no model.
