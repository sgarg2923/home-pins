"""Shared helpers: storage, schedule plan, free LLM (Cloudflare Workers AI)."""
import os, json, re, time, math, datetime as dt
import requests

DATA, DOCS = "data", "docs"
QUEUE, HISTORY, STATE, STATS = (f"{DATA}/{n}.json" for n in ("queue", "history", "state", "stats"))
WARMUP_DAYS = 14          # new Pinterest accounts: start slow, then scale up
PRODUCTS_PER_DAY = 2


def jload(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def jsave(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def today():
    ist = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5, minutes=30)
    return ist.date().isoformat()


def get_state():
    s = jload(STATE, {})
    if "start" not in s:
        s["start"] = today()
        jsave(STATE, s)
    return s


def plan(state):
    """(products/day, pins per product, pins per run). Two runs/day. Auto-scales after warm-up."""
    days = (dt.date.fromisoformat(today()) - dt.date.fromisoformat(state["start"])).days
    ppp = 1 if days < WARMUP_DAYS else 2
    return PRODUCTS_PER_DAY, ppp, math.ceil(PRODUCTS_PER_DAY * ppp / 2)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "item"


def cf_text(system, user, max_tokens=900):
    acc, tok = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    model = os.getenv("CF_TEXT_MODEL", "@cf/meta/llama-3.1-8b-instruct")
    last = None
    for i in range(3):
        try:
            r = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}",
                headers={"Authorization": f"Bearer {tok}"},
                json={"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                      "max_tokens": max_tokens},
                timeout=120)
            r.raise_for_status()
            return r.json()["result"]["response"]
        except Exception as e:
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"Cloudflare text failed: {last}")
