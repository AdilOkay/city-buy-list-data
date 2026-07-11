# City Buy List - data pipeline

Static JSON files under `docs/data/` feed the app. Regenerate them here so the
pipeline is never lost again (baseline's original generator was, once - now
rebuilt and self-contained, see build_baseline.py below).

**Automated**: `.github/workflows/refresh-data.yml` runs `build_baseline.py`,
`build_materials.py` and `build_toptraded.py` on a schedule (03:00 and 15:00 UTC)
and auto-commits the refreshed JSON to `main` if anything changed. This is what
lets the app show a useful royal-city-vs-Black-Market-average comparison the
moment it opens, with zero live scan needed first. Trigger it on demand from the
repo's Actions tab (`workflow_dispatch`) instead of waiting for the next tick.
`recipes.json` / `craftmeta.json` / `items.json` are NOT part of the schedule -
they mirror the game's own item data and only need a rebuild on a game patch.

| file | what | source | cadence |
|---|---|---|---|
| `baseline.json` | Black Market prices + a7/a30 averages + vol7 for T4-T8 gear | AODP history/prices + ao-bin-dumps metadata | 2x/day, automated |
| `recipes.json` | crafting materials + counts for every gear key in baseline | ao-bin-dumps (game client data) | on game patch only |
| `materials.json` | buy-side price of every material a recipe needs, per city (direct + 7d/30d avg) | AODP prices + history | 2x/day, automated |
| `toptraded.json` | per-city daily volume + avg price for every gear item (7d/30d) | AODP history | 2x/day, automated |
| `craftmeta.json` | item value (exact station fee) + bonus city per gear key | ao-bin-dumps + scripts/data/bonus_cities.json | on game patch only |

## Build the craft dataset

```
python scripts/build_recipes.py          # downloads ao-bin-dumps, writes recipes.json
python scripts/build_recipes.py --dump items.json   # or reuse a local dump (17 MB)
python scripts/build_baseline.py          # Black Market baseline (reads recipes.json) -> baseline.json
python scripts/build_materials.py         # prices every material via AODP -> materials.json
python scripts/build_toptraded.py         # per-city volume via AODP -> toptraded.json
```

`build_baseline.py` and `build_materials.py` both read `recipes.json`, so run
`build_recipes.py` first after a patch (new keys) before the others.
AODP rate-limits (HTTP 429); every builder backs off automatically (short fixed
wait, never escalating - see each script's `get_json`).

## baseline.json

```json
{ "items": {
  "T4_2H_ARCANESTAFF": {"cat":"weapons","sub":"arcanestaff","tier":4,"artefact":false,
    "name":"Adept's Great Arcane Staff","ench":0,
    "q":{"2":{"a7":14927,"vol7":15,"a30":15557,"bm_buy":632,"bm_buy_ts":"2026-07-08T21:55:00"}, ...}},
  "T4_2H_ARCANESTAFF_CRYSTAL": {"cat":"weapons","sub":"arcanestaff","tier":4,"artefact":true,
    "name":"Adept's Astral Staff","ench":0}
}}
```

- Key set = `recipes.json`'s keys exactly (the frozen gear universe); `cat`/`sub`/`tier` come from
  ao-bin-dumps `@shopcategory`/`@shopsubcategory1`/`@tier`, `artefact` = true when the item's own
  recipe consumes an `ARTEFACT_` material, `name` from `items.json` (English).
- `q` per quality: `a7`/`a30` = volume-weighted average Black Market price (AODP history, 7/30 day
  window), `vol7` = mean items sold per day at the Black Market, `bm_buy`/`bm_buy_ts` = the live
  Black Market buy order and its timestamp (AODP prices, snapshot at build time).
- No `q` key at all = no reliable Black Market data for that item; the app must show "no baseline",
  never a guess (unchanged convention from the original external generator).

## recipes.json

```json
{ "items": {
  "T4_2H_ARCANESTAFF":     [["T4_PLANKS",20],["T4_METALBAR",12]],
  "T4_2H_ARCANESTAFF@1":   [["T4_PLANKS_LEVEL1@1",20],["T4_METALBAR_LEVEL1@1",12]],
  "T4_2H_ARCANESTAFF_CRYSTAL@2": [["T4_PLANKS_LEVEL2@2",20],["T4_METALBAR_LEVEL2@2",12],["T4_ARTEFACT_2H_ARCANESTAFF_CRYSTAL",1]],
  "T4_CAPE_ARENA_BANNER":  null
}}
```

- Keys mirror `baseline.json` exactly; `@N` = enchantment level.
- Material ids are the **market/AODP ids**: enchanted resources trade as `T4_METALBAR_LEVEL1@1`
  (the `_LEVELn` uniquename plus the `@n` suffix), base resources and artefacts stay bare.
- `null` = no craft recipe (vanity / arena banners). Never a fabricated count.
- Recipes can be **nested**: Royal/faction gear consumes a crafted `_SET1@N` item + faction
  tokens (e.g. `T4_ARMOR_PLATE_ROYAL@1` -> `T4_ARMOR_PLATE_SET1@1` + `QUESTITEM_TOKEN_ROYAL_T4`).
- Coverage: 6130 / 6138 keys resolved, 8 vanity null, 0 base missing.

## materials.json

```json
{ "prices": {
  "T4_METALBAR":         {"min":295,"by":{"Thetford":295,"Bridgewatch":397, ...},
                          "by7":{"Thetford":301, ...},"by30":{"Thetford":310, ...}},
  "T4_METALBAR_LEVEL1@1":{"min":470,"by":{ ... }},
  "QUESTITEM_TOKEN_ROYAL_T4": null
}}
```

- `by`  = direct: cheapest live `sell_price_min` per city = what you pay to BUY the material now.
- `min` = cheapest city direct price (shortcut for the "cheapest" craft-city option).
- `by7` / `by30` = volume-weighted average price per city over 7 / 30 days (AODP history).
  Thinner coverage than direct; the app falls back to direct where a city has no average.
- `null` = no order and no history anywhere: faction/bound tokens, faction-cape blueprints, or an
  artefact with a thin market at build time. App must show "cost n/a", never a guess.
- The craft calculator's `mat price` control picks direct / 7d / 30d; `craft city` picks the city
  (or cheapest). Averages are steadier, direct is freshest.

## toptraded.json

```json
{ "cities": ["Bridgewatch", ...], "items": {
  "T4_2H_AXE": { "Bridgewatch": {"v7":12.3,"a7":11800,"v30":9.1,"a30":12050},
                 "Caerleon":    {"v7":40.5,"a7":11200,"v30":38.0,"a30":11500} },
  ...
}}
```

- Per `(item, city)`: `v` = mean items sold per day over the window, `a` = volume-weighted avg price.
  Aggregated across qualities. A city appears only if the item actually traded there (never a guess).
- Lets the Top Traded tab rank the most-traded gear per city (7d/30d), not only the Black Market.
  The Black Market column stays in `baseline.json` (`vol7`/`a7`); this file covers the 7 city markets.
- The app ranks by daily silver = `v * a` and joins name/tier/category from `baseline.json`.

## craftmeta.json

```json
{ "items": {
  "T4_2H_ARCANESTAFF": {"iv": 512, "bc": "Lymhurst"},
  "T8_ARMOR_PLATE_SET3@3": {"iv": 32768, "bc": "Bridgewatch"},
  "T4_CAPEITEM_MARTLOCK": null
}}
```

- `iv` = Item Value = sum of the materials' `@itemvalue` (ao-bin-dumps) x count, nested recipes
  resolved recursively. Drives the exact station fee (below). Missing = a leaf material has no
  `@itemvalue` (faction tokens, skillbooks) - fee unknowable, app shows cost n/a.
- `bc` = the city whose +15% crafting specialty covers this item's `@craftingcategory`
  (scripts/data/bonus_cities.json, curated from ao-bin-dumps x community craft tables x wiki).
  Missing = no specialty (royal/faction/crystal-league gear).
- Coverage at last build: iv 5805/6138 (94.6%), bonus city 5545/6138 (90.3%).

## Craft-cost model (implemented in the app)

```
PB  = 18 (any royal city/Caerleon/Brecilien)                  # production bonus, additive
    + 15 (crafting the item in its bonus city `bc`)
    + 59 (crafting focus)
    + 10 or 20 (daily city bonus - rotates, check in-game Activities)
RRR = PB / (100 + PB)                                          # 15.2% base, 24.8% specialty,
                                                               # 43.5% focus, 47.9% spec+focus...
nutrition   = iv x 0.1125
station_fee = nutrition x (silver per 100 nutrition) / 100     # the number on the station sign
craft_cost  = artefact_and_token_cost + resource_cost x (1 - RRR) + station_fee
craft_margin = BM_resale - craft_cost                          # BM_resale = live BM buy or a7/a30
```

- RRR applies to **refined resources only**, never artefacts/tokens (`@maxreturnamount:"0"`).
- A manual RRR override remains in the UI (hideouts: base 1-26% by zone quality, +1%/power
  general +2% specialist, power cores up to +26/+30 - too situational to model).
- The RRR math is verified (values match the known in-game figures); the fee formula should be
  eyeballed once in game against a real craft window (HYPOTHESE until then).
- If any material price is null or `iv` is missing, `craft_margin` = n/a (honest, no invented cost).
