#!/usr/bin/env python3
"""
Generate the static Tariffs banner shown on the bot's plans screen.

Run once to (re)create ``jarvis/interfaces/assets/plans_banner.png``; the image
is committed so the bot ships it as a static asset and needs no image library
at runtime:

    python scripts/gen_plan_banner.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
OUT = Path(__file__).resolve().parents[1] / "jarvis/interfaces/assets/plans_banner.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgradient(size: tuple[int, int], top, bottom) -> Image.Image:
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        grad.putpixel((0, y), lerp(top, bottom, y / max(1, h - 1)))
    return grad.resize((w, h))


def centered(draw, cx: int, y: int, text: str, fnt, fill):
    x0, _y0, x1, _y1 = draw.textbbox((0, 0), text, font=fnt)
    draw.text((cx - (x1 - x0) / 2, y), text, font=fnt, fill=fill)


def card(img: Image.Image, x: int, y: int, w: int, h: int, accent, *,
        name: str, price: str, feats: list[str], badge: str = ""):
    draw = ImageDraw.Draw(img, "RGBA")
    radius = 28
    # Card body.
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius,
                        fill=(255, 255, 255, 12), outline=accent + (255,), width=3)
    # Accent header strip.
    draw.rounded_rectangle([x, y, x + w, y + 84], radius=radius, fill=accent + (255,))
    draw.rectangle([x, y + 50, x + w, y + 84], fill=accent + (255,))
    cx = x + w // 2
    centered(draw, cx, y + 20, name, font(38, bold=True), (17, 24, 39))
    centered(draw, cx, y + 110, price, font(44, bold=True), (255, 255, 255))
    fy = y + 190
    for feat in feats:
        draw.ellipse([x + 34, fy + 10, x + 46, fy + 22], fill=accent + (255,))
        draw.text((x + 60, fy), feat, font=font(26), fill=(210, 216, 230))
        fy += 52
    if badge:
        bw, bh = 150, 40
        bx = x + w - bw - 16
        draw.rounded_rectangle([bx, y - bh // 2, bx + bw, y + bh // 2],
                            radius=bh // 2, fill=(245, 158, 11, 255))
        centered(draw, bx + bw // 2, y - bh // 2 + 7, badge, font(22, bold=True),
                (17, 24, 39))


def main() -> None:
    img = vgradient((W, H), (20, 24, 44), (8, 10, 20)).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle accent glow behind the title.
    draw.ellipse([W // 2 - 320, -220, W // 2 + 320, 160], fill=(99, 102, 241, 40))

    centered(draw, W // 2, 46, "J.A.R.V.I.S.", font(72, bold=True), (255, 255, 255))
    centered(draw, W // 2, 132, "PLANS", font(30, bold=True), (148, 163, 184))

    cw, ch, gap = 360, 420, 40
    total = cw * 3 + gap * 2
    x0 = (W - total) // 2
    y0 = 210

    card(img, x0, y0, cw, ch, (100, 116, 139),
        name="FREE", price="0 ★",
        feats=["10 / day", "Basic model", "Community"])
    card(img, x0 + (cw + gap), y0 - 20, cw, ch + 20, (245, 158, 11),
        name="PLUS", price="2500 ★",
        feats=["100 / day", "All models", "Images", "Priority"], badge="POPULAR")
    card(img, x0 + 2 * (cw + gap), y0, cw, ch, (139, 92, 246),
        name="PRO", price="8000 ★",
        feats=["Unlimited", "Your API key", "Images", "24/7"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
