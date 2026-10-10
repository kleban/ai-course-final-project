"""Data Story logo set: the author's mark (bars → open book) redrawn as vector + Montserrat wordmark."""
import base64
import json
import sys
from pathlib import Path

from mark import BLUE, book_icon_svg, mark_body

INK, INK2 = "#262626", "#5F5F5F"
TAG = "AI-POWERED ANALYTICS &amp; STORYTELLING"
FONT = base64.b64encode(Path("mont-sub.ttf").read_bytes()).decode()
STYLE = (
    "<style>@font-face{font-family:DSLogo;src:url(data:font/ttf;base64,%s)}"
    "text{font-family:DSLogo,Montserrat,Arial,sans-serif}"
    ".d{font-weight:700;fill:%s}.s{font-weight:600;fill:%s}.t{font-weight:500;fill:%s}</style>"
) % (FONT, INK, BLUE, INK2)
W = json.loads(Path("widths.json").read_text()) if Path("widths.json").exists() else {}


def mark(x, y, h, waves=True):
    s = h / 340
    return f'<g transform="translate({x} {y}) scale({s:.5f})">{mark_body(waves=waves)}</g>'


def svg(w, h, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f"{STYLE}{body}</svg>"
    )


def tag(x, y, size, width):
    fit = f' textLength="{width:.1f}" lengthAdjust="spacing"' if width else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" class="t"{fit}>{TAG}</text>'


def horizontal():
    mh = 96
    mw = 720 * mh / 340
    x = mw + 18
    word = W.get("h_word", 0)
    body = mark(0, 0, mh)
    body += f'<text id="w" x="{x:.1f}" y="70" font-size="62"><tspan class="d">DATA</tspan><tspan class="s"> STORY</tspan></text>'
    body += tag(0, 130, 22.4, mw + 18 + word if word else 0)
    width = mw + 18 + (word or 380)
    return svg(round(width + 2), 140, body)


def panel():
    """Side panel (≈208 px): mark left, DATA / STORY in two lines, tagline under the full width."""
    mh = 40
    mw = 720 * mh / 340
    x = mw + 10
    body = mark(0, 2, mh)
    body += f'<text x="{x:.1f}" y="21" font-size="20" class="d">DATA</text>'
    body += f'<text x="{x:.1f}" y="44" font-size="20" class="s">STORY</text>'
    body += tag(0, 64, 7.6, 208)
    return svg(208, 68, body)


def stacked():
    """Panel alternative: mark on top, one-line name, tagline."""
    mh = 64
    body = mark(0, 0, mh)
    body += '<text x="0" y="100" font-size="27.5"><tspan class="d">DATA</tspan><tspan class="s"> STORY</tspan></text>'
    body += tag(0, 120, 7.6, 208)
    return svg(208, 124, body)


def mark_only(waves=True):
    body = f'<g transform="translate(0 {(720 - 340) / 2})">{mark_body(waves=waves)}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 720">{body}</svg>'


out = Path("out")
out.mkdir(exist_ok=True)
files = {
    "logo-horizontal.svg": horizontal(),
    "logo-panel.svg": panel(),
    "logo-panel-stacked.svg": stacked(),
    "logo-mark.svg": mark_only(True),
    "logo-mark-simple.svg": mark_only(False),
    "logo-icon.svg": book_icon_svg(inner="bars"),
    "logo-icon-waves.svg": book_icon_svg(inner="waves"),
}
for name, text in files.items():
    (out / name).write_text(text, encoding="utf-8")
print("ok", list(files))
