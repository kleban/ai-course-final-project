from html import escape as e
from pathlib import Path
from shutil import copyfile
import importlib.util

# Architecture of Data Story as implemented (history 121): concrete blocks with icons, two buses
# (analytic modules → DuckDB; chat and built-in AI → RAG / LLM), numbered flows 1–10.
# Generates deliverables/architecture/{architecture.html, architecture.svg} and the in-app page
# src/data_story/assets/about/index.html («Про проєкт»). Run: python deliverables/architecture/build.py

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

W, H = 1600, 930
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

# zones: everything is local except the bottom-right corner (internet)
parts.append('<path class="zone" d="M15 15 H1590 V690 H1210 V915 H15 Z"/>')
parts.append('<text class="zl" x="30" y="900">Комп’ютер користувача (Windows) · розрахунки, дані, SQL, RAG і звіти — локально</text>')
parts.append('<text class="zlo" x="1235" y="714">Інтернет · HTTPS</text>')

box(30, 45, 240, 120, "Користувач у браузері", ["Chrome / Edge · Vue + Quasar", "формули MathJax", "усі ресурси локальні"], "b user", icon="user")
box(325, 60, 850, 75, "Інтерфейс і API", ["NiceGUI 3 (сторінки) + FastAPI (HTTP /api, JSON) на uvicorn"], "b core", icon="api")
box(325, 170, 850, 65, "Сервіс-оркестратор (ProjectService)", ["перевіряє дані й поточний проєкт, викликає модулі, пише журнал; спільний для сторінок, чату й API"], "b core", icon="settings")

# analytic modules: two rows, a data bus between them leads to DuckDB
box(325, 275, 530, 270, "Аналітичні модулі", [], "b grp", "bt")
chips = [(340, 315, "Дані й\nстатистика", "pandas, NumPy", "data"), (513, 315, "Графіки", "SVG, спільна тема", "compare"),
         (686, 315, "Підготовка\nй зведення", "вибірки, з’єднання", "table"), (340, 445, "Модель", "scikit-learn, SciPy", "regression"),
         (686, 445, "Звіти", "знімок → .qmd", "doc")]
for x, y, t, l, i in chips:
    box(x, y, 155, 80, t, [l] if "\n" in t else ["", l][1:], "b mod", "btm", "bl", 12, icon=i)
bus("M417 395 V445 M590 395 V420 M763 395 V445 M417 420 H763", [(417, 420), (590, 420), (763, 420)])
parts.append('<text class="busl" x="430" y="414">шина даних</text>')

# AI group
box(885, 275, 290, 345, "AI — лише явною дією", [], "b grp ai", "bt")
box(900, 312, 260, 75, "Чат-помічник", ["Порадь · Виконай · Поясни"], "b mod modai", "btm", "bl", 12, icon="chat", ic="ic o")
box(900, 445, 260, 80, "Вбудовані AI-функції", ["пояснення, висновки,", "чернетка звіту"], "b mod modai", "btm", "bl", 12, icon="spark", ic="ic o")
box(900, 540, 260, 70, "SQL від LLM", ["перевірка: 1 SELECT, 5 с, 512 МБ"], "b mod", "btm", "bl", 12, icon="code")

box(686, 570, 155, 62, "Quarto 1.10", ["офлайн → HTML"], "b rep", "btm", "bl", 12, icon="quarto")

# storage
box(325, 650, 850, 215, "Сховища · runtime/", [], "b store grp2", "bt")
box(340, 690, 240, 110, "SQLite (схема v16)", ["проєкти, метадані, налаштування,", "журнали подій і AI,", "тексти висновків і звітів"], "b", "btm", "bl", 12, icon="sqlite")
box(595, 690, 250, 110, "Постійна DuckDB", ["набори й результати з версіями:", "статистика, дані графіків,", "метрики, прогнози, залишки"], "b", "btm", "bl", 12, icon="duckdb")
box(900, 690, 260, 110, "Файли", ["CSV-оригінали з SHA-256,", "матриці .npz, HTML звітів,", "уривки книжок, вектори"], "b", "btm", "bl", 12, icon="folder")

# right column
box(1230, 290, 340, 120, "RAG · база знань", ["правила (SQLite) + 106 уривків книжок", "гібридний пошук: TF-IDF + вектори", "→ 3–5 фрагментів із джерелами"], "b rag", icon="rag")
box(1230, 460, 340, 125, "Модель embeddings BAAI/bge-m3", ["ONNX Runtime, локально, ~2,3 ГБ", "текст → вектор із 1024 чисел", "без неї пошук лише TF-IDF"], "b rag", icon="vector")
box(1230, 745, 340, 115, "LLM · OpenAI Responses API", ["gpt-6-luna / gpt-6.1-sol", "ключ лише в .env · через інтернет"], "b llm", icon="bot", ic="ic o")

line("M270 97 H325", "1", 297, 97)
line("M620 420 V690", "4", 620, 615, start=False)
parts.append('<circle class="jn" cx="620" cy="420" r="3.5"/>')
line("M750 135 V170", "2", 750, 152)
line("M325 202 H300 V745 H340", "3", 300, 470)
line("M300 745 V835 H1030 V800", start=False)
parts.append('<circle class="jn" cx="300" cy="745" r="3.5"/>')
line("M841 485 H900", "5", 870, 485)
line("M763 525 V570", "6", 790, 552, start=False)
bus("M1160 350 H1195 V485 M1160 485 H1195", [(1195, 350), (1195, 380), (1195, 485)])
line("M1195 380 H1230", "7", 1212, 362, start=False)
line("M1400 410 V460", "8", 1400, 435)
line("M1030 610 V641 H820 V690", "9", 935, 641)
line("M1195 485 V802 H1230", "10", 1195, 655, ai=True, start=False)

svg = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" xmlns="http://www.w3.org/2000/svg">
<title id="t">Архітектура Data Story</title>
<desc id="d">Браузер → інтерфейс → сервіс-оркестратор. Аналітичні модулі через шину даних працюють із DuckDB; сервіс — із SQLite і файлами. Звіти отримують чернетку від вбудованих AI-функцій і після затвердження передаються в Quarto. Чат і вбудовані AI-функції звертаються до RAG (з моделлю bge-m3) і до OpenAI; SQL від LLM виконується в DuckDB після перевірки. Стрілки 1–10 — потоки даних.</desc>
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
  "NiceGUI дає повноцінний вебінтерфейс (Vue + Quasar) прямо з Python — для MVP не потрібен окремий фронтенд і окрема команда. FastAPI працює в тому ж процесі й автоматично перевіряє дані запитів, тож ті самі дії доступні сторінкам, чату й тестам."),
 ("2", "Інтерфейс ⇄ Сервіс", "виклик сервісу з даними форми або HTTP-запиту", "результат або зрозуміла помилка", "pydantic-контракти; один ProjectService для сторінок, чату й API",
  "Одна точка правил: перевірки й журнал однакові для людини, API та AI. Це спрощує тестування MVP і не дає AI обійти обмеження."),
 ("3", "Сервіс ⇄ SQLite і Файли", "службовий стан: проєкти, метадані, налаштування, журнали, тексти висновків і звітів; оригінали CSV, HTML звітів", "стан проєкту, журнали, збережені файли", "SQLite v16; файли з SHA-256",
  "SQLite — вбудована база в одному файлі: без сервера й налаштувань, з надійними транзакціями. Для локального MVP на одному комп’ютері цього достатньо."),
 ("4", "Аналітичні модулі ⇄ DuckDB", "нові версії таблиць і результатів: статистика, дані графіків, метрики, прогнози, залишки", "збережені таблиці й результати без повторного розрахунку", "DuckDB 1.5; ключі джерела, метаданих і параметрів",
  "DuckDB — вбудована аналітична (колонкова) база: швидкі групування, зведення й з’єднання на SQL без окремого сервера. Результати зберігаються з версіями, тому після перезапуску їх не треба перераховувати."),
 ("5", "Звіти ⇄ Вбудовані AI-функції", "знімок звіту: факти моделі, статистика, затверджені висновки", "чернетка тексту звіту; автор редагує й затверджує", "ReportStore.ai_draft — один виклик OpenAI (завдання report_draft)",
  "AI допомагає сформулювати текст, але числа бере лише з фактів сервісу. Остаточне рішення — за людиною: чернетку редагують і затверджують."),
 ("6", "Звіти → Quarto", "після затвердження: Markdown звіту (.qmd), знімок моделі, статистика, SVG-графіки", "HTML-звіт, що відкривається без інтернету", "ReportStore.render; Quarto CLI 1.10, MathJax, шрифти сервісу; без OpenAI",
  "Quarto — відкритий стандарт відтворюваних звітів: Markdown + формули + графіки → самодостатній HTML. Джерело .qmd можна редагувати й перезібрати, а той самий інструмент у майбутньому дасть PDF, DOCX чи слайди."),
 ("7", "Чат і вбудовані AI ⇄ RAG", "питання користувача або факти моделі", "3–5 фрагментів правил і книжок із джерелом і сторінками", "гібридний пошук TF-IDF + вектори, локально",
  "LLM не знає правил курсу й змісту обраних книжок. RAG підставляє перевірені фрагменти з джерелами, тож відповіді ближчі до методики, а посилання можна перевірити."),
 ("8", "RAG ⇄ bge-m3", "текст питання; уривки книжок під час побудови індексу", "вектор із 1024 чисел для порівняння схожості", "BAAI/bge-m3 з Hugging Face, ONNX Runtime на CPU, ~2,3 ГБ",
  "Модель embeddings перетворює текст на вектор: близькі за змістом тексти мають близькі вектори, тому пошук іде за змістом, а не лише за словами. bge-m3 (ліцензія MIT) багатомовна, з українською; обрана порівнянням кількох моделей на контрольних питаннях. Завантажується один раз з Hugging Face під час Setup і далі працює офлайн; без неї — TF-IDF."),
 ("9", "SQL від LLM ⇄ DuckDB", "SQL, який склала LLM; згадані таблиці проєкту копіюються в окрему тимчасову DuckDB", "до 10 000 рядків і 2 МБ результату; новий набір — лише після «Застосувати»", "перевірка: один SELECT, лише таблиці поточного проєкту; 512 МБ, 5 с",
  "LLM добре перекладає питання людською мовою в SQL, а виконує запит лише сервіс під обмеженнями. Користувач не пише SQL, а дані проєкту захищені від змін."),
 ("10", "Чат і вбудовані AI ⇄ OpenAI", "інструкції + факти (JSON) + фрагменти RAG; чату — ще схема таблиць і список інструментів", "текст / JSON або виклик інструмента; інструмент і SQL виконує сервіс локально", "OpenAI Responses API, httpx",
  "Сильні моделі з викликом інструментів і структурованими відповідями без власної інфраструктури моделей — оптимально для MVP. Модель обирається окремо для кожної задачі; кожен виклик і токени видно в журналі."),
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
.lead {{ color:var(--ink2); max-width:70ch; margin:0; }}
.motivation p {{ max-width:85ch; margin:0 0 18px; }}
.motivation img {{ display:block; width:100%; max-width:1040px; height:auto; }}
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
.hero h1 {{ font-size:clamp(2rem,4vw,2.8rem); }}
.hero p {{ margin:0 0 10px; max-width:75ch; }}
.hero ul {{ margin:0 0 12px; padding-left:20px; }}
.meta {{ font-size:.92rem; color:var(--ink2); }}
.btn {{ display:inline-block; margin-top:6px; padding:9px 16px; background:var(--primary); color:#fff; text-decoration:none; font-weight:600; }}
.btn:hover, .btn:focus-visible {{ background:#0f3470; }}
a {{ color:var(--primary); }}
.shots {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr)); gap:26px; }}
.shots figure {{ margin:0; display:flex; flex-direction:column; gap:8px; }}
.shots img {{ width:100%; height:auto; border:1px solid var(--rule); }}
.shots figcaption {{ font-size:.9rem; color:var(--ink2); }}
td.why {{ min-width:280px; }}
@media (max-width:720px) {{ .hero {{ grid-template-columns:1fr; }} .hero img {{ max-width:240px; }} }}
</style>
<main>
<section class="hero" aria-labelledby="about-title">
  <img src="../../src/data_story/assets/logo/logo-panel.svg" width="300" height="146" alt="Логотип Data Story">
  <div>
    <span class="kicker">MVP сервісу аналітики даних · фінальний проєкт курсу «AI-агенти для розробників»</span>
    <h1 id="about-title">Data Story</h1>
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
    <figure><img src="screens/charts-seoul.png" width="1442" height="987" loading="lazy" alt="Демонстраційна галерея Seoul у вікні браузера: стовпчиковий графік середнього попиту за годинами з виділеним піком о 18:00"><figcaption>Візуалізація за принципами Storytelling with Data: заголовок-висновок, сірий фон і один виділений акцент (пік о 18:00).</figcaption></figure>
    <figure><img src="screens/model-check.png" width="1442" height="987" loading="lazy" alt="Сторінка перевірки моделі у вікні браузера: графік регресії кількості прокатів від температури на тестових даних із поясненням"><figcaption>Перевірка моделі: графік регресії на тестовій частині, поруч — як його читати.</figcaption></figure>
    <figure><img src="screens/chat-sql.png" width="1442" height="987" loading="lazy" alt="AI-помічник у вікні браузера: у режимі «Виконай» готує пропозицію зведення з таблицею результату й кнопкою «Застосувати»"><figcaption>Чат з AI: помічник бачить поточну сторінку, складає SQL-зведення й показує результат; зміни застосовує користувач.</figcaption></figure>
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
<p class="meta">Data Story — MVP, створений у межах курсу «AI-агенти для розробників». Код і документація — у <a href="https://github.com/kleban/ai-course-final-project">репозиторії</a>.</p>
</main>'''
output = Path(__file__).resolve().parent
(output / "architecture.html").write_text(page, encoding="utf-8")
(output / "architecture.svg").write_text(svg, encoding="utf-8")
about = output.parents[1] / "src/data_story/assets/about"
about.mkdir(parents=True, exist_ok=True)
about_page = page.replace("../../src/data_story/assets/fonts/", "../fonts/").replace("../../src/data_story/assets/logo/", "../logo/").replace(
    "../presentation-assets/storytelling-two-editions.png", "storytelling-two-editions.png"
)
(about / "index.html").write_text(about_page, encoding="utf-8")
copyfile(output.parent / "presentation-assets/storytelling-two-editions.png", about / "storytelling-two-editions.png")
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
for d in (docs / "assets/screens", about / "screens"):
    d.mkdir(parents=True, exist_ok=True)
    for shot in (output / "screens").glob("*.png"):
        copyfile(shot, d / shot.name)
for family in ("plex", "stix"):
    copyfile(fonts / family / "OFL.txt", docs / "assets/fonts" / family / "OFL.txt")
print("ok", len(page))
