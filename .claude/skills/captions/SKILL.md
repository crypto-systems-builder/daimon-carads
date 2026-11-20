---
name: captions
description: Build word-by-word captions and the hook title for a verified cut. Use after a cut is approved, or when asked to add or restyle captions.
---

# Captions

`python3 engine/captions.py <project>/work/cut.words.json --out <project>/work/captions.ass --title "<hook>"`

- `cut.words.json` is written by the verify-cut step: the cut's own word timings.
- The title follows the playbook: the claim in seven words or fewer, true on its own.
  Leave `--title` off for no title.
- Look comes from the style file's `captions` and `title` blocks (font, size, colours,
  position, words per chunk). Change the style file, not the script.
- If the transcript misspells a name, fix the word text in `cut.words.json` before
  running this. Leave the timings alone.
