"""Agent 2: keep the REAL product photo (background removed only), generate a new AI background,
add a headline, publish the pin, then learn from analytics."""
import os, io, sys, time, base64, random, subprocess, datetime as dt, urllib.parse
import requests
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from common import *

API = os.getenv("PINTEREST_API_BASE") or "https://api-sandbox.pinterest.com/v5"
BOARD = os.environ["PINTEREST_BOARD_ID"]
CF_ACC, CF_TOK = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
W, H = 1000, 1500
PH = {"Content-Type": "application/json"}      # Authorization is added in main()
POSTED_LOG = "data/posted_log.json"
SCENES = {
    "marble": "a clean white marble kitchen countertop, soft morning window light, blurred modern kitchen behind",
    "wood": "a warm wooden table in a cozy living room, soft daylight, blurred cushions and plants behind",
    "pastel": "a minimal pastel beige studio backdrop with a smooth tabletop and soft shadows",
    "shelf": "a light oak shelf next to a bright window, blurred green plants and white wall behind",
}
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]
_session = None


# ---------- learning ----------
def learn(queue):
    try:
        today_d = dt.date.fromisoformat(today())
        for it in queue:
            if it["status"] != "posted" or not it.get("pin_id") or it.get("measured_on") == today():
                continue
            start = dt.date.fromisoformat(it["created"])
            if (today_d - start).days < 3 or it.get("measures", 0) >= 4:
                continue
            r = requests.get(f"{API}/pins/{it['pin_id']}/analytics", headers=PH, timeout=30,
                             params={"start_date": start.isoformat(), "end_date": today(),
                                     "metric_types": "IMPRESSION,PIN_CLICK,SAVE"})
            if r.ok:
                m = r.json().get("all", {}).get("summary_metrics", {})
                it["metrics"] = {k: m.get(k, 0) or 0 for k in ("IMPRESSION", "PIN_CLICK", "SAVE")}
                it["measured_on"], it["measures"] = today(), it.get("measures", 0) + 1
        stats = {"scene": {}, "group": {}}
        for it in queue:
            m = it.get("metrics")
            if not m:
                continue
            score = (m["PIN_CLICK"] * 5 + m["SAVE"] * 3 + 1) / (m["IMPRESSION"] + 200)
            for key, val in (("scene", it.get("scene")), ("group", it.get("group"))):
                if val:
                    s = stats[key].setdefault(val, {"sum": 0, "n": 0})
                    s["sum"] += score
                    s["n"] += 1
        for key in stats:
            for s in stats[key].values():
                s["avg"] = s["sum"] / s["n"]
        jsave(STATS, stats)
    except Exception as e:
        print("learn() skipped:", e)


def choose_scene():
    sc = jload(STATS, {}).get("scene", {})
    good = {k: v["avg"] for k, v in sc.items() if v.get("n", 0) >= 3 and k in SCENES}
    if good and random.random() < 0.7:
        return max(good, key=good.get)
    return random.choice(list(SCENES))


# ---------- images ----------
def load_product(it):
    if it.get("image_local") and os.path.exists(it["image_local"]):
        return Image.open(it["image_local"]).convert("RGBA")
    r = requests.get(it["image"], timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGBA")


def cutout(img):
    """Remove background only; product pixels stay untouched. Reject bad cutouts."""
    global _session
    from rembg import remove, new_session
    if _session is None:
        _session = new_session(os.getenv("REMBG_MODEL", "u2net"))
    flat = Image.new("RGB", img.size, (255, 255, 255))
    flat.paste(img, mask=img.split()[3])
    out = remove(flat, session=_session).convert("RGBA")
    a = out.split()[3]
    cov = a.point(lambda v: 255 if v > 128 else 0).histogram()[255] / (out.width * out.height)
    if not 0.06 <= cov <= 0.95:
        raise ValueError(f"bad cutout (coverage {cov:.2f})")
    return out.crop(a.getbbox())


def cf_image(prompt):
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                      headers={"Authorization": f"Bearer {CF_TOK}"}, json={"prompt": prompt, "steps": 8}, timeout=180)
    r.raise_for_status()
    return base64.b64decode(r.json()["result"]["image"])


def pollinations_image(prompt):
    r = requests.get(f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1000&height=1500&model=flux&nologo=true", timeout=180)
    r.raise_for_status()
    return r.content


def background(scene):
    prompt = (f"empty {SCENES[scene]}, empty surface in the foreground center, no objects, no products, no people, "
              "no text, photorealistic, shallow depth of field, high quality")
    for fn in (cf_image, pollinations_image):
        for _ in range(2):
            try:
                im = Image.open(io.BytesIO(fn(prompt))).convert("RGB")
                s = H / im.height
                im = im.resize((round(im.width * s), H), Image.LANCZOS)
                left = max(0, (im.width - W) // 2)
                return im.crop((left, 0, left + W, H)).resize((W, H))
            except Exception as e:
                print(f"{fn.__name__} failed: {e}")
    bg = Image.new("RGB", (W, H), (240, 232, 222))  # last-resort soft backdrop, never blocks posting
    return bg


def font(size):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def headline(canvas, text):
    d = ImageDraw.Draw(canvas, "RGBA")
    for size in (76, 66, 58, 50):
        f, lines, cur = font(size), [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= W - 160:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= 3:
            break
    lh = int(size * 1.25)
    box_h = lh * len(lines) + 50
    d.rounded_rectangle((50, 60, W - 50, 60 + box_h), 28, fill=(0, 0, 0, 150))
    for i, ln in enumerate(lines):
        d.text((W / 2, 85 + i * lh), ln, font=f, fill="white", anchor="ma")
    return canvas


def compose(cut, bg, text):
    s = min(800 / cut.width, 820 / cut.height, 1.5)
    cut = cut.resize((max(1, round(cut.width * s)), max(1, round(cut.height * s))), Image.LANCZOS)
    x, y = (W - cut.width) // 2, 900 - cut.height // 2 + 40
    layer = Image.new("L", (W, H), 0)
    layer.paste(cut.split()[3], (x, y + 26))
    layer = layer.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.5))
    bg = bg.convert("RGB")
    bg.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), layer)
    bg.paste(cut, (x, y), cut)
    headline(bg, text)
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def scene_path(it):
    v = int(it["id"].rsplit("-v", 1)[-1]) if "-v" in it["id"] else 0
    return v, (f"docs/img/{it['slug']}.jpg" if v == 0 else f"docs/img/{it['slug']}-v{v}.jpg")


def ensure_scene_image(it):
    """AI lifestyle image (no brand, clearly illustrative). Cached in docs/img (also used on the website)."""
    v, path = scene_path(it)
    thumb = f"docs/img/{it['slug']}-thumb.jpg"
    if os.path.exists(path):
        bg = Image.open(path).convert("RGB")
        if v == 0 and not os.path.exists(thumb):
            bg.resize((400, 600), Image.LANCZOS).save(thumb, "JPEG", quality=80)
        return bg
    extra = "" if v == 0 else ", " + SCENES[random.choice(list(SCENES))]
    prompt = (f"{it['keyword']} in a bright, modern, tidy home{extra}, styled lifestyle photo, natural light, "
              "photorealistic, no text, no logos, no brand names, no people")
    last = None
    for fn in (cf_image, pollinations_image):
        for _ in range(2):
            try:
                im = Image.open(io.BytesIO(fn(prompt))).convert("RGB")
                s = H / im.height
                im = im.resize((round(im.width * s), H), Image.LANCZOS)
                left = max(0, (im.width - W) // 2)
                bg = im.crop((left, 0, left + W, H)).resize((W, H))
                os.makedirs("docs/img", exist_ok=True)
                bg.save(path, "JPEG", quality=85)
                if v == 0:
                    bg.resize((400, 600), Image.LANCZOS).save(thumb, "JPEG", quality=80)
                return bg
            except Exception as e:
                last = e
                print(f"{fn.__name__} failed: {e}")
    raise RuntimeError(f"image generation failed: {last}")


def lifestyle_pin(it):
    bg = ensure_scene_image(it).copy()
    headline(bg, it["overlay_text"])
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def compose_card(img, bg, text):
    """Amazon-safe mode: the original product image stays 100% unaltered; only the surrounding scene is new."""
    img = img.convert("RGB")
    s = min(840 / img.width, 900 / img.height, 2.0)
    img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), 28, fill=255)
    x, y = (W - img.width) // 2, 900 - img.height // 2 + 40
    layer = Image.new("L", (W, H), 0)
    layer.paste(mask, (x, y + 22))
    layer = layer.filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * 0.45))
    bg = bg.convert("RGB")
    bg.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), layer)
    bg.paste(img, (x, y), mask)
    headline(bg, text)
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


# ---------- pinterest ----------
def page_live(url, wait=600):
    end = time.time() + wait
    while time.time() < end:
        try:
            if requests.get(url, timeout=20).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(20)
    return False


def get_token():
    """Preferred: refresh token (OAuth) -> fresh access token every run. Fallback: a ready access token (e.g. 30-day sandbox token)."""
    rt, aid, sec = (os.getenv(k) or "" for k in ("PINTEREST_REFRESH_TOKEN", "PINTEREST_APP_ID", "PINTEREST_APP_SECRET"))
    if rt and aid and sec:
        try:
            basic = base64.b64encode(f"{aid}:{sec}".encode()).decode()
            r = requests.post(f"{API}/oauth/token", headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
                              data={"grant_type": "refresh_token", "refresh_token": rt}, timeout=30)
            if r.ok and r.json().get("access_token"):
                j = r.json()
                days = int(j.get("refresh_token_expires_in", 0) or 0) // 86400
                if days:
                    print(f"Token refreshed. Refresh token valid for about {days} more days.")
                    if days < 14:
                        note(f"WARNING: your Pinterest refresh token expires in about {days} days. Run pinterest_auth.py again and update the secret.")
                return j["access_token"]
            print(f"Token refresh failed ({r.status_code}): {r.text[:150]}")
        except Exception as e:
            print("Token refresh error:", e)
    return (os.getenv("PINTEREST_ACCESS_TOKEN") or "").strip()


NOTES = []


def note(s):
    NOTES.append(s)
    print(s)


def board_pins():
    """(title, link) of pins already on the board. Used so a pin is NEVER posted twice. None if the list is unavailable."""
    seen, bookmark = set(), None
    try:
        for _ in range(8):
            params = {"page_size": 100}
            if bookmark:
                params["bookmark"] = bookmark
            r = requests.get(f"{API}/boards/{BOARD}/pins", headers=PH, params=params, timeout=30)
            if not r.ok:
                print(f"Could not list board pins ({r.status_code}); relying on the local log only.")
                return None
            d = r.json()
            for p in d.get("items", []):
                seen.add(((p.get("title") or "").strip(), (p.get("link") or "").split("?")[0]))
            bookmark = d.get("bookmark")
            if not bookmark:
                break
        return seen
    except Exception as e:
        print("Board listing skipped:", e)
        return None


def checkpoint(msg):
    """Inside GitHub Actions: save progress to the repo right after each pin, so a crash can never cause a re-post."""
    if os.getenv("GITHUB_ACTIONS") != "true":
        return
    try:
        run = lambda *a: subprocess.run(a, check=False, capture_output=True, text=True)
        run("git", "config", "user.name", "bot")
        run("git", "config", "user.email", "bot@users.noreply.github.com")
        run("git", "add", "-A", "data", "docs")
        if run("git", "diff", "--cached", "--quiet").returncode != 0:
            run("git", "commit", "-m", msg)
            for _ in range(3):
                if run("git", "pull", "--no-rebase", "-X", "ours", "-q", "--no-edit", "origin", "main").returncode == 0 \
                        and run("git", "push", "-q", "origin", "HEAD:main").returncode == 0:
                    break
    except Exception as e:
        print("checkpoint skipped:", e)


def report(queue):
    posted = [i for i in queue if i["status"] == "posted"]
    pend = [i for i in queue if i["status"] == "pending"]
    fail = [i for i in queue if i["status"] == "failed"]
    t = today()
    lines = ["### Pinterest agent report", "",
             f"- **Already posted:** {len(posted)} (today: {sum(1 for i in posted if i.get('posted_on') == t)})",
             f"- **Waiting in queue:** {len(pend)}", f"- **Failed (gave up after 3 tries):** {len(fail)}", ""]
    lines += [f"- {n}" for n in NOTES]
    if posted:
        lines += ["", "| Date | Pin | Pin ID |", "|---|---|---|"]
        lines += [f"| {i.get('posted_on', '')} | {i['pin_title'][:70]} | {i.get('pin_id', '')} |" for i in posted[-15:][::-1]]
    text = "\n".join(lines)
    print("\n" + text)
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass


def pin_it(it, b64):
    if it.get("store") == "own":          # your own product: no affiliate disclosure needed
        tag = ""
    else:
        tag = {"flipkart": "#affiliate Affiliate link, I may earn a commission.",
               "amazon": "#affiliate As an Amazon Associate I earn from qualifying purchases."}[detect_store(it["affiliate_link"])]
    tail = ""
    if not it.get("image") and not it.get("pin_image"):
        tail += "\n\nImage: AI-generated illustration."
    if tag:
        tail += "\n\n" + tag
    payload = {"board_id": BOARD, "title": it["pin_title"][:100],
               "description": it["pin_description"][: 495 - len(tail)] + tail,
               "link": it["page_url"], "alt_text": it["alt_text"][:500],
               "media_source": {"source_type": "image_base64", "content_type": "image/jpeg", "data": b64}}
    r = requests.post(f"{API}/pins", headers=PH, json=payload, timeout=120)
    if r.status_code in (401, 403):
        raise PermissionError(f"Pinterest auth/permission error {r.status_code}: {r.text[:200]}. "
                              "If this says authentication failed, the token is wrong or expired (sandbox tokens last 30 days). Create a new token and update the GitHub secret.")
    r.raise_for_status()
    return r.json()


def main():
    token = get_token()
    if not token:
        print("No Pinterest token found. Add PINTEREST_ACCESS_TOKEN (or the refresh-token secrets) in GitHub Secrets.")
        sys.exit(1)
    PH["Authorization"] = "Bearer " + token
    queue = jload(QUEUE, [])
    existing = board_pins()
    learn(queue)
    jsave(QUEUE, queue)
    per_run = plan(get_state())[2]
    fatal = False
    for it in [i for i in queue if i["status"] == "pending" and not i.get("image") and not i.get("pin_image")][:6]:
        try:                      # make every pending page image now, so the website never shows a gap
            ensure_scene_image(it)
        except Exception as e:
            print("page image failed:", e)
    for it in [i for i in queue if i["status"] == "pending"][:per_run]:
        key = (it["pin_title"][:100].strip(), it["page_url"].split("?")[0])
        if existing is not None and key in existing:        # already on the board: never post twice
            it.update(status="posted", pin_id=it.get("pin_id") or "already-on-board", posted_on=it.get("posted_on") or today())
            note(f"Skipped duplicate (already on the board): {it['pin_title'][:60]}")
            jsave(QUEUE, queue)
            continue
        try:
            if it.get("pin_image"):                       # ready-made pin image (own digital product)
                with open(it["pin_image"], "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
            elif not page_live(it["page_url"]):
                print("Landing page not live yet, will retry next run:", it["page_url"])
                continue
            else:
                it["scene"] = it.get("scene") or choose_scene()
            if it.get("pin_image"):
                pass
            elif not it.get("image"):
                b64 = lifestyle_pin(it)
                it["scene"] = "lifestyle"
            else:
                prod, bg = load_product(it), background(it["scene"])
                if detect_store(it["affiliate_link"]) == "amazon" and os.getenv("AMAZON_CUTOUT") != "1":
                    b64 = compose_card(prod, bg, it["overlay_text"])
                else:
                    b64 = compose(cutout(prod), bg, it["overlay_text"])
            pin = pin_it(it, b64)
            it.update(status="posted", pin_id=pin.get("id"), posted_on=today())
            if existing is not None:
                existing.add(key)
            log = jload(POSTED_LOG, [])
            log.append({"id": it["id"], "title": it["pin_title"], "pin_id": pin.get("id"), "date": today()})
            jsave(POSTED_LOG, log)
            jsave(QUEUE, queue)
            checkpoint("agent2: pinned " + it["id"][:40])
            print("Pinned:", it["pin_title"], pin.get("id"))
        except PermissionError as e:
            print(e)
            fatal = True
        except Exception as e:
            it["attempts"] = it.get("attempts", 0) + 1
            it["last_error"] = str(e)[:200]
            if it["attempts"] >= 3:
                it["status"] = "failed"
            print(f"Failed ({it['attempts']}/3) {it['title'][:50]}: {e}")
        jsave(QUEUE, queue)
        if fatal:
            break
        time.sleep(45)
    report(queue)
    if fatal:
        sys.exit(1)


if __name__ == "__main__":
    main()
