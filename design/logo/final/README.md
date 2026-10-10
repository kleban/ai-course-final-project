# Фінальний логотип Data Story (історія 024)

Джерело — растровий логотип автора `source/author-logo.jpg`. Він точно переведений у вектор: контури знайдено на зображенні, збільшеному в 4 рази, без перемальовування на око. Кольори з оригіналу: синій `#174690` (знак і DATA), темний `#3B3B38` (STORY і слоган). Тло прозоре. Генератор — `source/build.py` (Python, OpenCV, Pillow).

| Файл | Для чого | Де в сервісі |
| --- | --- | --- |
| `logo-full.svg` / `.png` | повний логотип, як в оригіналі: знак, DATA STORY, слоган | — |
| `logo-panel.svg` | те саме для розгорнутої лівої панелі | `src/data_story/assets/logo/logo-panel.svg` |
| `logo-mark.svg` / `.png` | лише знак — для згорнутого меню | `…/logo-mark.svg` |
| `logo-horizontal.svg` / `.png` | знак ліворуч, назва й слоган праворуч — для широких місць (презентація, README) | — |
| `logo-icon.svg`, `favicon.ico` (16/32/48), `apple-touch-icon.png` (180), `logo-icon-192.png`, `logo-icon-512.png` | іконка вкладки: книга зі знака, квадрат | `…/logo-icon.svg` (favicon), `apple-touch-icon.png` |
| `preview-sheet.png` | усі варіанти, зокрема в розмірах 16–96 px | — |
| `app-panel-expanded-and-collapsed.png` | панель сервісу розгорнута й згорнута | — |

Чернетки з історії 023 (`design/logo/*.svg`, `png/`, `source/`) застарілі; їх можна видалити.
