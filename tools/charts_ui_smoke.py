"""Stage04 browser acceptance on a separate test server; bootstrap fixture via API."""

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8895"
SHOTS = ROOT / "design" / "reviews" / "050-charts"
SHOTS.mkdir(parents=True, exist_ok=True)
results, errors, external = [], [], []


def ok(name, condition):
    results.append((name, bool(condition)))
    print(("PASS " if condition else "FAIL ") + name, flush=True)


with httpx.Client(base_url=B) as api:
    project = api.post("/api/projects", json={"name": "Перевірка графіків Melbourne"}).json()[
        "data"
    ]["id"]
    uploaded = api.post(
        f"/api/projects/{project}/datasets",
        files={"file": ("melb.csv", (ROOT / "samples" / "melb_data.csv").read_bytes(), "text/csv")},
    )
    uploaded.raise_for_status()
    dataset = uploaded.json()["data"]["id"]
    api.post("/api/configuration/charts/reset").raise_for_status()

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    context = browser.new_context(viewport={"width": 1400, "height": 1000})

    def local_only(route):
        if urlparse(route.request.url).hostname == urlparse(B).hostname:
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort()

    context.route("**/*", local_only)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: message.type == "error" and errors.append(message.text))
    page.goto(B + "/settings/charts")
    page.locator(".heatmap-cell").first.wait_for()
    ok("storytelling default six lower cells", page.locator(".heatmap-cell").count() == 6)
    page.get_by_label("Тема", exact=True).click()
    page.get_by_role("option", name="Академічна", exact=True).click()
    page.wait_for_timeout(400)
    ok("academic preview nine cells", page.locator(".heatmap-cell").count() == 9)
    with httpx.Client(base_url=B) as api:
        ok(
            "preview not saved",
            api.get("/api/configuration/charts").json()["data"]["theme"] == "storytelling",
        )
    page.get_by_role("button", name="Зберегти налаштування", exact=True).click()
    page.wait_for_timeout(800)
    page.reload()
    page.locator(".heatmap-cell").first.wait_for()
    ok("academic survives reload", page.locator(".heatmap-cell").count() == 9)
    page.get_by_label("Додатні значення · HEX", exact=True).fill("#264653")
    page.get_by_role("checkbox", name="Числа в клітинках", exact=True).click()
    page.wait_for_timeout(400)
    ok("numbers can be hidden undefined remains", page.locator(".heatmap-cell text").count() == 2)
    page.get_by_role("button", name="Зберегти налаштування", exact=True).click()
    page.wait_for_timeout(800)
    with httpx.Client(base_url=B) as api:
        saved = api.get("/api/configuration/charts").json()["data"]
        ok(
            "custom persisted",
            saved["theme"] == "custom" and saved["custom"]["positive"] == "#264653",
        )
    page.get_by_label("Текст · HEX", exact=True).fill("#FFFFFF")
    page.get_by_text("Низький контраст тексту й фону:", exact=False).wait_for()
    ok("contrast warning in preview", True)
    page.get_by_label("Додатні значення · HEX", exact=True).fill("invalid")
    page.get_by_role("button", name="Зберегти налаштування", exact=True).click()
    page.get_by_text("Перевірте кольори, розміри та поріг перед збереженням.").wait_for()
    ok("invalid configuration rejected", True)
    page.get_by_role("button", name="Відновити початкові налаштування", exact=True).click()
    page.wait_for_timeout(800)
    page.screenshot(path=str(SHOTS / "settings.png"), full_page=True)
    ok(
        "reset restores defaults",
        page.get_by_role("checkbox", name="Числа в клітинках", exact=True).is_checked(),
    )
    page.goto(B + f"/?project={project}&dataset={dataset}&view=charts")
    selector = page.get_by_label("Числові поля · оберіть 2–12", exact=True)
    selector.click()
    page.get_by_role("option", name="Price", exact=True).click()

    page.get_by_role("option", name="Rooms", exact=True).click()
    selector.press("Escape")
    page.get_by_role("button", name="Побудувати", exact=True).click()
    page.locator(".heatmap-cell").first.wait_for()
    ok("heatmap three cells", page.locator(".heatmap-cell").count() == 3)
    pair = page.locator(".heatmap-cell").nth(1)
    pair.focus()
    page.wait_for_timeout(100)
    detail = page.locator(".heatmap-detail").inner_text()
    ok(
        "keyboard pair shows r n exclusions",
        "0.50" in detail and "13580" in detail and "виключено пар: 0" in detail,
    )
    page.get_by_text("Як розраховано · формули", exact=True).click()
    page.wait_for_function("document.querySelectorAll('.math-formula mjx-container').length === 4")
    ok(
        "four local MathJax formulas rendered",
        page.locator(".math-formula[data-rendered=ok]").count() == 4,
    )
    ok(
        "Pearson formula keeps TeX sums",
        "sum" in page.locator(".math-formula").first.get_attribute("data-formula"),
    )
    page.evaluate("scrollTo(0,0)")
    page.wait_for_timeout(200)
    page.screenshot(path=str(SHOTS / "heatmap.png"), full_page=True)
    page.get_by_text("Тимчасове оформлення графіка", exact=True).click()
    page.get_by_role("checkbox", name="Акцент за порогом |r|", exact=True).click()
    page.get_by_label("Поріг акценту |r|", exact=True).fill("0.9")
    page.get_by_role("checkbox", name="Числа в клітинках", exact=True).click()
    page.get_by_role("button", name="Побудувати", exact=True).click()
    page.get_by_text("Акцент: |r| ≥ 0.9.", exact=False).wait_for()
    ok(
        "weak pair retained accessible",
        "0.50" in page.locator(".heatmap-cell").nth(1).get_attribute("aria-label"),
    )
    with httpx.Client(base_url=B) as api:
        ok(
            "temporary changes not global",
            api.get("/api/configuration/charts").json()["data"]["theme"] == "storytelling",
        )
        events = api.get(f"/api/projects/{project}/events").json()["data"]
        ok(
            "one chart event per build no statistics duplicates",
            sum(e["operation"] == "chart.built" for e in events) == 2
            and not any(e["operation"] == "statistics.calculated" for e in events),
        )
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(500)
    ok(
        "mobile page has no horizontal overflow",
        page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
    )
    ok(
        "mobile chart scrolls internally",
        page.locator(".heatmap-scroll").evaluate("el=>el.scrollWidth>el.clientWidth"),
    )
    page.screenshot(path=str(SHOTS / "mobile.png"), full_page=True)
    ok("no external requests", not external)
    ok("no browser errors", not errors)
    browser.close()

(ROOT / "tmp" / "charts050-results.json").write_text(
    json.dumps(
        {"results": results, "errors": errors, "external": external}, ensure_ascii=False, indent=2
    ),
    encoding="utf-8",
)
raise SystemExit(0 if all(condition for _, condition in results) else 1)
