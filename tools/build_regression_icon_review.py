"""Build local SVG/HTML comparisons from icon proposals; does not change the UI."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_story.icons import REGRESSION_PROPOSALS  # noqa: E402

OUT = ROOT / "design" / "reviews" / "032-regression-icon"
OUT.mkdir(parents=True, exist_ok=True)
LABELS = ["Пряма й точки", "Хмара точок", "Крива регресії", "Пряма й похибки"]
parts = []
for (number, paths), label in zip(REGRESSION_PROPOSALS.items(), LABELS, strict=True):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round">' + paths + "</svg>"
    )
    (OUT / f"regression-{number}.svg").write_text(
        svg.replace("currentColor", "#174690"), encoding="utf-8"
    )
    parts.append(
        f'<section><h2>{number}. {label}</h2><div class="large">{svg}</div>'
        f'<div class="sample">{svg}<span>Регресія</span></div></section>'
    )
html = (
    """<!doctype html><html lang="uk"><meta charset="utf-8"><title>Іконка регресії — варіанти</title>
<style>
@font-face{font-family:Plex;src:url('../../../src/data_story/assets/fonts/plex/ibm-plex-sans-regular.woff2')}
body{margin:0;padding:32px;font-family:Plex,sans-serif;color:#262626;background:white}
h1{font-size:24px;margin:0 0 12px}p{color:#5f5f5f;margin:0 0 28px}
main{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #ebebeb;border-bottom:1px solid #ebebeb}
section{padding:20px 16px;border-right:1px solid #ebebeb}section:last-child{border-right:0}
h2{font-size:16px;font-weight:400;margin:0 0 28px}.large{color:#174690;margin:0 0 28px}
.large svg{width:72px;height:72px}.sample{display:flex;align-items:center;gap:10px;color:#174690;background:#f3f4f6;padding:10px}
.sample svg{width:24px;height:24px;flex:none}
</style><h1>Іконка регресії — 4 варіанти</h1><p>Угорі — збільшено, внизу — у розмірі 24 × 24. Поточну іконку ще не змінено.</p><main>"""
    + "".join(parts)
    + "</main></html>"
)
(OUT / "variants.html").write_text(html, encoding="utf-8")
