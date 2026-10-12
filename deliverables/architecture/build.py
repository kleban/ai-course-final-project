from html import escape as e
from pathlib import Path
from shutil import copyfile

# Architecture of Data Story as implemented (history 116): one diagram, numbered flows 1–12.
# Generates deliverables/architecture/{architecture.html, architecture.svg} and the in-app page
# src/data_story/assets/about/index.html («Про проєкт»). Run: python deliverables/architecture/build.py

W, H = 1600, 930
parts = []
def box(x, y, w, h, title, lines, cls="b", tcls="bt", lcls="bl", pad=14):
    parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    ty = y + 26
    for t in title.split("\n"):
        parts.append(f'<text class="{tcls}" x="{x+pad}" y="{ty}">{e(t)}</text>'); ty += 19
    ty += 4
    for t in lines:
        parts.append(f'<text class="{lcls}" x="{x+pad}" y="{ty}">{e(t)}</text>'); ty += 16

def badge(n, bx, by, ai=False):
    parts.append(f'<circle class="bd{" bdo" if ai else ""}" cx="{bx}" cy="{by}" r="13"/><text class="bn" x="{bx}" y="{by+4.5}">{n}</text>')

def line(d, cls="ln", n=None, bx=0, by=0, ends=True):
    ai = "ai" in cls
    marks = f' marker-start="url(#{"aso" if ai else "as"})" marker-end="url(#{"aeo" if ai else "ae"})"' if ends else ""
    parts.append(f'<path class="{cls}" d="{d}"{marks}/>')
    if n:
        badge(n, bx, by, ai)

# boundaries: everything is local except the bottom-right corner (internet)
parts.append('<path class="zone" d="M15 15 H1590 V700 H1190 V880 H15 Z"/>')
parts.append('<text class="zl" x="30" y="904">Комп’ютер користувача (Windows) · розрахунки, дані, SQL, RAG і звіти — локально</text>')
parts.append('<text class="zlo" x="1215" y="722">Інтернет · HTTPS</text>')

box(30, 70, 210, 190, "Користувач\nу браузері", ["Chrome / Edge", "інтерфейс Vue + Quasar", "формули MathJax", "(усі ресурси локальні)"], "b user", "bt")
box(30, 380, 240, 120, "Звіти · Quarto 1.10", ["окремий процес (CLI), офлайн", "Markdown (.qmd) + SVG → HTML"], "b rep")

# server container
parts.append('<rect class="srv" x="320" y="35" width="820" height="617"/>')
parts.append('<text class="srvl" x="338" y="62">Сервер Data Story · один процес Python 3.13 · 127.0.0.1:8765</text>')
box(345, 80, 762, 90, "Інтерфейс і API", ["NiceGUI 3 (сторінки, WebSocket) + FastAPI (HTTP /api, JSON) на uvicorn — спільний ProjectService"], "b core")
box(345, 220, 762, 90, "Сервіс-оркестратор (ProjectService)", ["перевіряє вхідні дані (pydantic) і поточний проєкт, викликає модулі, пише журнал подій;", "той самий для сторінок, кнопок, чату й HTTP API; AI — лише явною дією користувача"], "b core")
mods = [
 ("Звіти", ["знімок", "результатів", "→ Markdown", "(.qmd)"], False),
 ("Дані й\nстатистика", ["pandas,", "NumPy, CSV,", "пропуски"], False),
 ("Графіки", ["SVG сервісу,", "спільна тема,", "MathJax"], False),
 ("Підготовка\nй зведення", ["вибірки,", "з’єднання,", "зведення"], False),
 ("Модель", ["scikit-learn,", "SciPy,", "p-value"], False),
 ("Чат-\nпомічник", ["Порадь,", "Виконай,", "Поясни;", "SQL від LLM"], True),
 ("Вбудовані\nAI-функції", ["пояснення,", "висновки,", "чернетки", "звітів"], True),
]
for i, (t, ls, ai) in enumerate(mods):
    x = 345 + i * 110
    box(x, 360, 102, 125, t, ls, "b mod" + (" modai" if ai else ""), "btm", "blm", 9)
    cx = x + 51
    parts.append(f'<path class="ln" d="M{cx} 310 V360" marker-start="url(#as)" marker-end="url(#ae)"/>')
    if not ai:
        parts.append(f'<path class="bus" d="M{cx} 485 V520"/>')
badge("3", 396, 335)
parts.append('<path class="bus" d="M396 520 H836"/>')
parts.append('<text class="busl" x="480" y="540">спільні збережені результати</text>')

# analytical queries: SQL written by the LLM, checked and executed by the service
box(880, 545, 245, 95, "Аналітичні запити", ["SQL від LLM → перевірка сервісом", "1 SELECT · лише таблиці проєкту", "5 с · 512 МБ · до 10 000 рядків"], "b core")

# storage
box(320, 690, 260, 140, "Файли runtime/", ["CSV-оригінали з SHA-256,", "матриці .npz, HTML звітів,", "уривки книжок, вектори .npy"], "b store")
box(600, 690, 260, 140, "SQLite (схема v16)", ["проєкти, метадані, налаштування,", "журнали подій і викликів AI,", "тексти висновків і звітів,", "правила бази знань"], "b store")
box(880, 690, 260, 140, "Постійна DuckDB", ["runtime/analytics.duckdb", "набори й нормалізовані таблиці,", "статистика, дані графіків,", "метрики, коефіцієнти, прогнози,", "залишки · версії й походження"], "b store")

line("M240 125 H345", "ln", "1", 292, 125)
line("M720 170 V220", "ln", "2", 720, 195)
line("M836 520 V670 H900 V690", "ln", "4", 868, 670)
line("M760 520 V690", "ln", "5", 760, 605)
line("M450 520 V690", "ln", "6", 450, 605)
line("M946 485 V545", "ln", "7", 946, 515)
line("M1000 640 V690", "ln", "8", 1000, 665)
line("M345 440 H270", "ln", "12", 296, 440)

# right column
box(1210, 35, 360, 175, "RAG · база знань", ["пошук за словами (TF-IDF) і за змістом", "правила: 5 документів, 32 розділи (SQLite)", "книжки: 106 перевірених уривків", "результат: 3–5 фрагментів + джерело"], "b rag")
box(1210, 250, 360, 110, "Модель embeddings BAAI/bge-m3", ["ONNX Runtime, локально (~2,3 ГБ)", "текст → вектор 1024 чисел"], "b rag")
box(1210, 735, 360, 140, "LLM · OpenAI Responses API", ["gpt-6-luna / gpt-6.1-sol — за задачею", "httpx, ключ лише в .env", "єдиний компонент через інтернет"], "b llm")
line("M1107 265 H1175 V122 H1210", "ln", "9", 1175, 190)
line("M1390 210 V250", "ln", "10", 1390, 230)
# both AI ways share one OpenAI client
parts.append('<path class="ln ai" d="M1056 485 V503" marker-start="url(#aso)"/>')
line("M980 485 V503 H1175 V805 H1210", "ln ai", "11", 1175, 650)

svg = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" xmlns="http://www.w3.org/2000/svg">
<title id="t">Архітектура Data Story</title>
<desc id="d">Браузер; сервер Data Story з модулями, чат-помічником, вбудованими AI-функціями й аналітичними запитами; постійна DuckDB, SQLite і файли; RAG з моделлю bge-m3; Quarto; OpenAI через інтернет. Стрілки 1–12 — потоки даних.</desc>
<defs>
<marker id="ae" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" class="mh"/></marker>
<marker id="as" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10 0 L0 5 L10 10 z" class="mh"/></marker>
<marker id="aeo" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" class="mho"/></marker>
<marker id="aso" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10 0 L0 5 L10 10 z" class="mho"/></marker>
</defs>
{"".join(parts)}
</svg>'''

flows = [
 ("1", "Браузер ⇄ Інтерфейс і API", "дія користувача: клік, форма, файл CSV, питання помічнику", "сторінка, таблиці, SVG-графіки, результат дії", "NiceGUI (WebSocket), FastAPI (HTTP, JSON)"),
 ("2", "Інтерфейс ⇄ Сервіс", "виклик сервісу з даними форми або HTTP-запиту", "результат або зрозуміла помилка", "pydantic-контракти, Success / Failure"),
 ("3", "Сервіс ⇄ модулі", "набір, параметри розрахунку, обрані поля, явна AI-дія", "статистика, SVG, вибірки, модель, текст AI, чернетка звіту", "pandas, NumPy, scikit-learn, SciPy"),
 ("4", "Модулі ⇄ DuckDB", "нова незмінна версія таблиці або результату з ключем джерела, метаданих і параметрів", "збережені таблиці й результати — без повторного розрахунку після перезапуску", "DuckDB 1.5, runtime/analytics.duckdb"),
 ("5", "Модулі ⇄ SQLite", "службовий стан, подія журналу", "проєкти, метадані, налаштування, тексти висновків і звітів", "SQLite (sqlite3), схема v16"),
 ("6", "Модулі ⇄ файли", "CSV-оригінали, матриці вибірок, HTML звітів", "файли з перевіркою SHA-256", "файлова система runtime/"),
 ("7", "Чат ⇄ Аналітичні запити", "SQL, який склала LLM (інструменти query_analytics, propose_sql_summary)", "таблиця результату або помилка; новий набір — лише після «Застосувати»", "перевірка сервісом: один SELECT, лише таблиці поточного проєкту"),
 ("8", "Аналітичні запити ⇄ DuckDB", "згадані таблиці проєкту в окрему тимчасову DuckDB і сам SELECT", "до 10 000 рядків і 2 МБ результату", "без зовнішнього доступу; 512 МБ, 5 с"),
 ("9", "Сервіс ⇄ RAG", "питання користувача або факти моделі", "3–5 фрагментів правил і книжок із джерелом і сторінками", "TF-IDF (scikit-learn) + вектори"),
 ("10", "RAG ⇄ bge-m3", "текст запиту (фрагменти — заздалегідь)", "вектор 1024 чисел для пошуку за змістом", "ONNX Runtime, BAAI/bge-m3"),
 ("11", "Чат і вбудовані AI-функції ⇄ OpenAI", "інструкції + факти (JSON) + фрагменти RAG; чату — ще схема таблиць і список інструментів", "текст / JSON або виклик інструмента; інструмент і SQL виконує сервіс локально", "OpenAI Responses API, httpx"),
 ("12", "Звіти ⇄ Quarto", "Markdown звіту (.qmd): знімок моделі, статистика, SVG-графіки, затверджені висновки", "HTML-звіт, що відкривається без інтернету", "Quarto CLI 1.10, MathJax, шрифти сервісу"),
]
rows = "".join(f'<tr><td class="n"><span class="nb{" o" if n=="11" else ""}">{n}</span></td><td class="who">{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td class="tech">{e(d)}</td></tr>' for n,a,b,c,d in flows)

sql_steps = [
 ("1", "Користувач питає помічника, наприклад: «О котрій годині найбільше прокатів?»."),
 ("11", "Сервіс надсилає питання, схему таблиць поточного проєкту й дозволені інструменти. LLM повертає виклик query_analytics із текстом SQL."),
 ("7", "Сервіс перевіряє SQL: один SELECT, лише таблиці поточного проєкту, ліміт рядків."),
 ("8", "Згадані таблиці копіюються в ізольовану DuckDB, запит виконується з обмеженням часу й пам’яті."),
 ("11", "Таблиця результату повертається LLM, яка формулює відповідь. Для Seoul: пік о 18:00, середнє ≈ 1554 прокатів."),
 ("1", "Щоб зберегти результат як набір, користувач переглядає таблицю й натискає «Застосувати»."),
]
steps = [
 ("1", "Користувач натискає «Підготувати висновки AI» на сторінці «Висновки»."),
 ("2, 4, 5", "Сервіс перевіряє запит і бере збережену модель: опис із SQLite, метрики й коефіцієнти з DuckDB."),
 ("3, 4", "Модулі формують факти: R², MAE, коефіцієнти з p-value, обмеження; за потреби — до 3 зведень із DuckDB."),
 ("9, 10", "З фактів складаються запитання до бази знань; RAG повертає 3–5 фрагментів правил і книжок."),
 ("11", "Один запит до OpenAI: інструкції + факти + фрагменти з номерами [1]…[5]. Відповідь перевіряється: посилання лише на наявні джерела."),
 ("5", "Чернетка зберігається в SQLite з фактами, джерелами й токенами; виклик записується в журнал AI."),
 ("1, 12", "Автор редагує й затверджує текст. «Звіти» збирають знімок, Quarto формує HTML."),
]
lis = lambda s: "".join(f'<li><span class="sn">{e(n)}</span><span>{e(t)}</span></li>' for n,t in s)

page = f'''<!doctype html>
<html lang="uk">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Мотивація та архітектура Data Story</title>
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
.ln-s {{ width:30px; border-top:2px solid var(--primary); display:inline-block; }} .ln-a {{ width:30px; border-top:2px dashed var(--ai); display:inline-block; }}
/* svg */
svg text {{ font-family:var(--sans); fill:var(--ink); }}
.b {{ fill:#fff; stroke:var(--primary); stroke-width:1.5; }}
.b.user {{ fill:var(--band); }} .b.core {{ fill:var(--band); }} .b.mod {{ fill:#fff; }} .b.modai {{ fill:var(--aiband); stroke:var(--ai); }}
.b.store {{ fill:var(--store); stroke:#8a96a8; }} .b.rag {{ fill:#e9eef7; stroke-dasharray:6 4; }} .b.rep {{ fill:#fff; stroke-dasharray:6 4; }}
.b.llm {{ fill:var(--aiband); stroke:var(--ai); stroke-width:2; }}
.bt {{ font-size:16px; font-weight:700; }} .btm {{ font-size:14.5px; font-weight:700; }} .blm {{ font-size:12px; fill:var(--ink2) !important; }} .bl {{ font-size:13px; fill:var(--ink2) !important; }}
.srv {{ fill:none; stroke:var(--primary); stroke-width:2.5; }}
.srvl {{ font-size:14px; font-weight:600; fill:var(--primary) !important; }}
.zone {{ fill:none; stroke:#9aa4b2; stroke-width:1.2; stroke-dasharray:3 5; }}
.zl {{ font-size:13px; fill:var(--ink2) !important; font-style:italic; }} .zlo {{ font-size:13px; font-weight:600; fill:var(--ai) !important; }}
.ln {{ fill:none; stroke:var(--primary); stroke-width:2; }} .ln.ai {{ stroke:var(--ai); stroke-dasharray:7 5; }}
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
.nb {{ display:inline-grid; place-items:center; width:24px; height:24px; border-radius:50%; background:var(--primary); color:#fff; font-weight:700; font-size:.8rem; }}
.nb.o {{ background:var(--ai); }}
.cols2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:32px; }}
ol.path {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:10px; }}
ol.path li {{ display:grid; grid-template-columns:56px minmax(0,1fr); gap:10px; align-items:baseline; }}
.sn {{ font-weight:700; color:var(--primary); font-variant-numeric:tabular-nums; }}
.facts {{ display:flex; flex-direction:column; gap:10px; background:var(--shade); padding:16px 18px; }}
.facts p {{ margin:0; }}
@media (max-width:820px) {{ .cols2 {{ grid-template-columns:1fr; }} }}
</style>
<main>
<section class="motivation" aria-labelledby="motivation-title">
  <h1 id="motivation-title">Мотивація</h1>
  <p>«Storytelling with Data» Коул Нуссбаумер Кнафлік — чудова книжка про те, як перетворювати дані на зрозумілу історію. Її принципи дизайну стали одним із орієнтирів для побудови й візуалізації даних у Data Story: обирати доречний графік, прибирати зайве та спрямовувати увагу на головне, щоб аналітик міг ясно пояснити результати. Інструмент планується використовувати як демонстрацію на заняттях з аналітики даних — для пояснення її загальних принципів і понять, а також основ математичного моделювання.</p>
  <img src="../presentation-assets/storytelling-two-editions.png" width="1672" height="941" alt="Старе та ювілейне видання Storytelling with Data стоять поруч на дерев’яному столі в сонячному світлі">
</section>
<header>
  <span class="kicker">Data Story · фінальний проєкт курсу</span>
  <h1>Як влаштований сервіс і хто кому що передає</h1>
  <p class="lead">Окремі складові, пронумеровані потоки даних і технологія на кожному рівні. Дані, розрахунки, пошук у базі знань і звіти працюють на комп’ютері користувача. LLM — обов’язкова частина сервісу: це OpenAI, до якого сервіс звертається через інтернет за дією користувача.</p>
</header>
<section>
  <h2>Складові та потоки даних</h2>
  <p class="lead">Схема відповідає реалізованому коду. Аналітичні таблиці й результати зберігаються в постійній DuckDB, службовий стан — у SQLite. AI використовується двома способами: чат-помічник і вбудовані AI-функції на робочих етапах. Обидва користуються спільним клієнтом OpenAI, RAG і результатами сервісу; SQL від LLM виконує лише сервіс після перевірки.</p>
</section>
<div class="figure">{svg}</div>
<div class="legend">
  <span><i class="sw"></i>інтерфейс і ядро сервісу</span>
  <span><i class="sw c"></i>модулі розрахунків</span>
  <span><i class="sw l"></i>AI: чат, вбудовані функції, OpenAI</span>
  <span><i class="sw r"></i>окремі локальні сервіси (RAG, Quarto)</span>
  <span><i class="sw s"></i>сховище</span>
  <span><i class="ln-s"></i>локальний запит і відповідь</span>
  <span><i class="ln-a"></i>запит через інтернет</span>
</div>
<section>
  <h2>Потоки даних: що надсилається і що повертається</h2>
  <div class="tablewrap"><table>
    <thead><tr><th>№</th><th>Хто ⇄ кому</th><th>Що надсилає</th><th>Що отримує назад</th><th>Технологія</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</section>
<section class="cols2">
  <div>
    <h2>Приклад 1: SQL від LLM у чаті</h2>
    <ol class="path">{lis(sql_steps)}</ol>
  </div>
  <div>
    <h2>Приклад 2: «Підготувати висновки AI»</h2>
    <ol class="path">{lis(steps)}</ol>
  </div>
</section>
<section class="facts">
  <h2>Принципи</h2>
  <p><b>Числа рахує сервіс, не AI.</b> Модель отримує готові факти й лише формулює текст.</p>
  <p><b>SQL складає LLM, виконує сервіс.</b> Користувач не пише SQL; LLM не має прямого доступу до бази — лише один перевірений SELECT над таблицями поточного проєкту.</p>
  <p><b>Результати зберігаються.</b> Статистика, дані графіків і результати моделей — у DuckDB з версіями й походженням; після перезапуску не перераховуються.</p>
  <p><b>AI — лише явною дією.</b> Кожен виклик і токени видно в журналі AI; ключ не потрапляє в журнали.</p>
  <p><b>LLM — OpenAI, через інтернет.</b> Без нього не працюють помічник, висновки й пояснення; решта сервісу (дані, статистика, модель, графіки, HTML-звіт) працює.</p>
  <p><b>RAG локальний.</b> Пошук правил і книжок не потребує інтернету; без моделі bge-m3 сервіс переходить на TF-IDF.</p>
</section>
</main>'''
output = Path(__file__).resolve().parent
(output / "architecture.html").write_text(page, encoding="utf-8")
(output / "architecture.svg").write_text(svg, encoding="utf-8")
about = output.parents[1] / "src/data_story/assets/about"
about.mkdir(parents=True, exist_ok=True)
about_page = page.replace("../../src/data_story/assets/fonts/", "../fonts/").replace(
    "../presentation-assets/storytelling-two-editions.png", "storytelling-two-editions.png"
)
(about / "index.html").write_text(about_page, encoding="utf-8")
copyfile(output.parent / "presentation-assets/storytelling-two-editions.png", about / "storytelling-two-editions.png")
print("ok", len(page))
