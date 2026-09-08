---
name: scientific-method
description: "Apply the scientific method, constraint theory, and tiered agent execution to any non-trivial task — research, planning, debugging, implementation, or optimization. Use when the user wants to figure out WHY something works or fails, find and eliminate a bottleneck or rate limiter, reverse-engineer someone else's success into a repeatable procedure, decide between approaches with evidence instead of opinion, plan work before executing it, or scale execution across parallel subagents. Triggers on: 'why is this slow', 'what's the bottleneck', 'figure out how X works', 'how did they do it', 'test this', 'prove it', 'make a plan', 'scale this up', 'brute force it', 'is this actually working', or any request where the honest answer starts with a guess."
---

# Scientific Method / Constraint / Scale

Three laws, run in order. Full doctrine: `CLAUDE.md` at repo root.

**Route first — don't run all three by reflex:**

| Situation | Start at |
|---|---|
| "Why does this work / fail?" · "How did they do it?" · "Is this real?" | **Law 1** |
| "This is too slow" · "How do we scale?" · "Where do we invest?" | **Law 2**, then Law 1 |
| "Build / implement / research this" | **Law 3**, with Law 1 on the uncertain parts |

Trivial, reversible, single-step tasks: just do them. Don't ceremony a one-liner.

---

## LAW 1 — Test before you believe

Fill this in **in order**. Steps 3 and 4 are written *before* the test runs.

```
OBSERVE      <measured facts — numbers, not impressions>
QUESTION     <one question, answerable yes/no or with a number>
HYPOTHESIS   "If X, then Y — because Z."      ← must name a mechanism
PREDICTION   <what you'll see if true; what you'll see if false>
TEST         <cheapest experiment that could FALSIFY it>
RESULT       <what actually happened, including what didn't fit>
CONCLUSION   Kept / Killed / Revised → next question:
```

Hard rules:

- **Prediction before test.** Written after = rationalization, not evidence.
- **Design to kill, not confirm.** Ask "what would I see if I'm wrong?" If
  nothing would look different, it's not a test.
- **One variable at a time.** Batched changes buy results you can't attribute.
- **Rank tests by `information ÷ cost`.** Run the most decisive per unit cost —
  not the most thorough.
- **Log failures.** They're the map. Deleting them is why dead ends get re-run.

### Brute force → hypothesis

Brute force is legitimate as *data collection*, never as the endpoint.

```
1. Sweep the space — LOG EVERY VARIABLE PER TRIAL
2. Cluster the winners → what do they share?
3. That shared trait IS the hypothesis
4. Now run Law 1 properly on it
```

An unlogged brute-force win is unreproducible, which means it's worth nothing.
Never stop at "it worked."

### Extracting a real clue from someone else's success

Success leaves clues; most are decoys. The winner did 40 things — 38 irrelevant,
1 causal, 1 luck.

1. **Multiple independent winners** share it? (One case = anecdote.)
2. **Check the losers.** Did failures do it too? → not causal. *This step is
   almost always skipped and it's the one that does the work.*
3. **Name the mechanism.** No plausible *why* → correlation, move on.
4. **Test removal.** Take it out — does the result survive? Then it wasn't
   load-bearing.
5. **Write it as a procedure**, or it's a story.

Output form: `Do X, under condition C, to get Y — because Z.` Anything less
isn't knowledge yet.

### One-way doors

Irreversible / public / expensive-to-undo → cheap falsification isn't available.
Substitute: smallest reversible version first · pre-mortem (assume it failed,
write why, test that cause) · pick the option preserving most future options —
and **record what evidence would have changed your mind**, then check it later.

---

## LAW 2 — Find the rate limiter, kill it

One binding constraint sets throughput. Work anywhere else yields zero output
gain. The question:

> **What single thing, if 10× better, would 10× the output — measured, not guessed?**

### Cycle

1. **IDENTIFY** — measure. *Where does work pile up and wait?* The constraint is
   where the queue is. Never guess: attention lands on the loud thing, the real
   constraint is usually silent.
2. **EXPLOIT** — more output from it, **spending nothing.** Stop it idling, stop
   feeding it junk, strip non-constraint work off it. Most "need more capacity"
   dies here for free.
3. **SUBORDINATE** — everything else serves it. Slow non-constraints down if it
   keeps the constraint fed. A non-constraint at 100% builds inventory, not output.
4. **ELEVATE** — *now* spend: resources, agents, rebuild, automate, buy.
5. **REPEAT — it has moved.** Re-measure. Optimizing yesterday's bottleneck is
   the classic waste.

### Triage — check top row first

| Type | Tell | Fix |
|---|---|---|
| **Policy** | "We always…" / "have to wait for…" — a rule nobody rechecked | Free. Delete it |
| **Capacity** | Genuinely saturated | Exploit → elevate |
| **Skill** | Only one person/agent can do it | Document → parallelize |
| **Attention** | Everything blocked on review/decision | Structure output for fast review, or push the decision down |
| **Input quality** | Constraint burns time rejecting bad input | Fix upstream — best ROI here |

Rules: instrument before optimizing (can't measure → *that's* the constraint) ·
loudest ≠ binding · one at a time, not "top 3" · re-measure right after a break ·
log the ceiling you raised.

---

## LAW 3 — Plan expensive, execute cheap and wide

| Phase | Who | Output |
|---|---|---|
| Frame | Opus 5 / Fable 5 | Question, hypothesis, constraint |
| Plan | Opus 5 / Fable 5 | Decomposed tasks + contracts + acceptance criteria |
| Execute | Sonnet 5 × 5–15 parallel | Structured results against contract |
| Verify | A **different** agent than the producer | Confirm / refute, with evidence |
| Synthesize | Opus 5 / Fable 5 | Decision, next question, doctrine update |

**Top-tier model writes the plan before any fan-out.** Cheap models execute a
precise plan well and author one badly. Fanning out an unclear plan multiplies
ambiguity by agent count.

### Subagent contract — all four fields, every time

```
INPUT       exact files/paths/scope — what it may touch, what it may not
DELIVERABLE exact return shape (schema/fields/format), not "a summary"
ACCEPTANCE  how IT knows it succeeded before returning
BOUNDARIES  no shared mutable state with siblings
```

Vague prompt × 15 agents = 15× garbage, paid for in review time.

### Fan out / don't

**Do:** parallel search across many files · N variants of an asset · per-item
transforms · multi-angle research · independent verification of N findings.

**Don't:** serially dependent tasks (agent 2 needs agent 1's output) · agents
editing the same files (merge cost > parallelism gain) · one indivisible
judgment call.

Serial dependency → pipeline it (each item flows through all stages
independently) rather than barrier-syncing every stage.

### The trap

15 agents → 1 reviewer reading 15 outputs = **you moved the bottleneck into
review** (Law 2 biting). Defaults: structured checkable output, never essays ·
**verification fans out too**, each verifier prompted to *refute* · producer
never verifies itself · escalate only survivors to the expensive model.

---

## Closing the loop

Every pass leaves behind **one written, repeatable procedure** — appended to
`CLAUDE.md` or a doc, stated as `Do X, under condition C, to get Y — because Z`.
The accumulation is the asset. Individual wins are not.

```
Law 2 → what's the constraint?          (measure)
Law 1 → hypothesis + test that could kill it
Law 3 → plan top-tier, execute wide, verify independently
Law 1 → did the prediction hold? log it, failures included
Law 2 → re-measure, it moved
```
