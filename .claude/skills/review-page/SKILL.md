---
name: review-page
description: Build the review page for a finished short - player, raw recording, every cut, verification checks, transcript and a feedback box. Use after rendering, or when asked for a review page.
---

# Review page

`python3 engine/review_page.py <project> --title "<hook>" --approved-by "<who approved the cut>"`

Writes `<project>/review/index.html` with `final.mp4` and `raw.mp4` beside it. The folder
opens in any browser as-is.

On the page: the finished short, the raw recording, a to-scale timeline of what was kept
and removed, a "Play in raw" button for each removed item, the verification checks, a
clickable transcript, file specs, and a notes box whose "Copy feedback" button produces
text to paste back to Claude.

In a Claude cloud session, also publish it so it can be opened from a phone: publish
`review/index.html` with the Artifact tool, passing `final.mp4` and `raw.mp4` as
supporting files under those same names.

When feedback comes back, apply it with the rough-cut or captions skill, re-verify,
re-render, and rebuild this page.
