from html import escape as e
from pathlib import Path
from shutil import copyfile

# Architecture of Data Story as implemented (history 118): grouped layers, numbered flows 1–7.
# Generates deliverables/architecture/{architecture.html, architecture.svg} and the in-app page
# src/data_story/assets/about/index.html («Про проєкт»). Run: python deliverables/architecture/build.py

W, H = 1600, 920
parts = []
def box(x, y, w, h, title, lines, cls="b", tcls="bt", lcls="bl", pad=14):
    parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    ty = y + 26
    for t in title.split("\n"):
        parts.append(f'<text class="{tcls}" x="{x+pad}" y="{ty}">{e(t)}</text>'); ty += 19
    ty += 4
    for t in lines:
        parts.append(f'<text class="{lcls}" x="{x+pad}" y="{ty}">{e(t)}</text>'); ty += 16

def line(d, n, bx, by, ai=False, label=None, lx=0, ly=0):
    m = "o" if ai else ""
    parts.append(f'<path class="ln{" ai" if ai else ""}" d="{d}" marker-start="url(#as{m})" marker-end="url(#ae{m})"/>')
    if label:
        parts.append(f'<text class="busl" x="{lx}" y="{ly}">{e(label)}</text>')
    parts.append(f'<circle class="bd{" bdo" if ai else ""}" cx="{bx}" cy="{by}" r="13"/><text class="bn" x="{bx}" y="{by+4.5}">{n}</text>')

# zones: everything is local except the bottom-right corner (internet)
parts.append('<path class="zone" d="M15 15 H1590 V690 H1210 V870 H15 Z"/>')
parts.append('<text class="zl" x="30" y="895">Комп’ютер користувача (Windows) · розрахунки, дані, SQL, RAG і звіти — локально</text>')
parts.append('<text class="zlo" x="1235" y="712">Інтернет · HTTPS</text>')

box(30, 45, 240, 130, "Користувач у браузері", ["Chrome / Edge · Vue + Quasar", "формули MathJax", "усі ресурси локальні"], "b user")
box(30, 420, 240, 100, "Quarto 1.10", ["окремий процес, офлайн", ".qmd + SVG → HTML-звіт"], "b rep")

# server: UI → one service that contains two groups of modules
parts.append('<rect class="srv" x="300" y="35" width="880" height="605"/>')
parts.append('<text class="srvl" x="318" y="60">Сервер Data Story · один процес Python 3.13 · 127.0.0.1:8765</text>')
box(325, 75, 830, 70, "Інтерфейс і API", ["NiceGUI 3 (сторінки) + FastAPI (HTTP /api, JSON) на uvicorn"], "b core")
box(325, 185, 830, 435, "Сервіс-оркестратор (ProjectService)", ["перевіряє дані й поточний проєкт, викликає модулі, пише журнал; спільний для сторінок, чату й API"], "b core")

box(345, 260, 415, 340, "Аналітичні модулі", [], "b grp", "bt")
chips = [("Дані й статистика", "pandas, NumPy, CSV"), ("Графіки", "SVG, спільна тема"),
         ("Підготовка й зведення", "вибірки, з’єднання"), ("Модель", "scikit-learn, SciPy"),
         ("Звіти", "знімок → Markdown")]
for i, (t, l) in enumerate(chips):
    box(360 + (i % 2) * 198, 300 + (i // 2) * 95, 188, 80, t, [l], "b mod", "btm", "bl", 12)

box(780, 260, 355, 340, "AI — лише явною дією", [], "b grp ai", "bt")
box(795, 300, 325, 80, "Чат-помічник", ["Порадь · Виконай · Поясни"], "b mod modai", "btm", "bl", 12)
box(795, 395, 325, 80, "Вбудовані AI-функції", ["пояснення, висновки, чернетки звітів"], "b mod modai", "btm", "bl", 12)
box(795, 490, 325, 95, "Аналітичні запити", ["SQL від LLM → перевірка сервісом:", "1 SELECT, таблиці проєкту, 5 с, 512 МБ"], "b mod", "btm", "bl", 12)

# storage
box(300, 680, 880, 165, "Сховища · runtime/", [], "b store grp2", "bt")
box(320, 720, 270, 110, "Файли", ["CSV-оригінали з SHA-256,", "матриці .npz, HTML звітів,", "уривки книжок, вектори"], "b", "btm", "bl", 12)
box(605, 720, 270, 110, "SQLite (схема v16)", ["проєкти, метадані, налаштування,", "журнали подій і AI,", "тексти висновків і звітів"], "b", "btm", "bl", 12)
box(890, 720, 270, 110, "Постійна DuckDB", ["набори й результати з версіями:", "статистика, дані графіків,", "метрики, прогнози, залишки"], "b", "btm", "bl", 12)

# right column
box(1230, 260, 340, 140, "RAG · база знань", ["правила (SQLite) + 106 уривків книжок", "пошук: TF-IDF + bge-m3 (ONNX)", "→ 3–5 фрагментів із джерелами"], "b rag")
box(1230, 735, 340, 110, "LLM · OpenAI Responses API", ["gpt-6-luna / gpt-6.1-sol", "ключ лише в .env · через інтернет"], "b llm")

line("M270 110 H325", "1", 297, 110)
line("M740 145 V185", "2", 740, 165)
line("M552 600 V680", "3", 552, 650)
line("M345 470 H270", "4", 300, 470)
line("M1135 330 H1230", "5", 1190, 330)
line("M957 585 V720", "6", 957, 650, label="SQL від LLM", lx=972, ly=705)
line("M1135 540 H1195 V790 H1230", "7", 1195, 660, ai=True)

svg = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" xmlns="http://www.w3.org/2000/svg">
<title id="t">Архітектура Data Story</title>
<desc id="d">Браузер → інтерфейс → сервіс, у якому дві групи: аналітичні модулі та AI. Аналітика працює зі сховищами й Quarto; AI — з RAG, OpenAI і через перевірений SQL з DuckDB. Стрілки 1–7 — потоки даних.</desc>
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
 ("2", "Інтерфейс ⇄ Сервіс", "виклик сервісу з даними форми або HTTP-запиту", "результат або зрозуміла помилка", "pydantic-контракти; один ProjectService для сторінок, чату й API"),
 ("3", "Аналітичні модулі ⇄ сховища", "нові версії таблиць і результатів; службовий стан; оригінали файлів", "збережені таблиці й результати без повторного розрахунку; проєкти, метадані, журнали", "DuckDB 1.5 (аналітика), SQLite v16 (стан), файли з SHA-256"),
 ("4", "Звіти ⇄ Quarto", "Markdown звіту (.qmd): знімок моделі, статистика, SVG-графіки, затверджені висновки", "HTML-звіт, що відкривається без інтернету", "Quarto CLI 1.10, MathJax, шрифти сервісу"),
 ("5", "AI ⇄ RAG", "питання користувача або факти моделі", "3–5 фрагментів правил і книжок із джерелом і сторінками", "TF-IDF + bge-m3 (ONNX Runtime), локально"),
 ("6", "Аналітичні запити ⇄ DuckDB", "SQL, який склала LLM; згадані таблиці проєкту копіюються в окрему тимчасову DuckDB", "до 10 000 рядків і 2 МБ результату; новий набір — лише після «Застосувати»", "перевірка: один SELECT, лише таблиці поточного проєкту; 512 МБ, 5 с"),
 ("7", "AI ⇄ OpenAI", "інструкції + факти (JSON) + фрагменти RAG; чату — ще схема таблиць і список інструментів", "текст / JSON або виклик інструмента; інструмент і SQL виконує сервіс локально", "OpenAI Responses API, httpx"),
]
rows = "".join(f'<tr><td class="n"><span class="nb{" o" if n=="7" else ""}">{n}</span></td><td class="who">{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td class="tech">{e(d)}</td></tr>' for n,a,b,c,d in flows)

sql_steps = [
 ("1, 2", "Користувач питає помічника, наприклад: «О котрій годині найбільше прокатів?»."),
 ("7", "Сервіс надсилає питання, схему таблиць проєкту й дозволені інструменти. LLM повертає виклик query_analytics із текстом SQL."),
 ("6", "Сервіс перевіряє SQL (один SELECT, лише таблиці проєкту) і виконує його в ізольованій DuckDB з обмеженням часу й пам’яті."),
 ("7", "Таблиця результату повертається LLM, яка формулює відповідь. Для Seoul: пік о 18:00, середнє ≈ 1554 прокатів."),
 ("1", "Щоб зберегти результат як набір, користувач переглядає таблицю й натискає «Застосувати»."),
]
steps = [
 ("1, 2", "Користувач натискає «Підготувати висновки AI» на сторінці «Висновки»."),
 ("3", "Сервіс бере збережену модель і факти: R², MAE, коефіцієнти з p-value; за потреби — до 3 зведень із DuckDB."),
 ("5", "З фактів складаються запитання до бази знань; RAG повертає 3–5 фрагментів правил і книжок."),
 ("7", "Один запит до OpenAI: інструкції + факти + фрагменти [1]…[5]. Відповідь перевіряється: посилання лише на наявні джерела."),
 ("3", "Чернетка зберігається в SQLite з фактами, джерелами й токенами; виклик записується в журнал AI."),
 ("1, 4", "Автор редагує й затверджує текст. «Звіти» збирають знімок, Quarto формує HTML."),
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
.b.grp {{ fill:#fff; stroke-dasharray:none; }} .b.grp.ai {{ fill:#fffaf3; stroke:var(--ai); }} .b.grp2 {{ fill:var(--store); }}
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
  <p class="lead">Схема відповідає реалізованому коду; читати зверху вниз: користувач → інтерфейс → сервіс → дві групи модулів → сховища та зовнішні складові. Аналітичні таблиці й результати зберігаються в постійній DuckDB, службовий стан — у SQLite. AI використовується двома способами: чат-помічник і вбудовані AI-функції на робочих етапах. Обидва користуються спільним клієнтом OpenAI, RAG і результатами сервісу; SQL від LLM виконує лише сервіс після перевірки.</p>
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
