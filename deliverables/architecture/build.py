from html import escape as e

W, H = 1600, 900
parts = []
def box(x, y, w, h, title, lines, cls="b", tcls="bt"):
    parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    ty = y + 26
    for t in title.split("\n"):
        parts.append(f'<text class="{tcls}" x="{x+14}" y="{ty}">{e(t)}</text>'); ty += 19
    ty += 4
    for t in lines:
        parts.append(f'<text class="bl" x="{x+14}" y="{ty}">{e(t)}</text>'); ty += 17

def line(d, cls="ln", badge=None, bx=0, by=0):
    parts.append(f'<path class="{cls}" d="{d}" marker-start="url(#{"as" if "ai" not in cls else "aso"})" marker-end="url(#{"ae" if "ai" not in cls else "aeo"})"/>')
    if badge:
        parts.append(f'<circle class="bd{" bdo" if "ai" in cls else ""}" cx="{bx}" cy="{by}" r="13"/><text class="bn" x="{bx}" y="{by+4.5}">{badge}</text>')

# boundaries
parts.append('<path class="zone" d="M15 15 H1590 V640 H1150 V830 H15 Z"/>')
parts.append('<text class="zl" x="30" y="854">Комп’ютер користувача (Windows) · усе працює локально, без інтернету</text>')
parts.append('<text class="zlo" x="1175" y="660">Інтернет · HTTPS</text>')

box(30, 70, 210, 190, "Користувач\nу браузері", ["Chrome / Edge", "інтерфейс Vue + Quasar", "формули MathJax", "(усі ресурси локальні)"], "b user", "bt")
# server container
parts.append('<rect class="srv" x="320" y="35" width="720" height="565"/>')
parts.append('<text class="srvl" x="338" y="62">Сервер Data Story · один процес Python 3.13 · 127.0.0.1:8765</text>')
box(345, 80, 670, 90, "Інтерфейс і API", ["NiceGUI 3 (сторінки, WebSocket) + FastAPI (HTTP /api, JSON) на uvicorn"], "b core")
box(345, 220, 670, 90, "Сервіс-оркестратор (ProjectService)", ["перевіряє вхідні дані (pydantic), викликає модулі, пише журнал подій;", "AI викликається лише явною дією користувача"], "b core")
mods = [
 ("Дані і\nстатистика", ["pandas, NumPy", "CSV, метадані,", "пропуски"]),
 ("Графіки", ["SVG сервісу,", "спільна тема,", "MathJax"]),
 ("Зведення", ["DuckDB 1.5", "SQL складає", "сервіс"]),
 ("Модель", ["scikit-learn:", "лінійна регресія,", "SciPy: p-value"]),
 ("AI-логіка", ["помічник,", "висновки,", "чернетки звіту"]),
]
for i, (t, ls) in enumerate(mods):
    x = 345 + i * 136
    box(x, 360, 124, 125, t, ls, "b mod" + (" modai" if i == 4 else ""))
    cx = x + 62
    parts.append(f'<path class="ln" d="M{cx} 310 V360" marker-start="url(#as)" marker-end="url(#ae)"/>')
    parts.append(f'<path class="bus" d="M{cx} 485 V540"/>')
parts.append(f'')
parts.append('<circle class="bd" cx="407" cy="335" r="13"/><text class="bn" x="407" y="339.5">3</text>')
parts.append('<path class="bus" d="M407 540 H951"/>')
# storage
box(320, 670, 350, 140, "SQLite (схема v16)", ["проєкти, метадані, події журналу,", "вибірки, моделі, звіти, висновки,", "правила бази знань, журнал викликів AI"], "b store")
box(690, 670, 350, 140, "Файли runtime/", ["CSV-оригінали й зведення, матриці .npz,", "SVG і HTML звітів,", "фрагменти книжок і вектори .npy"], "b store")
line("M495 540 V670", "ln", "4", 495, 605)
line("M865 540 V670", "ln", "5", 865, 605)
# browser <-> UI
line("M240 125 H345", "ln", "1", 292, 125)
# UI <-> orchestrator
line("M680 170 V220", "ln", "2", 680, 195)
# right column
box(1170, 35, 400, 175, "RAG · база знань", ["пошук за словами (TF-IDF) і за змістом (bge-m3)", "правила: 5 документів, 32 розділи (SQLite)", "книжки: 6 книжок, 620 фрагментів", "результат: 3–5 фрагментів + джерело, сторінки"], "b rag")
box(1170, 250, 400, 110, "Модель embeddings BAAI/bge-m3", ["ONNX Runtime, локально (~2,3 ГБ)", "текст → вектор 1024 чисел"], "b rag")
box(1170, 410, 400, 120, "Звіти · Quarto 1.10", ["окремий процес (CLI), без інтернету", "Markdown (.qmd) + SVG → HTML офлайн"], "b rep")
box(1180, 675, 390, 140, "LLM · OpenAI Responses API", ["gpt-6-luna / gpt-6.1-sol — модель за задачею", "httpx, ключ лише в .env; до 3 рівнів моделей", "єдиний зовнішній сервіс"], "b llm")
line("M1015 265 H1095 V122 H1170", "ln", "6", 1095, 190)
line("M1370 210 V250", "ln", "7", 1370, 230)
line("M1013 400 H1135 V470 H1170", "ln", "9", 1135, 435)
line("M1013 445 H1115 V745 H1180", "ln ai", "8", 1115, 600)

svg = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" xmlns="http://www.w3.org/2000/svg">
<title id="t">Архітектура Data Story</title>
<desc id="d">Браузер, сервер Data Story з модулями, SQLite і файли, RAG з моделлю bge-m3, Quarto та OpenAI; стрілки 1–9 — потоки даних.</desc>
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
 ("2", "Інтерфейс ⇄ Оркестратор", "виклик сервісу з даними форми", "результат або зрозуміла помилка", "pydantic-контракти, Success / Failure"),
 ("3", "Оркестратор ⇄ модулі", "набір, параметри розрахунку, обрані поля", "статистика, SVG, зведення, модель, текст AI", "pandas, NumPy, DuckDB, scikit-learn, SciPy"),
 ("4", "Модулі ⇄ SQLite", "SQL: читання й запис стану, подія журналу", "рядки: проєкти, метадані, моделі, звіти", "SQLite (sqlite3), схема v16"),
 ("5", "Модулі ⇄ файли", "CSV, матриці вибірок, SVG і HTML звітів", "файли з перевіркою SHA-256", "файлова система runtime/"),
 ("6", "Оркестратор ⇄ RAG", "питання користувача або факти моделі", "3–5 фрагментів правил і книжок із джерелом і сторінками", "TF-IDF (scikit-learn) + вектори"),
 ("7", "RAG ⇄ bge-m3", "текст запиту (фрагменти — заздалегідь)", "вектор 1024 чисел для пошуку за змістом", "ONNX Runtime, BAAI/bge-m3"),
 ("8", "AI-логіка ⇄ OpenAI", "інструкції + факти (JSON) + фрагменти + список інструментів", "текст / JSON або виклик інструмента; інструмент виконує сервіс локально й повертає результат", "OpenAI Responses API, httpx"),
 ("9", "AI-логіка ⇄ Quarto", "Markdown звіту (.qmd) і SVG-графіки", "HTML-звіт, що відкривається без інтернету", "Quarto CLI 1.10, MathJax, шрифти сервісу"),
]
rows = "".join(f'<tr><td class="n"><span class="nb{" o" if n=="8" else ""}">{n}</span></td><td class="who">{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td class="tech">{e(d)}</td></tr>' for n,a,b,c,d in flows)

steps = [
 ("1", "Користувач натискає «Підготувати висновки AI» на сторінці «Висновки»."),
 ("2", "Оркестратор перевіряє запит і бере збережену модель з SQLite."),
 ("3, 4, 5", "Модулі формують факти: R², MAE, коефіцієнти з p-value, обмеження; за потреби — до 3 зведень DuckDB із файлів."),
 ("6, 7", "З фактів складаються 3–4 запитання до бази знань; bge-m3 перетворює їх на вектори, RAG повертає 3–5 фрагментів правил і книжок."),
 ("8", "Один запит до OpenAI: інструкції + факти + фрагменти з номерами [1]…[5]. Відповідь перевіряється: посилання лише на наявні джерела, без HTML і коду."),
 ("4", "Чернетка зберігається в SQLite разом із фактами, джерелами й кількістю токенів; виклик записується в журнал AI."),
 ("1", "Автор редагує й затверджує текст; нова чернетка звіту бере затверджені висновки, Quarto (9) формує HTML."),
]
steplis = "".join(f'<li><span class="sn">{e(n)}</span><span>{e(t)}</span></li>' for n,t in steps)

page = f'''<title>Архітектура Data Story</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,600;0,700;1,400&family=STIX+Two+Text:wght@600;700&display=swap">
<style>
/* Layout: one 16:9 diagram (slide-ready), then the flow table and one worked request. Single light look by choice (a printed slide), colours set explicitly. */
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
.bt {{ font-size:16px; font-weight:700; }} .bl {{ font-size:13px; fill:var(--ink2) !important; }}
.srv {{ fill:none; stroke:var(--primary); stroke-width:2.5; }}
.srvl {{ font-size:14px; font-weight:600; fill:var(--primary) !important; }}
.zone {{ fill:none; stroke:#9aa4b2; stroke-width:1.2; stroke-dasharray:3 5; }}
.zl {{ font-size:13px; fill:var(--ink2) !important; font-style:italic; }} .zlo {{ font-size:13px; font-weight:600; fill:var(--ai) !important; }}
.ln {{ fill:none; stroke:var(--primary); stroke-width:2; }} .ln.ai {{ stroke:var(--ai); stroke-dasharray:7 5; }}
.bus {{ fill:none; stroke:#8a96a8; stroke-width:1.5; }}
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
.cols {{ display:grid; grid-template-columns:minmax(0,1.4fr) minmax(0,1fr); gap:32px; }}
ol.path {{ list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:10px; }}
ol.path li {{ display:grid; grid-template-columns:64px minmax(0,1fr); gap:10px; align-items:baseline; }}
.sn {{ font-weight:700; color:var(--primary); font-variant-numeric:tabular-nums; }}
.facts {{ display:flex; flex-direction:column; gap:10px; background:var(--shade); padding:16px 18px; }}
.facts p {{ margin:0; }}
@media (max-width:820px) {{ .cols {{ grid-template-columns:1fr; }} }}
</style>
<main>
<header>
  <span class="kicker">Data Story · фінальний проєкт курсу</span>
  <h1>Як влаштований сервіс і хто кому що передає</h1>
  <p class="lead">Окремі складові, пронумеровані потоки даних і технологія на кожному рівні. Усе працює на комп’ютері користувача; в інтернет іде лише запит до OpenAI, і лише за дією користувача.</p>
</header>
<div class="figure">{svg}</div>
<div class="legend">
  <span><i class="sw"></i>інтерфейс і ядро сервісу</span>
  <span><i class="sw c"></i>модулі розрахунків</span>
  <span><i class="sw r"></i>окремі локальні сервіси (RAG, Quarto)</span>
  <span><i class="sw s"></i>сховище</span>
  <span><i class="sw l"></i>AI / зовнішній сервіс</span>
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
<section class="cols">
  <div>
    <h2>Приклад: шлях запиту «Підготувати висновки AI»</h2>
    <ol class="path">{steplis}</ol>
  </div>
  <div class="facts">
    <h2>Принципи</h2>
    <p><b>Числа рахує сервіс, не AI.</b> Модель отримує готові факти й лише формулює текст.</p>
    <p><b>AI — лише явною дією.</b> Кожен виклик і токени видно в журналі AI; ключ не потрапляє в журнали.</p>
    <p><b>RAG локальний.</b> Пошук правил і книжок працює без інтернету; без моделі bge-m3 сервіс переходить на TF-IDF.</p>
    <p><b>Користувач не пише SQL.</b> DuckDB виконує запит, який сервіс складає з кроків.</p>
  </div>
</section>
</main>'''
open("architecture.html", "w", encoding="utf-8").write(page)
open("architecture.svg", "w", encoding="utf-8").write(svg)
print("ok", len(page))
