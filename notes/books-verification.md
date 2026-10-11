# Книжки в базі знань — перевірка 093

| Книга | Розділи (стор. PDF) | Фрагментів |
| --- | --- | --- |
| Ziller, Introduction to Statistics and Data Analysis (2024) | 7–88 | 109 |
| Müller & Guido, Introduction to Machine Learning with Python (2016) | 40–42, 59–70, 146–153, 226–288, 313–318 | 116 |
| Zaki & Meira, Data Mining and Analysis (2014) | 12–20, 46–78 | 47 |
| Tamal, Machine Learning: From Zero to Advanced | 9–17, 45–46, 62–63 | 18 |
| Boularouk, The Data Analyst's Handbook | 39–52, 79–150, 155–166 | 110 |
| Saunders, Lewis, Thornhill, Research Methods for Business Students (2023) | 599–663, 745–762, 770–779 | 220 |

Разом 620 фрагментів; індексація bge-m3 на Windows — 10,7 хв (одноразово; вектори у `runtime/knowledge-sources/vectors-*.npy`).

Калібрування (косинус найкращого фрагмента): типові питання 0,51–0,63; сторонні 0,35–0,50. Поріг 0,48, а якщо правила бази не знайшли нічого — 0,55.

Відтворення: покласти PDF у `sources/` під іменами з `selection.json`, `python tools/build_sources.py` (потрібен pdftotext), потім `tools/windows/Index-Books.cmd`.

Ліцензії: тексти захищені авторським правом — лише локальне використання; PDF, фрагменти й вектори поза Git.
