# Swarm rig — observations and plan

Goal: own the setup from the video (see `video-breakdown.md`) so that an orchestrator
can fan agents out over many cloud computers, map a product into a spec, and build
from it. And have a working image, video and audio studio the agents can drive.

Status: **planning done, nothing bought, nothing running.** Last updated 2026-11-16.

## 1. Observations (measured on 2026-11-16)

| # | Observation | How it was checked |
|---|---|---|
| O1 | Parallax is public, MIT, one commit, 900 files, about 60,700 lines under `src/`, 168 API routes, 41 pages, 12 migrations, 33 test files | Cloned and counted |
| O2 | `npm ci` succeeds on Node 22.23.4 in 63 seconds (run with install scripts off) | Ran it |
| O3 | **Not checked:** that the app boots and serves pages in mock mode. Starting the server was blocked by this session's permission rules | Two attempts, both denied |
| O4 | Parallax talks to one media gateway only (`src/server/treg.ts`), with a daily spend cap setting (`TREG_DAILY_BUDGET_USD`, default 5 in `.env.example`) | Read the code and settings |
| O5 | Parallax's own guide says its Hermes-on-Orgo chat engine has never been run against a live agent | `docs/hermes-on-orgo.md` |
| O6 | Parallax's `CONTRIBUTING.md` is the rulebook the build agents worked from: one feature per set of paths, one way to start a generation, a test file and an API doc per feature | Read it |
| O7 | Orgo: Medium (2 vCPU, 8 GB) costs $0.055 per hour running. Free accounts get $5 credit and one Medium Linux computer at a time. Paid plans start at $29 per month. Paid accounts can hold 50 computers | `docs.orgo.ai/llms-full.txt` |
| O8 | Orgo has an API for everything the video does: create a computer from `template_ref`, run bash on it, open a public URL on a port | Same source |
| O9 | T3 Code is free and open source and drives Claude Code. It is a control panel, not a requirement | `t3.codes` |
| O10 | In the video, mapping took 24 minutes and $31.73. The build took most of a day and the rest of about $122 | Video description |

### What follows from the numbers

- **Computers are not the cost.** 15 Medium machines for 24 minutes is 15 × 0.4 h × $0.055
  = **$0.33**. The $31.73 was model usage. Budget for tokens, not machines.
- **Mapping is not the slow part.** 24 minutes of mapping, then roughly a day of
  building and merging. The rate limiter in his run was the build and the merge
  through one orchestrator (Law 2). Fifteen computers made the fast part faster.
- **For Higgsfield-style features there is nothing left to map.** The result is
  already published. Re-running his swarm against the same site would buy a spec we
  already have, at $31 and a terms-of-service risk.

## 2. Open questions (each must be a yes/no or a number)

| # | Question | Cheapest test |
|---|---|---|
| Q1 | Does Parallax boot and complete a mock generation on a clean machine? | Phase 0 |
| Q2 | What does one real image and one real 5-second video cost through Treg? | Phase 1 |
| Q3 | Can one Claude Code worker on one Orgo computer map one feature into a spec a second agent can build from, and at what cost? | Phase 2 |
| Q4 | Does a free or $29 Orgo account allow custom templates and 15 machines at once? | Read the plan page at signup, then Phase 3 |
| Q5 | Can this Claude Code cloud session be the orchestrator (reach `www.orgo.ai`), or is T3 Code on a dev box needed? | Phase 2, step 1 |

## 3. Plan

Each phase has a gate. Do not start a phase until the one before it passed. Write
the prediction in `docs/lab-notebook.md` before running each test.

### Phase 0 — Parallax running in mock mode (free, about 15 minutes)

1. On your own computer (Node 22.13 or newer):
   `git clone https://github.com/nickvasilescu/parallax.git && cd parallax && npm ci && PARALLAX_DEMO_SEED=1 npm run dev`
2. Open `http://localhost:3000`, generate one image, one video and one audio clip.
3. Run `npm run build && npm test`.

Gate: the three generations return sample files and the tests pass. If not, log what
broke. That answers Q1.

### Phase 1 — real generations, capped (about $5)

1. Create a Treg account and one key. Put it in `.env.local` as `TREG_TOKEN`.
2. Set `TREG_DAILY_BUDGET_USD=5`.
3. Generate one image and one 5-second video. Record model, price shown, price charged.

Gate: both files are real and the charged price matches the shown price. Answers Q2.
Compare the cost per clip with what the Higgsfield plan already costs. If Higgsfield
is cheaper per clip for the car ads, keep using it and treat Parallax as the
agent-drivable backup.

### Phase 2 — one worker on one cloud computer (inside Orgo's $5 free credit)

Target: something we own, for example the car ads site in this repo. Not a
third-party site behind a login.

1. Create an Orgo account and API key. Give the key to the orchestrator session
   through the credential form, never in chat. Check the session can reach
   `www.orgo.ai`. Answers Q5.
2. Create one Medium Linux computer. Install Claude Code on it with the bash API.
3. Send it the worker contract from section 4 for one feature.
4. Have a second agent try to refute the spec: can it rebuild the feature from the
   spec alone?
5. Record minutes, model cost, and how many times a person had to step in.

Gate: the verifier rebuilds the feature without asking questions. Answers Q3. This
number, cost and minutes per feature, decides whether 15 machines are worth it.

### Phase 3 — template and fan-out (first paid step, one-way door)

Pre-mortem, assume it failed. Likely causes: the plan tier does not allow custom
templates or 15 machines (Q4); a secret baked into the template leaks; machines are
left running; agents hit a CAPTCHA and stall.

1. Write the template file: Medium, Claude Code, the worker tooling pre-installed
   (the video's own lesson at 9:17), a spend-capped key. No personal cookies.
2. Boot 3 machines from it, three features. Then 15.
3. Orchestrator stops every machine when its worker returns, and lists what is still
   running at the end.

Gate: 3 of 3 specs pass verification before going to 15.
Evidence that would change the plan: Phase 2 shows mapping one feature costs under
$1 and 5 minutes on one machine. Then run features one after another and skip the fleet.

### Phase 4 — build from the spec

1. The orchestrator writes the shared core first, alone: database, auth, jobs, design
   tokens, and a `CONTRIBUTING.md` like Parallax's (O6).
2. Then one build agent per feature, each inside its own paths, each returning code,
   a test file and an API doc.
3. A different agent verifies each feature. The orchestrator merges only what passed.

Gate: the build, type check and all feature tests pass on a clean clone.

## 4. Contracts (reusable)

### Orchestrator prompt

```
You are the orchestrator. Target: <product we own or may automate>.
Workspace: <Orgo workspace>. Template: <namespace/name@version>.
1. List the target's features or pages. One feature per worker, at most <N> workers.
2. For each worker: create a computer from the template, send the worker contract,
   wait for the result file, then stop the computer.
3. Run a smoke test on one worker before launching the rest.
4. Give each returned spec to a verifier agent that tries to refute it.
5. Merge the specs that passed into one product spec. List what failed and why.
Limits: at most <N> computers, at most $<budget>, stop everything after <T> minutes.
Never enter credentials, pay for anything, or post content on the target.
Report: features mapped, failed, minutes, cost, computers still running (must be 0).
```

### Worker contract

```
Input: the feature "<name>" at <URL>. Touch only this feature. Do not change settings,
buy, post or delete anything.
Deliverable: /work/spec-<feature>.md with these sections:
  Purpose · Screens and states · Every control with its options and defaults ·
  Each user action and what the app does · Data the feature stores ·
  Error and empty states · Open questions.
Describe behaviour in your own words. Do not copy the target's text, names or images.
Acceptance: every control on the screen appears in the spec. Every action lists a
result. If you are blocked (login, CAPTCHA, paywall), stop and write BLOCKED with the
reason at the top of the file.
```

### Verifier contract

```
Input: one spec file and the acceptance rules above. Try to refute it.
Return JSON: {feature, verdict: pass|fail, missing: [...], contradictions: [...],
could_build_from_this: true|false}.
```

## 5. What we already have without buying anything

| His piece | Ours |
|---|---|
| T3 Code plus an always-on dev box | A Claude Code cloud session |
| 15 workers | Parallel subagents (Law 3 in `CLAUDE.md`), without a desktop browser each |
| Higgsfield-style studio | Parallax (once Q1 passes), and the Higgsfield connector on the account |
| Model gateway | Treg key, or the Higgsfield plan |
| The missing part | Cloud computers with a real desktop browser: Orgo, Phase 2 onward |

## 6. Rules we keep

- Secrets go in through credential forms and spend-capped keys. Never baked into a
  template with personal cookies.
- Swarms run against products we own or have permission to automate.
- Build clean-room: own wording, names and artwork (Parallax's own rule, O6).
- Every paid step has a budget and a list of machines that must be stopped at the end.
