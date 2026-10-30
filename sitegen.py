"""Static site generator for the affiliate site (GitHub Pages /docs).
Builds: home (10/page pagination), category pages, product pages, search, About, Contact,
Privacy, Disclosure, Terms, 404, sitemap.xml, robots.txt, shared CSS/JS, logo."""
import os, io, json, html, math, shutil, datetime as dt
from common import jload, slugify

SITE = os.environ["SITE_BASE_URL"].rstrip("/")
DOCS = "docs"
PER_PAGE = 10
VERIFY = os.getenv("PINTEREST_VERIFY") or "ff656e25a52b7f22a3ff1cef9239d416"
POLICY_DATE = "October 26, 2026"
HOME_CATS = ["Kitchen", "Organization", "Decor", "Festive"]
DIGITAL_CATS = ["Planners", "Trackers", "Worksheets", "Wall Art", "Templates", "Printables"]
CAT_ORDER = HOME_CATS + DIGITAL_CATS
CAT_TEXT = {
    "Kitchen": "Handy kitchen tools, drinkware and gadgets that make everyday cooking easier.",
    "Organization": "Storage ideas and organizers to tidy up your kitchen, cabinets and drawers.",
    "Decor": "Cozy lighting and simple decor touches that make a home feel warm.",
    "Festive": "Decorations and ideas for festivals and celebrations, including Diwali.",
    "Planners": "Printable planners for money, goals and daily life. Instant download.",
    "Trackers": "Habit, challenge and progress trackers you can print at home.",
    "Worksheets": "Printable worksheets for learning and planning.",
    "Wall Art": "Printable wall art for a quick home refresh.",
    "Templates": "Digital templates (resume, Notion and more).",
    "Printables": "Printable planners and trackers you can download instantly and print at home.",
}
e = html.escape
PH = f"{SITE}/assets/placeholder.svg"
BS_CSS, BS_JS = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"


def use_local_bootstrap():
    """If bootstrap.min.css and bootstrap.bundle.min.js are in the repo, copy them to docs/assets and use them (no CDN)."""
    global BS_CSS, BS_JS
    for name, var in (("bootstrap.min.css", "css"), ("bootstrap.bundle.min.js", "js")):
        for d in (".", "vendor", "assets_src"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
                shutil.copy(p, os.path.join(DOCS, "assets", name))
                if var == "css":
                    BS_CSS = u("assets/" + name)
                else:
                    BS_JS = u("assets/" + name)
                break
ONERR = f"this.onerror=null;this.src='{PH}'"


# ---------------- helpers ----------------
def cfg():
    c = {"name": "Nest & Nook Finds", "tagline": "Practical home & kitchen finds, picked for real life",
         "email": "", "pinterest_url": "https://www.pinterest.com/nestnookfinds/",
         "owner": "the Nest & Nook Finds team", "country": "India"}
    c.update(jload("site.json", {}))
    return c


def write(path, text):
    full = os.path.join(DOCS, path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


def u(path=""):
    return f"{SITE}/{path}"


def page_name(base, n):
    if base == "index":
        return "index.html" if n == 1 else f"page-{n}.html"
    return f"{base}.html" if n == 1 else f"{base}-{n}.html"


def page_url(base, n):
    name = page_name(base, n)
    return f"{SITE}/" if name == "index.html" else u(name)


def main_img(p):
    return p.get("image") or u(f"img/{p['slug']}.jpg")


def thumb_img(p):
    return p.get("image") or u(f"img/{p['slug']}-thumb.jpg")


def nice_date(s):
    try:
        return dt.date.fromisoformat(s).strftime("%B %d, %Y")
    except Exception:
        return ""


# ---------------- shared assets ----------------
CSS = """
:root{--bg:#fbf7f2;--card:#fff;--text:#2b2623;--muted:#6f6560;--accent:#c96f4a;--accent-d:#a9552f;--sage:#7aa37a;--line:#eadfd3;--radius:16px}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:16px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--text)}
img{max-width:100%;height:auto;display:block}a{color:var(--accent-d)}h1,h2,h3{line-height:1.25;margin:0 0 .5em}
.container{max-width:1120px;margin:auto;padding:0 20px}
.skip{position:absolute;left:-999px}.skip:focus{left:10px;top:10px;background:#fff;padding:8px 12px;z-index:100;border-radius:8px}
.strip{background:#2b2623;color:#f3e9de;font-size:13px;text-align:center;padding:6px 12px}.strip a{color:#f3e9de}
header.site{position:sticky;top:0;z-index:50;background:rgba(251,247,242,.95);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;gap:14px;min-height:64px;position:relative}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:19px;color:var(--text);text-decoration:none}
.brand img{width:38px;height:38px;border-radius:10px}
nav.main{margin-left:auto;display:flex;gap:2px;align-items:center;flex-wrap:wrap}
nav.main a{padding:8px 12px;border-radius:999px;color:var(--text);text-decoration:none;font-weight:600;font-size:15px}
nav.main a:hover,nav.main a[aria-current]{background:#f1e4d8}
.search{display:flex;margin-left:6px}.search input{border:1px solid var(--line);border-radius:999px 0 0 999px;padding:8px 14px;font-size:14px;width:150px;background:#fff}
.search button{border:1px solid var(--accent);background:var(--accent);color:#fff;border-radius:0 999px 999px 0;padding:8px 14px;cursor:pointer;font-weight:700}
.menu-btn{display:none;margin-left:auto;background:#fff;border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-size:20px;cursor:pointer}
@media(max-width:860px){.menu-btn{display:inline-block}nav.main{display:none;position:absolute;top:64px;left:-20px;right:-20px;flex-direction:column;align-items:stretch;background:var(--bg);padding:12px 20px 16px;border-bottom:1px solid var(--line);margin:0}nav.main.open{display:flex}.search{margin:8px 0 0}.search input{flex:1;width:auto}}
.hero{background:linear-gradient(135deg,#f6dcc8,#f9efe3 60%,#e6efe2);padding:56px 0 48px}
.hero h1{font-size:clamp(28px,5vw,46px);max-width:760px}.hero p{max-width:640px;color:var(--muted);font-size:18px;margin:0 0 22px}
.btn{display:inline-block;background:var(--accent);color:#fff!important;text-decoration:none;font-weight:700;padding:14px 26px;border-radius:999px;border:0;cursor:pointer;font-size:16px;text-align:center}
.btn:hover{background:var(--accent-d)}.btn.alt{background:#fff;color:var(--text)!important;border:1px solid var(--line)}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0 0}.chips a{background:#fff;border:1px solid var(--line);border-radius:999px;padding:8px 16px;text-decoration:none;color:var(--text);font-weight:600;font-size:15px}.chips a:hover{border-color:var(--accent)}
main{padding:34px 0 56px}body.home main{padding:0 0 56px}.section-title{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:18px}.section-title p{margin:0;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(80,50,30,.12)}
.thumb{display:block;aspect-ratio:4/5;background:#f1e4d8;overflow:hidden}.thumb img{width:100%;height:100%;object-fit:cover}
.cbody{padding:14px 16px 18px;display:flex;flex-direction:column;gap:6px;flex:1}.cbody h3{font-size:16px;margin:0}.cbody h3 a{color:var(--text);text-decoration:none}
.more{margin-top:auto;font-weight:700;font-size:14px;text-decoration:none}
.tag{display:inline-block;align-self:flex-start;background:#eef4ec;color:#47684a;border-radius:999px;font-size:12px;font-weight:700;padding:3px 10px}
.pager{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:34px 0 0}.pager a,.pager span{min-width:42px;text-align:center;padding:9px 14px;border-radius:10px;border:1px solid var(--line);background:#fff;text-decoration:none;color:var(--text);font-weight:600}
.pager .cur{background:var(--accent);border-color:var(--accent);color:#fff}.pager .gap{border:0;background:none}
.crumbs{font-size:14px;color:var(--muted);margin-bottom:18px}.crumbs a{color:var(--muted)}
.product{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:36px;align-items:start}
@media(max-width:860px){.product{grid-template-columns:1fr}}
.product figure{margin:0;background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}.product figure img{width:100%;max-height:640px;object-fit:cover}
.product figcaption{font-size:12.5px;color:var(--muted);padding:10px 14px}
.info h1{font-size:clamp(24px,4vw,34px)}.meta{color:var(--muted);font-size:14px}.note{font-size:13.5px;color:var(--muted)}
.share{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.share a{font-size:14px;font-weight:600;text-decoration:none;border:1px solid var(--line);background:#fff;color:var(--text);padding:8px 14px;border-radius:999px}
.box{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;margin:18px 0}
.prose{max-width:760px}.prose h2{margin-top:1.6em;font-size:22px}.prose li{margin:.3em 0}
.card-form label{display:block;font-weight:600;margin:14px 0 6px}.card-form input,.card-form select,.card-form textarea{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:12px;font:inherit;background:#fff}
.card-form textarea{min-height:150px}.hp{position:absolute;left:-9999px}

.navbar{padding:.35rem 0}.navbar-brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:19px;color:var(--text)}.navbar-brand img{width:38px;height:38px;border-radius:10px}
.navbar .nav-link{color:var(--text);font-weight:600;border-radius:999px;padding:.5rem .9rem}.navbar .nav-link:hover,.navbar .nav-link.active{background:#f1e4d8;color:var(--text)}
.navbar-toggler{border-color:var(--line)}.dropdown-menu{border:1px solid var(--line);border-radius:14px;box-shadow:0 12px 28px rgba(80,50,30,.15);padding:8px;min-width:220px}
.dropdown-header{font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}.dropdown-item{border-radius:8px;padding:.45rem .8rem;font-weight:500}.dropdown-item.active,.dropdown-item:active{background:var(--accent);color:#fff}
@media(min-width:992px){.navbar .dropdown:hover>.dropdown-menu{display:block;margin-top:0}}
.btn-search{border:0;background:var(--accent);color:#fff;font-weight:700;border-radius:999px;padding:.3rem 1rem}.btn-search:hover{background:var(--accent-d)}
.sl-wrap{margin-top:14px;position:relative;z-index:2}.carousel{border-radius:20px;overflow:hidden;background:#2b2623;box-shadow:0 12px 30px rgba(80,50,30,.18)}
.slide-link{display:block;color:#fff;text-decoration:none}.slide-img{width:100%;height:340px;object-fit:cover}.slide-cap{min-height:340px;padding:2.2rem 3.2rem;display:flex;flex-direction:column;justify-content:center;gap:12px;background:linear-gradient(135deg,#3a302b,#2b2623)}
.slide-cap h3{font-size:clamp(1.3rem,3vw,1.9rem);color:#fff;margin:0}.slide-cap .btn{align-self:flex-start}
@media(max-width:767px){.slide-img{height:230px}.slide-cap{min-height:0;padding:1.2rem 1.2rem 3rem}}
.carousel-indicators{margin-bottom:.6rem}.carousel-control-prev,.carousel-control-next{width:9%}
.f-brand{display:inline-flex;align-items:center;gap:12px;font-weight:800;font-size:20px;color:#fff!important;text-decoration:none;margin-bottom:10px}.f-brand img{width:48px;height:48px;border-radius:12px}
.f-pin{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:50%;background:#e60023;color:#fff!important;margin-top:6px}.f-pin:hover{background:#ad081b}
.sticky-cta{display:none}
@media(max-width:860px){.sticky-cta{display:block;position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.97);border-top:1px solid var(--line);padding:10px 16px;z-index:40}.sticky-cta .btn{display:block}body.has-cta{padding-bottom:76px}}
footer.site{background:#2b2623;color:#d9cdc1;padding:44px 0 26px;font-size:14.5px}footer.site a{color:#f3e9de}footer.site h4{color:#fff;margin:0 0 10px}
.fgrid{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:28px}@media(max-width:860px){.fgrid{grid-template-columns:1fr 1fr}}@media(max-width:520px){.fgrid{grid-template-columns:1fr}}
footer.site ul{list-style:none;margin:0;padding:0}footer.site li{margin:6px 0}.legal{border-top:1px solid #443b35;margin-top:28px;padding-top:16px;font-size:13px;color:#b9ab9d}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #f0a07c;outline-offset:2px}
"""

JS = """
(function(){
var b=document.querySelector('.menu-btn'),n=document.getElementById('nav');
if(b&&n){b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');});}
var dd=document.querySelector('.dd .ddb');if(dd){dd.addEventListener('click',function(){var p=dd.parentNode,o=p.classList.toggle('open');dd.setAttribute('aria-expanded',o?'true':'false');});}
var sl=document.querySelector('.slider');
if(sl){var S=sl.querySelectorAll('.slide'),D=sl.querySelectorAll('.dot'),k=0,t=null;
function go(i){k=(i+S.length)%S.length;S.forEach(function(x,j){x.classList.toggle('on',j===k);});D.forEach(function(x,j){x.classList.toggle('on',j===k);});}
function play(){if(!matchMedia('(prefers-reduced-motion: reduce)').matches){clearInterval(t);t=setInterval(function(){go(k+1);},5000);}}
sl.querySelector('.prev').onclick=function(){go(k-1);};sl.querySelector('.next').onclick=function(){go(k+1);};
D.forEach(function(x,j){x.onclick=function(){go(j);};});sl.addEventListener('mouseenter',function(){clearInterval(t);});sl.addEventListener('mouseleave',play);play();}
var r=document.getElementById('results');
if(r){
  var q=(new URLSearchParams(location.search).get('q')||'').trim();
  var inp=document.getElementById('q');if(inp){inp.value=q;}
  var cnt=document.getElementById('count');
  fetch(r.getAttribute('data-src')).then(function(x){return x.json();}).then(function(list){
    var t=q.toLowerCase().split(/\\s+/).filter(Boolean);
    var m=t.length?list.filter(function(p){var s=(p.t+' '+p.c).toLowerCase();return t.every(function(w){return s.indexOf(w)>-1;});}):list;
    if(cnt){cnt.textContent=m.length+(m.length===1?' result':' results')+(q?' for "'+q+'"':'');}
    m.forEach(function(p){
      var a=document.createElement('article');a.className='card';
      var l=document.createElement('a');l.className='thumb';l.href=p.u;
      var i=document.createElement('img');i.src=p.i;i.alt=p.t;i.loading='lazy';i.width=400;i.height=500;
      i.onerror=function(){i.onerror=null;i.src=r.getAttribute('data-ph');};
      l.appendChild(i);a.appendChild(l);
      var d=document.createElement('div');d.className='cbody';
      var tg=document.createElement('span');tg.className='tag';tg.textContent=p.c;d.appendChild(tg);
      var h=document.createElement('h3');var ha=document.createElement('a');ha.href=p.u;ha.textContent=p.t;h.appendChild(ha);d.appendChild(h);
      a.appendChild(d);r.appendChild(a);
    });
  }).catch(function(){if(cnt){cnt.textContent='Search is unavailable right now.';}});
}
})();
"""

PLACEHOLDER = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500"><rect width="400" height="500" fill="#f1e4d8"/>'
               '<path d="M200 170 110 250h26v90h128v-90h26z" fill="#fff4e6"/><rect x="180" y="280" width="40" height="60" rx="20" fill="#d6805a"/></svg>')


def make_logo(path):
    from PIL import Image, ImageDraw, ImageFilter
    S, bg, cream, roof, sage, door = 1024, (201, 111, 74), (255, 244, 230), (247, 223, 196), (122, 163, 122), (214, 128, 90)
    im = Image.new("RGB", (S, S), bg)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((295, 465, 729, 780), 30, fill=cream)
    d.polygon([(512, 250), (220, 495), (804, 495)], fill=roof)
    d.line([(220, 495), (512, 250), (804, 495)], fill=cream, width=35, joint="curve")
    d.ellipse((472, 360, 552, 440), fill=(255, 206, 140))
    d.rectangle((450, 625, 574, 780), fill=door)
    d.ellipse((450, 563, 574, 687), fill=door)
    d.line([(512, 250), (512, 190)], fill=sage, width=13)
    for cx, cy, ang in ((555, 175, 25), (470, 165, 155)):
        L = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(L).ellipse((35, 75, 165, 125), fill=sage + (255,))
        L = L.rotate(ang, resample=Image.BICUBIC)
        im.paste(L, (cx - 100, cy - 100), L)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.resize((512, 512), Image.LANCZOS).save(path)


# ---------------- layout ----------------
PINPATH = "M12.017 0C5.396 0 .029 5.367.029 11.987c0 5.079 3.158 9.417 7.618 11.162-.105-.949-.199-2.403.041-3.439.219-.937 1.406-5.957 1.406-5.957s-.359-.72-.359-1.781c0-1.663.967-2.911 2.168-2.911 1.024 0 1.518.769 1.518 1.688 0 1.029-.653 2.567-.992 3.992-.285 1.193.6 2.165 1.775 2.165 2.128 0 3.768-2.245 3.768-5.487 0-2.861-2.063-4.869-5.008-4.869-3.41 0-5.409 2.562-5.409 5.199 0 1.033.394 2.143.889 2.741.099.12.112.225.085.345-.09.375-.293 1.199-.334 1.363-.053.225-.172.271-.401.165-1.495-.69-2.433-2.878-2.433-4.646 0-3.776 2.748-7.252 7.92-7.252 4.158 0 7.392 2.967 7.392 6.923 0 4.135-2.607 7.462-6.233 7.462-1.214 0-2.354-.629-2.758-1.379l-.749 2.848c-.271 1.043-1.002 2.35-1.492 3.146C9.57 23.812 10.763 24 12.017 24c6.624 0 11.99-5.367 11.99-11.988C24.007 5.367 18.641.001 12.017.001z"


def layout(c, cats, title, desc, body, canonical, active="", og_img=None, noindex=False, extra_head="", body_class=""):
    full = title if c["name"] in title else f"{title} | {c['name']}"
    og = og_img or u("assets/logo.png")
    other = [x for x in cats if x not in HOME_CATS + DIGITAL_CATS]
    def _dd(label, names):
        its = [x for x in cats if x in names]
        if not its:
            return ""
        return f'<li><h6 class="dropdown-header">{e(label)}</h6></li>' + "".join(
            f'<li><a class="dropdown-item{" active" if active == x else ""}" href="{u("category-" + slugify(x) + ".html")}">{e(x)}</a></li>' for x in its)
    parts = [p for p in (_dd("Home & Kitchen", HOME_CATS), _dd("Digital downloads", DIGITAL_CATS), _dd("More", other)) if p]
    menu = '<li><hr class="dropdown-divider"></li>'.join(parts)
    def _link(href, label, key):
        cur = ' active" aria-current="page' if active == key else ""
        return f'<li class="nav-item"><a class="nav-link{cur}" href="{href}">{label}</a></li>'
    nav_items = (_link(SITE + "/", "Home", "home")
                 + f'<li class="nav-item dropdown"><a class="nav-link dropdown-toggle{" active" if active in cats else ""}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">Categories</a><ul class="dropdown-menu">{menu}</ul></li>'
                 + _link(u("about.html"), "About", "about") + _link(u("contact.html"), "Contact", "contact"))
    search = (f'<form class="d-flex ms-lg-3 mt-2 mt-lg-0" role="search" action="{u("search.html")}" method="get">'
              '<input class="form-control form-control-sm me-2" type="search" name="q" placeholder="Search finds" aria-label="Search">'
              '<button class="btn-search" type="submit">Search</button></form>')
    fcats = "".join(f'<li><a href="{u("category-" + slugify(x) + ".html")}">{e(x)}</a></li>' for x in cats)
    pin_btn = (f'<a class="f-pin" href="{e(c["pinterest_url"])}" target="_blank" rel="noopener" aria-label="{e(c["name"])} on Pinterest" title="Follow us on Pinterest">'
               f'<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><path d="{PINPATH}"/></svg></a>') if c.get("pinterest_url") else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="p:domain_verify" content="{VERIFY}"/>
<title>{e(full)}</title><meta name="description" content="{e(desc[:300])}">
<link rel="canonical" href="{e(canonical)}">{'<meta name="robots" content="noindex,follow">' if noindex else ''}
<meta property="og:site_name" content="{e(c['name'])}"><meta property="og:type" content="website"><meta property="og:title" content="{e(full)}">
<meta property="og:description" content="{e(desc[:200])}"><meta property="og:url" content="{e(canonical)}"><meta property="og:image" content="{e(og)}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#c96f4a">
<link rel="icon" href="{u('assets/logo.png')}"><link rel="apple-touch-icon" href="{u('assets/logo.png')}">
<link rel="stylesheet" href="{BS_CSS}">
<link rel="stylesheet" href="{u('assets/style.css')}">{extra_head}</head>
<body class="{body_class}"><a class="skip" href="#content">Skip to content</a>
<div class="strip">As an Amazon Associate I earn from qualifying purchases. <a href="{u('disclosure.html')}">Details</a></div>
<header class="site"><nav class="navbar navbar-expand-lg" aria-label="Main"><div class="container">
<a class="navbar-brand" href="{SITE}/"><img src="{u('assets/logo.png')}" alt="" width="38" height="38"><span>{e(c['name'])}</span></a>
<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav" aria-controls="nav" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>
<div class="collapse navbar-collapse" id="nav"><ul class="navbar-nav ms-auto align-items-lg-center">{nav_items}</ul>{search}</div></div></nav></header>
<main id="content">{body}</main>
<footer class="site"><div class="container"><div class="fgrid">
<div><a class="f-brand" href="{SITE}/"><img src="{u('assets/logo.png')}" alt="" width="48" height="48"><span>{e(c['name'])}</span></a><p>{e(c['tagline'])}.</p><p>We share products we found while researching popular, well-reviewed home and kitchen items.</p>{pin_btn}</div>
<div><h4>Explore</h4><ul><li><a href="{SITE}/">All finds</a></li>{fcats}<li><a href="{u('search.html')}">Search</a></li></ul></div>
<div><h4>Company</h4><ul><li><a href="{u('about.html')}">About</a></li><li><a href="{u('contact.html')}">Contact</a></li></ul></div>
<div><h4>Legal</h4><ul><li><a href="{u('privacy.html')}">Privacy Policy</a></li><li><a href="{u('disclosure.html')}">Affiliate Disclosure</a></li><li><a href="{u('terms.html')}">Terms &amp; Disclaimer</a></li></ul></div>
</div><div class="legal">&copy; {dt.date.today().year} {e(c['name'])}. As an Amazon Associate I earn from qualifying purchases. Prices, ratings and availability are set by Amazon and can change at any time. Product names and logos belong to their owners.</div></div></footer>
<script src="{BS_JS}"></script>
<script src="{u('assets/site.js')}" defer></script></body></html>"""


def pager(base, cur, total):
    if total <= 1:
        return ""
    show = sorted({1, total, cur - 1, cur, cur + 1} & set(range(1, total + 1)))
    out, last = [], 0
    if cur > 1:
        out.append(f'<a href="{page_url(base, cur - 1)}" rel="prev">&larr; Prev</a>')
    for n in show:
        if n - last > 1:
            out.append('<span class="gap">&hellip;</span>')
        out.append(f'<span class="cur" aria-current="page">{n}</span>' if n == cur else f'<a href="{page_url(base, n)}">{n}</a>')
        last = n
    if cur < total:
        out.append(f'<a href="{page_url(base, cur + 1)}" rel="next">Next &rarr;</a>')
    return f'<nav class="pager" aria-label="Pagination">{"".join(out)}</nav>'


def card(p):
    url = u(f"p/{p['slug']}.html")
    return (f'<article class="card"><a class="thumb" href="{url}"><img src="{e(thumb_img(p))}" alt="{e(p["title"])}" loading="lazy" '
            f'width="400" height="500" onerror="{ONERR}"></a><div class="cbody"><span class="tag">{e(p["category"])}</span>'
            f'<h3><a href="{url}">{e(p["title"])}</a></h3><a class="more" href="{url}">View details &rarr;</a></div></article>')


def slider(items):
    if not items:
        return ""
    ind = "".join(f'<button type="button" data-bs-target="#latest" data-bs-slide-to="{i}"{" class=active aria-current=true" if i == 0 else ""} aria-label="Slide {i + 1}"></button>' for i in range(len(items)))
    its = "".join(f'''<div class="carousel-item{" active" if i == 0 else ""}" data-bs-interval="5000"><a class="slide-link" href="{u("p/" + p["slug"] + ".html")}">
<div class="row g-0"><div class="col-md-5"><img class="slide-img" src="{e(thumb_img(p))}" alt="{e(p["title"])}" width="400" height="500" onerror="{ONERR}"></div>
<div class="col-md-7 slide-cap"><span class="tag">{e(p["category"])}</span><h3>{e(p["title"])}</h3><span class="btn">View this find &rarr;</span></div></div></a></div>''' for i, p in enumerate(items))
    return (f'<section class="container sl-wrap" aria-label="Latest finds"><div id="latest" class="carousel slide" data-bs-ride="carousel" data-bs-pause="hover">'
            f'<div class="carousel-indicators">{ind}</div><div class="carousel-inner">{its}</div>'
            '<button class="carousel-control-prev" type="button" data-bs-target="#latest" data-bs-slide="prev"><span class="carousel-control-prev-icon" aria-hidden="true"></span><span class="visually-hidden">Previous</span></button>'
            '<button class="carousel-control-next" type="button" data-bs-target="#latest" data-bs-slide="next"><span class="carousel-control-next-icon" aria-hidden="true"></span><span class="visually-hidden">Next</span></button></div></section>')


def listing(c, cats, base, items, heading, intro, active, hero=False, crumb=""):
    total = max(1, math.ceil(len(items) / PER_PAGE))
    for n in range(1, total + 1):
        chunk = items[(n - 1) * PER_PAGE:n * PER_PAGE]
        grid = "".join(card(p) for p in chunk) or '<p>New finds are coming soon. Please check back shortly.</p>'
        head = ""
        if hero and n == 1:
            chips = "".join(f'<a href="{u("category-" + slugify(x) + ".html")}">{e(x)}</a>' for x in cats)
            head = (f'<section class="hero"><div class="container"><h1>{e(c["tagline"])}</h1>'
                    f'<p>Simple, honest picks for your kitchen, storage and home. No fluff, just things people actually buy and use.</p>'
                    f'<a class="btn" href="#finds">Browse the latest finds</a><div class="chips">{chips}</div></div></section>'
                    + slider(items[:5]))
        title_h = heading if n == 1 else f"{heading} (page {n})"
        body = (head + f'<div class="container" id="finds">{crumb}<div class="section-title"><h2>{e(title_h)}</h2><p>{e(intro)}</p></div>'
                f'<div class="grid">{grid}</div>{pager(base, n, total)}</div>')
        links = ""
        if n > 1:
            links += f'<link rel="prev" href="{page_url(base, n - 1)}">'
        if n < total:
            links += f'<link rel="next" href="{page_url(base, n + 1)}">'
        t = c["name"] + " | " + c["tagline"] if (base == "index" and n == 1) else (heading + (f" - page {n}" if n > 1 else ""))
        write(page_name(base, n), layout(c, cats, t, intro or c["tagline"], body, page_url(base, n), active=active, extra_head=links, body_class="home" if (base == "index" and n == 1) else ""))
    return total


def product_page(c, cats, p, catalog):
    url = u(f"p/{p['slug']}.html")
    related = [x for x in catalog if x["pid"] != p["pid"] and x["category"] == p["category"]][:4]
    if len(related) < 4:
        related += [x for x in catalog if x["pid"] != p["pid"] and x not in related][:4 - len(related)]
    own = p.get("store") == "own"
    cta = "Get the printable" if own else "Check price on Amazon"
    rel = "noopener" if own else "sponsored nofollow noopener"
    ai = not p.get("image")
    cap = ('<figcaption>Illustrative AI-generated image, not the actual product. Please see the Amazon page for real photos and details.</figcaption>'
           if ai else "")
    share_t = e(p["title"])
    extras = "".join(f'<p><a class="btn alt" rel="noopener" target="_blank" href="{e(x["url"])}">Also on {e(x["label"])}</a></p>'
                     for x in (p.get("extra") or []) if str(x.get("url", "")).startswith("http")) if own else ""
    amz_note = (f'<p class="note">As an Amazon Associate I earn from qualifying purchases. Price, ratings and delivery details are shown on Amazon and may change. '
                f'<a href="{u("disclosure.html")}">Affiliate disclosure</a>.</p>')
    amz_box = "<li>Check the size, colour and what is included on the Amazon page.</li><li>Read recent customer reviews, especially the critical ones.</li><li>Confirm that the item ships to your country.</li>"
    own_note = '<p class="note">Instant digital download from our shop. No physical item is shipped. For personal use only.</p>'
    own_box = "<li>You receive a ZIP file with printable PDFs right after purchase.</li><li>US Letter and A4 sizes, three colour themes.</li><li>Print as many copies as you like for yourself.</li>"
    body = f"""<div class="container">
<nav class="crumbs" aria-label="Breadcrumb"><a href="{SITE}/">Home</a> &rsaquo; <a href="{u('category-' + slugify(p['category']) + '.html')}">{e(p['category'])}</a> &rsaquo; {e(p['title'])}</nav>
<article class="product"><figure><img src="{e(main_img(p))}" alt="{share_t}" width="800" height="1000" onerror="{ONERR}">{cap}</figure>
<div class="info"><span class="tag">{e(p['category'])}</span><h1>{share_t}</h1>
<p class="meta">Added {e(nice_date(p.get('created', '')))}</p><p>{e(p['page_text'])}</p>
<p><a class="btn" rel="{rel}" target="_blank" href="{e(p['link'])}">{cta}</a></p>
{extras}
{own_note if own else amz_note}
<div class="box"><strong>{"Good to know" if own else "Before you buy"}</strong><ul>{own_box if own else amz_box}</ul></div>
<div class="share"><a href="https://www.pinterest.com/pin/create/button/?url={e(url)}&amp;media={e(main_img(p))}&amp;description={share_t}" target="_blank" rel="noopener">Save on Pinterest</a>
<a href="https://wa.me/?text={share_t}%20{e(url)}" target="_blank" rel="noopener">Share on WhatsApp</a>
<a href="{u('contact.html')}">Report an issue</a></div></div></article>
<section style="margin-top:44px"><div class="section-title"><h2>You might also like</h2></div><div class="grid">{''.join(card(x) for x in related)}</div></section></div>
<div class="sticky-cta"><a class="btn" rel="{rel}" target="_blank" href="{e(p['link'])}">{cta}</a></div>"""
    write(f"p/{p['slug']}.html", layout(c, cats, p["title"], p["page_text"], body, url, active=p["category"], og_img=main_img(p), body_class="has-cta"))


# ---------------- static pages ----------------
def static_pages(c, cats):
    name, owner, email = e(c["name"]), e(c["owner"]), c.get("email", "")
    L = lambda t, d, b, path, **k: write(path, layout(c, cats, t, d, f'<div class="container"><div class="prose">{b}</div></div>', u(path), **k))
    L("About us", f"About {c['name']}: who we are and how we choose products.", f"""<h1>About {name}</h1>
<p>{name} is a small, independent site that shares practical home and kitchen finds: organizers, kitchen helpers, cozy lighting and festive decor.</p>
<h2>How we pick products</h2><ul><li>We look at what people buy a lot, what has strong ratings and many reviews, and what is useful in real homes.</li><li>We focus on everyday prices, not luxury items.</li><li>We do not test every item ourselves, and we never claim to. Please read reviews on the product page before you buy.</li><li>Nobody pays us to feature a product. Our picks are our own.</li></ul>
<h2>How the site makes money</h2><p>Many links on this site are Amazon affiliate links. If you buy through them, we may earn a small commission at no extra cost to you. This is what keeps the site running. Read our <a href="{u('disclosure.html')}">affiliate disclosure</a>.</p>
<h2>Our images</h2><p>Some pictures on this site are AI-generated illustrations of the kind of product we feature. When that is the case, it is stated on the page. The real product photos are always on Amazon.</p>
<h2>Get in touch</h2><p>Questions, corrections or ideas? Please use the <a href="{u('contact.html')}">contact page</a>.</p>""", "about.html", active="about")
    if email:
        form = (f'<form class="card-form" action="https://formsubmit.co/{e(email)}" method="POST">'
                f'<input type="hidden" name="_subject" value="New message from {name}"><input type="hidden" name="_next" value="{u("thanks.html")}">'
                '<input type="hidden" name="_template" value="table"><input class="hp" type="text" name="_honey" tabindex="-1" autocomplete="off">'
                '<label for="n">Your name</label><input id="n" name="name" required maxlength="80">'
                '<label for="m">Your email</label><input id="m" type="email" name="email" required maxlength="120">'
                '<label for="t">Topic</label><select id="t" name="topic"><option>Question</option><option>Report a problem with a product or link</option><option>Correction</option><option>Business or partnership</option><option>Other</option></select>'
                '<label for="g">Message</label><textarea id="g" name="message" required maxlength="3000"></textarea>'
                '<p class="note">We use your details only to reply to you. See our <a href="' + u("privacy.html") + '">Privacy Policy</a>.</p>'
                '<button class="btn" type="submit">Send message</button></form>')
        alt = f'<p>You can also write to us directly at <a href="mailto:{e(email)}">{e(email)}</a>.</p>'
    else:
        form, alt = "<p><strong>The contact form is being set up.</strong> Please check back soon.</p>", ""
    L("Contact us", f"Contact {c['name']}: questions, corrections and product issues.", f"""<h1>Contact us</h1>
<p>Found a broken link, an out-of-stock item or a mistake? Or just have a question? Send us a message and we will reply as soon as we can, usually within a few business days.</p>{form}{alt}
<p class="note">Please note: we do not sell products ourselves. For orders, delivery or returns, contact Amazon customer service.</p>""", "contact.html", active="contact")
    L("Thank you", "Message sent.", "<h1>Thank you!</h1><p>Your message has been sent. We will get back to you soon.</p>"
      f'<p><a class="btn" href="{SITE}/">Back to the finds</a></p>', "thanks.html", noindex=True)
    L("Privacy Policy", f"Privacy Policy of {c['name']}.", f"""<h1>Privacy Policy</h1><p>Last updated: {POLICY_DATE}</p>
<p>{name} (&ldquo;we&rdquo;, &ldquo;us&rdquo;) respects your privacy. This policy explains what information is handled when you use this website.</p>
<h2>Information we collect</h2><ul><li><strong>Contact form:</strong> if you write to us, we receive your name, email address and message. We use them only to reply to you. The form is processed by a third-party form service (FormSubmit), which forwards the message to our inbox.</li><li><strong>Search:</strong> the site search runs in your browser. We do not store what you search for.</li><li><strong>Hosting logs:</strong> our host (GitHub Pages) may record technical data such as IP address and browser type for security and operations.</li></ul>
<p>We do not require accounts, we do not sell personal data, and we do not run advertising or analytics trackers on this site.</p>
<h2>Cookies and third parties</h2><p>This site does not set its own cookies. When you click an affiliate link, Amazon may set cookies on its own website so that a purchase can be credited to us. Pinterest, WhatsApp and Amazon have their own privacy policies, and we are not responsible for their practices.</p>
<h2>Pinterest data</h2><p>We use the Pinterest API only with our own Pinterest business account, the account that owns this website. Our tool creates pins on that account and reads basic statistics (impressions, clicks and saves) about our own pins. We do not collect, store, sell or share data about other Pinterest users. Our Pinterest access tokens are kept as encrypted secrets and are used only for this purpose. Pinterest access can be revoked at any time in the Pinterest account settings.</p>
<h2>Affiliate links</h2><p>As an Amazon Associate I earn from qualifying purchases. See our <a href="{u('disclosure.html')}">Affiliate Disclosure</a>.</p>
<h2>Children</h2><p>This site is not directed at children under 13, and we do not knowingly collect their data.</p>
<h2>Your rights</h2><p>Depending on where you live, you may have the right to ask what data we hold about you, to correct it or to have it deleted. Contact us through the <a href="{u('contact.html')}">contact page</a> and we will respond.</p>
<h2>Changes</h2><p>We may update this policy from time to time. The date above shows the latest version.</p>""", "privacy.html")
    L("Affiliate Disclosure", f"Affiliate disclosure of {c['name']}.", f"""<h1>Affiliate Disclosure</h1>
<p><strong>As an Amazon Associate I earn from qualifying purchases.</strong></p>
<p>{name} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com and affiliated sites.</p>
<ul><li>Links to Amazon on this site and in our Pinterest pins are affiliate links. If you click one and buy something, we may earn a commission. It does not change the price you pay.</li><li>Affiliate commissions do not decide which products we feature. See <a href="{u('about.html')}">how we pick products</a>.</li><li>Prices, availability and reviews are controlled by Amazon and can change at any time. Always check the Amazon page before buying.</li><li>Some images are AI-generated illustrations, and this is stated where it applies.</li></ul>
<p>Questions? Please <a href="{u('contact.html')}">contact us</a>.</p>""", "disclosure.html")
    L("Terms & Disclaimer", f"Terms of use and disclaimer of {c['name']}.", f"""<h1>Terms of Use &amp; Disclaimer</h1><p>Last updated: {POLICY_DATE}</p>
<h2>General information only</h2><p>The content on this site is for general information and inspiration. We try to keep it accurate, but we cannot guarantee that product details, prices, ratings or availability are complete or current. They are set by Amazon and can change without notice.</p>
<h2>No sales by us</h2><p>We do not sell, ship or support any products. Purchases are made on Amazon and are covered by Amazon&rsquo;s own terms, returns and customer service.</p>
<h2>Product choice is yours</h2><p>Please read the full product page and customer reviews and decide for yourself. We are not responsible for any loss or dissatisfaction resulting from a purchase.</p>
<h2>Third-party links and trademarks</h2><p>We link to third-party websites that we do not control. Product names, brands and logos are the property of their owners and are used only to identify products.</p>
<h2>Our content</h2><p>You may link to this site. Please do not copy our texts or images without permission.</p>
<h2>Limitation of liability</h2><p>To the extent permitted by law, we are not liable for any damages arising from the use of this site or reliance on its content.</p>
<h2>Contact</h2><p>See our <a href="{u('contact.html')}">contact page</a>.</p>""", "terms.html")
    write("404.html", layout(c, cats, "Page not found", "This page could not be found.",
          f'<div class="container"><div class="prose"><h1>Page not found</h1><p>Sorry, we could not find that page. It may have moved.</p>'
          f'<p><a class="btn" href="{SITE}/">Go to the home page</a> <a class="btn alt" href="{u("search.html")}">Search finds</a></p></div></div>',
          u("404.html"), noindex=True))
    write("search.html", layout(c, cats, "Search", "Search all finds.",
          f'<div class="container"><div class="section-title"><h2>Search</h2><p id="count" aria-live="polite"></p></div>'
          f'<form class="search" role="search" action="{u("search.html")}" method="get" style="margin-bottom:20px"><input id="q" type="search" name="q" placeholder="What are you looking for?" style="width:100%;max-width:420px"><button type="submit">Search</button></form>'
          f'<div class="grid" id="results" data-src="{u("products.json")}" data-ph="{PH}"></div><noscript><p>Please enable JavaScript to use search.</p></noscript></div>',
          u("search.html"), noindex=True))


# ---------------- build ----------------
def build(catalog):
    use_local_bootstrap()
    c = cfg()
    items = sorted(catalog, key=lambda p: (p.get("created", ""), p["pid"]), reverse=True)
    for p in items:
        p.setdefault("category", "Home Finds")
        p.setdefault("image", "")
    present = {p["category"] for p in items}
    cats = [x for x in CAT_ORDER if x in present] + sorted(present - set(CAT_ORDER))
    write("assets/style.css", CSS.strip() + "\n")
    write("assets/site.js", JS.strip() + "\n")
    write("assets/placeholder.svg", PLACEHOLDER)
    make_logo(os.path.join(DOCS, "assets", "logo.png"))
    pages = [("index", "", [SITE + "/"])]
    n_home = listing(c, cats, "index", items, "Latest finds", "Newest products first. Tap any card for details.", "home", hero=True)
    urls = [page_url("index", n) for n in range(1, n_home + 1)]
    for cat in cats:
        sub = [p for p in items if p["category"] == cat]
        n = listing(c, cats, f"category-{slugify(cat)}", sub, cat, CAT_TEXT.get(cat, f"All {cat} finds."), cat,
                    crumb=f'<nav class="crumbs"><a href="{SITE}/">Home</a> &rsaquo; {e(cat)}</nav>')
        urls += [page_url(f"category-{slugify(cat)}", i) for i in range(1, n + 1)]
    for p in items:
        product_page(c, cats, p, items)
        urls.append(u(f"p/{p['slug']}.html"))
    static_pages(c, cats)
    urls += [u(x) for x in ("about.html", "contact.html", "privacy.html", "disclosure.html", "terms.html")]
    today = dt.date.today().isoformat()
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{e(x)}</loc><lastmod>{today}</lastmod></url>\n" for x in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {u('sitemap.xml')}\n")
    write("products.json", json.dumps([{"t": p["title"], "c": p["category"], "u": u(f"p/{p['slug']}.html"), "i": thumb_img(p)} for p in items],
                                      ensure_ascii=False))
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    print(f"Site built: {len(items)} products, {n_home} home page(s), {len(cats)} categories.")
