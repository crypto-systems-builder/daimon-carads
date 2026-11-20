---
name: rough-cut
description: Decide what to remove from a recording (false starts, repeated sentences, long pauses, filler) and cut it. Use after transcribing, or when asked to clean up, tighten or remove mistakes from a recording.
---

# Rough cut

1. `python3 engine/propose_cuts.py <project>/work/words.json --out <project>/work/edl.json`
   prints a numbered table: every utterance, KEEP or CUT, and why.
2. Read the whole transcript against "What to cut" and "What never to cut" in
   `playbook.md`. The script is a first draft: it finds a restart or repeat only when a
   pause separates the takes. Overrule it by re-running with `--drop 3,7` (cut more) or
   `--keep 4` (restore).
3. Act on any `WARNING: tight cut` line: that cut has almost no silence to land on.
   Listen to it, or keep the neighbouring utterance.
4. `python3 engine/apply_cuts.py <recording> <project>/work/edl.json --out <project>/work/cut.mp4`
5. Always follow with the verify-cut skill.

Pacing numbers (pause limits, punch-in zoom) come from the style file's `pacing` block.
