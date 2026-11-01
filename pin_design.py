"""Pin designer: turns a plain 1000x1500 photo into a finished, varied Pinterest pin (4 templates).
Pillow only (works on GitHub Actions). Templates: banner, frame, split, badge."""
import os, hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat

W, H = 1000, 1500
FD = ["/usr/share/fonts/truetype/google-fonts", "/usr/share/fonts/truetype/dejavu", "fonts"]
PALETTES = [((201, 111, 74), (107, 51, 32)), ((94, 139, 106), (47, 74, 56)), ((47, 75, 110), (27, 45, 69)), ((176, 124, 46), (92, 62, 20))]


def font(size, w="Bold"):
    for d in FD:
        for n in (f"Poppins-{w}.ttf", "DejaVuSans-Bold.ttf"):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)))
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))


def lines(d, text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            out.append(cur); cur = w
    return out + [cur]


def fit(d, text, maxw, sizes=(96, 84, 74, 64, 56), maxlines=3):
    for s in sizes:
        f = font(s)
        ls = lines(d, text, f, maxw)
        if len(ls) <= maxlines:
            return f, ls
    return f, ls


def shadow_text(img, xy, s, f, fill="white", anchor="ma", blur=6, off=4):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0], xy[1] + off), s, font=f, fill=(0, 0, 0, 150), anchor=anchor)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text(xy, s, font=f, fill=fill, anchor=anchor)


def pill(img, cx, y, s, bg, fg="white", size=30):
    d = ImageDraw.Draw(img)
    f = font(size, "Medium")
    w = d.textlength(s, font=f) + 54
    d.rounded_rectangle((cx - w / 2, y, cx + w / 2, y + size + 26), radius=(size + 26) // 2, fill=bg)
    d.text((cx, y + 12), s, font=f, fill=fg, anchor="ma")


def banner(bg, text, brand, pal):
    img = bg.convert("RGBA")
    g = Image.linear_gradient("L").resize((W, 720))
    over = Image.new("RGBA", (W, 720), (15, 10, 8, 0))
    over.putalpha(g.point(lambda v: int(v * .78)))
    img.alpha_composite(over, (0, H - 720))
    d = ImageDraw.Draw(img)
    f, ls = fit(d, text, 820)
    y = H - 170 - len(ls) * int(f.size * 1.2)
    pill(img, W // 2, y - 78, "TAP TO SEE MORE", pal[0], size=28)
    for ln in ls:
        shadow_text(img, (W // 2, y), ln, f)
        y += int(f.size * 1.2)
    pill(img, 190, 46, brand, (255, 255, 255, 215), fg=pal[1], size=26)
    return img


def frame(bg, text, brand, pal):
    tint = tuple(int(c + (255 - c) * .82) for c in pal[0])
    img = Image.new("RGBA", (W, H), tint + (255,))
    d = ImageDraw.Draw(img)
    for cx, cy, r in ((120, 1400, 160), (900, 150, 120), (940, 1250, 70)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(int(c + (255 - c) * .65) for c in pal[0]))
    f, ls = fit(d, text, 860, maxlines=2)
    y = 70
    for ln in ls:
        d.text((W // 2, y), ln, font=f, fill=pal[1], anchor="ma"); y += int(f.size * 1.2)
    ph_top = max(y + 30, 300)
    ph_h = H - ph_top - 120
    ph = cover(bg.convert("RGB"), 860, ph_h)
    mask = Image.new("L", ph.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), 40, fill=255)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((60, ph_top + 14, 940, ph_top + ph.height + 14), 44, fill=(0, 0, 0, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    d.rounded_rectangle((52, ph_top - 8, 948, ph_top + ph.height + 8), 48, fill="white")
    img.paste(ph, (70, ph_top), mask)
    d.text((W // 2, H - 80), brand, font=font(34, "Medium"), fill=pal[1], anchor="ma")
    return img


def split(bg, text, brand, pal):
    img = Image.new("RGBA", (W, H), pal[1] + (255,))
    top = cover(bg.convert("RGB"), W, 960)
    img.paste(top, (0, 0))
    d = ImageDraw.Draw(img)
    import math
    pts = [(x, 905 + 22 * math.sin(x / 80)) for x in range(0, W + 1, 8)] + [(W, H), (0, H)]
    d.polygon(pts, fill=pal[1])
    f, ls = fit(d, text, 840, maxlines=3)
    y = 980
    for ln in ls:
        d.text((W // 2, y), ln, font=f, fill="white", anchor="ma"); y += int(f.size * 1.18)
    pill(img, W // 2, H - 150, "SAVE FOR LATER", pal[0], size=28)
    d.text((W // 2, H - 70), brand, font=font(30, "Medium"), fill=(235, 225, 215), anchor="ma")
    return img


def badge(bg, text, brand, pal):
    img = bg.convert("RGBA")
    d = ImageDraw.Draw(img)
    f, ls = fit(d, text, 760, maxlines=2)
    h = len(ls) * int(f.size * 1.2) + 64
    rib = Image.new("RGBA", (W, h + 10), (0, 0, 0, 0)); rd = ImageDraw.Draw(rib)
    rd.polygon([(0, 8), (60, 8), (60, h), (0, h), (24, h / 2 + 4)], fill=pal[1])
    rd.polygon([(W, 8), (W - 60, 8), (W - 60, h), (W, h), (W - 24, h / 2 + 4)], fill=pal[1])
    rd.rectangle((40, 0, W - 40, h - 8), fill=pal[0])
    img.alpha_composite(rib, (0, 90))
    y = 90 + 28
    for ln in ls:
        d.text((W // 2, y), ln, font=f, fill="white", anchor="ma"); y += int(f.size * 1.2)
    b = Image.new("RGBA", (300, 300), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
    bd.ellipse((10, 10, 290, 290), fill=pal[1], outline="white", width=8)
    bd.text((150, 112), "NEW", font=font(56), fill="white", anchor="ma"); bd.text((150, 176), "FIND", font=font(56), fill="white", anchor="ma")
    b = b.rotate(8, resample=Image.BICUBIC)
    img.alpha_composite(b, (60, H - 380))
    d.text((W - 60, H - 70), brand, font=font(32, "Medium"), fill="white", anchor="ra")
    return img


TEMPLATES = {"banner": banner, "frame": frame, "split": split, "badge": badge}


def design(bg, text, brand, key="", template=None):
    """bg: PIL image (any size). Returns RGB 1000x1500 pin. Template is chosen from `key` so pins look varied but stable."""
    bg = bg.convert("RGB").resize((W, H)) if bg.size != (W, H) else bg.convert("RGB")
    h = int(hashlib.md5((key or text).encode()).hexdigest(), 16)
    name = template or list(TEMPLATES)[h % len(TEMPLATES)]
    pal = PALETTES[(h // 7) % len(PALETTES)]
    return TEMPLATES[name](bg, text, brand, pal).convert("RGB")
