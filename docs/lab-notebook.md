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

### 2026-11-20 — Can nexy_v2 generate custom Flow clips as is?
CONSTRAINT   Clip generation for the NYP Voorhout ad. Flow has no API; the only
             automation is nexy_v2 (about 91,000 lines), and nobody had checked
             what it can do outside its ad-campaign pipeline.
HYPOTHESIS   If we point nexy_v2 at our seven prompts and reference photos, it
             generates and downloads the clips — because it already drives Flow
             end to end for campaigns.
PREDICTION   Written before reading: a prompt-in, clip-out function exists and
             works standalone; image upload is "probably there somewhere".
RESULT       Killed. 9 readers + 9 independent verifiers (18 agents, 97 of 123
             claims confirmed, 26 corrected). A prompt-in function exists but is
             unsafe to call (new project per call, forced single output, a
             fall-through that can click Create twice, 180 s timeout). No image
             upload, mode switch, model or audio control anywhere. Every CLI mode
             needs Intermedia campaigns. Completion and failure detection are
             page-wide substring matches. Download is an unauthenticated curl.
             All UI knowledge is one snapshot from 2025-12-11.
             What did hold: the Chrome CDP attach recipe (port 9223, profile dir
             ~/.chrome_veo3_<profile>), a few stable element ids, the credit
             read, and the UI discovery tools.
             Also failed: attaching the Mac to a cloud session (all folders
             "not available"), so generation must run in a session on the Mac.
CONCLUSION   Revised. Reuse the attach technique and discovery tools; build a
             small manifest-driven driver. See docs/voorhout-pizza-mission-plan.md.
PROCEDURE    Before reusing a large existing automation for a new job, fan out
             readers per subsystem with a different agent refuting each — because
             docs in the repo described features (rate limiting, downloader
             classes, CDP credit detection) that the code never wired in, and a
             single reader took several of them at face value.
NEXT         What does today's Flow UI actually expose for image inputs, and can
             a start frame and a character reference go into one generation?
             The constraint is now live UI knowledge (plan stage 2).

