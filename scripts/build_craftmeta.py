#!/usr/bin/env python3
"""
build_craftmeta.py - City Buy List craft metadata (item value + bonus city)

Emits docs/data/craftmeta.json: for every baseline gear key,
  - iv : Item Value = sum of the materials' @itemvalue (ao-bin-dumps) x count.
         Drives the exact station fee: nutrition = iv x 0.1125,
         fee = nutrition x (station fee per 100 nutrition) / 100.
         null when a material has no @itemvalue (never a guess).
  - bc : bonus city for the item's @craftingcategory (+15% production bonus
         when crafted there), from scripts/data/bonus_cities.json.
         null when the category has no city specialty (royal/faction sets...).

Game-patch data (like recipes.json): rebuild only on game patches.

Usage:
  python scripts/build_craftmeta.py                      # downloads ao-bin-dumps items.json
  python scripts/build_craftmeta.py --dump items.json    # reuse a local dump (17 MB)
"""
import argparse, json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "docs" / "data" / "baseline.json"
RECIPES = ROOT / "docs" / "data" / "recipes.json"
CITIES = ROOT / "scripts" / "data" / "bonus_cities.json"
OUT = ROOT / "docs" / "data" / "craftmeta.json"
AOBIN_URL = "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/items.json"


def load_dump(path):
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    print(f"downloading {AOBIN_URL} ...")
    with urllib.request.urlopen(AOBIN_URL, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def index_dump(dump):
    """uniquename -> (@itemvalue int|None, @craftingcategory str|None), all item groups."""
    idx = {}
    for group in dump["items"].values():
        if not isinstance(group, list):
            group = [group]
        for e in group:
            if not isinstance(e, dict) or "@uniquename" not in e:
                continue
            iv = e.get("@itemvalue")
            idx[e["@uniquename"]] = (float(iv) if iv is not None else None, e.get("@craftingcategory"))
    return idx


def item_iv(key, recipes, idx, missing, seen, depth=0):
    """Item Value of a crafted key = sum of material IVs x count. A material with no
    @itemvalue that is itself craftable (nested recipe: specialty capes eat a crafted
    T4_CAPE, faction sets eat a crafted SET1 piece) resolves recursively. None when a
    leaf material has no @itemvalue - never a guess."""
    if depth > 4 or key in seen:
        return None
    seen = seen | {key}
    r = recipes.get(key)
    if not r:
        return None
    total = 0
    for mat, count in r:
        mat_un = re.sub(r"@\d+$", "", mat)               # T4_METALBAR_LEVEL1@1 -> T4_METALBAR_LEVEL1
        mat_iv = idx.get(mat_un, (None, None))[0]
        if mat_iv is None:
            mat_iv = item_iv(mat, recipes, idx, missing, seen, depth + 1)   # nested craftable
        if mat_iv is None:
            missing[mat_un] = missing.get(mat_un, 0) + 1
            return None
        total += mat_iv * count
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="local ao-bin-dumps items.json instead of downloading")
    args = ap.parse_args()

    keys = list(json.loads(BASELINE.read_text(encoding="utf-8"))["items"].keys())
    recipes = json.loads(RECIPES.read_text(encoding="utf-8"))["items"]
    cat2city = {k: v for k, v in json.loads(CITIES.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    idx = index_dump(load_dump(args.dump))
    print(f"{len(keys)} baseline keys | {len(idx)} dump uniquenames | {len(cat2city)} bonus categories")

    items, iv_ok, iv_null, bc_ok = {}, 0, 0, 0
    missing_mats = {}
    for key in keys:
        base_un = re.sub(r"@\d+$", "", key)              # dump uniquename = market id minus @N
        _, cc = idx.get(base_un, (None, None))
        bc = cat2city.get(cc) if cc else None

        iv = item_iv(key, recipes, idx, missing_mats, set())
        if iv is not None:
            iv = round(iv)
            iv_ok += 1
        else:
            iv_null += 1
        if bc:
            bc_ok += 1
        rec = {}
        if iv is not None:
            rec["iv"] = iv
        if bc:
            rec["bc"] = bc
        items[key] = rec or None

    payload = {
        "notes": {
            "iv": "Item Value = sum of material @itemvalue x count (ao-bin-dumps). Station fee = iv x 0.1125 x (fee per 100 nutrition) / 100. Missing = a material has no @itemvalue; app shows fee n/a.",
            "bc": "city whose +15% crafting specialty covers this item's @craftingcategory. Missing = no specialty (royal/faction/crystal-league sets).",
            "source": "ao-bin-dumps + scripts/data/bonus_cities.json; rebuild on game patch only",
        },
        "items": items,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"iv computed {iv_ok}/{len(keys)} | iv null {iv_null} | bonus city {bc_ok}/{len(keys)}")
    if missing_mats:
        top = sorted(missing_mats.items(), key=lambda x: -x[1])[:10]
        print("materials without @itemvalue (item iv -> null):", top)


if __name__ == "__main__":
    sys.exit(main())
