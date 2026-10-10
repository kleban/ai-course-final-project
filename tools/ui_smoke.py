"""End-to-end UI smoke test of every screen through the real browser UI (no API shortcuts).

Needs Playwright with Chromium and a running Data Story with an EMPTY database, e.g.:
    python tools/start.py --no-browser --port 8899 --database tmp/smoke/data.sqlite3
    python tools/ui_smoke.py http://127.0.0.1:8899
Not part of Check.cmd: Playwright is not in requirements.lock.
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899"
SAMPLE = str(Path(__file__).resolve().parents[1] / "samples" / "demo_apartments.csv")
SHOTS = Path(__file__).resolve().parents[1] / "tmp" / "ui-smoke"
SHOTS.mkdir(parents=True, exist_ok=True)
errors, results = [], []
external_requests = []


def ok(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def markdown(page):
    # Read the component's source text; inner_text adds visual paragraph breaks.
    return page.locator(".markdown-editor").evaluate(
        "el => runMethod(el.id.slice(1), 'getMarkdown', [])"
    )


with sync_playwright() as pw:
    b = pw.chromium.launch()
    context = b.new_context(viewport={"width": 1400, "height": 900})

    def local_only(route):
        if urlparse(route.request.url).hostname == urlparse(B).hostname:
            route.continue_()
        else:
            external_requests.append(route.request.url)
            route.abort()

    context.route("**/*", local_only)
    pg = context.new_page()
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(B)
    pg.wait_for_timeout(1500)
    ok("empty overview", pg.get_by_text("Тут з’являться ваші проєкти").count() == 1)
    ok("panel logo", pg.locator("img.brand-logo").count() == 1)
    pg.get_by_text("Створити проєкт").first.click()
    pg.wait_for_timeout(700)
    ok("type default regression", "Регресія" in pg.locator(".type-current").inner_text())
    pg.get_by_text("Зберегти проєкт").click()
    pg.wait_for_timeout(600)
    ok("empty name rejected", pg.get_by_text("Назва: введіть значення.").count() == 1)
    pg.get_by_label("Назва проєкту").fill("Ціни на квартири")
    pg.get_by_label("Мета дослідження (необов’язково)").fill("Що впливає на ціну")
    pg.get_by_text("Зберегти проєкт").click()
    pg.wait_for_timeout(1500)
    ok("project opened", "project=" in pg.url and pg.get_by_text("Ціни на квартири").count() >= 1)
    pg.locator(".uploader input[type=file]").first.set_input_files(SAMPLE)
    pg.wait_for_timeout(3000)
    ok(
        "csv uploaded -> dataset view",
        "dataset=" in pg.url and pg.get_by_text("Перші рядки").count() == 1,
    )
    ok("150 rows", pg.locator(".kpi-value").first.inner_text().strip() == "150")
    dataset_url = pg.url
    pg.get_by_text("Додати опис").click()
    pg.wait_for_timeout(600)
    pg.get_by_label("Текст опису").fill("ціна_тис_грн — ціна продажу, тис. грн")
    pg.get_by_text("Зберегти текст").click()
    pg.wait_for_timeout(1500)
    ok("raw description saved", pg.get_by_text("Сирі описи даних (1)").count() == 1)
    pg.get_by_text("Редагувати метадані").click()
    pg.wait_for_timeout(1500)
    card = pg.locator(".meta-card").nth(6)
    card.get_by_label("Назва для людей").fill("Ціна")
    card.get_by_label("Роль").click()
    pg.wait_for_timeout(300)
    pg.get_by_role("option", name="цільова").click()
    pg.get_by_text("Зберегти й підтвердити").click()
    pg.wait_for_timeout(1500)
    ok(
        "metadata confirmed",
        pg.get_by_text("Підтверджено").count() >= 1 and pg.locator(".role.target").count() == 1,
    )
    pg.goto(B + "/settings")
    pg.wait_for_timeout(1200)
    ok("settings page", pg.get_by_text("Типи проєктів та інструкції").count() == 1)
    editor = pg.get_by_role("textbox", name="Текст інструкції Markdown")
    editor.wait_for()
    original = markdown(pg).strip()
    ok("markdown editor mounted", len(original) > 100)
    ok("icon toolbar", pg.locator(".markdown-tools button > .ico").count() == 9)
    pg.get_by_role("button", name="Жирний", exact=True).hover()
    ok(
        "visible Ukrainian tooltip",
        pg.get_by_role("tooltip").filter(has_text="Ctrl+B").is_visible(),
    )
    pg.screenshot(path=str(SHOTS / "markdown-tooltip.png"))
    editor.hover()
    ok("preview hidden by default", not pg.locator(".toastui-editor-md-preview").is_visible())
    pg.get_by_text("Підказки Markdown", exact=True).click()
    ok("markdown help", pg.get_by_text("Виділіть текст", exact=False).is_visible())
    ok(
        "ukrainian button hint",
        "Ctrl+B" in pg.get_by_role("button", name="Жирний", exact=True).get_attribute("title"),
    )
    pg.get_by_role("button", name="Перегляд", exact=True).click()
    ok("preview toggles", pg.locator(".toastui-editor-md-preview").is_visible())
    pg.screenshot(path=str(SHOTS / "markdown-preview.png"))
    pg.get_by_role("button", name="Перегляд", exact=True).click()
    pg.get_by_text("Підказки Markdown", exact=True).click()
    draft = "## Перевірка Markdown\n\nУкраїнський **текст** і *курсив*.\n\n- Перший пункт\n- Другий пункт\n\n| Поле | Опис |\n| --- | --- |\n| Ціна | грн |\n\n```python\nx = 1\n```"
    editor.fill(draft)
    ok(
        "uniform Markdown source size",
        editor.evaluate("""el => [...el.querySelectorAll('[class*=toastui-editor-md-]')].every(n =>
            getComputedStyle(n).fontSize === '14px')"""),
    )
    ok(
        "Markdown bold italic and colour",
        editor.evaluate("""el => getComputedStyle(el.querySelector('.toastui-editor-md-strong')).fontWeight === '700'
            && getComputedStyle(el.querySelector('.toastui-editor-md-emph')).fontStyle === 'italic'
            && getComputedStyle(el.querySelector('.toastui-editor-md-heading')).color === 'rgb(23, 70, 144)'"""),
    )
    ok(
        "no empty toolbar gap",
        pg.locator(".toastui-editor-defaultUI").evaluate("""el =>
            el.querySelector('.toastui-editor-main').getBoundingClientRect().top - el.getBoundingClientRect().top <= 2"""),
    )
    # Save immediately after input: verifies that the last edit is not lost in transit.
    pg.get_by_text("Зберегти інструкцію", exact=True).click()
    pg.wait_for_timeout(1000)
    ok("markdown save and reload", markdown(pg).strip() == draft)
    pg.reload()
    editor.wait_for()
    ok("markdown survives page reload", markdown(pg).strip() == draft)
    # ProseMirror groups edits within 500 ms; make this a distinct undo operation.
    pg.wait_for_timeout(700)
    pg.get_by_role("button", name="Таблиця", exact=True).click()
    ok("table template inserted", "Пояснення" in editor.inner_text())
    pg.get_by_role("button", name="Скасувати", exact=True).click()
    ok("format undo", markdown(pg).strip() == draft)
    editor.hover()
    pg.screenshot(path=str(SHOTS / "markdown-editor.png"), full_page=True)
    editor.fill("")
    pg.get_by_text("Зберегти інструкцію", exact=True).click()
    pg.wait_for_timeout(500)
    ok("empty markdown rejected", pg.get_by_text("Інструкція: введіть значення.").count() == 1)
    editor.fill("а" * 20001)
    pg.get_by_text("Зберегти інструкцію", exact=True).click()
    pg.wait_for_timeout(500)
    ok("oversized markdown rejected", "20000" in pg.locator(".error-message").last.inner_text())
    pg.get_by_text("Відновити типову", exact=True).click()
    pg.wait_for_timeout(1000)
    ok("default instruction restored", markdown(pg).strip() == original)
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.reload()
    editor.wait_for()
    pg.screenshot(path=str(SHOTS / "markdown-mobile.png"), full_page=True)
    ok("mobile editor fits", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    pg.set_viewport_size({"width": 1400, "height": 900})
    pg.goto(B + "/icons")
    pg.wait_for_timeout(1200)
    ok("icons page", pg.locator(".icon-tile").count() >= 30)
    ok("Markdown icons in gallery", pg.get_by_text("Редактор Markdown", exact=True).count() == 1)
    pg.goto(B)
    pg.wait_for_timeout(1200)
    ok("project listed with type", pg.get_by_text("Регресія").count() >= 1)
    pg.locator(".nav-link.nav-toggle").click()
    pg.wait_for_timeout(700)
    pg.goto(B + "/settings")
    pg.wait_for_timeout(1200)
    ok(
        "collapsed menu remembered",
        "q-drawer--mini" in pg.evaluate("document.querySelector('.q-drawer').className"),
    )
    pg.locator(".nav-link.nav-toggle").click()
    pg.wait_for_timeout(500)
    pg.goto(dataset_url)
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(SHOTS / "final-dataset.png"))
    pg.goto(B)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(SHOTS / "final-home.png"))
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.goto(B)
    pg.wait_for_timeout(1200)
    ok("mobile renders", pg.get_by_text("Ваші дослідження").count() == 1)
    pg.screenshot(path=str(SHOTS / "final-mobile.png"))
    b.close()
ok("no external resource requests", not external_requests)
print("console errors:", errors)
print(f"{sum(r for _, r in results)}/{len(results)} passed")
sys.exit(0 if all(r for _, r in results) and not errors else 1)
