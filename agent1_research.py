"""Agent 1: daily research. Google Trends -> products with OFFICIAL images/links -> pin copy -> landing pages."""
import os, re, sys, csv, json, html, time, random, shutil
import requests
from common import *

SITE = os.environ["SITE_BASE_URL"].rstrip("/")
FK_ID, FK_TOKEN = os.getenv("FK_AFFILIATE_ID"), os.getenv("FK_AFFILIATE_TOKEN")
PRICE_MIN, PRICE_MAX = 199, 2999
ANCHOR = "home decor"

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
        out.append({"id": "fk-" + b["productId"].lower(), "store": "flipkart", "keyword": keyword,
                    "title": b.get("title", keyword)[:140], "desc": (b.get("productDescription") or "")[:400],
                    "image": img, "image_local": None, "link": b["productUrl"],
                    "discount": 1 - float(price) / float(mrp or price)})
    out.sort(key=lambda x: -x["discount"])
    return out


def manual_products(used):
    """inbox/manual_products.csv: name,keyword,image,link  (use for Amazon: SiteStripe image + link)."""
    path = "inbox/manual_products.csv"
    if not os.path.exists(path):
        return []
    out = []
    for row in csv.DictReader(open(path, encoding="utf-8")):
        if not (row.get("name") and row.get("image") and row.get("link")):
            continue
        pid = "m-" + slugify(row["name"])
        if pid in used:
            continue
        img, local = row["image"].strip(), None
        if not img.startswith("http"):
            if not os.path.exists(img):
                continue
            os.makedirs(f"{DOCS}/img", exist_ok=True)
            fn = os.path.basename(img)
            shutil.copy(img, f"{DOCS}/img/{fn}")
            local, img = img, f"{SITE}/img/{fn}"
        store = "amazon" if "amazon." in row["link"] or "amzn." in row["link"] else "flipkart"
        out.append({"id": pid, "store": store, "keyword": row.get("keyword") or row["name"], "title": row["name"],
                    "desc": "", "image": img, "image_local": local, "link": row["link"], "discount": 0})
    return out


# ---------- copy ----------
def write_copy(p, n_variants):
    system = ("You write honest Pinterest copy for home & kitchen products for an Indian audience. "
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


# ---------- landing pages (free GitHub Pages) ----------
CSS = ("body{font-family:system-ui,sans-serif;margin:0;background:#faf7f4;color:#222}main{max-width:720px;margin:auto;padding:20px}"
       "img{max-width:100%;height:auto;border-radius:12px;background:#fff}a.btn{display:block;text-align:center;background:#e60023;color:#fff;"
       "padding:14px;border-radius:999px;font-weight:700;text-decoration:none;margin:20px 0}.d{font-size:13px;color:#666}"
       ".g{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}.g a{color:#222;text-decoration:none;font-size:14px}")


def page(title, body, img=""):
    og = f'<meta property="og:title" content="{html.escape(title)}"><meta property="og:image" content="{html.escape(img)}">' if img else ""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title>{og}<style>{CSS}</style></head><body><main>{body}</main></body></html>')


def build_site(queue):
    os.makedirs(f"{DOCS}/p", exist_ok=True)
    open(f"{DOCS}/.nojekyll", "w").close()
    uniq = {}
    for it in queue:
        uniq.setdefault(it["pid"], it)
    for it in uniq.values():
        store = STORES[it["store"]]
        body = (f'<p><a href="{SITE}/">&larr; More home &amp; kitchen finds</a></p><h1>{html.escape(it["title"])}</h1>'
                f'<img src="{html.escape(it["image"])}" alt="{html.escape(it["title"])}">'
                f'<p>{html.escape(it["page_text"])}</p>'
                f'<a class="btn" rel="sponsored nofollow noopener" href="{html.escape(it["affiliate_link"])}">View current price on {store}</a>'
                f'<p class="d">{html.escape(DISCLOSURE[it["store"]])}</p>')
        open(f'{DOCS}/p/{it["slug"]}.html', "w", encoding="utf-8").write(page(it["title"], body, it["image"]))
    cards = "".join(f'<a href="{SITE}/p/{i["slug"]}.html"><img src="{html.escape(i["image"])}" alt=""><br>{html.escape(i["title"][:60])}</a>'
                    for i in list(uniq.values())[-60:][::-1])
    idx = (f'<h1>Home &amp; Kitchen Finds</h1><p>Practical picks for your home. '
           f'<span class="d">Some links are affiliate links; I may earn a commission at no extra cost to you.</span></p><div class="g">{cards}</div>')
    open(f"{DOCS}/index.html", "w", encoding="utf-8").write(page("Home & Kitchen Finds", idx))


# ---------- main ----------
def main():
    state = get_state()
    queue = jload(QUEUE, [])
    if state.get("last_added") == today():
        print("Products for today already added.")
        build_site(queue)
        return
    n, ppp, _ = plan(state)
    used = set(jload(HISTORY, []))
    picked = manual_products(used)[:n]
    if len(picked) < n:
        for kw in rank_keywords():
            if len(picked) >= n:
                break
            if any(p["keyword"] == kw for p in picked):
                continue
            fresh = [p for p in flipkart_search(kw) if p["id"] not in used]
            if fresh:
                picked.append(fresh[0])
    if not picked:
        sys.exit("No products found. Set FK_AFFILIATE_ID/FK_AFFILIATE_TOKEN or add rows to inbox/manual_products.csv")
    for p in picked:
        page_text, variants = write_copy(p, ppp)
        slug = f"{slugify(p['title'])[:45]}-{slugify(p['id'])[-8:]}"
        for i, v in enumerate(variants):
            queue.append({**{k: p[k] for k in ("store", "keyword", "title", "image", "image_local")},
                          "id": f"{p['id']}-v{i}", "pid": p["id"], "group": GROUP_OF.get(p["keyword"], "other"),
                          "affiliate_link": p["link"], "slug": slug, "page_url": f"{SITE}/p/{slug}.html",
                          "page_text": page_text, "status": "pending", "attempts": 0, "created": today(), **v})
        used.add(p["id"])
    queue = queue[-400:]
    jsave(QUEUE, queue)
    jsave(HISTORY, sorted(used))
    state["last_added"] = today()
    jsave(STATE, state)
    build_site(queue)
    print(f"Added {len(picked)} products x {ppp} pin(s).")


if __name__ == "__main__":
    main()
