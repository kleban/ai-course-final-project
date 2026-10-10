# Офіційні джерела технологічної пропозиції

Дата перегляду: 2026-10-10 (Europe/Kiev). Роль: перевірити можливості кандидатів для архітектури; джерела не є вимогами курсу чи затвердженням стека. Реєстр: SRC-013 у PROJECT_PROFILE.md.

| Джерело | Що підтримує |
| --- | --- |
| [FastAPI](https://fastapi.tiangolo.com/) | Python API, валідація, автоматична документація |
| [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | Обмеження простих фонових задач; не видавати їх за надійну чергу тяжких обчислень |
| [Streamlit Plotly](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart) | Відображення інтерактивних графіків; theme=None для збереження бібліотечної теми |
| [Streamlit LaTeX](https://docs.streamlit.io/develop/api-reference/text/st.latex) | Формули, підтримуваний синтаксис KaTeX |
| [Streamlit upload](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader) | Завантаження файлів |
| [Streamlit state](https://docs.streamlit.io/develop/concepts/architecture/session-state), [widget behavior](https://docs.streamlit.io/develop/concepts/architecture/widget-behavior) | Перезапуски й сесійний стан; потрібен явний контроль повторного виклику операцій |
| [NiceGUI, офіційний репозиторій](https://github.com/zauberzeug/nicegui) | Python UI в браузері, кнопки, діалоги, завантаження, компонування; подієва модель |
| [React Quick Start](https://react.dev/learn) | UI-компоненти, події й стан на JavaScript; альтернативний frontend |
| [SQLite в Python](https://docs.python.org/3/library/sqlite3.html) | Файлова БД та стандартний клієнт sqlite3 |
| [pandas merge](https://pandas.pydata.org/docs/user_guide/merging.html) | З’єднання таблиць; перевірка validate й походження записів через indicator |
| [statsmodels OLS](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html) | Лінійна регресія; константа не додається автоматично без formula API, пропуски потрібно обробляти явно |
| [Plotly templates](https://plotly.com/python/templates/) | Власні теми й шаблони оформлення |
| [HTTPX](https://www.python-httpx.org/) | HTTP-клієнт Python для UI → backend |
| [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) | Типізовані структури й перевірка параметрів |
| [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling) | Модель запитує виклик функції; застосунок перевіряє аргументи, виконує функцію й повертає результат |
| [OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings) | Векторні представлення текстів для пошуку |
| [OpenAI Python API library](https://developers.openai.com/api/reference/python) | Python SDK і Responses API |
| [MathJax](https://docs.mathjax.org/en/latest/web/start.html) | Відображення формул у браузері, локальне підключення, повторна обробка динамічного вмісту |
| [pandas describe](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.describe.html), [isna](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isna.html), [corr](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.corr.html) | Описова статистика, маска пропусків і кореляції |
| [Plotly heatmaps](https://plotly.com/python/heatmaps/) | Відображення матриць тепловими картами |

Вивчено релевантні частини, не всю документацію кожної бібліотеки. Номери версій і пакетну сумісність не фіксуємо до реалізації. Кілька сторінок Streamlit architecture overview/server-client та NiceGUI documentation не відкрилися через вебінструмент; використано доступні офіційні сторінки state/widget behavior і офіційний репозиторій NiceGUI.

Також розглянуто pgvector та Sentence Transformers як альтернативи. Після рішень про локальний Python MVP і зовнішній OpenAI до першої пропозиції вони не включені: окрема PostgreSQL БД і локальні ваги embedding-моделі не потрібні для запропонованого малого корпусу. Це архітектурний висновок агента; якість і час пошуку перевірити на фактичних правилах.

## Доповнення: економне AI, історія 013

2026-10-10 прочитано релевантні офіційні сторінки [каталогу моделей OpenAI](https://developers.openai.com/api/docs/models), [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [gpt-6.1-sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small), [usage Responses](https://developers.openai.com/api/reference/python/resources/responses/methods/create), [prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), [keyring](https://keyring.readthedocs.io/en/latest/), [CredWrite](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew) і [DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata). Результат — [ai-settings.md](../planning/ai-settings.md). Це перевірка документації; доступ моделей, якість, інтеграції й економію не тестували.


## DuckDB — історія 026

2026-10-10 прочитано релевантні розділи [Python API](https://duckdb.org/docs/current/clients/python/overview) (DataFrames, Result Conversion, Connection Options) і [SQL on Pandas](https://duckdb.org/docs/current/guides/python/sql_on_pandas). Підтверджено: SQL над pandas DataFrame, результат у DataFrame, з’єднання в пам’яті або з файлом; документація рекомендує власне з’єднання замість глобального. Це джерела для архітектури 0.4 (SRC-013). DuckDB не встановлювали, сумісність Windows/Python 3.13 та інтеграцію не перевіряли. Роль у нашому MVP — етап 05: з’єднання й агрегації; метадані залишаються в SQLite.

## Quarto — історія 027

2026-10-10 прочитано релевантні частини офіційних [форматів](https://quarto.org/docs/output-formats/all-formats), [HTML Basics](https://quarto.org/docs/output-formats/html-basics.html), [PDF Basics](https://quarto.org/docs/output-formats/pdf-basics.html), [Using Python](https://quarto.org/docs/computations/python.html) і [Get Started](https://quarto.org/docs/get-started/). Quarto перетворює документи у HTML/PDF/Word; HTML підтримує математичні формули через MathJax, PDF через LaTeX потребує TeX (наприклад TinyTeX). Виконувані Python-блоки підтримуються, але для нашого першого звіту пропонується використовувати готові результати без повторного виконання. Це доповнення SRC-013; Quarto запропоновано автором, не обрано, не встановлено й не протестовано.

## AI-помічник і голос — історія 061

2026-10-11 прочитано офіційні сторінки [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling) та [file transcription](https://developers.openai.com/api/docs/guides/speech-to-text), документацію [SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition), [processLocally](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally), [available()](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/available_static). Можливість передачі інструменту/аргументів застосунку підтверджена; виконання здійснює наш код. Браузерний API підтримує розпізнавання, але може використовувати сервер; processLocally експериментальний і потребує мовного пакета. Наявність локального uk-UA у браузері автора не встановлена, реальні аудіо/API-виклики не виконували. Автор віддав перевагу браузерному розпізнаванню; OpenAI-транскрипція лишається вивченим альтернативним варіантом, не обраним. Деталі й критерії — planning/ai-assistant.md. Це джерела технологічної пропозиції SRC-013, не вимоги курсу.
