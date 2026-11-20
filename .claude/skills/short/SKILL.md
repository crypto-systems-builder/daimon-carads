---
name: short
description: Turn a raw talking-head recording into a finished vertical short, end to end. Use when the user runs /short, gives a recording to edit, or asks for a short, reel or TikTok from a video file.
---

# /short <path to recording>

Runs the whole pipeline in `playbook.md`. Read `playbook.md` and the style file first.
Run every command from the repository root.

Set `P=projects/<name>`; the recording is `$P/raw/<file>`. If the user gave a file
somewhere else, copy it into a new `projects/<name>/raw/`.

1. **Transcribe** (skill: transcribe)
   `python3 engine/transcribe.py $P/raw/<file> --out $P/work/words.json`
2. **Propose the cut** (skill: rough-cut)
   `python3 engine/propose_cuts.py $P/work/words.json --out $P/work/edl.json`
   Read the full transcript against the playbook. Adjust with `--drop` / `--keep`.
3. **Cut**
   `python3 engine/apply_cuts.py $P/raw/<file> $P/work/edl.json --out $P/work/cut.mp4`
4. **Verify** (skill: verify-cut)
   `python3 engine/verify_cut.py $P/work/words.json $P/work/edl.json $P/work/cut.mp4 --out $P/work/verify.json`
   If it fails, fix the cut list and repeat from step 2. Never continue on a FAIL.
5. **CHECKPOINT.** Show the user the utterance table and the verify result. Check every
   factual claim in the kept transcript and report anything unconfirmed. Stop and wait
   for approval. Do not approve it yourself unless the user said so for this run.
6. **Captions** (skill: captions)
   `python3 engine/captions.py $P/work/cut.words.json --out $P/work/captions.ass --title "<hook>"`
7. **Render** (skill: render)
   `python3 engine/render.py $P/work/cut.mp4 $P/work/captions.ass --out $P/out/final.mp4`
8. **Look at it.** Extract a few frames and view them; confirm captions sit where the
   style says and nothing is clipped.
9. **Review page** (skill: review-page)
   `python3 engine/review_page.py $P --title "<hook>" --approved-by "<who approved>"`
10. **Report**: where `final.mp4` and the review page are, what was cut, what failed.

Use `--style styles/<name>.md` on steps 2, 3, 4, 6, 7 and 9 for a non-default look.
Never post or schedule the result. No paid generation unless asked for this run.
