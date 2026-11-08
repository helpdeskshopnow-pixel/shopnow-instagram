#!/usr/bin/env python3
"""Shop-Now.net Instagram product cards (1080x1350), drawn locally with Pillow: free, no AI service."""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
IMG = OUT / "images"
IMG.mkdir(exist_ok=True)
W, H = 1080, 1350
S = 2  # supersampling for the illustration layer
GREEN_DARK = (14, 58, 38)
GREEN_MID = (28, 96, 58)
GREEN_LIGHT = (52, 140, 84)
AMBER = (255, 176, 0)
CREAM = (255, 247, 230)
WHITE = (255, 255, 255)

FD = "/usr/share/fonts/opentype/inter/InterDisplay-{}.otf"
FI = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
SLOGAN = "Shop Now. Deliver Happiness Back Home."
SIG_TEXT = f"Shop-Now.net\n{SLOGAN}\n\U0001F310 https://www.shop-now.net"
HASHTAGS = "#ShopNow #ShopNowNet #DeliverHappiness #OnlineShopping #BackHome"

SHELF_Y = 1040  # items stand on this line


def font(path, size):
    return ImageFont.truetype(path, size)


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


# ---------- drawing helpers (1x coordinates, drawn at S x) ----------
def rr(d, x0, y0, x1, y1, r, fill):
    d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), radius=r * S, fill=fill)


def el(d, x0, y0, x1, y1, fill):
    d.ellipse((x0 * S, y0 * S, x1 * S, y1 * S), fill=fill)


def pg(d, pts, fill):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill)


def label(d, cx, cy, text, size, fill, bold="Bold"):
    f = font(FI.format(bold), int(size * S))
    d.multiline_text((cx * S, cy * S), text, font=f, fill=fill, anchor="mm", align="center", spacing=int(size * 0.2 * S))


def shadow(d, cx, by, w):
    el(d, cx - w * 0.62, by - 9, cx + w * 0.62, by + 11, (0, 0, 0, 70))



def bag(d, cx, by, w, h, body, text, text_col, label_bg):
    shadow(d, cx, by, w)
    x0, x1, top = cx - w / 2, cx + w / 2, by - h
    rr(d, x0, top, x1, by, 20, body)
    rr(d, x0, top, x1, top + 34, 14, shade(body, 0.86))  # folded top band
    for k in range(int(w // 22)):  # stitch dashes
        xx = x0 + 14 + k * 22
        rr(d, xx, top + 40, xx + 11, top + 44, 2, shade(body, 0.7))
    rr(d, x1 - 20, top + 34, x1 - 6, by - 14, 6, shade(body, 0.93))  # soft side shade
    lx0, lx1, ly0, ly1 = cx - w * 0.38, cx + w * 0.38, top + h * 0.34, top + h * 0.74
    rr(d, lx0, ly0, lx1, ly1, 12, label_bg)
    label(d, cx, (ly0 + ly1) / 2, text, min(34, w * 0.18), text_col, "ExtraBold")
    rr(d, lx0 + 12, ly1 - 12, lx1 - 12, ly1 - 8, 2, shade(label_bg, 0.8))


def bottle(d, cx, by, w, h, body, cap, text):
    shadow(d, cx, by, w)
    x0, x1 = cx - w / 2, cx + w / 2
    rr(d, x0, by - h * 0.66, x1, by, w * 0.3, body)
    pg(d, [(x0 + 2, by - h * 0.5), (cx - w * 0.18, by - h * 0.82), (cx + w * 0.18, by - h * 0.82), (x1 - 2, by - h * 0.5)], body)
    rr(d, cx - w * 0.18, by - h * 0.95, cx + w * 0.18, by - h * 0.78, 4, shade(body, 0.92))
    rr(d, cx - w * 0.23, by - h, cx + w * 0.23, by - h * 0.92, 7, cap)
    rr(d, x0 + 10, by - h * 0.6, x0 + 20, by - h * 0.14, 5, shade(body, 1.18))  # highlight
    rr(d, cx - w * 0.36, by - h * 0.46, cx + w * 0.36, by - h * 0.18, 10, CREAM)
    label(d, cx, by - h * 0.32, text, min(34, w * 0.3), GREEN_DARK, "ExtraBold")


def notebook(d, cx, by, w, h, cover):
    shadow(d, cx, by, w)
    x0, x1, top = cx - w / 2, cx + w / 2, by - h
    rr(d, x0 + 6, top + 6, x1 + 6, by, 12, shade(cover, 0.7))  # page block
    rr(d, x0, top, x1, by, 12, cover)
    rr(d, x1 - 28, top, x1 - 18, by, 3, shade(cover, 0.75))  # elastic band
    for k in range(6):  # spiral rings
        xx = x0 + 22 + k * ((w - 44) / 5)
        rr(d, xx - 5, top - 12, xx + 5, top + 18, 5, (240, 240, 240))
    rr(d, cx - w * 0.36, top + h * 0.3, cx + w * 0.3, top + h * 0.7, 8, WHITE)
    for k in range(3):
        rr(d, cx - w * 0.3, top + h * (0.38 + k * 0.1), cx + w * 0.24 - (k == 2) * 28, top + h * (0.38 + k * 0.1) + 4, 2, (200, 205, 205))


def pen(d, x0, y0, x1, y1, color):
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    px, py = -uy, ux
    hw = 9
    ex, ey = x1 - ux * 40, y1 - uy * 40
    pg(d, [(x0 + px * hw, y0 + py * hw), (ex + px * hw, ey + py * hw), (ex - px * hw, ey - py * hw), (x0 - px * hw, y0 - py * hw)], color)
    el(d, x0 - hw, y0 - hw, x0 + hw, y0 + hw, color)
    pg(d, [(ex + px * hw, ey + py * hw), (x1, y1), (ex - px * hw, ey - py * hw)], (235, 225, 205))
    el(d, x1 - 4, y1 - 4, x1 + 4, y1 + 4, (50, 50, 60))
    cx2, cy2 = x0 + ux * 62, y0 + uy * 62
    pg(d, [(x0 + px * (hw + 2), y0 + py * (hw + 2)), (cx2 + px * (hw + 2), cy2 + py * (hw + 2)), (cx2 - px * (hw + 2), cy2 - py * (hw + 2)), (x0 - px * (hw + 2), y0 - py * (hw + 2))], shade(color, 0.72))
    pg(d, [(x0 + ux * 10 + px * (hw + 5), y0 + uy * 10 + py * (hw + 5)), (x0 + ux * 58 + px * (hw + 5), y0 + uy * 58 + py * (hw + 5)), (x0 + ux * 58 + px * (hw + 1), y0 + uy * 58 + py * (hw + 1)), (x0 + ux * 10 + px * (hw + 1), y0 + uy * 10 + py * (hw + 1))], (200, 200, 205))


def pens(d, cx, by, w, h):
    """Three pens leaning in a fan; footprint ~ w x h."""
    shadow(d, cx, by, w * 0.7)
    base_y = by - 6
    for dx, ang, col in [(-w * 0.28, -14, (60, 110, 225)), (0, 0, AMBER), (w * 0.28, 14, (235, 235, 235))]:
        a = math.radians(ang)
        x0, y0 = cx + dx, base_y
        pen(d, x0, y0, x0 + math.sin(a) * h, y0 - math.cos(a) * h, col)

def brand_label(d, cx, ly0, ly1, name, col, brand_col, size):
    lines = name.split("\n")
    f1 = font(FI.format("Bold"), int(size * 0.42 * S))
    d.text((cx * S, (ly0 + 22) * S), "Shop-Now.net", font=f1, fill=brand_col, anchor="mm")
    f2 = font(FI.format("ExtraBold"), int(size * S))
    d.multiline_text((cx * S, ((ly0 + ly1) / 2 + 14) * S), name, font=f2, fill=col, anchor="mm", align="center", spacing=int(size * 0.15 * S))

def nuts(d, cx, y, w, kind):
    cols = {"almond": ((196, 150, 98), (160, 112, 66)), "pistachio": ((150, 190, 90), (225, 214, 170)), "raisin": ((92, 48, 70), (66, 32, 52))}[kind]
    for k in range(5):
        x = cx - w * 0.32 + k * w * 0.16
        yy = y + (k % 2) * 16
        if kind == "raisin":
            el(d, x - 13, yy - 12, x + 13, yy + 12, cols[k % 2])
        else:
            el(d, x - 11, yy - 17, x + 11, yy + 17, cols[0]); el(d, x - 5, yy - 12, x + 5, yy + 12, cols[1])

def hero_bag(d, cx, by, w, h, body, name, tcol, lbg, nut=None):
    bag(d, cx, by, w, h, body, "", tcol, lbg)
    top = by - h; ly0, ly1 = top + h * 0.34, top + h * 0.74
    if nut: nuts(d, cx, top + h * 0.2, w, nut)
    brand_label(d, cx, ly0, ly1, name, GREEN_DARK, GREEN_LIGHT, min(54, w * 0.15))

def hero_bottle(d, cx, by, w, h, body, cap, name):
    bottle(d, cx, by, w, h, body, cap, "")
    ly0, ly1 = by - h * 0.46, by - h * 0.18
    brand_label(d, cx, ly0 - 4, ly1, name, GREEN_DARK, GREEN_LIGHT, min(46, w * 0.2))

def pump(d, cx, by, w, h, body, name):
    shadow(d, cx, by, w)
    x0, x1 = cx - w / 2, cx + w / 2
    rr(d, x0, by - h * 0.72, x1, by, w * 0.18, body)
    rr(d, cx - w * 0.2, by - h * 0.8, cx + w * 0.2, by - h * 0.7, 4, shade(body, 0.85))
    rr(d, cx - w * 0.07, by - h * 0.95, cx + w * 0.07, by - h * 0.8, 4, shade(body, 0.8))
    rr(d, cx - w * 0.07, by - h * 0.98, cx + w * 0.42, by - h * 0.9, 5, shade(body, 0.8))
    rr(d, x0 + 10, by - h * 0.66, x0 + 20, by - h * 0.12, 5, shade(body, 1.18))
    rr(d, cx - w * 0.36, by - h * 0.55, cx + w * 0.36, by - h * 0.15, 10, CREAM)
    brand_label(d, cx, by - h * 0.55, by - h * 0.15, name, GREEN_DARK, GREEN_LIGHT, min(46, w * 0.2))

RICE = (244, 236, 215); FLOUR = (250, 250, 247); SUGAR = (196, 224, 245); SALT = (232, 238, 242)
PRODUCTS = [
 dict(key="rice", name="Rice", cat="PANTRY", draw=lambda d, cx, by, s: hero_bag(d, cx, by, 330*s, 470*s, RICE, "BASMATI\nRICE", GREEN_DARK, WHITE),
      body="Rice is the heart of so many family meals, from everyday dinners to special celebrations. \U0001F35A Take a moment to browse our website and see what's available for your pantry. Simple, comfortable online shopping, wherever you are."),
 dict(key="flour", name="Flour", cat="PANTRY", draw=lambda d, cx, by, s: hero_bag(d, cx, by, 330*s, 460*s, FLOUR, "FLOUR", GREEN_DARK, AMBER),
      body="Fresh bread, warm flatbreads, a weekend bake. \U0001F33E A good kitchen starts with the basics. Visit our website to browse flour and other pantry essentials from the comfort of home."),
 dict(key="sugar", name="Sugar", cat="PANTRY", draw=lambda d, cx, by, s: hero_bag(d, cx, by, 320*s, 440*s, SUGAR, "SUGAR", (30, 80, 130), WHITE),
      body="A cup of tea, a little something sweet, and good company. ☕ Take a look at our website to browse sugar and more everyday essentials, and find what your kitchen needs today."),
 dict(key="salt", name="Salt", cat="PANTRY", draw=lambda d, cx, by, s: hero_bag(d, cx, by, 300*s, 420*s, SALT, "SALT", (60, 80, 100), WHITE),
      body="Every good dish needs just the right pinch. ✨ Explore our website to browse salt and other kitchen staples, and stock up on the little things that make home cooking special."),
 dict(key="olive", s=1.06, name="Olive Oil", cat="PANTRY", draw=lambda d, cx, by, s: hero_bottle(d, cx, by, 230*s, 540*s, (86, 118, 52), (30, 60, 40), "OLIVE\nOIL"),
      body="Drizzled over a salad or warmed in the pan, olive oil is a kitchen favourite. \U0001FAD2 Visit our website to see what's available and add something to your pantry today."),
 dict(key="oil", s=1.06, name="Cooking Oil", cat="PANTRY", draw=lambda d, cx, by, s: hero_bottle(d, cx, by, 230*s, 540*s, (250, 190, 40), (30, 110, 60), "COOKING\nOIL"),
      body="From a quick stir-fry to a Friday feast, good cooking starts with the right oil. \U0001F373 Browse our website to see what's available and find what your kitchen needs."),
 dict(key="almonds", name="Almonds", cat="DRY FRUITS & NUTS", draw=lambda d, cx, by, s: hero_bag(d, cx, by, 320*s, 460*s, (214, 176, 126), "ALMONDS", GREEN_DARK, CREAM, "almond"),
      body="A handful of almonds is a simple pleasure, and a lovely thing to share. \U0001F330 Visit our website to browse nuts and dry fruits for yourself or as a thoughtful gift for someone you love."),
 dict(key="pistachios", name="Pistachios", cat="DRY FRUITS & NUTS", draw=lambda d, cx, by, s: hero_bag(d, cx, by, 320*s, 460*s, (170, 204, 120), "PISTA-\nCHIOS", GREEN_DARK, CREAM, "pistachio"),
      body="Crack, share and enjoy. \U0001F49A Pistachios are made for good company and long conversations. Explore our website for nuts and dry fruits, and find something to share with the people you love."),
 dict(key="raisins", name="Raisins", cat="DRY FRUITS & NUTS", draw=lambda d, cx, by, s: hero_bag(d, cx, by, 320*s, 460*s, (150, 100, 120), "RAISINS", WHITE, CREAM, "raisin"),
      body="Naturally sweet and always handy. \U0001F347 Raisins are a favourite for snacking, baking and sharing. Take a few minutes to browse our website and see what's available."),
 dict(key="soap", s=1.1, name="Hand Soap", cat="HOME CARE", draw=lambda d, cx, by, s: pump(d, cx, by, 250*s, 520*s, (72, 160, 190), "HAND\nSOAP"),
      body="Small everyday essentials make a home feel cared for. \U0001F9FC Visit our website to browse household items and stock up on what your family needs, from the comfort of home."),
 dict(key="notebook", s=1.2, name="Notebooks", cat="STATIONERY", draw=lambda d, cx, by, s: notebook(d, cx, by, 340*s, 450*s, (238, 102, 82)),
      body="A fresh notebook is a fresh start. \U0001F4D3 Whether it's for school, work or your own ideas, take a look at our website to browse stationery and find something that fits you."),
 dict(key="pens", s=1.05, name="Pens", cat="STATIONERY", draw=lambda d, cx, by, s: pens(d, cx, by, 330*s, 470*s),
      body="Good ideas deserve a good pen. ✏️ Browse stationery on our website, from pens and notebooks to everyday school and office essentials, and find what you need today."),
]

def make_card(i, p):
    headline = [f"Today's pick:", p["name"] + "."]
    _m = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    base = Image.new("RGBA", (W, H), GREEN_DARK + (255,))
    deco = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(deco)
    cx0, cy0, r0 = [(940, 230, 330), (120, 250, 320), (980, 330, 340), (860, 200, 300)][i % 4]
    dd.ellipse((cx0 - r0, cy0 - r0, cx0 + r0, cy0 + r0), fill=GREEN_MID + (255,))
    dd.ellipse((540 - 440, 780 - 340, 540 + 440, 780 + 340), fill=GREEN_MID + (210,))
    base = Image.alpha_composite(base, deco)
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pd = ImageDraw.Draw(pl)
    pd.rounded_rectangle((70, SHELF_Y, W - 70, SHELF_Y + 30), radius=12, fill=GREEN_LIGHT + (255,))
    pd.rounded_rectangle((70, SHELF_Y + 22, W - 70, SHELF_Y + 34), radius=8, fill=shade(GREEN_LIGHT, 0.7) + (255,))
    base = Image.alpha_composite(base, pl)
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    p["draw"](ld, W / 2, SHELF_Y, p.get("s", 1.28))
    ill = layer.convert("RGBa").resize((W, H), Image.LANCZOS).convert("RGBA")
    base = Image.alpha_composite(base, ill)
    img = base.convert("RGB"); d = ImageDraw.Draw(img); M = 90
    d.rectangle((0, H - 270, W, H), fill=GREEN_DARK)
    fm = font(FD.format("ExtraBold"), 44)
    d.text((M, 84), "Shop-Now", font=fm, fill=WHITE); d.text((M + d.textlength("Shop-Now", font=fm), 84), ".net", font=fm, fill=AMBER)
    fp = font(FI.format("Bold"), 28); lab = p["cat"]; tw = d.textlength(lab, font=fp)
    d.rounded_rectangle((W - M - tw - 56, 80, W - M, 140), radius=30, fill=AMBER); d.text((W - M - tw - 28, 94), lab, font=fp, fill=GREEN_DARK)
    fh = font(FD.format("Black"), 100); fs = font(FI.format("Medium"), 38); y = 190
    d.text((M, y), headline[0], font=font(FD.format("Black"), 64), fill=CREAM); y += 78
    d.text((M, y), headline[1], font=fh, fill=WHITE); y += 118
    d.rounded_rectangle((M, y, M + 150, y + 14), radius=7, fill=AMBER)
    d.line((M, H - 250, W - M, H - 250), fill=GREEN_LIGHT, width=3)
    size = 46; fsl = font(FI.format("BoldItalic"), size)
    while d.textlength(SLOGAN, font=fsl) > W - 2 * M and size > 30: size -= 1; fsl = font(FI.format("BoldItalic"), size)
    d.text((M, H - 215), SLOGAN, font=fsl, fill=AMBER); d.text((M, H - 140), "www.shop-now.net", font=font(FI.format("SemiBold"), 40), fill=WHITE)
    path = IMG / f"{p['key']}.jpg"; img.save(path, "JPEG", quality=93, optimize=True); return path

def main():
    caps = {}
    for i, p in enumerate(PRODUCTS):
        path = make_card(i, p)
        caps[p["key"]] = {"product": p["name"], "image": path.name, "caption": f"{p['body']}\n\n{SIG_TEXT}\n\n{HASHTAGS}"}
    (OUT / "captions.json").write_text(json.dumps(caps, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    th = [Image.open(IMG / c["image"]).resize((360, 450)) for c in caps.values()]
    sheet = Image.new("RGB", (4 * 380 + 20, 3 * 470 + 20), (235, 235, 235))
    for k, t in enumerate(th): sheet.paste(t, (20 + (k % 4) * 380, 20 + (k // 4) * 470))
    sheet.save(OUT / "contact_sheet.png"); print("ok", len(caps))

if __name__ == "__main__":
    main()
