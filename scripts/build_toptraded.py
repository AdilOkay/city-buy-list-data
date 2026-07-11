#!/usr/bin/env python3
"""
build_toptraded.py - City Buy List per-city Top Traded dataset

baseline.json only carries Black Market volume, so the Top Traded tab could rank
by the Black Market alone. This emits docs/data/toptraded.json: per-city daily
volume + average price for every T4-T8 gear item, so the tab can also rank the
most-traded gear in each royal city / Caerleon / Brecilien (like AFM's Locations
filter), on a 7d or 30d window.

Source: AODP history endpoint (same public data + server as baseline). Rebuild
alongside baseline (2x/day). Aggregated across qualities per (item, city); an
entry is written only when the item actually traded in that city (never a guess).

Output shape:
  { "cities": [...], "items": {
      "T4_2H_AXE": { "Bridgewatch": {"v7":12.3,"a7":11800,"v30":9.1,"a30":12050}, ... },
      ...
  }}
  v = mean items sold per day over the window; a = volume-weighted avg price.
  The app ranks by daily silver = v * a and joins names/tier/category from baseline.

Usage:
  python scripts/build_toptraded.py
  python scripts/build_toptraded.py --server west
"""
import argparse, json, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "docs" / "data" / "baseline.json"
OUT = ROOT / "docs" / "data" / "toptraded.json"
CITIES = ["Bridgewatch", "Fort Sterling", "Lymhurst", "Martlock", "Thetford", "Caerleon", "Brecilien"]
QUALITIES = "1,2,3,4,5"
CHUNK = 50
SLEEP = 2.0
UA = "city-buy-list-pro/1.0 (top-traded dataset builder)"


def gear_ids():
    return sorted(json.loads(BASELINE.read_text(encoding="utf-8"))["items"].keys())


def get_json(url, tries=10):
    # Exponential backoff SCOPED to this one call (resets for the next chunk) - distinct
    # from an earlier bug where the delay escalated and PERSISTED across chunks, permanently
    # slowing the whole run after one early 429. Honors Retry-After when AODP sends it, else
    # backs off 3s/6s/12s/... capped at 20s.
    delay = 3
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait = int(e.headers.get("Retry-After") or 0) or delay
                time.sleep(wait)
                delay = min(delay * 2, 20)
            else:
                raise
        except Exception:
            if attempt < tries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 20)
            else:
                raise


def history_url(server, ids):
    q = urllib.parse.urlencode({"locations": ",".join(CITIES), "qualities": QUALITIES, "time-scale": "24"})
    return f"https://{server}.albion-online-data.com/api/v2/stats/history/" + urllib.parse.quote(",".join(ids)) + "?" + q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="europe", choices=["europe", "west", "east"])
    args = ap.parse_args()

    ids = gear_ids()
    print(f"{len(ids)} gear ids from baseline.json -> AODP {args.server} history (7 cities x q1-5)", flush=True)

    # (item, city) -> aggregation accumulators across qualities, for the 7d and 30d windows
    acc = {}   # id -> city -> {"c7":cnt, "pv7":sum, "c30":cnt, "pv30":sum}
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i:i + CHUNK]
        try:
            data = get_json(history_url(args.server, chunk))
        except Exception as e:
            print(f"    chunk {i} failed ({e}); skipping")
            data = []
        for row in (data or []):
            series = sorted(row.get("data") or [], key=lambda p: p.get("timestamp") or "")
            if not series:
                continue
            mid, city = row["item_id"], row["location"]
            a = acc.setdefault(mid, {}).setdefault(city, {"c7": 0, "pv7": 0, "c30": 0, "pv30": 0})
            for p in series[-30:]:
                cnt = p.get("item_count", 0)
                a["c30"] += cnt
                a["pv30"] += p.get("avg_price", 0) * cnt
            for p in series[-7:]:
                cnt = p.get("item_count", 0)
                a["c7"] += cnt
                a["pv7"] += p.get("avg_price", 0) * cnt
        print(f"  {min(i+CHUNK, len(ids))}/{len(ids)}  items-with-city-data={len(acc)}", flush=True)
        time.sleep(SLEEP)

    items, kept, entries = {}, 0, 0
    for mid, bycity in acc.items():
        out_city = {}
        for city, a in bycity.items():
            if not (a["c7"] or a["c30"]):
                continue
            rec = {}
            if a["c7"]:
                rec["v7"] = round(a["c7"] / 7, 2)
                rec["a7"] = round(a["pv7"] / a["c7"])
            if a["c30"]:
                rec["v30"] = round(a["c30"] / 30, 2)
                rec["a30"] = round(a["pv30"] / a["c30"])
            out_city[city] = rec
            entries += 1
        if out_city:
            items[mid] = out_city
            kept += 1

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "server": args.server,
        "cities": CITIES,
        "notes": {
            "value": "items[id][city] = {v7,a7,v30,a30}: v = mean items/day over the window, a = volume-weighted avg price. Aggregated across qualities. Missing = did not trade there.",
            "scope": "T4-T8 gear (same set as baseline.json). Black Market volume stays in baseline.json.",
            "rank": "app ranks by daily silver = v * a; joins name/tier/category from baseline.json",
        },
        "items": items,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"items with city volume {kept}/{len(ids)} | (item,city) entries {entries}")


if __name__ == "__main__":
    sys.exit(main())
