// Offline test: runs liquidcharts-bridge.js against a mock MyTrader Framework.
//   node tradingbot/test-bridge.mjs [path-to-script]
import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

const file = process.argv[2] || new URL("./liquidcharts-bridge.js", import.meta.url).pathname;
const src = fs.readFileSync(file, "utf8");

function makeDict(objs) {
  const m = new Map(objs.map(o => [o.orderId, o]));
  return {
    get length() { return m.size; },
    values: () => [...m.values()],
    forEach: fn => { for (const [k, v] of m) if (fn(k, v) != null) break; },
    get: k => m.get(k) ?? null, has: k => m.has(k),
  };
}

async function run(orders, want, feed) {
  const sent = [];
  const OT = { BUY: 0, SELL: 1, BUY_LIMIT: 2, CLOSE: 100, CLOSEPOSITION: 101 };
  const ctx = {
    console: { log() {} }, Date, JSON, Array, Error,
    FXB: { OrderTypes: OT, PositionTypes: { LONG: 1, SHORT: 2 } },
    Framework: {
      Orders: makeDict(orders),
      Log() {},
      SendOrder(req, cb) { sent.push(req); cb({ result: { isOkay: true } }); },
    },
    fetch: async () => (feed || { ok: true, json: async () => ({ count: want.length, want }) }),
    setInterval: () => 0,
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  await new Promise(r => setTimeout(r, 20));
  return { sent, ctx, OT };
}

const orders = [
  { orderId: "T1", instrumentId: "EUR/USD", orderType: 0, magicNumber: 778899 }, // ours, still wanted
  { orderId: "T2", instrumentId: "GBP/USD", orderType: 1, magicNumber: 778899 }, // ours, dropped
  { orderId: "T3", instrumentId: "GBP/USD", orderType: 0, magicNumber: 0 },      // manual
  { orderId: "O4", instrumentId: "USD/JPY", orderType: 2, magicNumber: 778899 }, // our pending order
];
const want = [
  { instrumentId: "EUR/USD", side: "buy", sl: 1.05 },
  { instrumentId: "XAU/USD", side: "sell", sl: 2400, tp: 2300 },
  { instrumentId: "US30", side: "buy" },              // no SL -> must skip
];

const { sent, ctx, OT } = await run(orders, want);
const opens = sent.filter(r => r.tradingAction === OT.BUY || r.tradingAction === OT.SELL);
const closes = sent.filter(r => r.tradingAction === OT.CLOSE || r.tradingAction === OT.CLOSEPOSITION);

assert.equal(opens.length, 1, "exactly one open (XAU/USD); EUR/USD already held, US30 has no SL");
assert.equal(opens[0].instrumentId, "XAU/USD");
assert.equal(JSON.stringify(opens[0].volume), JSON.stringify({ equityPercent: 1 }));
assert.equal(JSON.stringify(opens[0].sl), JSON.stringify({ price: 2400 }));
assert.equal(JSON.stringify(opens[0].tp), JSON.stringify({ price: 2300 }));
assert.equal(opens[0].magicNumber, 778899);
assert.equal(closes.length, 1, "exactly one close");
assert.equal(closes[0].tradingAction, OT.CLOSE, "close by id, never CLOSEPOSITION");
assert.equal(closes[0].orderId, "T2", "closes only our dropped trade, not manual T3");

// Second poll before the fill shows up must not re-send the open.
await new Promise(r => { ctx.poll(); setTimeout(r, 20); });
assert.equal(sent.filter(r => r.instrumentId === "XAU/USD").length, 1, "no duplicate open while pending");

// A broken feed (error JSON or HTTP 500) must hold, not close everything.
for (const feed of [
  { ok: true, json: async () => ({ error: "bad secret" }) },
  { ok: false, status: 500, json: async () => ({ want: [] }) },
]) {
  const b = await run(orders, [], feed);
  assert.equal(b.sent.length, 0, "broken feed sends no orders");
}

console.log("PASS: opens=%d closes=%d, no dup open, broken feed holds", opens.length, closes.length);
