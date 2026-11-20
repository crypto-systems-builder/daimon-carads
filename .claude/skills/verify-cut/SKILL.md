---
name: verify-cut
description: Prove a cut is clean by re-transcribing it and checking words, removed lines, pauses, joins, clipped edges and sync. Use after every cut and before any approval or render.
---

# Verify cut

`python3 engine/verify_cut.py <project>/work/words.json <project>/work/edl.json <project>/work/cut.mp4 --out <project>/work/verify.json`

Add `--truth <file>.truth.json` when the recording is a generated test with planted mistakes.

| Check | Fails when |
|---|---|
| words | the cut does not say exactly the kept words (a word was clipped, lost or added) |
| removed | a removed line can still be heard, or a removed pause survives |
| pauses | a silence longer than the pacing limit remains |
| joins | a cut lands where the audio is not silent |
| edges | a kept segment starts or ends within 30 ms of a word |
| sync | picture and sound differ in length by more than a frame |
| truth | (test recordings) a planted mistake survives or a good line was lost |

Exit code 0 means every check passed. On any FAIL: do not approve, do not render. Fix the
cut list with the rough-cut skill and verify again.

What this cannot tell you: whether the choice of what to cut was right. It proves the
cut matches the cut list and is technically clean. Judgment is the checkpoint's job.
