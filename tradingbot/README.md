# Daimon → LiquidCharts bridge

`liquidcharts-bridge.js` is pasted into LiquidCharts (FX Blue MyTrader) → Scripts → Run script.
It polls `https://daimonmedia.com/tradingbot/webhook/signals` every 60s and mirrors the
engine's desired positions onto the demo account. It only manages trades tagged `magicNumber 778899`.

## Use
1. Copy `liquidcharts-bridge.js`, replace `PASTE_TRADINGBOT_WEBHOOK_SECRET_HERE` with the real secret
   **in the console only**. Never commit the secret.
2. START. Routine logs go to the browser console; opens/closes show as toasts.

## Feed contract
`{"want": [{"instrumentId": "EUR/USD", "side": "buy"|"sell", "sl": <price>, "tp": <price, optional>, "comment": "..."}]}`
- `sl` is **required**: volume is risk-sized (`RISK_PERCENT` of equity to the SL). Signals without `sl` are skipped.
- No `tp` → 2:1 reward:risk.
- `instrumentId` must match the broker's MyTrader instrument id exactly.
- Non-200, error JSON, or a missing `want` array → bridge holds (does not close anything).
  An explicit `"want": []` closes all bridge trades.

## Fixes vs the first draft (verified against the framework reference + `test-bridge.mjs`)
| Bug | Effect | Fix |
|---|---|---|
| `Framework.Orders.toArray()` doesn't exist (Orders is an FXB Dictionary) | Every poll threw → **zero trades ever placed** | `Framework.Orders.values()` |
| `CLOSEPOSITION` to exit | Closed *all* trades + pending orders on the market, incl. manual ones | `CLOSE` + `orderId`, per trade |
| `sl:{equityPercent}` with `volume:{equityPercent}` | Invalid combo (sl-equityPercent needs fixed volume) → order rejected | Require `sl` price from feed; skip otherwise |
| No in-flight guard | Slow fill → duplicate opens | 5-min pending map per open/close |
| `Framework.Log` every poll | It's a toast → popup spam | `console.log` for routine, toast for trades |
| Logged `FEED_URL` | Leaked secret into logs | Not logged |

## Test
`node tradingbot/test-bridge.mjs` — runs the script against a mock Framework (no network, no broker).

## Status (2026-09-27)
| Check | State |
|---|---|
| Script logic vs MyTrader API reference | ✅ verified (offline mock test passes) |
| Live feed `/tradingbot/webhook/signals` returns `want[]` with `sl` + CORS header | ⏳ unverified — engine source not found in accessible repos; check on first run |
| First live run on LiquidCharts demo | ⏳ pending — see checklist below |

### First-run checklist (LiquidCharts demo)
1. Open browser devtools console (F12) before START.
2. Expect `[daimon] feed: N desired position(s)` within a few seconds.
   - `feed error, holding: TypeError: Failed to fetch` → feed is missing the CORS header (`Access-Control-Allow-Origin: *`).
   - `feed error, holding: Error: HTTP 401/403` → wrong secret.
   - `feed: no usable data, holding` → feed JSON has no `want` array.
   - `SKIP ... feed gave no sl` → engine must add `sl` to each signal.
3. Opens/closes appear as toasts; trades carry magic `778899` and comment `daimon:...`.
4. `OPEN FAILED ... <code>` → look the code up in the framework reference's error table
   (e.g. market closed, volume too small, instrumentId mismatch).
