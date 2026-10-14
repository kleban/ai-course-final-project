from html import escape as e
from pathlib import Path
from shutil import copyfile
import importlib.util

# History 136: one Python process (uvicorn) split into frontend and backend; no bus — exact links in the
# «module × storage» matrix under the diagram (see notes/architecture-links-135.md).
# Architecture of Data Story as implemented (history 121): concrete blocks with icons, two buses
# (analytic modules → DuckDB; chat and built-in AI → RAG / LLM), numbered flows 1–10.
# Generates deliverables/architecture/{architecture.html, architecture.svg} and docs/ (GitHub Pages,
# main → /docs). The in-app «Про проєкт» page was removed in history 128. Run: python deliverables/architecture/build.py

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ds_icons", ROOT / "src/data_story/icons.py")
_icons = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_icons)
# Own drawings for the diagram (24x24, stroke 1.9, round caps — the style of src/data_story/icons.py).
ICONS = dict(_icons.ICONS) | {
    "user": '<rect x="3" y="3.5" width="18" height="13" rx="1.5"/><circle cx="12" cy="8.5" r="2.2"/>'
            '<path d="M8 15c.4-2 2-3 4-3s3.6 1 4 3M9 20.5h6M12 16.5v4"/>',
    "api": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 8.5h18M9.5 12l-2.5 2.5 2.5 2.5M14.5 12l2.5 2.5-2.5 2.5"/>',
    "sqlite": '<ellipse cx="10" cy="5.5" rx="6.5" ry="2.4"/><path d="M3.5 5.5v12.5c0 1.3 2.9 2.4 6.5 2.4M16.5 5.5v3.5'
              'M3.5 11.8c0 1.3 2.9 2.4 6.5 2.4"/><path d="M21 9.5c-3.5.5-6 3.5-7 10.5M14.6 16.5l3-1"/>',
    "duckdb": '<circle cx="9" cy="7.5" r="3.6"/><path d="M12.4 8.3h4.1"/><circle cx="8.4" cy="6.8" r=".5" fill="black"/>'
              '<path d="M4.5 12.5c-1 4.5 2.5 8 7.5 8s8.5-2.5 8.5-6.5c-2.2 1.2-4.5.6-6.5-1.2"/>',
    "rag": '<path d="M3 5h5.5A2.5 2.5 0 0 1 11 7.5V19a2 2 0 0 0-2-2H3z"/><circle cx="16.5" cy="12.5" r="3.6"/>'
           '<path d="M19.2 15.2l2.3 2.3"/>',
    "vector": '<path d="M3 6h7M3 10h5M3 14h7M3 18h4M11.5 12h3.5M13.5 10l2 2-2 2"/>'
              + "".join(f'<rect x="{x}" y="{y}" width="1.6" height="1.6" fill="black"/>'
                        for x in (18, 20.4) for y in (6, 9.5, 13, 16.5)),
    "bot": '<rect x="4.5" y="8" width="15" height="11.5" rx="3"/><path d="M12 8V4.8M10 16h4M2.5 12.5v3M21.5 12.5v3"/>'
           '<circle cx="12" cy="3.8" r="1.1"/><circle cx="9.3" cy="12.6" r="1.2" fill="black"/><circle cx="14.7" cy="12.6" r="1.2" fill="black"/>',
    "quarto": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M10 12.5l-2 2 2 2M14 12.5l2 2-2 2"/>',
}

W, H = 1600, 1000
parts = []
def box(x, y, w, h, title, lines, cls="b", tcls="bt", lcls="bl", pad=14, icon=None, ic="ic"):
    parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    tx = x + pad
    if icon:
        parts.append(f'<g class="{ic}" transform="translate({x+pad} {y+10}) scale(.875)">{ICONS[icon]}</g>')
        tx += 29
    ty = y + 26
    for t in title.split("\n"):
        parts.append(f'<text class="{tcls}" x="{tx}" y="{ty}">{e(t)}</text>'); ty += 18
    ty += 4
    for t in lines:
        parts.append(f'<text class="{lcls}" x="{x+pad}" y="{ty}">{e(t)}</text>'); ty += 16

def line(d, n=None, bx=0, by=0, ai=False, start=True, end=True):
    m = "o" if ai else ""
    ms = f' marker-start="url(#as{m})"' if start else ""
    me = f' marker-end="url(#ae{m})"' if end else ""
    parts.append(f'<path class="ln{" ai" if ai else ""}" d="{d}"{ms}{me}/>')
    if n:
        parts.append(f'<circle class="bd{" bdo" if ai else ""}" cx="{bx}" cy="{by}" r="13"/><text class="bn" x="{bx}" y="{by+4.5}">{n}</text>')

def bus(d, dots=(), ai=False):
    parts.append(f'<path class="bus2{" ai" if ai else ""}" d="{d}"/>')
    for x, y in dots:
        parts.append(f'<circle class="jn" cx="{x}" cy="{y}" r="3.5"/>')

# zones: everything is local except the right column (internet, OpenAI)
parts.append('<path class="zone" d="M15 15 H1385 V985 H15 Z"/>')
parts.append('<text class="zl" x="30" y="972">Комп’ютер користувача (Windows) · дані, розрахунки, SQL, RAG і звіти — локально</text>')
parts.append('<path class="zone zo" d="M1395 15 H1590 V985 H1395 Z"/>')
parts.append('<text class="zlo" x="1410" y="40">Інтернет · HTTPS</text>')

box(25, 60, 250, 120, "Користувач у браузері", ["Chrome / Edge · Vue + Quasar", "формули MathJax", "усі ресурси локальні"], "b user", icon="user")

# one Python process: frontend and backend are logical parts of the same program
parts.append('<rect class="proc" x="290" y="40" width="1090" height="660"/>')
parts.append('<text class="procl" x="306" y="64">Один процес Python · uvicorn (Start.cmd)</text>')
box(310, 80, 1050, 85, "Фронтенд · NiceGUI-сторінки", ["проєкти, дані, аналіз, модель, висновки, звіт, налаштування; панель AI-помічника — у браузер через WebSocket"], "b core", icon="api")
box(310, 195, 1050, 495, "Бекенд", [], "b grp", "bt")
box(330, 235, 220, 70, "FastAPI · /api", ["HTTP JSON: рядки, файли"], "b core", "btm", "bl", 12, icon="code")
box(600, 235, 740, 70, "Сервіс-оркестратор (ProjectService)", ["перевіряє дані й проєкт, викликає модулі й AI, виконує інструменти чату"], "b core", "btm", "bl", 12, icon="settings")

box(330, 335, 430, 290, "Аналітичні модулі", [], "b grp", "btm")
chips = [(345, 375, "Дані й метадані", "pandas, NumPy", "data"), (550, 375, "Статистика\nй графіки", "SVG, спільна тема", "compare"),
         (345, 455, "Підготовка\nй агрегація", "вибірки, з’єднання", "table"), (550, 455, "Модель", "scikit-learn, SciPy", "regression"),
         (550, 535, "Звіти", "знімок → .qmd", "doc")]
for x, y, t, l, i in chips:
    box(x, y, 195, 72, t, [l], "b mod", "btm", "bl", 12, icon=i)

box(780, 335, 290, 335, "AI — лише явною дією", [], "b grp ai", "btm")
box(795, 447, 260, 62, "Чат-помічник", ["Порадь · Виконай · Поясни"], "b mod modai", "btm", "bl", 12, icon="chat", ic="ic o")
box(795, 519, 260, 62, "Висновки й чернетка звіту", ["тексти з фактів сервісу"], "b mod modai", "btm", "bl", 12, icon="spark", ic="ic o")
box(795, 591, 260, 62, "SQL від LLM", ["1 SELECT, 5 с, 512 МБ"], "b mod", "btm", "bl", 12, icon="code")
box(795, 375, 260, 62, "Клієнт OpenAI", ["повтори, рівні, журнал, вартість"], "b mod modai", "btm", "bl", 12, icon="bot", ic="ic o")

box(1120, 335, 220, 150, "RAG · база знань", ["правила + 106 уривків", "TF-IDF + вектори", "→ 3–5 фрагментів"], "b rag", "btm", "bl", 12, icon="rag")
box(1120, 505, 220, 165, "bge-m3 (ONNX)", ["у цьому ж процесі,", "з Hugging Face під час", "Setup (SHA-256), ~2,3 ГБ,", "текст → 1024 числа"], "b rag", "btm", "bl", 12, icon="vector")

# outside the process: Quarto CLI, files on disk, OpenAI
box(40, 545, 210, 90, "Quarto 1.10", ["окремий процес (CLI)", "офлайн → HTML"], "b rep", "btm", "bl", 12, icon="quarto")
box(310, 740, 1050, 150, "Диск · runtime/ (відкриваються з процесу напряму)", [], "b store grp2", "btm")
box(330, 780, 320, 95, "SQLite (схема v16)", ["проєкти, набори, метадані, запуски,", "налаштування, журнали, правила RAG,", "висновки й звіти"], "b", "btm", "bl", 12, icon="sqlite")
box(670, 780, 320, 95, "Постійна DuckDB", ["таблиці й результати з версіями:", "статистика, дані графіків,", "метрики, прогнози, залишки"], "b", "btm", "bl", 12, icon="duckdb")
box(1010, 780, 330, 95, "Файли", ["CSV-оригінали з SHA-256, .npz,", "HTML і .qmd звітів, книжки,", "вектори, модель bge-m3"], "b", "btm", "bl", 12, icon="folder")
box(1405, 560, 175, 130, "OpenAI", ["Responses API", "gpt-6-luna /", "gpt-6.1-sol", "ключ лише в .env"], "b llm", "btm", "bl", 12, icon="bot", ic="ic o")

line("M275 120 H310", "1", 292, 140)
line("M140 180 V270 H330", "2", 140, 225)
line("M965 165 V235", "3", 990, 182)
line("M550 270 H600", "4", 575, 270)
line("M700 305 V335", "5", 675, 320)
line("M930 305 V335", "6", 955, 320)
line("M745 571 H795", "7", 770, 571)
line("M550 590 H250", "8", 270, 590, start=False)
line("M1055 478 H1120", "9", 1088, 478)
line("M1230 485 V505", "10", 1258, 495)
line("M1055 406 H1095 V320 H1370 V625 H1405", "11", 1232, 320, ai=True, start=False)
line("M450 625 V740", "12", 450, 705)
line("M925 670 V740", "13", 925, 705)
line("M1230 670 V740", "14", 1230, 705)

svg = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" xmlns="http://www.w3.org/2000/svg">
<title id="t">Архітектура Data Story</title>
<desc id="d">Увесь сервіс — один процес Python (uvicorn), логічно поділений на фронтенд (сторінки NiceGUI) і бекенд (FastAPI, сервіс-оркестратор, аналітичні модулі, AI, RAG з bge-m3). Браузер працює з фронтендом через WebSocket і з FastAPI через HTTP. Сервіс викликає аналітичні модулі й AI; чат повертає виклики інструментів, які виконує сервіс. Модулі, AI і RAG самі відкривають SQLite, DuckDB і файли на диску. Звіти передаються в окремий процес Quarto; до OpenAI звертається лише клієнт OpenAI через інтернет. Точні зв’язки — у таблиці «модуль × сховище».</desc>
<defs>
<marker id="ae" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" class="mh"/></marker>
<marker id="as" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10 0 L0 5 L10 10 z" class="mh"/></marker>
<marker id="aeo" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" class="mho"/></marker>
<marker id="aso" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10 0 L0 5 L10 10 z" class="mho"/></marker>
</defs>
{"".join(parts)}
</svg>'''

flows = [
 ("1", "Браузер ⇄ Фронтенд", "дії користувача: клік, форма, питання помічнику", "оновлення сторінки, таблиці, SVG-графіки", "NiceGUI (WebSocket), Vue + Quasar у браузері",
  "NiceGUI дає вебінтерфейс прямо з Python — для MVP не потрібен окремий фронтенд-проєкт. Фронтенд і бекенд — частини однієї програми."),
 ("2", "Браузер ⇄ FastAPI", "запит сторінки рядків таблиці, завантаження CSV, файли звітів", "JSON із рядками, файли", "FastAPI (HTTP /api) у тому ж процесі",
  "Великі таблиці підвантажуються сторінками за HTTP, без передачі всього набору у WebSocket; той самий API використовують тести."),
 ("3", "Фронтенд → Сервіс", "виклик методу сервісу з даними форми", "результат або зрозуміла помилка", "звичайний виклик Python, pydantic-контракти",
  "Одна точка правил: перевірки однакові для сторінок, API та AI."),
 ("4", "FastAPI → Сервіс", "HTTP-запит, перевірений за схемою", "результат або помилка з кодом", "pydantic-моделі запитів",
  "Сторінки й API не мають власної логіки — лише передають дію сервісу."),
 ("5", "Сервіс ⇄ Аналітичні модулі", "перевірені параметри: набір, поля, налаштування підготовки, модель, звіт", "таблиці, SVG, метрики, версія звіту", "Python-класи: pandas, NumPy, scikit-learn, SciPy",
  "Розрахунки — лише в коді сервісу, без AI: результат відтворюваний і перевірений тестами."),
 ("6", "Сервіс ⇄ AI", "задача AI: питання, режим, поточна сторінка, факти; чату — результати інструментів", "відповідь або виклик інструмента: LLM пропонує, сервіс виконує (навчання, SQL, чернетки, графіки)", "Assistant, ConclusionStore, ReportStore.ai_draft",
  "Агентний цикл: модель лише обирає інструмент і параметри, а виконує їх сервіс з усіма перевірками. Зміни — після «Застосувати»."),
 ("7", "Звіти ⇄ AI", "знімок звіту: факти моделі, статистика, затверджені висновки", "чернетка тексту розділів; автор редагує й затверджує", "ReportStore.ai_draft (задача report_draft)",
  "AI формулює текст, але числа бере лише з фактів сервісу."),
 ("8", "Звіти → Quarto", "після затвердження: .qmd, знімок моделі, статистика, SVG", "HTML-звіт, що відкривається без інтернету", "Quarto CLI 1.10 — окремий процес; без OpenAI",
  "Відкритий стандарт відтворюваних звітів: Markdown + формули + графіки → самодостатній HTML."),
 ("9", "AI ⇄ RAG", "питання користувача або факти моделі", "3–5 фрагментів правил і книжок із джерелами", "KnowledgeStore: гібридний пошук TF-IDF + вектори",
  "LLM не знає правил курсу й змісту книжок; RAG підставляє перевірені фрагменти, тож посилання можна перевірити."),
 ("10", "RAG ⇄ bge-m3", "текст питання; уривки книжок під час індексації", "вектор із 1024 чисел", "BAAI/bge-m3, ONNX Runtime у тому ж процесі, CPU",
  "Пошук за змістом, а не лише за словами; багатомовна модель з українською, обрана порівнянням на контрольних питаннях; без неї — TF-IDF."),
 ("11", "Клієнт OpenAI ⇄ OpenAI", "інструкції + факти (JSON) + фрагменти RAG; чату — схема таблиць та інструменти", "текст / JSON або виклик інструмента; usage токенів", "OpenAI Responses API, httpx, HTTPS",
  "Єдиний вихід в інтернет. Модель — для кожної задачі окремо; повтори й запасні рівні; кожен виклик, токени й вартість — у журналі AI."),
 ("12", "Аналітичні модулі ⇄ Диск", "реєстр, метадані, запуски (SQLite); таблиці й результати (DuckDB); CSV, .npz, звіти (файли)", "збережений стан і результати без повторного розрахунку", "sqlite3, duckdb, файли з SHA-256",
  "Кожне сховище — для свого: транзакції службового стану, швидкі агрегації, великі оригінали й матриці."),
 ("13", "AI ⇄ Диск", "журнал AI, висновки, події чату (SQLite); SQL від LLM — у тимчасовій копії таблиць DuckDB", "контекст проєкту, агрегації для висновків, результат SQL", "sqlite3, duckdb (ізольована копія)",
  "Кожен виклик AI зберігається; SQL від LLM не може змінити дані проєкту."),
 ("14", "RAG ⇄ Диск", "кеш векторів", "правила (SQLite), розділи книжок, вектори .npy, файли bge-m3", "sqlite3; runtime/knowledge-*, dependencies/embeddings",
  "Правила редагуються в сервісі; великі книжки й модель — файлами, завантажуються один раз під час Setup."),
]
MATRIX_COLS = ["SQLite", "DuckDB", "Файли", "RAG", "OpenAI", "Quarto"]
# Checked against src/data_story (history 135–136): who opens which storage or service directly.
MATRIX = [
 ("Дані й метадані", "datasets, metadata, dataset_copy", "так", "так", "так", "", "", ""),
 ("Статистика й графіки", "statistics, charts, chart_configuration", "так", "так", "", "", "", ""),
 ("Підготовка й агрегація", "preparation_store, prepared_datasets, combine", "так", "так", "так", "", "", ""),
 ("Модель", "training_store, model_store", "так", "так", "так", "", "", ""),
 ("Звіти", "reports, quarto_runtime", "так", "", "так", "", "через клієнт (чернетка)", "так"),
 ("Чат-помічник", "assistant", "так", "через інструменти", "", "так", "через клієнт", ""),
 ("Висновки", "conclusions", "так", "так", "", "так", "через клієнт", ""),
 ("SQL від LLM", "analytical_queries", "каталог", "тимчасова копія", "", "", "", ""),
 ("Клієнт OpenAI", "openai_client, ai_settings", "журнал, налаштування", "", "", "", "так", ""),
 ("RAG", "knowledge, embeddings", "правила", "", "так", "—", "", ""),
 ("Моніторинг", "monitoring", "перевірка", "перевірка", "перевірка", "перевірка", "", "перевірка"),
]
matrix_rows = "".join(
    f'<tr><td class="who">{e(n)}</td><td class="tech">{e(m)}</td>' + "".join(f"<td>{e(v)}</td>" for v in vals) + "</tr>"
    for n, m, *vals in MATRIX)
rows = "".join(f'<tr><td class="n"><span class="nb{" o" if n=="11" else ""}">{n}</span></td><td class="who">{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td class="tech">{e(d)}</td><td class="why">{e(w)}</td></tr>' for n,a,b,c,d,w in flows)

page = f'''<!doctype html>
<html lang="uk">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Story — про проєкт</title>
<meta name="description" content="Data Story — MVP сервісу аналітики даних для навчання: аналіз, візуалізація, основи моделювання й AI-помічник.">
<style>
@font-face {{ font-family:'IBM Plex Sans'; src:url('../../src/data_story/assets/fonts/plex/ibm-plex-sans-regular.woff2') format('woff2'); font-weight:400; }}
@font-face {{ font-family:'IBM Plex Sans'; src:url('../../src/data_story/assets/fonts/plex/ibm-plex-sans-600.woff2') format('woff2'); font-weight:600; }}
@font-face {{ font-family:'IBM Plex Sans'; src:url('../../src/data_story/assets/fonts/plex/ibm-plex-sans-700.woff2') format('woff2'); font-weight:700; }}
@font-face {{ font-family:'STIX Two Text'; src:url('../../src/data_story/assets/fonts/stix/stix-two-text-600.woff2') format('woff2'); font-weight:600; }}
@font-face {{ font-family:'STIX Two Text'; src:url('../../src/data_story/assets/fonts/stix/stix-two-text-700.woff2') format('woff2'); font-weight:700; }}
/* Layout: motivation, one diagram (slide-ready), the flow table, two worked requests and principles. Single light look by choice (a printed slide), colours set explicitly. */
:root {{
  --paper:#ffffff; --ink:#262626; --ink2:#5f5f5f; --rule:#d5dbe5; --shade:#f3f4f6;
  --primary:#174690; --band:#e1e7f3; --ai:#c76a00; --aiband:#fbefe0; --store:#eef1f5;
  --sans:'IBM Plex Sans', 'Segoe UI', Arial, sans-serif; --serif:'STIX Two Text', Georgia, 'Times New Roman', serif;
  color-scheme: light;
}}
html, body {{ background:var(--paper); color:var(--ink); }}
body {{ font-family:var(--sans); font-size:15px; line-height:1.5; padding-inline:clamp(16px,3vw,40px); padding-block:28px 48px; }}
main {{ max-width:1320px; margin:0 auto; display:flex; flex-direction:column; gap:28px; }}
header {{ display:flex; flex-direction:column; gap:6px; border-bottom:2px solid var(--primary); padding-bottom:14px; }}
.kicker {{ font-size:.78rem; letter-spacing:.08em; text-transform:uppercase; color:var(--primary); font-weight:600; }}
h1 {{ font-family:var(--serif); font-size:clamp(1.7rem,3.2vw,2.4rem); line-height:1.15; margin:0; text-wrap:balance; }}
h2 {{ font-family:var(--serif); font-size:1.35rem; margin:0 0 10px; }}
.lead {{ color:var(--ink2); margin:0; }}
.motivation p {{ margin:0 0 18px; }}
.motivation img {{ display:block; width:100%; height:auto; }}
.figure {{ overflow-x:auto; border:1px solid var(--rule); background:var(--paper); }}
.figure svg {{ display:block; width:100%; min-width:900px; height:auto; }}
.legend {{ display:flex; flex-wrap:wrap; gap:8px 22px; font-size:.86rem; color:var(--ink2); }}
.legend span {{ display:inline-flex; align-items:center; gap:8px; }}
.sw {{ width:22px; height:14px; border:1.5px solid var(--primary); background:var(--band); display:inline-block; }}
.sw.c {{ background:#fff; }} .sw.s {{ background:var(--store); border-color:#8a96a8; }} .sw.r {{ background:#e9eef7; border-style:dashed; }}
.sw.l {{ background:var(--aiband); border-color:var(--ai); }}
.ln-s {{ width:30px; border-top:2px solid var(--primary); display:inline-block; }} .ln-b {{ width:30px; border-top:2px solid #8a96a8; display:inline-block; }} .ln-a {{ width:30px; border-top:2px dashed var(--ai); display:inline-block; }}
/* svg */
svg text {{ font-family:var(--sans); fill:var(--ink); }}
.b {{ fill:#fff; stroke:var(--primary); stroke-width:1.5; }}
.b.user {{ fill:var(--band); }} .b.core {{ fill:var(--band); }} .b.mod {{ fill:#fff; }} .b.modai {{ fill:var(--aiband); stroke:var(--ai); }}
.b.store {{ fill:var(--store); stroke:#8a96a8; }} .b.rag {{ fill:#e9eef7; stroke-dasharray:6 4; }} .b.rep {{ fill:#fff; stroke-dasharray:6 4; }}
.b.llm {{ fill:var(--aiband); stroke:var(--ai); stroke-width:2; }}
.b.grp {{ fill:#fff; stroke-dasharray:none; }} .b.grp.ai {{ fill:#fffaf3; stroke:var(--ai); }} .b.grp2 {{ fill:var(--store); }}
.bt {{ font-size:16px; font-weight:700; }} .btm {{ font-size:14.5px; font-weight:700; }} .blm {{ font-size:12px; fill:var(--ink2) !important; }} .bl {{ font-size:13px; fill:var(--ink2) !important; }}
.srv {{ fill:none; stroke:var(--primary); stroke-width:2.5; }}
.srvl {{ font-size:14px; font-weight:600; fill:var(--primary) !important; }}
.proc {{ fill:none; stroke:var(--primary); stroke-width:2.2; }}
.procl {{ font-size:14px; font-weight:700; fill:var(--primary) !important; }}
.zone.zo {{ stroke:var(--ai); }}
.zone {{ fill:none; stroke:#9aa4b2; stroke-width:1.2; stroke-dasharray:3 5; }}
.zl {{ font-size:13px; fill:var(--ink2) !important; font-style:italic; }} .zlo {{ font-size:13px; font-weight:600; fill:var(--ai) !important; }}
.ln {{ fill:none; stroke:var(--primary); stroke-width:2; }} .ln.ai {{ stroke:var(--ai); stroke-dasharray:7 5; }}
.bus2 {{ fill:none; stroke:#8a96a8; stroke-width:2; }} .bus2.ai {{ stroke:var(--ai); }} .jn {{ fill:#8a96a8; }}
.ic {{ fill:none; stroke:var(--primary); stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }} .ic [fill="black"] {{ fill:var(--primary); stroke:none; }}
.ic.o {{ stroke:var(--ai); }} .ic.o [fill="black"] {{ fill:var(--ai); }}
.bus {{ fill:none; stroke:#8a96a8; stroke-width:1.5; }}
.busl {{ font-size:12px; fill:var(--ink2) !important; font-style:italic; }}
.mh {{ fill:var(--primary); }} .mho {{ fill:var(--ai); }}
.bd {{ fill:var(--primary); }} .bdo {{ fill:var(--ai); }}
.bn {{ font-size:13px; font-weight:700; fill:#fff !important; text-anchor:middle; }}
/* table */
.tablewrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; min-width:760px; font-size:.92rem; }}
th {{ text-align:left; font-size:.78rem; letter-spacing:.04em; text-transform:uppercase; color:var(--ink2); font-weight:600; padding:8px; border-bottom:2px solid var(--primary); }}
td {{ padding:9px 8px; border-bottom:1px solid var(--rule); vertical-align:top; }}
td.who {{ font-weight:600; white-space:nowrap; }} td.tech {{ color:var(--ink2); }}
.nb {{ display:inline-grid; place-items:center; min-width:24px; height:24px; border-radius:50%; background:var(--primary); color:#fff; font-weight:700; font-size:.8rem; }}
.nb.o {{ background:var(--ai); }}
.cols2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:32px; }}
ol.path {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:10px; }}
ol.path li {{ display:grid; grid-template-columns:56px minmax(0,1fr); gap:10px; align-items:baseline; }}
.sn {{ font-weight:700; color:var(--primary); font-variant-numeric:tabular-nums; }}
.facts {{ display:flex; flex-direction:column; gap:10px; background:var(--shade); padding:16px 18px; }}
.facts p {{ margin:0; }}
@media (max-width:820px) {{ .cols2 {{ grid-template-columns:1fr; }} }}
.hero {{ display:grid; grid-template-columns:minmax(200px,300px) 1fr; gap:28px; align-items:center; border-bottom:2px solid var(--primary); padding-bottom:22px; }}
.hero img {{ width:100%; height:auto; }}
.sr-only {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }}
.hero p {{ margin:0 0 10px; }}
.hero .kicker {{ display:block; margin-bottom:16px; }}
.ai-uses {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr)); gap:14px; margin-top:12px; }}
.ai-use {{ border-top:3px solid var(--ai); background:#fff; padding:12px 14px; }}
.ai-use h3 {{ margin:0 0 6px; font-size:1rem; }}
.ai-use p {{ margin:0; font-size:.94rem; }}
.hero ul {{ margin:0 0 12px; padding-left:20px; }}
.meta {{ font-size:.92rem; color:var(--ink2); }}
.btn {{ display:inline-block; margin-top:6px; padding:9px 16px; background:var(--primary); color:#fff; text-decoration:none; font-weight:600; }}
.btn:hover, .btn:focus-visible {{ background:#0f3470; }}
a {{ color:var(--primary); }}
.shots {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:24px; }}
.shots figure {{ margin:0; display:flex; flex-direction:column; gap:8px; }}
.shots img {{ width:100%; height:auto; border:1px solid var(--rule); }}
.shots figcaption {{ font-size:.9rem; color:var(--ink2); }}
td.why {{ min-width:280px; }}
@media (max-width:820px) {{ .shots {{ grid-template-columns:1fr; }} }}
@media (max-width:720px) {{ .hero {{ grid-template-columns:1fr; }} .hero img {{ max-width:240px; }} }}
</style>
<main>
<section class="hero" aria-labelledby="about-title">
  <img src="../../src/data_story/assets/logo/logo-panel.svg" width="300" height="146" alt="Логотип Data Story">
  <div>
    <span class="kicker">MVP сервісу аналітики даних · фінальний проєкт курсу «AI-агенти для розробників»</span>
    <h1 id="about-title" class="sr-only">Data Story</h1>
    <p><b>Data Story</b> — MVP локального сервісу, який проводить шлях від набору CSV до огляду даних, візуалізації, лінійної регресії, висновків і HTML-звіту. Розрахунки виконує сервіс, а AI-помічник підказує наступні кроки, пояснює результати й готує чернетки тексту.</p>
    <p><b>Для чого:</b> демонстрація принципів аналізу даних, візуалізації даних і основ моделювання та допомога студентам у вивченні аналітики даних.</p>
    <p><b>Для кого:</b> студенти, які вивчають аналітику даних, і викладачі, яким потрібен наочний інструмент для занять.</p>
    <p class="meta">Автор: Юрій Клебан · працює локально на Windows, LLM — OpenAI через інтернет</p>
    <a class="btn" href="https://github.com/kleban/ai-course-final-project">Репозиторій проєкту на GitHub: код, README, документація</a>
  </div>
</section>
<section class="motivation" aria-labelledby="motivation-title">
  <h2 id="motivation-title">Мотивація</h2>
  <p>Автор викладає студентам аналіз і візуалізацію даних, має досвід участі в комерційних проєктах з машинного навчання й хотів частково втілити ці знання в сервісі. Data Story — MVP такого інструмента: він показує на реальних даних, як іти від питання до перевіреного результату.</p>
  <p>«Storytelling with Data» Коул Нуссбаумер Кнафлік — книжка, яка дуже добре пояснює, як аналізувати дані й розповідати ними зрозумілу історію. Її принципи дизайну стали одним з основних орієнтирів для побудови візуалізації даних у Data Story: доречний тип графіка, нічого зайвого, увага — на головному.</p>
  <img src="../presentation-assets/storytelling-two-editions.png" width="1672" height="941" alt="Старе та ювілейне видання Storytelling with Data стоять поруч на дерев’яному столі в сонячному світлі">
</section>
<section aria-labelledby="shots-title">
  <h2 id="shots-title">Як це виглядає</h2>
  <p class="lead">Знімки екрана MVP на демонстраційних даних (Seoul Bike Sharing Demand і тестовий набір); рамку браузера домальовано.</p>
  <div class="shots">
    <figure><img src="screens/heatmap.png" width="1442" height="987" loading="lazy" alt="Оглядовий аналіз у вікні браузера: теплова карта кореляцій дев’яти числових полів Seoul у синьо-помаранчевій шкалі"><figcaption>Оглядовий аналіз: теплова карта кореляцій числових полів.</figcaption></figure>
    <figure><img src="screens/prediction.png" width="1442" height="987" loading="lazy" alt="Перевірка моделі у вікні браузера: діаграма «прогноз проти факту» на тестовій частині з поясненням, як її читати"><figcaption>Перевірка моделі: прогноз проти факту на тестових даних.</figcaption></figure>
    <figure><img src="screens/chat-model.png" width="1442" height="987" loading="lazy" alt="AI-помічник у вікні браузера поруч із графіком регресії: студентське питання про якість моделі й відповідь з R², MAE, порівнянням із простим прогнозом і посиланням на джерело"><figcaption>Чат з AI поруч із графіком: помічник пояснює якість моделі простими словами й посилається на базу знань.</figcaption></figure>
    <figure><img src="screens/report.png" width="1442" height="987" loading="lazy" alt="HTML-звіт Quarto у вікні браузера: гістограма розподілу кількості прокатів із медіаною"><figcaption>Звіт: HTML, зібраний Quarto з перевірених результатів.</figcaption></figure>
  </div>
</section>
<section aria-labelledby="arch-title">
  <h2 id="arch-title">Архітектура сервісу</h2>
  <p class="lead">Дані, розрахунки, пошук у базі знань і звіти працюють на комп’ютері користувача; до OpenAI сервіс звертається через інтернет лише за дією користувача. Номери на стрілках відповідають рядкам таблиці нижче.</p>
</section>
<div class="figure">{svg}</div>
<div class="legend">
  <span><i class="sw"></i>інтерфейс і ядро сервісу</span>
  <span><i class="sw c"></i>модулі розрахунків</span>
  <span><i class="sw l"></i>AI: чат, вбудовані функції, OpenAI</span>
  <span><i class="sw r"></i>RAG і bge-m3 (у процесі), Quarto (окремий процес)</span>
  <span><i class="sw s"></i>сховище</span>
  <span><i class="ln-s"></i>локальний запит і відповідь</span>
  <span><i class="ln-a"></i>запит через інтернет</span>
  <span><i class="sw c" style="border-width:2.2px"></i>рамка «Один процес Python»: фронтенд і бекенд — частини однієї програми</span>
</div>
<section aria-labelledby="flows-title">
  <h2 id="flows-title">Потоки даних і вибір технологій</h2>
  <p class="lead">Що передається між складовими, яка технологія це робить і чому для MVP обрано саме її.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>№</th><th>Хто ⇄ кому</th><th>Що надсилає</th><th>Що отримує назад</th><th>Технологія</th><th>Чому саме ця технологія</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</section>
<section aria-labelledby="matrix-title">
  <h2 id="matrix-title">Хто з чим працює напряму</h2>
  <p class="lead">Модулі — класи в одному процесі; кожен сам відкриває потрібне сховище (без брокера чи окремого шару доступу). OpenAI викликається лише через клієнт OpenAI.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Блок</th><th>Модулі коду</th>{"".join(f"<th>{c}</th>" for c in MATRIX_COLS)}</tr></thead>
    <tbody>{matrix_rows}</tbody>
  </table></div>
</section>
<section class="facts" aria-labelledby="assistant-title">
  <h2 id="assistant-title">Як працює AI-помічник</h2>
  <p>Помічник відкривається кнопкою «AI» на будь-якій сторінці й має три режими: <b>Порадь</b> (наступні кроки), <b>Виконай</b> (дозволені дії сервісу) і <b>Поясни результат</b>. Він знає поточний проєкт і сторінку, а за неоднозначного завдання ставить коротке уточнювальне питання.</p>
  <p>Відповідь будується з фактів сервісу, фрагментів бази знань (RAG) і результатів інструментів: LLM пропонує виклик, а виконує його сервіс — наприклад, перевірений SQL у DuckDB. Зміни застосовуються лише після «Застосувати»; кожен виклик і токени записуються в журнал AI.</p>
</section>
<section class="facts" aria-labelledby="ai-uses-title">
  <h2 id="ai-uses-title">Де задіяний AI</h2>
  <p>AI у MVP — помічник, а не калькулятор: розрахунки виконує сервіс, а LLM пропонує, пояснює й формулює. Кожен виклик — лише за дією користувача.</p>
  <div class="ai-uses">
    <div class="ai-use"><h3>Помічник у чаті</h3><p>Відкривається кнопкою «AI» на будь-якій сторінці: «Порадь», «Виконай», «Поясни результат». Бачить поточний проєкт і сторінку, відповідає на питання про дані й моделі, уточнює неоднозначні завдання.</p></div>
    <div class="ai-use"><h3>Опис проєкту й метадані</h3><p>З сирого опису набору готує чернетку опису проєкту та полів: назви, одиниці, ролі. Зміни застосовує користувач.</p></div>
    <div class="ai-use"><h3>Оглядовий аналіз</h3><p>Радить, що подивитися в даних, будує графік за текстовою командою (числа рахує сервіс) і пояснює побудовані графіки.</p></div>
    <div class="ai-use"><h3>SQL-запити до DuckDB</h3><p>LLM складає SQL під питання користувача, сервіс перевіряє його (лише один SELECT над таблицями проєкту) і виконує в DuckDB — вбудованій аналітичній базі. Результат стає новою агрегацією лише після «Застосувати».</p></div>
    <div class="ai-use"><h3>Підготовка й модель</h3><p>Радить кроки підготовки й налаштування моделі, може запустити навчання лінійної регресії дозволеним інструментом, пояснює коефіцієнти, метрики, графіки перевірки та наступні кроки.</p></div>
    <div class="ai-use"><h3>Висновки</h3><p>З фактів збереженої моделі, агрегацій і фрагментів бази знань (RAG) готує чернетку висновків із посиланнями на джерела. Автор редагує й затверджує.</p></div>
    <div class="ai-use"><h3>Звіт</h3><p>Готує чернетку тексту розділів звіту зі збережених результатів; числа, таблиці й графіки бере зі знімка, а HTML формує Quarto без AI.</p></div>
  </div>
  <p class="meta">Модель OpenAI обирається окремо для кожної задачі на сторінці «Моделі AI» (із запасними рівнями й повторами); запити, відповіді й токени записуються в журнал AI.</p>
</section>
<p class="meta">Data Story — MVP, створений у межах курсу «AI-агенти для розробників». Код і документація — у <a href="https://github.com/kleban/ai-course-final-project">репозиторії</a>.</p>
</main>'''
output = Path(__file__).resolve().parent
(output / "architecture.html").write_text(page, encoding="utf-8")
(output / "architecture.svg").write_text(svg, encoding="utf-8")
# Static copy for GitHub Pages (main → /docs): no build step on GitHub, everything relative and local.
docs = output.parents[1] / "docs"
(docs / "assets/fonts").mkdir(parents=True, exist_ok=True)
(docs / "index.html").write_text(page.replace("../../src/data_story/assets/fonts/", "assets/fonts/").replace("../../src/data_story/assets/logo/", "assets/").replace('src="screens/', 'src="assets/screens/').replace(
    "../presentation-assets/storytelling-two-editions.png", "assets/storytelling-two-editions.png"), encoding="utf-8")
(docs / ".nojekyll").write_text("", encoding="utf-8")
copyfile(output.parent / "presentation-assets/storytelling-two-editions.png", docs / "assets/storytelling-two-editions.png")
fonts = output.parents[1] / "src/data_story/assets/fonts"
for name in ("plex/ibm-plex-sans-regular.woff2", "plex/ibm-plex-sans-600.woff2", "plex/ibm-plex-sans-700.woff2",
             "stix/stix-two-text-600.woff2", "stix/stix-two-text-700.woff2"):
    (docs / "assets/fonts" / name).parent.mkdir(parents=True, exist_ok=True)
    copyfile(fonts / name, docs / "assets/fonts" / name)
copyfile(output.parents[1] / "src/data_story/assets/logo/logo-panel.svg", docs / "assets/logo-panel.svg")
for d in (docs / "assets/screens",):
    d.mkdir(parents=True, exist_ok=True)
    for shot in (output / "screens").glob("*.png"):
        copyfile(shot, d / shot.name)
for family in ("plex", "stix"):
    copyfile(fonts / family / "OFL.txt", docs / "assets/fonts" / family / "OFL.txt")
print("ok", len(page))
