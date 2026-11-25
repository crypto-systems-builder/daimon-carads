"""Download hourly bid/ask candles from FXCM's public candle bucket.

    python3 fetch_fxcm.py [--pairs EURUSD,GBPUSD] [--start 2012] [--end 2026] [--workers 4]

Files land in $FXDATA/fxcm/H1/<PAIR>/<YEAR>/<WEEK>.csv.gz (default
FXDATA=/home/user/fxdata). Re-running skips files already on disk, so an
interrupted download resumes. A 404 is recorded as an empty file (no data that
week / pair not offered). FXCM is a retail broker, so its bid/ask spreads are
retail-realistic - useful for honest cost modelling. Coverage starts 2012.
"""
import argparse, itertools, os, random, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

CCY = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"]  # market-convention order
PAIRS = [a + b for a, b in itertools.combinations(CCY, 2)]       # 28 pairs
URL = "https://candledata.fxcorporate.com/H1/{pair}/{year}/{week}.csv.gz"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) fx-research/1.0"}  # bucket rejects urllib's default UA
DATA = os.environ.get("FXDATA", "/home/user/fxdata")
_lock = threading.Lock()
_stats = {"ok": 0, "missing": 0, "skip": 0, "fail": 0}


def fetch(job):
    pair, year, week = job
    path = os.path.join(DATA, "fxcm", "H1", pair, str(year), f"{week}.csv.gz")
    if os.path.exists(path):
        with _lock:
            _stats["skip"] += 1
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    delay, err = 2.0, "?"
    for _ in range(7):
        try:
            req = urllib.request.Request(URL.format(pair=pair, year=year, week=week), headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read()
            with open(path + ".part", "wb") as f:
                f.write(body)
            os.replace(path + ".part", path)
            with _lock:
                _stats["ok"] += 1
            return
        except urllib.error.HTTPError as e:
            if e.code == 404:  # no file for that week (holiday week / pair not offered)
                open(path, "wb").close()
                with _lock:
                    _stats["missing"] += 1
                return
            err = f"HTTP {e.code}"
        except Exception as e:
            err = type(e).__name__
        time.sleep(delay + random.random())
        delay = min(delay * 2, 60)
    with _lock:
        _stats["fail"] += 1
    print(f"FAIL {pair} {year} w{week}: {err}", file=sys.stderr, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=",".join(PAIRS))
    ap.add_argument("--start", type=int, default=2012)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    jobs = [(p, y, w) for p in a.pairs.split(",") for y in range(a.start, a.end + 1)
            for w in range(1, 54)]
    t0, done = time.time(), 0
    with ThreadPoolExecutor(a.workers) as ex:
        for _ in ex.map(fetch, jobs):
            done += 1
            if done % 1000 == 0:
                print(f"{done}/{len(jobs)} {dict(_stats)} {time.time()-t0:.0f}s", flush=True)
    print(f"DONE {len(jobs)} jobs {dict(_stats)} {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
