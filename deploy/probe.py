#!/usr/bin/env python3
"""Throttle probe - run this ON the VPS before enabling the cron.

Fires N AODP price requests at the builders' pace and reports status codes +
latency. If you see mostly 200 and zero/near-zero 429, this VPS IP is fine for
option A. If you see a wall of 429 at 2s pace, this provider's IP range is
throttled by AODP - pick another provider, or move to option B (NATS stream).

  python3 deploy/probe.py            # europe server, 12 requests @ 2s
"""
import json, time, urllib.request, urllib.parse, urllib.error, statistics as st, sys
from pathlib import Path

SERVER = sys.argv[1] if len(sys.argv) > 1 else "europe"
ROOT = Path(__file__).resolve().parent.parent
ids = list(json.loads((ROOT / "docs/data/baseline.json").read_text(encoding="utf-8"))["items"].keys())[:50]
URL = f"https://{SERVER}.albion-online-data.com/api/v2/stats/prices/" + urllib.parse.quote(",".join(ids)) + "?locations=3003&qualities=1,2"

N, codes, lat = 12, {}, []
print(f"probing {SERVER} AODP: {N} requests of {len(ids)} items @ 2s pace ...")
for i in range(N):
    s = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "CBL-probe"}), timeout=30) as r:
            r.read(); code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = "ERR:" + type(e).__name__
    lat.append(time.time() - s); codes[code] = codes.get(code, 0) + 1
    time.sleep(2)

print("status codes:", codes)
print(f"latency s: median {st.median(lat):.2f}  max {max(lat):.2f}")
print("VERDICT:", "OK - VPS is fine for option A" if codes.get(429, 0) == 0 else
      f"THROTTLED ({codes.get(429,0)}/{N} were 429) - try another provider or option B")
