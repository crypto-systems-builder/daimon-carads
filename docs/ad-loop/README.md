# Ad loop — the actual goal

Status: **wrong target, parked on 2026-11-16.** The owner's goal is the a different business of theirs, not ads for Daimon Media's car ad service. Campaign 001 below must not be launched. The site tracking in `track.js` is harmless and can stay or go.

## Goal

AI agents create video ads, launch them as campaigns, read the performance and the
profit, and use that to decide what to make next. A person approves spend.

```
CREATE video  ->  LAUNCH campaign  ->  MEASURE spend, results, profit  ->  LEARN: stop losers, brief the next batch
     ^                                                                                    |
     +------------------------------------------------------------------------------------+
```

## Verdict on the swarm rig and Parallax (2026-11-16)

- The swarm rig copies software. That is not what limits this goal. **Parked.**
- Parallax covers one of the four stages (create). It is a candidate backend for that
  stage, to be judged on cost per clip against the alternatives. Not the system.
- Stages two to four (launch, measure, learn) are where the value is, and none of them
  exist yet.

## Measured starting point (2026-11-16)

| Stage | What exists | Gap |
|---|---|---|
| Create | This repo already renders car ad clips (`samples/`, `press/`). Higgsfield account: free plan, 0 credits | Paid generation is not funded. Cost per usable clip is unknown |
| Launch | Ad connector attached. **0 ad accounts connected.** No brand saved | No account, no campaign, no pixel |
| Measure | Creative analytics connector attached, 0 workspaces. Shopify store exists on a trial plan | No spend, no results, no revenue data |
| Learn | Nothing | Needs data from the stage above first |

Constraint (Law 2): **there is no live ad, so there is no feedback.** Better video
tooling adds zero output until an ad is running and its results can be read.

## Plan

1. **Decide the offer.** What is advertised, to whom, at what price, and what one
   customer is worth. Without this, profit cannot be computed.
2. **Connect one ad platform** and its tracking. One platform only.
3. **Run the loop once by hand, small.** 3 to 5 clips from the existing pipeline, one
   campaign, a fixed budget and end date. Write the prediction first (cost per lead or
   sale) in the lab notebook.
4. **Read the result.** Spend, results, cost per result, revenue, profit, per clip.
5. **Only then automate** the step that took the most time, usually the weekly read
   and the next brief. A scheduled agent does it, a person approves budget changes.
6. **Then choose the create backend** by cost per usable clip: existing pipeline,
   Higgsfield plan, or Parallax with a pay-per-use key.

Evidence that would change this plan: the first campaign shows the clips themselves
are the reason ads fail (people do not stop to watch). Then the create stage becomes
the constraint and Parallax or a better generator moves up.

## Built so far

| What | Where | State |
|---|---|---|
| Source tracking on both landing pages | `track.js` | Tested in a headless browser, 10 of 10 checks. Live once merged to `main` |
| Language redirect keeps campaign tags | `index.html` | Tested |
| Pixel loader with a consent banner | `track.js` | Off until a pixel id is filled in |
| First campaign brief | `campaign-001.md` | Ready, not launched |
| Lead and sales ledger | `ledger.csv` | Empty |
| Brand saved in the ad tool, competitors checked | `campaign-001.md` | Done |

## Needed from the owner

1. Connect a Meta ad account to the ad tool (a sign-in link, free).
2. Approve the budget in `campaign-001.md` (proposal: €70).
3. Merge the pull request so the tracking is on the live page.
4. Say what one clip costs to make, in money and minutes. Profit needs it.
5. Decide where the ads should land: the current `github.io` address, or a
   `daimonmedia.com` address.

## Related

- `docs/swarm-rig/` — the video breakdown and the parked rig plan.
