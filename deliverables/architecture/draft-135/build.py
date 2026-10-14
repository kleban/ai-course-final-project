from html import escape as e
from pathlib import Path
from shutil import copyfile
import importlib.util

# DRAFT 135 (agent proposal, not accepted): service as hub, modules ⇄ all stores, chat tools via service.
# Architecture of Data Story as implemented (history 121): concrete blocks with icons, two buses
# (analytic modules → DuckDB; chat and built-in AI → RAG / LLM), numbered flows 1–10.
# Generates deliverables/architecture/{architecture.html, architecture.svg} and docs/ (GitHub Pages,
# main → /docs). The in-app «Про проєкт» page was removed in history 128. Run: python deliverables/architecture/build.py

ROOT = Path(__file__).resolve().parents[3]  # draft-135: one level deeper
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

W, H = 1600, 960
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

# zones: everything is local except the top-right corner (internet, OpenAI)
parts.append('<path class="zone" d="M15 15 H1210 V205 H1590 V945 H15 Z"/>')
parts.append('<text class="zl" x="30" y="932">Комп’ютер користувача (Windows) · розрахунки, дані, SQL, RAG і звіти — локально</text>')
parts.append('<text class="zlo" x="1230" y="36">Інтернет · HTTPS</text>')

box(30, 45, 240, 120, "Користувач у браузері", ["Chrome / Edge · Vue + Quasar", "формули MathJax", "усі ресурси локальні"], "b user", icon="user")
box(325, 60, 850, 75, "Інтерфейс і API", ["NiceGUI 3 (сторінки) + FastAPI (HTTP /api, JSON) на uvicorn"], "b core", icon="api")
box(325, 170, 850, 65, "Сервіс-оркестратор (ProjectService)", ["центр сервісу: перевіряє дані й проєкт, викликає всі модулі й AI, виконує інструменти чату"], "b core", icon="settings")

# analytic modules: two rows, a data bus between them leads to DuckDB and to the files
box(325, 275, 530, 270, "Аналітичні модулі", [], "b grp", "bt")
chips = [(340, 315, "Дані й\nстатистика", "pandas, NumPy", "data"), (513, 315, "Графіки", "SVG, спільна тема", "compare"),
         (686, 315, "Підготовка\nй агрегація", "вибірки, з’єднання", "table"), (340, 445, "Модель", "scikit-learn, SciPy", "regression"),
         (686, 445, "Звіти", "знімок → .qmd", "doc")]
for x, y, t, l, i in chips:
    box(x, y, 155, 80, t, [l], "b mod", "btm", "bl", 12, icon=i)

# AI group
box(885, 275, 290, 345, "AI — лише явною дією", [], "b grp ai", "bt")
box(900, 312, 260, 75, "Чат-помічник", ["Порадь · Виконай · Поясни"], "b mod modai", "btm", "bl", 12, icon="chat", ic="ic o")
box(900, 445, 260, 80, "Вбудовані AI-функції", ["пояснення, висновки,", "чернетка звіту"], "b mod modai", "btm", "bl", 12, icon="spark", ic="ic o")
box(900, 540, 260, 70, "SQL від LLM", ["перевірка: 1 SELECT, 5 с, 512 МБ"], "b mod", "btm", "bl", 12, icon="code")

box(686, 570, 155, 62, "Quarto 1.10", ["офлайн → HTML"], "b rep", "btm", "bl", 12, icon="quarto")

# storage: files under the analytic modules, DuckDB in the middle, SQLite under AI
box(325, 650, 850, 215, "Сховища · runtime/", [], "b store grp2", "bt")
box(340, 712, 240, 110, "Файли", ["CSV-оригінали з SHA-256, .npz,", "HTML звітів, книжки й вектори,", "файли моделі bge-m3"], "b", "btm", "bl", 12, icon="folder")
box(595, 712, 250, 110, "Постійна DuckDB", ["набори й результати з версіями:", "статистика, дані графіків,", "метрики, прогнози, залишки"], "b", "btm", "bl", 12, icon="duckdb")
box(900, 712, 260, 110, "SQLite (схема v16)", ["проєкти, реєстр наборів, метадані,", "запуски, налаштування, журнали", "подій і AI, правила RAG, висновки"], "b", "btm", "bl", 12, icon="sqlite")

# right column: OpenAI on top (internet), RAG and bge-m3 below
box(1230, 50, 340, 115, "LLM · OpenAI Responses API", ["gpt-6-luna / gpt-6.1-sol", "ключ лише в .env · через інтернет"], "b llm", icon="bot", ic="ic o")
box(1230, 290, 340, 120, "RAG · база знань", ["правила (SQLite) + 106 уривків книжок", "гібридний пошук: TF-IDF + вектори", "→ 3–5 фрагментів із джерелами"], "b rag", icon="rag")
box(1230, 460, 340, 125, "Модель embeddings BAAI/bge-m3", ["завантажена з Hugging Face (Setup, SHA-256)", "ONNX Runtime, локально, ~2,3 ГБ", "текст → вектор із 1024 чисел"], "b rag", icon="vector")

line("M270 97 H325", "1", 297, 97)
line("M750 135 V170", "2", 750, 152)
line("M590 235 V275", "3", 560, 255)
line("M1030 235 V275", "4", 1060, 255)
# storage bus inside «Сховища»: every store is reached from it
bus("M460 692 H1160", [(630, 692), (1100, 692), (1160, 692)])
line("M460 692 V712", start=False)
line("M720 692 V712", start=False)
line("M1030 692 V712", start=False)
line("M630 545 V692", "5", 630, 610, end=False)
line("M841 485 H900", "6", 870, 485)
line("M763 525 V570", "7", 790, 552, start=False)
bus("M1160 350 H1195 V485 M1160 485 H1195", [(1195, 350), (1195, 380), (1195, 485)])
line("M1195 380 H1230", "8", 1212, 362, start=False)
line("M1400 410 V460", "9", 1400, 435)
line("M1195 350 V108 H1230", "10", 1195, 230, ai=True, start=False)
line("M1400 585 V692 H1160", "11", 1400, 640, end=False)
line("M1100 620 V692", "12", 1128, 656, end=False)

svg = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" xmlns="http://www.w3.org/2000/svg">
<title id="t">Архітектура Data Story</title>
<desc id="d">Чернетка 135. Браузер → інтерфейс → сервіс-оркестратор. Аналітичні модулі через шину даних пишуть і читають DuckDB та файли; сервіс веде службовий стан у SQLite. Звіти отримують чернетку від вбудованих AI-функцій і після затвердження передаються в Quarto. Чат і вбудовані AI-функції через спільну шину звертаються до RAG (з моделлю bge-m3, файли якої лежать локально), до OpenAI через інтернет і через сервіс до SQLite (контекст, журнал AI, чернетки); SQL від LLM виконується в DuckDB після перевірки. Стрілки 1–12 — потоки даних.</desc>
<defs>
<marker id="ae" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" class="mh"/></marker>
<marker id="as" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10 0 L0 5 L10 10 z" class="mh"/></marker>
<marker id="aeo" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" class="mho"/></marker>
<marker id="aso" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10 0 L0 5 L10 10 z" class="mho"/></marker>
</defs>
{"".join(parts)}
</svg>'''

flows = [
 ("1", "Браузер ⇄ Інтерфейс і API", "дія користувача: клік, форма, файл CSV, питання помічнику", "сторінка, таблиці, SVG-графіки, результат дії", "NiceGUI (WebSocket), FastAPI (HTTP, JSON)",
  "NiceGUI дає повноцінний вебінтерфейс (Vue + Quasar) прямо з Python — для MVP не потрібен окремий фронтенд. FastAPI працює в тому ж процесі й автоматично перевіряє дані запитів."),
 ("2", "Інтерфейс ⇄ Сервіс", "виклик сервісу з даними форми або HTTP-запиту", "результат або зрозуміла помилка", "pydantic-контракти; один ProjectService для сторінок, чату й API",
  "Одна точка правил: перевірки однакові для людини, API та AI. Це спрощує тестування й не дає AI обійти обмеження."),
 ("3", "Сервіс ⇄ Аналітичні модулі", "перевірені параметри дії: набір, поля, налаштування підготовки, модель, звіт", "результат розрахунку: таблиці, SVG, метрики, версія звіту", "Python-модулі: pandas, NumPy, scikit-learn, SciPy",
  "Розрахунки — лише в коді сервісу, без AI: результат відтворюваний і перевірений тестами."),
 ("4", "Сервіс ⇄ AI (чат і вбудовані функції)", "задача AI: питання, режим, поточна сторінка, факти; для чату — результати інструментів", "відповідь або виклик інструмента: LLM пропонує, сервіс виконує (навчання, SQL, чернетки, графіки)", "Assistant, ConclusionStore, ReportStore.ai_draft",
  "Агентний цикл: модель лише обирає інструмент і параметри, а виконує їх сервіс з усіма перевірками. Зміни застосовуються після «Застосувати»."),
 ("5", "Аналітичні модулі ⇄ Сховища", "SQLite: реєстр наборів, метадані, запуски навчання, знімки моделей, журнал подій; DuckDB: таблиці й результати з версіями; файли: оригінали CSV, .npz, HTML звітів", "збережений стан і результати без повторного розрахунку", "SQLite v16, DuckDB 1.5, файли в runtime/ з SHA-256",
  "Кожне сховище — для свого: SQLite — надійні транзакції службового стану, DuckDB — швидкі агрегації й з’єднання, файли — великі оригінали й матриці."),
 ("6", "Звіти ⇄ Вбудовані AI-функції", "знімок звіту: факти моделі, статистика, затверджені висновки", "чернетка тексту звіту; автор редагує й затверджує", "ReportStore.ai_draft — один виклик OpenAI (report_draft)",
  "AI допомагає сформулювати текст, але числа бере лише з фактів сервісу. Остаточне рішення — за людиною."),
 ("7", "Звіти → Quarto", "після затвердження: Markdown звіту (.qmd), знімок моделі, статистика, SVG-графіки", "HTML-звіт, що відкривається без інтернету", "Quarto CLI 1.10, MathJax, шрифти сервісу; без OpenAI",
  "Quarto — відкритий стандарт відтворюваних звітів: Markdown + формули + графіки → самодостатній HTML."),
 ("8", "AI ⇄ RAG", "питання користувача або факти моделі", "3–5 фрагментів правил і книжок із джерелом і сторінками", "гібридний пошук TF-IDF + вектори, локально",
  "LLM не знає правил курсу й змісту обраних книжок. RAG підставляє перевірені фрагменти з джерелами."),
 ("9", "RAG ⇄ bge-m3", "текст питання; уривки книжок під час побудови індексу", "вектор із 1024 чисел для порівняння схожості", "BAAI/bge-m3 з Hugging Face, ONNX Runtime на CPU, ~2,3 ГБ",
  "Пошук за змістом, а не лише за словами; багатомовна модель з українською, обрана порівнянням на контрольних питаннях; без неї — TF-IDF."),
 ("10", "AI ⇄ OpenAI", "інструкції + факти (JSON) + фрагменти RAG; чату — ще схема таблиць і список інструментів", "текст / JSON або виклик інструмента", "OpenAI Responses API, httpx",
  "Сильні моделі з викликом інструментів без власної інфраструктури. Модель обирається для кожної задачі; кожен виклик, токени й вартість — у журналі AI."),
 ("11", "RAG ⇄ Сховища", "кеш векторів уривків", "правила бази знань (SQLite), вибрані розділи книжок, вектори .npy, файли моделі bge-m3", "SQLite; runtime/knowledge-sources, knowledge-index, dependencies/embeddings",
  "Правила редагуються в сервісі й зберігаються в базі; великі книжки й модель — файлами, завантажуються один раз під час Setup."),
 ("12", "AI ⇄ Сховища", "журнал AI (запити, відповіді, токени, вартість), висновки, події чату; SQL від LLM", "контекст проєкту; результат SQL з тимчасової копії таблиць DuckDB", "SQLite; DuckDB — один SELECT, лише таблиці проєкту, 512 МБ, 5 с",
  "Кожен виклик AI зберігається й перевіряється. SQL від LLM виконується лише в ізольованій копії DuckDB, тому дані й службовий стан захищені від змін."),
]
rows = "".join(f'<tr><td class="n"><span class="nb{" o" if n=="10" else ""}">{n}</span></td><td class="who">{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td class="tech">{e(d)}</td><td class="why">{e(w)}</td></tr>' for n,a,b,c,d,w in flows)

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
  <span><i class="sw r"></i>окремі локальні сервіси (RAG, bge-m3, Quarto)</span>
  <span><i class="sw s"></i>сховище</span>
  <span><i class="ln-s"></i>локальний запит і відповідь</span>
  <span><i class="ln-a"></i>запит через інтернет</span>
  <span><i class="ln-b"></i>шина: кілька блоків користуються одним адресатом</span>
</div>
<section aria-labelledby="flows-title">
  <h2 id="flows-title">Потоки даних і вибір технологій</h2>
  <p class="lead">Що передається між складовими, яка технологія це робить і чому для MVP обрано саме її.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>№</th><th>Хто ⇄ кому</th><th>Що надсилає</th><th>Що отримує назад</th><th>Технологія</th><th>Чому саме ця технологія</th></tr></thead>
    <tbody>{rows}</tbody>
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
page = page.replace("../../src/", "../../../src/").replace("../presentation-assets/", "../../presentation-assets/").replace('src="screens/', 'src="../screens/')
(output / "architecture.html").write_text(page, encoding="utf-8")
(output / "architecture.svg").write_text(svg, encoding="utf-8")
print("draft ok", len(page))
