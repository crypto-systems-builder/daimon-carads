// ===========================================================================
// Daimon Trading Engine  ->  LiquidCharts / FX Blue MyTrader bridge
// ---------------------------------------------------------------------------
// Paste this into the LiquidCharts "Run script" console (Scripts -> Run script
// -> paste -> START). It polls our engine's desired-position feed every 60s
// and mirrors it onto THIS demo account: opens the trades the engine wants,
// closes the ones it no longer wants. Only touches trades it opened itself
// (tagged with magicNumber 778899) — your manual trades are never affected.
//
// Checked against the MyTrader framework reference
// (https://www.fxblue.com/mytrader/scripting/help):
//   - Framework.Orders is an FXB Dictionary (.values(), .forEach(key, obj)),
//     NOT an array — there is no .toArray()
//   - close ONE trade with {tradingAction: CLOSE, orderId}; CLOSEPOSITION
//     closes every trade AND pending order on the market (manual ones too)
//   - volume {equityPercent} is risk-sized and needs a real stop-loss;
//     sl {equityPercent} only works with a FIXED volume, so the two can't pair
//   - Framework.Log() is a toast popup — used only for trade events
//   - fetch() is allowed to https + CORS (our feed sends Access-Control-Allow-Origin)
//
// SET YOUR SECRET BELOW (the TRADINGBOT_WEBHOOK_SECRET value).
// Never commit the real value — this file lives in a git repo.
// ===========================================================================

var FEED_URL = "https://daimonmedia.com/tradingbot/webhook/signals?secret=PASTE_TRADINGBOT_WEBHOOK_SECRET_HERE";
var MAGIC = 778899;            // tag so we only manage our own trades
var POLL_MS = 60000;           // poll cadence
var RISK_PERCENT = 1.0;        // % of equity risked per trade (sized off SL)
var PENDING_TTL_MS = 5 * 60000; // don't resend an open/close for this long while awaiting fill

// Requests sent but not yet visible in Framework.Orders. Stops a slow fill
// (or an overlapping poll) from opening the same trade twice.
var _pending = {};

function info(msg) { console.log("[daimon] " + msg); }
function alertUser(msg) {
  info(msg);
  try { if (Framework.Log) Framework.Log(msg); } catch (e) { /* toast is best-effort */ }
}

function isPending(key) {
  var t = _pending[key];
  if (!t) return false;
  if (Date.now() - t > PENDING_TTL_MS) { delete _pending[key]; return false; }
  return true;
}

// Our open trades (not pending orders), tagged with MAGIC.
function ourTrades() {
  var out = [];
  var all = Framework.Orders ? Framework.Orders.values() : [];
  for (var i = 0; i < all.length; i++) {
    var o = all[i];
    if (!o || o.magicNumber != MAGIC) continue;
    if (o.orderType !== FXB.OrderTypes.BUY && o.orderType !== FXB.OrderTypes.SELL) continue;
    out.push(o);
  }
  return out;
}

function sideOf(o) { return o.orderType === FXB.OrderTypes.BUY ? "buy" : "sell"; }

function openTrade(sig) {
  var key = "open:" + sig.instrumentId + ":" + sig.side;
  if (isPending(key)) return;

  // Risk-sized volume needs a concrete stop. No SL from the engine -> skip
  // rather than open a naked or mis-sized position.
  if (!(sig.sl > 0)) {
    info("SKIP " + sig.side + " " + sig.instrumentId + ": feed gave no sl, can't size risk");
    return;
  }

  var req = {
    tradingAction: (sig.side === "buy") ? FXB.OrderTypes.BUY : FXB.OrderTypes.SELL,
    instrumentId: sig.instrumentId,
    volume: { equityPercent: RISK_PERCENT },   // framework sizes vs the SL
    sl: { price: sig.sl },
    tp: (sig.tp > 0) ? { price: sig.tp } : { rrr: 2 },  // 2:1 reward:risk default
    magicNumber: MAGIC,
    comment: ("daimon:" + (sig.comment || "")).slice(0, 40)
  };

  _pending[key] = Date.now();
  Framework.SendOrder(req, function (MsgResult) {
    var r = MsgResult && MsgResult.result;
    if (r && r.isOkay) {
      alertUser("OPEN " + sig.side + " " + sig.instrumentId + " ok");
    } else {
      delete _pending[key];   // allow retry next poll
      alertUser("OPEN FAILED " + sig.side + " " + sig.instrumentId + ": " + (r ? r.code : "?"));
    }
  });
}

// Close exactly one of our trades by id — never the whole market.
function closeTrade(o) {
  var key = "close:" + o.orderId;
  if (isPending(key)) return;
  _pending[key] = Date.now();
  Framework.SendOrder({
    tradingAction: FXB.OrderTypes.CLOSE,
    orderId: o.orderId
  }, function (MsgResult) {
    var r = MsgResult && MsgResult.result;
    if (r && r.isOkay) {
      alertUser("CLOSE " + sideOf(o) + " " + o.instrumentId + " (" + o.orderId + ") ok");
    } else {
      delete _pending[key];
      alertUser("CLOSE FAILED " + o.instrumentId + " (" + o.orderId + "): " + (r ? r.code : "?"));
    }
  });
}

function reconcile(want) {
  var trades = ourTrades();
  var haveKey = {};
  for (var i = 0; i < trades.length; i++) {
    var k = trades[i].instrumentId + ":" + sideOf(trades[i]);
    haveKey[k] = true;
    delete _pending["open:" + k];   // fill is now visible
  }

  var wantKey = {};
  for (var j = 0; j < want.length; j++) {
    var s = want[j];
    if (!s || !s.instrumentId || (s.side !== "buy" && s.side !== "sell")) {
      info("ignoring malformed signal: " + JSON.stringify(s));
      continue;
    }
    var key = s.instrumentId + ":" + s.side;
    wantKey[key] = true;
    if (!haveKey[key]) {
      info("engine wants " + s.side + " " + s.instrumentId + " — opening");
      openTrade(s);
    }
  }

  for (var m = 0; m < trades.length; m++) {
    var o = trades[m];
    if (!wantKey[o.instrumentId + ":" + sideOf(o)]) {
      info("engine dropped " + sideOf(o) + " " + o.instrumentId + " — closing " + o.orderId);
      closeTrade(o);
    }
  }
}

var _busy = false;
function poll() {
  if (_busy) return;              // previous poll still in flight
  _busy = true;
  fetch(FEED_URL, { cache: "no-store" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (d) {
      // A missing/garbled feed must NOT be read as "want nothing" (which
      // would close everything). Only an explicit array reconciles.
      if (!d || !Array.isArray(d.want)) { info("feed: no usable data, holding"); return; }
      info("feed: " + d.want.length + " desired position(s)");
      reconcile(d.want);
    })
    .catch(function (e) { info("feed error, holding: " + e); })
    .then(function () { _busy = false; });
}

alertUser("Daimon bridge starting — polling every " + (POLL_MS / 1000) + "s");
poll();
var _timer = setInterval(poll, POLL_MS);
// NB: do NOT call Framework.EndScript() — this script must run continuously.
