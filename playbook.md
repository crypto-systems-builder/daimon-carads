# Playbook: how a short gets edited here

The rules the skills follow. `CLAUDE.md` says how work is done in this repo; this
file says what a good short is. `styles/default.md` says what it looks like.

## The pipeline

```
raw recording
  -> transcribe      word-by-word transcript with timings
  -> rough-cut       propose what to remove, then cut it
  -> verify-cut      re-transcribe the cut and prove it is clean
  -> CHECKPOINT      a human approves the cut           <- nothing is rendered before this
  -> captions        word-by-word captions and a hook title
  -> render          captions, title, progress bar, loudness, optional music
  -> review-page     one page to watch it, see every cut, and give feedback
```

Each project lives in `projects/<name>/`: `raw/` (the recording), `work/` (transcript,
cut list, verification), `out/final.mp4`, `review/` (the review page).

## What to cut

1. **False starts.** The speaker begins a line, stops, and begins it again. Keep the
   complete take. If two complete takes exist, keep the last one.
2. **Repeated sentences.** Keep the last take unless an earlier one is clearly better.
3. **Long pauses.** Anything over 0.45 s is tightened to 0.28 s.
4. **Filler on its own.** A lone "um" or "uh" between sentences goes.
5. **Anything off-topic** that is not part of the point: throat clearing, "okay, take
   two", talking to someone off camera.

## What never to cut

- A word in the middle. Cuts land on silence, never inside speech.
- A pause that is doing a job (before a punchline, after a question). Say so at the
  checkpoint instead of removing it.
- Facts. If a cut changes what a sentence claims, do not make it.

## The checkpoint

The cut is shown to a human before anything is rendered: the numbered table from
`propose_cuts.py` and the result of `verify_cut.py`. Render only after they say yes.
Claude does not approve its own cut unless the human said so for that specific run,
and then only if every verification check passes.

The mechanical proposal is a first draft. Read the whole transcript yourself. It only
catches a restart or repeat when there is a gap before the retake; a stumble inside a
flowing sentence needs your judgment (`--drop`, `--keep`).

## Facts

Every checkable claim in a short is checked before the checkpoint. If one cannot be
confirmed, say so at the checkpoint. The hook title must be true on its own.

## Captions and title

- Two or three words on screen at a time, the spoken word highlighted.
- The title is the claim in seven words or fewer. No clickbait the video does not pay off.

## Music

If `assets/music/` holds an audio file, the first one is mixed in quietly under the
voice. If the folder is empty, there is no music. Only use music you have the rights to.

## Hard limits

- **No paid generation** (Higgsfield, stock, voice, music) without being asked for that run.
- **Never post, publish or schedule** anything to a social platform. The pipeline ends
  at the review page.
- **This repository is public.** Do not commit recordings of real people here.
