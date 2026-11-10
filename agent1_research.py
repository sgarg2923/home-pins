"""Agent 1: daily research. Google Trends -> products with OFFICIAL images/links -> pin copy -> landing pages."""
import os, re, sys, csv, json, html, time, random, shutil
import requests
from common import *

SITE = os.environ["SITE_BASE_URL"].rstrip("/")
FK_ID, FK_TOKEN = os.getenv("FK_AFFILIATE_ID"), os.getenv("FK_AFFILIATE_TOKEN")
PRICE_MIN, PRICE_MAX = 199, 2999
ANCHOR = "home decor"
# Pinterest website-claim tag (kept on every generated page so the claim never breaks)
VERIFY_META = '<meta name="p:domain_verify" content="%s"/>' % (os.getenv("PINTEREST_VERIFY") or "ff656e25a52b7f22a3ff1cef9239d416")

SEEDS = {
    "decor": ["led strip lights", "wall shelves", "macrame wall hanging", "table lamp", "artificial plants",
              "wall mirror", "scented candles", "aroma diffuser", "wall clock", "fairy lights",
              "cushion covers", "hanging planters"],
    "kitchen": ["air fryer", "spice rack", "glass storage jars", "vegetable chopper", "dish drying rack",
                "silicone baking mat", "coffee mug set", "lunch box", "kitchen trolley", "tea set"],
    "organization": ["fridge organizer", "cutlery organizer", "shoe rack", "storage baskets", "desk organizer",
                     "jewellery organizer", "bathroom organizer", "towel holder", "wardrobe organizer"],
}
GROUP_OF = {k: g for g, ks in SEEDS.items() for k in ks}
STORES = {"flipkart": "Flipkart", "amazon": "Amazon"}
DISCLOSURE = {
    "flipkart": "As a Flipkart affiliate I may earn a commission from qualifying purchases, at no extra cost to you. Prices and availability can change.",
    "amazon": "As an Amazon Associate I earn from qualifying purchases. Prices and availability can change.",
}


# ---------- keyword ranking ----------
def group_boost():
    g = jload(STATS, {}).get("group", {})
    vals = [v["avg"] for v in g.values() if v.get("n", 0) >= 3]
    if len(vals) < 2:
        return {}
    mean = sum(vals) / len(vals) or 1e-9
    return {k: max(0.5, min(2.0, v["avg"] / mean)) for k, v in g.items() if v.get("n", 0) >= 3}


def rank_keywords():
    pool = random.sample(list(GROUP_OF), 20)
    boost, scores = group_boost(), {}
    try:
        from pytrends.request import TrendReq
        py = TrendReq(hl="en-IN", tz=330, timeout=(10, 30))
        for i in range(0, len(pool), 4):
            batch = pool[i:i + 4]
            py.build_payload([ANCHOR] + batch, geo="IN", timeframe="today 3-m")
            df = py.interest_over_time()
            anchor = df[ANCHOR].tail(3).mean() or 1
            for kw in batch:
                rec, pri = df[kw].tail(3).mean(), df[kw].iloc[-9:-3].mean()
                scores[kw] = (rec / anchor) * ((rec + 1) / (pri + 1))
            time.sleep(8)
    except Exception as e:
        print(f"Google Trends unavailable ({e}); using random order.")
        scores = {k: random.random() for k in pool}
    for k in scores:
        scores[k] *= boost.get(GROUP_OF[k], 1.0)
    return sorted(scores, key=scores.get, reverse=True)


# ---------- product sources ----------
def flipkart_search(keyword):
    if not (FK_ID and FK_TOKEN):
        return []
    try:
        r = requests.get("https://affiliate-api.flipkart.net/affiliate/1.0/search.json",
                         params={"query": keyword, "resultCount": 10},
                         headers={"Fk-Affiliate-Id": FK_ID, "Fk-Affiliate-Token": FK_TOKEN}, timeout=40)
        r.raise_for_status()
        data = r.json().get("products", [])
    except Exception as e:
        print(f"Flipkart search failed for '{keyword}': {e}")
        return []
    out = []
    for p in data:
        b = p.get("productBaseInfoV1", {})
        imgs = b.get("imageUrls") or {}
        img = imgs.get("800x800") or imgs.get("400x400") or next(iter(imgs.values()), None)
        price = ((b.get("flipkartSpecialPrice") or b.get("flipkartSellingPrice") or {}).get("amount"))
        mrp = (b.get("maximumRetailPrice") or {}).get("amount") or price
        if not (b.get("inStock") and img and price and b.get("productUrl") and b.get("productId")):
            continue
        if not PRICE_MIN <= float(price) <= PRICE_MAX:
            continue
        out.append({"id": "fk-" + b["productId"].lower(), "store": "flipkart", "category": guess_category(keyword + " " + b.get("title", "")), "keyword": keyword,
                    "title": b.get("title", keyword)[:140], "desc": (b.get("productDescription") or "")[:400],
                    "image": img, "image_local": None, "link": b["productUrl"],
                    "discount": 1 - float(price) / float(mrp or price)})
    out.sort(key=lambda x: -x["discount"])
    return out


def manual_queue(used):
    """Reads inbox/manual_products.csv safely (BOM, odd headers, missing image files) and reports every row it cannot use."""
    path = "inbox/manual_products.csv"
    res = {"candidates": [], "skipped": [], "total": 0, "used": 0, "rows": [], "error": ""}
    if not os.path.exists(path):
        res["error"] = "inbox/manual_products.csv not found"
        return res
    seen = set()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for ln, raw in enumerate(csv.DictReader(f), start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
            if not any(row.values()):
                continue
            res["total"] += 1
            nm, lk = row.get("name", ""), row.get("link", "")
            res["rows"].append({"name": nm, "link": lk})
            why = "name is empty" if not nm else "link is empty" if not lk else "link must start with http" if not lk.startswith("http") else ""
            pid = "m-" + slugify(nm) if nm else ""
            if not why and pid in seen:
                why = "same name appears twice in the CSV"
            if why:
                res["skipped"].append({"line": ln, "name": nm[:50], "reason": why})
                continue
            seen.add(pid)
            if pid in used:
                res["used"] += 1
                continue
            img, local = row.get("image", ""), None
            if img and not img.startswith("http"):
                if os.path.exists(img):
                    os.makedirs(f"{DOCS}/img", exist_ok=True)
                    fn = os.path.basename(img)
                    shutil.copy(img, f"{DOCS}/img/{fn}")
                    local, img = img, f"{SITE}/img/{fn}"
                else:                                   # missing image file: do NOT skip the product, use the AI picture instead
                    res["skipped"].append({"line": ln, "name": nm[:50], "reason": f"image file '{img}' not found (product added without it)"})
                    img = ""
            cat = row.get("category", "") or guess_category(nm + " " + row.get("keyword", ""))
            res["candidates"].append({"id": pid, "store": detect_store(lk), "category": cat, "keyword": row.get("keyword") or nm, "title": nm,
                                      "desc": "", "image": img, "image_local": local, "link": lk, "discount": 0})
    return res


def manual_products(used):
    return manual_queue(used)["candidates"]


# ---------- copy ----------
def write_copy(p, n_variants):
    system = ("You write honest Pinterest copy for home & kitchen products for a global English-speaking audience. "
              "Use ONLY facts present in the product data. Never invent specs, prices, ratings or discounts. "
              "Reply with ONLY one JSON object.")
    user = f"""Product: {p['title']}
Details: {p['desc'] or 'n/a'}
Search keyword: {p['keyword']}
Return JSON: {{"page_text": "60-90 words, helpful, friendly, no hype",
"variants": [{n_variants} objects, each with: "pin_title" (max 90 chars, keyword-rich), "pin_description" (200-350 chars, natural keywords, end with 3 hashtags), "alt_text" (one sentence), "overlay_text" (max 6 words, shown on image, honest, e.g. "Small kitchen upgrade")]}}
Make the variants clearly different from each other."""
    for _ in range(3):
        try:
            d = json.loads(re.search(r"\{.*\}", cf_text(system, user, 1000), re.S).group(0))
            v = d["variants"]
            if len(v) >= n_variants and all({"pin_title", "pin_description", "alt_text", "overlay_text"} <= set(x) for x in v):
                return d["page_text"], v[:n_variants]
        except Exception as e:
            print("copy retry:", e)
    kw = p["keyword"]
    base = [{"pin_title": f"{kw.title()} for Your Home", "overlay_text": "Small upgrade, big change",
             "pin_description": f"Looking for {kw}? A practical pick to refresh your space. #homedecor #{kw.replace(' ', '')} #homeideas",
             "alt_text": f"{p['title']} styled in a home"},
            {"pin_title": f"Easy Home Idea: {kw.title()}", "overlay_text": "Home idea worth saving",
             "pin_description": f"Save this idea for later. {p['title'][:80]} could be a simple way to improve your home. #homeideas #{kw.replace(' ', '')} #organize",
             "alt_text": f"{p['title']} product"}]
    return f"{p['title']}. A practical pick for your home.", base[:n_variants]


# ---------- catalog + site ----------
def load_catalog(queue):
    cat = jload(CATALOG, [])
    if not cat and queue:      # bootstrap from an older queue
        seen = {}
        for it in queue:
            if it["pid"] not in seen:
                seen[it["pid"]] = {"pid": it["pid"], "store": detect_store(it["affiliate_link"]), "title": it["title"],
                                   "link": it["affiliate_link"], "page_text": it["page_text"], "slug": it["slug"],
                                   "image": it.get("image") or "", "created": it["created"], "seq": len(seen) + 1,
                                   "category": guess_category(it["title"] + " " + it["keyword"])}
        cat = list(seen.values())
    return cat


def rebuild_site(queue):
    try:
        import sitegen
        sitegen.build(load_catalog(queue))
    except Exception as ex:      # never block pinning because of a site problem
        import traceback
        traceback.print_exc()
        print("SITE BUILD FAILED (pins will still be posted):", ex)


# ---------- own digital products (Gumroad etc.) ----------
DIGITAL = "digital_products.json"


def find_file(name):
    for d in (".", "digital", "digital/images", "inbox", "docs/digital"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def add_digital(queue):
    """Keeps your own products on the website and adds at most ONE new digital pin to the queue per day."""
    items = jload(DIGITAL, [])
    if not items:
        return queue
    catalog = load_catalog(queue)
    changed = False
    items = [pr for pr in items if str(pr.get("url", "")).startswith("http")]     # skip products without a real link yet
    for pr in items:
        pid = "dg-" + slugify(pr["name"])[:30]
        cover = find_file(pr.get("cover", ""))
        old = next((x for x in catalog if x["pid"] == pid), None)
        if old:
            new = {"link": pr["url"], "extra": pr.get("extra_links", []), "category": pr.get("category", "Printables"), "page_text": pr["summary"]}
            if any(old.get(k) != v for k, v in new.items()):
                old.update(new)
                changed = True
            continue
        img = ""
        if cover:
            os.makedirs(f"{DOCS}/digital", exist_ok=True)
            shutil.copy(cover, f"{DOCS}/digital/{os.path.basename(cover)}")
            img = f"{SITE}/digital/{os.path.basename(cover)}"
        catalog.append({"pid": pid, "store": "own", "title": pr["name"], "link": pr["url"], "page_text": pr["summary"],
                        "slug": slugify(pr["name"])[:45] + "-" + pid[-6:], "image": img, "created": today(),
                        "category": pr.get("category", "Printables"), "extra": pr.get("extra_links", [])})
        changed = True
    if changed:
        jsave(CATALOG, catalog)
    state = get_state()
    if state.get("last_digital") != today():
        queued = {q["id"] for q in queue}
        for pr in items:
            pid = "dg-" + slugify(pr["name"])[:30]
            sep = "&" if "?" in pr["url"] else "?"
            link = f"{pr['url']}{sep}utm_source=pinterest&utm_medium=pin&utm_campaign={slugify(pr['name'])[:30]}"
            for i, pin in enumerate(pr.get("pins", [])):
                qid = f"{pid}-p{i}-v0"
                path = find_file(pin["image"])
                if qid in queued or not path:
                    continue
                queue.append({"id": qid, "pid": pid, "store": "own", "keyword": pr["name"], "title": pin["title"],
                              "image": "", "image_local": None, "affiliate_link": pr["url"], "page_url": link, "slug": pid,
                              "page_text": pr["summary"], "pin_title": pin["title"], "pin_description": pin["description"],
                              "alt_text": pin["alt_text"], "overlay_text": "", "group": "digital", "pin_image": path,
                              "status": "pending", "attempts": 0, "created": today()})
                state["last_digital"] = today()
                jsave(STATE, state)
                jsave(QUEUE, queue)
                print("Queued digital pin:", pin["title"])
                return queue
    return queue


# ---------- main ----------
def csv_report(mq, picked_n=0):
    """Numbers + messages the dashboard shows about the CSV."""
    left = len(mq["candidates"]) - picked_n
    return {"total_rows": mq["total"], "already_added": mq["used"], "remaining": max(left, 0), "skipped": mq["skipped"][:15],
            "last6": mq["rows"][-6:], "error": mq["error"]}


def main():
    try:
        import agent3_radar
        agent3_radar.run_if_due()
    except Exception as ex:      # the radar must never stop the daily work
        print("Radar skipped:", ex)
    queue = add_digital(jload(QUEUE, []))
    state = get_state()
    force = os.getenv("FORCE_ADD", "").strip().lower() in ("1", "true", "yes")
    used = set(jload(HISTORY, []))
    mq = manual_queue(used)
    n, ppp, _ = plan(state)
    prev = jload(STATUS, {})
    same_day = prev.get("date") == today()
    base = {"updated": now_ist(), "date": today(), "mode": "forced (Add now button)" if force else "scheduled/manual run"}
    if state.get("last_added") == today() and not force:
        done = prev.get("added_today", []) if same_day else []
        nxt = [c["title"] for c in mq["candidates"][:n]]
        set_status(**base, outcome="already_today", added_today=done, next_up=[c["title"] for c in mq["candidates"][:4]], csv=csv_report(mq),
                   message=f"Today's products were already added ({', '.join(x['name'] for x in done) or 'earlier run'}). Nothing was added again. "
                           f"Next up: {', '.join(nxt) or 'nothing left in the CSV'}. Use 'Add next products now' to add them early.")
        print("Products for today already added. Next up:", nxt)
        rebuild_site(queue)
        return
    picked = mq["candidates"][:n]
    if len(picked) < n and FK_ID and FK_TOKEN:
        for kw in rank_keywords():
            if len(picked) >= n:
                break
            if any(p["keyword"] == kw for p in picked):
                continue
            fresh = [p for p in flipkart_search(kw) if p["id"] not in used]
            if fresh:
                picked.append(fresh[0])
    if not picked:
        why = mq["error"] or ("the CSV has no usable rows" if not mq["used"] else f"all {mq['used']} usable products in the CSV are already added")
        set_status(**base, outcome="no_new_products", added_today=prev.get("added_today", []) if same_day else [], next_up=[], csv=csv_report(mq),
                   message=f"No product was added: {why}. Upload new products to inbox/manual_products.csv (dashboard > CSV editor).")
        print("NO NEW PRODUCTS:", why)
        rebuild_site(queue)
        return
    added, log = [], jload(ADDED_LOG, [])
    for p in picked:
        page_text, variants = write_copy(p, ppp)
        slug = f"{slugify(p['title'])[:45]}-{slugify(p['id'])[-8:]}"
        for i, v in enumerate(variants):
            queue.append({**{k: p[k] for k in ("store", "keyword", "title", "image", "image_local")},
                          "id": f"{p['id']}-v{i}", "pid": p["id"], "group": GROUP_OF.get(p["keyword"], "other"),
                          "affiliate_link": p["link"], "slug": slug, "page_url": f"{SITE}/p/{slug}.html",
                          "page_text": page_text, "status": "pending", "attempts": 0, "created": today(), **v})
        used.add(p["id"])
        catalog = load_catalog(queue)
        if not any(x["pid"] == p["id"] for x in catalog):
            catalog.append({"pid": p["id"], "store": p["store"], "title": p["title"], "link": p["link"], "page_text": page_text,
                            "slug": slug, "image": p["image"], "created": today(), "category": p["category"], "seq": len(catalog) + 1})
        jsave(CATALOG, catalog)
        ts = now_ist()
        page = f"{SITE}/p/{slug}.html"
        added.append({"name": p["title"], "category": p["category"], "link": p["link"], "added_at": ts, "page": page})
        log.append({"date": today(), "time": ts, "name": p["title"], "category": p["category"], "link": p["link"], "page": page, "pins_queued": len(variants),
                    "mode": "forced" if force else "scheduled"})
    queue = queue[-400:]
    jsave(QUEUE, queue)
    jsave(HISTORY, sorted(used))
    jsave(ADDED_LOG, log[-300:])
    state["last_added"] = today()
    jsave(STATE, state)
    rebuild_site(queue)
    left = max(len(mq["candidates"]) - len(picked), 0)
    names = [x["name"] for x in added]
    set_status(**base, outcome="added", added_today=(prev.get("added_today", []) if same_day else []) + added, last_added={"date": today(), "names": names},
               next_up=[c["title"] for c in mq["candidates"][len(picked):][:4]], csv=csv_report(mq, len(picked)),
               message=f"Added to the website and queued {ppp * len(picked)} pin(s): {', '.join(names)}. {left} product(s) left in the CSV (about {left // max(n, 1)} day(s)).")
    print(f"Added {len(picked)} products x {ppp} pin(s):", names)


if __name__ == "__main__":
    main()
