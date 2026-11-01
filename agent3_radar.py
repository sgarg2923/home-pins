"""Agent 3: Demand Radar. Weekly search-DEMAND signals for printable-product ideas (NOT sales data).
Sources: Google Trends (pytrends, last 12 months, US) + Google autocomplete. Output: data/ideas.json (shown in the dashboard)."""
import time, json, datetime as dt
import requests
from common import jload, jsave, today, DATA

OUT = f"{DATA}/ideas.json"
ANCHOR = "budget planner"
# keyword -> (product type, product idea)
SEEDS = {
    "adhd budget planner": ("Planners", "ADHD-friendly 2027 budget planner"), "sinking funds tracker": ("Trackers", "Sinking funds tracker set"),
    "cash envelope": ("Trackers", "Cash envelope and savings challenge binder"), "savings challenge": ("Trackers", "Savings challenge printables"),
    "debt payoff tracker": ("Trackers", "Debt payoff tracker"), "bi weekly budget": ("Planners", "Bi-weekly paycheck budget planner"),
    "paycheck budget": ("Planners", "Paycheck-to-paycheck budget planner"), "habit tracker printable": ("Trackers", "Habit tracker bundle"),
    "meal planner printable": ("Planners", "Weekly meal planner and grocery list"), "cleaning schedule printable": ("Planners", "Cleaning schedule planner"),
    "undated planner": ("Planners", "Undated weekly planner"), "weekly planner printable": ("Planners", "Weekly planner"),
    "gratitude journal printable": ("Worksheets", "Gratitude journal pages"), "workout log printable": ("Trackers", "Workout log"),
    "reading log printable": ("Trackers", "Reading log and book tracker"), "chore chart": ("Trackers", "Family chore chart"),
    "self care planner": ("Planners", "Self-care planner"), "study planner printable": ("Planners", "Student study planner"),
    "no spend challenge": ("Trackers", "No-spend challenge tracker"), "subscription tracker": ("Trackers", "Subscription and bill tracker"),
    "wedding planner printable": ("Planners", "Wedding planning checklist set"), "baby milestone tracker": ("Trackers", "Baby milestone tracker"),
}
SEED_TEXT = [k for k in SEEDS]


def autocomplete(q):
    try:
        r = requests.get("https://suggestqueries.google.com/complete/search", params={"client": "firefox", "q": q}, timeout=10)
        return [s for s in r.json()[1] if s != q][:8]
    except Exception:
        return []


def fetch_scores(seeds):
    """momentum = last 4 weeks vs the 8 weeks before; level = vs the anchor keyword in the same batch."""
    from pytrends.request import TrendReq
    py = TrendReq(hl="en-US", tz=0, timeout=(10, 30))
    out, fails = {}, 0
    for i in range(0, len(seeds), 4):
        batch = seeds[i:i + 4]
        try:
            py.build_payload([ANCHOR] + batch, timeframe="today 12-m", geo="US")
            df = py.interest_over_time()
            anchor = max(float(df[ANCHOR].tail(4).mean()), 1.0)
            for kw in batch:
                s = df[kw]
                rec, pri = float(s.tail(4).mean()), float(s.iloc[-12:-4].mean())
                peak = s.idxmax().strftime("%B") if s.max() > 0 else ""
                out[kw] = {"level": round(rec / anchor, 2), "momentum": round((rec + 1) / (pri + 1), 2), "peak_month": peak}
        except Exception as e:
            fails += 1
            print(f"Trends batch failed ({str(e)[:60]})")
        time.sleep(8)
    return out, fails


def rising(kw):
    try:
        from pytrends.request import TrendReq
        py = TrendReq(hl="en-US", tz=0, timeout=(10, 30))
        py.build_payload([kw], timeframe="today 3-m", geo="US")
        df = py.related_queries()[kw]["rising"]
        return [str(q) for q in df["query"].head(5)] if df is not None else []
    except Exception:
        return []


def score(v):
    return round(100 * (0.6 * min(v["level"], 2) / 2 + 0.4 * min(v["momentum"], 2) / 2), 1)


def run():
    data, fails = fetch_scores(SEED_TEXT)
    if not data:
        old = jload(OUT, {})
        old.update({"status": "blocked", "note": "Google Trends did not answer (rate limit). Previous ideas kept. Will try again next week."})
        old.setdefault("generated", today()); old.setdefault("ideas", [])
        old["last_try"] = today()
        jsave(OUT, old)
        print("Radar: Google Trends blocked, kept previous ideas.")
        return old
    ideas = []
    for kw, v in data.items():
        ptype, idea = SEEDS[kw]
        ideas.append({"keyword": kw, "score": score(v), "level": v["level"], "momentum": v["momentum"], "peak_month": v["peak_month"],
                      "type": ptype, "idea": idea, "rising": [], "suggestions": []})
    ideas.sort(key=lambda x: -x["score"])
    for it in ideas[:8]:
        it["rising"], it["suggestions"] = rising(it["keyword"]), autocomplete(it["keyword"])
        time.sleep(5)
    res = {"generated": today(), "last_try": today(), "status": "ok" if not fails else "partial", "region": "US", "window": "12 months",
           "note": "Search-demand signal from Google Trends and autocomplete. This is NOT sales data.", "ideas": ideas}
    jsave(OUT, res)
    print(f"Radar: {len(ideas)} ideas scored. Top: {[i['keyword'] for i in ideas[:3]]}")
    return res


def run_if_due(days=7):
    cur = jload(OUT, {})
    try:
        last = dt.date.fromisoformat(cur.get("last_try") or cur.get("generated") or "2000-01-01")
    except Exception:
        last = dt.date(2000, 1, 1)
    if (dt.date.fromisoformat(today()) - last).days >= days:
        return run()
    print("Radar: ideas are fresh, nothing to do.")


if __name__ == "__main__":
    run()
