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

### 2026-11-24 — Forex bot: does any rule-based FX strategy beat retail costs out-of-sample?

**Status: PRE-REGISTERED (written before any strategy was run). Results are appended below; nothing above the RESULT line is edited after the fact.**

```
CONSTRAINT   Execution plumbing exists (tradingbot/liquidcharts-bridge.js). The binding
             constraint for "a profitable bot" is evidence of an edge that survives retail
             costs out-of-sample. First sub-constraint was data: Dukascopy reset our
             connections after 4 files (throttle) -> switched to FXCM's public candles:
             hourly bid+ask, 2012-01..2026-11, 28 pairs, retail-realistic spreads.
             Known gap: no 2008 crisis in the sample.
QUESTION     Does any pre-registered strategy family reach OOS (2020-01..2026-11) net
             Sharpe >= 0.4 after FXCM bid/ask + 0.2 pip slippage/side + policy-rate swaps
             with 1%/yr broker markup?
```

**Setup (fixed before results).** Engine `tradingbot/research/fxlab.py`: signal at bar close, fill at a later bar's open at actual bid/ask; every trade has a stop; size = 1% equity risked to the stop (mirrors the live bridge: `volume: {equityPercent}` + `sl`). Basket = all 28 pairs, equal weight. In-sample (IS) = 2012-2019. OOS = 2020-01-01 onward, **encrypted** until candidates are frozen and committed.

**Hypotheses, predictions and grids (trial counts fixed now):**

| Family | Hypothesis (mechanism) | Grid (configs) | Prediction |
|---|---|---|---|
| A Trend: TSMOM L∈{20,60,120,250}; EMA cross (10/40, 20/50, 20/80, 50/200); stop k∈{2,3,4,6}×ATR20 | Trends persist for weeks-months because policy cycles and hedging flows move slowly | 32 | IS best 0.5-0.9 (selection-inflated), median config 0.1-0.3; OOS 0.2-0.6 (2022 USD/JPY trend helps) |
| B Breakout: Donchian entry N∈{20,55,100}, exit M (20:{10}; 55:{10,20}; 100:{20,50}; or reverse-only), k∈{2,3,4} | Same mechanism as A | 24 | Correlated with A (daily corr > 0.6), similar Sharpe |
| C Mean reversion: RSI2 x∈{5,10,20} & z-score(20) z0∈{1.5,2,2.5}; max hold, 200d trend filter on/off, k | 1-3 day overreactions get absorbed | 48 | IS median <= 0, best ~0.4, breadth < 60% -> no candidate |
| D Session (H1): Asian-range breakout at London open; London first-hour momentum/fade | Order-flow imbalance at the London open | 20 | Net negative for most configs after costs -> no candidate |
| E Carry: hold sign(r_base - r_quote) if abs > tau∈{0.25,1,2}%; trend filter {none, mom60, mom120}; k∈{3,5} | High-yielders earn a crash-risk premium | 18 | Pure carry IS 0.0-0.4 (2013-15 commodity-FX slump hurts); with trend filter 0.3-0.6 |
| F Calendar (negative control): USD weekday effect; USD month-end/start | None credible — this is data mining on purpose | 14 | Whatever wins IS fails OOS (< 0.2). If F passes OOS, distrust the whole pipeline |

**Engine canaries (must pass before any strategy result counts):** C1 oracle (tomorrow's direction) Sharpe > 3 on every pair; C2 random + costs: mean pair Sharpe in (-1.2, 0), none > 1.2; C3 random frictionless: abs(mean) < 0.2, and costs strictly worse; C4 one-day-stale oracle: abs(Sharpe) < 1.5; C5 buy-and-hold EURUSD sign = price-move sign; C6 one-bar round trip pays exactly half-spread in + half-spread out + 2×0.2 pip; C7 a 1-pip stop gets hit > 80% of the time at about -1.2R.

**Selection rule IS → OOS (per family, max 1 candidate):** highest IS portfolio Sharpe among configs with (1) Sharpe >= 0.4, (2) >= 60% of pairs net positive, (3) median Sharpe of one-step grid neighbours >= 0.5× own, (4) stress (2× spread, 0.5 pip slip, 2% swap markup) Sharpe >= 0.2, (5) >= 100 trades. Deflated Sharpe reported as a diagnostic. No qualifying config → family has no candidate (a valid result).

**OOS verdict (decided now):** PASS = OOS Sharpe >= 0.4 AND stress Sharpe >= 0.2 AND >= 4 of 7 positive years AND max drawdown <= 2.5× IS max drawdown. STRONG = PASS + OOS t-stat >= 2.0. KILL = OOS Sharpe < 0.2. If >= 2 pass, also test the equal-risk ensemble (prediction: ensemble Sharpe > best single). Only PASS candidates go to the demo bot. If none passes, no bot is presented as profitable.

**Demo forward test (one-way-door guard before any real money):** review at 50 trades or 3 months. Kill if cumulative R is below the 5th percentile of the backtest's distribution for the same number of trades, or if average cost per trade is > 1.5× the model's.


**Engine & data validation log (appended 2026-11-25, before any strategy sweep):**

- *Data.* FXCM publishes 25 of the 28 pairs (CHFJPY, EURCAD, GBPAUD: 404 at source). ~49.5k in-sample H1 bars per pair. Found bid > ask on ~97% of CADCHF/NZDCHF bars in 2012-2014 and on ~5% of bars elsewhere (0.2-pip crossings at bar close). First cleaning pass **dropped** them, which punched 38% holes into CADCHF/NZDCHF - caught by the row counts. Fix: keep the (sound) mid, rebuild bid/ask with the pair's 90th-percentile spread (conservative). Execution delay for daily strategies, by the pre-set rule: median open spread at NY 17:00 = 5.9x normal, 18:00 = 2.9x, **19:00 = 1.33x -> delay = 2 bars**.
- *Canaries, first run: 3 FAILED* (C1, C2, C3b) -> every daily strategy traded zero times. Cause: `daily_to_h1` built its index from `.values`, which strips the UTC timezone, so 0% of daily signals matched the H1 grid - a silent failure (no error, just no trades). Fixed; regression canary C0 added (mapping share 99.96%).
- *Canaries, second run: 2 FAILED, both were wrong predictions, not engine bugs* (each diagnosis tested before accepting it):
  - C1 (oracle Sharpe > 3 on every pair) failed on EURCHF only (1.85). Hypothesis "SNB-peg days were tiny" was **wrong** (peg-era daily range 47 pips = 2017's). Real cause: one day, the 2015-01-15 SNB de-peg, returned +55% and dominates the standard deviation; without it Sharpe = 10.5. Canary now measured without each pair's best day.
  - C4 (stale oracle abs(Sharpe) < 1.5 with costs) failed at -3.16. Cause: cost drag from flipping daily at the rollover (3.5%/yr), amplified across 25 pairs; frictionless it is -0.26 -> no leaked information. Canary now isolates lookahead (frictionless).
- *Known engine limitation found:* intrabar stops fill at the stop price. In a flash gap (SNB 2015: stops filled 1,000+ pips away) real losses are far larger. Backtests therefore understate tail risk; the final candidate gets an explicit gap-risk check.
- All 9 canaries pass. OOS (2020+) data encrypted; the latest bar visible to research is 2019-12-31 19:00 UTC.

```
RESULT       0 of 156 pre-registered configs passed the in-sample screen; none even
             reached IS Sharpe 0.4. Candidate list frozen EMPTY -> OOS data stays sealed
             (nothing to test; unsealing would only invite post-hoc fishing).
               trend      32 cfg  best -0.13  median -0.40  0% positive   (predicted best 0.5-0.9: WRONG)
               breakout   24 cfg  best -0.12  median -0.38  0% positive   (predicted ~trend: WRONG)
               meanrev    48 cfg  best +0.17  median -0.41  8% positive   (predicted no candidate: HELD)
               session    20 cfg  best -0.50  median -1.35  0% positive   (predicted no candidate: HELD)
               carry      18 cfg  best -0.09  median -0.34  0% positive   (predicted 0.0-0.6: WRONG)
               calendar   14 cfg  best +0.36  median -0.22  29% positive  (negative control: noise, HELD)
             Gross P&L was negative too for trend (costs ~0.07%/yr vs -0.5%/yr) -> not a
             cost artefact: 2012-2019 FX did not reward these rules. Session strategies were
             killed by costs (5-9%/yr). Calendar "winner" = the 2012-19 USD uptrend in disguise.
             Independent engine audit (14 hand-computed tests, refute-prompted): survived on
             lookahead/fills/stops/gaps/swaps/sizing/DST; 2 minor bugs refuted and fixed
             (reversal on a time-exit bar filled 1 bar late; max_dd ignored starting equity).
             Meanrev re-run after the fix: unchanged. Tests kept in tradingbot/research/audit/.
             Caveats: no re-entry after a stop (hurts slow-signal carry/trend); 2012-2019 only,
             no 2008; one cost model; intrabar stops fill at the stop (understates gap risk).
CONCLUSION   KILLED for deployment: no simple rule-based FX strategy here has evidence of an
             edge after retail costs. No bot is presented as profitable. My prior that daily
             trend/carry would show a modest edge was wrong for this period.
PROCEDURE    Do: pre-register grids + selection rule, validate the engine with canaries that
             could kill it, seal OOS, fan out sweeps, audit the engine adversarially - under
             condition: any trading-strategy claim - to get: a result you can trust either
             way, including "no edge" - because canaries + audit caught a silent tz bug that
             made every daily strategy trade zero times, and a 38% data hole, before they
             could produce fake conclusions.
NEXT         Constraint moved from "evidence" to "hypothesis quality": the cheap, well-known
             rule families are exhausted on this data. Next questions, cheapest first:
             (1) does a volatility-targeted, always-in, multi-asset trend portfolio (incl. gold,
             indices) differ? (2) is the Daimon engine's own signal set testable through this
             harness? Either must be pre-registered here first.
```

