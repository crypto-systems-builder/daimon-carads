# CLAUDE.md — Operating Doctrine

How work gets done in this repo. Three laws. They compose: Law 1 tells you how to
know something, Law 2 tells you what to point it at, Law 3 tells you how to move.

Applies to research, planning, implementation, and shipping. No exceptions for
"small" tasks — small tasks are where undisciplined habits get installed.

---

## Law 1 — Nothing is true until it survives a test that could have killed it

Opinion is free. Evidence is the only currency. Every non-trivial move follows
this loop, written down *in this order*:

| Step | Do | Fail if |
|---|---|---|
| 1. **Observe** | State the actual, measured situation. Numbers, not vibes. | You describe how it "feels" |
| 2. **Question** | One sharp question. Not a topic — a question. | It can't be answered yes/no or with a number |
| 3. **Hypothesis** | "If X, then Y — because Z." Names the mechanism. | It has no `because` |
| 4. **Prediction** | What you expect to see, **written before the test** | Written after. This is rationalization |
| 5. **Test** | Cheapest experiment that could *falsify* the hypothesis | The test can only confirm, never refute |
| 6. **Result** | What actually happened, including the ugly parts | You report only the parts that fit |
| 7. **Conclusion** | Kept, killed, or revised — and what the *next* question is | "Inconclusive" with no next question |

### The rules that make it real

- **Write the prediction before you run the test.** A prediction recorded after
  the fact is a story, not a result. This single rule does most of the work.
- **Design tests to kill, not to confirm.** Ask: "what would I see if I'm wrong?"
  If nothing could show you're wrong, you're not testing, you're decorating.
- **One variable at a time.** Change three things, learn nothing. If you must
  batch, you've bought a result you cannot attribute.
- **Log the failures.** Failed experiments are the map. They're deleted by
  default, which is why everyone re-runs the same dead ends forever.
- **Cheapest falsifying test first.** Order candidate tests by
  `information gained ÷ cost`. Run the top one. Not the most thorough — the most
  *decisive per unit of cost*.

### Brute force is a data-collection strategy, not a substitute for a hypothesis

Brute force is legitimate — when the search space is small enough to sweep and
you have no hypothesis yet. But it earns its keep **only if every trial is
logged with its variables.** An unlogged brute-force win is a lottery ticket:
it produced an outcome you cannot reproduce, which means it produced nothing.

The correct sequence:

```
no hypothesis → brute force the space, log every variable per trial
             → cluster the winners, find what they share
             → THAT is your hypothesis
             → now test it properly (Law 1, steps 3–7)
```

Brute force generates candidates. The scientific method promotes one to knowledge.
Never stop at "it worked."

### Success leaves clues — but most clues are decoys

"Success leaves clues" is true and it's the trap. The winner did forty things.
Thirty-eight were irrelevant, one was causal, one was luck. Copy all forty and
you have imported the noise, the cost, and none of the mechanism.

Extracting a real clue:

1. **Collect the pattern across multiple independent winners.** One case study
   is an anecdote. A trait shared by many *independent* winners is a signal.
2. **Check the losers.** Did they do it too? If failures did the same thing, it
   is not the causal variable. This step is skipped ~always, and it is the one
   that does the work.
3. **Name the mechanism.** *Why* would this cause the result? No plausible
   mechanism → treat it as correlation and move on.
4. **Test the removal.** Take the variable out. If the result survives without
   it, it was never load-bearing.
5. **Write it as a repeatable procedure**, or you have a story, not a method.

> A clue you cannot state as "do X, under condition C, to get Y — because Z"
> is not yet knowledge.

### When you can't run the test

Some moves are one-way doors: irreversible, public, or expensive to undo.
There, cheap falsification isn't available, so substitute:

- Find the smallest reversible version and test *that* first.
- Pre-mortem: assume it failed, write why. Then test that specific cause.
- Pick the option that preserves the most future options, and **write down what
  evidence would have changed your mind.** Check it later. That is how judgment
  compounds instead of just accumulating.

---

## Law 2 — Find the rate limiter. Everything else is decoration.

Every system has exactly **one** binding constraint at a time. Throughput is set
by that constraint alone. Improving anything else produces zero output gain — it
produces work-in-progress, which is cost wearing a costume.

This is the highest-leverage question available, in any domain:

> **What is the single thing that, if it were 10× better, would 10× the output —
> and what is it right now, measured, not guessed?**

### The five-step cycle

1. **IDENTIFY** — measure it. Where does work pile up and wait? The constraint is
   where the queue is. Guessing here is the #1 error: attention lands on what's
   *visible* or *annoying*, and the real constraint is usually silent.
2. **EXPLOIT** — get more out of the constraint *without spending anything*.
   Stop it idling. Stop feeding it junk it has to reject. Strip non-constraint
   work off it. **Most "we need more capacity" problems die here, for free.**
3. **SUBORDINATE** — every other part of the system serves the constraint. Run
   non-constraints at less than full speed if it keeps the constraint fed and
   unblocked. A non-constraint running at 100% is *manufacturing inventory*, not
   output.
4. **ELEVATE** — only now do you spend. More resources, more agents, rebuild,
   automate, buy. Spending before step 2 is how budgets die.
5. **REPEAT — the constraint has moved.** Go back to step 1 and re-measure. **Do
   not let inertia become the new constraint** — the classic failure is spending
   another quarter optimizing what *used* to be the bottleneck.

### Constraint triage

| Type | Looks like | Fix |
|---|---|---|
| **Policy** | A rule nobody has rechecked. "We always…", "you have to wait for…" | Free. Delete the rule. **Check for this first — most constraints are here** |
| **Capacity** | A genuinely saturated resource | Exploit, then elevate |
| **Skill/knowledge** | One person or agent is the only one who can do it | Document it, then parallelize it |
| **Attention** | Everything is blocked on review/decision | Structure the output so review is fast, or push the decision down |
| **Input quality** | The constraint burns time rejecting bad input | Fix upstream — highest ROI fix in the table |

### Non-negotiables

- **Instrument before you optimize.** Where does time actually go? If you can't
  measure it, your bottleneck is measurement — fix that first.
- **The loudest problem is rarely the constraint.** Neither is the most
  interesting one. Follow the queue.
- **One constraint at a time.** Splitting focus across "the top 3 bottlenecks"
  means starving the one that matters.
- **After the break, re-measure immediately.** New constraint, new cycle.
- **Log the ceiling you just raised**, so future-you knows the shape of the
  system instead of rediscovering it.

Law 2 without Law 1 is guessing at what's slow. Law 1 without Law 2 is rigorous
work on things that don't matter. Always both.

---

## Law 3 — Plan expensive. Execute cheap and wide.

Thinking and doing are different jobs with different cost curves. Stop paying
frontier prices for mechanical work, and stop letting cheap models make
architectural decisions.

### The split

| Phase | Who | Output |
|---|---|---|
| **Frame** | Opus 5 / Fable 5 | The question, the hypothesis, the constraint |
| **Plan** | Opus 5 / Fable 5 | Decomposed tasks + per-task contracts + acceptance criteria |
| **Execute** | Sonnet 5 fan-out — 5, 10, 15+ agents in parallel | Structured results against the contract |
| **Verify** | A *different* agent than the one that produced the work | Confirm / refute, with evidence |
| **Synthesize** | Opus 5 / Fable 5 | Decision, next question, updated doctrine |

**The plan is always made by the top-tier model before any fan-out.** Cheap
models are excellent executors of a precise plan and unreliable authors of one.
Fanning out an unclear plan multiplies the ambiguity by the agent count.

### Every subagent gets a contract

No prose dumps. A task handed to a subagent specifies:

- **Input** — exact files, paths, scope. What it may touch, what it may not.
- **Deliverable** — the exact shape of the return (schema, fields, format).
- **Acceptance criteria** — how *it* knows it succeeded, before returning.
- **Boundaries** — no shared mutable state with sibling agents.

A vague prompt × 15 agents = 15× the garbage, and you pay in review time.

### When to fan out — and when not to

Fan out when the work is **decomposable and independent**: parallel search across
many files, N variants of an asset, per-item transforms, multi-angle research,
independent verification of N findings.

**Do not fan out** when tasks are serially dependent (agent 2 needs agent 1's
output), when they'd edit the same files (conflicts cost more than the
parallelism saved), or when the task is genuinely one indivisible judgment call.

Serial dependency → pipeline it (each item flows through all stages independently)
rather than barrier-syncing every stage.

### The trap: fan-out relocates the bottleneck into review

Spawn 15 agents, and one reviewer now reads 15 outputs. **That's Law 2 biting.**
Countermeasures, applied by default:

- Subagents return **structured, checkable output** — not essays.
- **Verification is a fan-out too.** Cheap agents check each other in parallel,
  each prompted to *refute*. Never let the producing agent be its own verifier.
- Escalate to the expensive model only what survives verification.

### Standing defaults

- Every non-trivial task: **plan top-tier → execute wide → verify independently.**
- Reach for 5–15 parallel agents by reflex on decomposable work. Sequential
  execution of parallelizable work is a self-inflicted constraint.
- Cost scales with agent count; verification passes are cheap insurance against
  plausible-but-wrong shipped at scale. Buy the insurance.

---

## The loop

```
Law 2  →  what is the constraint?              (measure, don't guess)
Law 1  →  what's the hypothesis for breaking it, and the test that could kill it?
Law 3  →  plan it top-tier, execute it wide, verify it independently
Law 1  →  did the prediction hold? write down the result, including failures
Law 2  →  re-measure — the constraint has moved
```

Repeat. Every pass through this loop should leave behind one written, repeatable
procedure. That accumulation *is* the compounding asset — not any individual win.
