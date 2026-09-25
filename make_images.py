"""One-off: builds the social share card (og.png) and favicons into src/assets. Re-run only if the art changes."""
import pathlib
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
ART = HERE / "src" / "img"
OUT = HERE / "src" / "assets"
OUT.mkdir(parents=True, exist_ok=True)
NAVY, NAVY2, ORANGE, ICE, SKY = (10, 18, 36), (18, 31, 56), (249, 158, 26), (238, 244, 255), (63, 193, 255)
HERO_ACCENT = {"Bulwark": (255, 200, 60), "Ember": (255, 130, 40), "Vanguard": (90, 200, 255), "Longshot": (220, 130, 255), "Broker": (255, 205, 80), "Solace": (255, 240, 170)}


def font(size, instance=b"Bold Condensed"):
    f = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", size)
    try:
        f.set_variation_by_name(instance)
    except Exception:
        pass
    return f


def italic_text(text, size, fill, instance=b"Bold Condensed"):
    f = font(size, instance)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + 40, b - t + 20
    layer = Image.new("RGBA", (w + int(h * 0.25), h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((10 - l + int(h * 0.2), 10 - t), text, font=f, fill=fill)
    return layer.transform(layer.size, Image.AFFINE, (1, 0.2, 0, 0, 1, 0), resample=Image.BICUBIC)


def hexagon(d, cx, cy, r, **kw):
    import math
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-90, 270, 60)]
    d.polygon(pts, **kw)


def logo(size):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hexagon(d, S / 2, S / 2, S * 0.48, fill=NAVY + (255,))
    hexagon(d, S / 2, S / 2, S * 0.48, outline=ORANGE + (255,), width=int(S * 0.07))
    k = S / 40
    pts = [(13, 11), (18, 11), (17, 18), (23, 18), (24, 11), (29, 11), (26, 29), (21, 29), (22, 22), (16, 22), (15, 29), (10, 29)]
    d.polygon([(x * k, y * k) for x, y in pts], fill=ICE + (255,))
    return im.resize((size, size), Image.LANCZOS)


# --- og.png 1200x630
W, H = 1200, 630
og = Image.new("RGB", (W, H), NAVY)
g = Image.new("RGB", (1, H))
for y in range(H):
    t = y / H
    g.putpixel((0, y), tuple(int(NAVY2[i] * (1 - t) + NAVY[i] * t) for i in range(3)))
og.paste(g.resize((W, H)))
d = ImageDraw.Draw(og, "RGBA")
for x in range(-H, W, 44):  # faint diagonal grid like the site backdrop
    d.line([(x, H), (x + H * 0.58, 0)], fill=(255, 255, 255, 7), width=1)
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for r in range(420, 0, -6):
    gd.ellipse([W - 150 - r, -120 - r, W - 150 + r, -120 + r], fill=ORANGE + (int(3 * (1 - r / 420) ** 1.5 * 10),))
og.paste(glow, (0, 0), glow)

# hero tiles on the right, parallelograms, staggered
x0, tile_w, tile_h, gap = 610, 170, 250, 12
for i, name in enumerate(HERO_ACCENT):
    col, row = i % 3, i // 3
    x = x0 + col * (tile_w + gap - 30)
    y = 50 + row * (tile_h + 20) + (34 if col == 1 else 0)
    tile = Image.new("RGBA", (tile_w, tile_h), HERO_ACCENT[name] + (255,))
    port = Image.open(ART / f"Hero_{name}.webp").convert("RGBA")
    s = tile_h / port.height
    port = port.resize((int(port.width * s * 1.0), tile_h), Image.LANCZOS)
    tile.alpha_composite(port, ((tile_w - port.width) // 2, 0))
    shade = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for yy in range(tile_h // 2, tile_h):
        sd.line([(0, yy), (tile_w, yy)], fill=(5, 10, 22, int(220 * (yy - tile_h / 2) / (tile_h / 2))))
    tile.alpha_composite(shade)
    label = italic_text(name.upper(), 26, (255, 255, 255))
    tile.alpha_composite(label, ((tile_w - label.width) // 2, tile_h - label.height - 4))
    mask = Image.new("L", (tile_w, tile_h), 0)
    ImageDraw.Draw(mask).polygon([(tile_w * 0.14, 0), (tile_w, 0), (tile_w * 0.86, tile_h), (0, tile_h)], fill=255)
    og.paste(tile, (x, y), mask)

# title block
og.paste(logo(64), (60, 58), logo(64))
eyebrow = italic_text("ROBLOX  ·  HERO SHOOTER × INCREMENTAL", 26, ORANGE, b"Bold SemiCondensed")
og.paste(eyebrow, (140, 70), eyebrow)
t1 = italic_text("HERO", 150, ICE)
t2 = italic_text("INCREMENTAL", 118, ORANGE)
og.paste(t1, (40, 150), t1)
og.paste(t2, (40, 300), t2)
sub = italic_text("CODES  ·  TIER LIST  ·  HEROES  ·  CALCULATORS", 24, (195, 209, 234), b"SemiBold SemiCondensed")
og.paste(sub, (48, 452), sub)
d = ImageDraw.Draw(og, "RGBA")
d.polygon([(64, 530), (330, 530), (318, 562), (52, 562)], fill=ORANGE)
btn = italic_text("THE HERO INCREMENTAL WIKI", 22, (26, 15, 0))
og.paste(btn, (70, 530), btn)
d.rectangle([0, H - 6, W, H], fill=SKY)
d.rectangle([0, H - 6, W // 2, H], fill=ORANGE)
og.save(OUT / "og.png", optimize=True)

logo(96).save(OUT / "favicon-96.png", optimize=True)
fav = Image.new("RGBA", (180, 180), NAVY + (255,))
fav.alpha_composite(logo(150), (15, 15))
fav.convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)
print("ok", [p.name for p in OUT.iterdir()])
