# City Buy List - public price data

Public, always-fresh market data for the City Buy List tool. Everything here is
derived from public sources (the community AODP API + ao-bin-dumps) - no private
or premium logic. The premium app lives in a separate private repo; this repo
only exists so the launcher can pull fresh averages at each start without anyone
touching a keyboard.

## What's served

`docs/data/*.json`, fetched by the launcher over raw GitHub:

| file | refreshed | what |
|---|---|---|
| `baseline.json` | 2x/day (Action) | Black Market prices + 7/30d averages + volume, T4-T8 gear |
| `materials.json` | 2x/day (Action) | per-city material prices (direct + 7/30d avg) |
| `toptraded.json` | 2x/day (Action) | per-city daily volume + avg price, gear + resources + consumables + mounts |
| `routes.json` | 2x/day (Action) | per-city standing orders (sell min + buy max + timestamps) for the Routes tab |
| `recipes.json` | on game patch | crafting materials per gear key |
| `craftmeta.json` | on game patch | item value (station fee) + bonus city per gear key |
| `items.json` | on game patch | localized item names |
| `routesmeta.json` | on game patch | Routes universe + item weights + metadata for non-gear ids |

## Automation

`.github/workflows/refresh-data.yml` runs the four price builders at 03:00 and
15:00 UTC and commits the refreshed JSON. Trigger it on demand from the Actions
tab (`workflow_dispatch`). The patch-only files are rebuilt by hand after a game
update (`python scripts/build_recipes.py` then `build_craftmeta.py` /
`build_baseline.py` / `build_routesmeta.py`); see `scripts/README.md`.

## Raw URLs (what the launcher uses)

```
https://raw.githubusercontent.com/<owner>/<repo>/main/docs/data/baseline.json
https://raw.githubusercontent.com/<owner>/<repo>/main/docs/data/materials.json
https://raw.githubusercontent.com/<owner>/<repo>/main/docs/data/toptraded.json
https://raw.githubusercontent.com/<owner>/<repo>/main/docs/data/routes.json
https://raw.githubusercontent.com/<owner>/<repo>/main/docs/data/routesmeta.json
```

If you fork or rename this repo, update `DATA_BASE` in the launcher's `serve.py`.
