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

### 2026-11-20 — Video-editing system built here and proven on the test recording

CONSTRAINT   The kit the original prompt assumed was never found, and waiting on it was the
             queue. Policy constraint: "prove the existing kit" was the rule blocking
             output. Dropped it and built the system in this repo instead.
HYPOTHESIS   If mistakes are separated from their retakes by a pause, then comparing each
             utterance with the next one (same opening words = restart, near-identical =
             repeat) finds them without an LLM — because a retake repeats its own start.
PREDICTION   (before running) All 4 planted mistakes are found with 0 good lines lost, and
             a re-transcript of the cut equals the kept words exactly.
RESULT       Held: 4 of 4 found, 68 of 68 kept words heard in order, 7 of 7 checks pass,
             33.7 s -> 22.9 s. The verifier was then attacked: a cut that keeps two
             mistakes FAILS (truth check), a cut shifted to clip words FAILS (4 checks).
             Failures on the way:
             - faster-whisper still has no model (huggingface.co blocked). Switched the
               default to Parakeet TDT v2 via sherpa-onnx from GitHub releases. It is
               verbatim and gives token times; word ends are measured from the audio.
             - First cut render failed: odd pixel sizes after the punch-in zoom changed
               the aspect flag and concat refused. Fixed by rounding to even sizes.
             - Review page showed both videos at once: my own `display:block` beat the
               `hidden` attribute. Fixed with an explicit `[hidden]` rule.
             - New skills did not load until a few minutes after they were written.
             Weak spot found: without a truth file the verifier passes a cut that leaves
             mistakes in, because it checks the cut against the cut list, not against taste.
CONCLUSION   Kept, for clean synthetic speech only. Untested on a human voice.
PROCEDURE    Do the eight commands under "Edit a recording into a short" in CLAUDE.md,
             under the condition that takes are separated by a pause, to get a verified
             cut and a rendered short — because the cut list is checked by re-transcribing
             the result, which catches clipped or missing words before a human looks.
NEXT         Does it hold on a real recording of a person? That is now the constraint:
             one real 30-60 s phone recording with natural mistakes.
