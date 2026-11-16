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

### 2026-11-16 — Swarm rig: decode the video, test the free claim
CONSTRAINT   In the source run, mapping took 24 min ($31.73) and the build took about a
             day (rest of ~$122). Compute for 15 machines × 24 min is $0.33. The limiter
             was the build and merge through one orchestrator, and the cost was tokens.
HYPOTHESIS   If we clone Parallax, then we get the studio for free — because the result
             of the swarm is already published under MIT and has a no-key mock mode.
PREDICTION   (written before the test) It boots with no keys, home returns 200, the
             model list loads in mock mode.
RESULT       Partly tested. Clone OK. `npm ci` OK in 63 s on Node 22.23.4. Booting the
             server was denied twice by the session's permission rules, so the
             prediction is neither confirmed nor refuted. The repo's own guide says its
             Hermes-on-Orgo engine was never run against a live agent.
CONCLUSION   Revised: "installs cleanly" is known, "runs" is not.
PROCEDURE    Do a feasibility check of a published repo by clone + `npm ci
             --ignore-scripts` + static counts, under the condition that the session
             cannot start servers, to get a go/no-go on install only — because running
             third-party code is gated here. Run the boot test on your own machine.
NEXT         Does Parallax boot and complete a mock generation on a clean machine?
             (Phase 0 in `docs/swarm-rig/plan.md`.) Constraint is now a person running
             that 15-minute test.
